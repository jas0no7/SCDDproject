import json

import numpy as np
import pandas as pd
from loguru import logger

from logs.log_decorator import log_execution
from modules.config import SQL, Statistical_Time, import_data_with_cursor


def month(value):
    if value is None or pd.isna(value):
        return pd.NaT
    if isinstance(value, pd.Period):
        return value.asfreq('M')
    text = str(value).strip()
    # SQL 数值月份和空值一起装入 DataFrame 时可能被转换成浮点数。
    whole, dot, fraction = text.partition('.')
    if dot and fraction and set(fraction) == {'0'} and len(whole) == 6 and whole.isdigit():
        text = whole
    if len(text) == 6 and text.isdigit():
        date = pd.to_datetime(text, format='%Y%m', errors='coerce')
    else:
        date = pd.to_datetime(text, errors='coerce')
    return date.to_period('M') if pd.notna(date) else pd.NaT


def station_metadata(stations):
    """按站编号建立主数据；投资或投运日期互相矛盾的站点返回为冲突项。

    重复但完全相同的行只保留一条，避免主数据关联多行时整页无法计算。
    """
    frame = stations.copy()
    frame['station_no'] = frame['station_no'].astype(str).str.strip()
    metadata = {}
    conflicts = []
    for code, rows in frame.groupby('station_no', sort=False):
        distinct = rows[['investment_amount', 'commissioning_time']].drop_duplicates()
        if len(distinct) > 1:
            # 冲突站点保留编号，但把金额和日期置为缺失，只让相关映射不可预测。
            metadata[code] = {'investment_amount': np.nan, 'commissioning_time': pd.NaT}
            conflicts.append(code)
        else:
            metadata[code] = rows.iloc[0].to_dict()
    return metadata, conflicts


def _monthly(frame, date_column, values):
    frame = frame.copy()
    frame['month'] = frame[date_column].map(month)
    frame['station_no'] = frame['station_no'].astype(str).str.strip()
    frame = frame.dropna(subset=['month'])
    for name in values:
        frame[name] = pd.to_numeric(frame[name], errors='coerce')
    return frame.groupby(['station_no', 'month'], as_index=False)[values].sum(min_count=1)


def build_histories(stations, subsidy, operating, rent, sharing, maintenance, end_month):
    """保留无经营记录的月份为缺失，辅助来源无记录仍按既有口径取零。"""
    operating = _monthly(operating, 'cba_month', ['revenue', 'cost'])
    sharing = _monthly(sharing, 'rec_month', ['merchant_profit_amount'])
    maintenance = _monthly(maintenance, 'stat_time', ['maintenance_cost'])
    subsidy = subsidy.copy()
    subsidy['station_no'] = subsidy['station_no'].astype(str).str.strip()
    subsidy['year_key'] = subsidy['year'].astype(str).str[:4]
    subsidy = subsidy.groupby(['station_no', 'year_key'], as_index=False)['total_subsidy'].sum(min_count=1)
    rent = rent.copy()
    rent['station_no'] = rent['station_no'].astype(str).str.strip()
    # 多条租金规则不能直接与月度收支关联，否则会把整个月的收入成本重复累加。
    duplicate_rent = set(rent.loc[rent.duplicated('station_no', keep=False), 'station_no'])
    invalid_rent = set(rent.loc[~np.isfinite(pd.to_numeric(rent['parking_fee'], errors='coerce')), 'station_no'])
    rent = rent.drop_duplicates('station_no')
    end = month(end_month)
    histories = {}
    for row in stations.itertuples(index=False):
        code = str(row.station_no).strip()
        start = month(row.commissioning_time)
        if pd.isna(start) or start > end:
            histories[code] = pd.DataFrame()
            continue
        h = pd.DataFrame({'month': pd.period_range(start, end, freq='M')})
        h['station_no'] = code
        h = h.merge(operating, how='left', on=['station_no', 'month'], validate='one_to_one')
        for column in ['revenue', 'cost']:
            h[column] = pd.to_numeric(h[column], errors='coerce')
        h['observed'] = np.isfinite(h['revenue']) & np.isfinite(h['cost'])
        for source, column in [(sharing, 'merchant_profit_amount'), (maintenance, 'maintenance_cost')]:
            h = h.merge(source, how='left', on=['station_no', 'month'], validate='one_to_one')
            h[column] = pd.to_numeric(h[column], errors='coerce').fillna(0)
        h = h.merge(rent[['station_no', 'parking_fee']], how='left', on='station_no', validate='many_to_one')
        h['parking_fee'] = pd.to_numeric(h['parking_fee'], errors='coerce').fillna(0)
        h['year_key'] = h['month'].map(lambda p: str(p.year))
        h = h.merge(subsidy, how='left', on=['station_no', 'year_key'], validate='many_to_one')
        # 保留现有年度补贴在截至统计月的投运月份间平均分摊的规则。
        # 先汇总同年补贴，避免一对多合并把经营数据放大。
        h['total_subsidy'] = pd.to_numeric(h['total_subsidy'], errors='coerce').fillna(0)
        h['subsidy'] = h['total_subsidy'] / h.groupby('year_key')['month'].transform('size')
        h['net'] = (h['revenue'] + h['subsidy'] - h['cost'] - h['parking_fee']
                    - h['merchant_profit_amount'] - h['maintenance_cost'])
        h['observed'] &= np.isfinite(h['net'])
        h['complete_month'] = True
        if pd.Timestamp(row.commissioning_time).day != 1:
            h.loc[h['month'] == start, 'complete_month'] = False
        h = h.set_index('month').sort_index()
        if code in duplicate_rent or code in invalid_rent:
            h.attrs['rent_error'] = True
        histories[code] = h
    return histories


def _unavailable(reason):
    return {'years': None, 'status': '无法预测', 'reason': reason}


def estimate_period(stages, rate_code, metadata, histories, end_month, rate_end=None):
    """stages 为 (站编号, 现金流截止月)；各站投资只计一次。

    上游按新站投运日期选择旧站截止月。联合周期从最早站点的投运月起算。
    """
    end = month(end_month)
    rate_end = month(rate_end) if rate_end is not None else end
    total_investment = 0.0
    cash_parts = []
    starts = []
    investment_months = []
    seen = set()
    for code, stop in stages:
        if code in seen:
            continue
        seen.add(code)
        info = metadata.get(code)
        if info is None:
            return _unavailable('缺少站点主数据')
        investment = pd.to_numeric(info.get('investment_amount'), errors='coerce')
        if pd.isna(investment) or not np.isfinite(investment) or investment < 0:
            return _unavailable('缺少有效投资金额')
        start = month(info.get('commissioning_time'))
        stop = month(stop)
        if pd.isna(start) or pd.isna(stop) or pd.isna(end) or start > min(stop, end):
            return _unavailable('投运或截止月份无效')
        stop = min(stop, end)
        h = histories.get(code, pd.DataFrame())
        if h.empty:
            return _unavailable(f'{code} 缺少历史经营数据')
        if h.attrs.get('rent_error'):
            return _unavailable(f'{code} 租金金额无效或存在多个租金规则')
        required = pd.period_range(start, stop, freq='M')
        h = h.reindex(required)
        observed = h['observed'].eq(True)
        missing = required[~observed.to_numpy()]
        if len(missing):
            return _unavailable(f'{code} 历史经营数据不完整，'
                                f'涉及 {len(missing)} 个月（{missing[0]} 至 {missing[-1]}）')
        if not np.isfinite(h['net']).all():
            return _unavailable(f'{code} 历史收支净额无法计算')
        total_investment += float(investment)
        if investment > 0:
            investment_months.append(start)
        starts.append(start)
        cash_parts.append(h['net'])
    if not starts or total_investment <= 0:
        return _unavailable('总投资须大于零')

    start = min(starts)
    cash = pd.concat(cash_parts, axis=1).fillna(0).sum(axis=1).sort_index()
    cumulative = cash.cumsum()
    remaining = total_investment - float(cumulative.iloc[-1])
    elapsed = end.ordinal - start.ordinal + 1
    if remaining <= 0:
        # 若回收后又发生亏损，采用最后一段持续覆盖投资的起点。
        below = cumulative[cumulative < total_investment]
        crossing = cumulative.index[0] if below.empty else cumulative.index[cumulative.index > below.index[-1]][0]
        crossing = max(crossing, max(investment_months))
        return {'years': round((crossing.ordinal - start.ordinal + 1) / 12, 2),
                'status': '已回本', 'reason': '', 'remainingInvestment': 0.0}

    rate_history = histories.get(rate_code, pd.DataFrame())
    if rate_history.empty:
        return _unavailable(f'{rate_code} 缺少近期经营数据')
    sample = rate_history.loc[(rate_history.index <= rate_end) & (rate_history.index >= rate_end - 4)]
    sample = sample.loc[sample['observed'] & sample['complete_month']]
    if len(sample) < 2:
        return _unavailable('最近五个月不足两个完整有效经营月')
    monthly_net = float(sample['net'].mean())
    if not np.isfinite(monthly_net) or monthly_net <= 0:
        return _unavailable('月均净现金收益不为正，按当前收益无法回本')
    years = (elapsed + remaining / monthly_net) / 12
    if not np.isfinite(years):
        return _unavailable('预测年数超出可表示范围')
    return {'years': round(years, 2), 'status': '预测', 'reason': '',
            'remainingInvestment': round(remaining, 2),
            'monthlyNetCash': round(monthly_net, 2),
            'sampleMonths': [str(p) for p in sample.index]}


def comparison_record(old_code, before, after, comparable=True):
    """不可预测结果用 JSON null；保留原有 statistics 字段并补充状态。"""
    if before['years'] is None or after['years'] is None:
        summary = '；'.join(label + '：' + result['reason']
                           for label, result in [('技改前', before), ('技改后', after)]
                           if result['years'] is None)
    elif not comparable:
        summary = '技改后周期按多个旧站合并计算，无法与单个旧站直接比较'
    else:
        diff = round(before['years'] - after['years'], 2)
        summary = ('技改前后预计回本周期相同' if diff == 0 else
                   f"技改后，站点回本周期{'提前' if diff > 0 else '延后'}{abs(diff)}年")
    return {'siteNum': old_code,
            'statistics': [dict(title=label, name=name, value=result['years'], unit='年',
                                status=result['status'], reason=result['reason'])
                           for label, name, result in [('技改前', '预计回本期限', before),
                                                       ('技改后', '预计回本周期', after)]],
            'summary': summary}


def _money(values, multiplier=1):
    return pd.to_numeric(values.astype(str).str.replace(',', '', regex=False), errors='coerce') * multiplier


@log_execution
def runtechUpgradePaybackForecast():
    report_month, *_ = Statistical_Time()
    logger.info("开始执行技改站点回本周期预测，统计月={}", report_month)

    mapping = SQL("""
        SELECT old_code, new_code
        FROM dp_station_tech_upgrade_mapping
        ORDER BY id
    """)
    if mapping.empty:
        raise ValueError("dp_station_tech_upgrade_mapping 没有技改站点映射记录")

    mapping_columns = ['old_code', 'new_code']
    mapping[mapping_columns] = mapping[mapping_columns].astype('string').apply(lambda col: col.str.strip())
    if mapping[mapping_columns].isna().any().any() or mapping[mapping_columns].eq('').any().any():
        raise ValueError("dp_station_tech_upgrade_mapping 存在空的映射字段")
    mapping = mapping.drop_duplicates(mapping_columns)
    station_codes = pd.unique(pd.concat([mapping['old_code'], mapping['new_code']]))
    codes_sql = ', '.join("'{}'".format(code.replace("'", "''")) for code in station_codes)

    stations = SQL(f"""
        SELECT station_no, commissioning_time, investment_amount
        FROM charging_station
        WHERE station_no IN ({codes_sql})
    """)
    stations['investment_amount'] = _money(stations['investment_amount'])
    stations['station_no'] = stations['station_no'].astype(str).str.strip()
    stations['commissioning_time'] = pd.to_datetime(stations['commissioning_time'], errors='coerce')
    metadata, conflict_codes = station_metadata(stations)
    if conflict_codes:
        logger.warning("站点主数据存在重复且投资或投运时间不一致，相关站点无法预测：{}", conflict_codes)

    subsidy = SQL(f"""
        SELECT year, station_no, total_subsidy
        FROM dp_subsidy_NEW
        WHERE station_no IN ({codes_sql})
    """)
    subsidy['total_subsidy'] = _money(subsidy['total_subsidy'], 10000)

    # 预测用经营现金收益，保留人工成本，排除非现金折旧。
    operating = SQL(f"""
        SELECT b.station_no, b.cba_month,
               SUM(IFNULL(b.rec_data_elec_fee_revenue, 0) + IFNULL(b.rec_data_service_fee_revenue, 0)
                 + IFNULL(b.other_revenue_battery_swap_services, 0) + IFNULL(b.other_revenue_op_subsidies, 0)
                 + IFNULL(b.other_revenue_build_subsidies, 0) + IFNULL(b.other_revenue_access_control_barriers, 0)
                 + IFNULL(b.other_revenue_dr, 0)) AS revenue,
               SUM(IFNULL(b.rec_cost_elec_fee, 0) + IFNULL(b.rec_cost_actual_rec_amount, 0)
                 + IFNULL(b.rec_cost_plat_service, 0) + IFNULL(b.rec_cost_rent, 0) + IFNULL(b.om_cost_om, 0)
                 + IFNULL(b.om_cost_spare_parts, 0) + IFNULL(b.om_cost_op_project, 0)
                 + IFNULL(b.fin_cost_labor, 0)) AS cost
        FROM station_cba_org_data b
        WHERE b.station_no IN ({codes_sql}) AND b.cba_month <= '{report_month}'
        GROUP BY b.station_no, b.cba_month
    """)

    rent = SQL(f"""
        SELECT DISTINCT cs.station_no, rmr.merchant_id,
               JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) AS parking_fee
        FROM charging_station cs
        LEFT JOIN rec_merchant_rec_station rmr ON cs.station_no = rmr.station_on
        LEFT JOIN scdd_rec_rules sr ON rmr.merchant_id = sr.merchant_id
        WHERE cs.station_no IN ({codes_sql})
          AND JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL
    """)
    rent['parking_fee'] = _money(rent['parking_fee'])

    sharing = SQL(f"""
        SELECT station_no, rec_month, SUM(IFNULL(merchant_profit_amount, 0)) AS merchant_profit_amount
        FROM fin_rec_result_detail
        WHERE station_no IN ({codes_sql}) AND rec_month <= {report_month} AND merchant_id != 119
        GROUP BY station_no, rec_month
    """)
    maintenance = SQL(f"""
        SELECT station_no, stat_time, SUM(maintenance_cost) AS maintenance_cost
        FROM dp_station_maintenance_cost1
        WHERE station_no IN ({codes_sql}) AND stat_time <= {report_month} AND maintenance_cost > 0
        GROUP BY station_no, stat_time
    """)
    maintenance['maintenance_cost'] = _money(maintenance['maintenance_cost'], 10000)

    deduplicated_stations = stations.loc[~stations['station_no'].isin(conflict_codes)].drop_duplicates('station_no')
    histories = build_histories(deduplicated_stations, subsidy, operating,
                                rent, sharing, maintenance, report_month)
    records = []
    for new_code, related in mapping.groupby('new_code', sort=False):
        old_codes = related['old_code'].tolist()
        new_date = metadata.get(new_code, {}).get('commissioning_time')
        new_start = month(new_date)
        reason = ''
        if new_code in old_codes:
            reason = '技改映射的新旧站编号相同'
        elif pd.isna(new_start):
            reason = '缺少有效新站投运日期'
        elif new_start > month(report_month):
            reason = '截至统计月尚未技改'

        if reason:
            unavailable = {'years': None, 'status': '无法预测', 'reason': reason}
            records.extend(comparison_record(code, unavailable, unavailable) for code in old_codes)
            continue

        # 月初切换时，旧站累计截至上月。月中切换时，计入两个编号各自的当月实绩。
        # 技改前月均收益不取月中切换的当月，技改后由新站完整经营月估算。
        old_end = new_start - 1 if new_date.day == 1 else new_start
        stages = [(code, old_end) for code in old_codes] + [(new_code, report_month)]
        after = estimate_period(stages, new_code, metadata, histories, report_month)
        for old_code in old_codes:
            before = estimate_period([(old_code, old_end)], old_code, metadata, histories,
                                     old_end, rate_end=new_start - 1)
            records.append(comparison_record(old_code, before, after, comparable=len(old_codes) == 1))
            logger.info("技改回本预测：旧站={}，新站={}，技改前={}，技改后={}",
                        old_code, new_code, before, after)

    result = pd.DataFrame([{
        'result': json.dumps(records, ensure_ascii=False, allow_nan=False),
        'update_time': report_month,
    }])
    import_data_with_cursor(
        df=result,
        table_name="dp_jigai_result_expectedPaybackPeriod",
        table_comment="技改站点_预计回本周期",
        column_comments={'result': '预计回本周期', 'update_time': '更新日期'},
        append_data=False,
        update_columns=True,
    )
