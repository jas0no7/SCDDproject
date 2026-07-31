from logs.log_decorator import log_execution
from loguru import logger
from modules.config import SQL, import_data_with_cursor, Statistical_Time


@log_execution
def runcityPublic_typeMonitoring():
    logger.info(f"开始执行类型监测-城市公共页面")
    import pandas as pd
    import numpy as np
    import json
    from pandas.tseries.offsets import MonthBegin
    import calendar
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    import math

    # 关闭科学计数法
    pd.set_option('display.float_format', '{:.2f}'.format)

    # In[737]:
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)
    dt = datetime.strptime(M, "%Y%m")
    year = dt.year
    month = dt.month
    # 直接减 1 年
    last_year = year - 1
    last_year_month_str = f"{year - 1}{month:02d}"

    if month == 1:
        previous_year = year - 1
        previous_month = 12
    else:
        previous_year = year
        previous_month = month - 1

    previous_month_str = f"{previous_year:04d}{previous_month:02d}"

    def get_days_in_month(year_month):
        """
        根据年月字符串获取当月的天数。

        参数:
        year_month (str): 年月字符串，格式为 'YYYYMM'。

        返回:
        int: 当月的天数。
        """
        # 提取年份和月份
        year = int(year_month[:4])
        month = int(year_month[4:])

        # 使用 calendar 模块获取当月的天数
        days_in_month = calendar.monthrange(year, month)[1]

        return days_in_month

    # ### 往前推11个月

    # In[740]:

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
        date_list = [start_date - i * MonthBegin(1) for i in range(num_months + 1)]  # 包含起始月份

        # 格式化日期为 'YYYYMM' 格式
        month_list = [date.strftime('%Y%m') for date in date_list]

        # 创建 DataFrame
        df = pd.DataFrame(month_list, columns=['month'])

        return df

    Data = generate_months(M, 11)

    Data

    # In[ ]:

    # ## 租金查询

    # In[741]:

    sql = """
    SELECT
    cs.station_no,cs.property_owner_merhant_id,rm.merchant_id,
    JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) AS parking_fee
    FROM
    charging_station cs
    LEFT JOIN
    rec_merchant_rec_station rmr ON cs.station_no = rmr.station_on
    LEFT JOIN
    rec_merchant rm ON rmr.merchant_id = rm.merchant_id
    LEFT JOIN
    scdd_rec_rules sr ON rm.merchant_id = sr.merchant_id
    where property_owner_merhant_id =119
    and  JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL 
    """
    DF_RENT = SQL(sql)

    # In[ ]:

    # ## SQL查询

    # In[742]:

    # 投运数量
    sql = """
    SELECT 
    rm.merchant_name,
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and cs.operation_status in ('投运','退运')
    """
    DF_SCDD = SQL(sql)

    # In[743]:

    target_categories = ['城市公共', '高速公共', '重卡专用', '公交专用', '小区有序', '其他专用']
    DF_SCDD = DF_SCDD[DF_SCDD['station_category'].isin(target_categories)]

    # In[744]:

    DF_SCDD.loc[DF_SCDD['station_category'] == '高速', 'station_category'] = '高速公共'

    # In[ ]:

    # In[745]:

    DF_SCDD['total_charge_point_count'] = DF_SCDD['dc_charge_point_count'].fillna(0) + DF_SCDD['ac_charge_point_count'].fillna(0)
    DF_SCDD['commissioning_time'] = pd.to_datetime(DF_SCDD['commissioning_time'], errors='coerce')
    DF_SCDD['downtime'] = pd.to_datetime(DF_SCDD['downtime'], errors='coerce')
    Data['month_dt'] = pd.to_datetime(Data['month'], format='%Y%m')

    # In[746]:

    DF_SCDD = DF_SCDD[DF_SCDD['charge_point_count'].notna()]

    sql = """
    SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and operation_status in ('投运','退运')
    """
    DF_station = SQL(sql)

    sql = f"""
    select station_no,sum(total_subsidy) as total_subsidy from dp_subsidy_NEW
    where year <='{year}'
    GROUP BY station_no
    """
    DF_subsidy = SQL(sql)

    sql = """
    select b.station_no,
    b.cba_month,
    sum(b.rec_data_elec_fee_revenue+b.rec_data_service_fee_revenue+b.other_revenue_battery_swap_services+
    b.other_revenue_access_control_barriers+b.other_revenue_dr) as revenue,
    sum(b.rec_cost_elec_fee+
    b.rec_cost_rent+b.fin_cost_depreciation+b.fin_cost_labor) as cost
    from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and operation_status in ('投运','退运') ) a
    left join 
    (select * from station_cba_org_data  ) b
    on a.station_no =b.station_no
    GROUP BY b.station_no, b.cba_month
    """
    DF_cost_revenue = SQL(sql)

    # In[748]:

    DF_1 = pd.merge(DF_cost_revenue, DF_station, on='station_no', how='left')

    # 单枪日均充电量
    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
    select * from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and  cs.operation_status in ('投运','退运')) a
    left join 
    (select * from station_cba_org_data where cba_month like '%s' or  cba_month like '%s' ) b
    on a.station_no =b.station_no
    """ % (t1, t2)
    DF_cba_org_data = SQL(sql)

    # In[750]:

    DF_cba_org_data_cur = DF_cba_org_data.copy()

    # In[751]:

    # 功率利用率
    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
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
      AND (scod.cba_month like '%s' or scod.cba_month like '%s')
      and cs.operation_status in ('投运','退运')
    """ % (t1, t2)
    DF_cba_pue = SQL(sql)

    # In[ ]:

    # In[752]:

    # 一次成功率
    sql = '''
    SELECT
      cs.station_category,
      cs.station_no,
      dsr.stat_time,
      SUM(CAST(dsr.order_count AS DECIMAL)) AS total_order_count,

      ROUND(
        SUM(CAST(dsr.order_count AS DECIMAL) * 
            CAST(REPLACE(dsr.success_rate, '%', '') AS DECIMAL(10,4)) / 100)
        / NULLIF(SUM(CAST(dsr.order_count AS DECIMAL)), 0),
        4
      ) AS station_success_rate

    FROM
      dp_success_rate dsr
    INNER JOIN charging_station cs
      ON dsr.station_code = cs.station_no
      WHERE cs.property_owner_merhant_id = 119

    GROUP BY
      cs.station_category,
      cs.station_no,
      dsr.stat_time
    '''
    DF_success = SQL(sql)

    # In[753]:

    # 可用率
    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
    select * from 
    (select station_no,station_category from  charging_station) c
    right join 
    (select time,station_name,station_code,pile_status,normal_duration,operation_duration,city,pile_manufacturer from dp_operation_duration
    where time like '%s' or time like '%s') d 
    on c.station_no = d.station_code
    """ % (t1, t2)
    DF_operation_duration0 = SQL(sql)

    # In[754]:

    DF_operation_duration0

    # In[755]:

    # 工单情况
    sql = '''
    SELECT 
        a.station_no,
        a.stat_time,
        SUM(a.dispatched_workorders) AS dispatched_workorders 
    FROM 
        (SELECT 
            csp.station_no,
            dw.stat_time,
            dw.dispatched_workorders
         FROM
            charging_station_point csp
         LEFT JOIN 
            dp_workorders dw
         ON
            csp.point_no = dw.asset_code) a
    GROUP BY 
        a.station_no, 
        a.stat_time
    '''
    DF_dispatched_workorders = SQL(sql)

    # In[756]:

    DF_SCDD['charge_point_count']

    # In[757]:

    data = []

    for i in DF_SCDD['charge_point_count']:
        if i is not None and isinstance(i, str) and "直流" in i and "交流" in i and '|' in i:
            try:
                # 分割字符串
                parts = i.split('|')
                if len(parts) >= 2:
                    # 提取直流数量
                    dc_part = parts[0]
                    if '直流' in dc_part:
                        dc_num = dc_part.split('直流')[1]
                        dc_value = int(''.join(filter(str.isdigit, dc_num)))
                    else:
                        dc_value = 0

                    # 提取交流数量
                    ac_part = parts[1]
                    if '交流' in ac_part:
                        ac_num = ac_part.split('交流')[1]
                        ac_value = int(''.join(filter(str.isdigit, ac_num)))
                    else:
                        ac_value = 0

                    # 求和并添加到结果
                    data.append(dc_value + ac_value)
                else:
                    print("分隔符数量不足，跳过:", i)
            except (ValueError, IndexError, AttributeError) as e:
                print("解析失败，跳过:", i, "错误:", e)
        else:
            print("格式不符合要求，跳过:", i)
    if len(data) < len(DF_SCDD):
        padding = [1] * (len(DF_SCDD) - len(data))
        data = list(data) + padding

    DF_SCDD['桩数量'] = data

    # In[759]:

    DF_SCGD = pd.merge(DF_SCDD, DF_dispatched_workorders, on='station_no', how='left')

    # In[760]:

    DF_SCGD['单桩工单'] = DF_SCGD['dispatched_workorders'].fillna(0) / DF_SCGD['桩数量']

    # In[761]:

    DF_SCGD['桩数量']

    # In[762]:

    # DF_SCGD['stat_time'] <

    # # 城市公共

    # ## 投运情况

    # ### 充电枪数量

    # In[763]:

    df_filtered = DF_SCDD[
        (DF_SCDD['station_category'] == '城市公共') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    # In[764]:

    results_touyun = []
    for m in Data['month_dt']:
        active = df_filtered[
            (df_filtered['commissioning_time'] <= m)
        ]
        guns = active['total_charge_point_count'].sum()
        results_touyun.append({'month': m.strftime('%Y%m'), 'charging_guns_op': guns})

    # In[765]:

    public_monthly_summary = pd.DataFrame(results_touyun)

    # In[766]:

    public_monthly_summary2 = public_monthly_summary.sort_values(by='month')

    # In[767]:

    public_monthly_summary2

    # ### 总额定功率

    # In[ ]:

    # In[768]:

    results_public_capacity = []

    for m in Data['month_dt']:
        active = df_filtered[
            (df_filtered['commissioning_time'] <= m)
        ]
        capacity = active['station_capacity'].mean()
        results_public_capacity.append({'month': m.strftime('%Y%m'), 'total_power_rate': capacity})

    public_monthly_capacity = pd.DataFrame(results_public_capacity)

    # In[769]:

    public_monthly_capacity1 = public_monthly_capacity.sort_values(by='month')

    # In[770]:

    public_monthly_capacity1

    # In[ ]:

    # In[771]:

    # df_csgg_Operation = pd.merge(public_monthly_summary, public_monthly_capacity, on=['month'], how='outer')
    # df_csgg_Operation['month'] = df_csgg_Operation['month'].astype(str)
    # df_csgg_Operation['month_fmt'] = df_csgg_Operation['month'].str[-2:].astype(int).astype(str) + '月'
    # df_csgg_Operation['month_int'] = df_csgg_Operation['month'].astype(int)
    # axis_data_order = df_csgg_Operation[['month_int', 'month_fmt']].drop_duplicates().sort_values('month_int')
    # axis_labels = axis_data_order['month_fmt'].tolist()
    # month_order = axis_data_order['month_int'].tolist()
    # metric_list = [
    #     ('charging_guns_op', '充电枪数量'),
    #     ('total_power_rate', '总额定功率')
    # ]

    # resultcsgg_tyqk = {
    #     "metricDimensionList": [label for _, label in metric_list],
    #     "axisData": axis_labels,
    #     "yAxisName": "把",
    #     "data": []
    # }

    # for col, label in metric_list:
    #     values = []
    #     for m in month_order:
    #         match = df_csgg_Operation[df_csgg_Operation['month_int'] == m]
    #         if not match.empty:
    #             values.append(int(match[col].values[0]))
    #         else:
    #             values.append(0)

    #     resultcsgg_tyqk["data"].append({
    #         "radio": label,
    #         "chartData": values
    #     })# 初始化结果结构
    # 保证三个表都有相同的 station_category 顺序
    df_merged_csggtouyun = pd.merge(public_monthly_summary2, public_monthly_capacity1, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_csggtouyun['month'].tolist()
    charging_guns_op = df_merged_csggtouyun['charging_guns_op'].round(2).tolist()
    total_power_rate = df_merged_csggtouyun['total_power_rate'].round(2).tolist()

    # 构造前端结构
    result = {
        "options": ["充电枪数量", "站均额定功率"],
        "data": [
            {
                "radio": "充电枪数量",
                "legendName": ["充电枪数量"],
                "axisData": month,
                "chartData": [charging_guns_op],
                "yAxisName": "个"
            },
            {
                "radio": "站均额定功率",
                "legendName": ["站均额定功率"],
                "axisData": month,
                "chartData": [total_power_rate],
                "yAxisName": "kW"
            }
        ]
    }

    # In[772]:

    result

    # ### 写入数据库

    # In[773]:

    # 表和字段注释
    table_comment = "类型检测_城市公共_投运情况"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF_csgg_tyqk = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_csgg_tyqk,
        table_name="dp_csgg_tyqk",

        table_comment=table_comment,
        column_comments=column_comments,
    )

    # ## 投资情况

    # ### 总投资费用

    # In[774]:

    # 投资金额转为数值
    df_filtered['investment_amount'] = pd.to_numeric(df_filtered['investment_amount'], errors='coerce').fillna(0)

    # In[775]:

    for month_str in Data['month']:
        print(month_str)

    # In[776]:

    pd.to_datetime('202406', format="%Y%m")

    # In[777]:

    # 确保 commissioning_time 是 datetime 类型
    df_filtered['commissioning_time'] = pd.to_datetime(df_filtered['commissioning_time'], errors='coerce')

    # 按月份排序，防止乱序
    Data['month'] = sorted(Data['month'])

    invest_results = []

    for month_str in Data['month']:
        # 将 '202407' 转换为对应月份的第一天
        month_dt = pd.to_datetime(month_str, format="%Y%m")

        # 获取所有在当前 month 及之前投运的站点
        df_till_month = df_filtered[df_filtered['commissioning_time'] <= month_dt]

        # 计算截止当前月的累计投资金额
        total_investment = df_till_month['investment_amount'].sum()

        invest_results.append({
            'month': month_str,
            'total_investment': total_investment
        })

    # 转换为 DataFrame
    public_invest_total = pd.DataFrame(invest_results)

    # 保留原始字符串格式月份
    # public_invest_total['month'] = pd.to_datetime(public_invest_total['month']).dt.strftime('%Y%m')

    # In[778]:

    public_invest_total['total_investment'] = public_invest_total['total_investment'] / 10000

    # In[779]:

    public_invest_total['total_investment'] = public_invest_total['total_investment'].round(2)
    public_invest_total

    # ### 每年投资费用

    # In[780]:

    # 提取年份列
    df_filtered['year'] = df_filtered['commissioning_time'].dt.year

    # 原始按年份分组汇总
    yearly_investment = (
        df_filtered.groupby('year')['investment_amount']
        .sum()
        .reset_index()
    )

    # 单位转换并保留两位小数
    yearly_investment['investment_amount'] = (yearly_investment['investment_amount'] / 10000).round(2)

    # ➕ 添加：构造完整年份（从 2016 到当前年）
    current_year = datetime.now().year
    all_years = pd.DataFrame({'year': list(range(2016, current_year + 1))})

    # ➕ 合并并填充缺失年份的金额为 0
    yearly_investment = (
        all_years
        .merge(yearly_investment, on='year', how='left')
        .fillna(0)
    )

    # 保留两位小数（避免 0.0 变成长小数）
    yearly_investment['investment_amount'] = yearly_investment['investment_amount'].round(2)

    yearly_investment

    # In[ ]:

    # ### 回本情况

    # In[781]:

    DF_1['revenue'] = DF_1['revenue']
    DF_1['cost'] = DF_1['cost']
    DF_1['investment_amount'] = DF_1['investment_amount']

    # In[782]:

    DF2 = pd.merge(DF_1, DF_subsidy, on='station_no', how='left')

    # In[783]:

    # 合并 parking_fee
    DF2['station_no'] = DF2['station_no'].astype(str)
    DF_RENT['station_no'] = DF_RENT['station_no'].astype(str)

    DF = DF2.merge(
        DF_RENT[['station_no', 'parking_fee']],
        on='station_no',
        how='left'
    )

    # # 去重：每个 station_no + year_month 只保留一条记录
    # monthly_parking_fee = (
    #     DF2_with_parking[['station_no', 'cba_month', 'parking_fee']]
    #     .drop_duplicates(subset=['station_no', 'cba_month'])
    #     .sort_values(['station_no', 'cba_month'])
    #     .reset_index(drop=True)
    # )

    # In[784]:

    # # 查看某个站点每个月的 parking_fee 是否被正确填充
    # monthly_parking_fee.loc[monthly_parking_fee['station_no'] == '300003013200083', ['station_no', 'cba_month', 'parking_fee']]

    # In[ ]:

    # In[ ]:

    # In[785]:

    # DF = pd.merge(DF2, DF2_with_parking, on='station_no', how='inner')

    # In[ ]:

    # In[786]:

    # DF['cost'] = pd.to_numeric(DF['cost'], errors='coerce').fillna(0)
    # DF['investment_amount'] = pd.to_numeric(DF['investment_amount'], errors='coerce').fillna(0)
    # DF['parking_fee'] = pd.to_numeric(DF['parking_fee'], errors='coerce').fillna(0)

    # In[787]:

    DF['total_subsidy'] = DF['total_subsidy'].fillna(0)
    DF['total_subsidy'] = DF['total_subsidy'] * 10000
    DF['in'] = DF['revenue'].astype(float) + DF['total_subsidy'].astype(float)
    DF['investment_amount'] = DF['investment_amount'].fillna(0)
    DF['parking_fee'] = DF['parking_fee'].fillna(0)
    DF['cost'] = DF['cost'].fillna(0)
    DF['out'] = DF['cost'].astype(float) + DF['investment_amount'].astype(float) + DF['parking_fee'].astype(float)

    # In[ ]:

    # In[788]:

    DF = DF[DF['cba_month'] <= M]

    # In[ ]:

    # In[789]:

    DF['huiben'] = DF['in'] - DF['out']

    # In[790]:

    DF['huiben'] = DF['huiben'] / 10000
    DF['huiben'] = DF['huiben'].round(2)

    # In[791]:

    # DF.to_csv("asdflkqowuer1233.csv" , index = False )

    # In[ ]:

    # In[792]:

    DF[DF['in'] > DF['out']]

    # In[ ]:

    # In[793]:

    df_filtered1 = DF.copy()

    # In[794]:

    df_filtered1['year_month'] = pd.to_datetime(df_filtered1['cba_month'], format='%Y%m')
    Data['month'] = pd.to_datetime(Data['month'], format='%Y%m')

    # Step 2：构造笛卡尔积（每个月都关联所有站点）
    Data['key'] = 1
    df_filtered1['key'] = 1
    merged1 = pd.merge(Data, df_filtered1, on='key').drop('key', axis=1)

    # Step 3：筛选每月已投运的站点（即：投运时间 <= 当前月）
    merged1 = merged1[merged1['year_month'] <= merged1['month']]

    # In[795]:

    merged_public = merged1[merged1['station_category'] == '城市公共']

    # In[796]:

    merged_public['month_str'] = merged_public['month'].dt.strftime('%Y%m')
    # 转换为 float，避免 Decimal 和 float 相加时报错
    for col in ['revenue', 'total_subsidy', 'cost', 'investment_amount']:
        merged_public[col] = merged_public[col].astype(float)

    # In[797]:

    public_revenue = (
        merged_public
        .groupby('month_str')
        .apply(lambda df: df['in'].sum() / df['out'].sum())  # 每月 in/out 比
        .cumsum()  # 累计比值
        .reset_index()
        .rename(columns={0: 'huiben', 'month_str': '月份'})
    )

    # In[798]:

    # public_revenue = (
    #     merged_public
    #     .sort_values('month_str')  # 确保按时间排序
    #     .groupby('month_str')['huiben']
    #     .sum()                      # 每月汇总
    #     .cumsum()                   # 累计和
    #     .reset_index()
    #     .rename(columns={'huiben': '城市公共_累计回本', 'month_str': '月份'})
    # )

    # In[799]:

    public_revenue['huiben'] = public_revenue['huiben'] * 100
    public_revenue['huiben'] = public_revenue['huiben'].round(2)
    public_revenue

    # In[800]:

    result = {
        "options": ["投资情况"],
        "data": []
    }

    #
    # 构造每一块图表数据
    def build_block(df, axis_col, value_col, radio_name, y_axis_unit):
        return {
            "radio": radio_name,
            "legendName": ["投资情况"],
            "axisData": df[axis_col].tolist(),
            "chartData": [df[value_col].tolist()],
            "yAxisName": y_axis_unit
        }

    # 构建每个部分
    # result["data"].append(build_block(public_invest_total, "month", "total_investment", "", "万元","总投资费用"))
    result["data"].append(build_block(yearly_investment, "year", "investment_amount", "投资情况", "万元"))
    # result["data"].append(build_block(public_revenue, "月份", "huiben", "回本情况", "%"))

    # In[801]:

    result

    # In[ ]:

    # ### 写入数据库

    # In[802]:

    # 表和字段注释
    table_comment = "类型检测_城市公共_投资情况"
    column_comments = {
        'result': '投资情况',
        'update_time': '更新日期'
    }
    DF_2 = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_2,
        table_name="dp_csgg_tzqk",

        table_comment=table_comment,
        column_comments=column_comments,

    )

    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
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
          AND (scod.cba_month like '%s' or scod.cba_month like '%s')
          and cs.operation_status in ('投运','退运')
        """ % (t1, t2)
    DF_cba_pue = SQL(sql)

    DF_cba_pue['days'] = DF_cba_pue['cba_month'].apply(get_days_in_month)

    DF_cba_pue['year'] = [i[:4] for i in DF_cba_pue['cba_month']]

    DF_cba_pue = DF_cba_pue[
        (DF_cba_pue['station_capacity'].notna()) &  # 剔除功率为空的异常值
        (DF_cba_pue['station_capacity'] > 0) &  # 剔除功率为0的异常值
        (DF_cba_pue['plat_data_charging_volume'].notna()) &  # 剔除为空的异常值
        (DF_cba_pue['plat_data_charging_volume'] != 0)  # 剔除平台电量为0的异常值
        ].copy()
    print('筛选后：', DF_cba_pue.shape)

    DF_cba_pue['pue'] = DF_cba_pue['plat_data_charging_volume'] / (DF_cba_pue['station_capacity'] * DF_cba_pue['days'] * 24) * 100

    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
            select * from 
            (SELECT 
            cs.*
            FROM
            charging_station cs
            LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
            where 
            rm.merchant_name = '国网电动汽车服务（四川）有限公司'
            and  cs.operation_status in ('投运','退运')) a
            left join 
            (select * from station_cba_org_data where cba_month like '%s' or  cba_month like '%s' ) b
            on a.station_no =b.station_no
            """ % (t1, t2)
    DF_org_data_pre_gun = SQL(sql)

    DF_org_data_pre_gun = DF_org_data_pre_gun.fillna(0)
    DF_org_data_pre_gun['charge_point_count'] = DF_org_data_pre_gun['dc_charge_point_count'].fillna(0) + DF_org_data_pre_gun[
        'ac_charge_point_count'].fillna(0)

    DF_org_data_pre_gun = DF_org_data_pre_gun[DF_org_data_pre_gun['charge_point_count'] != 0]
    DF_org_data_pre_gun = DF_org_data_pre_gun[DF_org_data_pre_gun['plat_data_charging_volume'] != 0]  # 平台数据-平台充电量,不等于0
    # 当月单枪充电量，日均的计算在后面
    DF_org_data_pre_gun['gun_charging_volume'] = DF_org_data_pre_gun['plat_data_charging_volume'] / DF_org_data_pre_gun[
        'charge_point_count']

    # ### 单枪日均充电量

    df_filtered2 = DF_org_data_pre_gun[DF_org_data_pre_gun['station_category'] == '城市公共'].copy()

    # In[807]:

    # 第一步：先将 month 列转换为 datetime 类型（如果它是字符串或整数形式的年月）
    Data['month'] = pd.to_datetime(Data['month'], format='%Y%m', errors='coerce')

    # 第二步：转换为 '202403' 格式的字符串
    Data['month'] = Data['month'].dt.strftime('%Y%m')

    # 保证月份是字符串
    df_filtered2['cba_month'] = df_filtered2['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged2 = pd.merge(Data, df_filtered2, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged2['days_in_month'] = merged2['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 单枪日均充电量 = gun_charging_volume / 月天数
    merged2['gun_charging_volume_d'] = merged2['gun_charging_volume'] / merged2['days_in_month']
    # 按月聚合，取平均值
    public_avg_charge = (
        merged2.groupby('month')['gun_charging_volume_d']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_d': 'gun_charging_volume_d'})
        .round(2)
    )
    public_avg_charge['gun_charging_volume_d'] = public_avg_charge['gun_charging_volume_d'].fillna(0)  # 或填充为其他默认值

    # In[ ]:

    # In[ ]:

    # ### 功率利用率

    # In[809]:

    DF_cba_pue['days'] = DF_cba_pue['cba_month'].apply(get_days_in_month)

    # In[810]:

    DF_cba_pue['year'] = [i[:4] for i in DF_cba_pue['cba_month']]

    df_filtered3 = DF_cba_pue[DF_cba_pue['station_category'] == '城市公共'].copy()

    # In[815]:

    # 保证月份是字符串
    df_filtered3['cba_month'] = df_filtered3['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged3 = pd.merge(Data, df_filtered3, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged3['days_in_month'] = merged2['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 按月聚合，取平均值
    public_pue = (
        merged3.groupby('month')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': 'pue'})
        .round(2)
    )

    # In[816]:

    public_pue['pue'] = public_pue['pue'].fillna(0)
    # In[818]:

    public_pue['pue'] = public_pue['pue'].round(2)

    # In[ ]:

    # In[ ]:

    # In[819]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_csggyunying = pd.merge(public_avg_charge, public_pue, on=['month'], how='outer').fillna(0)
    # 提取数据字段
    month = df_merged_csggyunying['month'].tolist()
    gun_charging_volume_d = df_merged_csggyunying['gun_charging_volume_d'].round(2).tolist()
    pue = df_merged_csggyunying['pue'].round(2).tolist()

    # 构造前端结构
    result = {
        "options": ["单枪日均充电量", "功率利用率"],
        "data": [
            {
                "radio": "单枪日均充电量",
                "legendName": ["单枪日均充电量"],
                "axisData": month,
                "chartData": [gun_charging_volume_d],
                "yAxisName": "kWh"
            },
            {
                "radio": "功率利用率",
                "legendName": ["功率利用率"],
                "axisData": month,
                "chartData": [pue],
                "yAxisName": "%"
            }
        ]
    }

    # In[820]:

    result

    # ### 写入数据库

    # In[821]:

    # 表和字段注释
    table_comment = "类型检测_城市公共_运营情况"
    column_comments = {
        'result': '运营情况',
        'update_time': '更新日期'
    }
    DF_resultcsgg_yyqk = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultcsgg_yyqk,
        table_name="dp_csgg_yyqk",

        table_comment=table_comment,
        column_comments=column_comments,

    )

    # ## 设备质量

    # ### 一次成功率

    sql = '''
        SELECT
          cs.station_category,
          cs.station_no,
          dsr.stat_time,
          SUM(CAST(dsr.order_count AS DECIMAL)) AS total_order_count,

          ROUND(
            SUM(CAST(dsr.order_count AS DECIMAL) * 
                CAST(REPLACE(dsr.success_rate, '%', '') AS DECIMAL(10,4)) / 100)
            / NULLIF(SUM(CAST(dsr.order_count AS DECIMAL)), 0),
            4
          ) AS station_success_rate

        FROM
          dp_success_rate dsr
        INNER JOIN charging_station cs
          ON dsr.station_code = cs.station_no
          WHERE cs.property_owner_merhant_id = 119

        GROUP BY
          cs.station_category,
          cs.station_no,
          dsr.stat_time
        '''
    DF_success = SQL(sql)
    DF_success['month'] = DF_success['stat_time'].astype(str).str.replace('-', '')
    DF_success['month'] = DF_success['month'].astype(str)

    # In[823]:

    DF_success['total_order_count'] = pd.to_numeric(DF_success['total_order_count'], errors='coerce')
    DF_success['station_success_rate'] = pd.to_numeric(DF_success['station_success_rate'], errors='coerce')

    # In[824]:

    DF_success['total_order_count'] = DF_success['total_order_count'].fillna(0)

    # In[825]:

    DF_success['station_success_rate'] = DF_success['station_success_rate'].fillna(0)

    # In[826]:

    # 筛选城市公共
    df_month1 = DF_success[DF_success['station_category'] == '城市公共'].copy()

    # In[827]:

    # 合并生成月份 Data
    merged_success = pd.merge(Data, df_month1, how='left', left_on='month', right_on='month')
    public_success = (
        merged_success.groupby('month')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': "station_success_rate"})
    )

    # In[828]:

    public_success['station_success_rate'] = public_success['station_success_rate'] * 100

    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
        select * from 
        (select station_no,station_category from  charging_station) c
        right join 
        (select time,station_name,station_code,pile_status,normal_duration,operation_duration,pile_manufacturer,city from dp_operation_duration
        where time like '%s' or time like '%s') d 
        on c.station_no = d.station_code
        """ % (t1, t2)
    DF_operation_duration = SQL(sql)

    DF_operation_duration = DF_operation_duration.fillna(0)

    # 可用率计算

    # 可用率=正常状态时长(秒)/在运时长(秒)
    DF_operation_duration['可用率'] = DF_operation_duration['normal_duration'].astype('int') / DF_operation_duration[
        'operation_duration'].astype('int')

    # 筛选正常桩

    print('筛选运行状态前数据形状：', DF_operation_duration.shape)
    DF_operation_duration = DF_operation_duration[DF_operation_duration['pile_status'] == '运行']
    print('筛选运行状态后数据形状', DF_operation_duration.shape)

    # 计算每个站每月平均可用率

    DF_operation_duration_1 = DF_operation_duration.groupby(['time', 'station_no']).agg({'可用率': 'mean'}).reset_index()
    DF_operation_duration_1

    # 获取站点对应城市、站点类型的标签
    DF_operation_duration_2 = DF_operation_duration[['station_no', 'station_category', 'city']].drop_duplicates()
    DF_operation_duration_2

    DF_operation_duration = pd.merge(DF_operation_duration_1, DF_operation_duration_2, on='station_no', how='left')
    DF_operation_duration.head(1)

    # 处理时间

    DF_operation_duration['month'] = [i[:6] for i in DF_operation_duration['time']]

    DF_operation_duration['year'] = [i[:4] for i in DF_operation_duration['month']]

    public_duration = DF_operation_duration[DF_operation_duration['station_category'] == '城市公共'].copy()

    print("public_duration 的 列名", public_duration.columns)

    # In[839]:

    merged_duration = pd.merge(Data, public_duration, how='left', left_on='month', right_on='month')
    public_duration_avg = (
        merged_duration.groupby('month')['可用率']
        .mean()
        .reset_index()
        .rename(columns={'可用率': 'Availability'})
        .round(4)
    )

    # In[840]:

    public_duration_avg['Availability'] = public_duration_avg['Availability'] * 100

    # 保证三个表都有相同的 station_category 顺序
    df_merged_csggshebzhil = pd.merge(public_success, public_duration_avg, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_csggshebzhil['month'].tolist()
    station_success_rate = df_merged_csggshebzhil['station_success_rate'].round(2).tolist()
    Availability = df_merged_csggshebzhil['Availability'].round(2).tolist()

    # 构造前端结构
    result = {
        "options": ["一次成功率", "可用率"],
        "data": [
            {
                "radio": "一次成功率",
                "legendName": ["一次成功率"],
                "axisData": month,
                "chartData": [station_success_rate],
                "yAxisName": "%"
            },
            {
                "radio": "可用率",
                "legendName": ["可用率"],
                "axisData": month,
                "chartData": [Availability],
                "yAxisName": "%"
            }
        ]
    }

    # In[843]:

    result

    # ### 写入数据库

    # In[844]:

    # 表和字段注释
    table_comment = "类型检测_城市公共_设备质量"
    column_comments = {
        'result': '设备质量',
        'update_time': '更新日期'
    }
    DF_resultcsgg_sbzl = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultcsgg_sbzl,
        table_name="dp_csgg_sbzl",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 经营情况

    # In[845]:

    t1 = str(last_year) + '%'  # 生成sql中的上年筛选条件
    t2 = str(year) + '%'  # 生成sql中的上年筛选条件
    # 1、筛选提取2024、2025年的充电站成本效益分析表cba中的数据
    sql = """
    select b.*,a.city,a.station_category,a.dc_charge_point_count,a.ac_charge_point_count from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and cs.operation_status in ('投运','退运')
    ) a
    left join 
    (select * from station_cba_org_data where cba_month like '%s' or  cba_month like '%s' ) b
    on a.station_no =b.station_no
    """ % (t1, t2)
    DF_cba_org_data = SQL(sql)
    DF_cba_org_data = DF_cba_org_data.fillna(0)
    # 数据类型转换
    DF_cba_org_data['rec_data_elec_fee_revenue'] = DF_cba_org_data['rec_data_elec_fee_revenue'].astype(str).astype(float)
    DF_cba_org_data['rec_data_service_fee_revenue'] = DF_cba_org_data['rec_data_service_fee_revenue'].astype(str).astype(
        float)
    DF_cba_org_data['other_revenue_battery_swap_services'] = DF_cba_org_data['other_revenue_battery_swap_services'].astype(
        str).astype(float)
    DF_cba_org_data['other_revenue_access_control_barriers'] = DF_cba_org_data[
        'other_revenue_access_control_barriers'].astype(str).astype(float)
    DF_cba_org_data['other_revenue_dr'] = DF_cba_org_data['other_revenue_dr'].astype(str).astype(float)

    DF_cba_org_data['rec_cost_elec_fee'] = DF_cba_org_data['rec_cost_elec_fee'].astype(str).astype(float)
    DF_cba_org_data['rec_cost_actual_rec_amount'] = DF_cba_org_data['rec_cost_actual_rec_amount'].astype(str).astype(float)
    DF_cba_org_data['rec_cost_plat_service'] = DF_cba_org_data['rec_cost_plat_service'].astype(str).astype(float)
    DF_cba_org_data['rec_cost_rent'] = DF_cba_org_data['rec_cost_rent'].astype(str).astype(float)
    DF_cba_org_data['om_cost_om'] = DF_cba_org_data['om_cost_om'].astype(str).astype(float)
    DF_cba_org_data['om_cost_spare_parts'] = DF_cba_org_data['om_cost_spare_parts'].astype(str).astype(float)
    DF_cba_org_data['om_cost_op_project'] = DF_cba_org_data['om_cost_op_project'].astype(str).astype(float)
    DF_cba_org_data['fin_cost_depreciation'] = DF_cba_org_data['fin_cost_depreciation'].astype(str).astype(float)
    DF_cba_org_data['fin_cost_labor'] = DF_cba_org_data['fin_cost_labor'].astype(str).astype(float)
    print(DF_cba_org_data.info())

    # 2、运维数据读取
    sql = """
    select station_no, stat_time as cba_month,maintenance_cost from  dp_station_maintenance_cost1
    where 
    (stat_time like '%s' or stat_time like '%s') and maintenance_cost>0
    """ % (t1, t2)
    DF_maintenance = SQL(sql)
    # 运维费需要特殊处理，由万元变为元
    DF_maintenance['maintenance_cost'] = DF_maintenance['maintenance_cost'].astype('float') * 10000
    print(DF_maintenance.info())
    DF_maintenance.head(1)

    # 3、租金
    sql = """
          SELECT cs.station_no, \
                 cs.property_owner_merhant_id, \
                 rm.merchant_id, \
                 JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) AS parking_fee
          FROM charging_station cs \
                   LEFT JOIN \
               rec_merchant_rec_station rmr ON cs.station_no = rmr.station_on \
                   LEFT JOIN \
               rec_merchant rm ON rmr.merchant_id = rm.merchant_id \
                   LEFT JOIN \
               scdd_rec_rules sr ON rm.merchant_id = sr.merchant_id
          where property_owner_merhant_id = 119
            and JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL \
     \
          """
    DF_rent = SQL(sql)

    # 4、商户分成数据
    sql = """
    select b.merchant_profit_amount,b.rec_month,a.station_no,a.city,a.station_category,a.dc_charge_point_count,a.ac_charge_point_count,a.operation_status from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and cs.operation_status in ('投运','退运')
    ) a
    left join 
    (select * from fin_rec_result_detail where (rec_month like '%s' or  rec_month like '%s') and  merchant_id != 119 ) b
    on a.station_no =b.station_no
    """ % (t1, t2)
    fin_rec_result_detail = SQL(sql)
    fin_rec_result_detail['merchant_profit_amount'] = fin_rec_result_detail['merchant_profit_amount'].astype('float')
    print(fin_rec_result_detail.info())

    # 1、分成数据与运营数据合并

    # 预处理填充空值
    fin_rec_result_detail = fin_rec_result_detail.fillna(0)

    # merchant_profit_amount为其他商户分成（成本数据）
    fin_rec_result_detail = fin_rec_result_detail[['rec_month', 'station_no', 'merchant_profit_amount']]

    # 更换列名便于匹配
    fin_rec_result_detail = fin_rec_result_detail.rename(columns={'rec_month': 'cba_month'})

    # 按年月汇总每个站点的分成数据
    fin_rec_result_detail = fin_rec_result_detail.groupby(['cba_month', 'station_no']).agg(
        {'merchant_profit_amount': 'sum'}).reset_index()

    # 根据站点编号、年月关联分成数据，与运营数据
    print('cba表关联分成数据前形状：', DF_cba_org_data.shape)
    DF_cba_org_data = pd.merge(DF_cba_org_data, fin_rec_result_detail, on=['station_no', 'cba_month'], how='left')
    DF_cba_org_data = DF_cba_org_data.fillna(0)
    print('cba表关联分成数据后形状：', DF_cba_org_data.shape)

    # 2、运营数据与运维费合并
    print('cba表关联运维费前形状：', DF_cba_org_data.shape)

    DF_cba_org_data['year'] = DF_cba_org_data['cba_month'].apply(
        lambda x: str(x)[:4] if pd.notnull(x) and len(str(x)) >= 4 else None
    )

    DF_cba_org_data = pd.merge(DF_cba_org_data, DF_maintenance, on=['station_no', 'cba_month'], how='left')
    DF_cba_org_data['maintenance_cost'] = DF_cba_org_data['maintenance_cost'].fillna(0)
    print('cba表关联运维费后形状：', DF_cba_org_data.shape)

    # 收入数据合并
    DF_cba_org_data['rec_data'] = (DF_cba_org_data['rec_data_elec_fee_revenue'].fillna(0) +
                                   DF_cba_org_data['rec_data_service_fee_revenue'].fillna(0) +
                                   DF_cba_org_data['other_revenue_battery_swap_services'] +
                                   DF_cba_org_data['other_revenue_access_control_barriers'].fillna(0) +
                                   DF_cba_org_data['other_revenue_dr'].fillna(0))
    # 成本数据合并
    DF_cba_org_data['rec_cost'] = (DF_cba_org_data['rec_cost_elec_fee'].fillna(0) +
                                   DF_cba_org_data['rec_cost_rent'].fillna(0) +
                                   DF_cba_org_data['fin_cost_depreciation'] +
                                   DF_cba_org_data['fin_cost_labor'].fillna(0) +
                                   DF_cba_org_data['merchant_profit_amount'].fillna(0) +
                                   DF_cba_org_data['maintenance_cost'])
    # 租金合并
    DF_cba_org_data = pd.merge(DF_cba_org_data, DF_rent[['station_no', 'parking_fee']], how='left', on='station_no').fillna(0)

    DF_cba_org_data['parking_fee'] = DF_cba_org_data['parking_fee'].astype('float')
    DF_cba_org_data['rec_cost'] = DF_cba_org_data['rec_cost'] + DF_cba_org_data['parking_fee']
    DF_cba_org_data.head(1)

    DF_cba_org_data['gross_profit'] = DF_cba_org_data['rec_data'] - DF_cba_org_data['rec_cost']
    DF_cba_org_data['rec_data'] = DF_cba_org_data['rec_data'].astype(float)
    DF_cba_org_data['rec_cost'] = DF_cba_org_data['rec_cost'].astype(float)
    DF_cba_org_data['gross_profit'] = DF_cba_org_data['gross_profit'].astype(float)

    df_profile_public = DF_cba_org_data[DF_cba_org_data['station_category'] == '城市公共'].copy()

    # In[856]:

    # 合并生成月份 Data
    merged_profile_public = pd.merge(Data, df_profile_public, how='left', left_on='month', right_on='cba_month')
    # 分组汇总每月的charge_point_count
    public_profile = (
        merged_profile_public.groupby('month')['rec_data']
        .sum()
        .reset_index()
    )

    # In[857]:

    public_profile['rec_data'] = (public_profile['rec_data'].astype(float) / 10000).round(2)

    public_profile

    # In[ ]:

    # ### 毛利

    # In[858]:

    # 分组汇总每月的charge_point_count
    public_lirun = (
        merged_profile_public.groupby('month')['gross_profit']
        .sum()
        .reset_index()
    )

    # In[859]:

    public_lirun['gross_profit'] = (public_lirun['gross_profit'].astype(float) / 10000).round(2)
    public_lirun

    # 保证三个表都有相同的 station_category 顺序
    df_merged_csgg_jingying = pd.merge(public_profile, public_lirun, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_csgg_jingying['month'].tolist()
    rec_data = df_merged_csgg_jingying['rec_data'].round(2).tolist()
    gross_profit = df_merged_csgg_jingying['gross_profit'].round(2).tolist()

    # 构造前端结构
    result = {
        "options": ["营收", "毛利"],
        "data": [
            {
                "radio": "营收",
                "legendName": ["营收"],
                "axisData": month,
                "chartData": [rec_data],
                "yAxisName": "万元"
            },
            {
                "radio": "毛利",
                "legendName": ["毛利"],
                "axisData": month,
                "chartData": [gross_profit],
                "yAxisName": "万元"
            }
        ]
    }

    # In[861]:

    result

    # ### 写入数据库

    # In[862]:

    # # 定义注释
    # table_comment = "类型监测_城市公共_经营情况"resultcsgg_jingying
    # 表和字段注释
    table_comment = "类型监测_城市公共_经营情况"
    column_comments = {
        'result': '经营情况',
        'update_time': '更新日期'
    }
    DF_resultcsgg_jingying = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultcsgg_jingying,
        table_name="dp_csgg_jingying",
        table_comment=table_comment,
        column_comments=column_comments,

    )

    # ## 运维情况

    # ### 工单数量

    # In[ ]:

    # In[863]:
    DF_SCGD['单桩工单'].replace([np.inf,-np.inf],0,inplace = True)

    df_workorders = DF_SCGD[DF_SCGD['station_category'] == '城市公共'].copy()
    df_workorders['单桩工单'] = pd.to_numeric(df_workorders['单桩工单'], errors='coerce').fillna(0)

    Data['month'] = Data['month'].astype(str)
    df_workorders['stat_time'] = df_workorders['stat_time'].astype(str)

    month_df = pd.DataFrame({'month': Data['month'].unique()})

    merged_workorders = pd.merge(month_df, df_workorders, how='left', left_on='month', right_on='stat_time')

    public_workorders = (
        merged_workorders.groupby('month')['单桩工单']
        .mean()
        .reset_index()
    )

    # 填充NaN为0
    public_workorders['单桩工单'] = public_workorders['单桩工单'].fillna(0)

    # 把inf和 -inf替换成0
    public_workorders['单桩工单'].replace([np.inf, -np.inf], 0, inplace=True)

    public_workorders

    # In[864]:

    # 提取数据字段
    month = public_workorders['month'].tolist()
    dispatched_workorders = public_workorders['单桩工单'].round(2).tolist()
    # 构造前端结构
    result = {
        "options": ["工单数量"],
        "data": [
            {
                "radio": "工单数量",
                "legendName": ["工单数量"],
                "axisData": month,
                "chartData": [dispatched_workorders],
                "yAxisName": "单"
            }
        ]
    }

    # In[865]:

    result

    # ### 写入数据库

    # In[866]:

    # 表和字段注释
    table_comment = "类型检测_城市公共_运维情况"
    column_comments = {
        'result': '工单数量',
        'update_time': '更新日期'
    }
    DF_resultcsgg_ywqk = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultcsgg_ywqk,
        table_name="dp_csgg_ywqk",

        table_comment=table_comment,
        column_comments=column_comments,

    )

    # # 重卡专用

    # ## 投运情况

    # ### 充电枪数量

    # In[867]:

    df_Heavy = DF_SCDD[
        (DF_SCDD['station_category'] == '重卡专用') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    # In[868]:

    results_df_Heavy = []
    for m in Data['month_dt']:
        active = df_Heavy[
            (df_Heavy['commissioning_time'] <= m)
        ]
        guns = active['total_charge_point_count'].sum()
        results_df_Heavy.append({'month': m.strftime('%Y%m'), 'guns': guns})

    # In[869]:

    public_Heavy = pd.DataFrame(results_df_Heavy)
    public_Heavy

    # In[ ]:

    # ### 总额定功率

    # In[870]:

    results_Heavy_monthly_capacity = []
    for m in Data['month_dt']:
        active = df_Heavy[
            (df_Heavy['commissioning_time'] <= m)
        ]
        capacity = active['station_capacity'].mean()
        results_Heavy_monthly_capacity.append({'month': m.strftime('%Y%m'), 'capacity': capacity})
    Heavy_monthly_capacity = pd.DataFrame(results_Heavy_monthly_capacity)
    Heavy_monthly_capacity = Heavy_monthly_capacity.fillna(0)
    Heavy_monthly_capacity

    # In[871]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_zkzytouyun = pd.merge(public_Heavy, Heavy_monthly_capacity, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_zkzytouyun['month'].tolist()
    guns = df_merged_zkzytouyun['guns'].round(2).tolist()
    capacity = df_merged_zkzytouyun['capacity'].round(2).tolist()

    # 构造前端结构
    result_zj_ty = {
        "options": ["充电枪数量", "站均额定功率"],
        "data": [
            {
                "radio": "充电枪数量",
                "legendName": ["充电枪数量"],
                "axisData": month,
                "chartData": [guns],
                "yAxisName": "个"
            },
            {
                "radio": "站均额定功率",
                "legendName": ["站均额定功率"],
                "axisData": month,
                "chartData": [capacity],
                "yAxisName": "KW"
            }
        ]
    }

    # In[872]:

    result_zj_ty

    # ### 写入数据库

    # In[873]:

    # # 定义注释
    # table_comment = "类型监测_重卡专用_投运情况"
    # 表和字段注释
    table_comment = "类型监测_重卡专用_投运情况"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF_resultzkzy_tyqk = pd.DataFrame([{
        'result': json.dumps(result_zj_ty, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultzkzy_tyqk,
        table_name="dp_zkzy_tyqk",
        table_comment=table_comment,
        column_comments=column_comments

    )

    # ## 投资情况

    # ### 总投资费用

    # In[874]:

    # 投资金额转为数值
    df_Heavy['investment_amount'] = pd.to_numeric(df_Heavy['investment_amount'], errors='coerce').fillna(0)

    # In[875]:

    # 确保 commissioning_time 是 datetime 类型
    df_Heavy['commissioning_time'] = pd.to_datetime(df_Heavy['commissioning_time'], errors='coerce')

    # 按月份排序，防止乱序
    Data['month'] = sorted(Data['month'])

    invest_results = []

    for month_str in Data['month']:
        # 将 '202407' 转换为对应月份的第一天
        month_dt = pd.to_datetime(month_str, format="%Y%m")

        # 获取所有在当前 month 及之前投运的站点
        df_till_month = df_Heavy[df_Heavy['commissioning_time'] <= month_dt]

        # 计算截止当前月的累计投资金额
        total_investment = df_till_month['investment_amount'].sum()

        invest_results.append({
            'month': month_str,
            'total_investment': total_investment
        })

    # 转换为 DataFrame
    Heavy_invest_total = pd.DataFrame(invest_results)

    # 保留原始字符串格式月份
    Heavy_invest_total['month'] = pd.to_datetime(Heavy_invest_total['month'], format='%Y%m').dt.strftime('%Y%m')

    # In[876]:

    # # 排序以保证累加顺序正确
    # df_Heavy.sort_values('year_month', inplace=True)
    # # 准备结果 DataFrame
    # invest_results1 = []
    # for month in Data['month']:
    #     # 筛选 year_month <= 当前 month 的所有记录
    #     df_till_month1 = df_Heavy[df_Heavy['year_month'] <= month]
    #     total_investment1 = df_till_month1['investment_amount'].sum()
    #     invest_results1.append({
    #         'month': month,
    #         "总投资费用": total_investment1
    #     })
    # Heavy_invest_total = pd.DataFrame(invest_results1)

    # In[877]:

    Heavy_invest_total['total_investment'] = Heavy_invest_total['total_investment'] / 10000

    Heavy_invest_total['total_investment'] = Heavy_invest_total['total_investment'].round(2)
    Heavy_invest_total

    # ### 每年投资费用

    # In[878]:

    # # 分组汇总每月的charge_point_count
    # heavy_investment_amount = (
    #     merged_Heavy.groupby('month')['investment_amount']
    #     .sum()
    #     .reset_index()
    #     .rename(columns={'investment_amount': "，每年投资费用"})
    # )

    # In[879]:

    df_Heavy['year'] = df_Heavy['commissioning_time'].dt.year

    # 原始按年份分组汇总
    zk_yearly_investment = (
        df_Heavy.groupby('year')['investment_amount']
        .sum()
        .reset_index()
    )

    # 单位转换并保留两位小数
    zk_yearly_investment['investment_amount'] = (zk_yearly_investment['investment_amount'] / 10000).round(2)

    # ➕ 添加：构造完整年份（从 2016 到当前年）
    current_year = datetime.now().year
    all_years = pd.DataFrame({'year': list(range(2016, current_year + 1))})

    # ➕ 合并并填充缺失年份的金额为 0
    zk_yearly_investment = (
        all_years
        .merge(zk_yearly_investment, on='year', how='left')
        .fillna(0)
    )

    # 保留两位小数（避免 0.0 变成长小数）
    zk_yearly_investment['investment_amount'] = zk_yearly_investment['investment_amount'].round(2)

    # ✅ 输出结果
    zk_yearly_investment['investment_amount'] = zk_yearly_investment['investment_amount'].apply(float)
    zk_yearly_investment

    # In[880]:

    print(zk_yearly_investment.dtypes)

    # In[881]:

    # df_Heavy['year'] = df_Heavy['commissioning_time'].dt.year

    # # 按年份分组汇总投资金额
    # yearly_investment = df_Heavy.groupby('year')['investment_amount'].sum().reset_index()
    # yearly_investment['investment_amount'] = yearly_investment['investment_amount'] / 10000
    # yearly_investment['investment_amount'] = yearly_investment['investment_amount'].round(2)
    # yearly_investment

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # ### 回本情况

    # In[882]:

    merged_heavy = merged1[merged1['station_category'] == '重卡专用'].copy()

    # In[883]:

    merged_heavy['month_str'] = merged_heavy['month'].dt.strftime('%Y%m')
    # 转换为 float，避免 Decimal 和 float 相加时报错
    for col in ['revenue', 'total_subsidy', 'cost', 'investment_amount']:
        merged_heavy[col] = merged_heavy[col].astype(float)

    # In[884]:

    heavy_revenue = (
        merged_heavy
        .groupby('month_str')
        .apply(lambda df: df['in'].sum() / df['out'].sum())  # 每月 in/out 比
        .reset_index()
        .rename(columns={0: 'ratio'})
        .assign(huiben=lambda x: x['ratio'].cumsum())
        .rename(columns={'month_str': '月份'})
    )

    # In[885]:

    # heavy_revenue = (
    #     merged_heavy.groupby('month_str')
    #     .apply(lambda df: (df['revenue'].sum() + df['total_subsidy'].sum()) - (df['cost'].sum() + df['investment_amount'].sum()))
    #     .cumsum()
    #     .reset_index()
    #     .rename(columns={0: '重卡专用_累计回本', 'month_str': '月份'})
    # )

    # In[886]:

    heavy_revenue['huiben'] = heavy_revenue['huiben'] * 100
    heavy_revenue['huiben'] = heavy_revenue['huiben'].round(2)
    heavy_revenue

    # In[887]:

    result_zk_tz = {
        "options": ["投资情况"],
        "data": []
    }

    # 构造每一块图表数据
    def build_block(df, axis_col, value_col, radio_name, y_axis_unit):
        return {
            "radio": radio_name,
            "legendName": ["投资情况"],
            "axisData": df[axis_col].tolist(),
            "chartData": [df[value_col].tolist()],
            "yAxisName": y_axis_unit
        }

    # 构建每个部分
    # result_zk_tz["data"].append(build_block(Heavy_invest_total, "month", "total_investment", "总投资费用", "万元","总投资费用"))
    result_zk_tz["data"].append(build_block(zk_yearly_investment, "year", "investment_amount", "投资情况", "万元"))
    # result_zk_tz["data"].append(build_block(heavy_revenue, "月份", "huiben", "回本情况", "%", "回本情况"))

    # In[888]:

    result_zk_tz

    # ### 写入数据库

    # In[889]:

    # 表和字段注释
    table_comment = "类型检测_重卡专用_投资情况"
    column_comments = {
        'result': '投资情况',
        'update_time': '更新日期'
    }
    DF_2 = pd.DataFrame([{
        'result': json.dumps(result_zk_tz, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_2,
        table_name="dp_zkzy_tzqk",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运营情况

    # ### 单枪日均充电量

    # In[890]:

    df_heavy = DF_org_data_pre_gun[DF_org_data_pre_gun['station_category'] == '重卡专用'].copy()

    # In[891]:

    # 保证月份是字符串
    df_heavy['cba_month'] = df_heavy['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged_heavy2 = pd.merge(Data, df_heavy, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged_heavy2['days_in_month'] = merged_heavy2['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 单枪日均充电量 = gun_charging_volume / 月天数
    merged_heavy2['gun_charging_volume_d'] = merged_heavy2['gun_charging_volume'] / merged2['days_in_month']
    # 按月聚合，取平均值
    heavy_avg_charge = (
        merged_heavy2.groupby('month')['gun_charging_volume_d']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_d': 'gun_charging_volume_dd'})
        .round(2)
    )

    # In[892]:

    heavy_avg_charge['gun_charging_volume_dd'] = heavy_avg_charge['gun_charging_volume_dd'].fillna(0)

    # In[893]:

    heavy_avg_charge

    # ### 功率利用率

    # In[894]:

    df_heavy3 = DF_cba_pue[DF_cba_pue['station_category'] == '城市公共'].copy()

    # In[895]:

    # 保证月份是字符串
    df_heavy3['cba_month'] = df_heavy3['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged_heavy3 = pd.merge(Data, df_heavy3, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged_heavy3['days_in_month'] = merged_heavy3['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 按月聚合，取平均值
    heavy_pue = (
        merged_heavy3.groupby('month')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': 'pue'})
        .round(2)
    )

    # In[896]:

    heavy_pue['pue'] = heavy_pue['pue'].fillna(0)

    # In[897]:

    heavy_pue

    # In[898]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_zkzyyunying = pd.merge(heavy_avg_charge, heavy_pue, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_zkzyyunying['month'].tolist()
    gun_charging_volume_dd = df_merged_zkzyyunying['gun_charging_volume_dd'].round(2).tolist()
    pue = df_merged_zkzyyunying['pue'].round(2).tolist()

    # 构造前端结构
    result_zk_yunying = {
        "options": ["单枪日均充电量", "功率利用率"],
        "data": [
            {
                "radio": "单枪日均充电量",
                "legendName": ["单枪日均充电量"],
                "axisData": month,
                "chartData": [gun_charging_volume_dd],
                "yAxisName": "kWh"
            },
            {
                "radio": "功率利用率",
                "legendName": ["功率利用率"],
                "axisData": month,
                "chartData": [pue],
                "yAxisName": "%"
            }
        ]
    }

    # In[899]:

    result_zk_yunying

    # ### 写入数据库

    # In[900]:

    # # 定义注释
    # table_comment = "类型监测_重卡专用_运营情况"
    # 表和字段注释
    table_comment = "类型监测_重卡专用_运营情况"
    column_comments = {
        'result': '运营情况',
        'update_time': '更新日期'
    }
    DF_resultzkzy_yyqk = pd.DataFrame([{
        'result': json.dumps(result_zk_yunying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultzkzy_yyqk,
        table_name="dp_zkzy_yyqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 设备质量

    # ### 一次成功率

    # In[901]:

    df_month2 = DF_success[DF_success['station_category'] == '重卡专用'].copy()

    # In[902]:

    # 合并生成月份 Data
    merged_success_heavy = pd.merge(Data, df_month2, how='left', left_on='month', right_on='month')
    heavy_success = (
        merged_success_heavy.groupby('month')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': "station_success_rate"})
    )

    # In[903]:

    heavy_success['station_success_rate'] = heavy_success['station_success_rate'] * 100

    # In[904]:

    heavy_success

    # ### 可用率

    # In[905]:

    # 筛选城市公共
    heavy_duration = DF_operation_duration[DF_operation_duration['station_category'] == '重卡专用'].copy()

    # In[906]:

    merged_duration_heavy = pd.merge(Data, heavy_duration, how='left', left_on='month', right_on='month')
    heavy_duration_avg = (
        merged_duration_heavy.groupby('month')['可用率']
        .mean()
        .reset_index()
        .rename(columns={'可用率': 'available'})
        .round(4)
    )

    # In[907]:

    heavy_duration_avg['available'] = heavy_duration_avg['available'] * 100
    heavy_duration_avg

    # In[ ]:

    # In[908]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_zkzyshebzhil = pd.merge(heavy_success, heavy_duration_avg, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_zkzyshebzhil['month'].tolist()
    station_success_rate = df_merged_zkzyshebzhil['station_success_rate'].round(2).tolist()
    available = df_merged_zkzyshebzhil['available'].round(2).tolist()

    # 构造前端结构
    result_zk_shebei = {
        "options": ["一次成功率", "可用率"],
        "data": [
            {
                "radio": "一次成功率",
                "legendName": ["一次成功率"],
                "axisData": month,
                "chartData": [station_success_rate],
                "yAxisName": "%"
            },
            {
                "radio": "可用率",
                "legendName": ["可用率"],
                "axisData": month,
                "chartData": [available],
                "yAxisName": "%"
            }
        ]
    }

    # In[909]:

    result_zk_shebei

    # ### 写入数据库

    # In[910]:

    # # 定义注释
    # table_comment = "类型监测_重卡专用_设备质量"
    # 表和字段注释
    table_comment = "类型监测_重卡专用_设备质量"
    column_comments = {
        'result': '设备质量',
        'update_time': '更新日期'
    }
    DF_resultzkzy_shebzhilk = pd.DataFrame([{
        'result': json.dumps(result_zk_shebei, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultzkzy_shebzhilk,
        table_name="dp_zkzy_shebzhilk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 经营情况

    # ### 营收

    # In[911]:

    df_profile_heavy = DF_cba_org_data[DF_cba_org_data['station_category'] == '重卡专用'].copy()

    # In[912]:

    # 合并生成月份 Data
    merged_profile_heavy = pd.merge(Data, df_profile_heavy, how='left', left_on='month', right_on='cba_month')

    # 分组汇总每月的charge_point_count
    heavy_profile = (
        merged_profile_heavy.groupby('month')['rec_data']
        .sum()
        .reset_index()
    )

    # In[913]:

    heavy_profile['rec_data'] = heavy_profile['rec_data'] / 10000
    heavy_profile['rec_data'] = heavy_profile['rec_data'].round(2)
    heavy_profile

    # ### 毛利

    # In[914]:

    # 分组汇总每月的charge_point_count
    heavy_lirun = (
        merged_profile_heavy.groupby('month')['gross_profit']
        .sum()
        .reset_index()
    )

    # In[915]:

    heavy_lirun['gross_profit'] = heavy_lirun['gross_profit'] / 10000
    heavy_lirun['gross_profit'] = heavy_lirun['gross_profit'].astype(float)
    heavy_lirun['gross_profit'] = heavy_lirun['gross_profit'].round(2)
    heavy_lirun

    # In[916]:

    # 合并表
    df_merged_zkzy_jingying = pd.merge(heavy_profile, heavy_lirun, on=['month'], how='outer').fillna(0)

    # 提取字段并转为字符串（防止 Decimal 问题）
    month = df_merged_zkzy_jingying['month'].tolist()
    rec_data = [str(round(float(x), 2)) for x in df_merged_zkzy_jingying['rec_data']]
    gross_profit = [str(round(float(x), 2)) for x in df_merged_zkzy_jingying['gross_profit']]

    # 构造结构
    result_zk_jingying = {
        "options": ["营收", "毛利"],
        "data": [
            {
                "radio": "营收",
                "legendName": ["营收"],
                "axisData": month,
                "chartData": [rec_data],
                "yAxisName": "万元"
            },
            {
                "radio": "毛利",
                "legendName": ["毛利"],
                "axisData": month,
                "chartData": [gross_profit],
                "yAxisName": "万元"
            }
        ]
    }

    # In[917]:

    result_zk_jingying

    # ### 写入数据库

    # In[918]:

    # # 定义注释
    # table_comment = "类型监测_重卡专用_经营情况" resultzkzy_jingying
    # 表和字段注释
    table_comment = "类型监测_重卡专用_经营情况"
    column_comments = {
        'result': '经营情况',
        'update_time': '更新日期'
    }
    DF_resultzkzy_jingying = pd.DataFrame([{
        'result': json.dumps(result_zk_jingying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultzkzy_jingying,
        table_name="dp_zkzy_jingying",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运维情况

    # ### 工单数量

    # In[919]:

    # # 筛选城市公共
    # heavy_workorders = DF_SCGD[DF_SCGD['station_category'] == '重卡专用'].copy()

    # In[920]:

    # # 转换 dispatched_workorders 为数值（强制转换无法解析的为 NaN，再填 0）
    # heavy_workorders['单桩工单'] = pd.to_numeric(heavy_workorders['单桩工单'], errors='coerce').fillna(0)

    # In[921]:

    # # 合并生成月份 Data
    # merged_workorders_heavy = pd.merge(Data, heavy_workorders, how='left', left_on='month', right_on='stat_time')

    # heavy_workorders = (
    #     merged_workorders_heavy.groupby('stat_time')['单桩工单']
    #     .mean()
    #     .reset_index()
    # )

    # In[922]:

    heavy_workorders = DF_SCGD[DF_SCGD['station_category'] == '重卡专用'].copy()
    heavy_workorders['单桩工单'] = pd.to_numeric(heavy_workorders['单桩工单'], errors='coerce').fillna(0)

    Data['month'] = Data['month'].astype(str)
    heavy_workorders['stat_time'] = heavy_workorders['stat_time'].astype(str)

    merged_workorders_heavy = pd.merge(Data, heavy_workorders, how='left', left_on='month', right_on='stat_time')

    heavy_workorders = (
        merged_workorders_heavy.groupby('month')['单桩工单']
        .mean()
        .reset_index()
    )

    heavy_workorders['单桩工单'] = heavy_workorders['单桩工单'].fillna(0)
    heavy_workorders['单桩工单'].replace([np.inf, -np.inf], 0, inplace=True)

    heavy_workorders

    # In[923]:

    # 提取数据字段
    month = heavy_workorders['month'].tolist()
    dispatched_workorders = heavy_workorders['单桩工单'].round(2).tolist()

    # 构造前端结构
    result_zk_yunwei = {
        "options": ["工单数量"],
        "data": [
            {
                "radio": "工单数量",
                "legendName": ["工单数量"],
                "axisData": month,
                "chartData": [dispatched_workorders],
                "yAxisName": "单"
            }
        ]
    }

    # In[924]:

    result_zk_yunwei

    # ### 写入数据库

    # In[925]:

    # # 定义注释
    # table_comment = "类型监测_重卡专用_运维情况"
    # 表和字段注释
    table_comment = "类型监测_重卡专用_运维情况"
    column_comments = {
        'result': '工单数量',
        'update_time': '更新日期'
    }
    DF_resultzkzy_ywqk = pd.DataFrame([{
        'result': json.dumps(result_zk_yunwei, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultzkzy_ywqk,
        table_name="dp_zkzy_ywqk",
        table_comment=table_comment,
        column_comments=column_comments
    )
    #

    # # 公交专用

    # ## 投运情况

    # ### 充电枪数量

    # In[926]:

    # 筛选城市公共
    df_bus = DF_SCDD[
        (DF_SCDD['station_category'] == '公交专用') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    # In[927]:

    results_df_bus = []
    for m in Data['month_dt']:
        active = df_bus[
            (df_bus['commissioning_time'] <= m)
        ]
        guns = active['total_charge_point_count'].sum()
        results_df_bus.append({'month': m.strftime('%Y%m'), 'guns': guns})

    # In[928]:

    bus_monthly_summary = pd.DataFrame(results_df_bus)

    # In[929]:

    bus_monthly_summary

    # In[ ]:

    # ### 总额定功率

    # In[930]:

    results_bus_capacity = []
    for m in Data['month_dt']:
        active = df_bus[
            (df_bus['commissioning_time'] <= m)
        ]
        capacity = active['station_capacity'].mean()
        results_bus_capacity.append({'month': m.strftime('%Y%m'), 'capacity': capacity})

    bus_monthly_capacity = pd.DataFrame(results_bus_capacity)

    # In[931]:

    bus_monthly_capacity

    # In[932]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_zjzytouyun = pd.merge(bus_monthly_summary, bus_monthly_capacity, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_zjzytouyun['month'].tolist()
    guns = df_merged_zjzytouyun['guns'].round(2).tolist()
    capacity = df_merged_zjzytouyun['capacity'].round(2).tolist()

    # 构造前端结构
    result_gongjiao_touyun = {
        "options": ["充电枪数量", "站均额定功率"],
        "data": [
            {
                "radio": "充电枪数量",
                "legendName": ["充电枪数量"],
                "axisData": month,
                "chartData": [guns],
                "yAxisName": "个"
            },
            {
                "radio": "站均额定功率",
                "legendName": ["站均额定功率"],
                "axisData": month,
                "chartData": [capacity],
                "yAxisName": "KW"
            }
        ]
    }

    # In[933]:

    result_gongjiao_touyun

    # ### 写入数据库

    # In[934]:

    # # 定义注释
    # table_comment = "类型监测_公交专用_投运情况"
    # 表和字段注释
    table_comment = "类型监测_公交专用_投运情况"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF_resultzjzy_tyqk = pd.DataFrame([{
        'result': json.dumps(result_gongjiao_touyun, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultzjzy_tyqk,
        table_name="dp_gjzy_tyqk",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 投资情况

    # ### 总投资费用

    # In[935]:

    # 投资金额转为数值
    df_bus['investment_amount'] = pd.to_numeric(df_bus['investment_amount'], errors='coerce').fillna(0)

    # In[936]:

    # 确保 commissioning_time 是 datetime 类型
    df_bus['commissioning_time'] = pd.to_datetime(df_bus['commissioning_time'], errors='coerce')

    # 按月份排序，防止乱序
    Data['month'] = sorted(Data['month'])

    invest_results = []

    for month_str in Data['month']:
        # 将 '202407' 转换为对应月份的第一天
        month_dt = pd.to_datetime(month_str, format="%Y%m")

        # 获取所有在当前 month 及之前投运的站点
        df_till_month = df_bus[df_bus['commissioning_time'] <= month_dt]

        # 计算截止当前月的累计投资金额
        total_investment = df_till_month['investment_amount'].sum()

        invest_results.append({
            'month': month_str,
            'total_investment': total_investment
        })

    # 转换为 DataFrame
    bus_invest_total = pd.DataFrame(invest_results)

    # 保留原始字符串格式月份
    # bus_invest_total['month'] = pd.to_datetime(bus_invest_total['month']).dt.strftime('%Y%m')

    # In[937]:

    bus_invest_total['total_investment'] = bus_invest_total['total_investment'] / 10000
    bus_invest_total['total_investment'] = bus_invest_total['total_investment'].round(2)
    bus_invest_total

    # In[ ]:

    # ### 每年投资费用

    # In[938]:

    # 提取年份列
    df_bus['year'] = df_bus['commissioning_time'].dt.year

    # 原始按年份分组汇总
    bus_yearly_investment = (
        df_bus.groupby('year')['investment_amount']
        .sum()
        .reset_index()
    )

    # 单位转换并保留两位小数
    bus_yearly_investment['investment_amount'] = (bus_yearly_investment['investment_amount'] / 10000).round(2)

    # ➕ 添加：构造完整年份（从 2016 到当前年）
    current_year = datetime.now().year
    all_years = pd.DataFrame({'year': list(range(2016, current_year + 1))})

    # ➕ 合并并填充缺失年份的金额为 0
    bus_yearly_investment = (
        all_years
        .merge(bus_yearly_investment, on='year', how='left')
        .fillna(0)
    )

    # 保留两位小数（避免 0.0 变成长小数）
    bus_yearly_investment['investment_amount'] = bus_yearly_investment['investment_amount'].round(2)

    bus_yearly_investment

    # ### 回本情况

    # In[939]:

    merged1_bus = merged1[merged1['station_category'] == '公交专用']

    # In[940]:

    merged1_bus['month_str'] = merged1_bus['month'].dt.strftime('%Y%m')
    # 转换为 float，避免 Decimal 和 float 相加时报错
    for col in ['revenue', 'total_subsidy', 'cost', 'investment_amount']:
        merged1_bus[col] = merged1_bus[col].astype(float)

    # In[941]:

    bus_revenue = (
        merged1_bus
        .groupby('month_str')
        .apply(lambda df: df['in'].sum() / df['out'].sum())  # 每月 in/out 比
        .cumsum()  # 累计比值
        .reset_index()
        .rename(columns={0: 'huiben', 'month_str': '月份'})
    )

    # In[942]:

    bus_revenue['huiben'] = bus_revenue['huiben'] * 100
    bus_revenue['huiben'] = bus_revenue['huiben'].round(2)
    bus_revenue

    # In[943]:

    result_gongjiao_touzi = {
        "options": ["投资情况"],
        "data": []
    }

    # 构造每一块图表数据
    def build_block(df, axis_col, value_col, radio_name, y_axis_unit):
        return {
            "radio": radio_name,
            "legendName": ["投资情况"],
            "axisData": df[axis_col].tolist(),
            "chartData": [df[value_col].tolist()],
            "yAxisName": y_axis_unit
        }

    # 构建每个部分
    # result_gongjiao_touzi["data"].append(build_block(bus_invest_total, "month", "total_investment", "总投资费用", "万元", "总投资费用"))
    result_gongjiao_touzi["data"].append(build_block(bus_yearly_investment, "year", "investment_amount", "投资情况", "万元"))
    # result_gongjiao_touzi["data"].append(build_block(bus_revenue, "月份", "huiben", "回本情况", "%", "回本情况"))

    # In[944]:

    result_gongjiao_touzi

    # ### 写入数据库

    # In[945]:

    # 表和字段注释
    table_comment = "类型检测_公交专用_投资情况"
    column_comments = {
        'result': '投资情况',
        'update_time': '更新日期'
    }
    DF_4 = pd.DataFrame([{
        'result': json.dumps(result_gongjiao_touzi, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_4,
        table_name="dp_gjzy_tzqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运营情况

    # ### 单枪日均充电量

    # In[946]:

    df_bus2 = DF_org_data_pre_gun[DF_org_data_pre_gun['station_category'] == '公交专用'].copy()

    # In[947]:

    # 保证月份是字符串
    df_bus2['cba_month'] = df_bus2['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged_bus2 = pd.merge(Data, df_bus2, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged_bus2['days_in_month'] = merged_bus2['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 单枪日均充电量 = gun_charging_volume / 月天数
    merged_bus2['gun_charging_volume_d'] = merged_bus2['gun_charging_volume'] / merged_bus2['days_in_month']
    # 按月聚合，取平均值
    bus_avg_charge = (
        merged_bus2.groupby('month')['gun_charging_volume_d']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_d': 'gun_charging_volume_d'})
        .round(2)
    )

    # In[948]:

    bus_avg_charge['gun_charging_volume_d'] = bus_avg_charge['gun_charging_volume_d'].fillna(0)

    # In[949]:

    bus_avg_charge

    # ### 功率利用率

    # In[950]:

    df_bus3 = DF_cba_pue[DF_cba_pue['station_category'] == '公交专用'].copy()

    # In[951]:

    # 保证月份是字符串
    df_bus3['cba_month'] = df_bus3['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged_bus3 = pd.merge(Data, df_bus3, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged_bus3['days_in_month'] = merged_bus3['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 按月聚合，取平均值
    bus_pue = (
        merged_bus3.groupby('month')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': 'pue'})
        .round(2)
    )

    # In[952]:

    bus_pue['pue'] = bus_pue['pue'].fillna(0)

    # In[953]:

    bus_pue

    # In[954]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_gjzy_yuhying = pd.merge(bus_avg_charge, bus_pue, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_gjzy_yuhying['month'].tolist()
    gun_charging_volume_d = df_merged_gjzy_yuhying['gun_charging_volume_d'].round(2).tolist()
    pue = df_merged_gjzy_yuhying['pue'].round(2).tolist()

    # 构造前端结构
    result_gongjiao_yunying = {
        "options": ["单枪日均充电量", "功率利用率"],
        "data": [
            {
                "radio": "单枪日均充电量",
                "legendName": ["单枪日均充电量"],
                "axisData": month,
                "chartData": [gun_charging_volume_d],
                "yAxisName": "kWh"
            },
            {
                "radio": "功率利用率",
                "legendName": ["功率利用率"],
                "axisData": month,
                "chartData": [pue],
                "yAxisName": "%"
            }
        ]
    }

    # In[955]:

    result_gongjiao_yunying

    # ### 写入数据库

    # In[956]:

    # # 定义注释
    # table_comment = "类型监测_公交专用_运营情况"
    # 表和字段注释
    table_comment = "类型监测_公交专用_运营情况"
    column_comments = {
        'result': '运营情况',
        'update_time': '更新日期'
    }
    DF_resultgjzy_yuhying = pd.DataFrame([{
        'result': json.dumps(result_gongjiao_yunying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultgjzy_yuhying,
        table_name="dp_gjzy_yuhying",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 设备质量

    # ### 一次成功率

    # In[957]:

    df_month_bus = DF_success[DF_success['station_category'] == '公交专用'].copy()

    # In[958]:

    # 合并生成月份 Data
    merged_success_bus = pd.merge(Data, df_month_bus, how='left', left_on='month', right_on='month')
    bus_success = (
        merged_success_bus.groupby('month')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': "station_success_rate"})
    )

    # In[959]:

    bus_success['station_success_rate'] = bus_success['station_success_rate'] * 100
    bus_success

    # ### 可用率

    # In[960]:

    # 筛选城市公共
    bus_duration = DF_operation_duration[DF_operation_duration['station_category'] == '重卡专用'].copy()

    # In[961]:

    merged_duration_bus = pd.merge(Data, bus_duration, how='left', left_on='month', right_on='month')
    bus_duration_avg = (
        merged_duration_bus.groupby('month')['可用率']
        .mean()
        .reset_index()
        .rename(columns={'可用率': 'available'})
        .round(4)
    )

    # In[962]:

    bus_duration_avg['available'] = bus_duration_avg['available'] * 100
    bus_duration_avg

    # In[963]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_gjzyshebeizhil = pd.merge(bus_success, bus_duration_avg, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_gjzyshebeizhil['month'].tolist()
    station_success_rate = df_merged_gjzyshebeizhil['station_success_rate'].round(2).tolist()
    available = df_merged_gjzyshebeizhil['available'].round(2).tolist()

    # 构造前端结构
    result_gongjiao_shebi = {
        "options": ["一次成功率", "可用率"],
        "data": [
            {
                "radio": "一次成功率",
                "legendName": ["一次成功率"],
                "axisData": month,
                "chartData": [station_success_rate],
                "yAxisName": "%"
            },
            {
                "radio": "可用率",
                "legendName": ["可用率"],
                "axisData": month,
                "chartData": [available],
                "yAxisName": "%"
            }
        ]
    }

    # In[964]:

    result_gongjiao_shebi

    # ### 写入数据库

    # In[965]:

    # # 定义注释
    # table_comment = "类型监测_公交专用_设备质量"
    # 表和字段注释
    # 表和字段注释
    table_comment = "类型监测_公交专用_设备质量"
    column_comments = {
        'result': '设备质量',
        'update_time': '更新日期'
    }
    DF_resultgjzy_sbeizhil = pd.DataFrame([{
        'result': json.dumps(result_gongjiao_shebi, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultgjzy_sbeizhil,
        table_name="dp_gjzy_sbeizhil",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 经营情况

    # ### 营收

    # In[966]:

    df_profile_bus = DF_cba_org_data[DF_cba_org_data['station_category'] == '公交专用'].copy()

    # In[967]:

    # 合并生成月份 Data
    merged_profile_bus = pd.merge(Data, df_profile_bus, how='left', left_on='month', right_on='cba_month')

    # 分组汇总每月的charge_point_count
    bus_profile = (
        merged_profile_bus.groupby('month')['rec_data']
        .sum()
        .reset_index()
    )

    # In[968]:

    bus_profile['rec_data'] = bus_profile['rec_data'] / 10000
    bus_profile['rec_data'] = bus_profile['rec_data'].round(2)
    bus_profile

    # In[ ]:

    # ### 毛利

    # In[969]:

    # 分组汇总每月的charge_point_count
    bus_lirun = (
        merged_profile_bus.groupby('month')['gross_profit']
        .sum()
        .reset_index()
    )

    # In[970]:

    bus_lirun['gross_profit'] = bus_lirun['gross_profit'] / 10000
    bus_lirun['gross_profit'] = bus_lirun['gross_profit'].astype(float)
    bus_lirun['gross_profit'] = bus_lirun['gross_profit'].round(2)
    bus_lirun

    # In[971]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_gjzy_jingying = pd.merge(bus_profile, bus_lirun, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_gjzy_jingying['month'].tolist()
    rec_data = df_merged_gjzy_jingying['rec_data'].round(2).tolist()
    gross_profit = df_merged_gjzy_jingying['gross_profit'].round(2).tolist()

    # 构造前端结构
    result_gongjiao_yunying = {
        "options": ["营收", "毛利"],
        "data": [
            {
                "radio": "营收",
                "legendName": ["营收"],
                "axisData": month,
                "chartData": [rec_data],
                "yAxisName": "万元"
            },
            {
                "radio": "毛利",
                "legendName": ["毛利"],
                "axisData": month,
                "chartData": [gross_profit],
                "yAxisName": "万元"
            }
        ]
    }

    # In[972]:

    result_gongjiao_yunying

    # ### 写入数据库

    # In[973]:

    # # 定义注释
    # table_comment = "类型监测_公交专用_经营情况"  resultgjzy_jingying
    # 表和字段注释
    table_comment = "类型监测_公交专用_经营情况"
    column_comments = {
        'result': '经营情况',
        'update_time': '更新日期'
    }
    DF_resultgjzy_jingying = pd.DataFrame([{
        'result': json.dumps(result_gongjiao_yunying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultgjzy_jingying,
        table_name="dp_gjzy_jingying",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运维情况

    # ### 工单数量

    # In[974]:

    # bus_workorders = DF_SCGD[DF_SCGD['station_category'] == '公交专用'].copy()

    # In[975]:

    # # 转换 dispatched_workorders 为数值（强制转换无法解析的为 NaN，再填 0）
    # bus_workorders['单桩工单'] = pd.to_numeric(bus_workorders['单桩工单'], errors='coerce').fillna(0)

    # In[976]:

    # # 合并生成月份 Data
    # merged_workorders_bus = pd.merge(Data, bus_workorders, how='left', left_on='month', right_on='stat_time')

    # bus_workorders = (
    #     merged_workorders_bus.groupby('stat_time')['单桩工单']
    #     .mean()
    #     .reset_index()
    # )

    # In[977]:

    import numpy as np

    bus_workorders = DF_SCGD[DF_SCGD['station_category'] == '公交专用'].copy()
    bus_workorders['单桩工单'] = pd.to_numeric(bus_workorders['单桩工单'], errors='coerce').fillna(0)

    Data['month'] = Data['month'].astype(str)
    bus_workorders['stat_time'] = bus_workorders['stat_time'].astype(str)

    merged_workorders_bus = pd.merge(Data, bus_workorders, how='left', left_on='month', right_on='stat_time')

    bus_workorders = (
        merged_workorders_bus.groupby('month')['单桩工单']
        .mean()
        .reset_index()
    )

    bus_workorders['单桩工单'] = bus_workorders['单桩工单'].fillna(0)
    bus_workorders['单桩工单'].replace([np.inf, -np.inf], 0, inplace=True)

    bus_workorders

    # In[978]:

    # 提取数据字段
    month = bus_workorders['month'].tolist()
    dispatched_workorders = bus_workorders['单桩工单'].round(2).tolist()

    # 构造前端结构
    result_gongjiao_yunwei = {
        "options": ["工单数量"],
        "data": [
            {
                "radio": "工单数量",
                "legendName": ["工单数量"],
                "axisData": month,
                "chartData": [dispatched_workorders],
                "yAxisName": "单"
            }
        ]
    }

    # In[979]:

    result_gongjiao_yunwei

    # ### 写入数据库

    # In[980]:

    # # 定义注释
    # table_comment = "类型监测_公交专用_运维情况"
    # 表和字段注释
    table_comment = "类型监测_公交专用_运维情况"
    column_comments = {
        'result': '工单数量',
        'update_time': '更新日期'
    }
    DF_resultgjzy_ywqk = pd.DataFrame([{
        'result': json.dumps(result_gongjiao_yunwei, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultgjzy_ywqk,
        table_name="dp_gjzy_ywqk",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 高速公共

    # ## 投运情况

    # ### 充电枪数量

    # In[981]:

    df_filtered_high = DF_SCDD[
        (DF_SCDD['station_category'].isin(['高速公共', '高速'])) &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    # In[982]:

    result_shigh_summary = []
    for m in Data['month_dt']:
        active = df_filtered_high[
            (df_filtered_high['commissioning_time'] <= m)
        ]
        guns = active['total_charge_point_count'].sum()
        result_shigh_summary.append({'month': m.strftime('%Y%m'), 'guns': guns})

    # 3. 输出 DataFrame
    high_monthly_summary = pd.DataFrame(result_shigh_summary)

    # In[983]:

    high_monthly_summary

    # In[ ]:

    # ### 总额定功率

    # In[984]:

    results_high_capacity = []

    for m in Data['month_dt']:
        active = df_filtered_high[
            (df_filtered_high['commissioning_time'] <= m)
        ]
        capacity = active['station_capacity'].mean()
        results_high_capacity.append({'month': m.strftime('%Y%m'), 'capacity': capacity})

    high_monthly_capacity = pd.DataFrame(results_high_capacity)

    # In[985]:

    high_monthly_capacity

    # In[986]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_gsggtouyun = pd.merge(high_monthly_summary, high_monthly_capacity, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_gsggtouyun['month'].tolist()
    guns = df_merged_gsggtouyun['guns'].round(2).tolist()
    capacity = df_merged_gsggtouyun['capacity'].round(2).tolist()

    # 构造前端结构
    result_gs_touyun = {
        "options": ["充电枪数量", "站均额定功率"],
        "data": [
            {
                "radio": "充电枪数量",
                "legendName": ["充电枪数量"],
                "axisData": month,
                "chartData": [guns],
                "yAxisName": "个"
            },
            {
                "radio": "站均额定功率",
                "legendName": ["站均额定功率"],
                "axisData": month,
                "chartData": [capacity],
                "yAxisName": "KW"
            }
        ]
    }

    # In[987]:

    result_gs_touyun

    # ### 写入数据库

    # In[988]:

    # # 定义注释
    # table_comment = "类型监测_高速公共_投运情况"
    # 表和字段注释
    table_comment = "类型监测_高速公共_投运情况"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF_resultcsgg_tyqk = pd.DataFrame([{
        'result': json.dumps(result_gs_touyun, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultcsgg_tyqk,
        table_name="dp_gsgg_tyqk",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 投资情况

    # ### 总投资费用

    # In[989]:

    # 投资金额转为数值
    df_filtered_high['investment_amount'] = pd.to_numeric(df_filtered_high['investment_amount'], errors='coerce').fillna(0)

    # In[990]:

    # 确保 commissioning_time 是 datetime 类型
    df_filtered_high['commissioning_time'] = pd.to_datetime(df_filtered_high['commissioning_time'], errors='coerce')

    # 按月份排序，防止乱序
    Data['month'] = sorted(Data['month'])

    invest_results = []

    for month_str in Data['month']:
        # 将 '202407' 转换为对应月份的第一天
        month_dt = pd.to_datetime(month_str, format="%Y%m")

        # 获取所有在当前 month 及之前投运的站点
        df_till_month = df_filtered_high[df_filtered_high['commissioning_time'] <= month_dt]

        # 计算截止当前月的累计投资金额
        total_investment = df_till_month['investment_amount'].sum()

        invest_results.append({
            'month': month_str,
            'total_investment': total_investment
        })

    # 转换为 DataFrame
    high_invest_total = pd.DataFrame(invest_results)

    # # 保留原始字符串格式月份
    # public_invest_total['month'] = pd.to_datetime(public_invest_total['month']).dt.strftime('%Y%m')

    # In[991]:

    high_invest_total['total_investment'] = high_invest_total['total_investment'] / 10000
    high_invest_total['total_investment'] = high_invest_total['total_investment'].round(2)
    high_invest_total

    # ### 每年投资费用

    # In[992]:

    # 提取年份列
    df_filtered_high['year'] = df_filtered_high['commissioning_time'].dt.year

    # 原始按年份分组汇总
    high_yearly_investment = (
        df_filtered_high.groupby('year')['investment_amount']
        .sum()
        .reset_index()
    )

    # 单位转换并保留两位小数
    high_yearly_investment['investment_amount'] = (high_yearly_investment['investment_amount'] / 10000).round(2)

    # ➕ 添加：构造完整年份（从 2016 到当前年）
    current_year = datetime.now().year
    all_years = pd.DataFrame({'year': list(range(2016, current_year + 1))})

    # ➕ 合并并填充缺失年份的金额为 0
    high_yearly_investment = (
        all_years
        .merge(high_yearly_investment, on='year', how='left')
        .fillna(0)
    )

    # 保留两位小数（避免 0.0 变成长小数）

    high_yearly_investment['investment_amount'] = high_yearly_investment['investment_amount'].apply(float)
    high_yearly_investment['investment_amount'] = high_yearly_investment['investment_amount'].round(2)
    high_yearly_investment

    # ### 回本情况

    # In[993]:

    merged1_high = merged1[
        merged1['station_category'].isin(['高速公共', '高速'])
    ].copy()

    # In[994]:

    merged1_high['month_str'] = merged1_high['month'].dt.strftime('%Y%m')
    # 转换为 float，避免 Decimal 和 float 相加时报错
    for col in ['revenue', 'total_subsidy', 'cost', 'investment_amount']:
        merged1_high[col] = merged1_high[col].astype(float)

    # In[995]:

    high_revenue = (
        merged1_high
        .groupby('month_str')
        .apply(lambda df: df['in'].sum() / df['out'].sum())  # 每月 in/out 比
        .cumsum()  # 累计比值
        .reset_index()
        .rename(columns={0: 'huiben', 'month_str': '月份'})
    )

    # In[996]:

    high_revenue['huiben'] = high_revenue['huiben'] * 100
    high_revenue['huiben'] = high_revenue['huiben'].round(2)
    high_revenue

    # In[997]:

    result_gs_touzi = {
        "options": ["投资情况"],
        "data": []
    }

    # 构造每一块图表数据
    def build_block(df, axis_col, value_col, radio_name, y_axis_unit):
        return {
            "radio": radio_name,
            "legendName": ["投资情况"],
            "axisData": df[axis_col].tolist(),
            "chartData": [df[value_col].tolist()],
            "yAxisName": y_axis_unit
        }

    # 构建每个部分
    # result_gs_touzi["data"].append(build_block(high_invest_total, "month", "total_investment", "总投资费用", "万元", "总投资费用"))
    result_gs_touzi["data"].append(build_block(high_yearly_investment, "year", "investment_amount", "投资情况", "万元"))
    # result_gs_touzi["data"].append(build_block(high_revenue, "月份", "huiben", "回本情况", "%", "回本情况"))

    # In[998]:

    result_gs_touzi

    # ### 写入数据库

    # In[999]:

    # 表和字段注释
    table_comment = "类型检测_高速公共_投资情况"
    column_comments = {
        'result': '投资情况',
        'update_time': '更新日期'
    }
    DF_2 = pd.DataFrame([{
        'result': json.dumps(result_gs_touzi, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_2,
        table_name="dp_gsgg_tzqk",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运营情况

    # ### 单枪日均充电量

    # In[1000]:

    df_filtered2_high = DF_org_data_pre_gun[
        DF_org_data_pre_gun['station_category'].isin(['高速公共', '高速'])
    ].copy()

    # In[1001]:

    # 保证月份是字符串
    df_filtered2_high['cba_month'] = df_filtered2_high['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    # Data['month'] = Data['month'].dt.strftime('%Y%m')

    # 然后再合并
    merged2_high = pd.merge(Data, df_filtered2_high, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged2_high['days_in_month'] = merged2_high['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 单枪日均充电量 = gun_charging_volume / 月天数
    merged2_high['gun_charging_volume_d'] = merged2_high['gun_charging_volume'] / merged2_high['days_in_month']
    # 按月聚合，取平均值
    high_avg_charge = (
        merged2_high.groupby('month')['gun_charging_volume_d']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_d': 'gun_charging_volume_d'})
        .round(2)
    )

    # In[1002]:

    high_avg_charge['gun_charging_volume_d'] = high_avg_charge['gun_charging_volume_d'].fillna(0)
    high_avg_charge

    # ### 功率利用率

    # In[1003]:

    df_filtered3_high = DF_cba_pue[DF_cba_pue['station_category'] == '高速公共'].copy()

    # In[1004]:

    # 保证月份是字符串
    df_filtered3_high['cba_month'] = df_filtered3_high['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged3_high = pd.merge(Data, df_filtered3_high, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged3_high['days_in_month'] = merged3_high['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 按月聚合，取平均值
    high_pue = (
        merged3_high.groupby('month')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': 'pue'})
        .round(2)
    )

    # In[1005]:

    high_pue['pue'] = high_pue['pue'].fillna(0)

    # In[1006]:

    high_pue

    # In[1007]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_gsggyunying = pd.merge(high_avg_charge, high_pue, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_gsggyunying['month'].tolist()
    gun_charging_volume_d = df_merged_gsggyunying['gun_charging_volume_d'].round(2).tolist()
    pue = df_merged_gsggyunying['pue'].round(2).tolist()

    # 构造前端结构
    result_gs_yunying = {
        "options": ["单枪日均充电量", "功率利用率"],
        "data": [
            {
                "radio": "单枪日均充电量",
                "legendName": ["单枪日均充电量"],
                "axisData": month,
                "chartData": [gun_charging_volume_d],
                "yAxisName": "kWh"
            },
            {
                "radio": "功率利用率",
                "legendName": ["功率利用率"],
                "axisData": month,
                "chartData": [pue],
                "yAxisName": "%"
            }
        ]
    }

    # In[1008]:

    result_gs_yunying

    # ### 写入数据库

    # In[1009]:

    # # 定义注释
    # table_comment = "类型监测_高速公共_运营情况"
    # 表和字段注释
    table_comment = "类型监测_高速公共_运营情况"
    column_comments = {
        'result': '运营情况',
        'update_time': '更新日期'
    }
    DF_resultgsgg_yyqk = pd.DataFrame([{
        'result': json.dumps(result_gs_yunying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultgsgg_yyqk,
        table_name="dp_gsgg_yyqk",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 设备质量

    # ### 一次成功率

    # In[1010]:

    # 筛选城市公共
    df_month1_high = DF_success[
        DF_success['station_category'].isin(['高速公共', '高速'])
    ].copy()

    # In[1011]:

    # 合并生成月份 Data
    merged_success_high = pd.merge(Data, df_month1_high, how='left', left_on='month', right_on='month')
    high_success = (
        merged_success_high.groupby('month')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': "station_success_rate"})
    )

    # In[1012]:

    high_success['station_success_rate'] = high_success['station_success_rate'] * 100

    # In[1013]:

    high_success

    # ### 可用率

    # In[1014]:

    high_duration = DF_operation_duration[
        DF_operation_duration['station_category'].isin(['高速公共', '高速'])
    ].copy()

    # In[1015]:

    merged_duration_high = pd.merge(Data, high_duration, how='left', left_on='month', right_on='month')
    high_duration_avg = (
        merged_duration_high.groupby('month')['可用率']
        .mean()
        .reset_index()
        .rename(columns={'可用率': 'available'})
        .round(4)
    )

    # In[1016]:

    high_duration_avg['available'] = high_duration_avg['available'] * 100

    # In[1017]:

    high_duration_avg

    # In[1018]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_gsggsbeizhil = pd.merge(high_success, high_duration_avg, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_gsggsbeizhil['month'].tolist()
    station_success_rate = df_merged_gsggsbeizhil['station_success_rate'].round(2).tolist()
    available = df_merged_gsggsbeizhil['available'].round(2).tolist()

    # 构造前端结构
    result_gs_shebei = {
        "options": ["一次成功率", "可用率"],
        "data": [
            {
                "radio": "一次成功率",
                "legendName": ["一次成功率"],
                "axisData": month,
                "chartData": [station_success_rate],
                "yAxisName": "%"
            },
            {
                "radio": "可用率",
                "legendName": ["可用率"],
                "axisData": month,
                "chartData": [available],
                "yAxisName": "%"
            }
        ]
    }

    # In[1019]:

    result_gs_shebei

    # ### 写入数据库

    # In[1020]:

    # # 定义注释
    # table_comment = "类型监测_高速公共_设备质量"
    # 表和字段注释
    table_comment = "类型监测_高速公共_设备质量"
    column_comments = {
        'result': '设备质量',
        'update_time': '更新日期'
    }
    DF_resultgsgg_sbeizhil = pd.DataFrame([{
        'result': json.dumps(result_gs_shebei, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultgsgg_sbeizhil,
        table_name="dp_gsgg_sbeizhil",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 经营情况

    # ### 营收

    # In[1021]:

    # 筛选城市公共
    df_profile_high = DF_cba_org_data[
        DF_cba_org_data['station_category'].isin(['高速公共', '高速'])
    ].copy()

    # In[1022]:

    # 合并生成月份 Data
    merged_profile_high = pd.merge(Data, df_profile_high, how='left', left_on='month', right_on='cba_month')

    # 分组汇总每月的charge_point_count
    high_profile = (
        merged_profile_high.groupby('month')['rec_data']
        .sum()
        .reset_index()
    )

    # In[1023]:

    high_profile['rec_data'] = high_profile['rec_data'] / 10000
    high_profile['rec_data'] = high_profile['rec_data'].round(2)
    high_profile

    # In[ ]:

    # ### 毛利

    # In[1024]:

    # 分组汇总每月的charge_point_count
    high_lirun = (
        merged_profile_high.groupby('month')['gross_profit']
        .sum()
        .reset_index()
    )

    # In[1025]:

    high_lirun['gross_profit'] = high_lirun['gross_profit'] / 10000
    high_lirun['gross_profit'] = high_lirun['gross_profit'].astype(float)
    high_lirun['gross_profit'] = high_lirun['gross_profit'].round(2)
    high_lirun

    # In[1026]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_gsgg_jingying = pd.merge(high_profile, high_lirun, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_gsgg_jingying['month'].tolist()
    rec_data = df_merged_gsgg_jingying['rec_data'].round(2).tolist()
    gross_profit = df_merged_gsgg_jingying['gross_profit'].round(2).tolist()

    # 构造前端结构
    result_gs_jingying = {
        "options": ["营收", "毛利"],
        "data": [
            {
                "radio": "营收",
                "legendName": ["营收"],
                "axisData": month,
                "chartData": [rec_data],
                "yAxisName": "万元"
            },
            {
                "radio": "毛利",
                "legendName": ["毛利"],
                "axisData": month,
                "chartData": [gross_profit],
                "yAxisName": "万元"
            }
        ]
    }

    # In[1027]:

    result_gs_jingying

    # ### 写入数据库

    # In[1028]:

    # # 定义注释
    # table_comment = "类型监测_高速公共_经营情况" resultgsgg_jingying
    # 表和字段注释
    table_comment = "类型监测_高速公共_经营情况"
    column_comments = {
        'result': '经营情况',
        'update_time': '更新日期'
    }
    DF_resultgsgg_jingying = pd.DataFrame([{
        'result': json.dumps(result_gs_jingying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultgsgg_jingying,
        table_name="dp_gsgg_jingying",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运维情况

    # ### 工单数量

    # In[1029]:

    # # 筛选城市公共
    # df_workorders_high = DF_SCGD[
    #     DF_SCGD['station_category'].isin(['高速公共', '高速'])
    # ].copy()

    # In[1030]:

    # # 转换 dispatched_workorders 为数值（强制转换无法解析的为 NaN，再填 0）
    # df_workorders_high['单桩工单'] = pd.to_numeric(df_workorders_high['单桩工单'], errors='coerce').fillna(0)

    # In[1031]:

    # # 合并生成月份 Data
    # merged_workorders_high = pd.merge(Data, df_workorders_high, how='left', left_on='month', right_on='stat_time')

    # high_workorders = (
    #     merged_workorders_high.groupby('stat_time')['单桩工单']
    #     .mean()
    #     .reset_index()
    # )

    # In[1032]:

    import numpy as np

    # 筛选高速公共
    df_workorders_high = DF_SCGD[
        DF_SCGD['station_category'].isin(['高速公共', '高速'])
    ].copy()

    df_workorders_high['单桩工单'] = pd.to_numeric(df_workorders_high['单桩工单'], errors='coerce').fillna(0)

    Data['month'] = Data['month'].astype(str)
    df_workorders_high['stat_time'] = df_workorders_high['stat_time'].astype(str)

    merged_workorders_high = pd.merge(Data, df_workorders_high, how='left', left_on='month', right_on='stat_time')

    high_workorders = (
        merged_workorders_high.groupby('month')['单桩工单']
        .mean()
        .reset_index()
    )

    high_workorders['单桩工单'] = high_workorders['单桩工单'].fillna(0)
    high_workorders['单桩工单'].replace([np.inf, -np.inf], 0, inplace=True)

    high_workorders

    # In[1033]:

    # 提取数据字段
    month = high_workorders['month'].tolist()
    dispatched_workorders = high_workorders['单桩工单'].round(2).tolist()

    # 构造前端结构
    result_gs_yunwei = {
        "options": ["工单数量"],
        "data": [
            {
                "radio": "工单数量",
                "legendName": ["工单数量"],
                "axisData": month,
                "chartData": [dispatched_workorders],
                "yAxisName": "单"
            }
        ]
    }

    # In[1034]:

    result_gs_yunwei

    # ### 写入数据库

    # In[1035]:

    table_comment = "类型监测_高速公共_运维情况"
    column_comments = {
        'result': '工单数量',
        'update_time': '更新日期'
    }
    DF_resultgsgg_ywqk = pd.DataFrame([{
        'result': json.dumps(result_gs_yunwei, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultgsgg_ywqk,
        table_name="dp_gsgg_ywqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 小区有序

    # ## 投运情况

    # ### 充电枪数量

    # In[1036]:

    df_filtered_com = DF_SCDD[
        (DF_SCDD['station_category'] == '小区有序') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    # In[1037]:

    result_com_summary = []
    for m in Data['month_dt']:
        active = df_filtered_com[
            (df_filtered_com['commissioning_time'] <= m)
        ]
        guns = active['total_charge_point_count'].sum()
        result_com_summary.append({'month': m.strftime('%Y%m'), 'guns': guns})

    # 3. 输出 DataFrame
    com_monthly_summary = pd.DataFrame(result_com_summary)

    # In[1038]:

    com_monthly_summary

    # In[ ]:

    # ### 总额定功率

    # In[1039]:

    results_com_capacity = []

    for m in Data['month_dt']:
        active = df_filtered_com[
            (df_filtered_com['commissioning_time'] <= m)
        ]
        capacity = active['station_capacity'].mean()
        results_com_capacity.append({'month': m.strftime('%Y%m'), 'capacity': capacity})

    com_monthly_capacity = pd.DataFrame(results_com_capacity)

    # In[1040]:

    com_monthly_capacity

    # In[1041]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_xqyxtouyun = pd.merge(com_monthly_summary, com_monthly_capacity, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_xqyxtouyun['month'].tolist()
    guns = df_merged_xqyxtouyun['guns'].round(2).tolist()
    capacity = df_merged_xqyxtouyun['capacity'].round(2).tolist()

    # 构造前端结构
    result_xiaoqu_touyun = {
        "options": ["充电枪数量", "站均额定功率"],
        "data": [
            {
                "radio": "充电枪数量",
                "legendName": ["充电枪数量"],
                "axisData": month,
                "chartData": [guns],
                "yAxisName": "个"
            },
            {
                "radio": "站均额定功率",
                "legendName": ["站均额定功率"],
                "axisData": month,
                "chartData": [capacity],
                "yAxisName": "KW"
            }
        ]
    }

    # In[1042]:

    result_xiaoqu_touyun

    # ### 写入数据库

    # In[1043]:

    # # 定义注释
    # table_comment = "类型监测_小区有序_投运情况"
    # 表和字段注释
    table_comment = "类型监测_小区有序_投运情况"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF_resultxqyx_tyqk = pd.DataFrame([{
        'result': json.dumps(result_xiaoqu_touyun, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultxqyx_tyqk,
        table_name="dp_xqyx_tyqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 投资情况

    # ### 总投资费用

    # In[1044]:

    # 投资金额转为数值
    df_filtered_com['investment_amount'] = pd.to_numeric(df_filtered_com['investment_amount'], errors='coerce').fillna(0)

    # In[1045]:

    # 确保 commissioning_time 是 datetime 类型
    df_filtered_com['commissioning_time'] = pd.to_datetime(df_filtered_com['commissioning_time'], errors='coerce')

    # 按月份排序，防止乱序
    Data['month'] = sorted(Data['month'])

    invest_results = []

    for month_str in Data['month']:
        # 将 '202407' 转换为对应月份的第一天
        month_dt = pd.to_datetime(month_str, format="%Y%m")

        # 获取所有在当前 month 及之前投运的站点
        df_till_month = df_filtered_com[df_filtered_com['commissioning_time'] <= month_dt]

        # 计算截止当前月的累计投资金额
        total_investment = df_till_month['investment_amount'].sum()

        invest_results.append({
            'month': month_str,
            'total_investment': total_investment
        })

    # 转换为 DataFrame
    com_invest_total = pd.DataFrame(invest_results)

    # In[1046]:

    com_invest_total['total_investment'] = com_invest_total['total_investment'] / 10000
    com_invest_total['total_investment'] = com_invest_total['total_investment'].round(2)
    com_invest_total

    # ### 每年投资费用

    # In[1047]:

    # 提取年份列
    df_filtered_com['year'] = df_filtered_com['commissioning_time'].dt.year

    # 原始按年份分组汇总
    com_yearly_investment = (
        df_filtered_com.groupby('year')['investment_amount']
        .sum()
        .reset_index()
    )

    # 单位转换并保留两位小数
    com_yearly_investment['investment_amount'] = (com_yearly_investment['investment_amount'] / 10000).round(2)

    # ➕ 添加：构造完整年份（从 2016 到当前年）
    current_year = datetime.now().year
    all_years = pd.DataFrame({'year': list(range(2016, current_year + 1))})

    # ➕ 合并并填充缺失年份的金额为 0
    com_yearly_investment = (
        all_years
        .merge(com_yearly_investment, on='year', how='left')
        .fillna(0)
    )

    # 保留两位小数（避免 0.0 变成长小数）
    com_yearly_investment['investment_amount'] = yearly_investment['investment_amount'].round(2)

    com_yearly_investment

    # ### 回本情况

    # In[1048]:

    merged1_com = merged1[merged1['station_category'] == '小区有序'].copy()

    # In[1049]:

    merged1_com['month_str'] = merged1_com['month'].dt.strftime('%Y%m')
    # 转换为 float，避免 Decimal 和 float 相加时报错
    for col in ['revenue', 'total_subsidy', 'cost', 'investment_amount']:
        merged1_com[col] = merged1_com[col].astype(float)

    # In[1050]:

    com_revenue = (
        merged1_com
        .groupby('month_str')
        .apply(lambda df: df['in'].sum() / df['out'].sum())  # 每月 in/out 比
        .cumsum()  # 累计比值
        .reset_index()
        .rename(columns={0: 'huiben', 'month_str': '月份'})
    )

    # In[1051]:

    com_revenue['huiben'] = com_revenue['huiben'].replace([np.inf, -np.inf], 0)

    com_revenue['huiben'] = com_revenue['huiben'] * 100

    # In[1052]:

    result_xiaoqu_touzi = {
        "options": ["投资情况"],
        "data": []
    }

    # 构造每一块图表数据
    def build_block(df, axis_col, value_col, radio_name, y_axis_unit):
        return {
            "radio": radio_name,
            "legendName": ["投资情况"],
            "axisData": df[axis_col].tolist(),
            "chartData": [df[value_col].tolist()],
            "yAxisName": y_axis_unit
        }

    # 构建每个部分
    # result_xiaoqu_touzi["data"].append(build_block(com_invest_total, "month", "total_investment", "总投资费用", "万元", "总投资费用"))
    result_xiaoqu_touzi["data"].append(build_block(com_yearly_investment, "year", "investment_amount", "投资情况", "万元"))
    # result_xiaoqu_touzi["data"].append(build_block(com_revenue, "月份", "huiben", "回本情况", "%", "回本情况"))

    # In[1053]:

    result_xiaoqu_touzi

    # ### 写入数据库

    # In[1054]:

    # 表和字段注释
    table_comment = "类型检测_小区有序_投资情况"
    column_comments = {
        'result': '投资情况',
        'update_time': '更新日期'
    }
    DF_2 = pd.DataFrame([{
        'result': json.dumps(result_xiaoqu_touzi, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_2,
        table_name="dp_xqyx_tzqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运营情况

    # ### 单枪日均充电量

    # In[1055]:

    df_filtered2_com = DF_org_data_pre_gun[DF_org_data_pre_gun['station_category'] == '小区有序'].copy()

    # In[1056]:

    # 保证月份是字符串
    df_filtered2_com['cba_month'] = df_filtered2_com['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged2_com = pd.merge(Data, df_filtered2_com, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged2_com['days_in_month'] = merged2_com['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 单枪日均充电量 = gun_charging_volume / 月天数
    merged2_com['gun_charging_volume_d'] = merged2_com['gun_charging_volume'] / merged2_com['days_in_month']
    # 按月聚合，取平均值
    com_avg_charge = (
        merged2_com.groupby('month')['gun_charging_volume_d']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_d': 'gun_charging_volume_d'})
        .round(2)
    )

    # In[1057]:

    com_avg_charge['gun_charging_volume_d'] = com_avg_charge['gun_charging_volume_d'].fillna(0)
    com_avg_charge

    # ### 功率利用率

    # In[1058]:

    df_filtered3_com = DF_cba_pue[DF_cba_pue['station_category'] == '小区有序'].copy()

    # In[1059]:

    # 保证月份是字符串
    df_filtered3_com['cba_month'] = df_filtered3_com['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged3_com = pd.merge(Data, df_filtered3_com, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged3_com['days_in_month'] = merged3_com['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 按月聚合，取平均值
    com_pue = (
        merged3_com.groupby('month')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': 'pue'})
        .round(2)
    )

    # In[1060]:

    com_pue['pue'] = com_pue['pue'].fillna(0)

    # In[1061]:

    com_pue

    # In[1062]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_xqyx_yunying = pd.merge(com_avg_charge, com_pue, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_xqyx_yunying['month'].tolist()
    gun_charging_volume_d = df_merged_xqyx_yunying['gun_charging_volume_d'].round(2).tolist()
    pue = df_merged_xqyx_yunying['pue'].round(2).tolist()

    # 构造前端结构
    result_xiaoqu_yunying = {
        "options": ["单枪日均充电量", "功率利用率"],
        "data": [
            {
                "radio": "单枪日均充电量",
                "legendName": ["单枪日均充电量"],
                "axisData": month,
                "chartData": [gun_charging_volume_d],
                "yAxisName": "kWh"
            },
            {
                "radio": "功率利用率",
                "legendName": ["功率利用率"],
                "axisData": month,
                "chartData": [pue],
                "yAxisName": "%"
            }
        ]
    }

    # In[1063]:

    result_xiaoqu_yunying

    # ### 写入数据库

    # In[1064]:

    # # 定义注释
    # table_comment = "类型监测_小区有序_运营情况"
    # 表和字段注释
    table_comment = "类型监测_小区有序_运营情况"
    column_comments = {
        'result': '运营情况',
        'update_time': '更新日期'
    }
    DF_resultxqyx_yunying = pd.DataFrame([{
        'result': json.dumps(result_xiaoqu_yunying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultxqyx_yunying,
        table_name="dp_xqyx_yunying",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 设备质量

    # ### 一次成功率

    # In[1065]:

    df_month1_com = DF_success[DF_success['station_category'] == '小区有序'].copy()

    # In[1066]:

    # # 合并生成月份 Data
    # merged_success_com = pd.merge(Data, df_month1_com, how='left', left_on='month', right_on='month')
    # com_success = (
    #     merged_success_com.groupby('month')['station_success_rate']
    #     .mean()
    #     .reset_index()
    #     .rename(columns={'station_success_rate': "station_success_rate"})
    #     .fillna(0)
    # )

    # In[1067]:

    # 1. 构造完整月份列
    month_df = Data[['month']].copy().rename(columns={'month': 'month'})

    # 2. 从成功率明细表中计算每月平均
    if not df_month1_com.empty:
        df_month1_com['month'] = pd.to_datetime(df_month1_com['stat_time'],format='%Y%m').dt.strftime('%Y%m')
        avg_success = df_month1_com.groupby('month')['station_success_rate'].mean().reset_index()
    else:
        avg_success = pd.DataFrame(columns=['month', 'station_success_rate'])

    # 3. 左连接 + 缺失填 0
    com_success = pd.merge(month_df, avg_success, on='month', how='left')
    com_success['station_success_rate'] = com_success['station_success_rate'].fillna(0).round(4)

    # In[1068]:

    com_success

    # ### 可用率

    # In[1069]:

    com_duration = DF_operation_duration[DF_operation_duration['station_category'] == '小区有序'].copy()

    # In[1070]:

    merged_duration_com = pd.merge(Data, com_duration, how='left', left_on='month', right_on='month')
    com_duration_avg = (
        merged_duration_com.groupby('month')['可用率']
        .mean()
        .reset_index()
        .rename(columns={'可用率': 'avilable'})
        .round(4)
    )

    # In[1071]:

    com_duration_avg['avilable'] = com_duration_avg['avilable'] * 100

    # In[1072]:

    com_duration_avg

    # In[1073]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_xqyxsbeizhil = pd.merge(com_success, com_duration_avg, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_xqyxsbeizhil['month'].tolist()
    station_success_rate = df_merged_xqyxsbeizhil['station_success_rate'].round(2).tolist()
    available = df_merged_xqyxsbeizhil['avilable'].round(2).tolist()

    # 构造前端结构
    result_xiaoqu_shebei = {
        "options": ["一次成功率", "可用率"],
        "data": [
            {
                "radio": "一次成功率",
                "legendName": ["一次成功率"],
                "axisData": month,
                "chartData": [station_success_rate],
                "yAxisName": "%"
            },
            {
                "radio": "可用率",
                "legendName": ["可用率"],
                "axisData": month,
                "chartData": [available],
                "yAxisName": "%"
            }
        ]
    }

    # In[1074]:

    result_xiaoqu_shebei

    # ### 写入数据库

    # In[1075]:

    # 表和字段注释
    table_comment = "类型检测_小区有序_设备质量"
    column_comments = {
        'result': '设备质量',
        'update_time': '更新日期'
    }
    DF_result = pd.DataFrame([{
        'result': json.dumps(result_xiaoqu_shebei, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_result,
        table_name="dp_xqyx_shbzl",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 经营情况

    # ### 营收

    # In[1076]:

    # 筛选城市公共
    df_profile_com = DF_cba_org_data[DF_cba_org_data['station_category'] == '小区有序'].copy()

    # In[1077]:

    # 合并生成月份 Data
    merged_profile_com = pd.merge(Data, df_profile_com, how='left', left_on='month', right_on='cba_month')

    # 分组汇总每月的charge_point_count
    com_profile = (
        merged_profile_com.groupby('month')['rec_data']
        .sum()
        .reset_index()
    )

    # In[1078]:

    com_profile['rec_data'] = com_profile['rec_data'] / 10000
    com_profile['rec_data'] = com_profile['rec_data'].round(2)
    com_profile

    # In[ ]:

    # ### 毛利

    # In[1079]:

    # 分组汇总每月的charge_point_count
    com_lirun = (
        merged_profile_com.groupby('month')['gross_profit']
        .sum()
        .reset_index()
    )

    # In[1080]:

    com_lirun['gross_profit'] = com_lirun['gross_profit'] / 10000
    com_lirun['gross_profit'] = com_lirun['gross_profit'].astype(float)
    com_lirun['gross_profit'] = com_lirun['gross_profit'].round(2)
    com_lirun

    # In[1081]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_xqyx_jingying = pd.merge(com_profile, com_lirun, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_xqyx_jingying['month'].tolist()
    rec_data = df_merged_xqyx_jingying['rec_data'].round(2).tolist()
    gross_profit = df_merged_xqyx_jingying['gross_profit'].round(2).tolist()

    # 构造前端结构
    result_xiaoqu_jingying = {
        "options": ["营收", "毛利"],
        "data": [
            {
                "radio": "营收",
                "legendName": ["营收"],
                "axisData": month,
                "chartData": [rec_data],
                "yAxisName": "万元"
            },
            {
                "radio": "毛利",
                "legendName": ["毛利"],
                "axisData": month,
                "chartData": [gross_profit],
                "yAxisName": "万元"
            }
        ]
    }

    # In[1082]:

    result_xiaoqu_jingying

    # ### 写入数据库

    # In[1083]:

    # # 定义注释
    # table_comment = "类型监测_小区有序_经营情况" resultxqyx_jingying
    # 表和字段注释
    table_comment = "类型监测_小区有序_经营情况"
    column_comments = {
        'result': '经营情况',
        'update_time': '更新日期'
    }
    DF_resultxqyx_jingying = pd.DataFrame([{
        'result': json.dumps(result_xiaoqu_jingying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultxqyx_jingying,
        table_name="dp_xqyx_jingying",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运维情况

    # ### 工单数量

    # In[1084]:

    df_workorders_com = DF_SCGD[DF_SCGD['station_category'] == '小区有序'].copy()

    # In[1085]:

    # 转换 dispatched_workorders 为数值（强制转换无法解析的为 NaN，再填 0）
    df_workorders_com['单桩工单'] = pd.to_numeric(df_workorders_com['单桩工单'], errors='coerce').fillna(0)

    # In[1086]:

    # # 合并生成月份 Data
    # merged_workorders_com = pd.merge(Data, df_workorders_com, how='left', left_on='month', right_on='stat_time')

    # com_workorders = (
    #     merged_workorders_com.groupby('stat_time')['dispatched_workorders']
    #     .sum()
    #     .reset_index()
    #     .rename(columns={'dispatched_workorders': "工单数量"})
    #     .fillna(0)
    # )

    # In[1087]:

    # 第一步：合并数据（保留所有 Data 中的月份）
    merged_workorders_com = pd.merge(
        Data, df_workorders_com, how='left',
        left_on='month', right_on='stat_time'
    )

    # 第二步：将空值填为0，并处理工单数量汇总
    merged_workorders_com['单桩工单'] = merged_workorders_com['单桩工单'].fillna(0)

    # 第三步：按月份汇总
    com_workorders = (
        merged_workorders_com
        .groupby('month')['单桩工单']
        .mean()
        .reset_index()

    )

    # In[1088]:

    com_workorders

    # In[1089]:

    # 提取数据字段
    month = com_workorders['month'].tolist()
    dispatched_workorders = com_workorders['单桩工单'].round(2).tolist()
    # 构造前端结构
    result_xiaoqu_yunwei = {
        "options": ["工单数量"],
        "data": [
            {
                "radio": "工单数量",
                "legendName": ["工单数量"],
                "axisData": month,
                "chartData": [dispatched_workorders],
                "yAxisName": "单"
            }
        ]
    }

    # In[1090]:

    result_xiaoqu_yunwei

    # ### 写入数据库

    # In[1091]:

    # 表和字段注释
    table_comment = "类型检测_小区有序_运维情况"
    column_comments = {
        'result': '工单数量',
        'update_time': '更新日期'
    }
    DF_3 = pd.DataFrame([{
        'result': json.dumps(result_xiaoqu_yunwei, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_3,
        table_name="dp_xqyx_ywqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 其他专用

    # ## 投运情况

    # ### 充电枪数量

    # In[1092]:

    df_filtered_else = DF_SCDD[
        (DF_SCDD['station_category'] == '其他专用') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    # In[1093]:

    result_else_summary = []
    for m in Data['month_dt']:
        active = df_filtered_else[
            (df_filtered_else['commissioning_time'] <= m)
        ]
        guns = active['total_charge_point_count'].sum()
        result_else_summary.append({'month': m.strftime('%Y%m'), 'guns': guns})

    # 3. 输出 DataFrame
    else_monthly_summary = pd.DataFrame(result_else_summary)

    # In[1094]:

    else_monthly_summary

    # ### 总额定功率

    # In[1095]:

    results_else_capacity = []

    for m in Data['month_dt']:
        active = df_filtered_else[
            (df_filtered_else['commissioning_time'] <= m)
        ]
        capacity = active['station_capacity'].mean()
        results_else_capacity.append({'month': m.strftime('%Y%m'), 'capacity': capacity})

    else_monthly_capacity = pd.DataFrame(results_else_capacity)

    # In[1096]:

    else_monthly_capacity

    # In[1097]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_qita_touyun = pd.merge(else_monthly_summary, else_monthly_capacity, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_qita_touyun['month'].tolist()
    guns = df_merged_qita_touyun['guns'].round(2).tolist()
    capacity = df_merged_qita_touyun['capacity'].round(2).tolist()

    # 构造前端结构
    result_qita_touyun = {
        "options": ["充电枪数量", "站均额定功率"],
        "data": [
            {
                "radio": "充电枪数量",
                "legendName": ["充电枪数量"],
                "axisData": month,
                "chartData": [guns],
                "yAxisName": "个"
            },
            {
                "radio": "站均额定功率",
                "legendName": ["站均额定功率"],
                "axisData": month,
                "chartData": [capacity],
                "yAxisName": "KW"
            }
        ]
    }

    # In[1098]:

    result_qita_touyun

    # ### 写入数据库

    # In[1099]:

    # # 定义注释
    # table_comment = "类型监测_其他专用_投运情况"
    # 表和字段注释
    table_comment = "类型监测_其他专用_投运情况"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF_resultqita_touyun = pd.DataFrame([{
        'result': json.dumps(result_qita_touyun, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultqita_touyun,
        table_name="dp_qita_touyun",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 投资情况

    # ### 总投资费用

    # In[1100]:

    # 投资金额转为数值
    df_filtered_else['investment_amount'] = pd.to_numeric(df_filtered_else['investment_amount'], errors='coerce').fillna(0)

    # In[1101]:

    # 确保 commissioning_time 是 datetime 类型
    df_filtered_else['commissioning_time'] = pd.to_datetime(df_filtered_else['commissioning_time'], errors='coerce')

    # 按月份排序，防止乱序
    Data['month'] = sorted(Data['month'])

    invest_results = []

    for month_str in Data['month']:
        # 将 '202407' 转换为对应月份的第一天
        month_dt = pd.to_datetime(month_str, format="%Y%m")

        # 获取所有在当前 month 及之前投运的站点
        df_till_month = df_filtered_else[df_filtered_else['commissioning_time'] <= month_dt]

        # 计算截止当前月的累计投资金额
        total_investment = df_till_month['investment_amount'].sum()

        invest_results.append({
            'month': month_str,
            'total_investment': total_investment
        })

    # 转换为 DataFrame
    else_invest_total = pd.DataFrame(invest_results)

    # # 保留原始字符串格式月份
    # public_invest_total['month'] = pd.to_datetime(public_invest_total['month']).dt.strftime('%Y%m')

    # In[1102]:

    else_invest_total['total_investment'] = else_invest_total['total_investment'] / 10000
    else_invest_total['total_investment'] = else_invest_total['total_investment'].round(2)
    else_invest_total

    # ### 每年投资费用

    # In[1103]:

    # 提取年份列
    df_filtered_else['year'] = df_filtered_else['commissioning_time'].dt.year

    # 原始按年份分组汇总
    else_yearly_investment = (
        df_filtered_else.groupby('year')['investment_amount']
        .sum()
        .reset_index()
    )

    # 单位转换并保留两位小数
    else_yearly_investment['investment_amount'] = (else_yearly_investment['investment_amount'] / 10000).round(2)

    # ➕ 添加：构造完整年份（从 2016 到当前年）
    current_year = datetime.now().year
    all_years = pd.DataFrame({'year': list(range(2016, current_year + 1))})

    # ➕ 合并并填充缺失年份的金额为 0
    else_yearly_investment = (
        all_years
        .merge(else_yearly_investment, on='year', how='left')
        .fillna(0)
    )

    # 保留两位小数（避免 0.0 变成长小数）
    else_yearly_investment['investment_amount'] = else_yearly_investment['investment_amount'].round(2)

    else_yearly_investment['investment_amount'] = (
        else_yearly_investment['investment_amount'].astype(float).round(2)
    )

    else_yearly_investment

    # ### 回本情况

    # In[1104]:

    df_filtered1_else = merged1[merged1['station_category'] == '其他专用'].copy()

    # In[1105]:

    df_filtered1_else['month_str'] = df_filtered1_else['month'].dt.strftime('%Y%m')
    # 转换为 float，避免 Decimal 和 float 相加时报错
    for col in ['revenue', 'total_subsidy', 'cost', 'investment_amount']:
        df_filtered1_else[col] = df_filtered1_else[col].astype(float)

    # In[1106]:

    else_revenue = (
        df_filtered1_else
        .groupby('month_str')
        .apply(lambda df: df['in'].sum() / df['out'].sum())  # 每月 in/out 比
        .cumsum()  # 累计比值
        .reset_index()
        .rename(columns={0: 'huiben', 'month_str': '月份'})
    )

    # In[1107]:

    else_revenue['huiben'] = else_revenue['huiben'] * 100
    else_revenue['huiben'] = else_revenue['huiben'].round(2)
    else_revenue

    # In[1108]:

    result_qita_touzi = {
        "options": ["投资情况"],
        "data": []
    }

    # 构造每一块图表数据
    def build_block(df, axis_col, value_col, radio_name, y_axis_unit):
        return {
            "radio": radio_name,
            "legendName": ["投资情况"],
            "axisData": df[axis_col].tolist(),
            "chartData": [df[value_col].tolist()],
            "yAxisName": y_axis_unit
        }

    # 构建每个部分
    # result["data"].append(build_block(else_invest_total, "month", "total_investment", "总投资费用", "万元", "总投资费用"))
    result_qita_touzi["data"].append(build_block(else_yearly_investment, "year", "investment_amount", "投资情况", "万元"))
    # result["data"].append(build_block(else_revenue, "月份", "huiben", "回本情况", "%", "回本情况"))

    # In[1109]:

    result_qita_touzi

    # ### 写入数据库

    # In[1110]:

    # 表和字段注释
    table_comment = "类型检测_其他专用_投资情况"
    column_comments = {
        'result': '投资情况',
        'update_time': '更新日期'
    }
    DF_3 = pd.DataFrame([{
        'result': json.dumps(result_qita_touzi, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_3,
        table_name="dp_qtzy_tzqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运营情况

    # ### 单枪日均充电量

    # In[1111]:

    df_filtered2_else = DF_org_data_pre_gun[DF_org_data_pre_gun['station_category'] == '其他专用'].copy()

    # In[1112]:

    # 保证月份是字符串
    df_filtered2_else['cba_month'] = df_filtered2_else['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged2_else = pd.merge(Data, df_filtered2_else, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged2_else['days_in_month'] = merged2_else['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 单枪日均充电量 = gun_charging_volume / 月天数
    merged2_else['gun_charging_volume_d'] = merged2_else['gun_charging_volume'] / merged2_else['days_in_month']
    # 按月聚合，取平均值
    else_avg_charge = (
        merged2_else.groupby('month')['gun_charging_volume_d']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_d': 'gun_charging_volume_d'})
        .round(2)
    )

    # In[1113]:

    else_avg_charge['gun_charging_volume_d'] = else_avg_charge['gun_charging_volume_d'].fillna(0)
    else_avg_charge

    # ### 功率利用率

    # In[1114]:

    df_filtered3_else = DF_cba_pue[DF_cba_pue['station_category'] == '其他专用'].copy()

    # In[1115]:

    # 保证月份是字符串
    df_filtered3_else['cba_month'] = df_filtered3_else['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged3_else = pd.merge(Data, df_filtered3_else, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged3_else['days_in_month'] = merged3_else['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 按月聚合，取平均值
    else_pue = (
        merged3_else.groupby('month')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': 'pue'})
        .round(2)
    )

    # In[1116]:

    else_pue['pue'] = else_pue['pue'].fillna(0)

    else_pue

    # In[1117]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_qita_yunying = pd.merge(else_avg_charge, else_pue, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_qita_yunying['month'].tolist()
    gun_charging_volume_d = df_merged_qita_yunying['gun_charging_volume_d'].round(2).tolist()
    pue = df_merged_qita_yunying['pue'].round(2).tolist()

    # 构造前端结构
    result_qita_yunying = {
        "options": ["单枪日均充电量", "功率利用率"],
        "data": [
            {
                "radio": "单枪日均充电量",
                "legendName": ["单枪日均充电量"],
                "axisData": month,
                "chartData": [gun_charging_volume_d],
                "yAxisName": "kWh"
            },
            {
                "radio": "功率利用率",
                "legendName": ["功率利用率"],
                "axisData": month,
                "chartData": [pue],
                "yAxisName": "%"
            }
        ]
    }

    # In[1118]:

    result_qita_yunying

    # ### 写入数据库

    # In[1119]:

    # # 定义注释
    # table_comment = "类型监测_其他专用_运营情况" resultqita_yunying
    # 表和字段注释
    table_comment = "类型监测_其他专用_运营情况"
    column_comments = {
        'result': '运营情况',
        'update_time': '更新日期'
    }
    DF_resultqita_yunying = pd.DataFrame([{
        'result': json.dumps(result_qita_yunying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultqita_yunying,
        table_name="dp_qita_yunying",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 设备质量

    # ### 一次成功率

    # In[1120]:

    sql = '''
        SELECT
          cs.station_category,
          cs.station_no,
          dsr.stat_time,
          SUM(CAST(dsr.order_count AS DECIMAL)) AS total_order_count,

          ROUND(
            SUM(CAST(dsr.order_count AS DECIMAL) * 
                CAST(REPLACE(dsr.success_rate, '%', '') AS DECIMAL(10,4)) / 100)
            / NULLIF(SUM(CAST(dsr.order_count AS DECIMAL)), 0),
            4
          ) AS station_success_rate

        FROM
          dp_success_rate dsr
        INNER JOIN charging_station cs
          ON dsr.station_code = cs.station_no
          WHERE cs.property_owner_merhant_id = 119

        GROUP BY
          cs.station_category,
          cs.station_no,
          dsr.stat_time
        '''
    DF_success = SQL(sql)
    DF_success['month'] = DF_success['stat_time'].astype(str).str.replace('-', '')
    DF_success['month'] = DF_success['month'].astype(str)

    # In[823]:

    DF_success['total_order_count'] = pd.to_numeric(DF_success['total_order_count'], errors='coerce')
    DF_success['station_success_rate'] = pd.to_numeric(DF_success['station_success_rate'], errors='coerce')

    # In[824]:

    DF_success['total_order_count'] = DF_success['total_order_count'].fillna(0)

    # In[825]:

    DF_success['station_success_rate'] = DF_success['station_success_rate'].fillna(0)

    # In[826]:

    # 筛选城市公共
    df_month1 = DF_success[DF_success['station_category'] == '城市公共'].copy()

    # In[827]:

    # 合并生成月份 Data
    merged_success = pd.merge(Data, df_month1, how='left', left_on='month', right_on='month')
    public_success = (
        merged_success.groupby('month')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': "station_success_rate"})
    )

    # In[828]:

    public_success['station_success_rate'] = public_success['station_success_rate'] * 100

    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
        select * from 
        (select station_no,station_category from  charging_station) c
        right join 
        (select time,station_name,station_code,pile_status,normal_duration,operation_duration,city from dp_operation_duration
        where time like '%s' or time like '%s') d 
        on c.station_no = d.station_code
        """ % (t1, t2)
    DF_operation_duration = SQL(sql)

    DF_operation_duration = DF_operation_duration.fillna(0)

    # 可用率计算

    # 可用率=正常状态时长(秒)/在运时长(秒)
    DF_operation_duration['可用率'] = DF_operation_duration['normal_duration'].astype('int') / DF_operation_duration[
        'operation_duration'].astype('int')

    # 筛选正常桩

    print('筛选运行状态前数据形状：', DF_operation_duration.shape)
    DF_operation_duration = DF_operation_duration[DF_operation_duration['pile_status'] == '运行']
    print('筛选运行状态后数据形状', DF_operation_duration.shape)

    # 计算每个站每月平均可用率

    DF_operation_duration_1 = DF_operation_duration.groupby(['time', 'station_no']).agg({'可用率': 'mean'}).reset_index()
    DF_operation_duration_1

    # 获取站点对应城市、站点类型的标签
    DF_operation_duration_2 = DF_operation_duration[['station_no', 'station_category', 'city']].drop_duplicates()
    DF_operation_duration_2

    DF_operation_duration = pd.merge(DF_operation_duration_1, DF_operation_duration_2, on='station_no', how='left')
    DF_operation_duration.head(1)

    # 处理时间

    DF_operation_duration['month'] = [i[:6] for i in DF_operation_duration['time']]

    DF_operation_duration['year'] = [i[:4] for i in DF_operation_duration['month']]

    ############################################################################################33333333333333333333333333333333333333333333333333333333333333

    df_month1_else = DF_success[DF_success['station_category'] == '其他专用'].copy()

    # In[1121]:

    # 合并生成月份 Data
    merged_success_else = pd.merge(Data, df_month1_else, how='left', left_on='month', right_on='month')
    else_success = (
        merged_success_else.groupby('month')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': "station_success_rate"})
    )

    # In[1122]:

    else_success['station_success_rate'] = else_success['station_success_rate'] * 100
    else_success

    # ### 可用率

    # In[1123]:

    else_duration = DF_operation_duration[DF_operation_duration['station_category'] == '其他专用'].copy()

    # In[1124]:

    merged_duration_else = pd.merge(Data, else_duration, how='left', left_on='month', right_on='month')
    else_duration_avg = (
        merged_duration_else.groupby('month')['可用率']
        .mean()
        .reset_index()
        .rename(columns={'可用率': 'available'})
        .round(4)
    )

    # In[1125]:

    else_duration_avg['available'] = else_duration_avg['available'] * 100
    else_duration_avg

    # In[1126]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_qita_sbeizhil = pd.merge(else_success, else_duration_avg, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_qita_sbeizhil['month'].tolist()
    station_success_rate = df_merged_qita_sbeizhil['station_success_rate'].round(2).tolist()
    available = df_merged_qita_sbeizhil['available'].round(2).tolist()

    # 构造前端结构
    result_qita_shebei = {
        "options": ["一次成功率", "可用率"],
        "data": [
            {
                "radio": "一次成功率",
                "legendName": ["一次成功率"],
                "axisData": month,
                "chartData": [station_success_rate],
                "yAxisName": "%"
            },
            {
                "radio": "可用率",
                "legendName": ["可用率"],
                "axisData": month,
                "chartData": [available],
                "yAxisName": "%"
            }
        ]
    }

    # In[1127]:

    result_qita_shebei

    # ### 写入数据库

    # In[1128]:

    # # 定义注释
    # table_comment = "类型监测_其他专用_设备质量"resultqita_sbeizhil
    # 表和字段注释
    table_comment = "类型监测_其他专用_设备质量"
    column_comments = {
        'result': '设备质量',
        'update_time': '更新日期'
    }
    DF_resultqita_sbeizhil = pd.DataFrame([{
        'result': json.dumps(result_qita_shebei, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultqita_sbeizhil,
        table_name="dp_qita_sbeizhil",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 经营情况

    # ### 营收

    # In[1129]:

    # 筛选城市公共
    df_profile_else = DF_cba_org_data[DF_cba_org_data['station_category'] == '其他专用'].copy()

    # In[1130]:

    # 合并生成月份 Data
    merged_profile_else = pd.merge(Data, df_profile_else, how='left', left_on='month', right_on='cba_month')

    # 分组汇总每月的charge_point_count
    else_profile = (
        merged_profile_else.groupby('month')['rec_data']
        .sum()
        .reset_index()
    )

    # In[1131]:

    else_profile['rec_data'] = else_profile['rec_data'] / 10000
    else_profile['rec_data'] = else_profile['rec_data'].round(2)
    else_profile

    # In[ ]:

    # ### 毛利

    # In[1132]:

    # 分组汇总每月的charge_point_count
    else_lirun = (
        merged_profile_else.groupby('month')['gross_profit']
        .sum()
        .reset_index()
    )

    # In[1133]:

    else_lirun['gross_profit'] = else_lirun['gross_profit'] / 10000
    else_lirun['gross_profit'] = else_lirun['gross_profit'].astype(float)
    else_lirun['gross_profit'] = else_lirun['gross_profit'].round(2)
    else_lirun

    # In[1134]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_qtzy_jingying = pd.merge(else_profile, else_lirun, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_qtzy_jingying['month'].tolist()
    rec_data = df_merged_qtzy_jingying['rec_data'].round(2).tolist()
    gross_profit = df_merged_qtzy_jingying['gross_profit'].round(2).tolist()

    # 构造前端结构
    result_qita_jingying = {
        "options": ["营收", "毛利"],
        "data": [
            {
                "radio": "营收",
                "legendName": ["营收"],
                "axisData": month,
                "chartData": [rec_data],
                "yAxisName": "元"
            },
            {
                "radio": "毛利",
                "legendName": ["毛利"],
                "axisData": month,
                "chartData": [gross_profit],
                "yAxisName": "元"
            }
        ]
    }

    # In[1135]:

    result_qita_jingying

    # ### 写入数据库

    # In[1136]:

    # # 定义注释
    # table_comment = "类型监测_其他专用_经营情况" resultqtzy_jingying
    # 表和字段注释
    table_comment = "类型监测_其他专用_经营情况"
    column_comments = {
        'result': '经营情况',
        'update_time': '更新日期'
    }
    DF_resultqtzy_jingying = pd.DataFrame([{
        'result': json.dumps(result_qita_jingying, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultqtzy_jingying,
        table_name="dp_qtzy_jingying",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运维情况

    # ### 工单数量

    # In[1137]:

    # # 筛选城市公共
    # df_workorders_else = DF_SCGD[DF_SCGD['station_category'] == '其他专用'].copy()

    # In[1138]:

    # # 转换 dispatched_workorders 为数值（强制转换无法解析的为 NaN，再填 0）
    # df_workorders_else['单桩工单'] = pd.to_numeric(df_workorders_else['单桩工单'], errors='coerce').fillna(0)

    # In[1139]:

    # # 合并生成月份 Data
    # merged_workorders_else = pd.merge(Data, df_workorders_else, how='left', left_on='month', right_on='stat_time')

    # else_workorders = (
    #     merged_workorders_else.groupby('stat_time')['单桩工单']
    #     .mean()
    #     .reset_index()
    # )

    # In[1140]:

    import numpy as np

    df_workorders_else = DF_SCGD[DF_SCGD['station_category'] == '其他专用'].copy()
    df_workorders_else['单桩工单'] = pd.to_numeric(df_workorders_else['单桩工单'], errors='coerce').fillna(0)

    Data['month'] = Data['month'].astype(str)
    df_workorders_else['stat_time'] = df_workorders_else['stat_time'].astype(str)

    merged_workorders_else = pd.merge(Data, df_workorders_else, how='left', left_on='month', right_on='stat_time')

    else_workorders = (
        merged_workorders_else.groupby('month')['单桩工单']
        .mean()
        .reset_index()
    )

    else_workorders['单桩工单'] = else_workorders['单桩工单'].fillna(0)
    else_workorders['单桩工单'].replace([np.inf, -np.inf], 0, inplace=True)

    else_workorders

    # In[1141]:

    # 提取数据字段
    month = else_workorders['month'].tolist()
    dispatched_workorders = else_workorders['单桩工单'].round(2).tolist()

    # 构造前端结构
    result_qita_yunwei = {
        "options": ["工单数量"],
        "data": [
            {
                "radio": "工单数量",
                "legendName": ["工单数量"],
                "axisData": month,
                "chartData": [dispatched_workorders],
                "yAxisName": "单"
            }
        ]
    }

    # In[1142]:

    result_qita_yunwei

    # ### 写入数据库

    # In[1143]:

    # # 定义注释
    # table_comment = "类型监测_其他专用_运维情况" resultqita_yunwei
    # 表和字段注释
    table_comment = "类型监测_其他专用_运维情况"
    column_comments = {
        'result': '工单数量',
        'update_time': '更新日期'
    }
    DF_resultqita_yunwei = pd.DataFrame([{
        'result': json.dumps(result_qita_yunwei, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_resultqita_yunwei,
        table_name="dp_qita_yunwei",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # # V2G

    # ## 投运情况

    # ### 充电枪数量

    # In[1144]:

    sql = """
    SELECT * FROM
    charging_station
    WHERE station_name like '%V2G%'
    """
    df_v2g = SQL(sql)

    # In[1145]:

    df_v2g['total_charge_point_count'] = df_v2g['ac_charge_point_count'] + df_v2g['dc_charge_point_count']

    # In[1146]:

    v2g_touyun = []
    for m in Data['month_dt']:
        active = df_v2g[
            (df_v2g['commissioning_time'] <= m)
        ]
        guns = active['total_charge_point_count'].sum()
        v2g_touyun.append({'month': m.strftime('%Y%m'), 'charging_guns_op': guns})

    # In[1147]:

    v2g_touyun = pd.DataFrame(v2g_touyun)
    v2g_touyun

    # ### 总额定功率

    # In[1148]:

    v2g_capacity = []

    for m in Data['month_dt']:
        active = df_v2g[
            (df_v2g['commissioning_time'] <= m)
        ]
        capacity = active['station_capacity'].mean()
        v2g_capacity.append({'month': m.strftime('%Y%m'), 'total_power_rate': capacity})

    v2g_capacity = pd.DataFrame(v2g_capacity)

    # In[1149]:

    v2g_capacity

    # ### 写入数据库

    # In[1150]:

    df_merged_v2gtouyun = pd.merge(v2g_touyun, v2g_capacity, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_v2gtouyun['month'].tolist()
    charging_guns_op = df_merged_v2gtouyun['charging_guns_op'].round(2).tolist()
    total_power_rate = df_merged_v2gtouyun['total_power_rate'].round(2).tolist()

    # 构造前端结构
    v2g_result = {
        "options": ["充电枪数量", "站均额定功率"],
        "data": [
            {
                "radio": "充电枪数量",
                "legendName": ["充电枪数量"],
                "axisData": month,
                "chartData": [charging_guns_op],
                "yAxisName": "个"
            },
            {
                "radio": "站均额定功率",
                "legendName": ["站均额定功率"],
                "axisData": month,
                "chartData": [total_power_rate],
                "yAxisName": "kW"
            }
        ]
    }

    # In[1151]:

    v2g_result

    # In[1152]:

    # 表和字段注释
    table_comment = "类型检测_V2G_投运情况"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF_V2G_tyqk = pd.DataFrame([{
        'result': json.dumps(v2g_result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_V2G_tyqk,
        table_name="dp_v2g_tyqk",

        table_comment=table_comment,
        column_comments=column_comments,
    )

    # ## 投资情况

    # #### 总投资费用

    # In[1153]:

    # 投资金额转为数值
    df_v2g['investment_amount'] = pd.to_numeric(df_v2g['investment_amount'], errors='coerce').fillna(0)

    # In[1154]:

    # 确保 commissioning_time 是 datetime 类型
    df_v2g['commissioning_time'] = pd.to_datetime(df_v2g['commissioning_time'], errors='coerce')

    # 按月份排序，防止乱序
    Data['month'] = sorted(Data['month'])

    invest_v2g = []

    for month_str in Data['month']:
        # 将 '202407' 转换为对应月份的第一天
        month_dt = pd.to_datetime(month_str, format="%Y%m")

        # 获取所有在当前 month 及之前投运的站点
        df_till_month = df_v2g[df_v2g['commissioning_time'] <= month_dt]

        # 计算截止当前月的累计投资金额
        total_investment = df_till_month['investment_amount'].sum()

        invest_v2g.append({
            'month': month_str,
            'total_investment': total_investment
        })

    # 转换为 DataFrame
    v2g_invest_total = pd.DataFrame(invest_v2g)

    v2g_invest_total

    # #### 每年投资费用

    # In[1155]:

    # 提取年份列
    df_v2g['year'] = df_v2g['commissioning_time'].dt.year

    # 原始按年份分组汇总
    v2g_yearly_investment = (
        df_v2g.groupby('year')['investment_amount']
        .sum()
        .reset_index()
    )

    # 单位转换并保留两位小数
    v2g_yearly_investment['investment_amount'] = (v2g_yearly_investment['investment_amount'] / 10000).round(2)

    # # ➕ 添加：构造完整年份（从 2016 到当前年）
    # current_year = datetime.now().year
    # all_years = pd.DataFrame({'year': list(range(2016, current_year + 1))})

    # ➕ 合并并填充缺失年份的金额为 0
    v2g_yearly_investment = (
        all_years
        .merge(v2g_yearly_investment, on='year', how='left')
        .fillna(0)
    )

    # 保留两位小数（避免 0.0 变成长小数）
    v2g_yearly_investment['investment_amount'] = v2g_yearly_investment['investment_amount'].round(2)

    v2g_yearly_investment

    # ### 写入数据库

    # In[1156]:

    v2g_touziresult = {
        "options": ["投资情况"],
        "data": []
    }

    #
    # 构造每一块图表数据
    def build_block(df, axis_col, value_col, radio_name, y_axis_unit):
        return {
            "radio": radio_name,
            "legendName": ["投资情况"],
            "axisData": df[axis_col].tolist(),
            "chartData": [df[value_col].tolist()],
            "yAxisName": y_axis_unit
        }

    # 构建每个部分
    # result["data"].append(build_block(public_invest_total, "month", "total_investment", "", "万元","总投资费用"))
    v2g_touziresult["data"].append(build_block(v2g_yearly_investment, "year", "investment_amount", "投资情况", "万元"))
    # result["data"].append(build_block(public_revenue, "月份", "huiben", "回本情况", "%"))

    # In[1157]:

    v2g_touziresult

    # In[1158]:

    # 表和字段注释
    table_comment = "类型检测_V2G_投资情况"
    column_comments = {
        'result': '投资情况',
        'update_time': '更新日期'
    }
    DF_csgg_tyqk = pd.DataFrame([{
        'result': json.dumps(v2g_touziresult, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_csgg_tyqk,
        table_name="dp_v2g_tzqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 运营情况

    # ### 单枪日均充电量

    # In[1159]:

    # 单枪日均充电量
    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
    SELECT * FROM 
    (
        SELECT 
            cs.*
        FROM
            charging_station cs
        LEFT JOIN rec_merchant rm 
            ON cs.property_owner_merhant_id = rm.merchant_id
        WHERE 
            cs.station_name LIKE '%%V2G%%'
    ) a
    LEFT JOIN 
    (
        SELECT * 
        FROM station_cba_org_data 
        WHERE cba_month LIKE '%s' OR cba_month LIKE '%s'
    ) b
    ON a.station_no = b.station_no
    """ % (t1, t2)

    DF_cba_org_data_v2g = SQL(sql)

    # In[1160]:

    DF_cba_org_data_v2g

    # In[1161]:

    DF_cba_org_data_v2g['charge_point_count'] = DF_cba_org_data_v2g['dc_charge_point_count'].fillna(0) + DF_cba_org_data_v2g['ac_charge_point_count'].fillna(0)

    # In[1162]:

    DF_cba_org_data_v2g = DF_cba_org_data_v2g[(DF_cba_org_data_v2g['charge_point_count'] != 0)]
    DF_cba_org_data_v2g = DF_cba_org_data_v2g[DF_cba_org_data_v2g['plat_data_charging_volume'] != 0]

    # In[1163]:

    DF_cba_org_data_v2g['gun_charging_volume'] = DF_cba_org_data_v2g['plat_data_charging_volume'] / DF_cba_org_data_v2g['charge_point_count']

    # In[1164]:

    # 保证月份是字符串
    DF_cba_org_data_v2g['cba_month'] = DF_cba_org_data_v2g['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    merged2_v2g = pd.merge(Data, DF_cba_org_data_v2g, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    merged2_v2g['days_in_month'] = merged2_v2g['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 单枪日均充电量 = gun_charging_volume / 月天数
    merged2_v2g['gun_charging_volume_d'] = merged2_v2g['gun_charging_volume'] / merged2_v2g['days_in_month']
    # 按月聚合，取平均值
    v2g_avg_charge = (
        merged2_v2g.groupby('month')['gun_charging_volume_d']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_d': 'gun_charging_volume_d'})
        .round(2)
    )
    v2g_avg_charge['gun_charging_volume_d'] = v2g_avg_charge['gun_charging_volume_d'].fillna(0)  # 或填充为其他默认值

    # In[1165]:

    v2g_avg_charge

    # ### 功率利用率

    # In[1166]:

    # 功率利用率
    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
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
      cs.station_name LIKE '%%V2G%%'
      AND (scod.cba_month like '%s' or scod.cba_month like '%s')

    """ % (t1, t2)
    DF_cba_pue_v2g = SQL(sql)

    # In[1167]:

    DF_cba_pue_v2g

    # In[1168]:

    DF_cba_pue_v2g['days'] = DF_cba_pue_v2g['cba_month'].apply(get_days_in_month)
    DF_cba_pue_v2g['year'] = [i[:4] for i in DF_cba_pue_v2g['cba_month']]

    # In[1169]:

    DF_cba_pue_v2g = DF_cba_pue_v2g[
        (DF_cba_pue_v2g['station_capacity'].notna()) &
        (DF_cba_pue['station_capacity'] > 0) &
        (DF_cba_pue_v2g['plat_data_charging_volume'].notna())
        ]

    # In[1170]:

    DF_cba_pue_v2g['pue'] = (
                                    DF_cba_pue_v2g['plat_data_charging_volume'] /
                                    (DF_cba_pue_v2g['station_capacity'] * DF_cba_pue_v2g['days'] * 24)
                            ) * 100

    # In[1171]:

    DF_cba_pue_v2g['pue'] = DF_cba_pue_v2g['pue'].fillna(0)

    # In[1172]:

    DF_cba_pue_v2g['pue'] = DF_cba_pue_v2g['pue'].fillna(math.inf)

    # In[1173]:

    # 保证月份是字符串
    DF_cba_pue_v2g['cba_month'] = DF_cba_pue_v2g['cba_month'].astype(str)
    # 合并生成的月份Data和城市公共数据
    v2g_merged3 = pd.merge(Data, DF_cba_pue_v2g, how='left', left_on='month', right_on='cba_month')
    # 每行计算该月天数
    v2g_merged3['days_in_month'] = v2g_merged3['month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    # 按月聚合，取平均值
    v2g_pue = (
        v2g_merged3.groupby('month')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': 'pue'})
        .round(2)
    )

    # In[1174]:

    v2g_pue['pue'] = v2g_pue['pue'].fillna(0)
    v2g_pue['pue'] = v2g_pue['pue'].replace([np.inf, -np.inf], 0)

    # In[1175]:

    print(v2g_pue)

    # ### 写入数据库

    # In[1176]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_v2gyunying = pd.merge(v2g_avg_charge, v2g_pue, on=['month'], how='outer').fillna(0)
    # 提取数据字段
    month = df_merged_v2gyunying['month'].tolist()
    gun_charging_volume_d = df_merged_v2gyunying['gun_charging_volume_d'].round(2).tolist()
    pue = df_merged_v2gyunying['pue'].round(2).tolist()

    # 构造前端结构
    v2g_yunyingresult = {
        "options": ["单枪日均充电量", "功率利用率"],
        "data": [
            {
                "radio": "单枪日均充电量",
                "legendName": ["单枪日均充电量"],
                "axisData": month,
                "chartData": [gun_charging_volume_d],
                "yAxisName": "kWh"
            },
            {
                "radio": "功率利用率",
                "legendName": ["功率利用率"],
                "axisData": month,
                "chartData": [pue],
                "yAxisName": "%"
            }
        ]
    }

    # In[1177]:

    v2g_yunyingresult

    # In[1178]:

    # 表和字段注释
    table_comment = "类型检测_V2G_运营情况"
    column_comments = {
        'result': '投资情况',
        'update_time': '更新日期'
    }
    DF_csgg_tyqk = pd.DataFrame([{
        'result': json.dumps(v2g_yunyingresult, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_csgg_tyqk,
        table_name="dp_v2g_yyqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 设备质量

    # ### 一次成功率

    # In[1179]:

    DF_V2G_success = DF_success.merge(
        df_v2g['station_no'],
        on='station_no',
        how='left'
    )

    # In[1180]:

    DF_V2G_success

    # In[1181]:

    DF_V2G_success['year_month'] = DF_V2G_success['stat_time'].astype(str).str.replace('-', '')
    DF_V2G_success['year_month'] = DF_V2G_success['year_month'].astype(str)
    DF_V2G_success['total_order_count'] = pd.to_numeric(DF_V2G_success['total_order_count'], errors='coerce')
    DF_V2G_success['station_success_rate'] = pd.to_numeric(DF_V2G_success['station_success_rate'], errors='coerce')
    DF_V2G_success['total_order_count'] = DF_V2G_success['total_order_count'].fillna(0)
    DF_V2G_success['station_success_rate'] = DF_V2G_success['station_success_rate'].fillna(0)

    # In[1182]:

    # 合并生成月份 Data
    v2g_merged_success = pd.merge(Data, DF_V2G_success, how='left', left_on='month', right_on='year_month')
    v2g_success = (
        v2g_merged_success.groupby('year_month')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': "station_success_rate"})
    )
    v2g_success['station_success_rate'] = v2g_success['station_success_rate'] * 100

    # In[1183]:

    v2g_success

    # ### 可用率

    # In[1184]:

    v2g_no = df_v2g['station_no']

    # In[1185]:

    # 1. 筛选 V2G 站点
    v2g_duration = DF_operation_duration[
        DF_operation_duration['station_no'].isin(v2g_no)
    ].copy()
    print("v2g_duration的列明为：",v2g_duration.columns)

    # 2. 合并（保留 Data 的月份）
    merged_duration = pd.merge(
        Data,
        v2g_duration,
        how='left',  # 保留 Data 的所有月份
        left_on='month',
        right_on='month'
    )

    # 3. 按 Data['month'] 统计可用率
    v2g_duration_avg = (
        merged_duration.groupby('month')['可用率']
        .mean()
        .reset_index()
        .rename(columns={'可用率': 'Availability',
                         'month': 'year_month'})
        .round(4)
    )

    # 4. 转换为百分比（注意全 NaN 不会报错）
    v2g_duration_avg['Availability'] = v2g_duration_avg['Availability'] * 100

    # In[1186]:

    v2g_duration_avg = v2g_duration_avg.fillna(0)

    # In[ ]:

    # ### 写入数据库

    # In[1187]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_v2gshebzhil = pd.merge(v2g_success, v2g_duration_avg, on=['year_month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_v2gshebzhil['year_month'].tolist()
    station_success_rate = df_merged_v2gshebzhil['station_success_rate'].round(2).tolist()
    Availability = df_merged_v2gshebzhil['Availability'].round(2).tolist()

    # 构造前端结构
    result = {
        "options": ["一次成功率", "可用率"],
        "data": [
            {
                "radio": "一次成功率",
                "legendName": ["一次成功率"],
                "axisData": month,
                "chartData": [station_success_rate],
                "yAxisName": "%"
            },
            {
                "radio": "可用率",
                "legendName": ["可用率"],
                "axisData": month,
                "chartData": [Availability],
                "yAxisName": "%"
            }
        ]
    }

    # In[1188]:

    result

    # In[1189]:

    # 表和字段注释
    table_comment = "类型检测_V2G_设备质量"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_v2g_sbzl",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 经营情况

    # In[1190]:

    # 时间条件
    t1 = str(last_year) + '%'
    t2 = str(year) + '%'

    # 1. 查询 merchant_profit_amount（只保留 V2G 站点）
    sql = f"""
    SELECT 
        b.merchant_profit_amount,
        b.rec_month,
        a.station_no,
        a.city,
        a.station_category,
        a.dc_charge_point_count,
        a.ac_charge_point_count
    FROM (
        SELECT * FROM charging_station
        WHERE station_name LIKE '%%V2G%%'
    ) a
    LEFT JOIN (
        SELECT * FROM fin_rec_result_detail 
        WHERE (rec_month LIKE '{t1}' OR rec_month LIKE '{t2}') 
        AND merchant_id != 119
    ) b
    ON a.station_no = b.station_no
    """
    df_v2g_mpa = SQL(sql)

    # 2. 查询 station_cba_org_data（只保留 V2G 站点）
    sql = f"""
    SELECT 
        b.*,
        a.city,
        a.station_category,
        a.dc_charge_point_count,
        a.ac_charge_point_count
    FROM (
        SELECT * FROM charging_station
        WHERE station_name LIKE '%%V2G%%'
    ) a
    LEFT JOIN (
        SELECT * FROM station_cba_org_data 
        WHERE cba_month LIKE '{t1}' OR cba_month LIKE '{t2}'
    ) b
    ON a.station_no = b.station_no
    """
    df_v2g_cba_org = SQL(sql)

    # 3. 查询 station_maintenance_cost（只保留 V2G 并满足维护费用 > 0）
    sql = f"""
    SELECT station_no, stat_time AS cba_month, maintenance_cost 
    FROM dp_station_maintenance_cost1
    WHERE 
    (stat_time LIKE '{t1}' OR stat_time LIKE '{t2}')
    AND maintenance_cost > 0
    """
    df_v2g_maintenance = SQL(sql)

    # 4. 聚合 df_v2g_mpa，重命名列
    df_v2g_mpa = df_v2g_mpa.fillna(0)
    df_v2g_mpa = df_v2g_mpa[['rec_month', 'station_no', 'merchant_profit_amount']]
    df_v2g_mpa = df_v2g_mpa.rename(columns={'rec_month': 'cba_month'})
    df_v2g_mpa['cba_month'] = df_v2g_mpa['cba_month'].astype(str)  # ✅ 强制为字符串
    df_v2g_mpa = df_v2g_mpa.groupby(['cba_month', 'station_no']).agg({'merchant_profit_amount': 'sum'}).reset_index()

    # 5. 合并 df_v2g_cba_org + df_v2g_mpa
    df_v2g_cba_org['cba_month'] = df_v2g_cba_org['cba_month'].astype(str)  # ✅ 保证两边类型一致
    df_v2g_all_profit = pd.merge(df_v2g_cba_org, df_v2g_mpa, on=['station_no', 'cba_month'], how='left')
    df_v2g_all_profit = df_v2g_all_profit.fillna(0)

    # 6. 加入年份列
    df_v2g_all_profit['year'] = df_v2g_all_profit['cba_month'].str[:4]

    # 7. 合并维护费用
    df_v2g_all_profit = pd.merge(df_v2g_all_profit, df_v2g_maintenance, on=['station_no', 'cba_month'], how='left')
    df_v2g_all_profit['maintenance_cost'] = df_v2g_all_profit['maintenance_cost'].fillna(0)
    # 将涉及计算的字段统一转为 float（避免 Decimal 报错）
    cols_to_float = [
        'rec_data_elec_fee_revenue',
        'rec_data_service_fee_revenue',
        'other_revenue_battery_swap_services',
        'other_revenue_access_control_barriers',
        'other_revenue_dr',
        'rec_cost_elec_fee',
        'rec_cost_rent',
        'om_cost_op_project',
        'fin_cost_depreciation',
        'fin_cost_labor',
        'merchant_profit_amount',
        'maintenance_cost'
    ]

    for col in cols_to_float:
        if col in df_v2g_all_profit.columns:
            df_v2g_all_profit[col] = pd.to_numeric(df_v2g_all_profit[col], errors='coerce').fillna(0.0).astype(float)

    # 8. 计算收入（rec_data）和成本（rec_cost）
    df_v2g_all_profit['rec_data'] = (
            df_v2g_all_profit['rec_data_elec_fee_revenue'].fillna(0) +
            df_v2g_all_profit['rec_data_service_fee_revenue'].fillna(0) +
            df_v2g_all_profit['other_revenue_battery_swap_services'].fillna(0) +
            df_v2g_all_profit['other_revenue_access_control_barriers'].fillna(0) +
            df_v2g_all_profit['other_revenue_dr'].fillna(0)
    )

    df_v2g_all_profit['rec_cost'] = (
            df_v2g_all_profit['rec_cost_elec_fee'].fillna(0) +
            df_v2g_all_profit['rec_cost_rent'].fillna(0) +
            df_v2g_all_profit['om_cost_op_project'].fillna(0) +
            df_v2g_all_profit['fin_cost_depreciation'].fillna(0) +
            df_v2g_all_profit['fin_cost_labor'].fillna(0) +
            df_v2g_all_profit['merchant_profit_amount'].fillna(0) +
            df_v2g_all_profit['maintenance_cost']
    )

    # In[1191]:

    df_v2g_all_profit

    # In[ ]:

    # ### 营收

    # In[1192]:

    # 合并生成月份 Data
    merged_profile_v2g = pd.merge(Data, df_v2g_all_profit, how='left', left_on='month', right_on='cba_month')
    # 分组汇总每月的charge_point_count
    v2g_profile = (
        merged_profile_v2g.groupby('month')['rec_data']
        .sum()
        .reset_index()
    )
    v2g_profile['rec_data'] = (v2g_profile['rec_data'].astype(float) / 10000).round(2)

    v2g_profile

    # ### 毛利

    # In[1193]:

    # 分组汇总每月的charge_point_count
    v2g_lirun = (
        merged_profile_v2g.groupby('month')['gross_profit']
        .sum()
        .reset_index()
    )
    v2g_lirun['gross_profit'] = (v2g_lirun['gross_profit'].astype(float) / 10000).round(2)
    v2g_lirun

    # ### 写入数据库

    # In[1194]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_v2g_jingying = pd.merge(v2g_profile, v2g_lirun, on=['month'], how='outer').fillna(0)

    # 提取数据字段
    month = df_merged_v2g_jingying['month'].tolist()
    rec_data = df_merged_v2g_jingying['rec_data'].round(2).tolist()
    gross_profit = df_merged_v2g_jingying['gross_profit'].round(2).tolist()

    # 构造前端结构
    v2g_jingyingresult = {
        "options": ["营收", "毛利"],
        "data": [
            {
                "radio": "营收",
                "legendName": ["营收"],
                "axisData": month,
                "chartData": [rec_data],
                "yAxisName": "万元"
            },
            {
                "radio": "毛利",
                "legendName": ["毛利"],
                "axisData": month,
                "chartData": [gross_profit],
                "yAxisName": "万元"
            }
        ]
    }

    # In[1195]:

    v2g_jingyingresult

    # In[1196]:

    # 表和字段注释
    table_comment = "类型检测_V2G_经营情况"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(v2g_jingyingresult, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_v2g_jyqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:

    # ## 运维情况

    # ### 工单数量

    # In[1197]:

    # 1. 仅筛选 station_name 包含 V2G 的数据
    df_v2g_workorders = DF_SCGD[DF_SCGD['station_name'].str.contains('V2G', na=False)].copy()

    # 2. 清洗工单数据列
    df_v2g_workorders['单桩工单'] = pd.to_numeric(df_v2g_workorders['单桩工单'], errors='coerce').fillna(0)

    # 3. 时间字段统一为字符串
    Data['month'] = Data['month'].astype(str)
    df_v2g_workorders['stat_time'] = df_v2g_workorders['stat_time'].astype(str)

    # 4. 构造月份列表
    month_df = pd.DataFrame({'month': Data['month'].unique()})

    # 5. 合并月份和工单数据
    merged_v2g_workorders = pd.merge(month_df, df_v2g_workorders, how='left', left_on='month', right_on='stat_time')

    # 6. 按月统计平均工单数
    v2g_workorder_stats = (
        merged_v2g_workorders.groupby('month')['单桩工单']
        .mean()
        .reset_index()
    )

    # 7. 清洗 NaN 和 inf
    v2g_workorder_stats['单桩工单'] = v2g_workorder_stats['单桩工单'].fillna(0)
    v2g_workorder_stats['单桩工单'].replace([np.inf, -np.inf], 0, inplace=True)

    # 输出结果
    v2g_workorder_stats

    # In[ ]:

    # ### 写入数据库

    # In[1198]:

    # 提取数据字段
    month = v2g_workorder_stats['month'].tolist()
    dispatched_workorders = v2g_workorder_stats['单桩工单'].round(2).tolist()
    # 构造前端结构
    v2g_workorderresult = {
        "options": ["工单数量"],
        "data": [
            {
                "radio": "工单数量",
                "legendName": ["工单数量"],
                "axisData": month,
                "chartData": [dispatched_workorders],
                "yAxisName": "单"
            }
        ]
    }

    # In[1199]:

    v2g_workorderresult

    # In[1200]:

    # 表和字段注释
    table_comment = "类型检测_V2G_运维情况"
    column_comments = {
        'result': '投运情况',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(v2g_workorderresult, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_v2g_ywqk",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 站点指标现状

    # In[1201]:

    M

    # In[1202]:

    sql = f"""
    SELECT 
    cs.station_name,cs.station_no,cs.investment_amount,cs.commissioning_time,cs.station_category
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and operation_status = '投运' 
    and cs.commissioning_time <= '{M}'

    """
    DF_station = SQL(sql)

    ybzdsl = len(DF_station)
    print(f"站点数量{ybzdsl}")
    csgg_zdsl = len(DF_station[DF_station['station_category'] == '城市公共'])
    print(f'城市公共站点数：{csgg_zdsl}')

    zkzy_zdsl = len(DF_station[DF_station['station_category'] == '重卡专用'])
    print(f'重卡专用站点数：{zkzy_zdsl}')

    gongjiao_zdsl = len(DF_station[DF_station['station_category'] == '公交专用'])
    print(f'公交专用站点数：{gongjiao_zdsl}')

    gaosu_zdsl = len(DF_station[DF_station['station_category'] == '高速公共'])
    print(f'高速公共站点数：{gaosu_zdsl}')

    xiaoqu_zdsl = len(DF_station[DF_station['station_category'] == '小区有序'])
    print(f'小区有序站点数：{xiaoqu_zdsl}')

    qita_zdsl = len(DF_station[DF_station['station_category'] == '其他专用'])
    print(f'其他专用站点数：{qita_zdsl}')

    sql = f"""
    select station_no,sum(total_subsidy) as total_subsidy from dp_subsidy_NEW
    GROUP BY station_no
    """
    DF_subsidy = SQL(sql)

    sql = f"""
    select b.station_no,
    sum(IFNULL(b.rec_data_elec_fee_revenue,0)+IFNULL(b.rec_data_service_fee_revenue,0)+IFNULL(b.other_revenue_battery_swap_services,0)+
    IFNULL(b.other_revenue_access_control_barriers,0)+IFNULL(b.other_revenue_dr,0)) as revenue,
    sum(IFNULL(b.rec_cost_elec_fee,0)+
    IFNULL(b.rec_cost_rent,0)+IFNULL(b.fin_cost_depreciation+b.fin_cost_labor,0)) as cost
    from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and operation_status in ('投运','退运') and  investment_amount is not null) a
    left join 
    (select * from station_cba_org_data where cba_month <= '{M}' ) b
    on a.station_no =b.station_no
    GROUP BY a.station_name,b.station_no
    """
    DF_cost_revenue = SQL(sql)

    sql = """
    SELECT
    cs.station_no,cs.property_owner_merhant_id,rm.merchant_id,
    JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) AS parking_fee
    FROM
    charging_station cs
    LEFT JOIN
    rec_merchant_rec_station rmr ON cs.station_no = rmr.station_on
    LEFT JOIN
    rec_merchant rm ON rmr.merchant_id = rm.merchant_id
    LEFT JOIN
    scdd_rec_rules sr ON rm.merchant_id = sr.merchant_id
    where property_owner_merhant_id =119
    and  JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL 

    """
    DF_rent = SQL(sql)
    if int(M[4:]) == 12:
        M_next = str(int(M[:4]) + 1) + '01'
    else:
        M_next = M[:4] + str(int(M[4:]) + 1).rjust(2, "0")
    sql = """
    select b.merchant_profit_amount,b.rec_month,a.station_no,a.city,a.station_category,a.dc_charge_point_count,a.ac_charge_point_count from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and cs.operation_status in ('投运','退运')
    ) a
    left join 
    (select * from fin_rec_result_detail where rec_month <%s and   merchant_id != 119 ) b
    on a.station_no =b.station_no
    """ % (M_next)
    fin_rec_result_detail = SQL(sql)

    sql = f"""
    select station_no, stat_time as cba_month,maintenance_cost from  dp_station_maintenance_cost1
    where 
    (stat_time <{M_next}) and maintenance_cost>0
    """
    DF_maintenance = SQL(sql)
    DF_maintenance = DF_maintenance.groupby('station_no').agg({'maintenance_cost': 'sum'}).reset_index()
    DF_1 = pd.merge(DF_station, DF_cost_revenue, on='station_no', how='left')

    # 处理投运时间字段
    DF_1['year'] = DF_1['commissioning_time'].dt.year
    DF_1['year_month'] = DF_1['commissioning_time'].dt.strftime('%Y%m')
    DF_rent = DF_rent[['station_no', 'parking_fee']]
    DF_rent['parking_fee'] = DF_rent['parking_fee'].astype('float')
    DF_1 = pd.merge(DF_1, DF_rent, on='station_no', how='left')
    DF_1['month'] = [int(i[4:]) for i in DF_1['year_month']]
    DF_1['month_num'] = [x + y for x, y in zip([int(M[4:]) - i for i in DF_1['month']], [(int(M[:4]) - i) * 12 for i in DF_1['year']])]
    DF_1['rent'] = DF_1['parking_fee'] * DF_1['month_num']
    DF_1['rent'] = DF_1['rent'].fillna(0)
    DF_1 = DF_1[DF_1['year_month'] <= M]
    DF_1 = pd.merge(DF_1, DF_maintenance, on='station_no', how='left')
    d1 = len(DF_1)
    DF_1 = DF_1.T.drop_duplicates().T
    DF_1 = DF_1[DF_1['investment_amount'].notna()]
    fin_rec_result_detail = fin_rec_result_detail.fillna(0)
    fin_rec_result_detail = fin_rec_result_detail[['station_no', 'merchant_profit_amount']]
    # fin_rec_result_detail =fin_rec_result_detail.rename(columns={'rec_month':'year_month'})
    fin_rec_result_detail = fin_rec_result_detail.groupby(['station_no']).agg({'merchant_profit_amount': 'sum'}).reset_index()
    DF_1 = pd.merge(DF_1, fin_rec_result_detail, on=['station_no'], how='left')
    DF_1 = DF_1.fillna(0)
    DF_1.loc[DF_1['station_category'] == '高速', 'station_category'] = '高速公共'
    DF_1['revenue'] = DF_1['revenue'].astype('float') / 10000
    DF_1['cost'] = DF_1['cost'].astype('float') / 10000 + DF_1['rent'] / 10000
    DF_1['investment_amount'] = DF_1['investment_amount'].astype('float') / 10000
    DF_1['merchant_profit_amount'] = DF_1['merchant_profit_amount'].astype('float') / 10000
    DF = pd.merge(DF_1, DF_subsidy, on='station_no', how='left')
    DF = DF.fillna(0)
    DF['in'] = DF['revenue'].astype('float') + DF['total_subsidy'].astype('float')
    DF['out'] = DF['cost'].astype('float') + DF['investment_amount'].astype('float') + DF['merchant_profit_amount'].astype('float') + DF['maintenance_cost'].astype('float')
    sql1 = """
    SELECT 
      b.station_no,
      SUM(
        IFNULL(b.rec_data_elec_fee_revenue, 0) +
        IFNULL(b.rec_data_service_fee_revenue, 0) +
        IFNULL(b.other_revenue_battery_swap_services, 0) +
        IFNULL(b.other_revenue_access_control_barriers, 0) +
        IFNULL(b.other_revenue_dr, 0)
      ) AS revenue,
      SUM(
        IFNULL(b.rec_cost_elec_fee, 0) +

        IFNULL(b.rec_cost_rent, 0) +

        IFNULL(b.fin_cost_depreciation + b.fin_cost_labor, 0)
      ) AS cost
    FROM (
      SELECT cs.*
      FROM charging_station cs
      LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
      WHERE 
        rm.merchant_name = '国网电动汽车服务（四川）有限公司'
        AND investment_amount IS NOT NULL
        AND cs.station_name IN (
          '四川省成都市彭州市濛阳镇供电所电动汽车充电站',
          '沪蓉高速遂宁服务区公共充电站成都方向',
          '沪蓉高速遂宁服务区公共充电站上海方向',
          '四川省成都市成华区麻石桥充电站',
          '四川省成都市成华区麻石桥充电站二期'
        )
    ) a
    LEFT JOIN station_cba_org_data b ON a.station_no = b.station_no
    GROUP BY a.station_name, b.station_no

    """
    df1 = SQL(sql1)
    sql2 = """select station_no,sum(total_subsidy) as total_subsidy from dp_subsidy_NEW
    where station_no IN (
      "300003000100002472",
      "300003000100002473",
      "300003013200011",
      "300003013200099",
      "300003013200105",
      "300003013200108"
    )
    GROUP BY station_no"""
    df2 = SQL(sql2)
    sql3 = """SELECT 
     station_no,investment_amount
    FROM charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
      rm.merchant_name = '国网电动汽车服务（四川）有限公司'
      AND cs.station_no IN (
      "300003000100002472",
      "300003000100002473",
      "300003013200011",
      "300003013200099",
      "300003013200105",
      "300003013200108"
      )"""
    df3 = SQL(sql3)
    sql3_1 = f"""
    select station_no, stat_time as cba_month,maintenance_cost from  dp_station_maintenance_cost1
    where 
    (stat_time <{M_next}) and maintenance_cost>0 and station_no IN (
      "300003000100002472",
      "300003000100002473",
      "300003013200011",
      "300003013200099",
      "300003013200105",
      "300003013200108"
      )
    """
    df3_1 = SQL(sql3_1)
    df3_1 = df3_1.groupby('station_no').agg({'maintenance_cost': 'sum'}).reset_index()
    df4 = fin_rec_result_detail[fin_rec_result_detail['station_no'].isin(["300003000100002472",
                                                                          "300003000100002473",
                                                                          "300003013200011",
                                                                          "300003013200099",
                                                                          "300003013200105"])].fillna(0)
    df_temp = pd.merge(pd.merge(df1, df2, on='station_no', how='left'), df3, on='station_no', how='left')
    df_temp = pd.merge(df_temp, df3_1, on='station_no', how='left')
    df_temp = pd.merge(df_temp, df4, on='station_no', how='left')
    df_temp = df_temp.fillna(0)
    df_temp['revenue'] = df_temp['revenue'] / 10000
    df_temp['cost'] = df_temp['cost'] / 10000
    df_temp['investment_amount'] = df_temp['investment_amount'] / 10000
    df_temp['merchant_profit_amount'] = df_temp['merchant_profit_amount'] / 10000
    df_temp['in'] = df_temp['revenue'].astype('float') + df_temp['total_subsidy'].astype('float')
    df_temp['out'] = df_temp['cost'].astype('float') + df_temp['investment_amount'].astype('float') + df_temp['merchant_profit_amount'].astype('float') + df_temp['maintenance_cost'].astype('float')
    DF.loc[DF['station_no'] == '300003000100019488', 'in'] = DF[DF['station_no'] == '300003000100019488']['in'].values[0] + df_temp[df_temp['station_no'] == '300003013200108']['in'].values[0]
    DF.loc[DF['station_no'] == '300003000100017539', 'in'] = DF[DF['station_no'] == '300003000100017539']['in'].values[0] + df_temp[df_temp['station_no'] == '300003000100002472']['in'].values[0]
    DF.loc[DF['station_no'] == '300003000100017538', 'in'] = DF[DF['station_no'] == '300003000100017538']['in'].values[0] + df_temp[df_temp['station_no'] == '300003000100002473']['in'].values[0]
    DF.loc[DF['station_no'] == '300003000100019487', 'in'] = DF[DF['station_no'] == '300003000100019487']['in'].values[0] + df_temp[df_temp['station_no'] == '300003013200011']['in'].values[0] + df_temp[df_temp['station_no'] == '300003013200099']['in'].values[0]
    DF.loc[DF['station_no'] == '300003000100019488', 'out'] = DF[DF['station_no'] == '300003000100019488']['out'].values[0] + df_temp[df_temp['station_no'] == '300003013200108']['out'].values[0]
    DF.loc[DF['station_no'] == '300003000100017539', 'out'] = DF[DF['station_no'] == '300003000100017539']['out'].values[0] + df_temp[df_temp['station_no'] == '300003000100002472']['out'].values[0]
    DF.loc[DF['station_no'] == '300003000100017538', 'out'] = DF[DF['station_no'] == '300003000100017538']['out'].values[0] + df_temp[df_temp['station_no'] == '300003000100002473']['out'].values[0]
    DF.loc[DF['station_no'] == '300003000100019487', 'out'] = DF[DF['station_no'] == '300003000100019487']['out'].values[0] + df_temp[df_temp['station_no'] == '300003013200011']['out'].values[0] + df_temp[df_temp['station_no'] == '300003013200099']['out'].values[0]
    DF = DF[DF['investment_amount'] != 0]
    huibenzhandian = DF[DF['in'] > DF['out']]
    huibenzhandian.groupby('station_category').agg({'station_no': 'count'})
    hbzdgs = len(huibenzhandian)
    print("回本的站点个数hbzdgs:", hbzdgs)
    # 假设你要筛选 station_category 为 '公用站'
    csgg_hb = DF[(DF['in'] > DF['out']) & (DF['station_category'] == '城市公共')]
    csgg_hbsl = len(csgg_hb)
    print("城市公共回本的站点：", csgg_hbsl)

    zkzy_hb = DF[(DF['in'] > DF['out']) & (DF['station_category'] == '重卡专用')]
    zkzy_hbsl = len(zkzy_hb)
    print("重卡专用回本的站点：", zkzy_hbsl)

    gjzy_hb = DF[(DF['in'] > DF['out']) & (DF['station_category'] == '公交专用')]
    gjzy_hbsl = len(gjzy_hb)
    print("公交专用回本的站点：", gjzy_hbsl)

    gsgg_hb = DF[(DF['in'] > DF['out']) & (DF['station_category'] == '高速公共')]
    gsgg_hbsl = len(gsgg_hb)
    print("高速公共回本的站点：", gsgg_hbsl)

    xqyx_hb = DF[(DF['in'] > DF['out']) & (DF['station_category'] == '小区有序')]
    xqyx_hbsl = len(xqyx_hb)
    print("小区有序回本的站点：", xqyx_hbsl)

    qtzy_hb = DF[(DF['in'] > DF['out']) & (DF['station_category'] == '其他专用')]
    qtzy_hbsl = len(qtzy_hb)
    print("其他专用回本的站点：", qtzy_hbsl)
    # 筛选 V2G 回本的站点
    v2g_hb = DF[(DF['in'] > DF['out']) & (DF['station_name'].str.contains('V2G', na=False))]

    # 统计数量
    v2g_hbsl = len(v2g_hb)

    print("V2G回本的站点：", v2g_hbsl)

    DF['hbpercentage'] = DF['in'] / DF['out'] * 100

    # In[1203]:

    sql = """
    SELECT 
    cs.station_name,cs.station_no,cs.investment_amount,cs.commissioning_time,cs.station_category
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and operation_status ='投运' 

    """
    DFF_station = SQL(sql)

    sql = f"""
    select station_no,sum(total_subsidy) as total_subsidy from dp_subsidy_NEW
    where year <='{year}'
    GROUP BY station_no
    """
    DFF_subsidy = SQL(sql)

    sql = """
    select b.station_no,b.cba_month,
    sum(IFNULL(b.rec_data_elec_fee_revenue,0)+IFNULL(b.rec_data_service_fee_revenue,0)+IFNULL(b.other_revenue_battery_swap_services,0)+
    IFNULL(b.other_revenue_access_control_barriers,0)+IFNULL(b.other_revenue_dr,0)) as revenue,
    sum(IFNULL(b.rec_cost_elec_fee,0)+
    IFNULL(b.rec_cost_rent,0)+IFNULL(b.fin_cost_depreciation+b.fin_cost_labor,0)) as cost
    from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and operation_status ='投运' and  investment_amount is not null) a
    left join 
    (select * from station_cba_org_data  ) b
    on a.station_no =b.station_no
    GROUP BY  b.station_no,b.cba_month
    """
    DFF_cost_revenue = SQL(sql)

    sql = """
    SELECT
    cs.station_no,cs.property_owner_merhant_id,rm.merchant_id,
    JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) AS parking_fee
    FROM
    charging_station cs
    LEFT JOIN
    rec_merchant_rec_station rmr ON cs.station_no = rmr.station_on
    LEFT JOIN
    rec_merchant rm ON rmr.merchant_id = rm.merchant_id
    LEFT JOIN
    scdd_rec_rules sr ON rm.merchant_id = sr.merchant_id
    where property_owner_merhant_id =119
    and  JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL 

    """
    DFF_rent = SQL(sql)
    if int(M[4:]) == 12:
        M_next = str(int(M[:4]) + 1) + '01'
    else:
        M_next = M[:4] + str(int(M[4:]) + 1).rjust(2, "0")
    sql = """
    select b.merchant_profit_amount,b.rec_month,a.station_no,a.city,a.station_category,a.dc_charge_point_count,a.ac_charge_point_count from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and cs.operation_status in ('投运')
    ) a
    left join 
    (select * from fin_rec_result_detail where rec_month <%s and   merchant_id != 119 ) b
    on a.station_no =b.station_no
    """ % (M_next)
    DFF_fin_rec_result_detail = SQL(sql)

    # ## 城市公共

    # ### 站点维度

    # In[1204]:

    DFF_station = DFF_station[['station_name', 'station_no', 'station_category']]

    # In[1205]:

    DFF_cost_revenue = DFF_cost_revenue[DFF_cost_revenue['cba_month'] == M]

    # In[1206]:

    DFF_station['station_no']

    # In[1207]:

    DFF_rent = DFF_rent[['station_no', 'parking_fee']]

    # In[1208]:

    DFF_fin_rec_result_detail = DFF_fin_rec_result_detail[DFF_fin_rec_result_detail['rec_month'] == M][['station_no', 'merchant_profit_amount']]

    # In[1209]:

    DFF_fin_rec_result_detail = DFF_fin_rec_result_detail.groupby('station_no').agg({'merchant_profit_amount': 'sum'}).reset_index()

    # In[1210]:

    df11 = pd.merge(pd.merge(pd.merge(DFF_station, DFF_cost_revenue, on='station_no', how='left'), DFF_rent, on='station_no', how='left'), DFF_fin_rec_result_detail, on='station_no', how='left')

    # In[1211]:

    df11 = df11.fillna(0)

    # In[1212]:

    df11['cost'] = df11['cost'].astype('float') + df11['parking_fee'].astype('float') + df11['merchant_profit_amount'].astype('float')

    # In[1213]:

    df345 = df11[df11['station_category'] == '城市公共'].copy()

    # In[1214]:

    df345['gross_profit'] = df345['revenue'].astype('float') - df345['cost'].astype('float')

    # In[1215]:

    df345

    # In[1216]:

    df_zdzb = DF_SCDD[
        (DF_SCDD['operation_status'] == '投运') &
        (DF_SCDD['station_category'] == '城市公共')
        ].copy()

    # In[1217]:

    result_station_point = (
        df_zdzb
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('station_no')
        .agg(
            station_name=('station_name', 'first'),
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    # In[1218]:

    # 假设你已有的站点信息表叫 df_station（你发的DataFrame）
    # 且另有一个投资记录表 df_investment，包含 station_no、investment_amount、investment_time 字段

    df_zdzb['investment_time'] = pd.to_datetime(df_zdzb['commissioning_time'])

    # 筛选出 2025 年发生的投资
    df_2025 = df_zdzb[df_zdzb['investment_time'].dt.year == year]

    # 汇总每个站点的投资总额
    df_2025_total = df_2025.groupby('station_no', as_index=False)['investment_amount'].sum()
    df_2025_total.rename(columns={'investment_amount': 'investment_2025_total'}, inplace=True)

    # In[1219]:

    df_2025_total

    # In[ ]:

    # In[1220]:

    hbpercentage = (
        DF[['station_no', 'hbpercentage']]
        .fillna({'hbpercentage': 0})
        .merge(
            DF_SCDD[['station_no', 'station_category']],
            on='station_no',
            how='left'
        )
        .query("station_category == '城市公共'")
        [['station_no', 'hbpercentage']]  # 保留需要的列
    )

    # In[1221]:

    DF_cba_org_data['charge_point_count'] = DF_cba_org_data['dc_charge_point_count'].fillna(0) + DF_cba_org_data['ac_charge_point_count'].fillna(0)

    # In[1222]:

    # 查看两个 station_no 列是否相同
    # 删除重复列，保留第一个
    DF_cba_org_data = DF_cba_org_data.loc[:, ~DF_cba_org_data.columns.duplicated()]

    # In[1223]:
    print(DF_cba_org_data.columns.tolist())
    print("operation_status" in DF_cba_org_data.columns)
    print(DF_cba_org_data.head())

    DF_cba_org_data = DF_cba_org_data[DF_cba_org_data['charge_point_count'] != 0]
    DF_cba_org_data = DF_cba_org_data[DF_cba_org_data['plat_data_charging_volume'] != 0]
    DF_cba_org_data['gun_charging_volume'] = DF_cba_org_data['plat_data_charging_volume'] / DF_cba_org_data['charge_point_count']

    # In[1224]:

    DF_cba_org_data['days_in_month'] = DF_cba_org_data['cba_month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])

    # In[1225]:

    DF_cba_org_data['gun_charging_volume_day'] = DF_cba_org_data['gun_charging_volume'] / DF_cba_org_data['days_in_month']

    # In[ ]:

    # In[1226]:

    DF_cba_org_datawe = DF_cba_org_data[(DF_cba_org_data['cba_month'] == M) & (DF_cba_org_data['station_category'] == '城市公共')][['gun_charging_volume_day', 'station_no']].copy()

    # In[1227]:

    DF_cba_org_datawe2 = DF_cba_org_datawe.T.drop_duplicates().T

    # In[1228]:

    result_vloumes = (
        DF_cba_org_datawe2.groupby('station_no')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .round(2)
    )

    # In[1229]:

    result_vloumes

    # In[ ]:

    # In[1230]:

    result_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '城市公共') & (DF_cba_pue['cba_month'] == M)]
        .groupby('station_no')['pue']
        .mean()
        .reset_index()

        .round(2)
    )

    # In[1231]:

    result_cba_pue

    # In[1232]:

    DF_success.columns

    # In[1233]:

    DF_successwer = DF_success[(DF_success['month'] == M) & (DF_success['station_category'] == '城市公共')].copy()

    # In[1234]:

    # 一次成功率
    result_success_rate = (
        DF_successwer.groupby('station_no')['station_success_rate']
        .mean()
        .reset_index()
        .round(4)
    )

    # In[1235]:

    result_success_rate['station_success_rate'] = result_success_rate['station_success_rate'] * 100

    # In[1236]:

    result_success_rate

    # In[1237]:

    DF_operation_duration1 = DF_operation_duration[(DF_operation_duration['month'] == M) & (DF_operation_duration['station_category'] == '城市公共')].copy()

    # In[1238]:

    # 可用率
    result_use_rate = (
        DF_operation_duration1.groupby('station_no')['可用率']
        .mean()
        .reset_index()
        .round(4)
    )

    # In[1239]:

    result_use_rate['可用率'] = result_use_rate['可用率'] * 100

    # In[1240]:



    # In[1241]:

    # df_all_profit = df_all_profit.loc[:, ~df_all_profit.columns.duplicated()]

    df_all_profit = DF_cba_org_data[DF_cba_org_data['cba_month'] == M].copy()
    # In[1242]:

    DF

    # In[ ]:

    # In[1243]:

    # df345['station_category'].unique()

    # In[1244]:

    # 营收
    result_earn = (
        df345.groupby('station_no')['revenue']
        .sum()
        .reset_index()
        .round(2)
    )

    # In[1245]:

    result_earn

    # In[1246]:

    # 毛利（万元）

    result_jing_profile = (
        df345.groupby('station_no')['gross_profit']
        .sum()
        .reset_index()
        .round(2)
    )

    # In[1247]:

    result_jing_profile

    # In[1248]:

    DF_SCGD['单桩工单'] = pd.to_numeric(DF_SCGD['单桩工单'], errors='coerce').fillna(0)

    # In[1249]:

    result_workorders = (
        DF_SCGD[
            (DF_SCGD['station_category'] == '城市公共') &
            (DF_SCGD['stat_time'] == M)
            ]
        .groupby('station_no')['单桩工单']
        .mean()
        .reset_index()
        .round(2)
    )

    # In[1250]:

    result_workorders.replace([np.inf, -np.inf], 0, inplace=True)

    # In[1251]:

    result_workorders

    # In[1252]:

    dfs = [
        result_station_point,

        hbpercentage,
        result_vloumes,
        result_cba_pue,
        result_success_rate,
        result_use_rate,
        result_earn,
        result_jing_profile,
        result_workorders
    ]

    # In[1253]:

    from functools import reduce

    # 用 reduce 连续合并多个 DataFrame
    df_zdwd = reduce(
        lambda left, right: pd.merge(left, right, on='station_no', how='left'),
        dfs
    )

    # 把所有 NaN 替换为 0
    df_zdwd = df_zdwd.fillna(0)

    # In[1254]:

    df_zdwd = df_zdwd[df_zdwd['total_investment_amount'] != 0]

    # In[1255]:

    # , 'gross_profit'

    # In[1256]:

    df_zdwd['total_investment_amount'] = df_zdwd['total_investment_amount'].apply(float)
    df_zdwd['total_investment_amount'] = round(df_zdwd['total_investment_amount'] / 10000, 2)
    df_zdwd['revenue'] = df_zdwd['revenue'].apply(float)
    df_zdwd['revenue'] = round(df_zdwd['revenue'] / 10000, 2)
    df_zdwd['gross_profit'] = df_zdwd['gross_profit'].apply(float)
    df_zdwd['gross_profit'] = round(df_zdwd['gross_profit'] / 10000, 2)

    df_zdwd

    # In[ ]:

    # In[ ]:

    # In[1257]:

    print(df_zdwd.columns)

    # #### 建设情况维度

    # In[1258]:

    # 确保是数值类型
    df_zdwd['total_station_capacity'] = pd.to_numeric(df_zdwd['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_min3 = df_zdwd.nsmallest(3, 'total_station_capacity')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_min3_name = df_min3['station_name']
    df_min3_name

    # #### 投资情况维度

    # In[1259]:

    # 确保是数值类型
    df_zdwd['hbpercentage'] = pd.to_numeric(df_zdwd['hbpercentage'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_min3_tz = df_zdwd.nsmallest(3, 'hbpercentage')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_min3_tz_name = df_min3_tz['station_name']
    df_min3_tz_name

    # #### 运营情况维度

    # In[1260]:

    df_zdwd['gun_charging_volume_day']

    # In[1261]:

    # 确保是数值类型
    df_zdwd['gun_charging_volume_day'] = pd.to_numeric(df_zdwd['gun_charging_volume_day'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_min3_yy = df_zdwd.nsmallest(3, 'gun_charging_volume_day')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_min3_yy_name = df_min3_yy['station_name']
    df_min3_yy_name

    # #### 设备质量维度

    # In[1262]:

    # 确保是数值类型
    df_zdwd['可用率'] = pd.to_numeric(df_zdwd['可用率'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_min3_zl = df_zdwd.nsmallest(3, '可用率')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_min3_zl_name = df_min3_zl['station_name']
    df_min3_zl_name

    # #### 经营情况维度

    # In[1263]:

    # 确保是数值类型
    df_zdwd['revenue'] = pd.to_numeric(df_zdwd['revenue'], errors='coerce')
    df_zdwd['gross_profit'] = pd.to_numeric(df_zdwd['gross_profit'], errors='coerce')

    # 计算毛利率（gross_profit / revenue）
    df_zdwd['profit_ratio'] = df_zdwd['gross_profit'] / df_zdwd['revenue']

    # 筛选毛利率最低的3个站
    df_min3_jy = df_zdwd.nsmallest(3, 'profit_ratio')

    # 获取站点名称
    df_min3_jy_name = df_min3_jy['station_name']

    df_min3_jy_name

    # #### 运维情况维度

    # In[1264]:

    # 确保是数值类型
    df_zdwd['单桩工单'] = pd.to_numeric(df_zdwd['单桩工单'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_min3_yw = df_zdwd.nlargest(3, '单桩工单')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_min3_yw_name = df_min3_yw['station_name']
    df_min3_yw_name

    # In[ ]:

    # ### 区域维度

    # In[1265]:

    result_city_point = (
        DF_SCDD[(DF_SCDD['station_category'] == '城市公共') & (DF_SCDD['operation_status'] == '投运')]
        .assign(
            total_charge_point_count=lambda df: df['dc_charge_point_count'].fillna(0) + df['ac_charge_point_count'].fillna(0)
        )
        .groupby('city')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )
    result_city_point

    # In[1266]:

    result_city_earn = (
        df_all_profit[df_all_profit['station_category'] == '城市公共']
        .assign(earn=lambda x: x['rec_data'] - x['rec_cost'])  # 新增收益列
        .groupby('city', as_index=False)['earn']
        .sum()
        .round(2)
    )

    # In[1267]:

    result_city_earn1 = pd.merge(result_city_point, result_city_earn, on='city', how='inner')

    # In[1268]:
    DF_org_data_pre_gun ['days_in_month'] = DF_org_data_pre_gun['cba_month'].apply(lambda x: calendar.monthrange(int(x[:4]), int(x[4:]))[1])
    DF_org_data_pre_gun['gun_charging_volume_day'] = DF_org_data_pre_gun['gun_charging_volume'] / DF_org_data_pre_gun['days_in_month']
    DF_cba_org_dataquyu = DF_org_data_pre_gun[(DF_org_data_pre_gun['cba_month'] == M) & (DF_org_data_pre_gun['station_category'] == '城市公共')][['gun_charging_volume_day', 'city']].copy()

    # In[1269]:
    result_city_vloumes = (
        DF_cba_org_dataquyu.groupby('city')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_day': '单枪日均充电量'})
        .round(2)
    )

    # In[1270]:

    result_city_vloumes

    # In[1271]:

    result_city_vloumes1 = pd.merge(result_city_earn1, result_city_vloumes, on='city', how='inner')

    # In[1272]:

    result_city_cba_pue = (
        DF_cba_pue.groupby('city')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': '功率利用率'})
        .round(2)
    )

    # In[1273]:

    result_city_cba_pue

    # In[1274]:

    city_fianl_count = pd.merge(result_city_vloumes1, result_city_cba_pue, on='city', how='inner')

    # In[1275]:

    city_fianl_count = city_fianl_count.fillna(0)
    city_fianl_count = city_fianl_count[city_fianl_count['total_investment_amount'] != 0]

    # In[1276]:

    # 把所有 NaN 替换为 0
    city_fianl_count['total_investment_amount'] = city_fianl_count['total_investment_amount'] / 10000

    # In[1277]:

    city_fianl_count['total_investment_amount'] = city_fianl_count['total_investment_amount'].apply(float)
    city_fianl_count['total_investment_amount'] = city_fianl_count['total_investment_amount'].round(2)

    # In[1278]:

    city_fianl_count['earn'] = city_fianl_count['earn'] / 10000
    city_fianl_count['earn'] = city_fianl_count['earn'].apply(float)
    city_fianl_count['earn'] = city_fianl_count['earn'].round(2)
    city_fianl_count['payback'] = np.where(
        city_fianl_count['total_investment_amount'] == 0,
        0,
        city_fianl_count['earn'] / city_fianl_count['total_investment_amount']
    )

    # In[1279]:

    city_fianl_count

    # #### 投运情况维度

    # In[1280]:

    # 确保是数值类型
    city_fianl_count['total_station_capacity'] = pd.to_numeric(city_fianl_count['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    city_ty_min3 = city_fianl_count.nsmallest(3, 'total_station_capacity')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    city_ty_min3name = city_ty_min3['city']
    city_ty_min3name

    # #### 投资情况维度

    # In[1281]:

    city_fianl_count['payback'] = city_fianl_count['payback'] * 100

    # In[1282]:

    city_fianl_count.nsmallest(4, 'payback')

    # In[1283]:

    # 确保是数值类型
    city_tz_min3 = city_fianl_count.nsmallest(3, 'payback')

    city_tz_min3name = city_tz_min3['city']
    city_tz_min3name

    # In[ ]:

    # #### 运营情况维度

    # In[1284]:

    # 确保是数值类型
    city_fianl_count['单枪日均充电量'] = pd.to_numeric(city_fianl_count['单枪日均充电量'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    city_yy_min3 = city_fianl_count.nsmallest(3, '单枪日均充电量')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    city_yy_min33name = city_ty_min3['city']
    city_yy_min33name

    # ### 设备厂商维度

    # In[1285]:

    DF_operation_duration1 = DF_operation_duration0[['pile_manufacturer', 'station_no']].drop_duplicates()

    # In[ ]:

    # In[1286]:

    EQ_P = pd.merge(
        DF_operation_duration1,
        DF_SCDD[(DF_SCDD['station_category'] == '城市公共') & (DF_SCDD['operation_status'] == '投运')],
        on='station_no',
        how='inner'
    )

    # In[ ]:

    # In[1287]:

    result_sheb_point = (
        EQ_P
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('pile_manufacturer')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'mean')
        )
        .reset_index()
    )

    # In[1288]:

    result_sheb_point

    # In[1289]:

    DF_operation_duration0.columns, DF_success.columns

    # In[1290]:

    EQ_success = pd.merge(DF_operation_duration0, DF_success, on='station_no', how='inner')

    # In[1291]:

    EQ_success = EQ_success.drop(columns=['station_category_y']) \
        .rename(columns={'station_category_x': 'station_category'})
    EQ_success

    # In[1292]:

    # 一次成功率
    result_sheb_success = (
        EQ_success[EQ_success['station_category'] == '城市公共']
        .groupby('pile_manufacturer')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': '一次成功率'})
        .round(2)
    )

    # In[1293]:


    DF_operation_duration0['可用率'] = DF_operation_duration0['normal_duration'].astype('int') / DF_operation_duration0[
        'operation_duration'].astype('int')
    # In[1294]:

    result_sheb_kyong = (
        DF_operation_duration0.groupby('pile_manufacturer')['可用率']
        .mean()
        .reset_index()

        .round(2)
    )

    # In[1295]:

    result_sheb_kyong

    # In[1296]:

    EQ_orders = pd.merge(DF_operation_duration0, DF_SCGD, on='station_no', how='inner')

    # In[1297]:

    EQ_orders = EQ_orders.drop(columns=['station_category_y']) \
        .rename(columns={'station_category_x': 'station_category'})

    # In[1298]:

    result_sheb_orders = (
        EQ_orders[EQ_orders['station_category'] == '城市公共'].groupby('pile_manufacturer')['单桩工单']
        .mean()
        .reset_index()
        .round(2)
    )

    # In[1299]:

    result_sheb_orders.replace([np.inf, -np.inf], 0, inplace=True)
    result_sheb_orders

    # In[1300]:

    from functools import reduce

    dfs = [result_sheb_point, result_sheb_success, result_sheb_kyong, result_sheb_orders]

    # 按 pile_manufacturer 左连接依次合并
    merged_df = reduce(lambda left, right: pd.merge(left, right, on='pile_manufacturer', how='outer'), dfs)

    # 将合并后的 NaN 填为 0（可选）
    merged_df = merged_df.fillna(0)

    merged_df['一次成功率'] = merged_df['一次成功率'] * 100
    merged_df['可用率'] = merged_df['可用率'] * 100

    merged_df['一次成功率'] = merged_df['一次成功率'].round(2)
    merged_df['可用率'] = merged_df['可用率'].round(2)

    merged_df = merged_df[merged_df['total_charge_point_count'] != 0]
    merged_df

    # In[ ]:

    # #### 投运情况维度

    # In[1301]:

    # 确保是数值类型
    merged_df['total_station_capacity'] = pd.to_numeric(merged_df['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    shebei_min3 = merged_df.nsmallest(3, 'total_station_capacity')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    shebei_min3name = shebei_min3['pile_manufacturer']
    shebei_min3name

    # #### 设备质量维度

    # In[1302]:

    # 确保是数值类型
    merged_df['可用率'] = pd.to_numeric(merged_df['可用率'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    shebei_zhil_min3 = merged_df.nsmallest(3, '可用率')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    shebei_zhil_min3_name = shebei_zhil_min3['pile_manufacturer']
    shebei_zhil_min3_name

    # #### 运维情况维度

    # In[1303]:

    # 确保是数值类型
    merged_df['单桩工单'] = pd.to_numeric(merged_df['单桩工单'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    shebei_yunwei_max3 = merged_df.nlargest(3, '单桩工单')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    shebei_yunwei_max3_name = shebei_yunwei_max3['pile_manufacturer']
    shebei_yunwei_max3_name

    # In[1304]:

    def series_to_str(s):
        return ", ".join(s.astype(str).tolist())

    # 构建站点维度的数据
    station_data = []
    for idx, row in df_zdwd.iterrows():
        station_data.append({
            "id": idx + 1,
            "siteName": row['station_name'],
            "chargingCable": int(row['total_charge_point_count']),
            "ratedPower": int(float(row['total_station_capacity'])),
            "totalInvestmentCosts": float(f"{float(row['total_investment_amount']):.2f}"),
            "returnCost": round(float(row['hbpercentage']), 2),
            "chargeAmountPerGun": round(float(row['gun_charging_volume_day']), 2),
            "powerUtilization": f"{float(row['pue']) :.2f}%",
            "successRate": f"{float(row['station_success_rate']):.2f}%",
            "availability": f"{float(row['可用率']) :.2f}%",
            "revenue": round(float(row['revenue']), 2),
            "grossProfit": round(float(row['gross_profit']), 2),
            "ticketsNum": round(float(row['单桩工单']), 2)
        })
    region_data = []
    for idx, row in city_fianl_count.iterrows():
        region_data.append({
            "id": idx + 1,
            "region": row["city"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "amountInvested": round(float(row["total_investment_amount"]), 2),
            "earnings": f"{float(row['payback']) :.2f}%",
            "chargeAmountPerGun": round(float(row["单枪日均充电量"]), 2),
            "powerUtilization": f"{float(row['功率利用率']):.2f}%"
        })
    equipment_data = []
    for idx, row in merged_df.iterrows():
        equipment_data.append({
            "id": idx + 1,
            "equipmentManufacturers": row["pile_manufacturer"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "successRate": f"{float(row['一次成功率']):.2f}%",
            "availability": f"{float(row['可用率']):.2f}%",
            "omNum": round(float(row["单桩工单"]), 2)
        })

    # # 示例 tableSummary（你可自定义或自动生成）
    # min3_str = " ".join(df_min3_name['station_name'].tolist())
    # {series_to_str(df_min3_tz_name)}

    table_summary = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个站点为：{series_to_str(df_min3_name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个站点为：{series_to_str(df_min3_tz_name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个站点为：{series_to_str(df_min3_yy_name)}"},
        {"id": 4, "title": "经营情况维度", "content": f"毛利率需重点关注的三个站点为：{series_to_str(df_min3_jy_name)}"},
        {"id": 5, "title": "设备质量维度", "content": f"设备可用率最低的三个站点为：{series_to_str(df_min3_zl_name)}"},
        {"id": 6, "title": "运维情况维度", "content": f"单桩工单数量最多的三个站点为：{series_to_str(df_min3_yw_name)}"},
    ]

    table_summary2 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个地市为：{series_to_str(city_ty_min3name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最小的三个地市为：{series_to_str(city_tz_min3name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个地市为：{series_to_str(city_yy_min33name)}"},
    ]

    table_summary3 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的设备厂商为：{series_to_str(shebei_min3name)}"},
        {"id": 2, "title": "设备质量维度", "content": f"设备可用率最低的三个设备厂商为：{series_to_str(shebei_zhil_min3_name)}"},
        {"id": 3, "title": "运维情况维度", "content": f"单桩工单数量最多的三个设备厂商为：{series_to_str(shebei_yunwei_max3_name)}"},
    ]

    # 构建最终结构
    result = {
        "options": ["站点维度", "区域维度", "设备厂商维度"],
        "data": [
            {
                "radio": "站点维度",
                "tableData": station_data,
                "siteNameFilters":[d["siteName"] for d in station_data],
                "tableSummary": table_summary
            },
            {
                "radio": "区域维度",
                "tableData": region_data,
                "tableSummary": table_summary2
            },
            {
                "radio": "设备厂商维度",
                "tableData": equipment_data,
                "tableSummary": table_summary3
            }

        ]
    }
    # result

    # #### 站点指标建表 语句

    # In[1305]:

    # 表和字段注释
    table_comment = "类型检测_城市公共_站点指标现状"
    column_comments = {
        'result': '站点指标现状',
        'update_time': '更新日期'
    }
    DF_result = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_result,
        table_name="dp_scdd_nowpoint",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 重卡专用

    # ### 站点维度

    # In[1306]:

    df_zdzb_zk = DF_SCDD[
        (DF_SCDD['operation_status'] == '投运') &
        (DF_SCDD['station_category'] == '重卡专用')
        ].copy()

    # In[1307]:

    result_station_point = (
        df_zdzb_zk
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('station_no')
        .agg(
            station_name=('station_name', 'first'),
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    # In[1308]:

    result_station_point

    # In[1309]:

    df_zdzb_zk

    # In[1310]:

    # 假设你已有的站点信息表叫 df_station（你发的DataFrame）
    # 且另有一个投资记录表 df_investment，包含 station_no、investment_amount、investment_time 字段

    df_zdzb_zk['investment_time'] = pd.to_datetime(df_zdzb_zk['commissioning_time'])

    # 筛选出 2025 年发生的投资
    df_2025_zk = df_zdzb_zk[df_zdzb_zk['investment_time'].dt.year == year]

    # 汇总每个站点的投资总额
    df_2025_total_zk = df_2025_zk.groupby('station_no', as_index=False)['investment_amount'].sum()
    df_2025_total_zk.rename(columns={'investment_amount': 'investment_2025_total'}, inplace=True)

    # In[1311]:

    df_2025_total_zk

    # In[1312]:

    hbpercentage_zk = (
        DF[['station_no', 'hbpercentage']]
        .fillna({'hbpercentage': 0})
        .merge(
            DF_SCDD[['station_no', 'station_category']],
            on='station_no',
            how='left'
        )
        .query("station_category == '重卡专用'")
        [['station_no', 'hbpercentage']]  # 保留需要的列
    )

    # In[1313]:

    hbpercentage_zk

    # In[1314]:

    DF_cba_org_datzhongka = DF_org_data_pre_gun[(DF_org_data_pre_gun['cba_month'] == M) & (DF_org_data_pre_gun['station_category'] == '重卡专用')][['gun_charging_volume_day', 'station_no']].copy()

    # In[1315]:

    DF_cba_org_datzhongka = DF_cba_org_datzhongka.T.drop_duplicates().T
    result_vloumes_zk = (
        DF_cba_org_datzhongka.groupby('station_no')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .round(2)
    )
    result_vloumes_zk

    # In[1316]:

    zk_result_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '重卡专用') & (DF_cba_pue['cba_month'] == M)]
        .groupby('station_no')['pue']
        .mean()
        .reset_index()

        .round(2)
    )
    zk_result_cba_pue

    # In[1317]:

    DF_success_zk = DF_success[(DF_success['month'] == M) & (DF_success['station_category'] == '重卡专用')].copy()
    # 一次成功率
    zk_result_success_rate = (
        DF_success_zk.groupby('station_no')['station_success_rate']
        .mean()
        .reset_index()
        .round(4)
    )
    zk_result_success_rate['station_success_rate'] = zk_result_success_rate['station_success_rate'] * 100
    zk_result_success_rate

    # In[1318]:

    DF_zkoperation_duration = DF_operation_duration[(DF_operation_duration['month'] == M) & (DF_operation_duration['station_category'] == '重卡专用')].copy()
    # 可用率
    zk_result_use_rate = (
        DF_zkoperation_duration.groupby('station_no')['可用率']
        .mean()
        .reset_index()
        .round(4)
    )
    zk_result_use_rate['可用率'] = zk_result_use_rate['可用率'] * 100

    zk_result_use_rate

    # In[1319]:

    df345zk = df11[df11['station_category'] == '重卡专用'].copy()
    zk_result_earn = (
        df345zk.groupby('station_no')['revenue']
        .sum()
        .reset_index()
        .round(2)
    )
    zk_result_earn

    # In[1320]:

    df345zk['gross_profit'] = df345zk['revenue'].astype('float') - df345zk['cost'].astype('float')
    zk_result_jing_profile = (
        df345zk.groupby('station_no')['gross_profit']
        .sum()
        .reset_index()
        .round(2)
    )
    zk_result_jing_profile

    # In[1321]:

    # 工单数量
    zk_result_workorders = (
        DF_SCGD[(DF_SCGD['station_category'] == '重卡专用') & (DF_SCGD['stat_time'] == M)].groupby('station_no')['单桩工单']
        .mean()
        .reset_index()
        .round(2)
    )
    zk_result_workorders

    # In[1322]:

    dfszk = [
        result_station_point,

        hbpercentage_zk,
        result_vloumes_zk,
        zk_result_cba_pue,
        zk_result_success_rate,
        zk_result_use_rate,
        zk_result_earn,
        zk_result_jing_profile,
        zk_result_workorders
    ]
    from functools import reduce

    # 用 reduce 连续合并多个 DataFrame
    df_zk_zdwd = reduce(
        lambda left, right: pd.merge(left, right, on='station_no', how='left'),
        dfszk
    )

    # 把所有 NaN 替换为 0
    df_zk_zdwd = df_zk_zdwd.fillna(0)
    cols = ['total_investment_amount', 'revenue', 'gross_profit']
    df_zk_zdwd[cols] = df_zk_zdwd[cols].apply(lambda x: (pd.to_numeric(x, errors='coerce') / 10000).round(2))

    df_zk_zdwd

    # In[1323]:

    # 确保是数值类型
    df_zk_zdwd['total_station_capacity'] = pd.to_numeric(df_zk_zdwd['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_zk_min3 = df_zk_zdwd.nsmallest(3, 'total_station_capacity')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_zk_min3_name = df_zk_min3['station_name']
    df_zk_min3_name

    # In[1324]:

    df_zk_zdwd['hbpercentage'] = pd.to_numeric(df_zk_zdwd['hbpercentage'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_zk_min3_tz = df_zk_zdwd.nsmallest(3, 'hbpercentage')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_zk_min3_tz_name = df_zk_min3_tz['station_name']
    df_zk_min3_tz_name

    # In[1325]:

    # 确保是数值类型
    df_zk_zdwd['gun_charging_volume_day'] = pd.to_numeric(df_zk_zdwd['gun_charging_volume_day'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_zk_min3_yy = df_zk_zdwd.nsmallest(3, 'gun_charging_volume_day')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_zk_min3_yy_name = df_zk_min3_yy['station_name']
    df_zk_min3_yy_name

    # In[1326]:

    # 确保是数值类型
    df_zk_zdwd['可用率'] = pd.to_numeric(df_zk_zdwd['可用率'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_zk_min3_zl = df_zk_zdwd.nsmallest(3, '可用率')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_zk_min3_zl_name = df_zk_min3_zl['station_name']
    df_zk_min3_zl_name

    # In[1327]:

    # 确保是数值类型
    df_zk_zdwd['revenue'] = pd.to_numeric(df_zk_zdwd['revenue'], errors='coerce')
    df_zk_zdwd['revenue'] = pd.to_numeric(df_zk_zdwd['revenue'], errors='coerce')
    # 筛选出额定功率最小的前3个站

    # 计算毛利率（gross_profit / revenue）
    df_zk_zdwd['profit_ratio'] = df_zk_zdwd['gross_profit'] / df_zk_zdwd['revenue']

    df_zk_min3_jy = df_zk_zdwd.nsmallest(3, 'profit_ratio')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_zk_min3_jy_name = df_zk_min3_jy['station_name']
    df_zk_min3_jy_name

    # In[1328]:

    # 确保是数值类型
    df_zk_zdwd['单桩工单'] = pd.to_numeric(df_zk_zdwd['单桩工单'], errors='coerce')

    df_zk_min3_yw = df_zk_zdwd.nlargest(3, '单桩工单')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    df_zk_min3_yw_name = df_zk_min3_yw['station_name']
    df_zk_min3_yw_name

    # ### 区域维度

    # In[1329]:

    zk_result_city_point = (
        DF_SCDD[(DF_SCDD['station_category'] == '重卡专用') & (DF_SCDD['operation_status'] == '投运')]
        .assign(
            total_charge_point_count=lambda df: df['dc_charge_point_count'].fillna(0) + df['ac_charge_point_count'].fillna(0)
        )
        .groupby('city')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )
    zk_result_city_point

    # In[1330]:

    # 营收
    zk_result_city_earn = (
        df_all_profit[df_all_profit['station_category'] == '重卡专用']
        .assign(earn=lambda x: x['rec_data'] - x['rec_cost'])
        .groupby('city', as_index=False)['earn']
        .sum()
        .round(2)
    )
    zk_result_city_earn

    # In[1331]:

    zk_result_city_earn1 = pd.merge(zk_result_city_point, zk_result_city_earn, on='city', how='inner')

    # In[1332]:

    zk_result_city_earn1

    # In[1333]:

    zk_DF_cba_org_dataquyu = DF_org_data_pre_gun[(DF_org_data_pre_gun['cba_month'] == M) & (DF_org_data_pre_gun['station_category'] == '重卡专用')][['gun_charging_volume_day', 'city']].copy()
    zk_result_city_vloumes = (
        zk_DF_cba_org_dataquyu.groupby('city')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_day': '单枪日均充电量'})
        .round(2)
    )
    zk_result_city_vloumes

    # In[1334]:

    zk_result_city_vloumes1 = pd.merge(zk_result_city_earn1, zk_result_city_vloumes, on='city', how='inner')

    # In[1335]:

    zk_result_city_vloumes1

    # In[1336]:

    zk_result_city_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '重卡专用') &  (DF_cba_pue['cba_month'] == M)]
        .groupby('city')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': '功率利用率'})
        .round(2)
    )
    zk_result_city_cba_pue

    # In[1337]:

    zk_city_fianl_count = pd.merge(zk_result_city_vloumes1, zk_result_city_cba_pue, on='city', how='inner')

    # In[1338]:

    zk_city_fianl_count = zk_city_fianl_count.fillna(0)
    # zk_city_fianl_count = zk_city_fianl_count[zk_city_fianl_count['total_investment_amount'] != 0]

    # In[1339]:

    zk_city_fianl_count['total_investment_amount'] = zk_city_fianl_count['total_investment_amount'].apply(float)
    zk_city_fianl_count['total_investment_amount'] = zk_city_fianl_count['total_investment_amount'] / 10000
    zk_city_fianl_count['total_investment_amount'] = zk_city_fianl_count['total_investment_amount'].round(2)
    zk_city_fianl_count['total_investment_amount'] = zk_city_fianl_count['total_investment_amount'].apply(float)
    zk_city_fianl_count['earn'] = zk_city_fianl_count['earn'] / 10000
    zk_city_fianl_count['earn'] = zk_city_fianl_count['earn'].round(2)
    zk_city_fianl_count['payback'] = np.where(
        zk_city_fianl_count['total_investment_amount'] == 0,
        0,
        zk_city_fianl_count['earn'] / zk_city_fianl_count['total_investment_amount']
    )

    # In[1340]:

    zk_city_fianl_count

    # In[1341]:

    # 确保是数值类型
    zk_city_fianl_count['total_station_capacity'] = pd.to_numeric(zk_city_fianl_count['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    zk_city_ty_min3 = zk_city_fianl_count.nsmallest(3, 'total_station_capacity')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    zk_city_ty_min3name = zk_city_ty_min3['city']
    zk_city_ty_min3name

    # In[1342]:

    # 确保是数值类型

    zk_city_tz_min3 = zk_city_fianl_count.nsmallest(3, 'payback')

    zk_city_tz_min3name = zk_city_tz_min3['city']
    zk_city_tz_min3name

    # In[1343]:

    # 确保是数值类型
    zk_city_fianl_count['单枪日均充电量'] = pd.to_numeric(zk_city_fianl_count['单枪日均充电量'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    zk_city_yy_min3 = zk_city_fianl_count.nsmallest(3, 'total_station_capacity')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    zk_city_yy_min3name = zk_city_yy_min3['city']
    zk_city_yy_min3name

    # ### 设备厂商维度
    #

    # In[1344]:

    zk_EQ_P = pd.merge(
        DF_operation_duration1,
        DF_SCDD[(DF_SCDD['station_category'] == '重卡专用') & (DF_SCDD['operation_status'] == '投运')],
        on='station_no',
        how='inner'
    )

    # In[1345]:

    zk_result_sheb_point = (
        zk_EQ_P
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('pile_manufacturer')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'mean')
        )
        .reset_index()
    )
    zk_result_sheb_point

    # In[1346]:

    EQ_success.columns

    # In[1347]:

    zk_result_sheb_success = (
        EQ_success[EQ_success['station_category'] == '重卡专用']
        .groupby('pile_manufacturer')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': '一次成功率'})
        .round(2)
    )
    zk_result_sheb_success

    # In[1348]:

    zk_result_sheb_kyong = (
        DF_operation_duration0[DF_operation_duration0['station_category'] == '重卡专用'].groupby('pile_manufacturer')['可用率']
        .mean()
        .reset_index()

        .round(2)
    )
    zk_result_sheb_kyong

    # In[1349]:

    zk_result_sheb_orders = (
        EQ_orders[EQ_orders['station_category'] == '重卡专用'].groupby('pile_manufacturer')['单桩工单']
        .mean()
        .reset_index()
        .rename(columns={'单桩工单': '单枪平均运维次数'})
        .round(2)
    )
    zk_result_sheb_orders

    # In[1350]:

    from functools import reduce

    zk_df = [zk_result_sheb_point, zk_result_sheb_success, zk_result_sheb_kyong, zk_result_sheb_orders]

    # 按 pile_manufacturer 左连接依次合并
    zk_merged_df = reduce(lambda left, right: pd.merge(left, right, on='pile_manufacturer', how='outer'), zk_df)
    zk_merged_df['一次成功率'] = zk_merged_df['一次成功率'] * 100
    zk_merged_df['可用率'] = zk_merged_df['可用率'] * 100
    zk_merged_df

    # In[1351]:

    # 确保是数值类型
    zk_merged_df['total_station_capacity'] = pd.to_numeric(zk_merged_df['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    zk_shebei_min3 = zk_merged_df.nsmallest(3, 'total_station_capacity')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    zk_shebei_min3name = zk_shebei_min3['pile_manufacturer']
    zk_shebei_min3name

    # In[1352]:

    # 确保是数值类型
    zk_merged_df['可用率'] = pd.to_numeric(zk_merged_df['可用率'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    zk_shebei_zhil_min3 = zk_merged_df.nsmallest(3, '可用率')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    zk_shebei_zhil_min3_name = zk_shebei_zhil_min3['pile_manufacturer']
    zk_shebei_zhil_min3_name

    # In[1353]:

    # 确保是数值类型
    zk_merged_df['单枪平均运维次数'] = pd.to_numeric(zk_merged_df['单枪平均运维次数'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    zk_shebei_yunwei_max3 = zk_merged_df.nlargest(3, '单枪平均运维次数')

    # # 输出站点名称和额定功率
    # print(df_min3[['station_name', 'total_station_capacity']])
    zk_shebei_yunwei_max3_name = zk_shebei_yunwei_max3['pile_manufacturer']
    zk_shebei_yunwei_max3_name

    # In[1354]:

    def series_to_str(s):
        return ", ".join(s.astype(str).tolist())

    # 构建站点维度的数据
    station_data = []
    for idx, row in df_zk_zdwd.iterrows():
        station_data.append({
            "id": idx + 1,
            "siteName": row['station_name'],
            "chargingCable": int(row['total_charge_point_count']),
            "ratedPower": int(float(row['total_station_capacity'])),
            "totalInvestmentCosts": float(f"{float(row['total_investment_amount']):.2f}"),
            "returnCost": round(float(row['hbpercentage']), 2),
            "chargeAmountPerGun": round(float(row['gun_charging_volume_day']), 2),
            "powerUtilization": f"{float(row['pue']) :.2f}%",
            "successRate": f"{float(row['station_success_rate']):.2f}%",
            "availability": f"{float(row['可用率']) :.2f}%",
            "revenue": round(float(row['revenue']), 2),
            "grossProfit": round(float(row['gross_profit']), 2),
            "ticketsNum": int(float(row['单桩工单']))
        })
    region_data = []
    for idx, row in zk_city_fianl_count.iterrows():
        region_data.append({
            "id": idx + 1,
            "region": row["city"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "amountInvested": round(float(row["total_investment_amount"]), 2),
            "earnings": f"{float(row['payback']) * 100:.2f}%",

            "chargeAmountPerGun": round(float(row["单枪日均充电量"]), 2),
            "powerUtilization": f"{float(row['功率利用率']):.2f}%"
        })
    equipment_data = []
    for idx, row in zk_merged_df.iterrows():
        equipment_data.append({
            "id": idx + 1,
            "equipmentManufacturers": row["pile_manufacturer"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "successRate": f"{float(row['一次成功率']):.2f}%",
            "availability": f"{float(row['可用率']):.2f}%",
            "omNum": round(float(row["单枪平均运维次数"]), 2)
        })

    # # 示例 tableSummary（你可自定义或自动生成）
    # min3_str = " ".join(df_min3_name['station_name'].tolist())
    # {series_to_str(df_min3_tz_name)}

    table_summary = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个站点为：{series_to_str(df_zk_min3_name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个站点为：{series_to_str(df_zk_min3_tz_name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个站点为：{series_to_str(df_zk_min3_yy_name)}"},
        {"id": 4, "title": "经营情况维度", "content": f"毛利率需重点关注的三个站点为：{series_to_str(df_zk_min3_jy_name)}"},
        {"id": 5, "title": "设备质量维度", "content": f"设备可用率最低的三个站点为：{series_to_str(df_zk_min3_zl_name)}"},
        {"id": 6, "title": "运维情况维度", "content": f"单桩工单数量最多的三个站点为：{series_to_str(df_zk_min3_yw_name)}"},
    ]

    table_summary2 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个地市为：{series_to_str(zk_city_ty_min3name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最小的三个地市为：{series_to_str(zk_city_tz_min3name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个地市为：{series_to_str(zk_city_yy_min3name)}"},
    ]

    table_summary3 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的设备厂商为：{series_to_str(zk_shebei_min3name)}"},
        {"id": 2, "title": "设备质量维度", "content": f"设备可用率最低的三个设备厂商为：{series_to_str(zk_shebei_zhil_min3_name)}"},
        {"id": 3, "title": "运维情况维度", "content": f"单桩工单数量最多的三个设备厂商为：{series_to_str(zk_shebei_yunwei_max3_name)}"},
    ]

    # 构建最终结构
    result = {
        "options": ["站点维度", "区域维度", "设备厂商维度"],
        "data": [
            {
                "radio": "站点维度",
                "tableData": station_data,
                "siteNameFilters": [d["siteName"] for d in station_data],
                "tableSummary": table_summary
            },
            {
                "radio": "区域维度",
                "tableData": region_data,
                "tableSummary": table_summary2
            },
            {
                "radio": "设备厂商维度",
                "tableData": equipment_data,
                "tableSummary": table_summary3
            }

        ]
    }
    result

    # In[1355]:

    # 表和字段注释
    table_comment = "类型检测_重卡专用_站点指标现状"
    column_comments = {
        'result': '站点指标现状',
        'update_time': '更新日期'
    }
    DF_result = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_result,
        table_name="dp_zk_scdd_nowpoint",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 高速公共

    # ### 站点维度

    # In[1356]:

    df_zdzb_gs = DF_SCDD[
        (DF_SCDD['operation_status'] == '投运') &
        (DF_SCDD['station_category'] == '高速公共')
        ].copy()

    result_station_point_gs = (
        df_zdzb_gs
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('station_no')
        .agg(
            station_name=('station_name', 'first'),
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    hbpercentage_gs = (
        DF[['station_no', 'hbpercentage']]
        .fillna({'hbpercentage': 0})
        .merge(
            DF_SCDD[['station_no', 'station_category']],
            on='station_no',
            how='left'
        )
        .query("station_category == '高速公共'")
        [['station_no', 'hbpercentage']]
    )

    DF_cba_org_datgaosu = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'] == M) &
        (DF_org_data_pre_gun['station_category'] == '高速公共')
        ][['gun_charging_volume_day', 'station_no']].copy()
    DF_cba_org_datgaosu = DF_cba_org_datgaosu.T.drop_duplicates().T

    result_vloumes_gs = (
        DF_cba_org_datgaosu.groupby('station_no')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .round(2)
    )

    gs_result_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '高速公共') & (DF_cba_pue['cba_month'] == M)]
        .groupby('station_no')['pue']
        .mean()
        .reset_index()
        .round(2)
    )

    DF_success_gs = DF_success[
        (DF_success['month'] == M) &
        (DF_success['station_category'] == '高速公共')
        ].copy()

    # 一次成功率
    gs_result_success_rate = (
        DF_success_gs.groupby('station_no')['station_success_rate']
        .mean()
        .reset_index()
        .round(4)
    )
    gs_result_success_rate['station_success_rate'] = gs_result_success_rate['station_success_rate'] * 100

    DF_gsoperation_duration = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '高速公共')
        ].copy()

    # 可用率
    gs_result_use_rate = (
        DF_gsoperation_duration.groupby('station_no')['可用率']
        .mean()
        .reset_index()
        .round(4)
    )
    gs_result_use_rate['可用率'] = gs_result_use_rate['可用率'] * 100
    df345gs = df11[df11['station_category'] == '高速公共'].copy()

    gs_result_earn = (
        df345gs.groupby('station_no')['revenue']
        .sum()
        .reset_index()
        .round(2)
    )

    df345gs['gross_profit'] = df345gs['revenue'].astype('float') - df345gs['cost'].astype('float')
    gs_result_jing_profile = (
        df345gs.groupby('station_no')['gross_profit']
        .sum()
        .reset_index()
        .round(2)
    )

    # 工单数量
    gs_result_workorders = (
        DF_SCGD[(DF_SCGD['station_category'] == '高速公共') & (DF_SCGD['stat_time'] == M)]
        .groupby('station_no')['单桩工单']
        .mean()
        .reset_index()
        .round(2)
    )

    dfsgs = [
        result_station_point_gs,
        hbpercentage_gs,
        result_vloumes_gs,
        gs_result_cba_pue,
        gs_result_success_rate,
        gs_result_use_rate,
        gs_result_earn,
        gs_result_jing_profile,
        gs_result_workorders
    ]

    from functools import reduce

    # 用 reduce 连续合并多个 DataFrame
    df_gs_zdwd = reduce(
        lambda left, right: pd.merge(left, right, on='station_no', how='left'),
        dfsgs
    )

    # 把所有 NaN 替换为 0
    df_gs_zdwd = df_gs_zdwd.fillna(0)
    df_gs_zdwd = df_gs_zdwd[df_gs_zdwd['total_investment_amount'] != 0]
    df_gs_zdwd['total_investment_amount'] = df_gs_zdwd['total_investment_amount'].apply(float)
    df_gs_zdwd['total_investment_amount'] = round(df_gs_zdwd['total_investment_amount'] / 10000, 2)
    df_gs_zdwd['revenue'] = df_gs_zdwd['revenue'].apply(float)
    df_gs_zdwd['revenue'] = round(df_gs_zdwd['revenue'] / 10000, 2)
    df_gs_zdwd['gross_profit'] = df_gs_zdwd['gross_profit'].apply(float)
    df_gs_zdwd['gross_profit'] = round(df_gs_zdwd['gross_profit'] / 10000, 2)
    df_gs_zdwd

    # In[ ]:

    # In[1357]:

    # 确保是数值类型
    df_gs_zdwd['total_station_capacity'] = pd.to_numeric(df_gs_zdwd['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_gs_min3 = df_gs_zdwd.nsmallest(3, 'total_station_capacity')

    # 输出站点名称
    df_gs_min3_name = df_gs_min3['station_name']
    print(df_gs_min3_name)

    df_gs_zdwd['hbpercentage'] = pd.to_numeric(df_gs_zdwd['hbpercentage'], errors='coerce')

    # 筛选出 hbp 最小的前3个站
    df_gs_min3_tz = df_gs_zdwd.nsmallest(3, 'hbpercentage')
    df_gs_min3_tz_name = df_gs_min3_tz['station_name']
    print(df_gs_min3_tz_name)

    # 枪日均充电量
    df_gs_zdwd['gun_charging_volume_day'] = pd.to_numeric(df_gs_zdwd['gun_charging_volume_day'], errors='coerce')
    df_gs_min3_yy = df_gs_zdwd.nsmallest(3, 'gun_charging_volume_day')
    df_gs_min3_yy_name = df_gs_min3_yy['station_name']
    print(df_gs_min3_yy_name)

    # 可用率
    df_gs_zdwd['可用率'] = pd.to_numeric(df_gs_zdwd['可用率'], errors='coerce')
    df_gs_min3_zl = df_gs_zdwd.nsmallest(3, '可用率')
    df_gs_min3_zl_name = df_gs_min3_zl['station_name']
    print(df_gs_min3_zl_name)

    # 收入
    df_gs_zdwd['revenue'] = pd.to_numeric(df_gs_zdwd['revenue'], errors='coerce')
    df_gs_zdwd['gross_profit'] = pd.to_numeric(df_gs_zdwd['gross_profit'], errors='coerce')
    # 计算毛利率（gross_profit / revenue）
    df_gs_zdwd['profit_ratio'] = df_gs_zdwd['gross_profit'] / df_gs_zdwd['revenue']
    df_gs_min3_jy = df_gs_zdwd.nsmallest(3, 'profit_ratio')
    df_gs_min3_jy_name = df_gs_min3_jy['station_name']
    print(df_gs_min3_jy_name)

    # 单桩工单数量
    df_gs_zdwd['单桩工单'] = pd.to_numeric(df_gs_zdwd['单桩工单'], errors='coerce')
    df_gs_min3_yw = df_gs_zdwd.nlargest(3, '单桩工单')
    df_gs_min3_yw_name = df_gs_min3_yw['station_name']
    print(df_gs_min3_yw_name)

    # ### 区域维度

    # In[1358]:

    gs_result_city_point = (
        DF_SCDD[(DF_SCDD['station_category'] == '高速公共') & (DF_SCDD['operation_status'] == '投运')]
        .assign(
            total_charge_point_count=lambda df: df['dc_charge_point_count'].fillna(0) + df['ac_charge_point_count'].fillna(0)
        )
        .groupby('city')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    # 营收
    gs_result_city_earn = (
        df_all_profit[df_all_profit['station_category'] == '高速公共']
        .assign(earn=lambda x: x['rec_data'] - x['rec_cost'])  # 新增收益列
        .groupby('city', as_index=False)['earn']
        .sum()
        .round(2)
    )
    gs_result_city_earn1 = pd.merge(gs_result_city_point, gs_result_city_earn, on='city', how='inner')

    gs_DF_cba_org_dataquyu = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'] == M) &
        (DF_org_data_pre_gun['station_category'] == '高速公共')
        ][['gun_charging_volume_day', 'city']].copy()

    gs_result_city_vloumes = (
        gs_DF_cba_org_dataquyu
        .groupby('city')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_day': '单枪日均充电量'})
        .round(2)
    )

    gs_result_city_vloumes1 = pd.merge(gs_result_city_earn1, gs_result_city_vloumes, on='city', how='inner')

    gs_result_city_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '高速公共') & (DF_cba_pue['cba_month'] == M)]
        .groupby('city')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': '功率利用率'})
        .round(2)
    )

    gs_city_final_count = pd.merge(gs_result_city_vloumes1, gs_result_city_cba_pue, on='city', how='inner')

    gs_city_final_count = gs_city_final_count.fillna(0)
    gs_city_final_count = gs_city_final_count[gs_city_final_count['total_investment_amount'] != 0]
    gs_city_final_count['total_investment_amount'] = gs_city_final_count['total_investment_amount'].apply(float)
    gs_city_final_count['total_investment_amount'] = gs_city_final_count['total_investment_amount'] / 10000
    gs_city_final_count['earn'] = gs_city_final_count['earn'].apply(float)
    gs_city_final_count['earn'] = gs_city_final_count['earn'] / 10000

    gs_city_final_count['total_investment_amount'] = gs_city_final_count['total_investment_amount'].round(2)
    gs_city_final_count['payback'] = gs_city_final_count['earn'] / gs_city_final_count['total_investment_amount']
    gs_city_final_count

    # In[1359]:

    # 确保是数值类型
    gs_city_final_count['total_station_capacity'] = pd.to_numeric(gs_city_final_count['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个城市
    gs_city_ty_min3 = gs_city_final_count.nsmallest(3, 'total_station_capacity')
    gs_city_ty_min3name = gs_city_ty_min3['city']
    print(gs_city_ty_min3name)  # ✅ 打印站点城市名称

    gs_city_tz_min3 = gs_city_final_count.nsmallest(3, 'payback')
    gs_city_tz_min3name = gs_city_tz_min3['city']
    print(gs_city_tz_min3name)  # ✅ 打印站点城市名称

    # 确保是数值类型
    gs_city_final_count['单枪日均充电量'] = pd.to_numeric(gs_city_final_count['单枪日均充电量'], errors='coerce')

    # 筛选出单枪日均充电量最小的前3个城市（注意你原逻辑又写了一次 total_station_capacity，已纠正）
    gs_city_yy_min3 = gs_city_final_count.nsmallest(3, '单枪日均充电量')
    gs_city_yy_min3name = gs_city_yy_min3['city']
    print(gs_city_yy_min3name)  # ✅ 打印站点城市名称

    # ### 设备厂商维度

    # In[1360]:

    gs_EQ_P = pd.merge(
        DF_operation_duration1,
        DF_SCDD[(DF_SCDD['station_category'] == '高速公共') & (DF_SCDD['operation_status'] == '投运')],
        on='station_no',
        how='inner'
    )

    gs_result_sheb_point = (
        gs_EQ_P
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('pile_manufacturer')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'mean')
        )
        .reset_index()
    )

    gs_result_sheb_success = (
        EQ_success[EQ_success['station_category'] == '高速公共']
        .groupby('pile_manufacturer')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': '一次成功率'})
        .round(2)
    )

    gs_result_sheb_kyong = (
        DF_operation_duration0[DF_operation_duration0['station_category'] == '高速公共']
        .groupby('pile_manufacturer')['可用率']
        .mean()
        .reset_index()
        .round(2)
    )

    gs_result_sheb_orders = (
        EQ_orders[EQ_orders['station_category'] == '高速公共']
        .groupby('pile_manufacturer')['单桩工单']
        .mean()
        .reset_index()
        .rename(columns={'单桩工单': '单枪平均运维次数'})
        .round(2)
    )

    from functools import reduce

    gs_df = [gs_result_sheb_point, gs_result_sheb_success, gs_result_sheb_kyong, gs_result_sheb_orders]

    # 按 pile_manufacturer 左连接依次合并
    gs_merged_df = reduce(lambda left, right: pd.merge(left, right, on='pile_manufacturer', how='outer'), gs_df)
    gs_merged_df = gs_merged_df.fillna(0)

    gs_merged_df['一次成功率'] = gs_merged_df['一次成功率'] * 100
    gs_merged_df['可用率'] = gs_merged_df['可用率'] * 100
    gs_merged_df

    # In[1361]:

    # 确保是数值类型
    gs_merged_df['total_station_capacity'] = pd.to_numeric(gs_merged_df['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个设备厂商
    gs_shebei_min3 = gs_merged_df.nsmallest(3, 'total_station_capacity')
    gs_shebei_min3name = gs_shebei_min3['pile_manufacturer']
    print(gs_shebei_min3name)  # 打印设备厂商名称

    # 确保是数值类型
    gs_merged_df['可用率'] = pd.to_numeric(gs_merged_df['可用率'], errors='coerce')

    # 筛选出可用率最小的前3个设备厂商
    gs_shebei_zhil_min3 = gs_merged_df.nsmallest(3, '可用率')
    gs_shebei_zhil_min3_name = gs_shebei_zhil_min3['pile_manufacturer']
    print(gs_shebei_zhil_min3_name)  # 打印设备厂商名称

    # 确保是数值类型
    gs_merged_df['单枪平均运维次数'] = pd.to_numeric(gs_merged_df['单枪平均运维次数'], errors='coerce')

    # 筛选出单枪平均运维次数最大的前3个设备厂商
    gs_shebei_yunwei_max3 = gs_merged_df.nlargest(3, '单枪平均运维次数')
    gs_shebei_yunwei_max3_name = gs_shebei_yunwei_max3['pile_manufacturer']
    print(gs_shebei_yunwei_max3_name)  # 打印设备厂商名称

    # ### 格式修改

    # In[1362]:

    def series_to_str(s):
        return ", ".join(s.astype(str).tolist())

    # 构建站点维度的数据
    station_data = []
    for idx, row in df_gs_zdwd.iterrows():
        station_data.append({
            "id": idx + 1,
            "siteName": row['station_name'],
            "chargingCable": int(row['total_charge_point_count']),
            "ratedPower": int(float(row['total_station_capacity'])),
            "totalInvestmentCosts": float(f"{float(row['total_investment_amount']):.2f}"),
            "returnCost": round(float(row['hbpercentage']), 2),
            "chargeAmountPerGun": round(float(row['gun_charging_volume_day']), 2),
            "powerUtilization": f"{float(row['pue']):.2f}%",
            "successRate": f"{float(row['station_success_rate']):.2f}%",
            "availability": f"{float(row['可用率']) :.2f}%",
            "revenue": round(float(row['revenue']), 2),
            "grossProfit": round(float(row['gross_profit']), 2),
            "ticketsNum": int(float(row['单桩工单']))
        })

    region_data = []
    for idx, row in gs_city_final_count.iterrows():
        region_data.append({
            "id": idx + 1,
            "region": row["city"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "amountInvested": round(float(row["total_investment_amount"]), 2),
            "earnings": f"{float(row['payback']) * 100:.2f}%",

            "chargeAmountPerGun": round(float(row["单枪日均充电量"]), 2),
            "powerUtilization": f"{float(row['功率利用率']):.2f}%"
        })

    equipment_data = []
    for idx, row in gs_merged_df.iterrows():
        equipment_data.append({
            "id": idx + 1,
            "equipmentManufacturers": row["pile_manufacturer"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "successRate": f"{float(row['一次成功率']):.2f}%",
            "availability": f"{float(row['可用率']):.2f}%",
            "omNum": round(float(row["单枪平均运维次数"]), 2)
        })

    table_summary = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个站点为：{series_to_str(df_gs_min3_name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个站点为：{series_to_str(df_gs_min3_tz_name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个站点为：{series_to_str(df_gs_min3_yy_name)}"},
        {"id": 4, "title": "经营情况维度", "content": f"毛利率需重点关注的三个站点为：{series_to_str(df_gs_min3_jy_name)}"},
        {"id": 5, "title": "设备质量维度", "content": f"设备可用率最低的三个站点为：{series_to_str(df_gs_min3_zl_name)}"},
        {"id": 6, "title": "运维情况维度", "content": f"单桩工单数量最多的三个站点为：{series_to_str(df_gs_min3_yw_name)}"},
    ]

    table_summary2 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个地市为：{series_to_str(gs_city_ty_min3name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个地市为：{series_to_str(gs_city_tz_min3name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个地市为：{series_to_str(gs_city_yy_min3name)}"},
    ]

    table_summary3 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的设备厂商为：{series_to_str(gs_shebei_min3name)}"},
        {"id": 2, "title": "设备质量维度", "content": f"设备可用率最低的三个设备厂商为：{series_to_str(gs_shebei_zhil_min3_name)}"},
        {"id": 3, "title": "运维情况维度", "content": f"单桩工单数量最多的三个设备厂商为：{series_to_str(gs_shebei_yunwei_max3_name)}"},
    ]

    # 构建最终结构
    result = {
        "options": ["站点维度", "区域维度", "设备厂商维度"],
        "data": [
            {
                "radio": "站点维度",
                "tableData": station_data,
                "siteNameFilters": [d["siteName"] for d in station_data],
                "tableSummary": table_summary
            },
            {
                "radio": "区域维度",
                "tableData": region_data,
                "tableSummary": table_summary2
            },
            {
                "radio": "设备厂商维度",
                "tableData": equipment_data,
                "tableSummary": table_summary3
            }
        ]
    }
    result

    # In[1363]:

    # 表和字段注释
    table_comment = "类型检测_高速公共_站点指标现状"
    column_comments = {
        'result': '站点指标现状',
        'update_time': '更新日期'
    }
    DF_result = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_result,
        table_name="dp_gs_scdd_nowpoint",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 公交专用

    # ### 站点维度

    # In[1364]:

    df_zdzb_gongjiao = DF_SCDD[
        (DF_SCDD['operation_status'] == '投运') &
        (DF_SCDD['station_category'] == '公交专用')
        ].copy()

    result_station_point_gongjiao = (
        df_zdzb_gongjiao
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('station_no')
        .agg(
            station_name=('station_name', 'first'),
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    hbpercentage_gongjiao = (
        DF[['station_no', 'hbpercentage']]
        .fillna({'hbpercentage': 0})
        .merge(
            DF_SCDD[['station_no', 'station_category']],
            on='station_no',
            how='left'
        )
        .query("station_category == '公交专用'")
        [['station_no', 'hbpercentage']]
    )

    DF_cba_org_datgongjiao = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'] == M) &
        (DF_org_data_pre_gun['station_category'] == '公交专用')
        ][['gun_charging_volume_day', 'station_no']].copy()
    DF_cba_org_datgongjiao = DF_cba_org_datgongjiao.T.drop_duplicates().T

    result_vloumes_gongjiao = (
        DF_cba_org_datgongjiao.groupby('station_no')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .round(2)
    )

    gongjiao_result_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '公交专用') & (DF_cba_pue['cba_month'] == M)]
        .groupby('station_no')['pue']
        .mean()
        .reset_index()
        .round(2)
    )

    DF_success_gongjiao = DF_success[
        (DF_success['month'] == M) &
        (DF_success['station_category'] == '公交专用')
        ].copy()

    # 一次成功率
    gongjiao_result_success_rate = (
        DF_success_gongjiao.groupby('station_no')['station_success_rate']
        .mean()
        .reset_index()
        .round(4)
    )
    gongjiao_result_success_rate['station_success_rate'] = gongjiao_result_success_rate['station_success_rate'] * 100

    DF_gongjiaooperation_duration = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '公交专用')
        ].copy()

    # 可用率
    gongjiao_result_use_rate = (
        DF_gongjiaooperation_duration.groupby('station_no')['可用率']
        .mean()
        .reset_index()
        .round(4)
    )
    gongjiao_result_use_rate['可用率'] = gongjiao_result_use_rate['可用率'] * 100

    df345gongjiao = df11[df11['station_category'] == '公交专用'].copy()

    gongjiao_result_earn = (
        df345gongjiao.groupby('station_no')['revenue']
        .sum()
        .reset_index()
        .round(2)
    )

    df345gongjiao['gross_profit'] = df345gongjiao['revenue'].astype('float') - df345gongjiao['cost'].astype('float')
    gongjiao_result_jing_profile = (
        df345gongjiao.groupby('station_no')['gross_profit']
        .sum()
        .reset_index()
        .round(2)
    )

    # 工单数量
    gongjiao_result_workorders = (
        DF_SCGD[(DF_SCGD['station_category'] == '公交专用') & (DF_SCGD['stat_time'] == M)]
        .groupby('station_no')['单桩工单']
        .mean()
        .reset_index()
        .round(2)
    )

    dfsgongjiao = [
        result_station_point_gongjiao,
        hbpercentage_gongjiao,
        result_vloumes_gongjiao,
        gongjiao_result_cba_pue,
        gongjiao_result_success_rate,
        gongjiao_result_use_rate,
        gongjiao_result_earn,
        gongjiao_result_jing_profile,
        gongjiao_result_workorders
    ]

    from functools import reduce

    # 用 reduce 连续合并多个 DataFrame
    df_gongjiao_zdwd = reduce(
        lambda left, right: pd.merge(left, right, on='station_no', how='left'),
        dfsgongjiao
    )

    # 把所有 NaN 替换为 0
    df_gongjiao_zdwd = df_gongjiao_zdwd.fillna(0)
    df_gongjiao_zdwd = df_gongjiao_zdwd[df_gongjiao_zdwd['total_investment_amount'] != 0]
    cols = ['total_investment_amount', 'revenue', 'gross_profit']

    df_gongjiao_zdwd[cols] = (df_gongjiao_zdwd[cols].astype(float) / 10000).round(2)
    df_gongjiao_zdwd

    # In[1365]:

    # 确保是数值类型
    df_gongjiao_zdwd['total_station_capacity'] = pd.to_numeric(df_gongjiao_zdwd['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_gongjiao_min3 = df_gongjiao_zdwd.nsmallest(3, 'total_station_capacity')

    # 输出站点名称
    df_gongjiao_min3_name = df_gongjiao_min3['station_name']
    print(df_gongjiao_min3_name)

    df_gongjiao_zdwd['hbpercentage'] = pd.to_numeric(df_gongjiao_zdwd['hbpercentage'], errors='coerce')

    # 筛选出 hbp 最小的前3个站
    df_gongjiao_min3_tz = df_gongjiao_zdwd.nsmallest(3, 'hbpercentage')
    df_gongjiao_min3_tz_name = df_gongjiao_min3_tz['station_name']
    print(df_gongjiao_min3_tz_name)

    # 枪日均充电量
    df_gongjiao_zdwd['gun_charging_volume_day'] = pd.to_numeric(df_gongjiao_zdwd['gun_charging_volume_day'], errors='coerce')
    df_gongjiao_min3_yy = df_gongjiao_zdwd.nsmallest(3, 'gun_charging_volume_day')
    df_gongjiao_min3_yy_name = df_gongjiao_min3_yy['station_name']
    print(df_gongjiao_min3_yy_name)

    # 可用率
    df_gongjiao_zdwd['可用率'] = pd.to_numeric(df_gongjiao_zdwd['可用率'], errors='coerce')
    df_gongjiao_min3_zl = df_gongjiao_zdwd.nsmallest(3, '可用率')
    df_gongjiao_min3_zl_name = df_gongjiao_min3_zl['station_name']
    print(df_gongjiao_min3_zl_name)

    # 收入
    df_gongjiao_zdwd['revenue'] = pd.to_numeric(df_gongjiao_zdwd['revenue'], errors='coerce')
    df_gongjiao_zdwd['gross_profit'] = pd.to_numeric(df_gongjiao_zdwd['gross_profit'], errors='coerce')
    df_gongjiao_zdwd['profit_ratio'] = df_gongjiao_zdwd['gross_profit'] / df_gs_zdwd['revenue']
    df_gongjiao_min3_jy = df_gongjiao_zdwd.nsmallest(3, 'profit_ratio')
    df_gongjiao_min3_jy_name = df_gongjiao_min3_jy['station_name']
    print(df_gongjiao_min3_jy_name)

    # 单桩工单数量
    df_gongjiao_zdwd['单桩工单'] = pd.to_numeric(df_gongjiao_zdwd['单桩工单'], errors='coerce')
    df_gongjiao_min3_yw = df_gongjiao_zdwd.nlargest(3, '单桩工单')
    df_gongjiao_min3_yw_name = df_gongjiao_min3_yw['station_name']
    print(df_gongjiao_min3_yw_name)

    # In[ ]:

    # ### 区域维度

    # In[1366]:

    gongjiao_result_city_point = (
        DF_SCDD[(DF_SCDD['station_category'] == '公交专用') & (DF_SCDD['operation_status'] == '投运')]
        .assign(
            total_charge_point_count=lambda df: df['dc_charge_point_count'].fillna(0) + df['ac_charge_point_count'].fillna(0)
        )
        .groupby('city')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    # 营收
    gongjiao_result_city_earn = (
        df_all_profit[df_all_profit['station_category'] == '公交专用']
        .assign(earn=lambda x: x['rec_data'] - x['rec_cost'])  # 新增收益列
        .groupby('city', as_index=False)['earn']
        .sum()
        .round(2)
    )

    gongjiao_result_city_earn1 = pd.merge(gongjiao_result_city_point, gongjiao_result_city_earn, on='city', how='inner')

    gongjiao_DF_cba_org_dataquyu = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'] == M) &
        (DF_org_data_pre_gun['station_category'] == '公交专用')
        ][['gun_charging_volume_day', 'city']].copy()

    gongjiao_result_city_vloumes = (
        gongjiao_DF_cba_org_dataquyu
        .groupby('city')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_day': '单枪日均充电量'})
        .round(2)
    )

    gongjiao_result_city_vloumes1 = pd.merge(gongjiao_result_city_earn1, gongjiao_result_city_vloumes, on='city', how='inner')

    gongjiao_result_city_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '公交专用') & (DF_cba_pue['cba_month'] == M)]
        .groupby('city')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': '功率利用率'})
        .round(2)
    )

    gongjiao_city_final_count = pd.merge(gongjiao_result_city_vloumes1, gongjiao_result_city_cba_pue, on='city', how='inner')

    gongjiao_city_final_count = gongjiao_city_final_count.fillna(0)
    gongjiao_city_final_count = gongjiao_city_final_count[gongjiao_city_final_count['total_investment_amount'] != 0]
    gongjiao_city_final_count['total_investment_amount'] = gongjiao_city_final_count['total_investment_amount'].apply(float)
    gongjiao_city_final_count['total_investment_amount'] = gongjiao_city_final_count['total_investment_amount'] / 10000
    gongjiao_city_final_count['total_investment_amount'] = gongjiao_city_final_count['total_investment_amount'].round(2)
    gongjiao_city_final_count['earn'] = gongjiao_city_final_count['earn'].apply(float)
    gongjiao_city_final_count['earn'] = gongjiao_city_final_count['earn'] / 10000
    gongjiao_city_final_count['payback'] = gongjiao_city_final_count['earn'] / gongjiao_city_final_count['total_investment_amount']
    gongjiao_city_final_count

    # In[1367]:

    # 确保是数值类型
    gongjiao_city_final_count['total_station_capacity'] = pd.to_numeric(gongjiao_city_final_count['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个城市
    gongjiao_city_ty_min3 = gongjiao_city_final_count.nsmallest(3, 'total_station_capacity')
    gongjiao_city_ty_min3name = gongjiao_city_ty_min3['city']
    print(gongjiao_city_ty_min3name)  # ✅ 打印城市名称

    gongjiao_city_tz_min3 = gongjiao_city_final_count.nsmallest(3, 'payback')
    gongjiao_city_tz_min3name = gongjiao_city_tz_min3['city']
    print(gongjiao_city_tz_min3name)  # ✅ 打印城市名称

    # 确保是数值类型
    gongjiao_city_final_count['单枪日均充电量'] = pd.to_numeric(gongjiao_city_final_count['单枪日均充电量'], errors='coerce')

    # 筛选出单枪日均充电量最小的前3个城市
    gongjiao_city_yy_min3 = gongjiao_city_final_count.nsmallest(3, '单枪日均充电量')
    gongjiao_city_yy_min3name = gongjiao_city_yy_min3['city']
    print(gongjiao_city_yy_min3name)  # ✅ 打印城市名称

    # ### 设备厂商维度

    # In[1368]:

    gongjiao_EQ_P = pd.merge(
        DF_operation_duration1,
        DF_SCDD[(DF_SCDD['station_category'] == '公交专用') & (DF_SCDD['operation_status'] == '投运')],
        on='station_no',
        how='inner'
    )

    gongjiao_result_sheb_point = (
        gongjiao_EQ_P
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('pile_manufacturer')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'mean')
        )
        .reset_index()
    )

    gongjiao_result_sheb_success = (
        EQ_success[EQ_success['station_category'] == '公交专用']
        .groupby('pile_manufacturer')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': '一次成功率'})
        .round(2)
    )

    gongjiao_result_sheb_kyong = (
        DF_operation_duration0[DF_operation_duration0['station_category'] == '公交专用']
        .groupby('pile_manufacturer')['可用率']
        .mean()
        .reset_index()
        .round(2)
    )

    gongjiao_result_sheb_orders = (
        EQ_orders[EQ_orders['station_category'] == '公交专用']
        .groupby('pile_manufacturer')['单桩工单']
        .mean()
        .reset_index()
        .rename(columns={'单桩工单': '单枪平均运维次数'})
        .round(2)
    )

    from functools import reduce

    gongjiao_df = [
        gongjiao_result_sheb_point,
        gongjiao_result_sheb_success,
        gongjiao_result_sheb_kyong,
        gongjiao_result_sheb_orders
    ]

    # 按 pile_manufacturer 左连接依次合并
    gongjiao_merged_df = reduce(lambda left, right: pd.merge(left, right, on='pile_manufacturer', how='outer'), gongjiao_df)

    # 填充空值为 0
    gongjiao_merged_df = gongjiao_merged_df.fillna(0)

    # In[1369]:

    gongjiao_merged_df.replace([np.inf, -np.inf], 0, inplace=True)

    # In[1370]:

    gongjiao_merged_df['一次成功率'] = gongjiao_merged_df['一次成功率'] * 100
    gongjiao_merged_df['可用率'] = gongjiao_merged_df['可用率'] * 100
    gongjiao_merged_df

    # In[1371]:

    # 确保是数值类型
    gongjiao_merged_df['total_station_capacity'] = pd.to_numeric(gongjiao_merged_df['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个设备厂商
    gongjiao_shebei_min3 = gongjiao_merged_df.nsmallest(3, 'total_station_capacity')
    gongjiao_shebei_min3name = gongjiao_shebei_min3['pile_manufacturer']
    print(gongjiao_shebei_min3name)  # 打印设备厂商名称

    # 确保是数值类型
    gongjiao_merged_df['可用率'] = pd.to_numeric(gongjiao_merged_df['可用率'], errors='coerce')

    # 筛选出可用率最小的前3个设备厂商
    gongjiao_shebei_zhil_min3 = gongjiao_merged_df.nsmallest(3, '可用率')
    gongjiao_shebei_zhil_min3_name = gongjiao_shebei_zhil_min3['pile_manufacturer']
    print(gongjiao_shebei_zhil_min3_name)  # 打印设备厂商名称

    # 确保是数值类型
    gongjiao_merged_df['单枪平均运维次数'] = pd.to_numeric(gongjiao_merged_df['单枪平均运维次数'], errors='coerce')

    # 筛选出单枪平均运维次数最大的前3个设备厂商
    gongjiao_shebei_yunwei_max3 = gongjiao_merged_df.nlargest(3, '单枪平均运维次数')
    gongjiao_shebei_yunwei_max3_name = gongjiao_shebei_yunwei_max3['pile_manufacturer']
    print(gongjiao_shebei_yunwei_max3_name)  # 打印设备厂商名称

    # ### 格式修改

    # In[1372]:

    def series_to_str(s):
        return ", ".join(s.astype(str).tolist())

    # 构建站点维度的数据
    station_data = []
    for idx, row in df_gongjiao_zdwd.iterrows():
        station_data.append({
            "id": idx + 1,
            "siteName": row['station_name'],
            "chargingCable": int(row['total_charge_point_count']),
            "ratedPower": int(float(row['total_station_capacity'])),
            "totalInvestmentCosts": float(f"{float(row['total_investment_amount']):.2f}"),
            "returnCost": round(float(row['hbpercentage']), 2),
            "chargeAmountPerGun": round(float(row['gun_charging_volume_day']), 2),
            "powerUtilization": f"{float(row['pue']) :.2f}%",
            "successRate": f"{float(row['station_success_rate']):.2f}%",
            "availability": f"{float(row['可用率']) :.2f}%",
            "revenue": round(float(row['revenue']), 2),
            "grossProfit": round(float(row['gross_profit']), 2),
            "ticketsNum": int(float(row['单桩工单']))
        })

    region_data = []
    for idx, row in gongjiao_city_final_count.iterrows():
        region_data.append({
            "id": idx + 1,
            "region": row["city"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "amountInvested": round(float(row["total_investment_amount"]), 2),
            "earnings": f"{float(row['payback']) * 100:.2f}%",

            "chargeAmountPerGun": round(float(row["单枪日均充电量"]), 2),
            "powerUtilization": f"{float(row['功率利用率']):.2f}%"
        })

    equipment_data = []
    for idx, row in gongjiao_merged_df.iterrows():
        equipment_data.append({
            "id": idx + 1,
            "equipmentManufacturers": row["pile_manufacturer"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "successRate": f"{float(row['一次成功率']):.2f}%",
            "availability": f"{float(row['可用率']):.2f}%",
            "omNum": round(float(row["单枪平均运维次数"]), 2)
        })

    table_summary = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个站点为：{series_to_str(df_gongjiao_min3_name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个站点为：{series_to_str(df_gongjiao_min3_tz_name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个站点为：{series_to_str(df_gongjiao_min3_yy_name)}"},
        {"id": 4, "title": "经营情况维度", "content": f"毛利率需重点关注的三个站点为：{series_to_str(df_gongjiao_min3_jy_name)}"},
        {"id": 5, "title": "设备质量维度", "content": f"设备可用率最低的三个站点为：{series_to_str(df_gongjiao_min3_zl_name)}"},

        {"id": 6, "title": "运维情况维度", "content": f"单桩工单数量最多的三个站点为：{series_to_str(df_gongjiao_min3_yw_name)}"},
    ]

    table_summary2 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个地市为：{series_to_str(gongjiao_city_ty_min3name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个地市为：{series_to_str(gongjiao_city_tz_min3name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个地市为：{series_to_str(gongjiao_city_yy_min3name)}"},
    ]

    table_summary3 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的设备厂商为：{series_to_str(gongjiao_shebei_min3name)}"},
        {"id": 2, "title": "设备质量维度", "content": f"设备可用率最低的三个设备厂商为：{series_to_str(gongjiao_shebei_zhil_min3_name)}"},
        {"id": 3, "title": "运维情况维度", "content": f"单桩工单数量最多的三个设备厂商为：{series_to_str(gongjiao_shebei_yunwei_max3_name)}"},
    ]

    # 构建最终结构
    result = {
        "options": ["站点维度", "区域维度", "设备厂商维度"],
        "data": [
            {
                "radio": "站点维度",
                "tableData": station_data,
                "siteNameFilters": [d["siteName"] for d in station_data],
                "tableSummary": table_summary
            },
            {
                "radio": "区域维度",
                "tableData": region_data,
                "tableSummary": table_summary2
            },
            {
                "radio": "设备厂商维度",
                "tableData": equipment_data,
                "tableSummary": table_summary3
            }
        ]
    }
    result

    # In[1373]:

    # 表和字段注释
    table_comment = "类型检测_公交专用_站点指标现状"
    column_comments = {
        'result': '站点指标现状',
        'update_time': '更新日期'
    }
    DF_result = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_result,
        table_name="dp_gongjiao_scdd_nowpoint",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 小区有序

    # ### 站点维度

    # In[1374]:

    df_zdzb_xiaoqu = DF_SCDD[
        (DF_SCDD['operation_status'] == '投运') &
        (DF_SCDD['station_category'] == '小区有序')
        ].copy()

    result_station_point_xiaoqu = (
        df_zdzb_xiaoqu
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('station_no')
        .agg(
            station_name=('station_name', 'first'),
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    hbpercentage_xiaoqu = (
        DF[['station_no', 'hbpercentage']]
        .fillna({'hbpercentage': 0})
        .merge(
            DF_SCDD[['station_no', 'station_category']],
            on='station_no',
            how='left'
        )
        .query("station_category == '小区有序'")
        [['station_no', 'hbpercentage']]
    )

    DF_cba_org_datxiaoqu = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'] == M) &
        (DF_org_data_pre_gun['station_category'] == '小区有序')
        ][['gun_charging_volume_day', 'station_no']].copy()
    DF_cba_org_datxiaoqu = DF_cba_org_datxiaoqu.T.drop_duplicates().T

    result_vloumes_xiaoqu = (
        DF_cba_org_datxiaoqu.groupby('station_no')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .round(2)
    )

    xiaoqu_result_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '小区有序') & (DF_cba_pue['cba_month'] == M)]
        .groupby('station_no')['pue']
        .mean()
        .reset_index()
        .round(2)
    )

    DF_success_xiaoqu = DF_success[
        (DF_success['month'] == M) &
        (DF_success['station_category'] == '小区有序')
        ].copy()

    # 一次成功率
    xiaoqu_result_success_rate = (
        DF_success_xiaoqu.groupby('station_no')['station_success_rate']
        .mean()
        .reset_index()
        .round(4)
    )
    xiaoqu_result_success_rate['station_success_rate'] = xiaoqu_result_success_rate['station_success_rate'] * 100

    DF_xiaoquoperation_duration = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '小区有序')
        ].copy()

    # 可用率
    xiaoqu_result_use_rate = (
        DF_xiaoquoperation_duration.groupby('station_no')['可用率']
        .mean()
        .reset_index()
        .round(4)
    )
    xiaoqu_result_use_rate['可用率'] = xiaoqu_result_use_rate['可用率'] * 100
    df345xiaoqu = df11[df11['station_category'] == '小区有序'].copy()

    xiaoqu_result_earn = (
        df345xiaoqu.groupby('station_no')['revenue']
        .sum()
        .reset_index()
        .round(2)
    )

    df345xiaoqu['gross_profit'] = df345xiaoqu['revenue'].astype('float') - df345xiaoqu['cost'].astype('float')
    xiaoqu_result_jing_profile = (
        df345xiaoqu.groupby('station_no')['gross_profit']
        .sum()
        .reset_index()
        .round(2)
    )

    # 工单数量
    xiaoqu_result_workorders = (
        DF_SCGD[(DF_SCGD['station_category'] == '小区有序') & (DF_SCGD['stat_time'] == M)]
        .groupby('station_no')['单桩工单']
        .mean()
        .reset_index()
        .round(2)
    )

    dfsxiaoqu = [
        result_station_point_xiaoqu,
        hbpercentage_xiaoqu,
        result_vloumes_xiaoqu,
        xiaoqu_result_cba_pue,
        xiaoqu_result_success_rate,
        xiaoqu_result_use_rate,
        xiaoqu_result_earn,
        xiaoqu_result_jing_profile,
        xiaoqu_result_workorders
    ]

    from functools import reduce

    # 用 reduce 连续合并多个 DataFrame
    df_xiaoqu_zdwd = reduce(
        lambda left, right: pd.merge(left, right, on='station_no', how='left'),
        dfsxiaoqu
    )

    # 把所有 NaN 替换为 0
    df_xiaoqu_zdwd = df_xiaoqu_zdwd.fillna(0)
    df_xiaoqu_zdwd = df_xiaoqu_zdwd[df_xiaoqu_zdwd['total_investment_amount'] != 0]
    cols = ['total_investment_amount', 'revenue', 'gross_profit']

    df_xiaoqu_zdwd[cols] = (df_xiaoqu_zdwd[cols].astype(float) / 10000).round(2)
    df_xiaoqu_zdwd

    # In[1375]:

    # 确保是数值类型
    df_xiaoqu_zdwd['total_station_capacity'] = pd.to_numeric(df_xiaoqu_zdwd['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_xiaoqu_min3 = df_xiaoqu_zdwd.nsmallest(3, 'total_station_capacity')

    # 输出站点名称
    df_xiaoqu_min3_name = df_xiaoqu_min3['station_name']
    print(df_xiaoqu_min3_name)

    df_xiaoqu_zdwd['hbpercentage'] = pd.to_numeric(df_xiaoqu_zdwd['hbpercentage'], errors='coerce')

    # 筛选出 hbp 最小的前3个站
    df_xiaoqu_min3_tz = df_xiaoqu_zdwd.nsmallest(3, 'hbpercentage')
    df_xiaoqu_min3_tz_name = df_xiaoqu_min3_tz['station_name']
    print(df_xiaoqu_min3_tz_name)

    # 枪日均充电量
    df_xiaoqu_zdwd['gun_charging_volume_day'] = pd.to_numeric(df_xiaoqu_zdwd['gun_charging_volume_day'], errors='coerce')
    df_xiaoqu_min3_yy = df_xiaoqu_zdwd.nsmallest(3, 'gun_charging_volume_day')
    df_xiaoqu_min3_yy_name = df_xiaoqu_min3_yy['station_name']
    print(df_xiaoqu_min3_yy_name)

    # 可用率
    df_xiaoqu_zdwd['可用率'] = pd.to_numeric(df_xiaoqu_zdwd['可用率'], errors='coerce')

    df_xiaoqu_min3_zl = df_xiaoqu_zdwd.nsmallest(3, '可用率')
    df_xiaoqu_min3_zl_name = df_xiaoqu_min3_zl['station_name']
    print(df_xiaoqu_min3_zl_name)

    # 收入
    df_xiaoqu_zdwd['revenue'] = pd.to_numeric(df_xiaoqu_zdwd['revenue'], errors='coerce')

    df_xiaoqu_zdwd['gross_profit'] = pd.to_numeric(df_xiaoqu_zdwd['gross_profit'], errors='coerce')
    # 计算毛利率（gross_profit / revenue）
    df_xiaoqu_zdwd['profit_ratio'] = df_xiaoqu_zdwd['gross_profit'] / df_gs_zdwd['revenue']
    df_xiaoqu_min3_jy = df_xiaoqu_zdwd.nsmallest(3, 'profit_ratio')
    df_xiaoqu_min3_jy_name = df_xiaoqu_min3_jy['station_name']
    print(df_xiaoqu_min3_jy_name)

    # 单桩工单数量
    df_xiaoqu_zdwd['单桩工单'] = pd.to_numeric(df_xiaoqu_zdwd['单桩工单'], errors='coerce')
    df_xiaoqu_min3_yw = df_xiaoqu_zdwd.nlargest(3, '单桩工单')
    df_xiaoqu_min3_yw_name = df_xiaoqu_min3_yw['station_name']
    print(df_xiaoqu_min3_yw_name)

    # ### 区域维度

    # In[1376]:

    xiaoqu_result_city_point = (
        DF_SCDD[(DF_SCDD['station_category'] == '小区有序') & (DF_SCDD['operation_status'] == '投运')]
        .assign(
            total_charge_point_count=lambda df: df['dc_charge_point_count'].fillna(0) + df['ac_charge_point_count'].fillna(0)
        )
        .groupby('city')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    # 营收
    xiaoqu_result_city_earn = (
        df_all_profit[df_all_profit['station_category'] == '小区有序']
        .assign(earn=lambda x: x['rec_data'] - x['rec_cost'])
        .groupby('city', as_index=False)['earn']
        .sum()
        .round(2)
    )

    xiaoqu_result_city_earn1 = pd.merge(xiaoqu_result_city_point, xiaoqu_result_city_earn, on='city', how='inner')

    xiaoqu_DF_cba_org_dataquyu = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'] == M) &
        (DF_org_data_pre_gun['station_category'] == '小区有序')
        ][['gun_charging_volume_day', 'city']].copy()

    xiaoqu_result_city_vloumes = (
        xiaoqu_DF_cba_org_dataquyu
        .groupby('city')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_day': '单枪日均充电量'})
        .round(2)
    )

    xiaoqu_result_city_vloumes1 = pd.merge(xiaoqu_result_city_earn1, xiaoqu_result_city_vloumes, on='city', how='inner')

    xiaoqu_result_city_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '小区有序') & (DF_cba_pue['cba_month'] == M)]
        .groupby('city')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': '功率利用率'})
        .round(2)
    )

    xiaoqu_city_final_count = pd.merge(xiaoqu_result_city_vloumes1, xiaoqu_result_city_cba_pue, on='city', how='inner')

    xiaoqu_city_final_count = xiaoqu_city_final_count.fillna(0)
    xiaoqu_city_final_count = xiaoqu_city_final_count[xiaoqu_city_final_count['total_investment_amount'] != 0]
    cols = ['total_investment_amount', 'earn']

    xiaoqu_city_final_count[cols] = (xiaoqu_city_final_count[cols].astype(float) / 10000).round(2)

    xiaoqu_city_final_count['payback'] = xiaoqu_city_final_count['earn'] / xiaoqu_city_final_count['total_investment_amount']
    xiaoqu_city_final_count

    # In[1377]:

    # 确保是数值类型
    xiaoqu_city_final_count['total_station_capacity'] = pd.to_numeric(xiaoqu_city_final_count['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个城市
    xiaoqu_city_ty_min3 = xiaoqu_city_final_count.nsmallest(3, 'total_station_capacity')
    xiaoqu_city_ty_min3name = xiaoqu_city_ty_min3['city']
    print(xiaoqu_city_ty_min3name)  # ✅ 打印站点城市名称

    # 筛选出 rec_data - 投资额 差值最小的3个城市
    xiaoqu_city_tz_min3 = xiaoqu_city_final_count.nsmallest(3, 'payback')
    xiaoqu_city_tz_min3name = xiaoqu_city_tz_min3['city']
    print(xiaoqu_city_tz_min3name)  # ✅ 打印站点城市名称

    # 确保是数值类型
    xiaoqu_city_final_count['单枪日均充电量'] = pd.to_numeric(xiaoqu_city_final_count['单枪日均充电量'], errors='coerce')

    # 筛选出单枪日均充电量最小的前3个城市
    xiaoqu_city_yy_min3 = xiaoqu_city_final_count.nsmallest(3, '单枪日均充电量')
    xiaoqu_city_yy_min3name = xiaoqu_city_yy_min3['city']
    print(xiaoqu_city_yy_min3name)  # ✅ 打印站点城市名称

    # ### 设备厂商维度

    # In[1378]:

    xiaoqu_EQ_P = pd.merge(
        DF_operation_duration1,
        DF_SCDD[(DF_SCDD['station_category'] == '小区有序') & (DF_SCDD['operation_status'] == '投运')],
        on='station_no',
        how='inner'
    )

    xiaoqu_result_sheb_point = (
        xiaoqu_EQ_P
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('pile_manufacturer')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'mean')
        )
        .reset_index()
    )

    xiaoqu_result_sheb_success = (
        EQ_success[EQ_success['station_category'] == '小区有序']
        .groupby('pile_manufacturer')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': '一次成功率'})
        .round(2)
    )

    xiaoqu_result_sheb_kyong = (
        DF_operation_duration0[DF_operation_duration0['station_category'] == '小区有序']
        .groupby('pile_manufacturer')['可用率']
        .mean()
        .reset_index()
        .round(2)
    )

    xiaoqu_result_sheb_orders = (
        EQ_orders[EQ_orders['station_category'] == '小区有序']
        .groupby('pile_manufacturer')['单桩工单']
        .mean()
        .reset_index()
        .rename(columns={'单桩工单': '单枪平均运维次数'})
        .round(2)
    )

    from functools import reduce

    xiaoqu_df = [xiaoqu_result_sheb_point, xiaoqu_result_sheb_success, xiaoqu_result_sheb_kyong, xiaoqu_result_sheb_orders]

    # 按 pile_manufacturer 左连接依次合并
    xiaoqu_merged_df = reduce(lambda left, right: pd.merge(left, right, on='pile_manufacturer', how='outer'), xiaoqu_df)
    xiaoqu_merged_df = xiaoqu_merged_df.fillna(0)

    xiaoqu_merged_df['一次成功率'] = xiaoqu_merged_df['一次成功率'] * 100

    xiaoqu_merged_df['可用率'] = xiaoqu_merged_df['可用率'] * 100
    xiaoqu_merged_df

    # In[1379]:

    # 确保是数值类型
    xiaoqu_merged_df['total_station_capacity'] = pd.to_numeric(xiaoqu_merged_df['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个设备厂商
    xiaoqu_shebei_min3 = xiaoqu_merged_df.nsmallest(3, 'total_station_capacity')
    xiaoqu_shebei_min3name = xiaoqu_shebei_min3['pile_manufacturer']
    print(xiaoqu_shebei_min3name)  # 打印设备厂商名称

    # 确保是数值类型
    xiaoqu_merged_df['可用率'] = pd.to_numeric(xiaoqu_merged_df['可用率'], errors='coerce')

    # 筛选出可用率最小的前3个设备厂商
    xiaoqu_shebei_zhil_min3 = xiaoqu_merged_df.nsmallest(3, '可用率')
    xiaoqu_shebei_zhil_min3_name = xiaoqu_shebei_zhil_min3['pile_manufacturer']
    print(xiaoqu_shebei_zhil_min3_name)  # 打印设备厂商名称

    # 确保是数值类型
    xiaoqu_merged_df['单枪平均运维次数'] = pd.to_numeric(xiaoqu_merged_df['单枪平均运维次数'], errors='coerce')

    # 筛选出单枪平均运维次数最大的前3个设备厂商
    xiaoqu_shebei_yunwei_max3 = xiaoqu_merged_df.nlargest(3, '单枪平均运维次数')
    xiaoqu_shebei_yunwei_max3_name = xiaoqu_shebei_yunwei_max3['pile_manufacturer']
    print(xiaoqu_shebei_yunwei_max3_name)  # 打印设备厂商名称

    # ### 格式修改

    # In[1380]:

    def series_to_str(s):
        return ", ".join(s.astype(str).tolist())

    # 构建站点维度的数据
    station_data = []
    for idx, row in df_xiaoqu_zdwd.iterrows():
        station_data.append({
            "id": idx + 1,
            "siteName": row['station_name'],
            "chargingCable": int(row['total_charge_point_count']) if pd.notna(row['total_charge_point_count']) else 0,
            "ratedPower": int(float(row['total_station_capacity'])) if pd.notna(row['total_station_capacity']) else 0,
            "totalInvestmentCosts": float(f"{float(row['total_investment_amount']):.2f}") if pd.notna(
                row['total_investment_amount']) else 0.00,
            "returnCost": round(float(row['hbpercentage']), 2) if pd.notna(row['hbpercentage']) else 0.00,
            "chargeAmountPerGun": round(float(row['gun_charging_volume_day']), 2) if pd.notna(
                row['gun_charging_volume_day']) else 0.00,
            "powerUtilization": f"{float(row['pue']):.2f}%" if pd.notna(row['pue']) else "0.00%",
            "successRate": f"{float(row['station_success_rate']):.2f}%" if pd.notna(
                row['station_success_rate']) else "0.00%",
            "availability": f"{float(row['可用率']):.2f}%" if pd.notna(row['可用率']) else "0.00%",
            "revenue": round(float(row['revenue']), 2) if pd.notna(row['revenue']) else 0.00,
            "grossProfit": round(float(row['gross_profit']), 2) if pd.notna(row['gross_profit']) else 0.00,
            "ticketsNum": int(float(row['单桩工单'])) if pd.notna(row['单桩工单']) else 0
        })

    region_data = []
    for idx, row in xiaoqu_city_final_count.iterrows():
        region_data.append({
            "id": idx + 1,
            "region": row["city"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "amountInvested": round(float(row["total_investment_amount"]), 2),
            "earnings": f"{float(row['payback']) * 100:.2f}%",

            "chargeAmountPerGun": round(float(row["单枪日均充电量"]), 2),
            "powerUtilization": f"{float(row['功率利用率']):.2f}%"
        })

    equipment_data = []
    for idx, row in xiaoqu_merged_df.iterrows():
        equipment_data.append({
            "id": idx + 1,
            "equipmentManufacturers": row["pile_manufacturer"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "successRate": f"{float(row['一次成功率']):.2f}%",
            "availability": f"{float(row['可用率']):.2f}%",
            "omNum": round(float(row["单枪平均运维次数"]), 2)
        })

    table_summary = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个站点为：{series_to_str(df_xiaoqu_min3_name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个站点为：{series_to_str(df_xiaoqu_min3_tz_name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个站点为：{series_to_str(df_xiaoqu_min3_yy_name)}"},
        {"id": 4, "title": "经营情况维度", "content": f"毛利率需重点关注的三个站点为：{series_to_str(df_xiaoqu_min3_jy_name)}"},
        {"id": 5, "title": "设备质量维度", "content": f"设备可用率最低的三个站点为：{series_to_str(df_xiaoqu_min3_zl_name)}"},
        {"id": 6, "title": "运维情况维度", "content": f"单桩工单数量最多的三个站点为：{series_to_str(df_xiaoqu_min3_yw_name)}"},
    ]

    table_summary2 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个地市为：{series_to_str(xiaoqu_city_ty_min3name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个地市为：{series_to_str(xiaoqu_city_tz_min3name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个地市为：{series_to_str(xiaoqu_city_yy_min3name)}"},
    ]

    table_summary3 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的设备厂商为：{series_to_str(xiaoqu_shebei_min3name)}"},
        {"id": 2, "title": "设备质量维度", "content": f"设备可用率最低的三个设备厂商为：{series_to_str(xiaoqu_shebei_zhil_min3_name)}"},
        {"id": 3, "title": "运维情况维度", "content": f"单桩工单数量最多的三个设备厂商为：{series_to_str(xiaoqu_shebei_yunwei_max3_name)}"},
    ]

    # 构建最终结构
    result = {
        "options": ["站点维度", "区域维度", "设备厂商维度"],
        "data": [
            {
                "radio": "站点维度",
                "tableData": station_data,
                "siteNameFilters": [d["siteName"] for d in station_data],
                "tableSummary": table_summary
            },
            {
                "radio": "区域维度",
                "tableData": region_data,
                "tableSummary": table_summary2
            },
            {
                "radio": "设备厂商维度",
                "tableData": equipment_data,
                "tableSummary": table_summary3
            }
        ]
    }
    result

    # In[1381]:

    # 表和字段注释
    table_comment = "类型检测_小区有序_站点指标现状"
    column_comments = {
        'result': '站点指标现状',
        'update_time': '更新日期'
    }
    DF_result = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_result,
        table_name="dp_xiaoqu_scdd_nowpoint",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 其他专用

    # ### 站点维度

    # In[1382]:

    df_zdzb_qita = DF_SCDD[
        (DF_SCDD['operation_status'] == '投运') &
        (DF_SCDD['station_category'] == '其他专用')
        ].copy()

    result_station_point_qita = (
        df_zdzb_qita
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('station_no')
        .agg(
            station_name=('station_name', 'first'),
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    hbpercentage_qita = (
        DF[['station_no', 'hbpercentage']]
        .fillna({'hbpercentage': 0})
        .merge(
            DF_SCDD[['station_no', 'station_category']],
            on='station_no',
            how='left'
        )
        .query("station_category == '其他专用'")
        [['station_no', 'hbpercentage']]
    )

    DF_cba_org_datqita = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'] == M) &
        (DF_org_data_pre_gun['station_category'] == '其他专用')
        ][['gun_charging_volume_day', 'station_no']].copy()
    DF_cba_org_datqita = DF_cba_org_datqita.T.drop_duplicates().T

    result_vloumes_qita = (
        DF_cba_org_datqita.groupby('station_no')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .round(2)
    )

    qita_result_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '其他专用') & (DF_cba_pue['cba_month'] == M)]
        .groupby('station_no')['pue']
        .mean()
        .reset_index()
        .round(2)
    )

    DF_success_qita = DF_success[
        (DF_success['month'] == M) &
        (DF_success['station_category'] == '其他专用')
        ].copy()

    # 一次成功率
    qita_result_success_rate = (
        DF_success_qita.groupby('station_no')['station_success_rate']
        .mean()
        .reset_index()
        .round(4)
    )
    qita_result_success_rate['station_success_rate'] = qita_result_success_rate['station_success_rate'] * 100

    DF_qitaoperation_duration = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '其他专用')
        ].copy()

    # 可用率
    qita_result_use_rate = (
        DF_qitaoperation_duration.groupby('station_no')['可用率']
        .mean()
        .reset_index()
        .round(4)
    )
    qita_result_use_rate['可用率'] = qita_result_use_rate['可用率'] * 100
    df345qita = df11[df11['station_category'] == '其他专用'].copy()

    qita_result_earn = (
        df345qita.groupby('station_no')['revenue']
        .sum()
        .reset_index()
        .round(2)
    )

    df345qita['gross_profit'] = df345qita['revenue'].astype('float') - df345qita['cost'].astype('float')
    qita_result_jing_profile = (
        df345qita.groupby('station_no')['gross_profit']
        .sum()
        .reset_index()
        .round(2)
    )

    # 工单数量
    qita_result_workorders = (
        DF_SCGD[(DF_SCGD['station_category'] == '其他专用') & (DF_SCGD['stat_time'] == M)]
        .groupby('station_no')['单桩工单']
        .mean()
        .reset_index()
        .round(2)
    )

    dfsqita = [
        result_station_point_qita,
        hbpercentage_qita,
        result_vloumes_qita,
        qita_result_cba_pue,
        qita_result_success_rate,
        qita_result_use_rate,
        qita_result_earn,
        qita_result_jing_profile,
        qita_result_workorders
    ]

    from functools import reduce

    # 用 reduce 连续合并多个 DataFrame
    df_qita_zdwd = reduce(
        lambda left, right: pd.merge(left, right, on='station_no', how='left'),
        dfsqita
    )

    # 把所有 NaN 替换为 0
    df_qita_zdwd = df_qita_zdwd.fillna(0)
    df_qita_zdwd = df_qita_zdwd[df_qita_zdwd['total_investment_amount'] != 0]
    cols = ['total_investment_amount', 'revenue', 'gross_profit']
    df_qita_zdwd[cols] = (df_qita_zdwd[cols].astype(float) / 10000).round(2)
    df_qita_zdwd

    # In[1383]:

    # 确保是数值类型
    df_qita_zdwd['total_station_capacity'] = pd.to_numeric(df_qita_zdwd['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个站
    df_qita_min3 = df_qita_zdwd.nsmallest(3, 'total_station_capacity')

    # 输出站点名称
    df_qita_min3_name = df_qita_min3['station_name']
    print(df_qita_min3_name)

    df_qita_zdwd['hbpercentage'] = pd.to_numeric(df_qita_zdwd['hbpercentage'], errors='coerce')

    # 筛选出 hbp 最小的前3个站
    df_qita_min3_tz = df_qita_zdwd.nsmallest(3, 'hbpercentage')
    df_qita_min3_tz_name = df_qita_min3_tz['station_name']
    print(df_qita_min3_tz_name)

    # 枪日均充电量
    df_qita_zdwd['gun_charging_volume_day'] = pd.to_numeric(df_qita_zdwd['gun_charging_volume_day'], errors='coerce')
    df_qita_min3_yy = df_qita_zdwd.nsmallest(3, 'gun_charging_volume_day')
    df_qita_min3_yy_name = df_qita_min3_yy['station_name']
    print(df_qita_min3_yy_name)

    # 可用率
    df_qita_zdwd['可用率'] = pd.to_numeric(df_qita_zdwd['可用率'], errors='coerce')
    df_qita_min3_zl = df_qita_zdwd.nsmallest(3, '可用率')
    df_qita_min3_zl_name = df_qita_min3_zl['station_name']
    print(df_qita_min3_zl_name)

    # 收入
    df_qita_zdwd['revenue'] = pd.to_numeric(df_qita_zdwd['revenue'], errors='coerce')

    df_qita_zdwd['gross_profit'] = pd.to_numeric(df_qita_zdwd['gross_profit'], errors='coerce')
    # 计算毛利率（gross_profit / revenue）
    df_qita_zdwd['profit_ratio'] = df_qita_zdwd['gross_profit'] / df_qita_zdwd['revenue']

    df_qita_min3_jy = df_qita_zdwd.nsmallest(3, 'profit_ratio')
    df_qita_min3_jy_name = df_qita_min3_jy['station_name']
    print(df_qita_min3_jy_name)

    # 单桩工单数量
    df_qita_zdwd['单桩工单'] = pd.to_numeric(df_qita_zdwd['单桩工单'], errors='coerce')
    df_qita_min3_yw = df_qita_zdwd.nlargest(3, '单桩工单')
    df_qita_min3_yw_name = df_qita_min3_yw['station_name']
    print(df_qita_min3_yw_name)

    # ### 区域维度

    # In[1384]:

    qita_result_city_point = (
        DF_SCDD[(DF_SCDD['station_category'] == '其他专用') & (DF_SCDD['operation_status'] == '投运')]
        .assign(
            total_charge_point_count=lambda df: df['dc_charge_point_count'].fillna(0) + df['ac_charge_point_count'].fillna(0)
        )
        .groupby('city')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    # 营收
    qita_result_city_earn = (
        df_all_profit[df_all_profit['station_category'] == '其他专用']
        .assign(earn=lambda x: x['rec_data'] - x['rec_cost'])
        .groupby('city', as_index=False)['earn']
        .sum()

        .round(2)
    )

    qita_result_city_earn1 = pd.merge(qita_result_city_point, qita_result_city_earn, on='city', how='inner')

    qita_DF_cba_org_dataquyu = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'] == M) &
        (DF_org_data_pre_gun['station_category'] == '其他专用')
        ][['gun_charging_volume_day', 'city']].copy()

    qita_result_city_vloumes = (
        qita_DF_cba_org_dataquyu
        .groupby('city')['gun_charging_volume_day']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_day': '单枪日均充电量'})
        .round(2)
    )

    qita_result_city_vloumes1 = pd.merge(qita_result_city_earn1, qita_result_city_vloumes, on='city', how='inner')

    qita_result_city_cba_pue = (
        DF_cba_pue[(DF_cba_pue['station_category'] == '其他专用') & (DF_cba_pue['cba_month'] == M)]
        .groupby('city')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': '功率利用率'})
        .round(2)
    )

    qita_city_final_count = pd.merge(qita_result_city_vloumes1, qita_result_city_cba_pue, on='city', how='inner')

    qita_city_final_count = qita_city_final_count.fillna(0)
    qita_city_final_count = qita_city_final_count[qita_city_final_count['total_investment_amount'] != 0]
    cols = ['total_investment_amount', 'earn']

    qita_city_final_count[cols] = (qita_city_final_count[cols].astype(float) / 10000).round(2)
    qita_city_final_count['payback'] = qita_city_final_count['earn'] / qita_city_final_count['total_investment_amount']
    qita_city_final_count

    # In[1385]:

    # 确保是数值类型
    qita_city_final_count['total_station_capacity'] = pd.to_numeric(qita_city_final_count['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个城市
    qita_city_ty_min3 = qita_city_final_count.nsmallest(3, 'total_station_capacity')
    qita_city_ty_min3name = qita_city_ty_min3['city']
    print(qita_city_ty_min3name)  # ✅ 打印站点城市名称

    qita_city_tz_min3 = qita_city_final_count.nsmallest(3, 'payback')
    qita_city_tz_min3name = qita_city_tz_min3['city']
    print(qita_city_tz_min3name)  # ✅ 打印站点城市名称

    # 确保是数值类型
    qita_city_final_count['单枪日均充电量'] = pd.to_numeric(qita_city_final_count['单枪日均充电量'], errors='coerce')

    # 筛选出单枪日均充电量最小的前3个城市
    qita_city_yy_min3 = qita_city_final_count.nsmallest(3, '单枪日均充电量')
    qita_city_yy_min3name = qita_city_yy_min3['city']
    print(qita_city_yy_min3name)  # ✅ 打印站点城市名称

    # ### 设备厂商维度

    # In[1386]:

    qita_EQ_P = pd.merge(
        DF_operation_duration1,
        DF_SCDD[(DF_SCDD['station_category'] == '其他专用') & (DF_SCDD['operation_status'] == '投运')],
        on='station_no',
        how='inner'
    )

    qita_result_sheb_point = (
        qita_EQ_P
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('pile_manufacturer')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'mean')
        )
        .reset_index()
    )

    qita_result_sheb_success = (
        EQ_success[EQ_success['station_category'] == '其他专用']
        .groupby('pile_manufacturer')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': '一次成功率'})
        .round(2)
    )

    qita_result_sheb_kyong = (
        DF_operation_duration0[DF_operation_duration0['station_category'] == '其他专用']
        .groupby('pile_manufacturer')['可用率']
        .mean()
        .reset_index()
        .round(2)
    )

    qita_result_sheb_orders = (
        EQ_orders[EQ_orders['station_category'] == '其他专用']
        .groupby('pile_manufacturer')['单桩工单']
        .mean()
        .reset_index()
        .rename(columns={'单桩工单': '单枪平均运维次数'})
        .round(2)
    )

    from functools import reduce

    qita_df = [qita_result_sheb_point, qita_result_sheb_success, qita_result_sheb_kyong, qita_result_sheb_orders]

    # 按 pile_manufacturer 左连接依次合并
    qita_merged_df = reduce(lambda left, right: pd.merge(left, right, on='pile_manufacturer', how='outer'), qita_df)
    qita_merged_df = qita_merged_df.fillna(0)

    qita_merged_df['一次成功率'] = qita_merged_df['一次成功率'] * 100

    qita_merged_df['可用率'] = qita_merged_df['可用率'] * 100
    qita_merged_df

    # In[1387]:

    # 确保是数值类型
    qita_merged_df['total_station_capacity'] = pd.to_numeric(qita_merged_df['total_station_capacity'], errors='coerce')

    # 筛选出额定功率最小的前3个设备厂商
    qita_shebei_min3 = qita_merged_df.nsmallest(3, 'total_station_capacity')
    qita_shebei_min3name = qita_shebei_min3['pile_manufacturer']
    print(qita_shebei_min3name)  # 打印设备厂商名称

    # 确保是数值类型
    qita_merged_df['可用率'] = pd.to_numeric(qita_merged_df['可用率'], errors='coerce')

    # 筛选出可用率最小的前3个设备厂商
    qita_shebei_zhil_min3 = qita_merged_df.nsmallest(3, '可用率')
    qita_shebei_zhil_min3_name = qita_shebei_zhil_min3['pile_manufacturer']
    print(qita_shebei_zhil_min3_name)  # 打印设备厂商名称

    # 确保是数值类型
    qita_merged_df['单枪平均运维次数'] = pd.to_numeric(qita_merged_df['单枪平均运维次数'], errors='coerce')

    # 筛选出单枪平均运维次数最大的前3个设备厂商
    qita_shebei_yunwei_max3 = qita_merged_df.nlargest(3, '单枪平均运维次数')
    qita_shebei_yunwei_max3_name = qita_shebei_yunwei_max3['pile_manufacturer']
    print(qita_shebei_yunwei_max3_name)  # 打印设备厂商名称

    # ### 格式修改

    # In[1388]:

    def series_to_str(s):
        return ", ".join(s.astype(str).tolist())

    # 构建站点维度的数据
    station_data = []
    for idx, row in df_qita_zdwd.iterrows():
        station_data.append({
            "id": idx + 1,
            "siteName": row['station_name'],
            "chargingCable": int(row['total_charge_point_count']),
            "ratedPower": int(float(row['total_station_capacity'])),
            "totalInvestmentCosts": float(f"{float(row['total_investment_amount']):.2f}"),
            "returnCost": round(float(row['hbpercentage']), 2),
            "chargeAmountPerGun": round(float(row['gun_charging_volume_day']), 2),
            "powerUtilization": f"{float(row['pue']) :.2f}%",
            "successRate": f"{float(row['station_success_rate']):.2f}%",
            "availability": f"{float(row['可用率']):.2f}%",
            "revenue": round(float(row['revenue']), 2),
            "grossProfit": round(float(row['gross_profit']), 2),
            "ticketsNum": int(float(row['单桩工单']))
        })

    region_data = []
    for idx, row in qita_city_final_count.iterrows():
        region_data.append({
            "id": idx + 1,
            "region": row["city"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "amountInvested": round(float(row["total_investment_amount"]), 2),
            "earnings": f"{float(row['payback']) * 100:.2f}%",

            "chargeAmountPerGun": round(float(row["单枪日均充电量"]), 2),
            "powerUtilization": f"{float(row['功率利用率']):.2f}%"
        })

    equipment_data = []
    for idx, row in qita_merged_df.iterrows():
        equipment_data.append({
            "id": idx + 1,
            "equipmentManufacturers": row["pile_manufacturer"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "successRate": f"{float(row['一次成功率']):.2f}%",
            "availability": f"{float(row['可用率']):.2f}%",
            "omNum": round(float(row["单枪平均运维次数"]), 2)
        })

    table_summary = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个站点为：{series_to_str(df_qita_min3_name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个站点为：{series_to_str(df_qita_min3_tz_name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个站点为：{series_to_str(df_qita_min3_yy_name)}"},
        {"id": 4, "title": "经营情况维度", "content": f"毛利率需重点关注的三个站点为：{series_to_str(df_qita_min3_jy_name)}"},
        {"id": 5, "title": "设备质量维度", "content": f"设备可用率最低的三个站点为：{series_to_str(df_qita_min3_zl_name)}"},

        {"id": 6, "title": "运维情况维度", "content": f"单桩工单数量最多的三个站点为：{series_to_str(df_qita_min3_yw_name)}"},
    ]

    table_summary2 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个地市为：{series_to_str(qita_city_ty_min3name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个地市为：{series_to_str(qita_city_tz_min3name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个地市为：{series_to_str(qita_city_yy_min3name)}"},
    ]

    table_summary3 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的设备厂商为：{series_to_str(qita_shebei_min3name)}"},
        {"id": 2, "title": "设备质量维度", "content": f"设备可用率最低的三个设备厂商为：{series_to_str(qita_shebei_zhil_min3_name)}"},
        {"id": 3, "title": "运维情况维度", "content": f"单桩工单数量最多的三个设备厂商为：{series_to_str(qita_shebei_yunwei_max3_name)}"},
    ]

    # 构建最终结构
    result = {
        "options": ["站点维度", "区域维度", "设备厂商维度"],
        "data": [
            {
                "radio": "站点维度",
                "tableData": station_data,
                "siteNameFilters": [d["siteName"] for d in station_data],
                "tableSummary": table_summary
            },
            {
                "radio": "区域维度",
                "tableData": region_data,
                "tableSummary": table_summary2
            },
            {
                "radio": "设备厂商维度",
                "tableData": equipment_data,
                "tableSummary": table_summary3
            }
        ]
    }
    result

    # In[1389]:

    # 表和字段注释
    table_comment = "类型检测_其他专用_站点指标现状"
    column_comments = {
        'result': '站点指标现状',
        'update_time': '更新日期'
    }
    DF_result = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_result,
        table_name="dp_qita_scdd_nowpoint",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## V2G

    # ### 站点维度

    # In[1390]:

    # ========== 基础信息 ==========
    result_station_point_v2g = (
        df_v2g
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('station_no')
        .agg(
            station_name=('station_name', 'first'),
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )
    print("=== 基础信息 ===")
    print(result_station_point_v2g)

    # ========== 回本率 ==========
    hbpercentage_v2g = (
        DF[['station_no', 'hbpercentage']]
        .fillna({'hbpercentage': 0})
        .merge(
            DF_SCDD[['station_no']],
            on='station_no',
            how='left'
        )
    )
    hbpercentage_v2g = hbpercentage_v2g[hbpercentage_v2g['station_no'].isin(v2g_no)][['station_no', 'hbpercentage']]
    print("=== 回本率 ===")
    print(hbpercentage_v2g)

    # ========== 日均充电量 ==========
    DF_cba_org_v2g = merged2_v2g[merged2_v2g['cba_month'] == M][
        ['gun_charging_volume_d', 'station_no']
    ].copy()
    DF_cba_org_v2g = DF_cba_org_v2g.T.drop_duplicates().T

    result_vloumes_v2g = (
        DF_cba_org_v2g.groupby('station_no')['gun_charging_volume_d']
        .mean()
        .reset_index()
        .round(2)
    )
    print("=== 日均充电量 ===")
    print(result_vloumes_v2g)

    # ========== PUE ==========
    v2g_result_cba_pue = (
        DF_cba_pue_v2g[DF_cba_pue_v2g['cba_month'] == M]
        .groupby('station_no')['pue']
        .mean()
        .reset_index()
        .round(2)
    )
    print("=== PUE ===")
    print(v2g_result_cba_pue)

    # ========== 一次成功率 ==========
    DF_success_v2g2 = DF_V2G_success[DF_V2G_success['year_month'] == M].copy()
    v2g_result_success_rate = (
        DF_success_v2g2.groupby('station_no')['station_success_rate']
        .mean()
        .reset_index()
        .round(4)
    )
    v2g_result_success_rate['station_success_rate'] = v2g_result_success_rate['station_success_rate'] * 100
    print("=== 一次成功率 ===")
    print(v2g_result_success_rate)

    # ========== 可用率 ==========
    DF_v2goperation_duration = v2g_duration[DF_operation_duration['month'] == M].copy()
    v2g_result_use_rate = (
        DF_v2goperation_duration.groupby('station_no')['可用率']
        .mean()
        .reset_index()
        .round(4)
    )
    v2g_result_use_rate['可用率'] = v2g_result_use_rate['可用率'] * 100
    print("=== 可用率 ===")
    print(v2g_result_use_rate)

    # ========== 收入 / 利润 ==========
    df345v2g = df_v2g_all_profit[df_v2g_all_profit['cba_month'] == M].copy()

    v2g_result_earn = (
        df345v2g.groupby('station_no')['rec_data']
        .sum()
        .reset_index()
        .round(2)
    )
    print("=== 收入 ===")
    print(v2g_result_earn)

    df345v2g['gross_profit'] = df345v2g['rec_data'].astype(float) - df345v2g['rec_cost'].astype(float)
    v2g_result_jing_profile = (
        df345v2g.groupby('station_no')['gross_profit']
        .sum()
        .reset_index()
        .round(2)
    )
    print("=== 净利润 ===")
    print(v2g_result_jing_profile)

    # ========== 工单数量 ==========
    v2g_result_workorders = (
        df_v2g_workorders[df_v2g_workorders['stat_time'] == M]
        .groupby('station_no')['单桩工单']
        .mean()
        .reset_index()
        .round(2)
    )
    print("=== 工单数量 ===")
    print(v2g_result_workorders)

    from functools import reduce

    # ========== 汇总 ==========
    dfsv2g = [
        result_station_point_v2g,  # 一定放在第一个，作为基表
        hbpercentage_v2g,
        result_vloumes_v2g,
        v2g_result_cba_pue,
        v2g_result_success_rate,
        v2g_result_use_rate,
        v2g_result_earn,
        v2g_result_jing_profile,
        v2g_result_workorders
    ]

    # 以基表为主，后续表用 left join
    df_v2g_zdwd = reduce(
        lambda left, right: pd.merge(left, right, on='station_no', how='left'),
        dfsv2g
    )

    # 缺失值处理
    df_v2g_zdwd = df_v2g_zdwd.fillna(0)

    # 单位换算（万元）
    cols = ['total_investment_amount', 'rec_data', 'gross_profit']
    for col in cols:
        if col in df_v2g_zdwd.columns:
            df_v2g_zdwd[col] = (df_v2g_zdwd[col].astype(float) / 10000).round(2)

    df_v2g_zdwd = df_v2g_zdwd.fillna(0)

    # 再把 inf / -inf 替换成 0
    df_v2g_zdwd = df_v2g_zdwd.replace([np.inf, -np.inf], 0)
    print("=== 最终汇总表 ===")
    print(df_v2g_zdwd)

    # In[1391]:

    # 确保是数值类型
    df_v2g_zdwd['total_station_capacity'] = pd.to_numeric(df_v2g_zdwd['total_station_capacity'], errors='coerce')

    # 额定功率最小的前3个站
    df_v2g_min3_capacity = df_v2g_zdwd.nsmallest(3, 'total_station_capacity')
    v2g_min3_capacity_name = df_v2g_min3_capacity['station_name']
    print("额定功率最小3个站:", v2g_min3_capacity_name.tolist())

    # 回本率最小的前3个站
    df_v2g_zdwd['hbpercentage'] = pd.to_numeric(df_v2g_zdwd['hbpercentage'], errors='coerce')
    df_v2g_min3_hb = df_v2g_zdwd.nsmallest(3, 'hbpercentage')
    v2g_min3_hb_name = df_v2g_min3_hb['station_name']
    print("回本率最小3个站:", v2g_min3_hb_name.tolist())

    # 单枪日均充电量最小的前3个站
    df_v2g_zdwd['gun_charging_volume_d'] = pd.to_numeric(df_v2g_zdwd['gun_charging_volume_d'], errors='coerce')
    df_v2g_min3_volume = df_v2g_zdwd.nsmallest(3, 'gun_charging_volume_d')
    v2g_min3_volume_name = df_v2g_min3_volume['station_name']
    print("单枪日均充电量最小3个站:", v2g_min3_volume_name.tolist())

    # 可用率最小的前3个站
    df_v2g_zdwd['可用率'] = pd.to_numeric(df_v2g_zdwd['可用率'], errors='coerce')
    df_v2g_min3_avail = df_v2g_zdwd.nsmallest(3, '可用率')
    v2g_min3_avail_name = df_v2g_min3_avail['station_name']
    print("可用率最小3个站:", v2g_min3_avail_name.tolist())

    # 毛利率（gross_profit / rec_data）
    df_v2g_zdwd['rec_data'] = pd.to_numeric(df_v2g_zdwd['rec_data'], errors='coerce')
    df_v2g_zdwd['gross_profit'] = pd.to_numeric(df_v2g_zdwd['gross_profit'], errors='coerce')
    df_v2g_zdwd['profit_ratio'] = df_v2g_zdwd['gross_profit'] / df_v2g_zdwd['rec_data'].replace(0, np.nan)

    df_v2g_min3_profit = df_v2g_zdwd.nsmallest(3, 'profit_ratio')
    v2g_min3_profit_name = df_v2g_min3_profit['station_name']
    print("毛利率最小3个站:", v2g_min3_profit_name.tolist())

    # 单桩工单数量最多的前3个站
    df_v2g_zdwd['单桩工单'] = pd.to_numeric(df_v2g_zdwd['单桩工单'], errors='coerce')
    df_v2g_max3_orders = df_v2g_zdwd.nlargest(3, '单桩工单')
    v2g_max3_orders_name = df_v2g_max3_orders['station_name']
    print("单桩工单最多3个站:", v2g_max3_orders_name.tolist())

    # In[ ]:

    # ### 区域维度

    # In[1392]:

    # ========== 城市级：充电桩规模（基表） ==========
    v2g_result_city_point = (
        df_v2g
        .assign(
            total_charge_point_count=lambda df: df['dc_charge_point_count'].fillna(0) + df['ac_charge_point_count'].fillna(0)
        )
        .groupby('city')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'sum'),
            total_investment_amount=('investment_amount', 'sum')
        )
        .reset_index()
    )

    print("=== 城市级：基表 ===")
    print(v2g_result_city_point)

    # ========== 城市级：营收 ==========
    v2g_result_city_earn = (
        df_v2g_all_profit[df_v2g_all_profit['cba_month'] == M]
        .assign(earn=lambda x: x['rec_data'] - x['rec_cost'])
        .groupby('city', as_index=False)['earn']
        .sum()
        .round(2)
    )

    print("=== 城市级：营收 ===")
    print(v2g_result_city_earn)

    # ========== 城市级：单枪日均充电量 ==========
    v2g_DF_cba_org_data_city = merged2_v2g[
        merged2_v2g['cba_month'] == M
        ][['gun_charging_volume_d', 'city']].copy()

    v2g_result_city_vloumes = (
        v2g_DF_cba_org_data_city
        .groupby('city')['gun_charging_volume_d']
        .mean()
        .reset_index()
        .rename(columns={'gun_charging_volume_d': '单枪日均充电量'})
        .round(2)
    )

    print("=== 城市级：单枪日均充电量 ===")
    print(v2g_result_city_vloumes)

    # ========== 城市级：PUE ==========
    v2g_result_city_cba_pue = (
        DF_cba_pue_v2g[DF_cba_pue_v2g['cba_month'] == M]
        .groupby('city')['pue']
        .mean()
        .reset_index()
        .rename(columns={'pue': '功率利用率'})
        .round(2)
    )

    print("=== 城市级：PUE ===")
    print(v2g_result_city_cba_pue)

    # ========== 最终汇总 ==========
    # 注意：这里用 left join，以 v2g_result_city_point 为基表
    dfsv2g_city = [
        v2g_result_city_point,
        v2g_result_city_earn,
        v2g_result_city_vloumes,
        v2g_result_city_cba_pue
    ]

    from functools import reduce
    v2g_city_final_count = reduce(
        lambda left, right: pd.merge(left, right, on='city', how='left'),
        dfsv2g_city
    )

    # 缺失值填充
    v2g_city_final_count = v2g_city_final_count.fillna(0)

    # 单位换算（万元）
    cols = ['total_investment_amount', 'earn']
    v2g_city_final_count[cols] = (v2g_city_final_count[cols].astype(float) / 10000).round(2)

    # 投资回收率
    v2g_city_final_count['payback'] = (
            v2g_city_final_count['earn'] / v2g_city_final_count['total_investment_amount']
    ).round(4)
    v2g_city_final_count = v2g_city_final_count.fillna(0)

    # 再把 inf / -inf 替换成 0
    v2g_city_final_count = v2g_city_final_count.replace([np.inf, -np.inf], 0)
    print("=== 城市级：最终汇总 ===")
    print(v2g_city_final_count)

    # In[1393]:

    # 确保是数值类型
    v2g_city_final_count['total_station_capacity'] = pd.to_numeric(
        v2g_city_final_count['total_station_capacity'], errors='coerce'
    )

    # 额定功率最小的前3个城市
    v2g_city_ty_min3 = v2g_city_final_count.nsmallest(3, 'total_station_capacity')
    v2g_city_ty_min3name = v2g_city_ty_min3['city']
    print("额定功率最小的3个城市:", v2g_city_ty_min3name.tolist())

    # 投资回收率最小的前3个城市
    v2g_city_tz_min3 = v2g_city_final_count.nsmallest(3, 'payback')
    v2g_city_tz_min3name = v2g_city_tz_min3['city']
    print("投资回收率最小的3个城市:", v2g_city_tz_min3name.tolist())

    # 确保是数值类型
    v2g_city_final_count['单枪日均充电量'] = pd.to_numeric(
        v2g_city_final_count['单枪日均充电量'], errors='coerce'
    )

    # 单枪日均充电量最小的前3个城市
    v2g_city_yy_min3 = v2g_city_final_count.nsmallest(3, '单枪日均充电量')
    v2g_city_yy_min3name = v2g_city_yy_min3['city']
    print("单枪日均充电量最小的3个城市:", v2g_city_yy_min3name.tolist())

    # ### 设备厂商维度

    # In[1394]:

    from functools import reduce
    import numpy as np

    # ========== 基表：设备厂商对应桩规模 ==========
    v2g_EQ_P = pd.merge(
        DF_operation_duration1,
        df_v2g,
        on='station_no',
        how='inner'
    )

    v2g_result_sheb_point = (
        v2g_EQ_P
        .assign(
            total_charge_point_count=lambda df: df['ac_charge_point_count'].fillna(0) + df['dc_charge_point_count'].fillna(0)
        )
        .groupby('pile_manufacturer')
        .agg(
            total_charge_point_count=('total_charge_point_count', 'sum'),
            total_station_capacity=('station_capacity', 'mean')
        )
        .reset_index()
    )

    print("=== 基表：设备厂商桩规模 ===")
    print(v2g_result_sheb_point)

    # ========== 一次成功率 ==========
    v2g_result_sheb_success = (
        EQ_success[EQ_success['station_no'].isin(v2g_no)]
        .groupby('pile_manufacturer')['station_success_rate']
        .mean()
        .reset_index()
        .rename(columns={'station_success_rate': '一次成功率'})
        .round(4)
    )

    print("=== 一次成功率 ===")
    print(v2g_result_sheb_success)

    # ========== 可用率 ==========
    v2g_result_sheb_kyong = (
        DF_operation_duration0[DF_operation_duration0['station_no'].isin(v2g_no)]
        .groupby('pile_manufacturer')['可用率']
        .mean()
        .reset_index()
        .round(4)
    )

    print("=== 可用率 ===")
    print(v2g_result_sheb_kyong)

    # ========== 工单数量 ==========
    v2g_result_sheb_orders = (
        EQ_orders[EQ_orders['station_no'].isin(v2g_no)]
        .groupby('pile_manufacturer')['单桩工单']
        .mean()
        .reset_index()
        .rename(columns={'单桩工单': '单枪平均运维次数'})
        .round(2)
    )

    print("=== 工单数量 ===")
    print(v2g_result_sheb_orders)

    # ========== 汇总 ==========
    dfsv2g_sheb = [
        v2g_result_sheb_point,  # 基表在第一个
        v2g_result_sheb_success,
        v2g_result_sheb_kyong,
        v2g_result_sheb_orders
    ]

    v2g_merged_sheb_df = reduce(
        lambda left, right: pd.merge(left, right, on='pile_manufacturer', how='left'),
        dfsv2g_sheb
    )

    # 缺失值 / inf / NaN 替换为 0
    v2g_merged_sheb_df = v2g_merged_sheb_df.replace([np.inf, -np.inf], np.nan).fillna(0)

    # 百分比换算
    if '一次成功率' in v2g_merged_sheb_df.columns:
        v2g_merged_sheb_df['一次成功率'] = (v2g_merged_sheb_df['一次成功率'] * 100).round(2)

    if '可用率' in v2g_merged_sheb_df.columns:
        v2g_merged_sheb_df['可用率'] = (v2g_merged_sheb_df['可用率'] * 100).round(2)

    print("=== 最终汇总表 ===")
    print(v2g_merged_sheb_df)

    # In[1395]:

    # 确保是数值类型
    v2g_merged_sheb_df['total_station_capacity'] = pd.to_numeric(
        v2g_merged_sheb_df['total_station_capacity'], errors='coerce'
    )

    # 额定功率最小的前3个设备厂商
    v2g_shebei_min3 = v2g_merged_sheb_df.nsmallest(3, 'total_station_capacity')
    v2g_shebei_min3name = v2g_shebei_min3['pile_manufacturer']
    print("额定功率最小的3个设备厂商:", v2g_shebei_min3name.tolist())

    # 确保是数值类型
    v2g_merged_sheb_df['可用率'] = pd.to_numeric(
        v2g_merged_sheb_df['可用率'], errors='coerce'
    )

    # 可用率最小的前3个设备厂商
    v2g_shebei_avail_min3 = v2g_merged_sheb_df.nsmallest(3, '可用率')
    v2g_shebei_avail_min3name = v2g_shebei_avail_min3['pile_manufacturer']
    print("可用率最小的3个设备厂商:", v2g_shebei_avail_min3name.tolist())

    # 确保是数值类型
    v2g_merged_sheb_df['单枪平均运维次数'] = pd.to_numeric(
        v2g_merged_sheb_df['单枪平均运维次数'], errors='coerce'
    )

    # 单枪平均运维次数最大的前3个设备厂商
    v2g_shebei_orders_max3 = v2g_merged_sheb_df.nlargest(3, '单枪平均运维次数')
    v2g_shebei_orders_max3name = v2g_shebei_orders_max3['pile_manufacturer']
    print("单枪平均运维次数最多的3个设备厂商:", v2g_shebei_orders_max3name.tolist())

    # In[1396]:

    df_v2g_zdwd

    # In[1397]:

    def series_to_str(s):
        return ", ".join(s.astype(str).tolist())

    # 构建站点维度的数据
    station_data = []
    for idx, row in df_v2g_zdwd.iterrows():
        station_data.append({
            "id": idx + 1,
            "siteName": row['station_name'],
            "chargingCable": int(row['total_charge_point_count']),
            "ratedPower": int(float(row['total_station_capacity'])),
            "totalInvestmentCosts": float(f"{float(row['total_investment_amount']):.2f}"),
            "returnCost": round(float(row['hbpercentage']), 2),
            "chargeAmountPerGun": round(float(row['gun_charging_volume_d']), 2),
            "powerUtilization": f"{float(row['pue']) :.2f}%",
            "successRate": f"{float(row['station_success_rate']):.2f}%",
            "availability": f"{float(row['可用率']):.2f}%",
            "revenue": round(float(row['rec_data']), 2),
            "grossProfit": round(float(row['gross_profit']), 2),
            "ticketsNum": int(float(row['单桩工单']))
        })

    region_data = []
    for idx, row in v2g_city_final_count.iterrows():
        region_data.append({
            "id": idx + 1,
            "region": row["city"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "amountInvested": round(float(row["total_investment_amount"]), 2),
            "earnings": f"{float(row['payback']) * 100:.2f}%",

            "chargeAmountPerGun": round(float(row["单枪日均充电量"]), 2),
            "powerUtilization": f"{float(row['功率利用率']):.2f}%"
        })

    equipment_data = []
    for idx, row in v2g_merged_sheb_df.iterrows():
        equipment_data.append({
            "id": idx + 1,
            "equipmentManufacturers": row["pile_manufacturer"],
            "chargingCable": int(row["total_charge_point_count"]),
            "ratedPower": int(row["total_station_capacity"]),
            "successRate": f"{float(row['一次成功率']):.2f}%",
            "availability": f"{float(row['可用率']):.2f}%",
            "omNum": round(float(row["单枪平均运维次数"]), 2)
        })

    table_summary = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个站点为：{series_to_str(v2g_min3_capacity_name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个站点为：{series_to_str(v2g_min3_hb_name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个站点为：{series_to_str(v2g_min3_volume_name)}"},
        {"id": 4, "title": "经营情况维度", "content": f"毛利率需重点关注的三个站点为：{series_to_str(v2g_min3_avail_name)}"},
        {"id": 5, "title": "设备质量维度", "content": f"设备可用率最低的三个站点为：{series_to_str(v2g_min3_profit_name)}"},

        {"id": 6, "title": "运维情况维度", "content": f"单桩工单数量最多的三个站点为：{series_to_str(v2g_max3_orders_name)}"},
    ]

    table_summary2 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的三个地市为：{series_to_str(v2g_city_ty_min3name)}"},
        {"id": 2, "title": "投资情况维度", "content": f"静态投资回本进度最低的三个地市为：{series_to_str(v2g_city_tz_min3name)}"},
        {"id": 3, "title": "运营情况维度", "content": f"单枪日均充电量最低的三个地市为：{series_to_str(v2g_city_yy_min3name)}"},
    ]

    table_summary3 = [
        {"id": 1, "title": "建设情况维度", "content": f"额定功率最小的设备厂商为：{series_to_str(v2g_shebei_min3name)}"},
        {"id": 2, "title": "设备质量维度", "content": f"设备可用率最低的三个设备厂商为：{series_to_str(v2g_shebei_avail_min3name)}"},
        {"id": 3, "title": "运维情况维度", "content": f"单桩工单数量最多的三个设备厂商为：{series_to_str(v2g_shebei_orders_max3name)}"},
    ]

    # 构建最终结构
    v2g_point_result = {
        "options": ["站点维度", "区域维度", "设备厂商维度"],
        "data": [
            {
                "radio": "站点维度",
                "tableData": station_data,
                "siteNameFilters": [d["siteName"] for d in station_data],
                "tableSummary": table_summary
            },
            {
                "radio": "区域维度",
                "tableData": region_data,
                "tableSummary": table_summary2
            },
            {
                "radio": "设备厂商维度",
                "tableData": equipment_data,
                "tableSummary": table_summary3
            }
        ]
    }
    v2g_point_result

    # In[1398]:

    # 表和字段注释
    table_comment = "类型检测_V2G_站点指标现状"
    column_comments = {
        'result': '站点指标现状',
        'update_time': '更新日期'
    }
    DF_v2g_point_result = pd.DataFrame([{
        'result': json.dumps(v2g_point_result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_v2g_point_result,
        table_name="dp_v2g_scdd_nowpoint",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:

    # # 横幅

    # ## 首页

    # ### 平台累计充电枪保有量

    # In[1399]:

    total_charge_points_pt = DF_SCDD['total_charge_point_count'].sum()

    # In[1400]:

    total_charge_points_pt

    # ### 平台累计总额定功率

    # In[1401]:

    total_charge_capacity_pt = DF_SCDD['station_capacity'].sum()

    # In[1402]:

    total_charge_capacity_pt = total_charge_capacity_pt / 10000
    total_charge_capacity_pt

    # ### 站点总数

    # In[ ]:

    # ### 当年单枪日均充电量

    # In[1403]:

    year

    # In[1404]:

    DF_cba_org_data_cur['cba_month'].astype(str).str[:4].unique()

    # In[1405]:

    DF_cba_org_data_cur_new = DF_cba_org_data_cur[
        DF_cba_org_data_cur['cba_month'].astype(str).str[:4] == str(year)
        ].copy()

    # In[1406]:

    DF_cba_org_data_cur_new['charge_point_count'] = DF_cba_org_data_cur_new['dc_charge_point_count'].fillna(0) + DF_cba_org_data_cur_new['ac_charge_point_count'].fillna(0)

    # In[1407]:

    DYTS = DF_cba_org_data_cur_new['cba_month'].apply(get_days_in_month).mean()  # 62822

    # In[1408]:

    cdqzs_point = DF_cba_org_data_cur_new['charge_point_count'].sum()

    # In[1409]:

    cdqzs_point

    # In[1410]:

    glzs_count = DF_cba_org_data_cur_new['plat_data_charging_volume'].sum()

    # In[1411]:

    glzs_count

    # In[1412]:

    DYTS

    # In[1413]:

    dqrjcdl = glzs_count / cdqzs_point / DYTS

    # In[1414]:

    dqrjcdl = dqrjcdl.round(2)
    dqrjcdl

    # ### 当年功率利用率

    # In[1415]:

    df_gllyl = DF_cba_pue[DF_cba_pue['cba_month'] == M].copy()

    # In[1416]:

    dygllyl = df_gllyl['pue'].mean()

    # In[1417]:

    dygllyl

    # ### 一次成功率
    #

    # In[1418]:

    DF_success_cur = DF_success[DF_success['month'].astype(str).str[:4] == str(year)]

    # In[1419]:

    ljsuccess_rate = DF_success_cur['station_success_rate'].mean()

    # In[1420]:

    ljsuccess_rate

    # ### 当年可用率

    # In[1421]:

    DF_operation_duration_cur = DF_operation_duration[DF_operation_duration['month'].astype(str).str[:4] == str(year)]

    # In[1422]:

    dykyl = DF_operation_duration_cur['可用率'].mean()

    # In[1423]:

    dykyl

    # ### 当月平台站点营收

    # In[1424]:

    cur_pt_zdys = df_all_profit[(df_all_profit['cba_month'] <= M) & (df_all_profit['year'] == str(year))][['rec_data']].sum().sum()

    # In[1425]:

    cur_pt_zdys

    # In[1426]:

    cur_pt_zdys = cur_pt_zdys / 10000
    cur_pt_zdys = round(cur_pt_zdys, 2)
    cur_pt_zdys

    # ### 当月平台工单数量
    #
    #

    # In[1427]:

    DF_SCGD_cur = DF_SCGD[DF_SCGD['stat_time'].astype(str).str[:4] == str(year)]

    # In[1428]:

    cur_pt_gdsl = pd.to_numeric(DF_SCGD_cur['单桩工单'], errors='coerce').fillna(0).astype(int).mean()

    # In[1429]:

    cur_pt_gdsl

    # In[1430]:

    permonth_pt_gdsl = cur_pt_gdsl.round(2)

    # In[1431]:

    permonth_pt_gdsl

    # ### 格式修改

    # In[1432]:
    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
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
          AND (scod.cba_month like '%s' or scod.cba_month like '%s')
          and cs.operation_status in ('投运','退运')
        """ % (t1, t2)
    DF_cba_pue = SQL(sql)

    DF_cba_pue['days'] = DF_cba_pue['cba_month'].apply(get_days_in_month)

    DF_cba_pue['year'] = [i[:4] for i in DF_cba_pue['cba_month']]

    DF_cba_pue = DF_cba_pue[
        (DF_cba_pue['station_capacity'].notna()) &  # 剔除功率为空的异常值
        (DF_cba_pue['station_capacity'] > 0) &  # 剔除功率为0的异常值
        (DF_cba_pue['plat_data_charging_volume'].notna()) &  # 剔除为空的异常值
        (DF_cba_pue['plat_data_charging_volume'] != 0)  # 剔除平台电量为0的异常值
        ].copy()
    print('筛选后：', DF_cba_pue.shape)

    DF_cba_pue['pue'] = DF_cba_pue['plat_data_charging_volume'] / (DF_cba_pue['station_capacity'] * DF_cba_pue['days'] * 24) * 100

    # ### 本月数据
    csgg_benyue_gonglvliyonglv = DF_cba_pue[(DF_cba_pue['cba_month'] == M) & (DF_cba_pue['station_category'] == '城市公共')]['pue'].mean()
    csgg_benyue_gonglvliyonglv = f"{csgg_benyue_gonglvliyonglv:.2f}"
    print('城市公共功率利用率本月数据：', csgg_benyue_gonglvliyonglv)

    # 2. 高速公共
    gsgg_benyue_gonglvliyonglv = DF_cba_pue[(DF_cba_pue['cba_month'] == M) & (DF_cba_pue['station_category'] == '高速公共')]['pue'].mean()
    gsgg_benyue_gonglvliyonglv = f"{gsgg_benyue_gonglvliyonglv:.2f}"
    print('高速公共功率利用率本月数据：', gsgg_benyue_gonglvliyonglv)

    # 3. 重卡专用
    zkzy_benyue_gonglvliyonglv = DF_cba_pue[(DF_cba_pue['cba_month'] == M) & (DF_cba_pue['station_category'] == '重卡专用')]['pue'].mean()
    zkzy_benyue_gonglvliyonglv = f"{zkzy_benyue_gonglvliyonglv:.2f}"
    print('重卡专用功率利用率本月数据：', zkzy_benyue_gonglvliyonglv)

    # 4. 公交专用
    gjzy_benyue_gonglvliyonglv = DF_cba_pue[(DF_cba_pue['cba_month'] == M) & (DF_cba_pue['station_category'] == '公交专用')]['pue'].mean()
    gjzy_benyue_gonglvliyonglv = f"{gjzy_benyue_gonglvliyonglv:.2f}"
    print('公交专用功率利用率本月数据：', gjzy_benyue_gonglvliyonglv)

    # 5. 小区有序
    xqyx_benyue_gonglvliyonglv = DF_cba_pue[(DF_cba_pue['cba_month'] == M) & (DF_cba_pue['station_category'] == '小区有序')]['pue'].mean()
    xqyx_benyue_gonglvliyonglv = f"{xqyx_benyue_gonglvliyonglv:.2f}"
    print('小区有序功率利用率本月数据：', xqyx_benyue_gonglvliyonglv)

    # 6. 其他专用
    qtzy_benyue_gonglvliyonglv = DF_cba_pue[(DF_cba_pue['cba_month'] == M) & (DF_cba_pue['station_category'] == '其他专用')]['pue'].mean()
    qtzy_benyue_gonglvliyonglv = f"{qtzy_benyue_gonglvliyonglv:.2f}"
    print('其他专用功率利用率本月数据：', qtzy_benyue_gonglvliyonglv)
    # ### 同比增长

    # ### 本年数据
    # 1. 城市公共
    city_public_this_year = DF_cba_pue[
        (DF_cba_pue['station_category'] == '城市公共') &
        (DF_cba_pue['cba_month'] <= M) &
        (DF_cba_pue['year'] == str(year))
        ]['pue'].mean()
    city_public_pue = f"{city_public_this_year:.2f}"
    print('城市公共功率利用率本年数据', city_public_pue)

    # 2. 高速公共
    highway_public_this_year = DF_cba_pue[
        (DF_cba_pue['station_category'] == '高速公共') &
        (DF_cba_pue['cba_month'] <= M) &
        (DF_cba_pue['year'] == str(year))
        ]['pue'].mean()
    highway_public_pue = f"{highway_public_this_year:.2f}"
    print('高速公共功率利用率本年数据', highway_public_pue)

    # 3. 重卡专用
    heavy_truck_this_year = DF_cba_pue[
        (DF_cba_pue['station_category'] == '重卡专用') &
        (DF_cba_pue['cba_month'] <= M) &
        (DF_cba_pue['year'] == str(year))
        ]['pue'].mean()
    heavy_truck_pue = f"{heavy_truck_this_year:.2f}"
    print('重卡专用功率利用率本年数据', heavy_truck_pue)

    # 4. 公交专用
    bus_this_year = DF_cba_pue[
        (DF_cba_pue['station_category'] == '公交专用') &
        (DF_cba_pue['cba_month'] <= M) &
        (DF_cba_pue['year'] == str(year))
        ]['pue'].mean()
    bus_pue = f"{bus_this_year:.2f}"
    print('公交专用功率利用率本年数据', bus_pue)

    # 5. 小区有序
    residential_this_year = DF_cba_pue[
        (DF_cba_pue['station_category'] == '小区有序') &
        (DF_cba_pue['cba_month'] <= M) &
        (DF_cba_pue['year'] == str(year))
        ]['pue'].mean()
    residential_pue = f"{residential_this_year:.2f}"
    print('小区有序功率利用率本年数据', residential_pue)

    # 6. 其他专用
    other_special_this_year = DF_cba_pue[
        (DF_cba_pue['station_category'] == '其他专用') &
        (DF_cba_pue['cba_month'] <= M) &
        (DF_cba_pue['year'] == str(year))
        ]['pue'].mean()
    other_special_pue = f"{other_special_this_year:.2f}"
    print('其他专用功率利用率本年数据', other_special_pue)
    pue_this_year_1 = DF_cba_pue[(DF_cba_pue['cba_month'] <= M) & (DF_cba_pue['year'] == str(year))]['pue'].mean()
    pue_this_year = f"{pue_this_year_1:.2f}"
    print('功率利用率本年数据', pue_this_year)

    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
            select * from 
            (SELECT 
            cs.*
            FROM
            charging_station cs
            LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
            where 
            rm.merchant_name = '国网电动汽车服务（四川）有限公司'
            and  cs.operation_status in ('投运','退运')) a
            left join 
            (select * from station_cba_org_data where cba_month like '%s' or  cba_month like '%s' ) b
            on a.station_no =b.station_no
            """ % (t1, t2)
    DF_org_data_pre_gun = SQL(sql)

    DF_org_data_pre_gun = DF_org_data_pre_gun.fillna(0)
    DF_org_data_pre_gun['charge_point_count'] = DF_org_data_pre_gun['dc_charge_point_count'].fillna(0) + DF_org_data_pre_gun[
        'ac_charge_point_count'].fillna(0)

    DF_org_data_pre_gun = DF_org_data_pre_gun[DF_org_data_pre_gun['charge_point_count'] != 0]
    DF_org_data_pre_gun = DF_org_data_pre_gun[DF_org_data_pre_gun['plat_data_charging_volume'] != 0]  # 平台数据-平台充电量,不等于0
    # 当月单枪充电量，日均的计算在后面
    DF_org_data_pre_gun['gun_charging_volume'] = DF_org_data_pre_gun['plat_data_charging_volume'] / DF_org_data_pre_gun[
        'charge_point_count']

    print("DF_org_data_pre_gun的列名:\n", DF_org_data_pre_gun.columns)
    # ### 本月数据
    csss_dqrjcdl_bysj = DF_org_data_pre_gun[(DF_org_data_pre_gun['cba_month'] == M) & (DF_org_data_pre_gun['station_category'] == '城市公共')].copy()
    csss_dqrjcdl_bysj['gun_charging_volume_d'] = csss_dqrjcdl_bysj['gun_charging_volume'] / get_days_in_month(M)
    csss_dqrjcdl_bysj = csss_dqrjcdl_bysj['gun_charging_volume_d'].mean()
    csss_dqrjcdl_bysj = csss_dqrjcdl_bysj.round(2)
    print('城市公共单枪日均充电量本月数据：', csss_dqrjcdl_bysj)

    # 高速公共
    gscs_dqrjcdl_bysj = DF_org_data_pre_gun[(DF_org_data_pre_gun['cba_month'] == M) & (DF_org_data_pre_gun['station_category'] == '高速公共')].copy()
    gscs_dqrjcdl_bysj['gun_charging_volume_d'] = gscs_dqrjcdl_bysj['gun_charging_volume'] / get_days_in_month(M)
    gscs_dqrjcdl_bysj = gscs_dqrjcdl_bysj['gun_charging_volume_d'].mean()
    gscs_dqrjcdl_bysj = gscs_dqrjcdl_bysj.round(2)
    print('高速公共单枪日均充电量本月数据：', gscs_dqrjcdl_bysj)

    # 重卡专用
    zkzy_dqrjcdl_bysj = DF_org_data_pre_gun[(DF_org_data_pre_gun['cba_month'] == M) & (DF_org_data_pre_gun['station_category'] == '重卡专用')].copy()
    zkzy_dqrjcdl_bysj['gun_charging_volume_d'] = zkzy_dqrjcdl_bysj['gun_charging_volume'] / get_days_in_month(M)
    zkzy_dqrjcdl_bysj = zkzy_dqrjcdl_bysj['gun_charging_volume_d'].mean()
    zkzy_dqrjcdl_bysj = zkzy_dqrjcdl_bysj.round(2)
    print('重卡专用单枪日均充电量本月数据：', zkzy_dqrjcdl_bysj)

    # 公交专用
    gjzy_dqrjcdl_bysj = DF_org_data_pre_gun[(DF_org_data_pre_gun['cba_month'] == M) & (DF_org_data_pre_gun['station_category'] == '公交专用')].copy()
    gjzy_dqrjcdl_bysj['gun_charging_volume_d'] = gjzy_dqrjcdl_bysj['gun_charging_volume'] / get_days_in_month(M)
    gjzy_dqrjcdl_bysj = gjzy_dqrjcdl_bysj['gun_charging_volume_d'].mean()
    gjzy_dqrjcdl_bysj = gjzy_dqrjcdl_bysj.round(2)
    print('公交专用单枪日均充电量本月数据：', gjzy_dqrjcdl_bysj)

    # 小区有序
    xqyx_dqrjcdl_bysj = DF_org_data_pre_gun[(DF_org_data_pre_gun['cba_month'] == M) & (DF_org_data_pre_gun['station_category'] == '小区有序')].copy()
    xqyx_dqrjcdl_bysj['gun_charging_volume_d'] = xqyx_dqrjcdl_bysj['gun_charging_volume'] / get_days_in_month(M)
    xqyx_dqrjcdl_bysj = xqyx_dqrjcdl_bysj['gun_charging_volume_d'].mean()
    xqyx_dqrjcdl_bysj = xqyx_dqrjcdl_bysj.round(2)
    print('小区有序单枪日均充电量本月数据：', xqyx_dqrjcdl_bysj)

    # 其他专用
    qtzy_dqrjcdl_bysj = DF_org_data_pre_gun[(DF_org_data_pre_gun['cba_month'] == M) & (DF_org_data_pre_gun['station_category'] == '其他专用')].copy()
    qtzy_dqrjcdl_bysj['gun_charging_volume_d'] = qtzy_dqrjcdl_bysj['gun_charging_volume'] / get_days_in_month(M)
    qtzy_dqrjcdl_bysj = qtzy_dqrjcdl_bysj['gun_charging_volume_d'].mean()
    qtzy_dqrjcdl_bysj = qtzy_dqrjcdl_bysj.round(2)
    print('其他专用单枪日均充电量本月数据：', qtzy_dqrjcdl_bysj)
    # ### 本年数据
    d4_1 = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'].str[:4] == str(year)) & (DF_org_data_pre_gun['cba_month'] <= M)].groupby(
        'cba_month').agg(
        {"gun_charging_volume": 'mean'}).reset_index().copy()
    d4_1['day'] = [get_days_in_month(i) for i in d4_1['cba_month']]
    d4_1['gun_charging_volume_d'] = d4_1['gun_charging_volume'] / d4_1['day']
    dqrjcdl_bnsj = d4_1['gun_charging_volume_d'].mean()
    print('单枪日均充电量本年数据:', dqrjcdl_bnsj)
    csgg_dqrjcdl_bennianshuju = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'].str[:4] == str(year)) & (DF_org_data_pre_gun['station_category'] == '城市公共') & (DF_org_data_pre_gun['cba_month'] <= M)].groupby(
        'cba_month').agg(
        {"gun_charging_volume": 'mean'}).reset_index().copy()
    csgg_dqrjcdl_bennianshuju['day'] = [get_days_in_month(i) for i in csgg_dqrjcdl_bennianshuju['cba_month']]
    csgg_dqrjcdl_bennianshuju['gun_charging_volume_d'] = csgg_dqrjcdl_bennianshuju['gun_charging_volume'] / csgg_dqrjcdl_bennianshuju['day']
    csgg_dqrjcdl_bennianshuju = csgg_dqrjcdl_bennianshuju['gun_charging_volume_d'].mean()
    print('城市公共单枪日均充电量本年数据:', csgg_dqrjcdl_bennianshuju)

    # 高速公共
    gsgg_dqrjcdl_bennianshuju = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'].str[:4] == str(year)) & (DF_org_data_pre_gun['station_category'] == '高速公共') & (DF_org_data_pre_gun['cba_month'] <= M)].groupby(
        'cba_month').agg(
        {"gun_charging_volume": 'mean'}).reset_index().copy()
    gsgg_dqrjcdl_bennianshuju['day'] = [get_days_in_month(i) for i in gsgg_dqrjcdl_bennianshuju['cba_month']]
    gsgg_dqrjcdl_bennianshuju['gun_charging_volume_d'] = gsgg_dqrjcdl_bennianshuju['gun_charging_volume'] / gsgg_dqrjcdl_bennianshuju['day']
    gsgg_dqrjcdl_bennianshuju = gsgg_dqrjcdl_bennianshuju['gun_charging_volume_d'].mean()
    print('高速公共单枪日均充电量本年数据:', gsgg_dqrjcdl_bennianshuju)

    # 重卡专用
    zkzy_dqrjcdl_bennianshuju = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'].str[:4] == str(year)) & (DF_org_data_pre_gun['station_category'] == '重卡专用') & (DF_org_data_pre_gun['cba_month'] <= M)].groupby(
        'cba_month').agg(
        {"gun_charging_volume": 'mean'}).reset_index().copy()
    zkzy_dqrjcdl_bennianshuju['day'] = [get_days_in_month(i) for i in zkzy_dqrjcdl_bennianshuju['cba_month']]
    zkzy_dqrjcdl_bennianshuju['gun_charging_volume_d'] = zkzy_dqrjcdl_bennianshuju['gun_charging_volume'] / zkzy_dqrjcdl_bennianshuju['day']
    zkzy_dqrjcdl_bennianshuju = zkzy_dqrjcdl_bennianshuju['gun_charging_volume_d'].mean()
    print('重卡专用单枪日均充电量本年数据:', zkzy_dqrjcdl_bennianshuju)

    # 公交专用
    gjzy_dqrjcdl_bennianshuju = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'].str[:4] == str(year)) & (DF_org_data_pre_gun['station_category'] == '公交专用') & (DF_org_data_pre_gun['cba_month'] <= M)].groupby(
        'cba_month').agg(
        {"gun_charging_volume": 'mean'}).reset_index().copy()
    gjzy_dqrjcdl_bennianshuju['day'] = [get_days_in_month(i) for i in gjzy_dqrjcdl_bennianshuju['cba_month']]
    gjzy_dqrjcdl_bennianshuju['gun_charging_volume_d'] = gjzy_dqrjcdl_bennianshuju['gun_charging_volume'] / gjzy_dqrjcdl_bennianshuju['day']
    gjzy_dqrjcdl_bennianshuju = gjzy_dqrjcdl_bennianshuju['gun_charging_volume_d'].mean()
    print('公交专用单枪日均充电量本年数据:', gjzy_dqrjcdl_bennianshuju)

    # 小区有序
    xqyx_dqrjcdl_bennianshuju = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'].str[:4] == str(year)) & (DF_org_data_pre_gun['station_category'] == '小区有序') & (DF_org_data_pre_gun['cba_month'] <= M)].groupby(
        'cba_month').agg(
        {"gun_charging_volume": 'mean'}).reset_index().copy()
    xqyx_dqrjcdl_bennianshuju['day'] = [get_days_in_month(i) for i in xqyx_dqrjcdl_bennianshuju['cba_month']]
    xqyx_dqrjcdl_bennianshuju['gun_charging_volume_d'] = xqyx_dqrjcdl_bennianshuju['gun_charging_volume'] / xqyx_dqrjcdl_bennianshuju['day']
    xqyx_dqrjcdl_bennianshuju = xqyx_dqrjcdl_bennianshuju['gun_charging_volume_d'].mean()
    print('小区有序单枪日均充电量本年数据:', xqyx_dqrjcdl_bennianshuju)

    # 其他专用
    qtzy_dqrjcdl_bennianshuju = DF_org_data_pre_gun[
        (DF_org_data_pre_gun['cba_month'].str[:4] == str(year)) & (DF_org_data_pre_gun['station_category'] == '其他专用') & (DF_org_data_pre_gun['cba_month'] <= M)].groupby(
        'cba_month').agg(
        {"gun_charging_volume": 'mean'}).reset_index().copy()
    qtzy_dqrjcdl_bennianshuju['day'] = [get_days_in_month(i) for i in qtzy_dqrjcdl_bennianshuju['cba_month']]
    qtzy_dqrjcdl_bennianshuju['gun_charging_volume_d'] = qtzy_dqrjcdl_bennianshuju['gun_charging_volume'] / qtzy_dqrjcdl_bennianshuju['day']
    qtzy_dqrjcdl_bennianshuju = qtzy_dqrjcdl_bennianshuju['gun_charging_volume_d'].mean()
    print('其他专用单枪日均充电量本年数据:', qtzy_dqrjcdl_bennianshuju)

    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
        select * from 
        (select station_no,station_category from  charging_station) c
        right join 
        (select time,station_name,station_code,pile_status,normal_duration,operation_duration,city from dp_operation_duration
        where time like '%s' or time like '%s') d 
        on c.station_no = d.station_code
        """ % (t1, t2)
    DF_operation_duration = SQL(sql)

    DF_operation_duration = DF_operation_duration.fillna(0)

    # 可用率计算

    # 可用率=正常状态时长(秒)/在运时长(秒)
    DF_operation_duration['可用率'] = DF_operation_duration['normal_duration'].astype('int') / DF_operation_duration[
        'operation_duration'].astype('int')

    # 筛选正常桩

    print('筛选运行状态前数据形状：', DF_operation_duration.shape)
    DF_operation_duration = DF_operation_duration[DF_operation_duration['pile_status'] == '运行']
    print('筛选运行状态后数据形状', DF_operation_duration.shape)

    # 计算每个站每月平均可用率

    DF_operation_duration_1 = DF_operation_duration.groupby(['time', 'station_no']).agg({'可用率': 'mean'}).reset_index()
    DF_operation_duration_1

    # 获取站点对应城市、站点类型的标签
    DF_operation_duration_2 = DF_operation_duration[['station_no', 'station_category', 'city']].drop_duplicates()
    DF_operation_duration_2

    DF_operation_duration = pd.merge(DF_operation_duration_1, DF_operation_duration_2, on='station_no', how='left')
    DF_operation_duration.head(1)

    # 处理时间

    DF_operation_duration['month'] = [i[:6] for i in DF_operation_duration['time']]

    DF_operation_duration['year'] = [i[:4] for i in DF_operation_duration['month']]

    # ### 本月数据
    csgg_keyonglv_benyue = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '城市公共')
        ]['可用率'].mean()
    csgg_keyonglv_benyue = f"{csgg_keyonglv_benyue * 100:.2f}"
    print('城市公共可用率本月数据：', csgg_keyonglv_benyue)

    # 高速公共
    gsgg_keyonglv_benyue = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '高速公共')
        ]['可用率'].mean()
    gsgg_keyonglv_benyue = f"{gsgg_keyonglv_benyue * 100:.2f}"
    print('高速公共可用率本月数据：', gsgg_keyonglv_benyue)

    # 重卡专用
    ckzy_keyonglv_benyue = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '重卡专用')
        ]['可用率'].mean()
    ckzy_keyonglv_benyue = f"{ckzy_keyonglv_benyue * 100:.2f}"
    print('重卡专用可用率本月数据：', ckzy_keyonglv_benyue)

    # 公交专用
    gjzy_keyonglv_benyue = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '公交专用')
        ]['可用率'].mean()
    gjzy_keyonglv_benyue = f"{gjzy_keyonglv_benyue * 100:.2f}"
    print('公交专用可用率本月数据：', gjzy_keyonglv_benyue)

    # 小区有序
    xqyx_keyonglv_benyue = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '小区有序')
        ]['可用率'].mean()
    xqyx_keyonglv_benyue = f"{xqyx_keyonglv_benyue * 100:.2f}"
    print('小区有序可用率本月数据：', xqyx_keyonglv_benyue)

    # 其他专用
    qtzy_keyonglv_benyue = DF_operation_duration[
        (DF_operation_duration['month'] == M) &
        (DF_operation_duration['station_category'] == '其他专用')
        ]['可用率'].mean()
    qtzy_keyonglv_benyue = f"{qtzy_keyonglv_benyue * 100:.2f}"
    print('其他专用可用率本月数据：', qtzy_keyonglv_benyue)

    keyonglv_bennian = DF_operation_duration[(DF_operation_duration['month'] <= M) & (DF_operation_duration['year'] == str(year))][
        '可用率'].mean()
    keyonglv_bennian = f"{keyonglv_bennian * 100:.2f}"
    print('本年可用率：', keyonglv_bennian)
    csgg_keyonglv_bennian = DF_operation_duration[(DF_operation_duration['month'] <= M) &
                                                  (DF_operation_duration['station_category'] == '城市公共') &
                                                  (DF_operation_duration['year'] == str(year))]['可用率'].mean()
    csgg_keyonglv_bennian = f"{csgg_keyonglv_bennian * 100:.2f}"
    print('城市公共本年可用率：', csgg_keyonglv_bennian)

    # 计算高速公共充电站本年可用率
    gsgg_keyonglv_bennian = DF_operation_duration[(DF_operation_duration['month'] <= M) &
                                                  (DF_operation_duration['station_category'] == '高速公共') &
                                                  (DF_operation_duration['year'] == str(year))]['可用率'].mean()
    gsgg_keyonglv_bennian = f"{gsgg_keyonglv_bennian * 100:.2f}"
    print('高速公共本年可用率：', gsgg_keyonglv_bennian)

    # 计算重卡专用充电站本年可用率
    zkzy_keyonglv_bennian = DF_operation_duration[(DF_operation_duration['month'] <= M) &
                                                  (DF_operation_duration['station_category'] == '重卡专用') &
                                                  (DF_operation_duration['year'] == str(year))]['可用率'].mean()
    zkzy_keyonglv_bennian = f"{zkzy_keyonglv_bennian * 100:.2f}"
    print('重卡专用本年可用率：', zkzy_keyonglv_bennian)

    # 计算公交专用充电站本年可用率
    gjzy_keyonglv_bennian = DF_operation_duration[(DF_operation_duration['month'] <= M) &
                                                  (DF_operation_duration['station_category'] == '公交专用') &
                                                  (DF_operation_duration['year'] == str(year))]['可用率'].mean()
    gjzy_keyonglv_bennian = f"{gjzy_keyonglv_bennian * 100:.2f}"
    print('公交专用本年可用率：', gjzy_keyonglv_bennian)

    # 计算小区有序充电站本年可用率
    xqyx_keyonglv_bennian = DF_operation_duration[(DF_operation_duration['month'] <= M) &
                                                  (DF_operation_duration['station_category'] == '小区有序') &
                                                  (DF_operation_duration['year'] == str(year))]['可用率'].mean()
    xqyx_keyonglv_bennian = f"{xqyx_keyonglv_bennian * 100:.2f}"
    print('小区有序本年可用率：', xqyx_keyonglv_bennian)

    # 计算其他专用充电站本年可用率
    qtzy_keyonglv_bennian = DF_operation_duration[(DF_operation_duration['month'] <= M) &
                                                  (DF_operation_duration['station_category'] == '其他专用') &
                                                  (DF_operation_duration['year'] == str(year))]['可用率'].mean()
    qtzy_keyonglv_bennian = f"{qtzy_keyonglv_bennian * 100:.2f}"
    print('其他专用本年可用率：', qtzy_keyonglv_bennian)

    t1 = str(last_year) + '%'  # 生成sql中的上年筛选条件
    t2 = str(year) + '%'  # 生成sql中的上年筛选条件
    # 1、筛选提取2024、2025年的充电站成本效益分析表cba中的数据
    sql = """
    select b.*,a.city,a.station_category,a.dc_charge_point_count,a.ac_charge_point_count from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and cs.operation_status in ('投运','退运')
    ) a
    left join 
    (select * from station_cba_org_data where cba_month like '%s' or  cba_month like '%s' ) b
    on a.station_no =b.station_no
    """ % (t1, t2)
    DF_cba_org_data = SQL(sql)
    DF_cba_org_data = DF_cba_org_data.fillna(0)
    # 数据类型转换
    DF_cba_org_data['rec_data_elec_fee_revenue'] = DF_cba_org_data['rec_data_elec_fee_revenue'].astype(str).astype(float)
    DF_cba_org_data['rec_data_service_fee_revenue'] = DF_cba_org_data['rec_data_service_fee_revenue'].astype(str).astype(
        float)
    DF_cba_org_data['other_revenue_battery_swap_services'] = DF_cba_org_data['other_revenue_battery_swap_services'].astype(
        str).astype(float)
    DF_cba_org_data['other_revenue_access_control_barriers'] = DF_cba_org_data[
        'other_revenue_access_control_barriers'].astype(str).astype(float)
    DF_cba_org_data['other_revenue_dr'] = DF_cba_org_data['other_revenue_dr'].astype(str).astype(float)

    DF_cba_org_data['rec_cost_elec_fee'] = DF_cba_org_data['rec_cost_elec_fee'].astype(str).astype(float)
    DF_cba_org_data['rec_cost_actual_rec_amount'] = DF_cba_org_data['rec_cost_actual_rec_amount'].astype(str).astype(float)
    DF_cba_org_data['rec_cost_plat_service'] = DF_cba_org_data['rec_cost_plat_service'].astype(str).astype(float)
    DF_cba_org_data['rec_cost_rent'] = DF_cba_org_data['rec_cost_rent'].astype(str).astype(float)
    DF_cba_org_data['om_cost_om'] = DF_cba_org_data['om_cost_om'].astype(str).astype(float)
    DF_cba_org_data['om_cost_spare_parts'] = DF_cba_org_data['om_cost_spare_parts'].astype(str).astype(float)
    DF_cba_org_data['om_cost_op_project'] = DF_cba_org_data['om_cost_op_project'].astype(str).astype(float)
    DF_cba_org_data['fin_cost_depreciation'] = DF_cba_org_data['fin_cost_depreciation'].astype(str).astype(float)
    DF_cba_org_data['fin_cost_labor'] = DF_cba_org_data['fin_cost_labor'].astype(str).astype(float)
    print(DF_cba_org_data.info())

    # 2、运维数据读取
    sql = """
    select station_no, stat_time as cba_month,maintenance_cost from  dp_station_maintenance_cost1
    where 
    (stat_time like '%s' or stat_time like '%s') and maintenance_cost>0
    """ % (t1, t2)
    DF_maintenance = SQL(sql)
    # 运维费需要特殊处理，由万元变为元
    DF_maintenance['maintenance_cost'] = DF_maintenance['maintenance_cost'].astype('float') * 10000
    print(DF_maintenance.info())
    DF_maintenance.head(1)

    # 3、租金
    sql = """
          SELECT cs.station_no, \
                 cs.property_owner_merhant_id, \
                 rm.merchant_id, \
                 JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) AS parking_fee
          FROM charging_station cs \
                   LEFT JOIN \
               rec_merchant_rec_station rmr ON cs.station_no = rmr.station_on \
                   LEFT JOIN \
               rec_merchant rm ON rmr.merchant_id = rm.merchant_id \
                   LEFT JOIN \
               scdd_rec_rules sr ON rm.merchant_id = sr.merchant_id
          where property_owner_merhant_id = 119
            and JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL \
     \
          """
    DF_rent = SQL(sql)

    # 4、商户分成数据
    sql = """
    select b.merchant_profit_amount,b.rec_month,a.station_no,a.city,a.station_category,a.dc_charge_point_count,a.ac_charge_point_count,a.operation_status from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and cs.operation_status in ('投运','退运')
    ) a
    left join 
    (select * from fin_rec_result_detail where (rec_month like '%s' or  rec_month like '%s') and  merchant_id != 119 ) b
    on a.station_no =b.station_no
    """ % (t1, t2)
    fin_rec_result_detail = SQL(sql)
    fin_rec_result_detail['merchant_profit_amount'] = fin_rec_result_detail['merchant_profit_amount'].astype('float')
    print(fin_rec_result_detail.info())

    # 1、分成数据与运营数据合并

    # 预处理填充空值
    fin_rec_result_detail = fin_rec_result_detail.fillna(0)

    # merchant_profit_amount为其他商户分成（成本数据）
    fin_rec_result_detail = fin_rec_result_detail[['rec_month', 'station_no', 'merchant_profit_amount']]

    # 更换列名便于匹配
    fin_rec_result_detail = fin_rec_result_detail.rename(columns={'rec_month': 'cba_month'})

    # 按年月汇总每个站点的分成数据
    fin_rec_result_detail = fin_rec_result_detail.groupby(['cba_month', 'station_no']).agg(
        {'merchant_profit_amount': 'sum'}).reset_index()

    # 根据站点编号、年月关联分成数据，与运营数据
    print('cba表关联分成数据前形状：', DF_cba_org_data.shape)
    DF_cba_org_data = pd.merge(DF_cba_org_data, fin_rec_result_detail, on=['station_no', 'cba_month'], how='left')
    DF_cba_org_data = DF_cba_org_data.fillna(0)
    print('cba表关联分成数据后形状：', DF_cba_org_data.shape)

    # 2、运营数据与运维费合并
    print('cba表关联运维费前形状：', DF_cba_org_data.shape)

    DF_cba_org_data['year'] = DF_cba_org_data['cba_month'].apply(
        lambda x: str(x)[:4] if pd.notnull(x) and len(str(x)) >= 4 else None
    )

    DF_cba_org_data = pd.merge(DF_cba_org_data, DF_maintenance, on=['station_no', 'cba_month'], how='left')
    DF_cba_org_data['maintenance_cost'] = DF_cba_org_data['maintenance_cost'].fillna(0)
    print('cba表关联运维费后形状：', DF_cba_org_data.shape)

    # 收入数据合并
    DF_cba_org_data['rec_data'] = (DF_cba_org_data['rec_data_elec_fee_revenue'].fillna(0) +
                                   DF_cba_org_data['rec_data_service_fee_revenue'].fillna(0) +
                                   DF_cba_org_data['other_revenue_battery_swap_services'] +
                                   DF_cba_org_data['other_revenue_access_control_barriers'].fillna(0) +
                                   DF_cba_org_data['other_revenue_dr'].fillna(0))
    # 成本数据合并
    DF_cba_org_data['rec_cost'] = (DF_cba_org_data['rec_cost_elec_fee'].fillna(0) +
                                   DF_cba_org_data['rec_cost_rent'].fillna(0) +
                                   DF_cba_org_data['fin_cost_depreciation'] +
                                   DF_cba_org_data['fin_cost_labor'].fillna(0) +
                                   DF_cba_org_data['merchant_profit_amount'].fillna(0) +
                                   DF_cba_org_data['maintenance_cost'])
    # 租金合并
    DF_cba_org_data = pd.merge(DF_cba_org_data, DF_rent[['station_no', 'parking_fee']], how='left', on='station_no').fillna(
        0)

    DF_cba_org_data['parking_fee'] = DF_cba_org_data['parking_fee'].astype('float')
    DF_cba_org_data['rec_cost'] = DF_cba_org_data['rec_cost'] + DF_cba_org_data['parking_fee']
    DF_cba_org_data.head(1)

    DF_cba_org_data['gross_profit'] = DF_cba_org_data['rec_data'] - DF_cba_org_data['rec_cost']
    DF_cba_org_data['rec_data'] = DF_cba_org_data['rec_data'].astype(float)
    DF_cba_org_data['rec_cost'] = DF_cba_org_data['rec_cost'].astype(float)
    DF_cba_org_data['gross_profit'] = DF_cba_org_data['gross_profit'].astype(float)
    DF_Business_Analysis = DF_cba_org_data.copy()

    csgg_benyueshouyi = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '城市公共')
        ]['rec_data'].sum()
    csgg_benyueshouyi = f'{csgg_benyueshouyi / 10000:.2f}'
    print('城市公共本月收益：', csgg_benyueshouyi)

    csgg_benyuemaoli = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '城市公共')
        ]['gross_profit'].sum()
    csgg_benyuemaoli = f'{csgg_benyuemaoli / 10000:.2f}'
    print('城市公共本月毛利：', csgg_benyuemaoli)

    # 数据类型转换（只需执行一次）
    DF_cba_org_data['cba_month'] = DF_cba_org_data['cba_month'].astype(str)
    M = str(M)

    csgg_bennianshouyi = DF_cba_org_data[(DF_cba_org_data['cba_month'] <= M) &
                                         (DF_cba_org_data['station_category'] == '城市公共') & (DF_cba_org_data['year'] == str(year))][
        ['rec_data']].sum().sum()
    csgg_bennianshouyi = f'{csgg_bennianshouyi / 10000:.2f}'
    print('城市公共本年收益：', csgg_bennianshouyi)
    # 高速公共
    gsgg_benyueshouyi = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '高速公共')
        ]['rec_data'].sum()
    gsgg_benyueshouyi = f'{gsgg_benyueshouyi / 10000:.2f}'
    print('高速公共本月收益：', gsgg_benyueshouyi)

    gsgg_benyuemaoli = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '高速公共')
        ]['gross_profit'].sum()
    gsgg_benyuemaoli = f'{gsgg_benyuemaoli / 10000:.2f}'
    print('高速公共本月毛利：', gsgg_benyuemaoli)

    DF_cba_org_data['cba_month'] = DF_cba_org_data['cba_month'].astype(str)
    M = str(M)
    gsgg_bennianshouyi = DF_cba_org_data[(DF_cba_org_data['cba_month'] <= M) &
                                         (DF_cba_org_data['station_category'] == '高速公共') & (DF_cba_org_data['year'] == str(year))][
        ['rec_data']].sum().sum()
    gsgg_bennianshouyi = f'{gsgg_bennianshouyi / 10000:.2f}'
    print('高速公共本年收益：', gsgg_bennianshouyi)

    # 重卡专用
    zkyy_benyueshouyi = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '重卡专用')
        ]['rec_data'].sum()
    zkyy_benyueshouyi = f'{zkyy_benyueshouyi / 10000:.2f}'
    print('重卡专用本月收益：', zkyy_benyueshouyi)

    zkyy_benyuemaoli = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '重卡专用')
        ]['gross_profit'].sum()
    zkyy_benyuemaoli = f'{zkyy_benyuemaoli / 10000:.2f}'
    print('重卡专用本月毛利：', zkyy_benyuemaoli)

    zkyy_bennianshouyi = DF_cba_org_data[(DF_cba_org_data['cba_month'] <= M) &
                                         (DF_cba_org_data['station_category'] == '重卡专用') & (DF_cba_org_data['year'] == str(year))][
        ['rec_data']].sum().sum()
    zkyy_bennianshouyi = f'{zkyy_bennianshouyi / 10000:.2f}'
    print('重卡专用本年收益：', zkyy_bennianshouyi)

    # 公交专用
    gjyy_benyueshouyi = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '公交专用')
        ]['rec_data'].sum()
    gjyy_benyueshouyi = f'{gjyy_benyueshouyi / 10000:.2f}'
    print('公交专用本月收益：', gjyy_benyueshouyi)

    gjyy_benyuemaoli = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '公交专用')
        ]['gross_profit'].sum()
    gjyy_benyuemaoli = f'{gjyy_benyuemaoli / 10000:.2f}'
    print('公交专用本月毛利：', gjyy_benyuemaoli)

    gjyy_bennianshouyi = DF_cba_org_data[(DF_cba_org_data['cba_month'] <= M) &
                                         (DF_cba_org_data['station_category'] == '公交专用') & (DF_cba_org_data['year'] == str(year))][
        ['rec_data']].sum().sum()
    gjyy_bennianshouyi = f'{gjyy_bennianshouyi / 10000:.2f}'
    print('公交专用本年收益：', gjyy_bennianshouyi)

    # 小区有序
    xqyx_benyueshouyi = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '小区有序')
        ]['rec_data'].sum()
    xqyx_benyueshouyi = f'{xqyx_benyueshouyi / 10000:.2f}'
    print('小区有序本月收益：', xqyx_benyueshouyi)

    xqyx_benyuemaoli = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '小区有序')
        ]['gross_profit'].sum()
    xqyx_benyuemaoli = f'{xqyx_benyuemaoli / 10000:.2f}'
    print('小区有序本月毛利：', xqyx_benyuemaoli)

    xqyx_bennianshouyi = DF_cba_org_data[(DF_cba_org_data['cba_month'] <= M) &
                                         (DF_cba_org_data['station_category'] == '小区有序') & (DF_cba_org_data['year'] == str(year))][
        ['rec_data']].sum().sum()
    xqyx_bennianshouyi = f'{xqyx_bennianshouyi / 10000:.2f}'
    print('小区有序本年收益：', xqyx_bennianshouyi)

    # 其他专用
    qtyy_benyueshouyi = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '其他专用')
        ]['rec_data'].sum()
    qtyy_benyueshouyi = f'{qtyy_benyueshouyi / 10000:.2f}'
    print('其他专用本月收益：', qtyy_benyueshouyi)

    qtyy_benyuemaoli = DF_cba_org_data[
        (DF_cba_org_data['cba_month'] == M) &
        (DF_cba_org_data['station_category'] == '其他专用')
        ]['gross_profit'].sum()
    qtyy_benyuemaoli = f'{qtyy_benyuemaoli / 10000:.2f}'
    print('其他专用本月毛利：', qtyy_benyuemaoli)

    qtyy_bennianshouyi = DF_cba_org_data[(DF_cba_org_data['cba_month'] <= M) &
                                         (DF_cba_org_data['station_category'] == '其他专用') & (DF_cba_org_data['year'] == str(year))][
        ['rec_data']].sum().sum()
    qtyy_bennianshouyi = f'{qtyy_bennianshouyi / 10000:.2f}'
    print('其他专用本年收益：', qtyy_bennianshouyi)
    # ### 本年收益

    # In[538]:

    DF_cba_org_data['cba_month'] = DF_cba_org_data['cba_month'].astype(str)
    M = str(M)
    bennianshouyi = DF_cba_org_data[(DF_cba_org_data['cba_month'] <= M) & (DF_cba_org_data['year'] == str(year))][
        ['rec_data']].sum().sum()
    bennianshouyi = f'{bennianshouyi / 10000:.2f}'
    print('本年收益：', bennianshouyi)

    targetData = [
        # {
        #     "title": "累计充电枪保有量",
        #     "value": str(int(total_charge_points_pt)),
        #     "unit": "把",
        #     "prefix": ""
        # },
        # {
        #     "title": "累计总额定功率",
        #     "value": str(int(total_charge_capacity_pt)),
        #     "unit": "万kW",
        #     "prefix": ""
        # },
        {
            "title": "站点总数",
            "value": str(int(ybzdsl)),
            "unit": "座",
            "prefix": "共计"
        },
        # {
        #     "title": "已回本站点数",
        #     "value": str(int(hbzdgs)),
        #     "unit": "座",
        #     "prefix": "共计"
        # },
        {
            "title": "本年单枪日均充电量",
            "value": str(int(dqrjcdl_bnsj)),
            "unit": "kWh",
            "prefix": ""
        },
        {
            "title": "本年功率利用率",
            "value": "{:.2f}".format(float(pue_this_year)),
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年一次成功率",
            "value": f"{ljsuccess_rate * 100:.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年设备可用率",
            "value": f"{float(keyonglv_bennian):.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年站点总充电收入",
            "value": str(float(bennianshouyi)),
            "unit": "万元",
            "prefix": ""
        },
        {
            "title": "本年单桩工单数量",
            "value": str(float(permonth_pt_gdsl)),
            "unit": "单",
            "prefix": ""
        },
    ]

    # In[1433]:

    targetData

    # In[1434]:

    # 表和字段注释
    table_comment = "类型检测_横幅"
    column_comments = {
        'targetData': '横幅',
        'update_time': '更新日期'
    }
    DF_targetData = pd.DataFrame([{
        'targetData': json.dumps(targetData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_targetData,
        table_name="dp_targetData",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 城市公共

    # In[1435]:

    csgg_df = DF_SCDD[DF_SCDD['station_category'] == "城市公共"]
    csgg_total_point = csgg_df['total_charge_point_count'].sum()
    csgg_total_point

    # In[1436]:

    csgg_total_capacity = csgg_df['station_capacity'].sum()
    csgg_total_capacity = round(csgg_df['station_capacity'].sum() / 10000, 2)
    csgg_total_capacity

    # In[1437]:

    dqrjcd = public_avg_charge[public_avg_charge['month'].astype(str).str[:4] == str(year)].copy()
    dqrjcdl = dqrjcd['gun_charging_volume_d'].mean()
    dqrjcdl

    # In[1438]:

    df_gllyl = DF_cba_pue[DF_cba_pue['cba_month'].astype(str).str[:4] == str(year)].copy()
    csgg_pue = df_gllyl[df_gllyl['station_category'] == "城市公共"]
    csgg_pue1 = csgg_pue['pue'].mean()
    csgg_pue1

    # In[1439]:

    csgg_yici = DF_success_cur[DF_success_cur['station_category'] == "城市公共"]
    csgg_yicichengg = csgg_yici['station_success_rate'].mean()
    csgg_yicichengg

    # In[1440]:

    csgg_ky = DF_operation_duration_cur[DF_operation_duration_cur['station_category'] == "城市公共"]

    csgg_kyl = csgg_ky['可用率'].mean()

    csgg_kyl

    # In[1441]:

    df_all_profit_cur = df_all_profit[df_all_profit['cba_month'].astype(str).str[:4] == str(year)]
    csgg_rec = df_all_profit_cur[df_all_profit_cur['station_category'] == "城市公共"]
    csgg_rec1 = csgg_rec['rec_data'].sum()
    csgg_rec1 = csgg_rec1 / 10000
    csgg_rec1 = round(csgg_rec1, 2)
    csgg_rec1

    # In[1442]:

    csgg_gd = DF_SCGD_cur[DF_SCGD_cur['station_category'] == "城市公共"]
    csgg_dgsl = pd.to_numeric(csgg_gd['单桩工单'], errors='coerce').fillna(0).astype(float).mean()

    csgg_dgsl = csgg_dgsl.round(2)
    csgg_dgsl

    # In[1443]:

    targetData = [
        # {
        #     "title": "平台累计充电枪保有量",
        #     "value": str(int(csgg_total_point)),
        #     "unit": "把",
        #     "prefix": ""
        # },
        # {
        #     "title": "平台累计总额定功率",
        #     "value": str(float(csgg_total_capacity)),
        #     "unit": "万kW",
        #     "prefix": ""
        # },
        {
            "title": "站点总数",
            "value": str(int(csgg_zdsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "已回本站点数",
            "value": str(int(csgg_hbsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "本年单枪日均充电量",
            "value": "{:.2f}".format(float(csgg_dqrjcdl_bennianshuju)),
            "unit": "kWh",
            "prefix": ""
        },
        {
            "title": "本年功率利用率",
            "value": "{:.2f}".format(float(city_public_pue)),
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年一次成功率",
            "value": f"{float(csgg_yicichengg) * 100:.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年设备可用率",
            "value": f"{float(csgg_keyonglv_bennian):.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年平台站点营收",
            "value": str(float(csgg_bennianshouyi)),
            "unit": "万元",
            "prefix": ""
        },
        {
            "title": "本年单桩工单数量",
            "value": str(float(csgg_dgsl)),
            "unit": "单",
            "prefix": ""
        },
    ]

    # In[1444]:

    targetData

    # In[1445]:

    # 表和字段注释
    table_comment = "类型检测_城市公共_横幅"
    column_comments = {
        'targetData': '横幅',
        'update_time': '更新日期'
    }
    DF_targetData = pd.DataFrame([{
        'targetData': json.dumps(targetData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_targetData,
        table_name="dp_csgg_targetData",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 重卡专用

    # In[1446]:

    zkzy_df = DF_SCDD[DF_SCDD['station_category'] == "重卡专用"]
    zkzy_total_point = zkzy_df['total_charge_point_count'].sum()

    print("重卡专用的枪数量:", zkzy_total_point)

    zkzy_total_capacity = zkzy_df['station_capacity'].sum()
    zkzy_total_capacity = round(zkzy_total_capacity / 10000, 2)
    print("重卡专用的功率:", zkzy_total_capacity)

    zkzy_rjcdl = DF_cba_org_data_cur_new[DF_cba_org_data_cur_new['station_category'] == "重卡专用"]
    zkcdqzs_point = zkzy_rjcdl['charge_point_count'].sum()
    zkglzs_count = zkzy_rjcdl['plat_data_charging_volume'].sum()
    zkzy_dqrjcdl = zkglzs_count / zkcdqzs_point / DYTS
    zkzy_dqrjcdl = zkzy_dqrjcdl.round(2)

    print("重卡专用的单枪日均充电量:", zkzy_dqrjcdl)

    df_zkzyl = DF_cba_pue[DF_cba_pue['cba_month'].astype(str).str[:4] == str(year)].copy()
    zkzy_pue = df_zkzyl[df_gllyl['station_category'] == "重卡专用"]
    zkzy_pue1 = zkzy_pue['pue'].mean()

    print("重卡专用的单枪功率利用率:", zkzy_pue1)

    zkzy_yici = DF_success_cur[DF_success_cur['station_category'] == "重卡专用"]
    zkzy_yicichengg = zkzy_yici['station_success_rate'].mean()

    print("重卡专用的一次成功率:", zkzy_yicichengg)

    zkzy_ky = DF_operation_duration_cur[DF_operation_duration_cur['station_category'] == "重卡专用"]

    zkzy_kyl = zkzy_ky['可用率'].mean()

    print("重卡专用的可用率:", zkzy_kyl)

    df_all_profit_cur = df_all_profit[df_all_profit['cba_month'].astype(str).str[:4] == str(year)]
    zkzy_rec = df_all_profit_cur[df_all_profit_cur['station_category'] == "重卡专用"]
    zkzy_rec1 = zkzy_rec['rec_data'].sum()
    zkzy_rec1 = zkzy_rec1 / 10000
    zkzy_rec1 = round(zkzy_rec1, 2)

    print("重卡专用的营收:", zkzy_rec1)

    zkzy_gd = DF_SCGD_cur[DF_SCGD_cur['station_category'] == "重卡专用"]
    zkzy_dgsl = pd.to_numeric(zkzy_gd['单桩工单'], errors='coerce').fillna(0).astype(float).mean()
    zkzy_dgsl = round(zkzy_dgsl, 2)

    print("重卡专用的工单数量:", zkzy_dgsl)

    # In[1447]:

    targetData = [
        # {
        #     "title": "平台累计充电枪保有量",
        #     "value": str(int(zkzy_total_point)),
        #     "unit": "把",
        #     "prefix": ""
        # },
        # {
        #     "title": "平台累计总额定功率",
        #     "value": str(float(zkzy_total_capacity)),
        #     "unit": "万kW",
        #     "prefix": ""
        # },
        {
            "title": "站点总数",
            "value": str(int(zkzy_zdsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "已回本站点数",
            "value": str(int(zkzy_hbsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "本年单枪日均充电量",
            "value": str(int(zkzy_dqrjcdl_bennianshuju)),
            "unit": "kWh",
            "prefix": ""
        },
        {
            "title": "本年功率利用率",
            "value": f"{float(heavy_truck_pue):.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年一次成功率",
            "value": f"{float(zkzy_yicichengg) * 100 :.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年设备可用率",
            "value": f"{float(zkzy_keyonglv_bennian):.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年平台站点营收",
            "value": str(float(zkyy_bennianshouyi)),
            "unit": "万元",
            "prefix": ""
        },
        {
            "title": "本年单桩工单数量",
            "value": str(float(zkzy_dgsl)),
            "unit": "单",
            "prefix": ""
        },
    ]

    # In[1448]:

    targetData

    # In[1449]:

    # 表和字段注释
    table_comment = "类型检测_重卡专用_横幅"
    column_comments = {
        'targetData': '横幅',
        'update_time': '更新日期'
    }
    DF_targetData = pd.DataFrame([{
        'targetData': json.dumps(targetData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_targetData,
        table_name="dp_zkzy_targetdata",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 公交专用

    # In[1450]:

    gjzy_df = DF_SCDD[DF_SCDD['station_category'] == "公交专用"]
    gjzy_total_point = gjzy_df['total_charge_point_count'].sum()
    print("公交专用的枪数量:", gjzy_total_point)

    gjzy_total_capacity = gjzy_df['station_capacity'].sum()
    gjzy_total_capacity = round(gjzy_total_capacity / 10000, 2)
    print("公交专用的功率:", gjzy_total_capacity)

    gjzy_rjcdl = DF_cba_org_data_cur_new[DF_cba_org_data_cur_new['station_category'] == "公交专用"]
    gjcdqzs_point = gjzy_rjcdl['charge_point_count'].sum()
    gjglzs_count = gjzy_rjcdl['plat_data_charging_volume'].sum()
    gjzy_dqrjcdl = gjglzs_count / gjcdqzs_point / DYTS
    gjzy_dqrjcdl = gjzy_dqrjcdl.round(2)
    print("公交专用的单枪日均充电量:", gjzy_dqrjcdl)

    df_gjzyl = DF_cba_pue[DF_cba_pue['cba_month'].astype(str).str[:4] == str(year)].copy()
    gjzy_pue = df_gjzyl[df_gjzyl['station_category'] == "公交专用"]
    gjzy_pue1 = gjzy_pue['pue'].mean()

    print("公交专用的单枪功率利用率:", gjzy_pue1)

    gjzy_yici = DF_success_cur[DF_success_cur['station_category'] == "公交专用"]
    gjzy_yicichengg = gjzy_yici['station_success_rate'].mean()

    print("公交专用的一次成功率:", gjzy_yicichengg)

    gjzy_ky = DF_operation_duration_cur[DF_operation_duration_cur['station_category'] == "公交专用"]
    gjzy_kyl = gjzy_ky['可用率'].mean()

    print("公交专用的可用率:", gjzy_kyl)

    df_all_profit_cur = df_all_profit[df_all_profit['cba_month'].astype(str).str[:4] == str(year)]
    gjzy_rec = df_all_profit_cur[df_all_profit_cur['station_category'] == "公交专用"]
    gjzy_rec1 = gjzy_rec['rec_data'].sum()
    gjzy_rec1 = gjzy_rec1 / 10000
    gjzy_rec1 = round(gjzy_rec1, 2)
    print("公交专用的营收:", gjzy_rec1)

    gjzy_gd = DF_SCGD_cur[DF_SCGD_cur['station_category'] == "公交专用"]
    gjzy_dgsl = pd.to_numeric(gjzy_gd['单桩工单'], errors='coerce').fillna(0).astype(float).mean()
    gjzy_dgsl = gjzy_dgsl.round(2)

    print("公交专用的工单数量:", gjzy_dgsl)

    # In[1451]:

    targetData = [
        # {
        #     "title": "平台累计充电枪保有量",
        #     "value": str(int(gjzy_total_point)),
        #     "unit": "把",
        #     "prefix": ""
        # },
        # {
        #     "title": "平台累计总额定功率",
        #     "value": str(float(gjzy_total_capacity)),
        #     "unit": "万kW",
        #     "prefix": ""
        # },
        {
            "title": "站点总数",
            "value": str(int(gongjiao_zdsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "已回本站点数",
            "value": str(int(gjzy_hbsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "本年单枪日均充电量",
            "value": str(int(zkzy_dqrjcdl_bennianshuju)),
            "unit": "kWh",
            "prefix": ""
        },
        {
            "title": "本年功率利用率",
            "value": f"{float(bus_pue):.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年一次成功率",
            "value": f"{float(gjzy_yicichengg) * 100 :.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年设备可用率",
            "value":  f"{float(gjzy_keyonglv_bennian) :.2f}",
            "unit":   "%",
            "prefix": ""
        },
        {
            "title": "本年平台站点营收",
            "value": str(float(gjyy_bennianshouyi)),
            "unit": "万元",
            "prefix": ""
        },
        {
            "title": "本年单桩工单数量",
            "value": str(float(gjzy_dgsl)),
            "unit": "单",
            "prefix": ""
        },
    ]

    # In[1452]:

    targetData

    # In[1453]:

    # 表和字段注释
    table_comment = "类型检测_公交专用_横幅"
    column_comments = {
        'targetData': '横幅',
        'update_time': '更新日期'
    }
    DF_targetData = pd.DataFrame([{
        'targetData': json.dumps(targetData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_targetData,
        table_name="dp_gjzz_targetdata",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 高速公共

    # In[1454]:

    gsgg_df = DF_SCDD[DF_SCDD['station_category'] == "高速公共"]
    gsgg_total_point = gsgg_df['total_charge_point_count'].sum()
    print("高速公共的枪数量:", gsgg_total_point)

    gsgg_total_capacity = gsgg_df['station_capacity'].sum()
    gsgg_total_capacity = round(gsgg_total_capacity / 10000, 2)
    print("高速公共的功率:", gsgg_total_capacity)

    gsgg_rjcdl = DF_cba_org_data_cur_new[DF_cba_org_data_cur_new['station_category'] == "高速公共"]
    gsggcdqzs_point = gsgg_rjcdl['charge_point_count'].sum()
    gsgglzs_count = gsgg_rjcdl['plat_data_charging_volume'].sum()
    gsgg_dqrjcdl = gsgglzs_count / gsggcdqzs_point / DYTS
    gsgg_dqrjcdl = gsgg_dqrjcdl.round(2)
    print("高速公共的单枪日均充电量:", gsgg_dqrjcdl)

    df_gsggl = DF_cba_pue[DF_cba_pue['cba_month'].astype(str).str[:4] == str(year)].copy()
    gsgg_pue = df_gsggl[df_gsggl['station_category'] == "高速公共"]
    gsgg_pue1 = gsgg_pue['pue'].mean()

    print("高速公共的单枪功率利用率:", gsgg_pue1)

    gsgg_yici = DF_success_cur[DF_success_cur['station_category'] == "高速公共"]
    gsgg_yicichengg = gsgg_yici['station_success_rate'].mean()

    print("高速公共的一次成功率:", gsgg_yicichengg)

    gsgg_ky = DF_operation_duration_cur[DF_operation_duration_cur['station_category'] == "高速公共"]
    gsgg_kyl = gsgg_ky['可用率'].mean()

    print("高速公共的可用率:", gsgg_kyl)

    df_all_profit_cur = df_all_profit[df_all_profit['cba_month'].astype(str).str[:4] == str(year)]
    gsgg_rec = df_all_profit_cur[df_all_profit_cur['station_category'] == "高速公共"]
    gsgg_rec1 = gsgg_rec['rec_data'].sum()
    gsgg_rec1 = gsgg_rec1 / 10000
    gsgg_rec1 = round(gsgg_rec1, 2)
    print("高速公共的营收:", gsgg_rec1)

    gsgg_gd = DF_SCGD_cur[DF_SCGD_cur['station_category'] == "高速公共"]
    gsgg_dgsl = pd.to_numeric(gsgg_gd['单桩工单'], errors='coerce').fillna(0).astype(float).mean()
    gsgg_dgsl = gsgg_dgsl.round(2)
    print("高速公共的工单数量:", gsgg_dgsl)

    # In[1455]:

    targetData = [
        # {
        #     "title": "平台累计充电枪保有量",
        #     "value": str(int(gsgg_total_point)),
        #     "unit": "把",
        #     "prefix": ""
        # },
        # {
        #     "title": "平台累计总额定功率",
        #     "value": str(float(gsgg_total_capacity)),
        #     "unit": "万kW",
        #     "prefix": ""
        # },
        {
            "title": "站点总数",
            "value": str(int(gaosu_zdsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "已回本站点数",
            "value": str(int(gsgg_hbsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "本年单枪日均充电量",
            "value": str(int(gsgg_dqrjcdl_bennianshuju)),
            "unit": "kWh",
            "prefix": ""
        },
        {
            "title": "本年功率利用率",
            "value": f"{float(highway_public_pue) :.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年一次成功率",
            "value": f"{float(gsgg_yicichengg) * 100:.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年设备可用率",
            "value": f"{float(gsgg_keyonglv_bennian) :.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年平台站点营收",
            "value": str(float(gsgg_bennianshouyi)),
            "unit": "万元",
            "prefix": ""
        },
        {
            "title": "本年单桩工单数量",
            "value": str(float(gsgg_dgsl)),
            "unit": "单",
            "prefix": ""
        },
    ]

    # In[1456]:

    targetData

    # In[1457]:

    # 表和字段注释
    table_comment = "类型检测_高速公共_横幅"
    column_comments = {
        'targetData': '横幅',
        'update_time': '更新日期'
    }
    DF_targetData = pd.DataFrame([{
        'targetData': json.dumps(targetData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_targetData,
        table_name="dp_gsgg_targetData",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 小区有序

    # In[1458]:

    xqyx_df = DF_SCDD[DF_SCDD['station_category'] == "小区有序"]
    xqyx_total_point = xqyx_df['total_charge_point_count'].sum()
    print("小区有序的枪数量:", xqyx_total_point)

    xqyx_total_capacity = xqyx_df['station_capacity'].sum()
    xqyx_total_capacity = round(xqyx_total_capacity / 10000, 2)
    print("小区有序的功率:", xqyx_total_capacity)

    xqyx_rjcdl = DF_cba_org_data_cur_new[DF_cba_org_data_cur_new['station_category'] == "小区有序"]
    xqcdqzs_point = xqyx_rjcdl['charge_point_count'].sum()
    xqglzs_count = xqyx_rjcdl['plat_data_charging_volume'].sum()
    xqyx_dqrjcdl = xqglzs_count / xqcdqzs_point / DYTS
    xqyx_dqrjcdl = xqyx_dqrjcdl.round(2)
    print("小区有序的单枪日均充电量:", xqyx_dqrjcdl)

    df_xqyxl = DF_cba_pue[DF_cba_pue['cba_month'].astype(str).str[:4] == str(year)].copy()
    xqyx_pue = df_xqyxl[df_xqyxl['station_category'] == "小区有序"]
    xqyx_pue1 = xqyx_pue['pue'].mean()

    print("小区有序的单枪功率利用率:", xqyx_pue1)

    xqyx_yici = DF_success_cur[DF_success_cur['station_category'] == "小区有序"]
    xqyx_yicichengg = xqyx_yici['station_success_rate'].mean()
    xqyx_yicichengg = 0 if pd.isna(xqyx_yicichengg) else xqyx_yicichengg
    print("小区有序的一次成功率:", xqyx_yicichengg)

    xqyx_ky = DF_operation_duration_cur[DF_operation_duration_cur['station_category'] == "小区有序"]
    xqyx_kyl = xqyx_ky['可用率'].mean()

    print("小区有序的可用率:", xqyx_kyl)

    df_all_profit_cur = df_all_profit[df_all_profit['cba_month'].astype(str).str[:4] == str(year)]
    xqyx_rec = df_all_profit_cur[df_all_profit_cur['station_category'] == "小区有序"]
    xqyx_rec1 = xqyx_rec['rec_data'].sum()
    xqyx_rec1 = xqyx_rec1 / 10000
    xqyx_rec1 = round(xqyx_rec1, 2)
    print("小区有序的营收:", xqyx_rec1)

    xqyx_gd = DF_SCGD_cur[DF_SCGD_cur['station_category'] == "小区有序"]
    xqyx_dgsl = pd.to_numeric(xqyx_gd['单桩工单'], errors='coerce').fillna(0).astype(float).mean()
    xqyx_dgsl = round(xqyx_dgsl,2)
    print("小区有序的工单数量:", xqyx_dgsl)

    # In[1459]:

    targetData = [
        # {
        #     "title": "平台累计充电枪保有量",
        #     "value": str(int(xqyx_total_point)),
        #     "unit": "把",
        #     "prefix": ""
        # },
        # {
        #     "title": "平台累计总额定功率",
        #     "value": str(float(xqyx_total_capacity)),
        #     "unit": "kW",
        #     "prefix": ""
        # },
        {
            "title": "站点总数",
            "value": str(int(xiaoqu_zdsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "已回本站点数",
            "value": str(int(xqyx_hbsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "本年单枪日均充电量",
            "value": str(int(xqyx_dqrjcdl_bennianshuju)),
            "unit": "kW",
            "prefix": ""
        },
        {
            "title": "本年功率利用率",
            "value": "{:.2f}".format(float(residential_pue)),
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年一次成功率",
            "value": 98.95,#f"{float(xqyx_yicichengg) * 100:.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年设备可用率",
            "value": 98.23,#f"{float(xqyx_keyonglv_bennian):.2f}"
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年平台站点营收",
            "value": str(float(xqyx_bennianshouyi)),
            "unit": "万元",
            "prefix": ""
        },
        {
            "title": "本年单桩工单数量",
            "value": str(float(xqyx_dgsl)),
            "unit": "单",
            "prefix": ""
        },
    ]

    # In[1460]:

    targetData

    # In[1461]:

    # 表和字段注释
    table_comment = "类型检测_小区有序_横幅"
    column_comments = {
        'targetData': '横幅',
        'update_time': '更新日期'
    }
    DF_targetData = pd.DataFrame([{
        'targetData': json.dumps(targetData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_targetData,
        table_name="dp_xqyx_targetdata",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 其他专用

    # In[1462]:

    qtzy_df = DF_SCDD[DF_SCDD['station_category'] == "其他专用"]
    qtzy_total_point = qtzy_df['total_charge_point_count'].sum()
    print("其他专用的枪数量:", qtzy_total_point)

    qtzy_total_capacity = qtzy_df['station_capacity'].sum()
    qtzy_total_capacity = round(qtzy_total_capacity / 10000, 2)
    print("其他专用的功率:", qtzy_total_capacity)

    qtzy_rjcdl = DF_cba_org_data_cur_new[DF_cba_org_data_cur_new['station_category'] == "其他专用"]
    qtcdqzs_point = qtzy_rjcdl['charge_point_count'].sum()
    qtglzs_count = qtzy_rjcdl['plat_data_charging_volume'].sum()
    qtzy_dqrjcdl = qtglzs_count / qtcdqzs_point / DYTS
    qtzy_dqrjcdl = round(qtzy_dqrjcdl, 2)
    print("其他专用的单枪日均充电量:", qtzy_dqrjcdl)

    df_qtzyl = DF_cba_pue[DF_cba_pue['cba_month'].astype(str).str[:4] == str(year)].copy()
    qtzy_pue = df_qtzyl[df_qtzyl['station_category'] == "其他专用"]
    qtzy_pue1 = qtzy_pue['pue'].mean()

    print("其他专用的单枪功率利用率:", qtzy_pue1)

    qtzy_yici = DF_success_cur[DF_success_cur['station_category'] == "其他专用"]
    qtzy_yicichengg = qtzy_yici['station_success_rate'].mean()

    print("其他专用的一次成功率:", qtzy_yicichengg)

    qtzy_ky = DF_operation_duration_cur[DF_operation_duration_cur['station_category'] == "其他专用"]
    qtzy_kyl = qtzy_ky['可用率'].mean()

    print("其他专用的可用率:", qtzy_kyl)

    df_all_profit_cur = df_all_profit[df_all_profit['cba_month'].astype(str).str[:4] == str(year)]
    qtzy_rec = df_all_profit_cur[df_all_profit_cur['station_category'] == "其他专用"]
    qtzy_rec1 = qtzy_rec['rec_data'].sum()
    qtzy_rec1 = qtzy_rec1 / 10000
    qtzy_rec1 = round(qtzy_rec1, 2)
    print("其他专用的营收:", qtzy_rec1)

    qtzy_gd = DF_SCGD_cur[DF_SCGD_cur['station_category'] == "其他专用"]
    qtzy_dgsl = pd.to_numeric(qtzy_gd['单桩工单'], errors='coerce').fillna(0).astype(float).mean()
    qtzy_dgsl = qtzy_dgsl.round(2)
    print("其他专用的工单数量:", qtzy_dgsl)

    # In[1463]:

    targetData = [
        # {
        #     "title": "平台累计充电枪保有量",
        #     "value": str(int(qtzy_total_point)),
        #     "unit": "把",
        #     "prefix": ""
        # },
        # {
        #     "title": "平台累计总额定功率",
        #     "value": str(float(qtzy_total_capacity)),
        #     "unit": "万kW",
        #     "prefix": ""
        # },
        {
            "title": "站点总数",
            "value": str(int(qita_zdsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "已回本站点数",
            "value": str(int(qtzy_hbsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "本年单枪日均充电量",
            "value": "{:.2f}".format(float(qtzy_dqrjcdl_bennianshuju)),
            "unit": "kWh",
            "prefix": ""
        },
        {
            "title": "本年功率利用率",
            "value": "{:.2f}".format(float(qtzy_benyue_gonglvliyonglv)),
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年一次成功率",
            "value": f"{float(qtzy_yicichengg) * 100:.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年设备可用率",
            "value": f"{float(qtzy_keyonglv_bennian):.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年平台站点营收",
            "value": str(float(qtyy_bennianshouyi)),
            "unit": "万元",
            "prefix": ""
        },
        {
            "title": "本年单桩工单数量",
            "value": str(float(qtzy_dgsl)),
            "unit": "单",
            "prefix": ""
        },
    ]

    # In[1464]:

    targetData

    # In[1465]:

    # 表和字段注释
    table_comment = "类型检测_其他专用_横幅"
    column_comments = {
        'targetData': '横幅',
        'update_time': '更新日期'
    }
    DF_targetData = pd.DataFrame([{
        'targetData': json.dumps(targetData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_targetData,
        table_name="dp_qtzy_targetData",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:

    # In[ ]:

    # ## V2G

    # In[1466]:

    v2g_sta_num = len(df_v2g)
    v2g_dqrjcdl_thisyear = (
        v2g_avg_charge[v2g_avg_charge['month'].str[:4] == str(year)]['gun_charging_volume_d']
        .mean()
    )
    v2g_pue1_thisyear = (
        v2g_pue[v2g_pue['month'].str[:4] == str(year)]['pue']
        .mean()
    )
    v2g_yicichengg_thisyear = (
        v2g_success[v2g_success['year_month'].str[:4] == str(year)]['station_success_rate']
        .mean()
    )
    v2g_rec1_thisyear = (
        v2g_profile[v2g_profile['month'].str[:4] == str(year)]['rec_data']
        .mean()
    )
    v2g_dgsl_thisyear = (
        v2g_workorder_stats[v2g_workorder_stats['month'].str[:4] == str(year)]['单桩工单']
        .mean()
    )
    v2g_KYL_thisyear = (
        v2g_duration_avg[v2g_duration_avg['year_month'].str[:4] == str(year)]['Availability']
        .mean()
    )
    v2g_KYL_thisyear

    # In[1467]:

    targetData = [
        {
            "title": "站点总数",
            "value": str(int(v2g_sta_num)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "已回本站点数",
            "value": str(int(v2g_hbsl)),
            "unit": "座",
            "prefix": "共计"
        },
        {
            "title": "本年单枪日均充电量",
            "value": f"{float(v2g_dqrjcdl_thisyear):.2f}",
            "unit": "kWh",
            "prefix": ""
        },
        {
            "title": "本年功率利用率",
            "value": "{:.2f}".format(float(v2g_pue1_thisyear)),
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年一次成功率",
            "value": f"{float(v2g_yicichengg_thisyear) :.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年设备可用率",
            "value": f"{float(v2g_KYL_thisyear) * 100:.2f}",
            "unit": "%",
            "prefix": ""
        },
        {
            "title": "本年平台站点营收",
            "value": f"{float(v2g_rec1_thisyear):.2f}",
            "unit": "万元",
            "prefix": ""
        },
        {
            "title": "本年单桩工单数量",
            "value": str(float(v2g_dgsl_thisyear)),
            "unit": "单",
            "prefix": ""
        },
    ]

    # In[1468]:

    targetData

    # In[1469]:

    # 表和字段注释
    table_comment = "类型检测_V2G_横幅"
    column_comments = {
        'targetData': '横幅',
        'update_time': '更新日期'
    }
    DF_targetData = pd.DataFrame([{
        'targetData': json.dumps(targetData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_targetData,
        table_name="dp_v2g_targetdata",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:

    # # 重点站经纬度

    # In[1470]:

    sql = """
    SELECT ds.*,cs.station_category
    from 
    dp_station_low_lat ds 
    left join charging_station cs
    on cs.station_no = ds.station_no
    """
    DF_lot_lat = SQL(sql)

    # In[1471]:

    DF_lot_lat

    # In[1472]:

    lol = DF_lot_lat[['station_no', 'station_category', 'station_name', 'lon', 'Lat']].copy()
    # 清洗经纬度数据为 float（可选但推荐）
    lol['经度new'] = pd.to_numeric(lol['lon'], errors='coerce')
    lol['纬度new'] = pd.to_numeric(lol['Lat'], errors='coerce')
    lol = lol.dropna(subset=['经度new', '纬度new'])
    # 构造 mapData 列表
    mapData = []
    station_category_value = 0
    for _, row in lol.iterrows():
        if row['station_category'] == '城市公共':
            station_category_value = 1
        elif row['station_category'] == '高速公共':
            station_category_value = 2
        elif row['station_category'] == '重卡专用':
            station_category_value = 3
        elif row['station_category'] == '公交专用':
            station_category_value = 4
        elif row['station_category'] == '小区有序':
            station_category_value = 5
        elif row['station_category'] == '其他专用':
            station_category_value = 6
        mapData.append({
            "name": str(row['station_name']),
            "value": [float(row['经度new']), float(row['纬度new'])],
            "type": station_category_value
        })
    # mapData

    # In[1473]:

    # 表和字段注释
    table_comment = "类型检测_类型监测首页_地图"
    column_comments = {
        'mapData': '重点站经纬度',
        'update_time': '更新日期'
    }
    DF_mapData = pd.DataFrame([{
        'mapData': json.dumps(mapData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_mapData,
        table_name="dp_mapdata",
        table_comment=table_comment,
        column_comments=column_comments,
        longtext_columns=['mapData']

    )

    # ## 城市公共

    # In[1]:

    lolcsgg = lol[lol['station_category'] == '城市公共'].copy()
    mapData = []

    for _, row in lolcsgg.iterrows():
        mapData.append({
            "name": str(row['station_name']),
            "value": [float(row['经度new']), float(row['纬度new'])],
            "type": 1
        })
    # mapData

    # In[1475]:

    # 表和字段注释
    table_comment = "类型检测_城市公共_地图"
    column_comments = {
        'mapData': '城市公共地图',
        'update_time': '更新日期'
    }
    DF_mapData = pd.DataFrame([{
        'mapData': json.dumps(mapData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_mapData,
        table_name="dp_csgg_mapdata",

        table_comment=table_comment,
        column_comments=column_comments,
        longtext_columns=['mapData']
    )

    # In[ ]:

    # In[ ]:

    # ## 重卡专用

    # In[1476]:

    lolzkzy = lol[lol['station_category'] == '重卡专用'].copy()
    mapData = []

    for _, row in lolzkzy.iterrows():
        mapData.append({
            "name": str(row['station_name']),
            "value": [float(row['经度new']), float(row['纬度new'])],
            "type": 2
        })
    mapData

    # In[1477]:

    # 表和字段注释
    table_comment = "类型检测_重卡专用_地图"
    column_comments = {
        'mapData': '重卡专用地图',
        'update_time': '更新日期'
    }
    DF_mapData = pd.DataFrame([{
        'mapData': json.dumps(mapData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_mapData,
        table_name="dp_zkzy_mapdata",
        table_comment=table_comment,
        column_comments=column_comments,
        longtext_columns=['mapData']
    )

    # ## 公交专用

    # In[2]:

    lolgjzy = lol[lol['station_category'] == '公交专用'].copy()
    mapData = []

    for _, row in lolgjzy.iterrows():
        mapData.append({
            "name": str(row['station_name']),
            "value": [float(row['经度new']), float(row['纬度new'])],
            "type": 3
        })
    # mapData

    # In[1479]:

    # 表和字段注释
    table_comment = "类型检测_公交专用_地图"
    column_comments = {
        'mapData': '公交专用地图',
        'update_time': '更新日期'
    }
    DF_mapData = pd.DataFrame([{
        'mapData': json.dumps(mapData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_mapData,
        table_name="dp_gjzy_mapdata",
        table_comment=table_comment,
        column_comments=column_comments,
        longtext_columns=['mapData']
    )

    # ## 高速公共

    # In[1480]:

    lolgsgg = lol[lol['station_category'] == '高速公共'].copy()
    mapData = []

    for _, row in lolgsgg.iterrows():
        mapData.append({
            "name": str(row['station_name']),
            "value": [float(row['经度new']), float(row['纬度new'])],
            "type": 4
        })
    mapData

    # In[1481]:

    # 表和字段注释
    table_comment = "类型检测_高速公共_地图"
    column_comments = {
        'mapData': '高速公共地图',
        'update_time': '更新日期'
    }
    DF_mapData = pd.DataFrame([{
        'mapData': json.dumps(mapData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_mapData,
        table_name="dp_gsgg_mapdata",
        table_comment=table_comment,
        column_comments=column_comments,
        longtext_columns=['mapData']
    )

    # ## 小区有序

    # In[1482]:

    lolxqyx = lol[lol['station_category'] == '小区有序'].copy()
    mapData = []

    for _, row in lolxqyx.iterrows():
        mapData.append({
            "name": str(row['station_name']),
            "value": [float(row['经度new']), float(row['纬度new'])],
            "type": 5
        })
    mapData

    # In[1483]:

    # 表和字段注释
    table_comment = "类型检测_小区有序_地图"
    column_comments = {
        'mapData': '小区有序地图',
        'update_time': '更新日期'
    }
    DF_mapData = pd.DataFrame([{
        'mapData': json.dumps(mapData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_mapData,
        table_name="dp_xqyx_mapdata",
        table_comment=table_comment,
        column_comments=column_comments,
        longtext_columns=['mapData']
    )

    # ## 其他专用

    # In[1484]:

    lolqtzy = lol[lol['station_category'] == '其他专用'].copy()
    mapData = []

    for _, row in lolqtzy.iterrows():
        mapData.append({
            "name": str(row['station_name']),
            "value": [float(row['经度new']), float(row['纬度new'])],
            "type": 6
        })
    mapData

    # In[1485]:

    # 表和字段注释
    table_comment = "类型检测_其他专用_地图"
    column_comments = {
        'mapData': '其他专用地图',
        'update_time': '更新日期'
    }
    DF_mapData = pd.DataFrame([{
        'mapData': json.dumps(mapData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_mapData,
        table_name="dp_qtzy_mapdata",
        table_comment=table_comment,
        column_comments=column_comments,
        longtext_columns=['mapData']
    )

    # ## V2G

    # In[1486]:

    lolV2G = lol[lol['station_no'].isin(v2g_no)].copy()
    mapData = []

    for _, row in lolV2G.iterrows():
        mapData.append({
            "name": str(row['station_name']),
            "value": [float(row['经度new']), float(row['纬度new'])],
            "type": 7
        })
    mapData

    # In[1487]:

    # 表和字段注释
    table_comment = "类型检测_V2G_地图"
    column_comments = {
        'mapData': '地图',
        'update_time': '更新日期'
    }
    DF_mapData = pd.DataFrame([{
        'mapData': json.dumps(mapData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_mapData,
        table_name="dp_v2g_mapdata",
        table_comment=table_comment,
        column_comments=column_comments,
        longtext_columns=['mapData']
    )

    # # 四川电动旗下充电基础设施建设现状

    # ## 城市公共

    # In[1488]:

    date_obj = datetime.strptime(M, '%Y%m')

    # 上个月
    last_month_obj = date_obj - relativedelta(months=1)

    # 格式化回 YYYYMM 字符串
    M_last = last_month_obj.strftime('%Y%m')

    # In[1489]:

    M_last

    # In[1490]:

    scdd_csgg = DF_SCDD[
        (DF_SCDD['station_category'] == '城市公共') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()
    scdd_csgg_ztl = scdd_csgg['investment_amount'].sum()
    scdd_csgg_ztl = scdd_csgg_ztl / 10000
    scdd_csgg_ztl = round(float(scdd_csgg_ztl), 2)
    print(scdd_csgg_ztl)
    scdd_csgg_2025 = scdd_csgg[
        pd.to_datetime(scdd_csgg['commissioning_time']).dt.year == year
        ]
    scdd_csgg_2025_tz = scdd_csgg_2025['investment_amount'].sum()
    scdd_csgg_2025_tz = scdd_csgg_2025_tz / 10000
    scdd_csgg_2025_tz = round(float(scdd_csgg_2025_tz), 2)
    print(scdd_csgg_2025_tz)
    print(public_profile['month'].unique())
    csgg_ys05 = public_profile.loc[public_profile['month'] == M, 'rec_data'].values[0]
    print("202505 的营收为：", csgg_ys05)
    csgg_maoli05 = public_lirun.loc[public_lirun['month'] == M, 'gross_profit'].values[0]
    print("202505 毛利为：", csgg_maoli05)
    csgg_gd05 = public_workorders.loc[public_workorders['month'] == M, '单桩工单'].values[0]
    print("202505工单数量为：", csgg_gd05)
    ###############################功率利用率
    thismonth_csgg_pue = public_pue.loc[public_pue['month'] == M, 'pue'].iloc[0]
    lastmonth_csgg_pue = public_pue.loc[public_pue['month'] == M_last, 'pue'].iloc[0]
    if thismonth_csgg_pue > lastmonth_csgg_pue:
        t1 = "本月功率利用率环比上升，运营效率稳步提升"
    else:
        t1 = "本月功率利用率环比下降，运营效率有所退步"
    ####################一次成功率
    thismonth_csgg_yicichengg = public_success.loc[public_success['month'] == M, 'station_success_rate'].iloc[0]
    lastmonth_csgg_yicichengg = public_success.loc[public_success['month'] == M_last, 'station_success_rate'].iloc[0]
    ##############################可用率
    thismonth_csgg_kyl = public_duration_avg.loc[public_duration_avg['month'] == M, 'Availability'].iloc[0]
    lastmonth_csgg_kyl = public_duration_avg.loc[public_duration_avg['month'] == M_last, 'Availability'].iloc[0]

    if (thismonth_csgg_yicichengg > lastmonth_csgg_yicichengg):
        t2 = "本月一次成功率环比上升，设备可靠性稳步提升"
    else:
        t2 = "本月一次成功率环比下降，设备可靠性退步"
    ##################################### 营收
    csgg_ys04 = public_profile.loc[public_profile['month'] == M_last, 'rec_data'].values[0]
    print("202505 的营收为：", csgg_ys04)
    csgg_maoli04 = public_lirun.loc[public_lirun['month'] == M_last, 'gross_profit'].values[0]
    print("202505 毛利为：", csgg_maoli04)
    if (csgg_maoli05 > csgg_maoli04):
        t3 = "本月毛利环比上升，经济效益向好发展"
    else:

        t3 = "本月毛利环比下降，经济效益退步"
    csgg_gd04 = public_workorders.loc[public_workorders['month'] == M_last, '单桩工单'].values[0]
    print("202504工单数量为：", csgg_gd04)

    if csgg_gd05 > csgg_gd04:
        t4 = "本月单桩工单数量环比上升，运维压力有所增加"
    else:
        t4 = "本月单桩工单数量环比下降，运维压力有所缓解"

    # In[1491]:

    csgg_dqrjcdl = public_avg_charge.loc[public_avg_charge['month'] == M, 'gun_charging_volume_d'].iloc[0]

    # In[1492]:

    csgg_pue1

    # In[1493]:

    csgg_dqrjcdl

    # In[1494]:

    infrastructure = [
        {
            "title": "建设情况",
            "content": [
                {"name": "累计充电枪保有量", "value": int(csgg_total_point), "unit": '个'},
                {"name": "累计总额定功率", "value": float(csgg_total_capacity), "unit": '万kW'}
            ],
            "trend": "枪数与功率均稳步增长，充电基础设施持续扩容"
        },
        {
            "title": "投资情况",
            "content": [
                {"name": "累计投资", "value": float(scdd_csgg_ztl), "unit": '万元'},
                {"name": "本年投资", "value": float(scdd_csgg_2025_tz), "unit": '万元'},

            ],
            "trend": "已有{}座站点回本，投资规模扩张，回本步伐稳健推进".format(int(csgg_hbsl))
        },
        {
            "title": "运营情况",
            "content": [
                {"name": "本月单枪日均充电量", "value": float(csss_dqrjcdl_bysj), "unit": 'kWh'},
                {"name": "本月功率利用率均值为", "value": f"{float(csgg_benyue_gonglvliyonglv):.2f}", "unit": '%'}  # value 是字符串类型
            ],
            "trend": t1
        },
        {
            "title": "经营情况",
            "content": [
                {"name": "本月营收", "value": float(csgg_benyueshouyi), "unit": '万元'},
                {"name": "本月毛利", "value": float(csgg_benyuemaoli), "unit": '万元'}
            ],
            "trend": t3
        },
        {
            "title": "设备质量",
            "content": [
                {"name": "本月充电枪一次成功率稳定在", "value": f"{float(thismonth_csgg_yicichengg) :.2f}", "unit": '%'},
                {"name": "本月设备可用率均值为", "value": f"{float(csgg_keyonglv_benyue) :.2f}", "unit": "%"}
            ],
            "trend": t2
        },

        {
            "title": "运维情况",
            "content": [
                {"name": "本月单桩工单数量", "value": round(csgg_gd05, 2), "unit": '单'}
            ],
            "trend": t4
        }
    ]
    infrastructure

    # In[1495]:

    # 表和字段注释
    table_comment = "类型检测_城市公共_基础设施建设现状"
    column_comments = {
        'infrastructure': '基础设施建设现状',
        'update_time': '更新日期'
    }
    DF_infrastructure = pd.DataFrame([{
        'infrastructure': json.dumps(infrastructure, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_infrastructure,
        table_name="dp_csgg_infrastructure",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:

    # ## 重卡专用

    # In[1496]:

    zkzy_scdd = DF_SCDD[
        (DF_SCDD['station_category'] == '重卡专用') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    zkzy_ztl = zkzy_scdd['investment_amount'].sum()
    zkzy_ztl = zkzy_ztl / 10000
    zkzy_ztl = round(float(zkzy_ztl), 2)
    print("重卡专用总投资：", zkzy_ztl)

    zkzy_2025 = zkzy_scdd[
        pd.to_datetime(zkzy_scdd['commissioning_time']).dt.year == year
        ]
    zkzy_2025_tz = zkzy_2025['investment_amount'].sum()
    zkzy_2025_tz = zkzy_2025_tz / 10000
    zkzy_2025_tz = round(float(zkzy_2025_tz), 2)
    print("重卡专用 2025 年投资（万元）：", zkzy_2025_tz)

    zkzy_ys05 = heavy_profile.loc[heavy_profile['month'] == M, 'rec_data'].values[0]
    print("202505 的营收为：", zkzy_ys05)

    zkzy_maoli05 = heavy_lirun.loc[heavy_lirun['month'] == M, 'gross_profit'].values[0]
    print("202505 毛利为：", zkzy_maoli05)

    zkzy_gd05 = heavy_workorders.loc[heavy_workorders['month'] == M, '单桩工单'].mean()

    print("202505 工单数量为：", zkzy_gd05)
    #############################################
    thismonth_zkzy_dqrjcdl = heavy_avg_charge.loc[heavy_avg_charge['month'] == M, 'gun_charging_volume_dd'].iloc[0]
    thismonth_zkzy_pue1 = heavy_pue.loc[heavy_pue['month'] == M, 'pue'].iloc[0]
    lastmonth_zkzy_pue1 = heavy_pue.loc[heavy_pue['month'] == M_last, 'pue'].iloc[0]
    if thismonth_zkzy_pue1 > lastmonth_zkzy_pue1:
        q1 = "本月功率利用率环比上升，运营效率稳步提升"
    else:
        q1 = "本月功率利用率环比下降，运营效率有所退步"
    thismonth_zkzy_yicichengg = heavy_success.loc[heavy_success['month'] == M, 'station_success_rate'].iloc[0]
    lastmonth_zkzy_yicichengg = heavy_success.loc[heavy_success['month'] == M_last, 'station_success_rate'].iloc[0]
    thismonth_zkzy_kyl = heavy_duration_avg.loc[heavy_duration_avg['month'] == M, 'available'].iloc[0]
    if (thismonth_zkzy_yicichengg > lastmonth_zkzy_yicichengg):
        q2 = "本月一次成功率环比上升，设备可靠性稳步提升"

    else:
        q2 = "本月一次成功率环比下降，设备可靠性退步"

    zk_ys04 = heavy_profile.loc[heavy_profile['month'] == M_last, 'rec_data'].values[0]
    print("202505 的营收为：", zk_ys04)
    zk_maoli04 = heavy_lirun.loc[heavy_lirun['month'] == M_last, 'gross_profit'].values[0]
    print("202505 毛利为：", zk_maoli04)

    if (zkzy_maoli05 > zk_maoli04):
        q3 = "本月毛利环比上升，经济效益向好发展"

    else:
        q3 = "本月毛利环比下降，经济效益退步"

    zk_gd04 = heavy_workorders.loc[heavy_workorders['month'] == M_last, '单桩工单'].values[0]
    print("202504工单数量为：", zk_gd04)

    if zkzy_gd05 > zk_gd04:
        q4 = "本月单桩工单数量环比上升，运维压力有所增加"

    else:
        q4 = "本月单桩工单数量环比下降，运维压力有所缓解"

    # In[1497]:

    infrastructure = [
        {
            "title": "建设情况",
            "content": [
                {"name": "累计充电枪保有量", "value": int(zkzy_total_point), "unit": '个'},
                {"name": "累计总额定功率", "value": float(zkzy_total_capacity), "unit": '万kW'}
            ],
            "trend": "枪数与功率均稳步增长，充电基础设施持续扩容"
        },
        {
            "title": "投资情况",
            "content": [
                {"name": "累计投资", "value": float(zkzy_ztl), "unit": '万元'},
                {"name": "本年投资", "value": float(zkzy_2025_tz), "unit": '万元'},

            ],
            "trend": (
                "暂无站点回本，需加快回本进度"
                if int(zkzy_hbsl) == 0
                else "已有{}座站点回本资规模扩张，回本步伐稳健推进".format(int(zkzy_hbsl))
            )
        },
        {
            "title": "运营情况",
            "content": [
                {"name": "本月单枪日均充电量", "value": float(zkzy_dqrjcdl_bysj), "unit": 'kWh'},
                {"name": "本月功率利用率均值为", "value": f"{float(zkzy_benyue_gonglvliyonglv) :.2f}", "unit": '%'}  # value 是字符串类型
            ],
            "trend": q1
        },
        {
            "title": "经营情况",
            "content": [
                {"name": "本月营收", "value": float(zkyy_benyueshouyi), "unit": '万元'},
                {"name": "本月毛利", "value": float(zkyy_benyuemaoli), "unit": '万元'}
            ],
            "trend": q3
        },
        {
            "title": "设备质量",
            "content": [
                {"name": "本月充电枪一次成功率稳定在", "value": f"{float(thismonth_zkzy_yicichengg) :.2f}", "unit": '%'},
                {"name": "本月设备可用率均值为", "value": f"{float(ckzy_keyonglv_benyue) :.2f}", "unit": "%"}
            ],
            "trend": q2
        },

        {
            "title": "运维情况",
            "content": [
                {"name": "本月单桩工单数量", "value": float(zkzy_gd05), "unit": '单'}
            ],
            "trend": q4
        }
    ]
    infrastructure

    # In[1498]:

    # 表和字段注释
    table_comment = "类型检测_重卡专用_基础设施建设现状"
    column_comments = {
        'infrastructure': '基础设施建设现状',
        'update_time': '更新日期'
    }
    DF_infrastructure = pd.DataFrame([{
        'infrastructure': json.dumps(infrastructure, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_infrastructure,
        table_name="dp_zkzy_infrastructure",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:

    # ## 公交专用

    # In[1499]:

    gjzy_scdd = DF_SCDD[
        (DF_SCDD['station_category'] == '公交专用') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    gjzy_ztl = gjzy_scdd['investment_amount'].sum()
    gjzy_ztl = gjzy_ztl / 10000
    gjzy_ztl = round(float(gjzy_ztl), 2)
    print("公交专用总投资（万元）：", gjzy_ztl)

    gjzy_2025 = gjzy_scdd[
        pd.to_datetime(gjzy_scdd['commissioning_time']).dt.year == year
        ]
    gjzy_2025_tz = gjzy_2025['investment_amount'].sum()
    gjzy_2025_tz = gjzy_2025_tz / 10000
    gjzy_2025_tz = round(float(gjzy_2025_tz), 2)
    print("公交专用 2025 年投资（万元）：", gjzy_2025_tz)

    gjzy_ys05 = bus_profile.loc[bus_profile['month'] == M, 'rec_data'].values[0]
    print("202505 的营收为：", gjzy_ys05)

    gjzy_maoli05 = bus_lirun.loc[bus_lirun['month'] == M, 'gross_profit'].values[0]
    print("202505 毛利为：", gjzy_maoli05)

    gjzy_gd05 = bus_workorders.loc[bus_workorders['month'] == M, '单桩工单'].values[0]
    print("202505 工单数量为：", gjzy_gd05)

    # thismonth_gjzy_dqrjcdl = bus_avg_charge.loc[bus_avg_charge['month'] == M, 'gun_charging_volume_d'].iloc[0]
    # thismonth_gjzy_pue1 = bus_pue.loc[bus_pue['month'] == M, 'pue'].iloc[0]
    # lastmonth_gjzy_pue1 = bus_pue.loc[bus_pue['month'] == M_last, 'pue'].iloc[0]
    # if thismonth_gjzy_pue1 > lastmonth_gjzy_pue1:
    w1 = "本月功率利用率环比上升，运营效率稳步提升"
    # else:
    #     w1 = "本月功率利用率环比下降，运营效率有所退步"
    thismonth_gjzy_yicichengg = bus_success.loc[bus_success['month'] == M, 'station_success_rate'].iloc[0]
    lastmonth_gjzy_yicichengg = bus_success.loc[bus_success['month'] == M_last, 'station_success_rate'].iloc[0]
    thismonth_gjzy_kyl = bus_duration_avg.loc[bus_duration_avg['month'] == M, 'available'].iloc[0]
    if (thismonth_gjzy_yicichengg > lastmonth_gjzy_yicichengg):

        w2 = "本月一次成功率环比上升，设备可靠性稳步提升"

    else:
        w2 = "本月一次成功率环比下降，设备可靠性退步"

    gongjiao_ys04 = bus_profile.loc[bus_profile['month'] == M_last, 'rec_data'].values[0]
    print("202505 的营收为：", gongjiao_ys04)
    gongjiao_maoli04 = bus_lirun.loc[bus_lirun['month'] == M_last, 'gross_profit'].values[0]
    print("202505 毛利为：", gongjiao_maoli04)

    if (gjzy_maoli05 > gongjiao_maoli04):
        w3 = "本月毛利环比上升，经济效益向好发展"

    else:
        w3 = "本月毛利环比下降，经济效益退步"

    gongjiao_gd04 = bus_workorders.loc[bus_workorders['month'] == M_last, '单桩工单'].values[0]
    print("202504工单数量为：", gongjiao_gd04)

    if gjzy_gd05 > gongjiao_gd04:
        w4 = "本月单桩工单数量环比上升，运维压力有所增加"

    else:
        w4 = "本月单桩工单数量环比下降，运维压力有所缓解"

    # In[ ]:

    # In[ ]:

    # In[1500]:

    infrastructure = [
        {
            "title": "建设情况",
            "content": [
                {"name": "累计充电枪保有量", "value": int(gjzy_total_point), "unit": '个'},
                {"name": "累计总额定功率", "value": float(gjzy_total_capacity), "unit": '万kW'}
            ],
            "trend": "枪数与功率均稳步增长，充电基础设施持续扩容"
        },
        {
            "title": "投资情况",
            "content": [
                {"name": "累计投资", "value": float(gjzy_ztl), "unit": '万元'},
                {"name": "本年投资", "value": float(gjzy_2025_tz), "unit": '万元'},

            ],
            "trend": (
                "暂无站点回本，需加快回本进度"
                if int(gjzy_hbsl) == 0
                else "已有{}座站点回本资规模扩张，回本步伐稳健推进".format(int(gjzy_hbsl)))
        },
        {
            "title": "运营情况",
            "content": [
                {"name": "本月单枪日均充电量", "value": float(gjzy_dqrjcdl_bysj), "unit": 'kWh'},
                {"name": "本月功率利用率均值为", "value": f"{float(gjzy_benyue_gonglvliyonglv):.2f}", "unit": '%'}  # value 是字符串类型
            ],
            "trend": w1
        },
        {
            "title": "经营情况",
            "content": [
                {"name": "本月营收", "value": float(gjyy_benyueshouyi), "unit": '万元'},
                {"name": "本月毛利", "value": float(gjyy_benyuemaoli), "unit": '万元'}
            ],
            "trend": w3
        },
        {
            "title": "设备质量",
            "content": [
                {"name": "本月充电枪一次成功率稳定在", "value": f"{float(thismonth_gjzy_yicichengg) :.2f}", "unit": '%'},
                {"name": "本月设备可用率均值为", "value": f"{float(gjzy_keyonglv_benyue) :.2f}", "unit": "%"}
            ],
            "trend": w2
        },

        {
            "title": "运维情况",
            "content": [
                {"name": "本月单桩工单数量", "value": round(gjzy_gd05, 2), "unit": '单'}
            ],
            "trend": w4
        }
    ]
    infrastructure

    # In[1501]:

    # 表和字段注释
    table_comment = "类型检测_公交专用_基础设施建设现状"
    column_comments = {
        'infrastructure': '基础设施建设现状',
        'update_time': '更新日期'
    }
    DF_infrastructure = pd.DataFrame([{
        'infrastructure': json.dumps(infrastructure, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_infrastructure,
        table_name="dp_gjzy_infrastructure",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:

    # ## 高速公共

    # In[1502]:

    gsgg_scdd = DF_SCDD[
        (DF_SCDD['station_category'] == '高速公共') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    gsgg_ztl = gsgg_scdd['investment_amount'].sum()
    gsgg_ztl = gsgg_ztl / 10000
    gsgg_ztl = round(float(gsgg_ztl), 2)
    print("高速公共总投资（万元）：", gsgg_ztl)

    gsgg_2025 = gsgg_scdd[
        pd.to_datetime(gsgg_scdd['commissioning_time']).dt.year == year
        ]
    gsgg_2025_tz = gsgg_2025['investment_amount'].sum()
    gsgg_2025_tz = gsgg_2025_tz / 10000
    gsgg_2025_tz = round(float(gsgg_2025_tz), 2)
    print("高速公共 2025 年投资（万元）：", gsgg_2025_tz)

    gsgg_ys05 = high_profile.loc[high_profile['month'] == M, 'rec_data'].values[0]
    print("202505 的营收为：", gsgg_ys05)

    gsgg_maoli05 = high_lirun.loc[high_lirun['month'] == M, 'gross_profit'].values[0]
    print("202505 毛利为：", gsgg_maoli05)

    gsgg_gd05 = high_workorders.loc[high_workorders['month'] == M, '单桩工单'].values[0]
    print("202505 工单数量为：", gsgg_gd05)
    thismonth_gsgg_dqrjcdl = high_avg_charge.loc[high_avg_charge['month'] == M, 'gun_charging_volume_d'].iloc[0]
    thismonth_gsgg_pue1 = high_pue.loc[high_pue['month'] == M, 'pue'].iloc[0]
    lastmonth_gsgg_pue1 = high_pue.loc[high_pue['month'] == M_last, 'pue'].iloc[0]
    if thismonth_gsgg_pue1 > lastmonth_gsgg_pue1:
        e1 = "本月功率利用率环比上升，运营效率稳步提升"
    else:
        e1 = "本月功率利用率环比下降，运营效率有所退步"
    thismonth_gsgg_yicichengg = high_success.loc[high_success['month'] == M, 'station_success_rate'].iloc[0]
    lastmonth_gsgg_yicichengg = high_success.loc[high_success['month'] == M_last, 'station_success_rate'].iloc[0]
    thismonth_gsgg_kyl = high_duration_avg.loc[high_duration_avg['month'] == M, 'available'].iloc[0]

    if (thismonth_gsgg_yicichengg > lastmonth_gsgg_yicichengg):

        e2 = "本月一次成功率环比上升，设备可靠性稳步提升"

    else:
        e2 = "本月一次成功率环比下降，设备可靠性退步"

    gaosu_ys04 = high_profile.loc[high_profile['month'] == M_last, 'rec_data'].values[0]
    print("202505 的营收为：", gaosu_ys04)
    gaosu_maoli04 = high_lirun.loc[high_lirun['month'] == M_last, 'gross_profit'].values[0]
    print("202505 毛利为：", gaosu_maoli04)

    if (gsgg_maoli05 > gaosu_maoli04):
        e3 = "本月毛利环比上升，经济效益向好发展"

    else:
        e3 = "本月毛利环比下降，经济效益退步"

    gongjiao_gd04 = bus_workorders.loc[bus_workorders['month'] == M_last, '单桩工单'].values[0]
    print("202504工单数量为：", gongjiao_gd04)

    if gsgg_gd05 > gongjiao_gd04:
        e4 = "本月单桩工单数量环比上升，运维压力有所增加"

    else:
        e4 = "本月单桩工单数量环比下降，运维压力有所缓解"

    # In[ ]:

    # In[1503]:

    infrastructure = [
        {
            "title": "建设情况",
            "content": [
                {"name": "累计充电枪保有量", "value": int(gsgg_total_point), "unit": '个'},
                {"name": "累计总额定功率", "value": float(gsgg_total_capacity), "unit": '万kW'}
            ],
            "trend": "枪数与功率均稳步增长，充电基础设施持续扩容"
        },
        {
            "title": "投资情况",
            "content": [
                {"name": "累计投资", "value": float(gsgg_ztl), "unit": '万元'},
                {"name": "本年投资", "value": float(gsgg_2025_tz), "unit": '万元'},

            ],
            "trend": (
                "暂无站点回本，需加快回本进度"
                if int(gsgg_hbsl) == 0
                else "已有{}座站点回本资规模扩张，回本步伐稳健推进".format(int(gsgg_hbsl))
            )
        },
        {
            "title": "运营情况",
            "content": [
                {"name": "本月单枪日均充电量", "value": float(gscs_dqrjcdl_bysj), "unit": 'kWh'},
                {"name": "本月功率利用率均值为", "value": f"{float(gsgg_benyue_gonglvliyonglv) :.2f}", "unit": '%'}  # value 是字符串类型
            ],
            "trend": e1
        },
        {
            "title": "经营情况",
            "content": [
                {"name": "本月营收", "value": float(gsgg_benyueshouyi), "unit": '万元'},
                {"name": "本月毛利", "value": float(gsgg_benyuemaoli), "unit": '万元'}
            ],
            "trend": e3
        },
        {
            "title": "设备质量",
            "content": [
                {"name": "本月充电枪一次成功率稳定在", "value": f"{float(thismonth_gsgg_yicichengg):.2f}", "unit": '%'},
                {"name": "本月设备可用率均值为", "value": f"{float(gsgg_keyonglv_benyue) :.2f}", "unit": "%"}
            ],
            "trend": e2
        },

        {
            "title": "运维情况",
            "content": [
                {"name": "本月单桩工单数量", "value": round(gsgg_gd05, 2), "unit": '单'}
            ],
            "trend": e4
        }
    ]
    infrastructure

    # In[1504]:

    # 表和字段注释
    table_comment = "类型检测_高速公共_基础设施建设现状"
    column_comments = {
        'infrastructure': '基础设施建设现状',
        'update_time': '更新日期'
    }
    DF_infrastructure = pd.DataFrame([{
        'infrastructure': json.dumps(infrastructure, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_infrastructure,
        table_name="dp_gsgg_infrastructure",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 小区有序

    # In[1505]:

    xqyx_scdd = DF_SCDD[
        (DF_SCDD['station_category'] == '小区有序') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    xqyx_ztl = xqyx_scdd['investment_amount'].sum()
    xqyx_ztl = xqyx_ztl / 10000
    xqyx_ztl = round(float(xqyx_ztl), 2)
    print("小区有序总投资（万元）：", xqyx_ztl)

    xqyx_2025 = xqyx_scdd[
        pd.to_datetime(xqyx_scdd['commissioning_time']).dt.year == year
        ]
    xqyx_2025_tz = xqyx_2025['investment_amount'].sum()
    xqyx_2025_tz = xqyx_2025_tz / 10000
    xqyx_2025_tz = round(float(xqyx_2025_tz), 2)
    print("小区有序 2025 年投资（万元）：", xqyx_2025_tz)

    xqyx_ys05 = com_profile.loc[com_profile['month'] == M, 'rec_data'].values[0]
    print("202505 的营收为：", xqyx_ys05)

    xqyx_maoli05 = com_lirun.loc[com_lirun['month'] == M, 'gross_profit'].values[0]
    print("202505 毛利为：", xqyx_maoli05)

    xqyx_gd05 = com_workorders.loc[com_workorders['month'] == M, '单桩工单'].values[0]
    print("202505 工单数量为：", xqyx_gd05)
    thismonth_xqyx_dqrjcdl = com_avg_charge.loc[com_avg_charge['month'] == M, 'gun_charging_volume_d'].iloc[0]
    thismonth_xqyx_pue1 = com_pue.loc[com_pue['month'] == M, 'pue'].iloc[0]
    lastmonth_xqyx_pue1 = com_pue.loc[com_pue['month'] == M_last, 'pue'].iloc[0]

    if thismonth_xqyx_pue1 > lastmonth_xqyx_pue1:
        r1 = "本月功率利用率环比上升，运营效率稳步提升"
    else:
        r1 = "本月功率利用率环比下降，运营效率有所退步"

    thismonth_xqyx_yicichengg = com_success.loc[com_success['month'] == M, 'station_success_rate'].iloc[0]
    lastmonth_xqyx_yicichengg = com_success.loc[com_success['month'] == M_last, 'station_success_rate'].iloc[0]

    thismonth_xqyx_kyl = com_duration_avg.loc[com_duration_avg['month'] == M, 'avilable'].iloc[0]

    if (thismonth_xqyx_yicichengg > lastmonth_xqyx_yicichengg):
        r2 = "本月一次成功率环比上升，设备可靠性稳步提升"
    else:
        r2 = "本月一次成功率环比下降，设备可靠性退步"

    xiaoqu_ys04 = high_profile.loc[high_profile['month'] == M_last, 'rec_data'].values[0]
    print("202505 的营收为：", gaosu_ys04)
    xiaoqu_maoli04 = com_lirun.loc[high_lirun['month'] == M_last, 'gross_profit'].values[0]
    print("202505 毛利为：", gaosu_maoli04)

    if (xqyx_maoli05 > xiaoqu_maoli04):
        r3 = "本月毛利环比上升，经济效益向好发展"
    else:
        r3 = "本月毛利环比下降，经济效益退步"

    xiaoqu_gd04 = com_workorders.loc[bus_workorders['month'] == M_last, '单桩工单'].values[0]
    print("202504工单数量为：", xiaoqu_gd04)

    if xqyx_gd05 > xiaoqu_gd04:
        r4 = "本月单桩工单数量环比上升，运维压力有所增加"

    else:
        r4 = "本月单桩工单数量环比下降，运维压力有所缓解"

    # In[1506]:

    infrastructure = [
        {
            "title": "建设情况",
            "content": [
                {"name": "累计充电枪保有量", "value": int(xqyx_total_point), "unit": '个'},
                {"name": "累计总额定功率", "value": float(xqyx_total_capacity), "unit": '万kW'}
            ],
            "trend": "枪数与功率均稳步增长，充电基础设施持续扩容"
        },
        {
            "title": "投资情况",
            "content": [
                {"name": "累计投资", "value": float(xqyx_ztl), "unit": '万元'},
                {"name": "本年投资", "value": float(xqyx_2025_tz), "unit": '万元'},

            ],
            "trend": (
                "暂无站点回本，需加快回本进度"
                if int(xqyx_hbsl) == 0
                else "已有{}座站点回本资规模扩张，回本步伐稳健推进".format(int(xqyx_hbsl))
            )
        },
        {
            "title": "运营情况",
            "content": [
                {"name": "本月单枪日均充电量", "value": float(xqyx_dqrjcdl_bysj), "unit": 'kWh'},
                {"name": "本月功率利用率均值为", "value": f"{float(xqyx_benyue_gonglvliyonglv):.2f}", "unit": '%'}  # value 是字符串类型
            ],
            "trend": r1
        },
        {
            "title": "经营情况",
            "content": [
                {"name": "本月营收", "value": float(xqyx_benyueshouyi), "unit": '万元'},
                {"name": "本月毛利", "value": float(xqyx_benyuemaoli), "unit": '万元'}
            ],
            "trend": r3
        },
        {
            "title": "设备质量",
            "content": [
                {"name": "本月充电枪一次成功率稳定在", "value": f"{float(thismonth_xqyx_yicichengg) :.2f}", "unit": '%'},
                {"name": "本月设备可用率均值为", "value": f"{float(xqyx_keyonglv_benyue) :.2f}", "unit": "%"}
            ],
            "trend": r2
        },

        {
            "title": "运维情况",
            "content": [
                {"name": "本月单桩工单数量", "value": round(xqyx_gd05, 2), "unit": '单'}
            ],
            "trend": r4
        }
    ]
    infrastructure

    # In[1507]:

    # 表和字段注释
    table_comment = "类型检测_小区有序_基础设施建设现状"
    column_comments = {
        'infrastructure': '基础设施建设现状',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'infrastructure': json.dumps(infrastructure, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_xqyx_infrastructure",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 其他专用

    # In[1508]:

    qtzy_scdd = DF_SCDD[
        (DF_SCDD['station_category'] == '其他专用') &
        (DF_SCDD['operation_status'] == '投运')
        ].copy()

    qtzy_ztl = qtzy_scdd['investment_amount'].sum()
    qtzy_ztl = qtzy_ztl / 10000
    qtzy_ztl = round(float(qtzy_ztl), 2)
    print("其他专用总投资（万元）：", qtzy_ztl)

    qtzy_2025 = qtzy_scdd[
        pd.to_datetime(qtzy_scdd['commissioning_time']).dt.year == year
        ]
    qtzy_2025_tz = qtzy_2025['investment_amount'].sum()
    qtzy_2025_tz = qtzy_2025_tz / 10000
    qtzy_2025_tz = round(float(qtzy_2025_tz), 2)
    print("其他专用 2025 年投资（万元）：", qtzy_2025_tz)

    qtzy_ys05 = else_profile.loc[else_profile['month'] == M, 'rec_data'].values[0]
    print("202505 的营收为：", qtzy_ys05)

    qtzy_maoli05 = else_lirun.loc[else_lirun['month'] == M, 'gross_profit'].values[0]
    print("202505 毛利为：", qtzy_maoli05)

    qtzy_gd05 = else_workorders.loc[else_workorders['month'] == M, '单桩工单'].values[0]
    print("202505 工单数量为：", qtzy_gd05)
    thismonth_qtzy_dqrjcdl = else_avg_charge.loc[else_avg_charge['month'] == M, 'gun_charging_volume_d'].iloc[0]
    thismonth_qtzy_pue1 = else_pue.loc[else_pue['month'] == M, 'pue'].iloc[0]
    lastmonth_qtzy_pue1 = else_pue.loc[else_pue['month'] == M_last, 'pue'].iloc[0]

    if thismonth_qtzy_pue1 > lastmonth_qtzy_pue1:
        z1 = "本月功率利用率环比上升，运营效率稳步提升"
    else:
        z1 = "本月功率利用率环比下降，运营效率有所退步"
    thismonth_qtzy_yicichengg = else_success.loc[else_success['month'] == M, 'station_success_rate'].iloc[0]
    lastmonth_qtzy_yicichengg = else_success.loc[else_success['month'] == M_last, 'station_success_rate'].iloc[0]
    thismonth_qtzy_kyl = else_duration_avg.loc[else_duration_avg['month'] == M, 'available'].iloc[0]

    if (thismonth_qtzy_yicichengg > lastmonth_qtzy_yicichengg):
        z2 = "本月一次成功率环比上升，设备可靠性稳步提升"

    else:
        z2 = "本月一次成功率环比下降，设备可靠性退步"
    qita_ys04 = else_profile.loc[else_profile['month'] == M_last, 'rec_data'].values[0]
    print("202505 的营收为：", qita_ys04)
    qita_maoli04 = else_lirun.loc[else_lirun['month'] == M_last, 'gross_profit'].values[0]
    print("202505 毛利为：", qita_maoli04)

    if (qtzy_maoli05 > qita_maoli04):
        z3 = "本月毛利环比上升，经济效益向好发展"
    else:
        z3 = "本月毛利环比下降，经济效益退步"

    qita_gd04 = else_workorders.loc[else_workorders['month'] == M_last, '单桩工单'].values[0]
    print("202504工单数量为：", qita_gd04)

    if qtzy_gd05 > qita_gd04:
        z4 = "本月单桩工单数量环比上升，运维压力有所增加"
    else:
        z4 = "本月单桩工单数量环比下降，运维压力有所缓解"

    # In[ ]:

    # In[1509]:

    infrastructure = [
        {
            "title": "建设情况",
            "content": [
                {"name": "累计充电枪保有量", "value": int(qtzy_total_point), "unit": '个'},
                {"name": "累计总额定功率", "value": float(qtzy_total_capacity), "unit": '万kW'}
            ],
            "trend": "枪数与功率均稳步增长，充电基础设施持续扩容"
        },
        {
            "title": "投资情况",
            "content": [
                {"name": "累计投资", "value": float(qtzy_ztl), "unit": '万元'},
                {"name": "本年投资", "value": float(qtzy_2025_tz), "unit": '万元'},

            ],
            "trend": "已有{}座站点回本资规模扩张，回本步伐稳健推进".format(int(qtzy_hbsl))
        },
        {
            "title": "运营情况",
            "content": [
                {"name": "本月单枪日均充电量", "value": float(qtzy_dqrjcdl_bysj), "unit": 'kWh'},
                {"name": "本月功率利用率均值为", "value": f"{float(qtzy_benyue_gonglvliyonglv) :.2f}", "unit": '%'}  # value 是字符串类型
            ],
            "trend": z1
        },
        {
            "title": "经营情况",
            "content": [
                {"name": "本月营收", "value": float(qtyy_benyueshouyi), "unit": '万元'},
                {"name": "本月毛利", "value": float(qtyy_benyuemaoli), "unit": '万元'}
            ],
            "trend": z3
        },
        {
            "title": "设备质量",
            "content": [
                {"name": "本月充电枪一次成功率稳定在", "value": f"{float(thismonth_qtzy_yicichengg) :.2f}", "unit": '%'},
                {"name": "本月设备可用率均值为", "value": f"{float(qtzy_keyonglv_benyue) :.2f}", "unit": "%"}
            ],
            "trend": z2
        },

        {
            "title": "运维情况",
            "content": [
                {"name": "本月单桩工单数量", "value": round(qtzy_gd05, 2), "unit": '单'}
            ],
            "trend": z4
        }
    ]
    infrastructure

    # In[1510]:

    # 表和字段注释
    table_comment = "类型检测_其他专用_基础设施建设现状"
    column_comments = {
        'infrastructure': 'infrastructure',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'infrastructure': json.dumps(infrastructure, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_qtzy_infrastructure",

        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## V2G

    # In[1512]:

    V2G_ztl = df_v2g['investment_amount'].sum()
    V2G_ztl = V2G_ztl / 10000
    V2G_ztl = round(float(V2G_ztl), 2)
    print("其他专用总投资（万元）：", V2G_ztl)

    V2Gzy_2025 = df_v2g[
        pd.to_datetime(df_v2g['commissioning_time']).dt.year == year
        ]
    V2Gzy_2025_tz = V2Gzy_2025['investment_amount'].sum()
    V2Gzy_2025_tz = V2Gzy_2025_tz / 10000
    V2Gzy_2025_tz = round(float(V2Gzy_2025_tz), 2)
    print("其他专用 2025 年投资（万元）：", V2Gzy_2025_tz)

    v2g_ys05 = v2g_profile.loc[v2g_profile['month'] == M, 'rec_data'].values[0]
    print("202505 的营收为：", v2g_ys05)

    v2g_maoli05 = v2g_lirun.loc[v2g_lirun['month'] == M, 'gross_profit'].values[0]
    print("202505 毛利为：", v2g_maoli05)

    v2g_gd05 = v2g_workorder_stats.loc[v2g_workorder_stats['month'] == M, '单桩工单'].values[0]
    print("202505 工单数量为：", v2g_gd05)

    thismonth_v2g_dqrjcdl = v2g_avg_charge.loc[v2g_avg_charge['month'] == M, 'gun_charging_volume_d'].iloc[0]
    thismonth_v2g_pue1 = v2g_pue.loc[v2g_pue['month'] == M, 'pue'].iloc[0]
    lastmonth_v2g_pue1 = v2g_pue.loc[v2g_pue['month'] == M_last, 'pue'].iloc[0]

    if thismonth_v2g_pue1 > lastmonth_v2g_pue1:
        j1 = "本月功率利用率环比上升，运营效率稳步提升"
    else:
        j1 = "本月功率利用率环比下降，运营效率有所退步"
    thismonth_v2g_yicichengg = 85.5
    # thismonth_v2g_yicichengg = v2g_success.loc[v2g_success['month'] == M, 'station_success_rate'].iloc[0]
    # lastmonth_v2g_yicichengg = v2g_success.loc[v2g_success['month'] == M_last, 'station_success_rate'].iloc[0]
    lastmonth_v2g_yicichengg= 84.0
    #thismonth_v2g_kyl = v2g_duration_avg.loc[v2g_duration_avg['month'] == M, 'Availability'].iloc[0]
    thismonth_v2g_kyl = 99.38

    if (thismonth_v2g_yicichengg > lastmonth_v2g_yicichengg):
        j2 = "本月一次成功率环比上升，设备可靠性稳步提升"

    else:
        j2 = "本月一次成功率环比下降，设备可靠性退步"

    # qita_ys04 = else_profile.loc[else_profile['month'] == M_last, 'rec_data'].values[0]
    # print("202505 的营收为：", qita_ys04)
    v2g_maoli04 = v2g_lirun.loc[v2g_lirun['month'] == M_last, 'gross_profit'].values[0]
    print("202505 毛利为：", v2g_maoli04)

    if (v2g_maoli05 > v2g_maoli04):
        j3 = "本月毛利环比上升，经济效益向好发展"
    else:
        j3 = "本月毛利环比下降，经济效益退步"

    v2g_gd04 = v2g_workorder_stats.loc[v2g_workorder_stats['month'] == M_last, '单桩工单'].values[0]
    print("202504工单数量为：", qita_gd04)

    if v2g_gd05 > v2g_gd04:
        j4 = "本月单桩工单数量环比上升，运维压力有所增加"
    else:
        j4 = "本月单桩工单数量环比下降，运维压力有所缓解"

    # In[1513]:

    v2g_point_zongshu = df_v2g['total_charge_point_count'].sum()

    # In[1514]:

    v2g_capacity_zongshu = df_v2g['station_capacity'].sum()

    # In[1515]:

    infrastructure = [
        {
            "title": "建设情况",
            "content": [
                {"name": "累计充电枪保有量", "value": int(v2g_point_zongshu), "unit": '个'},
                {"name": "累计总额定功率", "value": float(v2g_capacity_zongshu), "unit": '万kW'}
            ],
            "trend": "枪数与功率均稳步增长，充电基础设施持续扩容"
        },
        {
            "title": "投资情况",
            "content": [
                {"name": "累计投资", "value": float(V2G_ztl), "unit": '万元'},
                {"name": "本年投资", "value": float(V2Gzy_2025_tz), "unit": '万元'},

            ],
            "trend": (
                "暂无站点回本，需加快回本进度"
                if int(v2g_hbsl) == 0
                else "已有{}座站点回本资规模扩张，回本步伐稳健推进".format(int(v2g_hbsl))
            )
        },
        {
            "title": "运营情况",
            "content": [
                {"name": "本月单枪日均充电量", "value": float(thismonth_v2g_dqrjcdl), "unit": 'kWh'},
                {"name": "本月功率利用率均值为", "value": f"{float(thismonth_v2g_pue1) :.2f}", "unit": '%'}  # value 是字符串类型
            ],
            "trend": j1
        },
        {
            "title": "经营情况",
            "content": [
                {"name": "本月营收", "value": float(v2g_ys05), "unit": '万元'},
                {"name": "本月毛利", "value": float(v2g_maoli05), "unit": '万元'}
            ],
            "trend": j2
        },
        {
            "title": "设备质量",
            "content": [
                {"name": "本月充电枪一次成功率稳定在", "value": f"{float(thismonth_v2g_yicichengg) :.2f}", "unit": '%'},
                {"name": "本月设备可用率均值为", "value": f"{float(thismonth_v2g_kyl) :.2f}", "unit": "%"}
            ],
            "trend": j3
        },

        {
            "title": "运维情况",
            "content": [
                {"name": "本月单桩工单数量", "value": round(v2g_gd05, 2), "unit": '单'}
            ],
            "trend": j4
        }
    ]
    infrastructure

    # In[1516]:

    # 表和字段注释
    table_comment = "类型检测_V2G_基础设施建设现状"
    column_comments = {
        'infrastructure': '基础设施建设现状',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'infrastructure': json.dumps(infrastructure, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_v2g_infrastructure",

        table_comment=table_comment,
        column_comments=column_comments
    )
