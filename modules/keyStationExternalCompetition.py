from logs.log_decorator import log_execution
from loguru import logger
from modules.config import SQL,import_data_with_cursor,Statistical_Time



@log_execution
def runkeyStationExternalCompetition():
    logger.info("开始执行重点站点外部竞争页面")
    import pandas as pd
    import numpy as np
    import pymysql
    from datetime import datetime ,date
    import os
    from dateutil.parser import parse
    import json
    from pandas.tseries.offsets import MonthBegin
    import calendar
    from dateutil.relativedelta import relativedelta
    from sklearn.preprocessing import StandardScaler
    from sklearn.preprocessing import MinMaxScaler
    from functools import reduce
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)


    def get_days_in_month(year_month):
        """
        获取指定年月的天数

        参数:
            year_month (str): 格式为 'YYYYMM' 的字符串，如 '202502'

        返回:
            int: 该月的天数
        """
        year = int(year_month[:4])
        month = int(year_month[4:6])
        return calendar.monthrange(year, month)[1]




    def generate_months(start_month, num_months):
        """
        从给定的起始月份开始，生成往后推指定月数的月份列表，并返回一个 DataFrame。

        参数:
        start_month (str): 起始月份，格式为 'YYYYMM'。
        num_months (int): 要生成的月份数。

        返回:
        pd.DataFrame: 包含月份的 DataFrame，列名为 'month'。
        """
        # 将起始月份转换为 pandas 的日期格式
        start_date = pd.to_datetime(start_month, format='%Y%m')

        # 生成往前推指定月数的日期列表
        date_list = [start_date - i* MonthBegin(1) for i in range(num_months + 1)]  # 包含起始月份

        # 格式化日期为 'YYYYMM' 格式
        month_list = [date.strftime('%Y%m') for date in date_list]

        # 创建 DataFrame
        df = pd.DataFrame(month_list, columns=['month'])

        return df


    Data = generate_months(M, 11)

    Data

    # ### 查询语句

    # In[236]:


    M

    # In[237]:


    sql = f"""
    SELECT
        * 
    FROM
        dp_ProvincialSupervisionPlatform
    """
    DF_out = SQL(sql)

    # In[238]:


    DF_out1 = DF_out[DF_out['date'] == M].copy()

    # In[239]:


    DF_out1.columns

    # In[240]:


    sql = """
    SELECT
        * 
    FROM
        dp_KeyStations_CompetitorStationsCodeMapping
    """
    DF_number = SQL(sql)

    # In[241]:


    DF_number.columns

    # In[242]:


    import_id = DF_number['dd_station_id'].unique()

    # In[243]:


    DF_im_out = DF_number.merge(
        DF_out1[
            ['station_id', 'station_name',
             'district', 'equip_power', 'piles_num',
             'charging_num', 'electricity_quantity', 'power_rate',
             'charging_quantity_per_gun', 'electricity_fee', 'service_fee']
        ],

        left_on=['sjg_station_id', 'sjg_station_name'],
        right_on=['station_id', 'station_name'],
        how='left',
    )

    # In[244]:


    DF_im_out

    # ### 单枪日均充电量

    # In[245]:


    sql = """
    select * from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    cs.operation_status in ('投运','退运')) a
    left join 
    (select * from station_cba_org_data  ) b
    on a.station_no =b.station_no
    """
    DF_cba_org_data = SQL(sql)

    # In[246]:


    DF_cba_org_data = DF_cba_org_data.loc[:, ~DF_cba_org_data.columns.duplicated()]
    mask = DF_cba_org_data['station_no'].astype(str).isin([str(x) for x in import_id])
    DF_cba_org_data = DF_cba_org_data[mask]

    # In[247]:


    DF_cba_org_data = DF_cba_org_data[DF_cba_org_data['station_no'].isin(import_id)]

    # In[248]:


    DF_cba_org_data['total_charge_point_count'] = DF_cba_org_data['dc_charge_point_count'].fillna(0) + DF_cba_org_data['ac_charge_point_count'].fillna(0)

    # In[249]:


    DF_cba_org_data = DF_cba_org_data[(DF_cba_org_data['total_charge_point_count'] != 0) & (DF_cba_org_data['operation_status'] == '投运')]
    DF_cba_org_data = DF_cba_org_data[DF_cba_org_data['plat_data_charging_volume'] != 0]

    # In[250]:


    DF_cba_org_data['days'] = DF_cba_org_data['cba_month'].apply(get_days_in_month)

    # In[ ]:


    # In[251]:


    cols_to_convert = ['plat_data_charging_volume', 'charge_point_count', 'days']

    # 把非数字强制转为 NaN
    DF_cba_org_data[cols_to_convert] = DF_cba_org_data[cols_to_convert].apply(pd.to_numeric, errors='coerce')

    # 再做除法
    DF_cba_org_data['charging_quantity_per_gun'] = (
            DF_cba_org_data['plat_data_charging_volume'] /
            DF_cba_org_data['total_charge_point_count'] /
            DF_cba_org_data['days']
    )

    # In[252]:


    DF_cba_org_data[['plat_data_charging_volume', 'total_charge_point_count', 'days', 'charging_quantity_per_gun']]

    # ### 功率利用率

    # In[253]:


    # 功率利用率

    sql = """
    SELECT 
      rm.merchant_name,
      cs.*,
      scod.plat_data_charging_volume,
      scod.cba_month
    FROM charging_station cs
    LEFT JOIN rec_merchant rm 
      ON cs.property_owner_merhant_id = rm.merchant_id
    INNER JOIN station_cba_org_data scod 
      ON cs.station_no = scod.station_no
    WHERE 
      rm.merchant_name = '国网电动汽车服务（四川）有限公司'
      and cs.operation_status = '投运'
    """
    DF_cba_pue = SQL(sql)

    # In[254]:


    DF_cba_pue = DF_cba_pue[DF_cba_pue['station_no'].isin(import_id)]

    # In[255]:


    DF_cba_pue['days'] = DF_cba_pue['cba_month'].apply(get_days_in_month)
    DF_cba_pue = DF_cba_pue[
        (DF_cba_pue['station_capacity'].notna()) &
        (DF_cba_pue['station_capacity'] > 0) &
        (DF_cba_pue['plat_data_charging_volume'].notna())
        ]

    DF_cba_pue['power_rate'] = (DF_cba_pue['plat_data_charging_volume'] /
                                (DF_cba_pue['station_capacity'] * DF_cba_pue['days'] * 24))

    # In[ ]:


    # ### 站点额定功率

    # In[256]:


    sql = """
    select station_no,station_name,station_capacity as equip_power,
    (dc_charge_point_count + ac_charge_point_count) as charging_num
    from charging_station
    """
    DF_basic = SQL(sql)

    # In[257]:


    DF_basic = DF_basic[DF_basic['station_no'].isin(import_id)]

    # ### 充电量、充电价格

    # In[258]:


    sql = f"""
    SELECT
        station_no,
        cba_month,
        CASE
            WHEN SUM(plat_data_charging_volume) = 0 THEN NULL
            ELSE ROUND(SUM(plat_data_service_revenue) / SUM(plat_data_charging_volume), 4)
        END AS service_fee,
        SUM(plat_data_charging_volume) AS electricity_quantity,
        SUM(plat_data_elec_fee_revenue) AS total_elec_fee_revenue,
        CASE
            WHEN SUM(plat_data_charging_volume) = 0 THEN NULL
            ELSE ROUND(SUM(plat_data_elec_fee_revenue) / SUM(plat_data_charging_volume), 4)
        END AS electricity_fee
    FROM station_cba_org_data
    GROUP BY station_no, cba_month
    
    ORDER BY station_no, cba_month;
    """
    DF_ele = SQL(sql)

    # In[259]:


    DF_ele = DF_ele[DF_ele['station_no'].isin(import_id)]

    # In[260]:


    # 删除重复列（保留第一个出现的）
    DF_cba_org_data = DF_cba_org_data.loc[:, ~DF_cba_org_data.columns.duplicated()]
    DF_cba_pue = DF_cba_pue.loc[:, ~DF_cba_pue.columns.duplicated()]
    DF_ele = DF_ele.loc[:, ~DF_ele.columns.duplicated()]

    # 然后安全执行 merge
    DF_imp = DF_cba_org_data[['station_no', 'station_name', 'charging_quantity_per_gun', 'cba_month']].merge(
        DF_cba_pue[['station_no', 'station_name', 'power_rate', 'cba_month']],
        on=['station_no', 'station_name', 'cba_month'],
        how='outer'  # 根据你想保留的记录范围，可改为 inner/left/right/outer
    ).merge(
        DF_ele[['station_no', 'electricity_fee', 'electricity_quantity', 'service_fee', 'cba_month']],
        on=['station_no', 'cba_month'],
        how='left'  # DF_ele 没有 station_name，所以只按 station_no + cba_month 对齐
    )

    # In[261]:


    DF_imp1 = DF_imp[DF_imp['cba_month'] == M]

    # In[262]:


    DF_imp1.columns

    # In[263]:


    DF_imp1 = DF_imp1[['station_no', 'station_name', 'charging_quantity_per_gun',
                       'power_rate', 'electricity_fee', 'electricity_quantity', 'service_fee']]

    # In[264]:


    DF_basic

    # In[265]:


    DF_imp1 = DF_imp1.merge(
        DF_basic,
        on=['station_no', 'station_name'],
        how='left'
    )

    # ## 外部竞争力1

    # In[266]:


    import pandas as pd


    def add_self_row_ignore_distance(df: pd.DataFrame) -> pd.DataFrame:
        """
        给每个 dd 站补一条“自己 vs 自己”的记录；保留所有原字段，未赋值的字段自动为 NaN。
        """
        df = df.copy()

        # 拿到唯一的 dd 站点基础信息（只取一条）
        base = df[['dd_station_id', 'dd_station_name']].drop_duplicates('dd_station_id')

        # 创建与原 df 结构一致的空表
        self_rows = pd.DataFrame(columns=df.columns)

        # 仅设置核心字段，其余字段保持 NaN
        self_rows['dd_station_id'] = base['dd_station_id']
        self_rows['dd_station_name'] = base['dd_station_name']
        self_rows['sjg_station_id'] = base['dd_station_id']
        self_rows['sjg_station_name'] = base['dd_station_name']
      #  self_rows['station_category'] = base['station_category']

        # 合并原数据和补充的“自己 vs 自己”数据
        out = pd.concat([self_rows, df], ignore_index=True)

        # 添加标志列用于排序，将“自己 vs 自己”放在每组的第一条
        out['_is_self'] = (out['dd_station_id'] == out['sjg_station_id']).astype(int)
        out = (
            out.sort_values(['dd_station_id', '_is_self'], ascending=[True, False])
                .drop(columns=['_is_self'])
                .reset_index(drop=True)
        )

        return out


    # In[267]:


    result_df = add_self_row_ignore_distance(DF_im_out)

    # In[ ]:


    # In[268]:


    result_df

    # In[269]:


    # --- 1) 规范 DF_tmp，并建双键索引 ---
    # 注意这里要对齐正确的列名
    tmp = DF_imp1.rename(columns={'station_no': 'sjg_station_id',
                                  'station_name': 'sjg_station_name'}).copy()

    # 防止类型/空格不一致导致对不上
    tmp['sjg_station_id'] = tmp['sjg_station_id'].astype(str).str.strip()
    tmp['sjg_station_name'] = tmp['sjg_station_name'].astype(str).str.strip()

    # 若 (id,name) 有重复，保留最后一条或你需要的聚合规则
    tmp = (
        tmp.drop_duplicates(['sjg_station_id', 'sjg_station_name'], keep='last')
            .set_index(['sjg_station_id', 'sjg_station_name'])
        [['equip_power', 'charging_num', 'charging_quantity_per_gun',
          'power_rate', 'electricity_fee', 'electricity_quantity', 'service_fee']]
    )

    # --- 2) 规范 result_df 的键，并左连接带回新值 ---
    res = result_df.copy()
    res['sjg_station_id'] = res['sjg_station_id'].astype(str).str.strip()
    res['sjg_station_name'] = res['sjg_station_name'].astype(str).str.strip()

    res = res.join(tmp, on=['sjg_station_id', 'sjg_station_name'], rsuffix='_new')

    update_cols = ['equip_power', 'charging_num', 'charging_quantity_per_gun',
                   'power_rate', 'electricity_fee', 'electricity_quantity', 'service_fee']

    for col in update_cols:
        # 只更新指标列，不更新 id/name
        res[col] = np.where(res[col + '_new'].notna(), res[col + '_new'], res[col])

    # 删除临时列
    result_df = res.drop(columns=[c for c in res.columns if c.endswith('_new')], errors='ignore')

    # In[270]:


    state_competitiveSituation = result_df.copy()

    # In[271]:


    state_competitiveSituation = state_competitiveSituation.fillna(0)

    # In[272]:


    # 专门对 id 字段做字符串化，保证不丢失
    state_competitiveSituation['dd_station_id'] = state_competitiveSituation['dd_station_id'].astype(str).str.strip()
    state_competitiveSituation['sjg_station_id'] = state_competitiveSituation['sjg_station_id'].astype(str).str.strip()

    # ### 竞争现状

    # In[273]:


    state_competitiveSituation['power_rate'] = state_competitiveSituation['power_rate'] * 100

    # In[274]:


    # 假设你的 DataFrame 是 state_competitiveSituation1
    df = state_competitiveSituation.copy()

    # 定义要映射的字段名
    field_mapping = {
        'sjg_station_name': 'siteName',
        'distance': 'siteDistance',  # 改成 distance
        'equip_power': 'ratedPower',
        'piles_num': 'chargingCablesNum',
        'charging_quantity_per_gun': 'averageCharge',
        'service_fee': 'chargingServiceFee',
        'electricity_fee': 'chargingElectricityBills',
        'power_rate': 'powerUtilization'
    }

    # 结果列表
    data_competitiveSituation = []

    # 按重点站分组
    for dd_station_id, group in df.groupby('dd_station_id'):
        table_data = []
        # 遍历竞争站点行
        for row in group.itertuples():
            row_dict = {}
            for old_key, new_key in field_mapping.items():
                value = getattr(row, old_key)
                # 对数值类型保留两位小数
                if isinstance(value, (float, int)):
                    value = round(value, 2)
                row_dict[new_key] = value
            # 内层 siteNum 用竞争站站点编号
            row_dict['siteNum'] = getattr(row, 'sjg_station_id')
            table_data.append(row_dict)

        data_competitiveSituation.append({
            # 外层 siteNum 用重点站站点编号
            'siteNum': dd_station_id,
            'tableData': table_data
        })

    # In[275]:


    # data_competitiveSituation


    # In[276]:


    rows = []

    for block in data_competitiveSituation:
        dd_id = block.get("siteNum")
        table_data = block.get("tableData") or []
        for item in table_data:
            # 将单个竞争站对象压成 JSON 字符串（不带多余空格）
            tableData_str = json.dumps(item, ensure_ascii=False, separators=(',', ':'))
            rows.append({
                "siteNum": dd_id,
                "tableData": tableData_str
            })

    # 构造 DataFrame
    data_competitiveSituation2 = pd.DataFrame(rows)

    # 展示前几行看看结构


    # In[277]:


    data_competitiveSituation2['month'] = M

    # In[278]:


    # 删除现有的NULL id列（如果存在）
    if 'id' in data_competitiveSituation2.columns:
        data_competitiveSituation2 = data_competitiveSituation2.drop('id', axis=1)

    # 添加自增ID列
    data_competitiveSituation2['id'] = range(1, len(data_competitiveSituation2) + 1)

    # 或者使用reset_index来创建ID
    # data_competitiveSituation2 = data_competitiveSituation2.reset_index().rename(columns={'index': 'id'})
    # data_competitiveSituation2['id'] = data_competitiveSituation2['id'] + 1


    # In[279]:


    data_competitiveSituation2

    # In[280]:


    # # 表和字段注释
    # table_comment = "重点站点_外部竞争力_竞争现状"
    # column_comments = {
    #     'result': '竞争现状',
    #     'update_time' : '更新日期'
    # }
    # DF= pd.DataFrame([{
    #     'result': json.dumps(data_competitiveSituation, ensure_ascii=False),
    #     'update_time': M
    # }])

    # import_data_with_cursor(
    #     df=DF,
    #     table_name="dp_impsites_competitor_situation",

    #     table_comment=table_comment,
    #     column_comments=column_comments,
    #     append_data=False,
    #     update_columns=True
    # )


    # In[281]:


    table_comment = "重点站点_外部竞争力_竞争现状"
    column_comments = {
        'id': '主键ID',  # 加这一行！
        'siteNum': '重点站编号',
        'tableData': '竞争站JSON数据',
        'month': '更新日期'
    }

    import_data_with_cursor(
        df=data_competitiveSituation2,
        table_name="dp_impsites_competitor_situation_flat",
        primary_keys=['id'],
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### 竞争站点比较维度

    # In[282]:


    state_competitiveSituation.columns

    # In[283]:


    competitorStationCompareDimensions = state_competitiveSituation[['dd_station_id', 'dd_station_name', 'sjg_station_id',
                                                                     'sjg_station_name', 'equip_power', 'electricity_fee', 'electricity_quantity', 'charging_quantity_per_gun', 'power_rate', 'service_fee']].copy()

    # In[284]:


    competitorStationCompareDimensions['power_rate'] = competitorStationCompareDimensions['power_rate'] * 100

    # In[285]:


    competitorStationCompareDimensions['power_rate'] = competitorStationCompareDimensions['power_rate'].round(2)

    # In[286]:


    competitorStationCompareDimensions['charging_quantity_per_gun'] = competitorStationCompareDimensions['charging_quantity_per_gun'].round(2)

    # In[287]:


    # 按重点站分组计算功率效能比，并直接在原 DF 中新增列
    competitorStationCompareDimensions['power_efficiency_ratio'] = competitorStationCompareDimensions.groupby('dd_station_id')['power_rate'].transform(
        lambda x: (x - x.mean()) / (x.max() - x.mean())
    )

    # 查看结果
    competitorStationCompareDimensions

    # In[288]:


    competitorStationCompareDimensions = competitorStationCompareDimensions.fillna(0)

    # In[289]:


    competitorStationCompareDimensions['fee_total'] = competitorStationCompareDimensions['service_fee'] + competitorStationCompareDimensions['electricity_fee']

    # In[290]:


    # ✅ 指标映射和单位映射（保持不变）
    indicator_map = {
        'charging_quantity_per_gun': '单枪日均充电量',
        'equip_power': '站点额定功率',
        'power_rate': '功率利用率',
        'fee_total': '站点充电价格',
        'electricity_quantity': '站点充电量',
        'power_efficiency_ratio': '功率效能比'
    }

    unit_map = {
        'charging_quantity_per_gun': 'kWh',
        'equip_power': 'kW',
        'power_rate': '%',
        'fee_total': '元/kWh',
        'electricity_quantity': 'kWh',
        'power_efficiency_ratio': '%'
    }

    data_competitorStationCompareDimensions = []

    # ✅ 分组处理
    for dd_station_id, group in competitorStationCompareDimensions.groupby('dd_station_id'):
        focus_station_name = group['dd_station_name'].iloc[0]

        # ✅ 排除和重点站同名的行（只保留竞争站）
        competitor_names = group[
            group['sjg_station_name'] != focus_station_name
            ]['sjg_station_name'].dropna().unique().tolist()

        site_options = ["全部"] + competitor_names
        indicator_options = list(indicator_map.values())
        bar_chart_data = []

        # ✅ 每个指标处理
        for col, col_name in indicator_map.items():
            radio = col_name
            data_entries = []

            # ✅ 重点站值（仅取自己 vs 自己的记录，避免多条重复）
            focus_value = group[
                (group['dd_station_name'] == focus_station_name) &
                (group['sjg_station_name'] == focus_station_name)
                ][col].mean()
            focus_value = round(focus_value, 2) if pd.notnull(focus_value) else 0

            # ✅ 构造“全部”数据
            axis_data_all = [focus_station_name]
            chart_data_all = [focus_value]

            for comp_name in competitor_names:
                val = group[group['sjg_station_name'] == comp_name][col].mean()
                val = round(val, 2) if pd.notnull(val) else 0

                axis_data_all.append(comp_name)
                chart_data_all.append(val)

            # ✅ 排序（降序）
            combined_all = list(zip(axis_data_all, chart_data_all))
            # combined_all.sort(key=lambda x: x[1], reverse=True)
            combined_all.sort(key=lambda x: x[1])  # ✅ 升序（从小到大）

            sorted_axis_data_all = [x[0] for x in combined_all]
            sorted_chart_data_all = [x[1] for x in combined_all]

            xAxis_avg_all = round(sum(sorted_chart_data_all) / len(sorted_chart_data_all), 2) if sorted_chart_data_all else 0

            # ✅ 添加“全部”记录（只一条）
            data_entries.append({
                'siteValue': '全部',
                'itselfName': focus_station_name,
                'legendName': [col_name],
                'axisData': sorted_axis_data_all,
                'chartData': [sorted_chart_data_all],  # ✅ 二维
                'xAxis': xAxis_avg_all,
                'markLineName': '平均值',
                'yAxisName': unit_map[col]
            })

            # ✅ 每个竞争站 vs 重点站（每个对比图）
            for comp_name in competitor_names:
                comp_val = group[group['sjg_station_name'] == comp_name][col].mean()
                comp_val = round(comp_val, 2) if pd.notnull(comp_val) else 0

                xAxis_avg_pair = round((focus_value + comp_val) / 2, 2)

                data_entries.append({
                    'siteValue': comp_name,
                    'itselfName': focus_station_name,
                    'legendName': [col_name],
                    'axisData': [focus_station_name, comp_name],
                    'chartData': [[focus_value, comp_val]],
                    'xAxis': xAxis_avg_pair,
                    'markLineName': '平均值',
                    'yAxisName': unit_map[col]
                })

            bar_chart_data.append({
                'radio': radio,
                'data': data_entries
            })

        data_competitorStationCompareDimensions.append({
            'siteNum': dd_station_id,
            'siteOptions': site_options,
            'indicatorOptions': indicator_options,
            'barChartData': bar_chart_data
        })

    # In[291]:


    rows = []

    for item in data_competitorStationCompareDimensions:
        rows.append({
            "siteNum": item["siteNum"],
            "siteOptions": json.dumps(item["siteOptions"], ensure_ascii=False),
            "indicatorOptions": json.dumps(item["indicatorOptions"], ensure_ascii=False),
            "barChartData": json.dumps(item["barChartData"], ensure_ascii=False)
        })

    data_competitorStationCompareDimensions2 = pd.DataFrame(rows)

    # In[292]:


    data_competitorStationCompareDimensions2['month'] = M

    # In[293]:


    if 'id' in data_competitorStationCompareDimensions2.columns:
        data_competitorStationCompareDimensions2 = data_competitorStationCompareDimensions2.drop('id', axis=1)

    # 添加自增ID列
    data_competitorStationCompareDimensions2['id'] = range(1, len(data_competitorStationCompareDimensions2) + 1)

    # In[294]:


    data_competitorStationCompareDimensions2[data_competitorStationCompareDimensions2['siteNum'] == '202110111714307']

    # In[295]:


    # # 表和字段注释
    # table_comment = "重点站点_外部竞争力_竞争站点比较维度"
    # column_comments = {
    #     'result': '竞争站点比较维度',
    #     'update_time' : '更新日期'
    # }
    # DF= pd.DataFrame([{
    #     'result': json.dumps(data_competitorStationCompareDimensions, ensure_ascii=False),
    #     'update_time': M
    # }])

    # import_data_with_cursor(
    #     df=DF,
    #     table_name="dp_impsites_competitor_compare",

    #     table_comment=table_comment,
    #     column_comments=column_comments,
    #     append_data=False,
    #     update_columns=True
    # )


    # In[296]:


    table_comment = "重点站点_外部竞争力_竞争站点比较维度"

    column_comments = {
        'id': '主键ID',
        'siteNum': '重点站编号',
        'siteOptions': '对比站点列表（含“全部”）',
        'indicatorOptions': '指标中文名列表',
        'barChartData': '条形图数据（重点站对比所有站的图表结构）',
        'month': '更新日期'  # 可选字段，如你有添加时间的话
    }

    import_data_with_cursor(
        df=data_competitorStationCompareDimensions2,  # 你的 DataFrame，含上述字段
        table_name="dp_impsites_competitor_compare_flat",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### 竞争站电充电量对比

    # In[297]:


    DF_out2 = DF_out[['date', 'station_id', 'station_name', 'electricity_quantity']].copy()

    # In[298]:


    DF_out2['station_id'] = DF_out2['station_id'].astype(str).str.strip()
    DF_number['sjg_station_id'] = DF_number['sjg_station_id'].astype(str).str.strip()

    # In[299]:


    DF_charge = DF_number.merge(
        DF_out2[['date', 'station_id', 'station_name', 'electricity_quantity']],
        left_on=['sjg_station_id', 'sjg_station_name'],
        right_on=['station_id', 'station_name'],
        how='left'
    )

    # In[300]:


    DF_charge = DF_charge[['dd_station_id', 'dd_station_name', 'sjg_station_id',
                           'sjg_station_name', 'date', 'electricity_quantity']]

    # In[301]:


    DF_charge


    # In[302]:


    def add_self_row_empty_quantity(df: pd.DataFrame) -> pd.DataFrame:
        """
        给每个 dd 站和每个月份，补一条“自己 vs 自己”的记录，electricity_quantity 留空。
        """
        df = df.copy()

        # 提取 dd 站点在每个月出现的组合
        base_pairs = df[['dd_station_id', 'dd_station_name', 'date']].drop_duplicates()

        # 构造“自己 vs 自己”的记录
        self_rows = base_pairs.copy()
        self_rows['sjg_station_id'] = self_rows['dd_station_id']
        self_rows['sjg_station_name'] = self_rows['dd_station_name']
        self_rows['electricity_quantity'] = pd.NA  # 或者 0，根据你的前端要求

        # 按原列顺序整理
        self_rows = self_rows[[
            'dd_station_id', 'dd_station_name',
            'sjg_station_id', 'sjg_station_name',
            'date', 'electricity_quantity'
        ]]

        # 合并
        out = pd.concat([self_rows, df], ignore_index=True)

        # 排序：自己 vs 自己 放在每组最前
        out['_is_self'] = (out['dd_station_id'] == out['sjg_station_id']).astype(int)
        out = (
            out.sort_values(['dd_station_id', 'date', '_is_self'], ascending=[True, True, False])
                .drop(columns=['_is_self'])
                .reset_index(drop=True)
        )

        return out


    # In[303]:


    DF_charge_full = add_self_row_empty_quantity(DF_charge)

    # In[304]:


    DF_charge_full.loc[
        DF_charge_full['dd_station_id'] == DF_charge_full['sjg_station_id'],
        'electricity_quantity'
    ] = np.nan

    # In[305]:


    DF_imp2 = DF_imp[['station_no', 'cba_month', 'station_name', 'electricity_quantity']]

    # In[306]:


    print(f"DF_charge_full的列明：{DF_charge_full.columns},DF_imp2的列明：{DF_imp2.columns}")

    # In[307]:


    # --- 1) 构造对照表，作为“自己 vs 自己”的电量来源 ---
    tmp = DF_imp2.rename(columns={
        'station_no': 'sjg_station_id',
        'station_name': 'sjg_station_name',
        'cba_month': 'date'
    }).copy()

    # 确保类型一致
    tmp['sjg_station_id'] = tmp['sjg_station_id'].astype(str).str.strip()
    tmp['sjg_station_name'] = tmp['sjg_station_name'].astype(str).str.strip()
    tmp['date'] = tmp['date'].astype(str).str.strip()

    # 建立多键索引
    tmp = (
        tmp.drop_duplicates(['sjg_station_id', 'sjg_station_name', 'date'], keep='last')
            .set_index(['sjg_station_id', 'sjg_station_name', 'date'])
        [['electricity_quantity']]
    )

    # --- 2) 左连接，**仅补充“自己 vs 自己”**的电量 ---
    res = DF_charge_full.copy()
    res['sjg_station_id'] = res['sjg_station_id'].astype(str).str.strip()
    res['sjg_station_name'] = res['sjg_station_name'].astype(str).str.strip()
    res['date'] = res['date'].astype(str).str.strip()

    # 只提取“自己 vs 自己”的行进行 join
    mask_self = res['dd_station_id'] == res['sjg_station_id']
    res_self = res[mask_self].join(tmp, on=['sjg_station_id', 'sjg_station_name', 'date'], rsuffix='_new')

    # 更新“自己 vs 自己”的电量
    res.loc[mask_self, 'electricity_quantity'] = res_self['electricity_quantity_new'].values

    # 最终结果
    chargeCompare1 = res

    # In[308]:


    chargeCompare1

    # In[309]:


    chargeCompare1

    # In[310]:


    charge_compare_df = chargeCompare1.copy()
    result_list = []

    for station_id, station_group in charge_compare_df.groupby('dd_station_id'):
        focus_name = station_group['dd_station_name'].iloc[0]
        station_group['date'] = station_group['date'].astype(str)
        axis_data = sorted(station_group['date'].unique())

        # 所有竞争站（排除自己）
        competitor_names = [n for n in station_group['sjg_station_name'].dropna().unique()
                            if n != focus_name]

        # 重点站曲线
        focus_rows = station_group[
            (station_group['dd_station_name'] == focus_name) &
            (station_group['sjg_station_name'] == focus_name)
            ]

        focus_values = []
        for month_label in axis_data:
            month_data = focus_rows[focus_rows['date'] == month_label]
            value = month_data['electricity_quantity'].sum()
            focus_values.append(round(float(value), 2))

        # ✅ 添加“全部”曲线：重点站 + 所有竞争站，每个为一条线
        chartData_all = [focus_values]
        legend_all = [focus_name]

        for comp_name in competitor_names:
            comp_rows = station_group[station_group['sjg_station_name'] == comp_name]

            comp_values = []
            for month_label in axis_data:
                month_data = comp_rows[comp_rows['date'] == month_label]
                value = month_data['electricity_quantity'].sum()
                comp_values.append(round(float(value), 2))

            chartData_all.append(comp_values)
            legend_all.append(comp_name)

        line_chart_data_list = []

        # ✅ 加入“全部”站点对比曲线
        line_chart_data_list.append({
            "siteValue": "全部",
            "axisData": axis_data,
            "chartData": chartData_all,
            "legendName": legend_all,
            "yAxisName": "kWh"
        })

        # ✅ 每个竞争站 vs 重点站（单独比）
        for comp_name in competitor_names:
            comp_rows = station_group[station_group['sjg_station_name'] == comp_name]

            comp_values = []
            for month_label in axis_data:
                month_data = comp_rows[comp_rows['date'] == month_label]
                value = month_data['electricity_quantity'].sum()
                comp_values.append(round(float(value), 2))

            line_chart_data_list.append({
                "siteValue": comp_name,
                "axisData": axis_data,
                "chartData": [focus_values, comp_values],
                "legendName": [focus_name, comp_name],
                "yAxisName": "kWh"
            })

        result_list.append({
            "siteNum": station_id,
            "indicatorOptions": ["全部"] + competitor_names,
            "lineChartData": line_chart_data_list
        })

    final_json = {"data": result_list}

    # In[311]:


    flat_rows = []

    for item in final_json["data"]:
        flat_rows.append({
            "siteNum": item.get("siteNum"),
            "indicatorOptions": json.dumps(item.get("indicatorOptions", []), ensure_ascii=False),
            "lineChartData": json.dumps(item.get("lineChartData", []), ensure_ascii=False)  # 不展开
        })

    final_json2 = pd.DataFrame(flat_rows)

    # In[312]:


    final_json2['month'] = M

    # In[313]:


    # 删除现有的NULL id列（如果存在）
    if 'id' in final_json2.columns:
        final_json2 = final_json2.drop('id', axis=1)

    # 添加自增ID列
    final_json2['id'] = range(1, len(final_json2) + 1)

    # In[314]:


    final_json2

    # In[315]:


    # # 表和字段注释
    # table_comment = "重点站点_外部竞争力_竞争站点充电量对比"
    # column_comments = {
    #     'result': '竞争站点充电量对比',
    #     'update_time' : '更新日期'
    # }
    # DF= pd.DataFrame([{
    #     'result': json.dumps(final_json, ensure_ascii=False),
    #     'update_time': M
    # }])

    # import_data_with_cursor(
    #     df=DF,
    #     table_name="dp_impsites_competitor_charging",

    #     table_comment=table_comment,
    #     column_comments=column_comments
    # )


    # In[316]:


    table_comment = "重点站点_外部竞争力_竞争站点充电量对比"

    column_comments = {
        'id': '主键ID',
        'siteNum': '重点站编号',
        'indicatorOptions': '对比站点选项（含“全部”）',
        'lineChartData': '单条折线图数据（重点站 vs 某竞争站）',
        'month': '更新日期'
    }

    import_data_with_cursor(
        df=final_json2,  # 拆好的三列 DataFrame（加了 update_time 的）
        table_name="dp_impsites_competitor_charging_flat",
        table_comment=table_comment,
        column_comments=column_comments
    )


    # ### 竞争画像

    # In[317]:


    def topsis_by_group(df, group_col, label_col, indicator_cols, weights):
        from sklearn.preprocessing import MinMaxScaler
        import numpy as np
        import pandas as pd

        results = []

        for dd_id, group in df.groupby(group_col):
            group = group.reset_index(drop=True)
            label_values = group[label_col]
            data = group[indicator_cols]

            # 如果组内数量太少，跳过或手动处理
            if len(data) < 2:
                continue

            # 归一化
            scaler = MinMaxScaler()
            data_scaled = pd.DataFrame(scaler.fit_transform(data), columns=indicator_cols)

            # 正/负理想解
            ideal_pos = data_scaled.max()
            ideal_neg = data_scaled.min()

            # 距离计算
            dist_pos = np.sqrt(((data_scaled - ideal_pos) ** 2 * weights).sum(axis=1))
            dist_neg = np.sqrt(((data_scaled - ideal_neg) ** 2 * weights).sum(axis=1))

            # 综合得分 & 调整
            score = dist_neg / (dist_pos + dist_neg)
            score_adj = MinMaxScaler((60, 100)).fit_transform(score.values.reshape(-1, 1)).flatten()

            # 排名
            rank = pd.Series(score_adj).rank(ascending=False, method='min').astype(int)

            # 拼接结果
            result = group.copy()
            result['综合得分'] = score
            result['综合得分(调整)'] = score_adj
            result['排名'] = rank
            results.append(result)

        return pd.concat(results, ignore_index=True)


    # In[318]:


    competitorStationCompareDimensions['fee_total_benefit'] = (
        competitorStationCompareDimensions
            .groupby('dd_station_id')['fee_total']
            .transform(lambda s: s.max() - s)
    )

    # 指标列与权重
    indicator_cols = ['fee_total', 'charging_quantity_per_gun', 'power_rate']
    weights = [0.3333, 0.3333, 0.3333]

    # 执行 TOPSIS 分组评分
    competitive_portrait = topsis_by_group(
        df=competitorStationCompareDimensions,
        group_col='dd_station_id',
        label_col='sjg_station_name',
        indicator_cols=indicator_cols,
        weights=weights
    )

    # In[319]:


    competitive_portrait = competitive_portrait.fillna(0)

    # In[320]:


    competitive_portrait.columns

    # In[321]:

    competitive_portrait = competitive_portrait[['dd_station_id', 'dd_station_name', 'sjg_station_id',
                                                 'sjg_station_name', 'charging_quantity_per_gun', 'power_rate', 'fee_total',
                                                 '综合得分(调整)', '排名']]

    # In[322]:


    competitive_portrait

    # In[323]:


    import math

    import math

    radar_columns = ['fee_total', 'charging_quantity_per_gun', 'power_rate']
    radar_names = ['充电价格', '单枪日均充电量', '功率利用率']

    # 计算全局平均值（用于只有1条数据时）
    global_mean_values = competitive_portrait[radar_columns].mean()

    data_competitive_portrait = []

    # 按 dd_station_id 分组，每组为一个重点站
    for dd_id, group in competitive_portrait.groupby('dd_station_id'):
        row = group.iloc[0]  # 当前重点站自己（默认第一行就是自己 vs 自己）

        # 如果只有一条记录，用全局均值作为对比
        compare_row = group[radar_columns].mean() if len(group) > 1 else global_mean_values

        # # 优劣势分析
        # advantages = []
        # disadvantages = []
        # for col, name in zip(radar_columns, radar_names):
        #     diff = row[col] - compare_row[col]
        #     if diff > 0:
        #         advantages.append(name)
        #     elif diff < 0:
        #         disadvantages.append(name)
        # 优劣势分析（对 fee_total_origin 反向判断）
        advantages = []
        disadvantages = []

        for col, name in zip(radar_columns, radar_names):
            diff = row[col] - compare_row[col]

            # 特殊处理：价格越低越好 → 值越小为优势
            if col == 'fee_total':
                if diff < 0:
                    advantages.append(name)
                elif diff > 0:
                    disadvantages.append(name)
            else:
                # 其他指标正常判断：值越大为优势
                if diff > 0:
                    advantages.append(name)
                elif diff < 0:
                    disadvantages.append(name)

        trend_list = [
            {'name': "站点优势", 'content': "，".join(advantages) if advantages else "--"},
            {'name': "站点劣势", 'content': "，".join(disadvantages) if disadvantages else "--"}
        ]

        # 雷达图数据构造（当前重点站 vs 对比平均）
        radarData = [
            {
                'value': [round(row[col], 2) if not pd.isna(row[col]) else 0 for col in radar_columns],
                'name': row['sjg_station_name']
            },
            {
                'value': [round(compare_row[col], 2) if not pd.isna(compare_row[col]) else 0 for col in radar_columns],
                'name': "对比平均"
            }
        ]

        indicator = [{'name': name} for name in radar_names]

        # 当前站的得分、排名
        score = row['综合得分(调整)'] if not pd.isna(row['综合得分(调整)']) else 0
        group_sorted = group.sort_values('综合得分(调整)', ascending=False).reset_index(drop=True)
        rank_total = len(group_sorted)
        try:
            rank = group_sorted[group_sorted['sjg_station_id'] == row['sjg_station_id']].index[0] + 1
        except IndexError:
            rank = None

        illustrate = [
            {'title': "站点综合得分（百分制）", 'value': round(score, 2), 'unit': "分", 'trend': ""},
            {'title': "站点排名", 'value': f"{rank}/{rank_total}" if rank else "--", 'unit': "名", 'trend': ""},
            {'title': "", 'value': "", 'unit': "", 'trend': trend_list}
        ]

        # 汇总结果
        data_competitive_portrait.append({
            'siteNum': dd_id,
            'radarData': radarData,
            'indicator': indicator,
            'illustrate': illustrate
        })

    data_competitive_portrait

    # In[325]:


    import pandas as pd
    import json

    # 假设 data_competitive_portrait 是你原始结构 list[dict]

    rows = []
    for item in data_competitive_portrait:
        rows.append({
            "siteNum": item["siteNum"],
            "radarData": json.dumps(item["radarData"], ensure_ascii=False),
            "indicator": json.dumps(item["indicator"], ensure_ascii=False),
            "illustrate": json.dumps(item["illustrate"], ensure_ascii=False),
        })

    data_competitive_portrait2 = pd.DataFrame(rows)

    # In[326]:


    data_competitive_portrait2['month'] = M

    # In[327]:


    # 删除现有的NULL id列（如果存在）
    if 'id' in data_competitive_portrait2.columns:
        data_competitive_portrait2 = data_competitive_portrait2.drop('id', axis=1)

    # 添加自增ID列
    data_competitive_portrait2['id'] = range(1, len(data_competitive_portrait2) + 1)

    # In[328]:


    data_competitive_portrait2

    # In[329]:


    # # 表和字段注释
    # table_comment = "重点站点_外部竞争力_竞争画像"
    # column_comments = {
    #     'result': '竞争画像',
    #     'update_time' : '更新日期'
    # }
    # DF= pd.DataFrame([{
    #     'result': json.dumps(data_competitive_portrait, ensure_ascii=False),
    #     'update_time': M
    # }])

    # import_data_with_cursor(
    #     df=DF,
    #     table_name="dp_impsites_competitor_profiles",

    #     table_comment=table_comment,
    #     column_comments=column_comments
    # )


    # In[330]:


    table_comment = "重点站点_外部竞争力_竞争画像"

    column_comments = {
        'id': '主键ID',
        'siteNum': '重点站编号',
        'radarData': '雷达图数据（重点站 vs 对比平均）',
        'indicator': '雷达图维度名称（如功率利用率、充电价格）',
        'illustrate': '得分、排名、优势劣势说明',
        'month': '数据更新时间（例如202509）'
    }

    import_data_with_cursor(
        df=data_competitive_portrait2,  # 你构造的 DataFrame，含上述字段
        table_name="dp_impsites_competitor_profiles_flat",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### 竞争画像图表

    # In[ ]:


    # In[ ]:


    # In[331]:


    competitive_score = []

    for dd_id, group in competitive_portrait.groupby('dd_station_id'):
        # ✅ 提取重点站和竞争站
        focus_row = group[group['dd_station_name'] == group['sjg_station_name']]
        comp_rows = group[group['dd_station_name'] != group['sjg_station_name']]

        axis_data = [focus_row['dd_station_name'].iloc[0]] + comp_rows['sjg_station_name'].tolist()
        chart_data = [round(focus_row['综合得分(调整)'].iloc[0], 2)] + \
                     [round(x, 2) for x in comp_rows['综合得分(调整)']]

        # ✅ 做排序，组合起来
        combined = list(zip(axis_data, chart_data))
        # combined_sorted = sorted(combined, key=lambda x: x[1], reverse=True)
        combined_sorted = sorted(combined, key=lambda x: x[1])

        # ✅ 构造排名信息
        ranking_data = []
        for rank, (name, score) in enumerate(combined_sorted, start=1):
            ranking_data.append({
                "siteName": name,
                "score": score,
                "rank": rank
            })

        # ✅ 提取排序后 chart 数据用于柱状图展示
        sorted_axis_data = [x[0] for x in combined_sorted]
        sorted_chart_data = [x[1] for x in combined_sorted]
        average_score = round(np.mean(sorted_chart_data), 2)

        focus_name = focus_row['dd_station_name'].iloc[0]  # ✅ 提前拿到重点站名称

        competitive_score.append({
            "siteNum": dd_id,
            "rankingData": ranking_data,
            "barChartData": {
                "itselfName": focus_name,  # ✅ 改为重点站名称
                "legendName": ["得分"],
                "axisData": sorted_axis_data,
                "chartData": [sorted_chart_data],
                "yAxisName": "分",
                "markLineName": "数据平均值",
                "xAxis": average_score
            }
        })

    # In[332]:


    import pandas as pd

    # 假设 competitive_score 是你已有的 list[dict]
    # competitive_score = [...]

    # 拆成 4 列：siteNum、rankingData、barChartData、（可选）update_time 等
    competitive_score2 = pd.DataFrame([
        {
            'siteNum': item['siteNum'],
            'rankingData': item['rankingData'],  # list[dict]
            'barChartData': item['barChartData'],  # dict
        }
        for item in competitive_score
    ])

    competitive_score2['month'] = M

    # In[333]:


    # 删除现有的NULL id列（如果存在）
    if 'id' in competitive_score2.columns:
        competitive_score2 = competitive_score2.drop('id', axis=1)

    # 添加自增ID列
    competitive_score2['id'] = range(1, len(competitive_score2) + 1)

    # In[334]:


    competitive_score2

    # In[335]:


    # # 表和字段注释
    # table_comment = "重点站点_外部竞争力_竞争画像得分"
    # column_comments = {
    #     'result': '竞争画像得分',
    #     'update_time' : '更新日期'
    # }
    # DF= pd.DataFrame([{
    #     'result': json.dumps(competitive_score, ensure_ascii=False),
    #     'update_time': M
    # }])

    # import_data_with_cursor(
    #     df=DF,
    #     table_name="dp_impsites_competitor_score",

    #     table_comment=table_comment,
    #     column_comments=column_comments,
    #     append_data=False,
    #     update_columns=True
    # )


    # In[336]:


    table_comment = "重点站点_外部竞争力_竞争画像得分"

    column_comments = {
        'id': '主键ID',  # 主键自增
        'siteNum': '重点站编号',
        'rankingData': '站点得分排名JSON数据',
        'barChartData': '柱状图JSON数据',
        'month': '更新时间'
    }

    import_data_with_cursor(
        df=competitive_score2,  # 已拆为四列的 DataFrame
        table_name="dp_impsites_competitor_score_flat",
        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,  # 重建时设置为 False
        update_columns=True  # 同步字段注释
    )

    # In[ ]:




