from logs.log_decorator import log_execution
from loguru import logger
from modules.config import SQL, import_data_with_cursor, Statistical_Time


@log_execution
def runtypeMonitoringOverview():
    logger.info("开始执行类型监测概览页")

    import pandas as pd
    import numpy as np
    from datetime import datetime
    import json
    from pandas.tseries.offsets import MonthBegin
    import calendar
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)
    dt = datetime.strptime(M, "%Y%m")
    year = dt.year
    month = dt.month

    # In[7]:

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

    # In[ ]:

    # In[8]:

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

    # ## 投运情况

    # ### 充电枪保有量

    # In[9]:

    sql = """
    SELECT 
    rm.merchant_name,
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    cs.merchant_nature = "电动公司"
    and cs.operation_status in ('投运','停运')
    """
    DF_SCDD = SQL(sql)
    DF_SCDD = DF_SCDD[DF_SCDD['charge_point_count'].notna()]

    # In[10]:

    target_categories = ['城市公共', '高速公共', '重卡专用', '公交专用', '小区有序', '其他专用','V2G']
    DF_SCDD = DF_SCDD[DF_SCDD['station_category'].isin(target_categories)]
    DF_SCDD.loc[DF_SCDD['station_category'] == '高速', 'station_category'] = '高速公共'

    # 投资数据需同时包含投运、退运和停运站点，不能复用普通页面的站点口径。
    sql = """
    SELECT
    rm.merchant_name,
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE
    cs.merchant_nature = "电动公司"
    AND cs.operation_status IN ('投运','退运','停运')
    """
    DF_SCDD_investment = SQL(sql)
    DF_SCDD_investment = DF_SCDD_investment[
        DF_SCDD_investment['station_category'].isin(target_categories)
    ].copy()
    DF_SCDD_investment.loc[
        DF_SCDD_investment['station_category'] == '高速', 'station_category'
    ] = '高速公共'
    DF_SCDD_investment['year'] = DF_SCDD_investment['commissioning_time'].dt.year
    DF_SCDD_investment['year_month'] = DF_SCDD_investment['commissioning_time'].dt.strftime('%Y%m')
    nearly_invest = DF_SCDD_investment.copy()
    # 枪数量
    # DF_SCDD['charge_point_count1'] = DF_SCDD['dc_charge_point_count'].fillna(0)+DF_SCDD['ac_charge_point_count'].fillna(0)

    # In[11]:

    # 处理投运时间字段
    DF_SCDD['year'] = DF_SCDD['commissioning_time'].dt.year
    DF_SCDD['year_month'] = DF_SCDD['commissioning_time'].dt.strftime('%Y%m')
    # DF_SCDD = DF_SCDD[DF_SCDD['charge_point_count'].notna()]

    # In[12]:

    DF_SCDD['total_point'] = DF_SCDD['dc_charge_point_count'].fillna(0) + DF_SCDD['ac_charge_point_count'].fillna(0)
    type_gun_number = DF_SCDD.groupby('station_category')['total_point'].sum().reset_index()

    # In[13]:

    type_gun_number

    # In[ ]:

    # ### 平均额定功率

    # In[14]:

    DF_SCDD['station_capacity'] = pd.to_numeric(DF_SCDD['station_capacity'], errors='coerce')
    # 按 station_category 分组，计算 station_capacity 平均值
    type_avg_capacity = DF_SCDD.groupby('station_category')['station_capacity'].mean().reset_index()

    # In[15]:

    type_avg_capacity['station_capacity'] = type_avg_capacity['station_capacity'].round(2)
    type_avg_capacity

    # In[16]:

    df_merged_tyqk = pd.merge(type_gun_number, type_avg_capacity, on="station_category")

    # In[17]:

    # 保证三个表都有相同的 station_category 顺序
    df_merged_tyqk = (
        type_gun_number
        .merge(type_avg_capacity, on='station_category', how='left')
        .fillna(0)
    )

    # 提取数据字段
    station_categorys = df_merged_tyqk['station_category'].tolist()
    total_point = df_merged_tyqk['total_point'].astype(int).apply(str).tolist()
    station_capacity = df_merged_tyqk['station_capacity'].round(2).tolist()

    result = {
        "yAxisLeftName": "个",
        "yAxisRightName": "kW",
        "legendName": ["充电枪保有量", "站均额定功率"],
        "axisData": station_categorys,
        "chartData": [
            total_point,
            station_capacity
        ]
    }

    # In[18]:

    result

    # In[ ]:

    # ### 写入数据库

    # In[19]:

    # 表和字段注释
    table_comment = "类型检测_首页_投运情况"
    column_comments = {
        'result': '投运情况',
        'data': '更新日期'
    }
    DF_Commissioning_status = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Commissioning_status,
        table_name="dp_Commissioning_status",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 投资情况

    # ### 总投资费用

    # In[20]:

    # 将 investment_amount 转换为数值，忽略非数字
    DF_SCDD_investment['investment_amount'] = pd.to_numeric(
        DF_SCDD_investment['investment_amount'], errors='coerce'
    )
    # 分组求和
    total_investment_amount = (
        DF_SCDD_investment.groupby('station_category')['investment_amount'].sum().reset_index()
    )

    # In[21]:

    total_investment_amount['investment_amount'] = total_investment_amount['investment_amount'] / 10000
    total_investment_amount['investment_amount'] = total_investment_amount['investment_amount'].round(2)
    total_investment_amount

    # In[ ]:

    # ### 当年投资情况

    # In[22]:

    current_year = dt.year
    current_month = dt.month

    # In[23]:

    current_year

    # In[24]:

    # 获取所有 station_category
    all_station_categorys = pd.DataFrame(
        DF_SCDD_investment['station_category'].dropna().unique(), columns=['station_category']
    )
    # 原始链式聚合
    total_investment_current_year = (
        DF_SCDD_investment[DF_SCDD_investment['year'] == current_year]
        .assign(investment_amount=lambda df: pd.to_numeric(df['investment_amount'], errors='coerce'))
        .groupby('station_category')['investment_amount']
        .sum()
        .reset_index()
        .rename(columns={'investment_amount': 'total_investment_amount_2025'})
    )
    # 合并并补全
    total_investment_current_year = (
        all_station_categorys
        .merge(total_investment_current_year, on='station_category', how='left')
        .fillna({'total_investment_amount_2025': 0})
    )

    # In[25]:

    total_investment_current_year['total_investment_amount_2025'] = total_investment_current_year[
                                                                        'total_investment_amount_2025'] / 10000
    total_investment_current_year

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # ### 回本情况

    # In[26]:

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
    where cs.merchant_nature = "电动公司"
    and  JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL 
    """
    DF_RENT = SQL(sql)

    # In[ ]:

    # In[29]:

    # DF_1['revenue'] = DF_1['revenue']
    # DF_1['cost'] = DF_1['cost']
    # DF_1['investment_amount'] = DF_1['investment_amount']

    # In[30]:

    # DF2 = pd.merge(DF_1,DF_subsidy,on='station_no',how='left')

    # In[31]:

    # # 合并 parking_fee
    # DF2['station_no'] = DF2['station_no'].astype(str)
    # DF_RENT['station_no'] = DF_RENT['station_no'].astype(str)

    # DF_rrentt = DF2.merge(
    #     DF_RENT[['station_no', 'parking_fee']],
    #     on='station_no',
    #     how='left'
    # )

    # In[32]:

    # DF_rrentt['total_subsidy'] = DF_rrentt['total_subsidy'].fillna(0)
    # DF_rrentt['in'] = DF_rrentt['revenue'].astype(float) + DF_rrentt['total_subsidy'].astype(float)
    # DF_rrentt['investment_amount'] = DF_rrentt['investment_amount'].fillna(0)
    # DF_rrentt['parking_fee'] = DF_rrentt['parking_fee'].fillna(0)
    # DF_rrentt['cost'] = DF_rrentt['cost'].fillna(0)
    # DF_rrentt['out'] = DF_rrentt['cost'].astype(float) + DF_rrentt['investment_amount'].astype(float)+ DF_rrentt['parking_fee'].astype(float)

    # In[33]:

    # df_month = DF_rrentt.copy()

    # In[34]:

    # df_month['huiben'] = df_month['in'] / df_month['out'] * 100

    # In[35]:

    sql = """
    SELECT 
    cs.station_name,cs.station_no,cs.investment_amount,cs.commissioning_time,cs.station_category
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    cs.merchant_nature = "电动公司"
    and operation_status in ('投运','退运','停运')

    """
    DF_station = SQL(sql)
    DF_station = DF_station[DF_station['station_category'].isin(target_categories)]
    DF_station.loc[DF_station['station_category'] == '高速', 'station_category'] = '高速公共'

    DF_station = DF_station[DF_station['investment_amount'].notna()]
    ybzdsl = len(DF_station)
    print(f"站点数量{ybzdsl}")
    csgg_zdsl = len(DF_station[DF_station['station_category'] == '城市公共'])
    zkzy_zdsl = len(DF_station[DF_station['station_category'] == '重卡专用'])
    gongjiao_zdsl = len(DF_station[DF_station['station_category'] == '公交专用'])
    gaosu_zdsl = len(DF_station[DF_station['station_category'] == '高速公共'])
    xiaoqu_zdsl = len(DF_station[DF_station['station_category'] == '小区有序'])
    qita_zdsl = len(DF_station[DF_station['station_category'] == '其他专用'])
    sql = f"""
    select station_no,sum(total_subsidy) as total_subsidy from dp_subsidy_NEW
    GROUP BY station_no
    """
    DF_subsidy = SQL(sql)

    sql = f"""
    select b.station_no,
    sum(IFNULL(b.rec_data_elec_fee_revenue,0)+IFNULL(b.rec_data_service_fee_revenue,0)+IFNULL(b.other_revenue_battery_swap_services,0)+
    IFNULL(b.other_revenue_op_subsidies,0)+IFNULL(b.other_revenue_build_subsidies,0)+IFNULL(b.other_revenue_access_control_barriers,0)+IFNULL(b.other_revenue_dr,0)) as revenue,
    sum(IFNULL(b.rec_cost_elec_fee,0)+IFNULL(b.rec_cost_actual_rec_amount,0)+IFNULL(b.rec_cost_plat_service,0)+
    IFNULL(b.rec_cost_rent,0)+IFNULL(b.om_cost_om,0)+IFNULL(b.om_cost_spare_parts,0)+IFNULL(b.om_cost_op_project,0)+IFNULL(b.fin_cost_depreciation+b.fin_cost_labor,0)) as cost
    from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    cs.merchant_nature = "电动公司"
    and operation_status in ('投运','退运','停运') and  investment_amount is not null) a
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
    where cs.merchant_nature = "电动公司"
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
    cs.merchant_nature = "电动公司"
    and cs.operation_status in ('投运','退运','停运')
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
    DF_1['month_num'] = [x + y for x, y in
                         zip([int(M[4:]) - i for i in DF_1['month']], [(int(M[:4]) - i) * 12 for i in DF_1['year']])]
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
    fin_rec_result_detail = fin_rec_result_detail.groupby(['station_no']).agg(
        {'merchant_profit_amount': 'sum'}).reset_index()
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
    DF['out'] = DF['cost'].astype('float') + DF['investment_amount'].astype('float') + DF[
        'merchant_profit_amount'].astype('float') + DF['maintenance_cost'].astype('float')
    sql1 = """
    SELECT 
      b.station_no,
      SUM(
        IFNULL(b.rec_data_elec_fee_revenue, 0) +
        IFNULL(b.rec_data_service_fee_revenue, 0) +
        IFNULL(b.other_revenue_battery_swap_services, 0) +
        IFNULL(b.other_revenue_op_subsidies, 0) +
        IFNULL(b.other_revenue_build_subsidies, 0) +
        IFNULL(b.other_revenue_access_control_barriers, 0) +
        IFNULL(b.other_revenue_dr, 0)
      ) AS revenue,
      SUM(
        IFNULL(b.rec_cost_elec_fee, 0) +
        IFNULL(b.rec_cost_actual_rec_amount, 0) +
        IFNULL(b.rec_cost_plat_service, 0) +
        IFNULL(b.rec_cost_rent, 0) +
        IFNULL(b.om_cost_om, 0) +
        IFNULL(b.om_cost_spare_parts, 0) +
        IFNULL(b.om_cost_op_project, 0) +
        IFNULL(b.fin_cost_depreciation + b.fin_cost_labor, 0)
      ) AS cost
    FROM (
      SELECT cs.*
      FROM charging_station cs
      LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
      WHERE 
        cs.merchant_nature = "电动公司"
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
      cs.merchant_nature = "电动公司"
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
    df_temp['out'] = df_temp['cost'].astype('float') + df_temp['investment_amount'].astype('float') + df_temp[
        'merchant_profit_amount'].astype('float') + df_temp['maintenance_cost'].astype('float')
    DF.loc[DF['station_no'] == '300003000100019488', 'in'] = DF[DF['station_no'] == '300003000100019488']['in'].values[
                                                                 0] + \
                                                             df_temp[df_temp['station_no'] == '300003013200108'][
                                                                 'in'].values[0]
    DF.loc[DF['station_no'] == '300003000100017539', 'in'] = DF[DF['station_no'] == '300003000100017539']['in'].values[
                                                                 0] + \
                                                             df_temp[df_temp['station_no'] == '300003000100002472'][
                                                                 'in'].values[0]
    DF.loc[DF['station_no'] == '300003000100017538', 'in'] = DF[DF['station_no'] == '300003000100017538']['in'].values[
                                                                 0] + \
                                                             df_temp[df_temp['station_no'] == '300003000100002473'][
                                                                 'in'].values[0]
    DF.loc[DF['station_no'] == '300003000100019487', 'in'] = DF[DF['station_no'] == '300003000100019487']['in'].values[
                                                                 0] + \
                                                             df_temp[df_temp['station_no'] == '300003013200011'][
                                                                 'in'].values[0] + \
                                                             df_temp[df_temp['station_no'] == '300003013200099'][
                                                                 'in'].values[0]
    DF.loc[DF['station_no'] == '300003000100019488', 'out'] = \
    DF[DF['station_no'] == '300003000100019488']['out'].values[0] + \
    df_temp[df_temp['station_no'] == '300003013200108']['out'].values[0]
    DF.loc[DF['station_no'] == '300003000100017539', 'out'] = \
    DF[DF['station_no'] == '300003000100017539']['out'].values[0] + \
    df_temp[df_temp['station_no'] == '300003000100002472']['out'].values[0]
    DF.loc[DF['station_no'] == '300003000100017538', 'out'] = \
    DF[DF['station_no'] == '300003000100017538']['out'].values[0] + \
    df_temp[df_temp['station_no'] == '300003000100002473']['out'].values[0]
    DF.loc[DF['station_no'] == '300003000100019487', 'out'] = \
    DF[DF['station_no'] == '300003000100019487']['out'].values[0] + \
    df_temp[df_temp['station_no'] == '300003013200011']['out'].values[0] + \
    df_temp[df_temp['station_no'] == '300003013200099']['out'].values[0]
    DF = DF[DF['investment_amount'] != 0]
    DF = DF[DF['station_category'].isin(target_categories)]
    huibenzhandian = DF[DF['in'] > DF['out']]
    # huibenzhandian.groupby('station_category').agg({'station_no':'count'})
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
    DF['hbpercentage'] = DF['in'] / DF['out'] * 100

    # In[36]:

    hb_df = DF[DF['in'] > DF['out']]
    count_type_huiben = hb_df.groupby('station_category').size().reset_index(name='回本数量')
    all_types = ['城市公共', '重卡专用', '公交专用', '高速公共', '小区有序', '其他专用']
    count_type_huiben = count_type_huiben.set_index('station_category').reindex(all_types, fill_value=0).reset_index()
    count_type_huiben

    # In[37]:

    # len(DF[DF['in'] >= DF['out']])

    # In[38]:

    # DF.columns

    # In[39]:

    # df_valid_huibenlv = pd.DataFrame(
    #     columns=['城市公共', '重卡专用', '公交专用', '高速公共', '小区有序', '其他专用'],
    #     data=[[csgg_hbsl, zkzy_hbsl, gjzy_hbsl, gsgg_hbsl, xqyx_hbsl, qtzy_hbsl]]
    # )

    # In[40]:

    # # 先排除 huiben 为 inf 或 nan 的行
    # df_valid_huibenlv = df_month.replace([np.inf, -np.inf], np.nan).dropna(subset=['huiben'])

    # # 按 station_category 分组求平均回本率（保留两位小数）
    # result_huibenlv = (
    #     df_valid_huibenlv
    #     .groupby('station_category')['huiben']
    #     .round(2)
    #     .reset_index()
    #     .rename(columns={'huiben': '回本率'})
    # )

    # In[41]:

    # df_valid_huibenlv = df_valid_huibenlv.T

    # In[42]:

    # df_valid_huibenlv =df_valid_huibenlv.reset_index().rename(columns={'index':'station_category',0:'hb'})

    # In[43]:

    # df_valid_huibenlv

    # In[44]:

    # # 保证三个表都有相同的 station_category 顺序
    # df_merged_touzi = (
    #     total_investment_amount
    #     .merge(total_investment_current_year, on='station_category', how='left')
    #     .merge(count_type_huiben, on='station_category', how='left')
    #     .fillna(0)
    # )

    # # 提取数据字段
    # station_categorys = df_merged_touzi['station_category'].tolist()
    # total_investment = df_merged_touzi['investment_amount'].round(2).tolist()
    # current_year_investment = df_merged_touzi['total_investment_amount_2025'].round(2).tolist()
    # huiben_rate = count_type_huiben['回本数量'].tolist()

    # # 构造前端结构
    # invest_data= {
    #     "options": ["累计投资金额", "当年投资情况", "回本情况"],
    #     "data": [
    #         {
    #             "radio": "累计投资金额",
    #             "legendName": ["累计投资金额"],
    #             "axisData": station_categorys,
    #             "chartData": [total_investment],
    #             "yAxisName": "万元"
    #         },
    #         {
    #             "radio": "当年投资情况",
    #             "legendName": ["当年投资情况"],
    #             "axisData": station_categorys,
    #             "chartData": [current_year_investment],
    #             "yAxisName": "万元"
    #         },
    #         {
    #             "radio": "回本情况",
    #             "legendName": ["回本情况"],
    #             "axisData": station_categorys,
    #             "chartData": [huiben_rate],
    #             "yAxisName": "个"
    #         }
    #     ]
    # }

    # In[45]:

    # 保证两个表都有相同的 station_category 顺序
    df_merged_touzi = (
        total_investment_amount
        .merge(total_investment_current_year, on='station_category', how='left')
        .fillna(0)
    )

    # 提取数据字段
    station_categorys = df_merged_touzi['station_category'].tolist()
    total_investment = df_merged_touzi['investment_amount'].round(2).tolist()
    current_year_investment = df_merged_touzi['total_investment_amount_2025'].round(2).tolist()

    # 构造前端结构（删除回本情况）
    invest_data = {
        "options": ["累计投资金额", "当年投资情况"],
        "data": [
            {
                "radio": "累计投资金额",
                "legendName": ["累计投资金额"],
                "axisData": station_categorys,
                "chartData": [total_investment],
                "yAxisName": "万元"
            },
            {
                "radio": "当年投资情况",
                "legendName": ["当年投资情况"],
                "axisData": station_categorys,
                "chartData": [current_year_investment],
                "yAxisName": "万元"
            }
        ]
    }

    # In[46]:

    invest_data

    # In[ ]:

    # In[ ]:

    # ### 写入数据库

    # In[47]:

    # 表和字段注释
    table_comment = "类型检测_首页_投资情况"
    column_comments = {
        'invest_data': '投资情况',
        'update_time': '更新日期'
    }
    DF_Investments_status = pd.DataFrame([{
        'invest_data': json.dumps(invest_data, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Investments_status,
        table_name="dp_Investments_status",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 运营情况（当月）

    # ### 单枪日均电量

    # In[48]:

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
            cs.merchant_nature = "电动公司"
            and  cs.operation_status in ('投运','停运')) a
            left join 
            (select * from station_cba_org_data where cba_month like '%s' or  cba_month like '%s' ) b
            on a.station_no =b.station_no
            """ % (t1, t2)
    DF_org_data_pre_gun = SQL(sql)
    DF_org_data_pre_gun = DF_org_data_pre_gun[DF_org_data_pre_gun['station_category'].isin(target_categories)]

    DF_org_data_pre_gun = DF_org_data_pre_gun.fillna(0)
    DF_org_data_pre_gun['charge_point_count'] = DF_org_data_pre_gun['dc_charge_point_count'].fillna(0) + \
                                                DF_org_data_pre_gun[
                                                    'ac_charge_point_count'].fillna(0)

    DF_org_data_pre_gun = DF_org_data_pre_gun[DF_org_data_pre_gun['charge_point_count'] != 0]
    DF_org_data_pre_gun = DF_org_data_pre_gun[DF_org_data_pre_gun['plat_data_charging_volume'] != 0]  # 平台数据-平台充电量,不等于0
    # 当月单枪充电量，日均的计算在后面
    DF_org_data_pre_gun['gun_charging_volume'] = DF_org_data_pre_gun['plat_data_charging_volume'] / DF_org_data_pre_gun[
        'charge_point_count']

    print("DF_org_data_pre_gun的列名:\n", DF_org_data_pre_gun.columns)

    DF_cba_org_data_cur = DF_org_data_pre_gun[DF_org_data_pre_gun['cba_month'] == M].copy()

    # In[51]:

    days_in_month = get_days_in_month(M)

    # In[ ]:

    # In[52]:

    DF_cba_org_data_cur = DF_cba_org_data_cur[DF_cba_org_data_cur['charge_point_count'] != 0]
    DF_cba_org_data_cur = DF_cba_org_data_cur[DF_cba_org_data_cur['plat_data_charging_volume'] != 0]

    # In[53]:

    DF_cba_org_data_cur['gun_charging_volume'] = DF_cba_org_data_cur['plat_data_charging_volume'] / DF_cba_org_data_cur[
        'charge_point_count'] / days_in_month

    # In[ ]:

    # In[54]:

    type_avg_daily_energy_per_gun = DF_cba_org_data_cur.groupby('station_category')[
        'gun_charging_volume'].mean().reset_index()

    # In[55]:

    type_avg_daily_energy_per_gun

    # In[ ]:

    # ### 功率利用率

    # In[56]:

    sql = """
        SELECT
          pue.*,
          cs.station_category
        FROM dp_pue_capacity_utilization pue
        LEFT JOIN charging_station cs
          ON pue.station_code COLLATE utf8mb4_unicode_ci
          = cs.station_no COLLATE utf8mb4_unicode_ci
        WHERE pue.data_category = '四川电动'
          AND cs.operation_status IN ('投运','停运')
        """
    DF_cba_pue = SQL(sql)
    # 新表的容量利用率即功率利用率，仅保留旧列名以兼容后续图表结构。
    DF_cba_pue['cba_month'] = (
        DF_cba_pue['month'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    )
    DF_cba_pue['pue'] = pd.to_numeric(
        DF_cba_pue['capacity_utilization_rate'], errors='coerce'
    )
    DF_cba_pue['station_category'] = DF_cba_pue['station_category'].replace({'高速': '高速公共'})
    DF_cba_pue = DF_cba_pue[DF_cba_pue['pue'].notna()].copy()
    DF_cba_pue_by_type = DF_cba_pue[
        DF_cba_pue['station_category'].isin(target_categories)
    ].copy()
    print('功率利用率新表筛选后：', DF_cba_pue.shape)

    # In[ ]:

    # In[57]:

    DF_cba_pue_CUR = DF_cba_pue_by_type[DF_cba_pue_by_type['cba_month'] == M].copy()

    # In[61]:

    type_pue = DF_cba_pue_CUR.groupby('station_category')['pue'].mean().reset_index()
    type_pue

    # In[62]:

    Operational_status = {
        "options": ["单枪日均充电量", "功率利用率"],
        "data": [
            {
                "radio": "单枪日均充电量",
                "legendName": ["单枪日均充电量"],
                "axisData": type_avg_daily_energy_per_gun['station_category'].tolist(),
                "chartData": [[round(x, 2) for x in type_avg_daily_energy_per_gun['gun_charging_volume']]],
                "yAxisName": "kWh"
            },
            {
                "radio": "功率利用率",
                "legendName": ["功率利用率"],
                "axisData": type_pue['station_category'].tolist(),
                "chartData": [[round(x, 2) for x in type_pue['pue']]],
                "yAxisName": "%"
            }
        ]
    }

    # In[63]:

    Operational_status

    # ### 写入数据库

    # In[64]:

    # 表和字段注释
    table_comment = "类型检测_首页_运营情况"
    column_comments = {
        'Operational_status': '运营情况',
        'update_time': '更新日期'
    }
    DF_Operational_status = pd.DataFrame([{
        'Operational_status': json.dumps(Operational_status, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Operational_status,
        table_name="dp_Operational_status",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 设备质量（当月）

    # ### 一次成功率

    # In[65]:

    sql = '''
    SELECT
      cs.station_category,  
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
    WHERE cs.merchant_nature = "电动公司"
    GROUP BY
      cs.station_category,
      dsr.stat_time

    '''
    DF_success = SQL(sql)
    DF_success = DF_success[DF_success['station_category'].isin(target_categories)]
    DF_success.loc[DF_success['station_category'] == '高速', 'station_category'] = '高速公共'

    # In[66]:

    df_firstrate = DF_success.copy()

    # In[67]:

    df_firstrate['stat_month'] = df_firstrate['stat_time'].astype(str).str.replace('-', '')

    # In[68]:

    df_month = df_firstrate[df_firstrate['stat_month'] == M].copy()

    # In[69]:

    df_month

    # In[70]:

    df_month['total_order_count'] = pd.to_numeric(df_month['total_order_count'], errors='coerce')
    df_month['station_success_rate'] = pd.to_numeric(df_month['station_success_rate'], errors='coerce')

    # In[71]:

    # 去除空值行
    df_month = df_month.dropna(subset=['total_order_count', 'station_success_rate'])
    # 计算加权成功次数
    df_month['weighted_success'] = df_month['total_order_count'] * df_month['station_success_rate']

    # In[72]:

    # 分组计算各类型的加权平均成功率
    df_type_success = (
        df_month
        .groupby('station_category')[['weighted_success', 'total_order_count']]
        .sum()
        .assign(
            type_success_rate=lambda d: (d['weighted_success'] / d['total_order_count']).round(4)
        )
        .reset_index()[['station_category', 'type_success_rate']]
    )

    # In[73]:

    df_type_success

    # In[74]:

    list_success = []
    list_success.append(df_type_success)

    # ### 可用率
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
    DF_operation_duration = DF_operation_duration[DF_operation_duration['station_category'].isin(target_categories)]
    DF_operation_duration.loc[DF_operation_duration['station_category'] == '高速', 'station_category'] = '高速公共'

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

    DF_operation_duration_1 = DF_operation_duration.groupby(['time', 'station_no']).agg(
        {'可用率': 'mean'}).reset_index()
    DF_operation_duration_1

    # 获取站点对应城市、站点类型的标签
    DF_operation_duration_2 = DF_operation_duration[['station_no', 'station_category', 'city']].drop_duplicates()
    DF_operation_duration_2

    DF_operation_duration = pd.merge(DF_operation_duration_1, DF_operation_duration_2, on='station_no', how='left')
    DF_operation_duration.head(1)

    # 处理时间

    DF_operation_duration['month'] = [i[:6] for i in DF_operation_duration['time']]

    DF_operation_duration['year'] = [i[:4] for i in DF_operation_duration['month']]

    DF_operation_duration = DF_operation_duration[~DF_operation_duration['station_no'].isna()]

    # In[80]:

    DF_operation_duration_1 = DF_operation_duration.groupby(['time', 'station_no']).agg(
        {'可用率': 'mean'}).reset_index()

    DF_operation_duration_2 = DF_operation_duration[['station_no', 'station_category', 'city']].drop_duplicates()

    DF_operation_duration = pd.merge(DF_operation_duration_1, DF_operation_duration_2, on='station_no', how='left')

    #  关键修复：覆盖后重新补充 month / year
    DF_operation_duration['month'] = DF_operation_duration['time'].astype(str).str[:6]
    DF_operation_duration['year'] = DF_operation_duration['month'].str[:4]

    # 筛选当前月数据
    df_month = DF_operation_duration[DF_operation_duration['month'] == M].copy()

    # 去除无效数据（如 operation_duration 为 0 会导致无穷）
    df_month = df_month[df_month['可用率'].notna()]
    # 按 station_category 计算平均可用率
    df_avail_by_type = (
        df_month
        .groupby('station_category')['可用率']
        .mean()
        .reset_index()
    )
    df_avail_by_type

    # In[ ]:

    # In[86]:

    Equipment_quality = {
        "options": ["一次成功率", "可用率"],
        "data": [
            {
                "radio": "一次成功率",
                "legendName": ["一次成功率"],
                "axisData": df_type_success['station_category'].tolist(),
                "chartData": [[round(x * 100, 2) for x in df_type_success['type_success_rate']]],
                "yAxisName": "%"
            },
            {
                "radio": "可用率",
                "legendName": ["可用率"],
                "axisData": df_avail_by_type['station_category'].tolist(),
                "chartData": [[round(x * 100, 2) for x in df_avail_by_type['可用率']]],
                "yAxisName": "%"
            }
        ]
    }

    # In[87]:

    Equipment_quality

    # ### 写入数据库

    # In[88]:

    # 表和字段注释
    table_comment = "类型检测_首页_设备质量"
    column_comments = {
        'Equipment_quality': '投资情况',
        'update_time': '更新日期'
    }
    DF_Equipment_quality = pd.DataFrame([{
        'Operational_status': json.dumps(Equipment_quality, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Equipment_quality,
        table_name="dp_Equipment_quality",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 经营情况（当月）

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
    cs.merchant_nature = "电动公司"
    and cs.operation_status in ('投运','停运')
    ) a
    left join 
    (select * from station_cba_org_data where cba_month like '%s' or  cba_month like '%s' ) b
    on a.station_no =b.station_no
    """ % (t1, t2)
    DF_cba_org_data = SQL(sql)
    DF_cba_org_data = DF_cba_org_data[DF_cba_org_data['station_category'].isin(target_categories)]
    DF_cba_org_data.loc[DF_cba_org_data['station_category'] == '高速', 'station_category'] = '高速公共'
    DF_cba_org_data = DF_cba_org_data.fillna(0)
    # 数据类型转换
    DF_cba_org_data['rec_data_elec_fee_revenue'] = DF_cba_org_data['rec_data_elec_fee_revenue'].astype(str).astype(
        float)
    DF_cba_org_data['rec_data_service_fee_revenue'] = DF_cba_org_data['rec_data_service_fee_revenue'].astype(
        str).astype(
        float)
    DF_cba_org_data['other_revenue_battery_swap_services'] = DF_cba_org_data[
        'other_revenue_battery_swap_services'].astype(
        str).astype(float)
    DF_cba_org_data['other_revenue_access_control_barriers'] = DF_cba_org_data[
        'other_revenue_access_control_barriers'].astype(str).astype(float)
    DF_cba_org_data['other_revenue_dr'] = DF_cba_org_data['other_revenue_dr'].astype(str).astype(float)

    DF_cba_org_data['rec_cost_elec_fee'] = DF_cba_org_data['rec_cost_elec_fee'].astype(str).astype(float)
    DF_cba_org_data['rec_cost_actual_rec_amount'] = DF_cba_org_data['rec_cost_actual_rec_amount'].astype(str).astype(
        float)
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
          where cs.merchant_nature = "电动公司"
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
    cs.merchant_nature = "电动公司"
    and cs.operation_status in ('投运','停运')
    ) a
    left join 
    (select * from fin_rec_result_detail where (rec_month like '%s' or  rec_month like '%s') and  merchant_id != 119 ) b
    on a.station_no =b.station_no
    """ % (t1, t2)
    fin_rec_result_detail = SQL(sql)
    fin_rec_result_detail = fin_rec_result_detail[fin_rec_result_detail['station_category'].isin(target_categories)]
    fin_rec_result_detail.loc[fin_rec_result_detail['station_category'] == '高速', 'station_category'] = '高速公共'
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
    DF_cba_org_data = pd.merge(DF_cba_org_data, DF_rent[['station_no', 'parking_fee']], how='left',
                               on='station_no').fillna(
        0)

    DF_cba_org_data['parking_fee'] = DF_cba_org_data['parking_fee'].astype('float')
    DF_cba_org_data['rec_cost'] = DF_cba_org_data['rec_cost'] + DF_cba_org_data['parking_fee']
    DF_cba_org_data.head(1)

    DF_cba_org_data['gross_profit'] = DF_cba_org_data['rec_data'] - DF_cba_org_data['rec_cost']
    DF_cba_org_data['rec_data'] = DF_cba_org_data['rec_data'].astype(float)
    DF_cba_org_data['rec_cost'] = DF_cba_org_data['rec_cost'].astype(float)
    DF_cba_org_data['gross_profit'] = DF_cba_org_data['gross_profit'].astype(float)
    DF_Business_Analysis = DF_cba_org_data.copy()

    # 按站点类型统计营收
    df_profit_income = (
        DF_cba_org_data[DF_cba_org_data['cba_month'] == M].groupby('station_category')['rec_data']
        .sum()
        .reset_index()
    )

    df_profit_income['rec_data'] = df_profit_income['rec_data'] / 10000  # 转万元

    # 按站点类型统计毛利
    df_profit_diff = (
        DF_cba_org_data[DF_cba_org_data['cba_month'] == M]  # 筛选指定月份
        .groupby('station_category')['gross_profit']
        .sum()
        .reset_index()
    )

    df_profit_diff['gross_profit'] = df_profit_diff['gross_profit'] / 10000  # 转万元

    # =====================================================
    # 5. 构建 Business_performance（你要的最终结构）
    # =====================================================

    Business_performance = {
        "options": ["营收", "毛利"],
        "data": [
            {
                "radio": "营收",
                "legendName": ["营收"],
                "axisData": df_profit_income['station_category'].tolist(),
                "chartData": [[round(x, 2) for x in df_profit_income['rec_data']]],
                "yAxisName": "万元"
            },
            {
                "radio": "毛利",
                "legendName": ["毛利"],
                "axisData": df_profit_diff['station_category'].tolist(),
                "chartData": [[round(x, 2) for x in df_profit_diff['gross_profit']]],
                "yAxisName": "万元"
            }
        ]
    }

    # In[111]:

    # ### 写入数据库

    # In[112]:

    # 表和字段注释
    table_comment = "类型检测_首页_经营情况"
    column_comments = {
        'Business_performance': '经营情况（当月）',
        'update_time': '更新日期'
    }
    DF_Business_performance = pd.DataFrame([{
        'Business_performance': json.dumps(Business_performance, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Business_performance,
        table_name="dp_Business_performance",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 运维情况

    # ### 单桩工单数量

    # In[113]:

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

    # In[114]:

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

    # In[116]:

    DF_SCGD = pd.merge(DF_SCDD, DF_dispatched_workorders, on='station_no', how='left')
    DF_SCGD = DF_SCGD[DF_SCGD['operation_status'] == '投运']

    # In[117]:

    DF_SCGD['单桩工单'] = DF_SCGD['dispatched_workorders'].fillna(0) / DF_SCGD['桩数量']
    DF_SCGD['单桩工单'] = pd.to_numeric(DF_SCGD['单桩工单'], errors='coerce').fillna(0)

    # In[118]:

    df_workorders = DF_SCGD[DF_SCGD['stat_time'] == M]
    df_workorders['单桩工单'].replace([np.inf, -np.inf], 0, inplace=True)

    # In[119]:

    DF_SCGD[DF_SCGD['stat_time'] == '202405']['单桩工单'].mean()

    # In[120]:

    df_workorders['单桩工单'].mean()

    # In[121]:

    # 转换 dispatched_workorders 为数值（强制转换无法解析的为 NaN，再填 0）
    df_workorders['dispatched_workorders'] = pd.to_numeric(df_workorders['dispatched_workorders'],
                                                           errors='coerce').fillna(0)

    # In[122]:

    c_workorders = df_workorders.groupby('station_category')['单桩工单'].mean().reset_index()

    # In[123]:

    c_workorders

    # In[124]:

    Operation_maintenance = {
        "options": ["单桩工单数量"],
        "data": [
            {
                "radio": "单桩工单数量",
                "legendName": ["单桩工单数量"],
                "axisData": c_workorders['station_category'].tolist(),
                "chartData": [[round(x, 2) for x in c_workorders['单桩工单']]],
                "yAxisName": "单"
            }

        ]
    }

    # In[125]:

    Operation_maintenance

    # ### 写入数据库

    # In[126]:

    # 表和字段注释
    table_comment = "类型检测_首页_运维情况"
    column_comments = {
        'Operation_maintenance': '单桩工单数量',
        'update_time': '更新日期'
    }
    DF_Operation_maintenance = pd.DataFrame([{
        'Operation_maintenance': json.dumps(Operation_maintenance, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Operation_maintenance,
        table_name="dp_Operation_maintenance",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 投运情况折线图

    # ### 充电枪数量

    # In[253]:

    valid_months = set(Data['month'])

    # In[ ]:

    # In[254]:

    df = DF_SCDD.copy()

    # In[ ]:

    # In[255]:

    # 1. 构造时间格式
    df['commissioning_time'] = pd.to_datetime(df['commissioning_time'], errors='coerce')
    df['投运年月'] = df['commissioning_time'].dt.strftime('%Y%m')
    # 2. 提取所有月份 & 类型组合（你已有）
    all_months = Data['month'].unique()
    all_types = df['station_category'].dropna().unique()
    full_index = pd.MultiIndex.from_product([all_months, all_types], names=['month', 'station_category'])
    # 3. 对每月，统计截至该月所有已投运的 total_point 累加值
    results = []
    for month in all_months:
        df_filtered = df[df['投运年月'] <= month]
        df_grouped = (
            df_filtered
            .groupby('station_category')['total_point']
            .sum()
            .reset_index()
        )
        df_grouped['month'] = month
        results.append(df_grouped)

    # 4. 合并并补全空值
    df_cumulative = pd.concat(results, ignore_index=True)
    df_cumulative = (
        df_cumulative.set_index(['month', 'station_category'])
        .reindex(full_index, fill_value=0)
        .reset_index()
        .rename(columns={'total_point': '累计投运枪数量'})
    )
    df_cumulative

    # ### 总额定功率

    # In[256]:

    # 3. 按月份循环，累计 station_capacity（投运站容量）
    results_capacity = []
    for month in all_months:
        df_filtered = df[df['投运年月'] <= month]
        df_grouped = (
            df_filtered
            .groupby('station_category')['station_capacity']
            .sum()
            .reset_index()
        )
        df_grouped['month'] = month
        results_capacity.append(df_grouped)

    # 4. 合并并补齐所有组合，缺失补 0
    df_capacity = pd.concat(results_capacity, ignore_index=True)
    df_capacity = (
        df_capacity.set_index(['month', 'station_category'])
        .reindex(full_index, fill_value=0)
        .reset_index()
        .rename(columns={'station_capacity': '累计投运站容量'})
    )

    # In[257]:

    df_capacity

    # In[258]:

    df_Operation_status_chart = pd.merge(df_cumulative, df_capacity, on=['month', 'station_category'], how='outer')

    # In[259]:

    df_Operation_status_chart['month'] = df_Operation_status_chart['month'].astype(str)
    df_Operation_status_chart['month_fmt'] = df_Operation_status_chart['month'].str[-2:].astype(int).astype(str) + '月'
    df_Operation_status_chart['month_int'] = df_Operation_status_chart['month'].astype(int)

    # In[260]:

    axis_data_order = df_Operation_status_chart[['month_int', 'month_fmt']].drop_duplicates().sort_values('month_int')
    axis_labels = axis_data_order['month_fmt'].tolist()
    month_order = axis_data_order['month_int'].tolist()

    # In[277]:

    metric_list = [
        ('累计投运枪数量', '累计充电枪数量'),
        ('累计投运站容量', '累计额定功率')
    ]

    # In[278]:

    site_types = ['城市公共', '高速公共', '重卡专用', '公交专用', '小区有序', '其他专用']

    # In[279]:

    metric_list

    # In[281]:

    # 投运情况折线图
    touyun_line_chart = {
        "metricDimensionList": [label for _, label in metric_list],
        "siteTypeList": site_types,
        "axisData": axis_labels,
        "data": []
    }

    for col, label in metric_list:
        chart_data = []
        for stype in site_types:
            values = []
            for m in month_order:
                match = df_Operation_status_chart[
                    (df_Operation_status_chart['station_category'] == stype) &
                    (df_Operation_status_chart['month_int'] == m)
                    ]
                if not match.empty:
                    values.append(int(match[col].values[0]))
                else:
                    values.append(0)
            chart_data.append({'name': stype, 'value': values})

        print(col)

        if col == '累计投运枪数量':
            touyun_line_chart["data"].append({
                "radio": label,
                "chartData": chart_data,
                "yAxisName": '个'
            })
        else:
            touyun_line_chart["data"].append({
                "radio": label,
                "chartData": chart_data,
                "yAxisName": 'kW'
            })

    # In[282]:

    touyun_line_chart

    # ### 写入数据库

    # In[283]:

    # 表和字段注释
    table_comment = "类型检测_首页_投运情况折线图"
    column_comments = {
        'result': '投运情况折线图',
        'update_time': '更新日期'
    }
    DF_Commissioning_chart = pd.DataFrame([{
        'result': json.dumps(touyun_line_chart, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Commissioning_chart,
        table_name="dp_Commissioning_chart",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 投资情况折线图

    # ### 总投资费用

    # In[142]:

    results = []
    # 确保 year_month 为字符串格式
    DF_SCDD_investment['year_month'] = DF_SCDD_investment['year_month'].astype(str)
    DF_SCDD_investment['investment_amount'] = pd.to_numeric(
        DF_SCDD_investment['investment_amount'], errors='coerce'
    ).fillna(0)
    DF_SCDD_investment['investment_amount'] = DF_SCDD_investment['investment_amount'] / 10000
    # 遍历每个月，计算累计投资
    for month_str in Data['month']:
        df_cum = DF_SCDD_investment[DF_SCDD_investment['year_month'] <= month_str]
        if df_cum.empty:
            continue

        df_grouped = (
            df_cum
            .groupby('station_category')['investment_amount']
            .sum()
            .reset_index()
        )
        df_grouped['month'] = month_str
        results.append(df_grouped)

    # 合并所有结果
    df_cumulative_investment = pd.concat(results, ignore_index=True)

    df_cumulative_investment = df_cumulative_investment.sort_values(by=['month', 'station_category'])
    # 查看结果

    # In[143]:

    df_cumulative_investment['investment_amount'] = df_cumulative_investment['investment_amount'].round(2)

    # In[144]:

    df_cumulative_investment

    # In[ ]:

    # ### 近一年投资情况

    # In[145]:

    nearly_invest['commissioning_month'] = pd.to_datetime(nearly_invest['commissioning_time']).dt.strftime('%Y%m')

    # In[146]:

    nearly_invest['investment_amount'] = nearly_invest['investment_amount'] / 10000

    # In[147]:

    nearly_invest['investment_amount'] = nearly_invest['investment_amount'].apply(float)
    nearly_invest['investment_amount'] = nearly_invest['investment_amount'].round(2)

    # In[148]:

    nearly_invest['investment_amount'] = nearly_invest['investment_amount'].apply(float)

    # In[149]:

    results = []
    # 确保 year_month 为字符串格式

    # 遍历每个月，计算累计投资
    for month_str in Data['month']:
        df_cum = nearly_invest[nearly_invest['commissioning_month'] == month_str]
        if df_cum.empty:
            continue

        df_grouped = (
            df_cum
            .groupby('station_category')['investment_amount']
            .sum()
            .reset_index()
            .rename(columns={'investment_amount': 'investment_nearly'})
        )
        df_grouped['month'] = month_str
        results.append(df_grouped)

    # 合并所有结果
    filtered_monthly_investment = pd.concat(results, ignore_index=True)

    filtered_monthly_investment = filtered_monthly_investment.sort_values(by=['month', 'station_category'])
    # 查看结果

    # In[150]:

    filtered_monthly_investment

    # In[ ]:

    # ### 回本情况

    # In[151]:

    sql = """
    select b.station_no,b.cba_month,
    sum(b.rec_data_elec_fee_revenue+b.rec_data_service_fee_revenue+b.other_revenue_battery_swap_services+
    b.other_revenue_op_subsidies+b.other_revenue_build_subsidies+b.other_revenue_access_control_barriers+b.other_revenue_dr) as revenue,
    sum(b.rec_cost_elec_fee+b.rec_cost_actual_rec_amount+b.rec_cost_plat_service+
    b.rec_cost_rent+b.om_cost_om+b.om_cost_spare_parts+b.om_cost_op_project+b.fin_cost_depreciation+b.fin_cost_labor) as cost
    from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    cs.merchant_nature = "电动公司"
    and operation_status in ('投运','退运','停运') ) a
    left join 
    (select * from station_cba_org_data  ) b
    on a.station_no =b.station_no
    GROUP BY a.station_name,b.station_no, b.cba_month
    """
    DF_cost_revenue_month = SQL(sql)
    # DF_cost_revenue_month = DF_cost_revenue_month[DF_cost_revenue_month['station_category'].isin(target_categories)]
    # DF_cost_revenue_month.loc[DF_cost_revenue_month['station_category'] == '高速', 'station_category'] = '高速公共'

    # In[152]:

    DF_1_month = pd.merge(DF_cost_revenue_month, DF_station, on='station_no', how='left')

    # In[153]:

    DF_1_month['revenue'] = DF_1_month['revenue']
    DF_1_month['cost'] = DF_1_month['cost']
    DF_1_month['investment_amount'] = DF_1_month['investment_amount']

    # In[154]:

    DF2_month = pd.merge(DF_1_month, DF_subsidy, on='station_no', how='left')

    # In[155]:

    DF2_month['station_no'] = DF2_month['station_no'].astype(str)
    DF_RENT['station_no'] = DF2_month['station_no'].astype(str)

    # In[156]:

    DF_rrentt_momth = DF2_month.merge(
        DF_RENT[['station_no', 'parking_fee']],
        on='station_no',
        how='left'
    )

    # In[157]:

    DF_rrentt_momth['total_subsidy'] = DF_rrentt_momth['total_subsidy'].fillna(0)
    DF_rrentt_momth['in'] = DF_rrentt_momth['revenue'].astype(float) + DF_rrentt_momth['total_subsidy'].astype(float)
    DF_rrentt_momth['investment_amount'] = DF_rrentt_momth['investment_amount'].fillna(0)
    DF_rrentt_momth['parking_fee'] = DF_rrentt_momth['parking_fee'].fillna(0)
    DF_rrentt_momth['cost'] = DF_rrentt_momth['cost'].fillna(0)
    DF_rrentt_momth['out'] = DF_rrentt_momth['cost'].astype(float) + DF_rrentt_momth['investment_amount'].astype(
        float) + DF_rrentt_momth['parking_fee'].astype(float)

    # In[158]:

    DF_rrentt_momth['huiben'] = DF_rrentt_momth['in'] / DF_rrentt_momth['out'] * 100

    # In[159]:

    DF_rrentt_momth['huiben'] = DF_rrentt_momth['huiben'].replace([np.inf, -np.inf], 0)
    DF_rrentt_momth['huiben'] = pd.to_numeric(DF_rrentt_momth['huiben'], errors='coerce').fillna(0)

    # In[160]:

    df_filtered_huiebn = DF_rrentt_momth[DF_rrentt_momth['cba_month'].isin(Data['month'].astype(str))]

    # In[161]:

    # 分组计算
    result_huiben = (
        df_filtered_huiebn
        .groupby(['cba_month', 'station_category'])['huiben']
        .mean()
        .reset_index()
        .rename(columns={'cba_month': 'month', 'huiben': 'huiben_mean'})
    )

    # In[162]:

    result_huiben['huiben_mean'] = result_huiben['huiben_mean'].fillna(0)
    result_huiben

    # In[163]:

    df_Investment_chart = pd.merge(df_cumulative_investment, filtered_monthly_investment,
                                   on=['month', 'station_category'], how='outer')
    df_Investment_chart['investment_nearly'] = df_Investment_chart['investment_nearly'].fillna(0)
    df_Investment_chart['investment_amount'] = df_Investment_chart['investment_amount'].fillna(0)

    # In[164]:

    df_Investment_chart

    # In[165]:

    # df_Investment_chart['month'] = df_Investment_chart['month'].astype(str)
    # df_Investment_chart['month_fmt'] = df_Investment_chart['month'].str[-2:].astype(int).astype(str) + '月'
    # df_Investment_chart['month_int'] = df_Investment_chart['month'].astype(int)
    # axis_data_order = df_Investment_chart[['month_int', 'month_fmt']].drop_duplicates().sort_values('month_int')
    # axis_labels = axis_data_order['month_fmt'].tolist()
    # month_order = axis_data_order['month_int'].tolist()
    # metric_list = [
    #     ('investment_amount', '总投资费用'),
    #     ('investment_nearly','近一年投资'),
    #     ('huiben_mean', '回本情况')
    # ]

    # result = {
    #     "metricDimensionList": [label for _, label in metric_list],
    #     "siteTypeList": site_types,
    #     "axisData": axis_labels,
    #     "yAxisName": "万元",
    #     "data": []
    # }

    # for col, label in metric_list:
    #     chart_data = []
    #     for stype in site_types:
    #         values = []
    #         for m in month_order:
    #             match = df_Investment_chart[
    #                 (df_Investment_chart['station_category'] == stype) &
    #                 (df_Investment_chart['month_int'] == m)
    #             ]
    #             if not match.empty:
    #                 values.append(int(match[col].values[0]))
    #             else:
    #                 values.append(0)
    #         chart_data.append({'name': stype, 'value': values})

    #     result["data"].append({
    #         "radio": label,
    #         "chartData": chart_data
    #     })

    # In[166]:

    df_Investment_chart['month'] = df_Investment_chart['month'].astype(str)
    df_Investment_chart['month_fmt'] = df_Investment_chart['month'].str[-2:].astype(int).astype(str) + '月'
    df_Investment_chart['month_int'] = df_Investment_chart['month'].astype(int)

    axis_data_order = df_Investment_chart[['month_int', 'month_fmt']].drop_duplicates().sort_values('month_int')
    axis_labels = axis_data_order['month_fmt'].tolist()
    month_order = axis_data_order['month_int'].tolist()

    # 去掉回本情况，只保留前两个指标
    metric_list = [
        ('investment_amount', '累计投资金额'),
        ('investment_nearly', '近一年投资')
    ]

    result = {
        "metricDimensionList": [label for _, label in metric_list],
        "siteTypeList": site_types,
        "axisData": axis_labels,

        "data": []
    }

    for col, label in metric_list:
        chart_data = []
        for stype in site_types:
            values = []
            for m in month_order:
                match = df_Investment_chart[
                    (df_Investment_chart['station_category'] == stype) &
                    (df_Investment_chart['month_int'] == m)
                    ]
                if not match.empty:
                    values.append(round(float(match[col].values[0]), 2))
                else:
                    values.append(0)
            chart_data.append({'name': stype, 'value': values})

        result["data"].append({
            "radio": label,
            "chartData": chart_data,
            "yAxisName": "万元"
        })

    # In[167]:

    print(result)

    # ### 写入数据库

    # In[168]:

    # 表和字段注释
    table_comment = "类型检测_首页_投资情况折线图"
    column_comments = {
        'result': '投资情况折线图',
        'update_time': '更新日期'
    }
    DF_Investment_chart = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Investment_chart,
        table_name="dp_Investment_chart",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 运营情况折线图

    # ### 单枪日均充电量

    # In[169]:

    # 1. 确保 cba_month 和 Data['month'] 都是字符串格式
    DF_org_data_pre_gun['cba_month'] = DF_org_data_pre_gun['cba_month'].astype(str)
    month_list = Data['month'].astype(str).tolist()
    # 2. 筛选指定月份数据
    df_gun_filtered = DF_org_data_pre_gun[DF_org_data_pre_gun['cba_month'].isin(month_list)]

    # # 3. 添加每月天数
    df_gun_filtered['days_in_month'] = df_gun_filtered['cba_month'].apply(get_days_in_month)
    #
    # # 4. 计算单枪日均充电量
    # df_gun_filtered['gun_charging_volume'] = (
    #     df_gun_filtered['plat_data_charging_volume'] /
    #     df_gun_filtered['charge_point_count'] /
    #     df_gun_filtered['days_in_month']
    # )
    #
    # # 5. 过滤无效记录（除数为0或充电量为0）
    # df_gun_filtered = df_gun_filtered[
    #     (df_gun_filtered['charge_point_count'] > 0) &
    #     (df_gun_filtered['plat_data_charging_volume'] > 0)
    # ]

    # 6. 分组统计 station_category 每月均值

    df_gun_filtered['gun_charging_volume'] = df_gun_filtered['gun_charging_volume'] / df_gun_filtered['days_in_month']
    df_avg_gun_volume = (
        df_gun_filtered
        .groupby(['cba_month', 'station_category'])['gun_charging_volume']
        .mean()
        .reset_index()
        .rename(columns={'cba_month': 'month', 'gun_charging_volume': '单枪日均充电量'})
    )

    # In[170]:

    M

    # In[171]:

    df_avg_gun_volume

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # ### 功率利用率

    # In[172]:

    month_list = Data['month'].astype(str).tolist()
    # 2. 筛选指定月份数据
    DF_cba_pue_chart = DF_cba_pue_by_type[DF_cba_pue_by_type['cba_month'].isin(month_list)]

    # In[173]:

    monthly_util = DF_cba_pue_chart.groupby(['cba_month', 'station_category'])['pue'].mean().reset_index()

    # In[174]:

    monthly_util = monthly_util.rename(columns={'cba_month': 'month'})
    monthly_util['pue'] = monthly_util['pue'].round(2)
    monthly_util

    # In[175]:

    df_operations_chart = pd.merge(df_avg_gun_volume, monthly_util, on=['month', 'station_category'], how='outer')
    df_operations_chart['month'] = df_operations_chart['month'].astype(str)
    df_operations_chart['month_fmt'] = df_operations_chart['month'].str[-2:].astype(int).astype(str) + '月'
    df_operations_chart['month_int'] = df_operations_chart['month'].astype(int)
    axis_data_order = df_operations_chart[['month_int', 'month_fmt']].drop_duplicates().sort_values('month_int')
    axis_labels = axis_data_order['month_fmt'].tolist()
    month_order = axis_data_order['month_int'].tolist()
    metric_list = [
        ('单枪日均充电量', '单枪日均充电量'),
        ('pue', '功率利用率')
    ]

    result = {
        "metricDimensionList": [label for _, label in metric_list],
        "siteTypeList": site_types,
        "axisData": axis_labels,

        "data": []
    }

    for col, label in metric_list:
        chart_data = []
        for stype in site_types:
            values = []
            for m in month_order:
                match = df_operations_chart[
                    (df_operations_chart['station_category'] == stype) &
                    (df_operations_chart['month_int'] == m)
                    ]
                if not match.empty:
                    values.append(round(float(match[col].values[0]), 2))
                else:
                    values.append(0)
            chart_data.append({'name': stype, 'value': values})
        # print(col)
        if col == '单枪日均充电量':
            result["data"].append({
                "radio": label,
                "chartData": chart_data,
                "yAxisName": "kWh"
            })
        else:
            result["data"].append({
                "radio": label,
                "chartData": chart_data,
                "yAxisName": "%"
            })

    # In[176]:

    result

    # In[177]:

    # 假设这些变量你已经提前定义好了
    # df_Operation_status_chart: DataFrame 包含你的数据
    # axis_labels: ['6月', '7月', ..., '11月']
    # month_order: [202406, 202407, ..., 202411]
    # site_types: ['城市公共', ..., '其他专用']
    # metric_list: [('累计投运枪数量', '充电枪数量'), ('累计投运站容量', '总额定功率')]

    # ### 写入数据库

    # In[178]:

    # 表和字段注释
    table_comment = "类型检测_首页_运营情况折线图"
    column_comments = {
        'result': '运营情况折线图',
        'update_time': '更新日期'
    }
    DF_operations_chart = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_operations_chart,
        table_name="dp_operations_chart",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 设备质量折线图

    # ### 一次成功率

    # In[ ]:

    # In[179]:

    month_list = Data['month'].astype(str).tolist()
    # 2. 筛选指定月份数据
    trend_table = df_firstrate[df_firstrate['stat_month'].isin(month_list)]

    # In[ ]:

    # In[180]:

    monthly_success_rate = trend_table.groupby(['stat_month', 'station_category'])[
        'station_success_rate'].mean().reset_index()

    # In[ ]:

    # In[181]:

    monthly_success_rate.rename(columns={'stat_month': 'month'}, inplace=True)
    monthly_success_rate['station_success_rate'] = (monthly_success_rate['station_success_rate'] * 100).round(2)
    monthly_success_rate

    # ### 可用率

    # In[ ]:

    # In[182]:

    month_list = Data['month'].astype(str).tolist()
    # 2. 筛选指定月份数据
    cuse_rate = DF_operation_duration[DF_operation_duration['month'].isin(month_list)]

    # In[183]:

    cuse_rate_chart = cuse_rate.groupby(['month', 'station_category'])['可用率'].mean().reset_index()

    # In[184]:

    cuse_rate_chart['可用率'] = (cuse_rate_chart['可用率'] * 100).round(2)

    # In[185]:

    cuse_rate_chart

    # In[186]:

    df_Equipment_quality_chart = pd.merge(monthly_success_rate, cuse_rate_chart, on=['month', 'station_category'],
                                          how='outer')
    df_Equipment_quality_chart['month'] = df_Equipment_quality_chart['month'].astype(str)
    df_Equipment_quality_chart['month_fmt'] = df_Equipment_quality_chart['month'].str[-2:].astype(int).astype(str) + '月'
    df_Equipment_quality_chart['month_int'] = df_Equipment_quality_chart['month'].astype(int)
    axis_data_order = df_Equipment_quality_chart[['month_int', 'month_fmt']].drop_duplicates().sort_values('month_int')
    axis_labels = axis_data_order['month_fmt'].tolist()
    month_order = axis_data_order['month_int'].tolist()
    metric_list = [
        ('station_success_rate', '一次成功率'),
        ('可用率', '可用率')
    ]
    # data_Equipment_chart  = []
    # for col, label in metric_list:
    #     chart_data = []
    #     for stype in site_types:
    #         values = []
    #         for m in month_order:
    #             m_str = str(m)
    #             match = df_Equipment_quality_chart[
    #                 (df_Equipment_quality_chart['station_category'] == stype) &
    #                 (df_Equipment_quality_chart['month'] == m_str)
    #             ]

    #             if not match.empty:
    #                 value = match[col].values[0]
    #                 if pd.notna(value):
    #                     values.append(int(value))
    #                 else:
    #                     values.append(0)
    #             else:
    #                 values.append(0)

    #         chart_data.append({'name': stype, 'value': values})

    #     y_axis_name = '%'

    # data_Equipment_chart.append({
    #     'radio': label,
    #     'chartData': chart_data,
    #     'yAxisName': y_axis_name
    # })
    result = {
        "metricDimensionList": [label for _, label in metric_list],
        "siteTypeList": site_types,
        "axisData": axis_labels,

        "data": []
    }

    for col, label in metric_list:
        chart_data = []
        for stype in site_types:
            values = []
            for m in month_order:
                match = df_Equipment_quality_chart[
                    (df_Equipment_quality_chart['station_category'] == stype) &
                    (df_Equipment_quality_chart['month_int'] == m)
                    ]
                if not match.empty:
                    values.append(round(float(match[col].values[0]), 2) if pd.notna(match[col].values[0]) else 0.00)
                else:
                    values.append(0)
            chart_data.append({'name': stype, 'value': values})

        result["data"].append({
            "radio": label,
            "chartData": chart_data,
            "yAxisName": "%"
        })

    # In[187]:

    result

    # ### 写入数据库

    # In[188]:

    # 表和字段注释
    table_comment = "类型检测_首页_设备质量折线图"
    column_comments = {
        'result': '设备质量折线图',
        'update_time': '更新日期'
    }
    DF_Equipment_chart = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Equipment_chart,
        table_name="dp_Equipment_chart",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 经营情况折线图

    # ### 营收

    # In[189]:

    month_list = Data['month'].astype(str).tolist()
    # 2. 筛选指定月份数据
    df_all_profit_56 = DF_cba_org_data[DF_cba_org_data['cba_month'].isin(month_list)]

    # In[190]:

    monthly_revenue = df_all_profit_56.groupby(['cba_month', 'station_category'])['rec_data'].sum().reset_index()

    # In[191]:

    monthly_revenue['rec_data'] = monthly_revenue['rec_data'] / 10000
    monthly_revenue['rec_data'] = monthly_revenue['rec_data'].round(2)
    monthly_revenue

    # ### 毛利

    # In[192]:

    df_profit_diff = df_all_profit_56.groupby(['cba_month', 'station_category'])['gross_profit'].sum().reset_index()

    # In[193]:

    df_profit_diff['gross_profit'] = df_profit_diff['gross_profit'] / 10000
    df_profit_diff['gross_profit'] = df_profit_diff['gross_profit'].round(2)

    df_profit_diff

    # In[194]:

    df_Management_chart = pd.merge(monthly_revenue, df_profit_diff, on=['cba_month', 'station_category'], how='outer')
    df_Management_chart['cba_month'] = df_Management_chart['cba_month'].astype(str)
    df_Management_chart['month_fmt'] = df_Management_chart['cba_month'].str[-2:].astype(int).astype(str) + '月'
    df_Management_chart['month_int'] = df_Management_chart['cba_month'].astype(int)
    axis_data_order = df_Management_chart[['month_int', 'month_fmt']].drop_duplicates().sort_values('month_int')
    axis_labels = axis_data_order['month_fmt'].tolist()
    month_order = axis_data_order['month_int'].tolist()
    metric_list = [
        ('rec_data', '营收'),
        ('gross_profit', '毛利')
    ]

    result = {
        "metricDimensionList": [label for _, label in metric_list],
        "siteTypeList": site_types,
        "axisData": axis_labels,

        "data": []
    }

    for col, label in metric_list:
        chart_data = []
        for stype in site_types:
            values = []
            for m in month_order:
                match = df_Management_chart[
                    (df_Management_chart['station_category'] == stype) &
                    (df_Management_chart['month_int'] == m)
                    ]
                if not match.empty:
                    values.append(round(float(match[col].values[0]), 2) if pd.notna(match[col].values[0]) else 0.00)
                else:
                    values.append(0)
            chart_data.append({'name': stype, 'value': values})

        result["data"].append({
            "radio": label,
            "chartData": chart_data,
            "yAxisName": "万元",
        })

    # In[195]:

    result

    # ### 写入数据库

    # In[196]:

    # 表和字段注释
    table_comment = "类型检测_首页_经营情况折线图"
    column_comments = {
        'result': '经营情况折线图',
        'update_time': '更新日期'
    }
    DF_Business_chart = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_Business_chart,
        table_name="dp_Business_chart",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 运维情况折线图

    # ### 工单数量

    # In[197]:

    # DF_SCGD['单桩工单']

    # In[198]:

    Data

    # In[199]:

    month_list = Data['month'].astype(str).tolist()
    # 2. 筛选指定月份数据
    df_workorders45 = DF_SCGD[DF_SCGD['stat_time'].isin(month_list)]

    # In[200]:

    # df_workorders['单桩工单'].mean()

    # In[201]:

    monthly_workorders = df_workorders45.groupby(['stat_time', 'station_category'])['单桩工单'].mean().reset_index()

    # In[202]:

    # monthly_workorders['单桩工单'] = monthly_workorders['单桩工单'].round(2)
    # monthly_workorders

    # In[203]:

    month_list = Data['month'].astype(str).tolist()

    # 筛选指定月份数据
    df_workorders45 = DF_SCGD[DF_SCGD['stat_time'].astype(str).isin(month_list)]

    # 计算平均单桩工单
    monthly_workorders = df_workorders45.groupby(['stat_time', 'station_category'])['单桩工单'].mean().reset_index()
    monthly_workorders['单桩工单'] = monthly_workorders['单桩工单'].round(2)

    # 生成所有月份和站点类型的笛卡尔积
    station_categorys = DF_SCGD['station_category'].unique()
    full_index = pd.MultiIndex.from_product([month_list, station_categorys], names=['stat_time', 'station_category'])
    full_df = pd.DataFrame(index=full_index).reset_index()

    # 与计算结果合并，缺失部分用0填充
    monthly_workorders = pd.merge(full_df, monthly_workorders, on=['stat_time', 'station_category'], how='left')
    monthly_workorders['单桩工单'] = monthly_workorders['单桩工单'].fillna(0)

    # In[247]:

    monthly_workorders['单桩工单'] = monthly_workorders['单桩工单'].round(2)

    # In[248]:

    monthly_workorders['stat_time'] = monthly_workorders['stat_time'].astype(str)
    monthly_workorders['month_fmt'] = monthly_workorders['stat_time'].str[-2:].astype(int).astype(str) + '月'
    monthly_workorders['month_int'] = monthly_workorders['stat_time'].astype(int)
    axis_data_order = monthly_workorders[['month_int', 'month_fmt']].drop_duplicates().sort_values('month_int')
    axis_labels = axis_data_order['month_fmt'].tolist()
    month_order = axis_data_order['month_int'].tolist()
    metric_list = [
        ('单桩工单', '单桩工单数量')
    ]
    monthly_workorders['单桩工单'] = pd.to_numeric(monthly_workorders['单桩工单'], errors='coerce')
    result = {
        "metricDimensionList": [label for _, label in metric_list],
        "siteTypeList": site_types,
        "axisData": axis_labels,

        "data": []
    }

    for col, label in metric_list:
        chart_data = []
        for stype in site_types:
            values = []
            for m in month_order:
                match = monthly_workorders[
                    (monthly_workorders['station_category'] == stype) &
                    (monthly_workorders['month_int'] == m)
                    ]
                if not match.empty:
                    values.append(float(match[col].values[0]) if pd.notna(match[col].values[0]) else 0.0)

                else:
                    values.append(0)
            chart_data.append({'name': stype, 'value': values})

        result["data"].append({
            "radio": label,
            "chartData": chart_data,
            "yAxisName": "单"
        })

    # In[205]:

    # result = {
    #     "metricDimensionList": [label for _, label in metric_list],
    #     "siteTypeList": site_types,
    #     "axisData": axis_labels,
    #     "yAxisName": "单",
    #     "data": []
    # }

    # for col, label in metric_list:
    #     chart_data = []
    #     for stype in site_types:
    #         values = []
    #         for m in month_order:
    #             match = monthly_workorders[
    #                 (monthly_workorders['station_category'] == stype) &
    #                 (monthly_workorders['month_int'] == m)
    #             ]
    #             if not match.empty:
    #                values.append(int(match[col].values[0]) if pd.notna(match[col].values[0]) else 0)
    #             else:
    #                 values.append(0)
    #         chart_data.append({'name': stype, 'value': values})

    #     result["data"].append({
    #         "radio": label,
    #         "chartData": chart_data
    #     })

    # In[249]:

    result

    # ### 写入数据库

    # In[250]:

    # 表和字段注释
    table_comment = "类型检测_首页_运维情况折线图"
    column_comments = {
        'result': '运维情况折线图',
        'update_time': '更新日期'
    }
    DF_workorders_chart = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_workorders_chart,
        table_name="dp_workorders_chart",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )

    # ## 四川电动旗下充电基础设施建设现状

    # In[208]:

    # sql = """
    # SELECT
    # cs.station_name,cs.station_no,cs.investment_amount,cs.commissioning_time,cs.station_category
    # FROM
    # charging_station cs
    # LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    # where
    # cs.merchant_nature = "电动公司"
    # and operation_status ='投运'

    # """
    # DF_station = SQL(sql)

    # sql = f"""
    # select station_no,sum(total_subsidy) as total_subsidy from dp_subsidy_NEW
    # where year <='{year}'
    # GROUP BY station_no
    # """
    # DF_subsidy = SQL(sql)

    # sql = """
    # select b.station_no,
    # sum(IFNULL(b.rec_data_elec_fee_revenue,0)+IFNULL(b.rec_data_service_fee_revenue,0)+IFNULL(b.other_revenue_battery_swap_services,0)+
    # IFNULL(b.other_revenue_op_subsidies,0)+IFNULL(b.other_revenue_build_subsidies,0)+IFNULL(b.other_revenue_access_control_barriers,0)+IFNULL(b.other_revenue_dr,0)) as revenue,
    # sum(IFNULL(b.rec_cost_elec_fee,0)+IFNULL(b.rec_cost_actual_rec_amount,0)+IFNULL(b.rec_cost_plat_service,0)+
    # IFNULL(b.rec_cost_rent,0)+IFNULL(b.om_cost_om,0)+IFNULL(b.om_cost_spare_parts,0)+IFNULL(b.om_cost_op_project,0)+IFNULL(b.fin_cost_depreciation+b.fin_cost_labor,0)) as cost
    # from
    # (SELECT
    # cs.*
    # FROM
    # charging_station cs
    # LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    # where
    # cs.merchant_nature = "电动公司"
    # and operation_status ='投运' and  investment_amount is not null) a
    # left join
    # (select * from station_cba_org_data  ) b
    # on a.station_no =b.station_no
    # GROUP BY a.station_name,b.station_no
    # """
    # DF_cost_revenue = SQL(sql)

    # sql = """
    # SELECT
    # cs.station_no,cs.property_owner_merhant_id,rm.merchant_id,
    # JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) AS parking_fee
    # FROM
    # charging_station cs
    # LEFT JOIN
    # rec_merchant_rec_station rmr ON cs.station_no = rmr.station_on
    # LEFT JOIN
    # rec_merchant rm ON rmr.merchant_id = rm.merchant_id
    # LEFT JOIN
    # scdd_rec_rules sr ON rm.merchant_id = sr.merchant_id
    # where property_owner_merhant_id =119
    # and  JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL

    # """
    # DF_rent = SQL(sql)
    # if int(M[4:])==12:
    #     M_next = str(int(M[:4])+1)+'01'
    # else:
    #     M_next = M[:4]+str(int(M[4:])+1).rjust(2, "0")
    # sql = """
    # select b.merchant_profit_amount,b.rec_month,a.station_no,a.city,a.station_category,a.dc_charge_point_count,a.ac_charge_point_count from
    # (SELECT
    # cs.*
    # FROM
    # charging_station cs
    # LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    # where
    # cs.merchant_nature = "电动公司"
    # and cs.operation_status in ('投运','停运')
    # ) a
    # left join
    # (select * from fin_rec_result_detail where rec_month <%s and   merchant_id != 119 ) b
    # on a.station_no =b.station_no
    # """%(M_next)
    # fin_rec_result_detail = SQL(sql)

    # # sql = """
    # # select * from  dp_value_added
    # # """
    # # DF_value_added = SQL(sql)
    # DF_1 = pd.merge(DF_station,DF_cost_revenue,on='station_no',how='left')
    # # 处理投运时间字段
    # DF_1['year'] = DF_1['commissioning_time'].dt.year
    # DF_1['year_month'] = DF_1['commissioning_time'].dt.strftime('%Y%m')
    # DF_rent = DF_rent[['station_no','parking_fee']]
    # DF_rent['parking_fee'] = DF_rent['parking_fee'].astype('float')
    # DF_1 = pd.merge(DF_1,DF_rent,on='station_no',how='left')
    # DF_1['month'] = [int(i[4:]) for i in DF_1['year_month']]
    # DF_1['month_num'] = [x+y for x,y in zip([int(M[4:])-i for i in  DF_1['month']],[(int(M[:4])-i)*12 for i in  DF_1['year']])]
    # DF_1['rent'] = DF_1['parking_fee']*DF_1['month_num']
    # DF_1['rent'] = DF_1['rent'].fillna(0)
    # DF_1 = DF_1[DF_1['year_month']<=M]
    # d1 = len(DF_1)
    # DF_1 = DF_1[DF_1['investment_amount'].notna()]
    # fin_rec_result_detail = fin_rec_result_detail.fillna(0)
    # fin_rec_result_detail = fin_rec_result_detail[['station_no','merchant_profit_amount']]
    # # fin_rec_result_detail =fin_rec_result_detail.rename(columns={'rec_month':'year_month'})
    # fin_rec_result_detail = fin_rec_result_detail.groupby(['station_no']).agg({'merchant_profit_amount':'sum'}).reset_index()
    # DF_1 = pd.merge(DF_1,fin_rec_result_detail,on=['station_no'],how='left')
    # DF_1 = DF_1.fillna(0)
    # DF_1['revenue'] = DF_1['revenue'].astype('float')/10000
    # DF_1['cost'] = DF_1['cost'].astype('float')/10000 + DF_1['rent']/10000
    # DF_1['investment_amount'] = DF_1['investment_amount'].astype('float')/10000
    # DF_1['merchant_profit_amount'] = DF_1['merchant_profit_amount'].astype('float')/10000
    # DF = pd.merge(DF_1,DF_subsidy,on='station_no',how='left')
    # DF = DF.fillna(0)
    # DF['in']=DF['revenue'].astype('float')+DF['total_subsidy'].astype('float')
    # DF['out']=DF['cost'].astype('float')+DF['investment_amount'].astype('float')+DF['merchant_profit_amount'].astype('float')
    # sql1 = """
    # SELECT
    #   b.station_no,
    #   SUM(
    #     IFNULL(b.rec_data_elec_fee_revenue, 0) +
    #     IFNULL(b.rec_data_service_fee_revenue, 0) +
    #     IFNULL(b.other_revenue_battery_swap_services, 0) +
    #     IFNULL(b.other_revenue_op_subsidies, 0) +
    #     IFNULL(b.other_revenue_build_subsidies, 0) +
    #     IFNULL(b.other_revenue_access_control_barriers, 0) +
    #     IFNULL(b.other_revenue_dr, 0)
    #   ) AS revenue,
    #   SUM(
    #     IFNULL(b.rec_cost_elec_fee, 0) +
    #     IFNULL(b.rec_cost_actual_rec_amount, 0) +
    #     IFNULL(b.rec_cost_plat_service, 0) +
    #     IFNULL(b.rec_cost_rent, 0) +
    #     IFNULL(b.om_cost_om, 0) +
    #     IFNULL(b.om_cost_spare_parts, 0) +
    #     IFNULL(b.om_cost_op_project, 0) +
    #     IFNULL(b.fin_cost_depreciation + b.fin_cost_labor, 0)
    #   ) AS cost
    # FROM (
    #   SELECT cs.*
    #   FROM charging_station cs
    #   LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    #   WHERE
    #     cs.merchant_nature = "电动公司"
    #     AND investment_amount IS NOT NULL
    #     AND cs.station_name IN (
    #       '四川省成都市彭州市濛阳镇供电所电动汽车充电站',
    #       '沪蓉高速遂宁服务区公共充电站成都方向',
    #       '沪蓉高速遂宁服务区公共充电站上海方向',
    #       '四川省成都市成华区麻石桥充电站',
    #       '四川省成都市成华区麻石桥充电站二期'
    #     )
    # ) a
    # LEFT JOIN station_cba_org_data b ON a.station_no = b.station_no
    # GROUP BY a.station_name, b.station_no

    # """
    # df1 = SQL(sql1)
    # sql2="""select station_no,sum(total_subsidy) as total_subsidy from dp_subsidy_NEW
    # where station_no IN (
    #   "300003000100002472",
    #   "300003000100002473",
    #   "300003013200011",
    #   "300003013200099",
    #   "300003013200105",
    #   "300003013200108"
    # )
    # GROUP BY station_no"""
    # df2 = SQL(sql2)
    # sql3 = """SELECT
    #  station_no,investment_amount
    # FROM charging_station cs
    # LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    # WHERE
    #   cs.merchant_nature = "电动公司"
    #   AND cs.station_name IN (
    #   "300003000100002472",
    #   "300003000100002473",
    #   "300003013200011",
    #   "300003013200099",
    #   "300003013200105",
    #   "300003013200108"
    #   )"""
    # df3 = SQL(sql3)
    # df4 = fin_rec_result_detail[fin_rec_result_detail['station_no'].isin(["300003000100002472",
    #   "300003000100002473",
    #   "300003013200011",
    #   "300003013200099",
    #   "300003013200105"])].fillna(0)
    # df_temp= pd.merge(pd.merge(df1,df2,on='station_no',how='left'),df3,on='station_no',how='left')
    # df_temp = pd.merge(df_temp,df4,on='station_no',how='left')
    # df_temp = df_temp.fillna(0)
    # df_temp['revenue'] = df_temp['revenue']/10000
    # df_temp['cost'] = df_temp['cost']/10000
    # df_temp['in'] = df_temp['revenue'].astype('float')+df_temp['total_subsidy'].astype('float')
    # df_temp['out'] = df_temp['cost'].astype('float')+df_temp['investment_amount'].astype('float')+df_temp['merchant_profit_amount'].astype('float')
    # DF.loc[DF['station_no']=='300003000100019488','in']  =DF[DF['station_no']=='300003000100019488']['in'].values[0]+df_temp[df_temp['station_no']=='300003013200108']['in'].values[0]
    # DF.loc[DF['station_no']=='300003000100017539','in']  =DF[DF['station_no']=='300003000100017539']['in'].values[0]+df_temp[df_temp['station_no']=='300003000100002472']['in'].values[0]
    # DF.loc[DF['station_no']=='300003000100017538','in']  =DF[DF['station_no']=='300003000100017538']['in'].values[0]+df_temp[df_temp['station_no']=='300003000100002473']['in'].values[0]
    # DF.loc[DF['station_no']=='300003000100019487','in']  =DF[DF['station_no']=='300003000100019487']['in'].values[0]+df_temp[df_temp['station_no']=='300003013200011']['in'].values[0]+df_temp[df_temp['station_no']=='300003013200099']['in'].values[0]
    # DF.loc[DF['station_no']=='300003000100019488','out']  =DF[DF['station_no']=='300003000100019488']['out'].values[0]+df_temp[df_temp['station_no']=='300003013200108']['out'].values[0]
    # DF.loc[DF['station_no']=='300003000100017539','out']  =DF[DF['station_no']=='300003000100017539']['out'].values[0]+df_temp[df_temp['station_no']=='300003000100002472']['out'].values[0]
    # DF.loc[DF['station_no']=='300003000100017538','out']  =DF[DF['station_no']=='300003000100017538']['out'].values[0]+df_temp[df_temp['station_no']=='300003000100002473']['out'].values[0]
    # DF.loc[DF['station_no']=='300003000100019487','out']  =DF[DF['station_no']=='300003000100019487']['out'].values[0]+df_temp[df_temp['station_no']=='300003013200011']['out'].values[0]+df_temp[df_temp['station_no']=='300003013200099']['out'].values[0]

    # In[209]:

    DF.loc[DF['station_category'] == '高速', 'station_category'] = '高速公共'

    # In[210]:

    huibenzhandian.groupby('station_category').agg({'station_no': 'count'})

    # In[211]:

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

    # ### 建设情况维度

    # #### 充电枪总数

    # In[212]:

    # 将当前月 M 转换为 datetime 对象（取当月最后一天）
    month_end = pd.to_datetime(M, format='%Y%m') + pd.offsets.MonthEnd(0)

    # 筛选所有在 M 月及之前投运的站点
    df_in_service = DF_SCDD[DF_SCDD['commissioning_time'] <= month_end]

    # 计算累计枪数
    total_guns = df_in_service['total_point'].sum()

    total_guns

    # In[213]:

    DF_SCDD

    # #### 总额定功率

    # In[214]:

    # 确保额定功率为数值型
    DF_SCDD['station_capacity'] = pd.to_numeric(DF_SCDD['station_capacity'], errors='coerce')
    # 过滤投运时间 <= 当前月末的站点
    df_in_service = DF_SCDD[DF_SCDD['commissioning_time'] <= month_end]
    # 计算总额定功率
    total_capacity = df_in_service['station_capacity'].sum()
    total_capacity = total_capacity / 10000
    total_capacity = total_capacity.round(2)
    total_capacity

    # ### 投资情况维度

    # #### 累计投资

    # In[215]:

    DF_SCDD_investment['investment_amount'] = pd.to_numeric(
        DF_SCDD_investment['investment_amount'], errors='coerce'
    )

    total_investment = DF_SCDD_investment['investment_amount'].sum()

    total_investment = round(total_investment, 2)
    total_investment

    # #### 年度投资

    # In[216]:

    # 筛选投运年份为当前年的记录
    df_year = DF_SCDD_investment[DF_SCDD_investment['commissioning_time'].dt.year == year]

    # 求和
    annual_investment = df_year['investment_amount'].sum()

    # annual_investment = annual_investment / 10000
    annual_investment = round(annual_investment, 2)
    annual_investment

    # #### 回本站点

    # In[217]:

    hbzdgs

    # In[ ]:

    # ### 运营情况维度

    # #### 日均充电量

    # In[218]:

    thismonth_dqrjcdl = df_avg_gun_volume.loc[df_avg_gun_volume['month'] == M, '单枪日均充电量'].mean()

    # In[219]:

    # lastmonth_dqrjcdl = df_avg_gun_volume.loc[df_avg_gun_volume['month'] == previous_month_str, '单枪日均充电量'].mean()

    # In[ ]:

    # #### 功率利用率

    # In[220]:

    thismonth_pue = monthly_util.loc[monthly_util['month'] == M, 'pue'].mean()

    # In[221]:

    thismonth_pue = thismonth_pue.round(2)

    # In[222]:

    lastmonth_pue = monthly_util.loc[monthly_util['month'] == previous_month_str, 'pue'].mean()

    # In[223]:

    lastmonth_pue = lastmonth_pue.round(2)

    # In[224]:

    if thismonth_pue >= lastmonth_pue:
        q1 = "本月功率利用率环比上升，运营效率稳步提升"
    else:
        q1 = "本月功率利用率环比下降，运营效率有所退步"

    # ### 设备质量维度

    # #### 一次成功率

    # In[225]:

    thismonth_yicichenggong = monthly_success_rate.loc[
        monthly_success_rate['month'] == M, 'station_success_rate'].mean()

    # In[226]:

    thismonth_yicichenggong = round(thismonth_yicichenggong, 2)

    # In[227]:

    lastmonth_yicichenggong = monthly_success_rate.loc[
        monthly_success_rate['month'] == previous_month_str, 'station_success_rate'].mean()

    # In[228]:

    lastmonth_yicichenggong = round(lastmonth_yicichenggong, 2)

    # In[229]:

    if (thismonth_yicichenggong >= lastmonth_yicichenggong):
        q2 = "本月一次成功率环比上升，设备可靠性稳步提升"
    else:
        q2 = "本月一次成功率环比下降，设备可靠性退步"

    # #### 可用率

    # In[230]:

    thismonth_kyl_re = cuse_rate_chart.loc[cuse_rate_chart['month'] == M, '可用率'].mean()

    # In[231]:

    thismonth_kyl_re = round(thismonth_kyl_re, 2)

    # ### 经营情况维度

    # #### 本月营收

    # In[232]:

    thismonth_rec = monthly_revenue.loc[monthly_revenue['cba_month'] == M, 'rec_data'].sum()

    # In[233]:

    thismonth_rec = round(thismonth_rec, 2)

    # #### 毛利

    # In[234]:

    thismonth_maoli = df_profit_diff.loc[df_profit_diff['cba_month'] == M, 'gross_profit'].sum()

    # In[235]:

    thismonth_maoli = round(thismonth_maoli, 2)

    # In[236]:

    lastmonth_maoli = df_profit_diff.loc[df_profit_diff['cba_month'] == previous_month_str, 'gross_profit'].sum()

    # In[237]:

    lastmonth_maoli = round(lastmonth_maoli, 2)

    # In[238]:

    if (thismonth_maoli > lastmonth_maoli):
        q3 = "本月毛利环比上升，经济效益向好发展"
    else:

        q3 = "本月毛利环比下降，经济效益退步"

    # ### 运营情况维度

    # #### 工单

    # In[239]:

    thismonth_workorders = monthly_workorders.loc[monthly_workorders['stat_time'] == M, '单桩工单'].mean()

    # In[240]:

    thismonth_workorders = round(thismonth_workorders, 2)

    # In[241]:

    lastmonth_workorders = monthly_workorders.loc[
        monthly_workorders['stat_time'] == previous_month_str, '单桩工单'].mean()

    # In[242]:

    lastmonth_workorders

    # In[243]:

    if thismonth_workorders > lastmonth_workorders:
        q4 = "本月单桩工单数量环比上升，运维压力有所增加"
    else:
        q4 = "本月单桩工单数量环比下降，运维压力有所缓解"

    # ### 写入数据库

    # In[244]:
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
            cs.merchant_nature = "电动公司"
            and  cs.operation_status in ('投运','停运')) a
            left join 
            (select * from station_cba_org_data where cba_month like '%s' or  cba_month like '%s' ) b
            on a.station_no =b.station_no
            """ % (t1, t2)
    DF_org_data_pre_gun = SQL(sql)

    DF_org_data_pre_gun = DF_org_data_pre_gun.fillna(0)
    DF_org_data_pre_gun['charge_point_count'] = DF_org_data_pre_gun['dc_charge_point_count'].fillna(0) + \
                                                DF_org_data_pre_gun[
                                                    'ac_charge_point_count'].fillna(0)

    DF_org_data_pre_gun = DF_org_data_pre_gun[DF_org_data_pre_gun['charge_point_count'] != 0]
    DF_org_data_pre_gun = DF_org_data_pre_gun[DF_org_data_pre_gun['plat_data_charging_volume'] != 0]  # 平台数据-平台充电量,不等于0
    # 当月单枪充电量，日均的计算在后面
    DF_org_data_pre_gun['gun_charging_volume'] = DF_org_data_pre_gun['plat_data_charging_volume'] / DF_org_data_pre_gun[
        'charge_point_count']

    print("DF_org_data_pre_gun的列名:\n", DF_org_data_pre_gun.columns)
    # ### 本月数据
    d1_1 = DF_org_data_pre_gun[DF_org_data_pre_gun['cba_month'] == M].copy()
    d1_1['gun_charging_volume_d'] = d1_1['gun_charging_volume'] / get_days_in_month(M)
    dqrjcdl_bysj = d1_1['gun_charging_volume_d'].mean()
    print('单枪日均充电量本月数据：', dqrjcdl_bysj)
    # ### 本月数据

    pue_value_1 = DF_cba_pue[DF_cba_pue['cba_month'] == M]['pue'].mean()
    pue_value = f"{pue_value_1:.2f}"
    pue_value = float(pue_value)

    print('功率利用率本月数据：', pue_value)
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
    cs.merchant_nature = "电动公司"
    and cs.operation_status in ('投运','停运')
    ) a
    left join 
    (select * from station_cba_org_data where cba_month like '%s' or  cba_month like '%s' ) b
    on a.station_no =b.station_no
    """ % (t1, t2)
    DF_cba_org_data = SQL(sql)
    DF_cba_org_data = DF_cba_org_data.fillna(0)
    # 数据类型转换
    DF_cba_org_data['rec_data_elec_fee_revenue'] = DF_cba_org_data['rec_data_elec_fee_revenue'].astype(str).astype(
        float)
    DF_cba_org_data['rec_data_service_fee_revenue'] = DF_cba_org_data['rec_data_service_fee_revenue'].astype(
        str).astype(
        float)
    DF_cba_org_data['other_revenue_battery_swap_services'] = DF_cba_org_data[
        'other_revenue_battery_swap_services'].astype(
        str).astype(float)
    DF_cba_org_data['other_revenue_access_control_barriers'] = DF_cba_org_data[
        'other_revenue_access_control_barriers'].astype(str).astype(float)
    DF_cba_org_data['other_revenue_dr'] = DF_cba_org_data['other_revenue_dr'].astype(str).astype(float)

    DF_cba_org_data['rec_cost_elec_fee'] = DF_cba_org_data['rec_cost_elec_fee'].astype(str).astype(float)
    DF_cba_org_data['rec_cost_actual_rec_amount'] = DF_cba_org_data['rec_cost_actual_rec_amount'].astype(str).astype(
        float)
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
          where cs.merchant_nature = "电动公司"
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
    cs.merchant_nature = "电动公司"
    and cs.operation_status in ('投运','停运')
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
    DF_cba_org_data = pd.merge(DF_cba_org_data, DF_rent[['station_no', 'parking_fee']], how='left',
                               on='station_no').fillna(
        0)

    DF_cba_org_data['parking_fee'] = DF_cba_org_data['parking_fee'].astype('float')
    DF_cba_org_data['rec_cost'] = DF_cba_org_data['rec_cost'] + DF_cba_org_data['parking_fee']
    DF_cba_org_data.head(1)

    DF_cba_org_data['gross_profit'] = DF_cba_org_data['rec_data'] - DF_cba_org_data['rec_cost']
    DF_cba_org_data['rec_data'] = DF_cba_org_data['rec_data'].astype(float)
    DF_cba_org_data['rec_cost'] = DF_cba_org_data['rec_cost'].astype(float)
    DF_cba_org_data['gross_profit'] = DF_cba_org_data['gross_profit'].astype(float)
    DF_Business_Analysis = DF_cba_org_data.copy()

    benyueshouyi = DF_cba_org_data[DF_cba_org_data['cba_month'] == M][['rec_data']].sum().sum()
    benyueshouyi = f'{benyueshouyi / 10000:.2f}'

    print('本月收益：', benyueshouyi)

    benyuemaoli = DF_cba_org_data[DF_cba_org_data['cba_month'] == M][['gross_profit']].sum().sum()
    benyuemaoli = f'{benyuemaoli / 10000:.2f}'

    print('本月毛利：', benyuemaoli)
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

    DF_operation_duration_1 = DF_operation_duration.groupby(['time', 'station_no']).agg(
        {'可用率': 'mean'}).reset_index()
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

    keyonglv_benyue = DF_operation_duration[DF_operation_duration['month'] == M]['可用率'].mean()
    keyonglv_benyue = f"{keyonglv_benyue * 100:.2f}"
    print('可用率本月数据：', keyonglv_benyue)

    infrastructure = [
        {
            "title": "建设情况",
            "content": [
                {"name": "累计充电枪保有量", "value": int(total_guns), "unit": '把'},
                {"name": "累计总额定功率", "value": float(total_capacity), "unit": '万kW'}
            ],
            "trend": "枪数与功率均稳步增长，充电基础设施持续扩容"
        },
        {
            "title": "投资情况",
            "content": [
                {"name": "累计投资", "value": float(total_investment), "unit": '万元'},
                {"name": "本年投资", "value": float(annual_investment), "unit": '万元'},

            ],
            "trend": "已有{}座站点回本，回本步伐稳健推进".format(int(hbzdgs))
        },
        {
            "title": "运营情况",  # float(f"{pue_value:.2f}")
            "content": [
                {"name": "本月单枪日均充电量", "value": round(dqrjcdl_bysj, 2), "unit": 'kWh'},
                {"name": "本月功率利用率均值为", "value": pue_value, "unit": '%'}
            ],
            "trend": q1
        },
        {
            "title": "经营情况",
            "content": [
                {"name": "本月营收", "value": float(benyueshouyi), "unit": '万元'},
                {"name": "本月毛利", "value": float(benyuemaoli), "unit": '万元'}
            ],
            "trend": q3
        },
        {
            "title": "设备质量",
            "content": [
                {"name": "本月充电枪一次成功率均值为", "value": float(thismonth_yicichenggong), "unit": '%'},
                {"name": "本月充电枪可用率均值为", "value": float(keyonglv_benyue), "unit": '%'}
            ],
            "trend": q2
        },
        {
            "title": "运维情况",
            "content": [
                {"name": "本月单桩工单数量", "value": float(thismonth_workorders), "unit": '单'}
            ],
            "trend": q4
        }
    ]

    # 表和字段注释
    table_comment = "类型检测_首页_四川电动旗下基础设施建设现状"
    column_comments = {
        'infrastructure': '四川电动旗下基础设施建设现状',
        'update_time': '更新日期'
    }
    DF_scdd_Infrastructure = pd.DataFrame([{
        'infrastructure': infrastructure,
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF_scdd_Infrastructure,
        table_name="dp_scdd_Infrastructure",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )
