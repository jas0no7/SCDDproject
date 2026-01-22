from logs.log_decorator import log_execution
from loguru import logger
import  re
from modules.config import SQL,import_data_with_cursor,Statistical_Time

@log_execution
def runpanoramaOverview():
    logger.info(f"开始执行全景概览页面")
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
    import re
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)



    def bar_chart(df ,axis ,YxisName ,m):
        axisData = df[axis].tolist()
        chartData = [df[col].tolist() for col in [i for  i  in df.columns if  axis not in i]]
        YxisName = YxisName
        legendName = [i for  i  in df.columns if  axis not in i]
        L = [axisData ,chartData ,YxisName ,legendName]
        print(L)
        DF = pd.DataFrame(columns=['axisData' ,'chartData' ,'YxisName' ,'legendName'] ,data = [L])
        DF['month'] = m
        return DF




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


    # ## 获取当月天数

    # In[10]:


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


    # In[11]:


    get_days_in_month(M)


    # ## sql分区筛选

    # In[12]:


    def get_months_in_year(month_str):
        """获取指定月份及其当年之前的所有月份，返回元组格式"""
        year = int(month_str[:4])
        month = int(month_str[4:])

        # 生成从1月到指定月份的所有月份，并转换为元组
        months = tuple(int(f"{year}{m:02d}") for m in range(1, month + 1))

        placeholders = ", ".join([f"p{p}" for p in months])

        return placeholders


    # In[13]:


    # 区间筛选
    result = get_months_in_year(M)
    result

    # ## 月份筛选数据码表

    # In[14]:


    # 前端会获取最后一行


    # In[15]:


    M_data = pd.DataFrame({'month': [M]})
    M_data

    # In[16]:


    # 定义注释
    table_comment = "大屏展示数据对应年月筛选条件"
    column_comments = {
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=M_data,
        table_name="M_data",
        table_comment=table_comment,
        primary_keys=['month'],
        column_comments=column_comments
    )

    # # 核心监测指标

    # ## 公司充电枪规模

    # ### 初始数据读取

    # In[17]:


    sql = """
    SELECT 
    rm.merchant_name,
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and cs.operation_status in ('投运')
    """
    DF_SCDD = SQL(sql)

    # In[18]:


    # 枪数量合并
    DF_SCDD['charge_point_count'] = DF_SCDD['dc_charge_point_count'].fillna(0) + DF_SCDD['ac_charge_point_count'].fillna(0)

    # In[19]:


    # 处理投运时间字段，提取投运年份、年月
    DF_SCDD['year'] = DF_SCDD['commissioning_time'].dt.year
    DF_SCDD['year_month'] = DF_SCDD['commissioning_time'].dt.strftime('%Y%m')

    # In[20]:


    print('当前四川电动投运状态中的充电站数量：', DF_SCDD.shape[0])

    # ### 本年新增

    # In[21]:


    data1 = []

    # In[22]:


    d1 = DF_SCDD[(DF_SCDD['year'] == year) & (DF_SCDD['year_month'] <= M)]['charge_point_count'].sum()
    data1.append(d1)
    data1

    # ### 同比增长

    # In[23]:


    # 计算截至到上年同月的新增枪数量
    d2_1 = DF_SCDD[(DF_SCDD['year_month'] <= last_year_month_str) & (DF_SCDD['year'] == last_year)]['charge_point_count'].sum()
    print('上年新增枪数量：', d2_1)
    # 计算同比增长
    d2 = f"{(d1 / d2_1 - 1) * 100:.2f}"
    data1.append(d2)
    data1

    # ### 累计建设

    # In[24]:


    d3 = DF_SCDD[DF_SCDD['year_month'] <= M]['charge_point_count'].sum()
    data1.append(d3)
    data1

    # ### 同比增长

    # In[25]:


    d4_1 = DF_SCDD[DF_SCDD['year_month'] <= last_year_month_str]['charge_point_count'].sum()
    d4 = f"{(d3 / d4_1 - 1) * 100:.2f}"
    data1.append(d4)
    data1

    # ### 新增枪数TOP1站类型

    # In[26]:


    d5 = DF_SCDD[(DF_SCDD['year'] == year) & (DF_SCDD['year_month'] <= M)].groupby('station_category').agg({'charge_point_count': 'sum'}).reset_index().sort_values(by='charge_point_count', ascending=False).iloc[0]['station_category']
    data1.append(d5)
    data1

    # ### 新增枪数TOP1城市

    # In[27]:


    d6 = DF_SCDD[(DF_SCDD['year'] == year) & (DF_SCDD['year_month'] <= M)].groupby('city').agg({'charge_point_count': 'sum'}).reset_index().sort_values(by='charge_point_count', ascending=False).iloc[0]['city']
    data1.append(d6)
    data1

    # ### 统计图数据

    # In[28]:


    d7 = DF_SCDD[DF_SCDD['year_month'] <= M].groupby('year').agg({'charge_point_count': 'sum'}).reset_index().sort_values(by='year', ascending=False).head(5)
    d7['year'] = [str(int(i)) + '年' for i in d7['year']]
    d7.rename(columns={'charge_point_count': '公司新增充电枪数量'}, inplace=True)
    d7 = d7.sort_values(by='year', ascending=True)
    d7

    #  整合表格

    # In[29]:


    DF1 = pd.DataFrame(
        columns=['annual_new', 'yoy_growth_1', 'total_built', 'yoy_growth_2', 'top1_type', 'top1_city'],
        data=[data1]
    )

    # In[30]:


    DF2 = bar_chart(d7, 'year', '个', M)

    # In[31]:


    DF = pd.concat([DF1, DF2], axis=1)
    DF

    # In[32]:


    # 定义注释
    table_comment = "公司全景_核心监测指标_公司充电枪规模"
    column_comments = {
        'annual_new': '本年新增',
        'yoy_growth_1': '同比增长',
        'total_built': '累计建设',
        'yoy_growth_2': '同比增长',
        'top1_type': '新增枪数TOP1站类型',
        'top1_city': '新增枪数TOP1城市',
        'chart_data': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'chart_data': '统计图数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_company_core_gun",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 公司经营情况

    # ### 初始数据读取

    # In[33]:


    t1 = str(last_year) + '%'  # 生成sql中的上年筛选条件
    t2 = str(year) + '%'  # 生成sql中的上年筛选条件

    # In[34]:


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
    DF_cba_org_data['rec_data_service_fee_revenue'] = DF_cba_org_data['rec_data_service_fee_revenue'].astype(str).astype(float)
    DF_cba_org_data['other_revenue_battery_swap_services'] = DF_cba_org_data['other_revenue_battery_swap_services'].astype(str).astype(float)
    DF_cba_org_data['other_revenue_access_control_barriers'] = DF_cba_org_data['other_revenue_access_control_barriers'].astype(str).astype(float)
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

    # In[35]:


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

    # In[36]:


    # 3、租金
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
    DF_rent

    # In[37]:


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
    fin_rec_result_detail.head(1)

    # ### 数据处理合并

    # In[38]:


    # 1、分成数据与运营数据合并

    # 预处理填充空值
    fin_rec_result_detail = fin_rec_result_detail.fillna(0)

    # merchant_profit_amount为其他商户分成（成本数据）
    fin_rec_result_detail = fin_rec_result_detail[['rec_month', 'station_no', 'merchant_profit_amount']]

    # 更换列名便于匹配
    fin_rec_result_detail = fin_rec_result_detail.rename(columns={'rec_month': 'cba_month'})

    # 按年月汇总每个站点的分成数据
    fin_rec_result_detail = fin_rec_result_detail.groupby(['cba_month', 'station_no']).agg({'merchant_profit_amount': 'sum'}).reset_index()

    # 根据站点编号、年月关联分成数据，与运营数据
    print('cba表关联分成数据前形状：', DF_cba_org_data.shape)
    DF_cba_org_data = pd.merge(DF_cba_org_data, fin_rec_result_detail, on=['station_no', 'cba_month'], how='left')
    DF_cba_org_data = DF_cba_org_data.fillna(0)
    print('cba表关联分成数据后形状：', DF_cba_org_data.shape)

    # In[39]:


    # 2、运营数据与运维费合并
    print('cba表关联运维费前形状：', DF_cba_org_data.shape)

    DF_cba_org_data['year'] = DF_cba_org_data['cba_month'].apply(
        lambda x: str(x)[:4] if pd.notnull(x) and len(str(x)) >= 4 else None
    )

    DF_cba_org_data = pd.merge(DF_cba_org_data, DF_maintenance, on=['station_no', 'cba_month'], how='left')
    DF_cba_org_data['maintenance_cost'] = DF_cba_org_data['maintenance_cost'].fillna(0)
    print('cba表关联运维费后形状：', DF_cba_org_data.shape)

    # In[40]:


    DF_cba_org_data.info()

    # In[41]:


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

    # In[42]:


    DF_cba_org_data['parking_fee'] = DF_cba_org_data['parking_fee'].astype('float')
    DF_cba_org_data['rec_cost'] = DF_cba_org_data['rec_cost'] + DF_cba_org_data['parking_fee']
    DF_cba_org_data.head(1)

    # In[43]:


    DF_Business_Analysis = DF_cba_org_data.copy()

    # In[44]:


    DF_Business_Analysis.columns

    # In[533]:


    # #收入字段：没有加cba里的补贴数据，也没有加补贴表中的补贴数据
    # rec_data_elec_fee_revenue：清分数据_清分电费收入
    # rec_data_service_fee_revenue:清分数据_清分服务费收入
    # other_revenue_battery_swap_services:其它收入_换电服务费
    # other_revenue_access_control_barriers:其它收入_道闸
    # other_revenue_dr:其它收入_需求响应

    # 成本字段：运营成本+运维费+分成数据，没有加初始投资金额，不加清分成本清分费，也不加清分成本平台服务费
    # rec_cost_elec_fee:清分成本_用电电费
    # rec_cost_actual_rec_amount：清分成本_清分费(实际清分金额) #不加
    # rec_cost_plat_service：清分成本_平台服务费 #不加
    # rec_cost_rent：清分成本_租金
    # om_cost_om：运维成本_运维费
    # om_cost_spare_parts：运维成本_备件费用
    # om_cost_op_project：运维成本_运维项目
    # fin_cost_depreciation：财务成本_折旧
    # fin_cost_labor：财务成本_人工

    # merchant_profit_amount：分成数据
    # maintenance_cost：运维费


    # In[534]:


    data2 = []

    # ### 本月收益

    # In[535]:


    d1 = DF_cba_org_data[DF_cba_org_data['cba_month'] == M][['rec_data']].sum().sum()
    d1
    data2.append(f"{d1 / 10000:.2f}")
    data2

    # ### 同比增长

    # In[536]:


    d2_1 = DF_cba_org_data[DF_cba_org_data['cba_month'] == last_year_month_str][['rec_data']].sum().sum()
    d2 = f"{(d1 / d2_1 - 1) * 100:.2f}"
    data2.append(d2)
    data2

    # ### 环比增长

    # In[537]:


    d3_1 = DF_cba_org_data[DF_cba_org_data['cba_month'] == previous_month_str][['rec_data']].sum().sum()
    d3 = f"{(d1 / d3_1 - 1) * 100:.2f}"
    data2.append(d3)
    data2

    # ### 本年收益

    # In[538]:

    DF_cba_org_data['cba_month'] = DF_cba_org_data['cba_month'].astype(str)
    M = str(M)
    d4 = DF_cba_org_data[(DF_cba_org_data['cba_month'] <= M) & (DF_cba_org_data['year'] == str(year))][['rec_data']].sum().sum()
    data2.append(f"{d4 / 10000:.2f}")
    data2

    # ### 同比增长

    # In[539]:


    d5_1 = DF_cba_org_data[(DF_cba_org_data['cba_month'] <= last_year_month_str) & (DF_cba_org_data['year'] == str(last_year))][['rec_data']].sum().sum()
    d5 = f"{(d4 / d5_1 - 1) * 100:.2f}"
    data2.append(d5)
    data2

    # ### 收益TOP1站点类型

    # In[540]:


    d6 = DF_cba_org_data[DF_cba_org_data['cba_month'] == M].groupby('station_category').agg({'rec_data': 'sum'}).reset_index().sort_values(by='rec_data', ascending=False).iloc[0]['station_category']
    data2.append(d6)
    data2

    # ### 收益TOP1地级市

    # In[541]:


    d7 = DF_cba_org_data[DF_cba_org_data['cba_month'] == M].groupby('city').agg({'rec_data': 'sum'}).reset_index().sort_values(by='rec_data', ascending=False).iloc[0]['city']
    data2.append(d7)
    data2

    # In[542]:


    DF1 = pd.DataFrame(columns=['month_revenue', 'yoy_growth_1', 'mom_growth', 'year_revenue', 'yoy_growth_2', 'top1_type', 'top1_city'], data=[data2])

    # In[543]:


    DF1

    # ### 统计图数据

    # In[544]:


    Data

    # In[545]:


    # 统计每个年月对应的运营收入和成本
    d8 = DF_cba_org_data.groupby('cba_month').agg({'rec_data': 'sum', 'rec_cost': 'sum'}).reset_index()

    # 将单位转换为万元
    d8['rec_data'] = d8['rec_data'] / 10000
    d8['rec_cost'] = d8['rec_cost'] / 10000

    d8 = pd.merge(Data, d8, left_on='month', right_on='cba_month', how='left')
    d8 = d8[['month', 'rec_data', 'rec_cost']]
    d8 = d8.rename(columns={'rec_data': '公司经济收入', 'rec_cost': '公司总成本'})

    d8['公司经济收入'] = d8['公司经济收入'].astype('float').round(2)
    d8['公司总成本'] = d8['公司总成本'].astype('float').round(2)

    d8 = d8.sort_values(by='month', ascending=True)
    d8

    # In[546]:


    DF2 = bar_chart(d8, 'month', '万元', M)

    # In[547]:


    DF = pd.concat([DF1, DF2], axis=1)
    DF

    # In[548]:


    # 定义注释
    table_comment = "公司全景_核心监测指标_公司经济收益"
    column_comments = {
        'month_revenue': '本月收益',
        'yoy_growth_1': '同比增长',
        'mom_growth': '环比增长',
        'year_revenue': '本年收益',
        'yoy_growth_2': '同比增长',
        'top1_type': '收益TOP1站类型',
        'top1_city': '收益TOP1城市',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'chart_data': '统计图数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_company_revenue",
        table_comment=table_comment,
        primary_keys=['month'],
        column_comments=column_comments

    )

    # ## 公司设备可用率

    # In[549]:


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

    # In[550]:


    DF_operation_duration = DF_operation_duration.fillna(0)

    # 可用率计算

    # In[551]:


    # 可用率=正常状态时长(秒)/在运时长(秒)
    DF_operation_duration['可用率'] = DF_operation_duration['normal_duration'].astype('int') / DF_operation_duration['operation_duration'].astype('int')

    # 筛选正常桩

    # In[552]:


    DF_operation_duration.head(1)

    # In[553]:


    print('筛选运行状态前数据形状：', DF_operation_duration.shape)
    DF_operation_duration = DF_operation_duration[DF_operation_duration['pile_status'] == '运行']
    print('筛选运行状态后数据形状', DF_operation_duration.shape)

    # 计算每个站每月平均可用率

    # In[554]:


    DF_operation_duration_1 = DF_operation_duration.groupby(['time', 'station_no']).agg({'可用率': 'mean'}).reset_index()
    DF_operation_duration_1

    # In[555]:


    # 获取站点对应城市、站点类型的标签
    DF_operation_duration_2 = DF_operation_duration[['station_no', 'station_category', 'city']].drop_duplicates()
    DF_operation_duration_2

    # In[556]:


    DF_operation_duration = pd.merge(DF_operation_duration_1, DF_operation_duration_2, on='station_no', how='left')
    DF_operation_duration.head(1)

    # 处理时间

    # In[557]:


    DF_operation_duration['month'] = [i[:6] for i in DF_operation_duration['time']]

    # In[558]:


    DF_operation_duration['year'] = [i[:4] for i in DF_operation_duration['month']]

    # In[559]:


    data4 = []

    # ### 本月数据

    # In[560]:


    d1 = DF_operation_duration[DF_operation_duration['month'] == M]['可用率'].mean()
    data4.append(f"{d1 * 100:.2f}")
    data4

    # ### 同比增长

    # In[561]:


    d2_1 = DF_operation_duration[DF_operation_duration['month'] == last_year_month_str]['可用率'].mean()
    d2 = f'{(d1 / d2_1 - 1) * 100:.2f}'
    data4.append(d2)
    data4

    # ### 环比增长

    # In[562]:


    d3_1 = DF_operation_duration[DF_operation_duration['month'] == previous_month_str]['可用率'].mean()
    d3 = f'{(d1 / d3_1 - 1) * 100:.2f}'
    data4.append(d3)
    data4

    # ### 本年数据

    # In[563]:


    d4 = DF_operation_duration[(DF_operation_duration['month'] <= M) & (DF_operation_duration['year'] == str(year))]['可用率'].mean()
    data4.append(f"{d4 * 100:.2f}")
    data4

    # ### 同比增长

    # In[564]:


    d5_1 = DF_operation_duration[(DF_operation_duration['month'] <= last_year_month_str) & (DF_operation_duration['year'] == str(last_year))]['可用率'].mean()
    d5 = f"{(d4 / d5_1 - 1) * 100:.2f}"
    data4.append(d5)
    data4

    # ### 可用率TOP1站类型

    # In[565]:


    DF_operation_duration['month'] = DF_operation_duration['month'].astype('str')
    d6 = DF_operation_duration[DF_operation_duration['month'] == M].groupby('station_category').agg({'可用率': 'mean'}).reset_index().sort_values(by='可用率', ascending=False).iloc[0]['station_category']
    data4.append(d6)
    data4

    # ### 可用率TOP1地级市

    # In[566]:


    d7 = DF_operation_duration[DF_operation_duration['month'] == M].groupby('city').agg({'可用率': 'mean'}).reset_index().sort_values(by='可用率', ascending=False).iloc[0]['city']
    data4.append(d7)
    data4

    # In[567]:


    DF1 = pd.DataFrame(columns=['month_data', 'yoy_growth_1', 'mom_growth', 'year_data', 'yoy_growth_2', 'top1_type',
                                'top1_city'], data=[data4])

    # ### 统计图数据

    # In[568]:


    d8_1 = DF_operation_duration.groupby('month').agg({'可用率': 'mean'}).reset_index()
    d8 = pd.merge(Data, d8_1, on='month', how='left')

    # In[569]:


    d8['可用率'] = (d8['可用率'] * 100).round(2)

    # In[570]:


    d8 = d8.sort_values(by='month', ascending=True)

    # In[571]:


    DF2 = bar_chart(d8, 'month', '%', M)

    # 生成数据表

    # In[572]:


    DF = pd.concat([DF1, DF2], axis=1)

    # 上传数据库

    # In[573]:


    DF

    # In[574]:


    # 定义注释
    table_comment = "公司全景_核心监测指标_公司设备可用率"
    column_comments = {
        'month_acc': '本月数据',
        'yoy_growth_1': '同比增长',
        'mom_growth': '环比增长',
        'year_acc': '本年数据',
        'yoy_growth_2': '同比增长',
        'top1_type': '接入规模TOP1站类型',
        'top1_city': '接入规模TOP1城市',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名字',
        'axisData': '横坐标数据',
        'chart_data': '统计图数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_company_operation_duration",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 公司单枪日均充电量

    # In[575]:


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
    DF_cba_org_data = DF_cba_org_data.fillna(0)

    # In[576]:


    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
    select * from dp_province
    where stat_time like '%s' or stat_time like '%s'
    """ % (t1, t2)
    DF_province = SQL(sql)
    DF_province['avg_daily_energy'] = DF_province['avg_daily_energy'].astype('float').round(2)

    # In[577]:


    DF_province

    # In[578]:


    DF_cba_org_data['charge_point_count'] = DF_cba_org_data['dc_charge_point_count'].fillna(0) + DF_cba_org_data['ac_charge_point_count'].fillna(0)

    # In[579]:


    print('筛选前：', DF_cba_org_data.shape)
    DF_cba_org_data = DF_cba_org_data[DF_cba_org_data['charge_point_count'] != 0]
    DF_cba_org_data = DF_cba_org_data[DF_cba_org_data['plat_data_charging_volume'] != 0]  # 平台数据-平台充电量,不等于0
    print('筛选后：', DF_cba_org_data.shape)

    # In[580]:


    # 当月单枪充电量，日均的计算在后面
    DF_cba_org_data['gun_charging_volume'] = DF_cba_org_data['plat_data_charging_volume'] / DF_cba_org_data['charge_point_count']

    # In[581]:


    DF_cba_org_data.head(1)

    # In[582]:


    data5 = []

    # ### 本月数据

    # In[583]:


    d1_1 = DF_cba_org_data[DF_cba_org_data['cba_month'] == M].copy()
    d1_1['gun_charging_volume_d'] = d1_1['gun_charging_volume'] / get_days_in_month(M)
    d1 = d1_1['gun_charging_volume_d'].mean()
    data5.append(round(d1, 2))
    data5

    # ### 同比增长

    # In[584]:


    d2_1 = DF_cba_org_data[DF_cba_org_data['cba_month'] == last_year_month_str].copy()
    d2_1['gun_charging_volume_d'] = d2_1['gun_charging_volume'] / get_days_in_month(last_year_month_str)
    d2_1 = d2_1['gun_charging_volume_d'].mean()
    d2 = f"{(d1 / d2_1 - 1) * 100:.2f}"
    data5.append(d2)
    data5

    # ### 环比增长

    # In[585]:


    d3_1 = DF_cba_org_data[DF_cba_org_data['cba_month'] == previous_month_str].copy()
    d3_1['gun_charging_volume_d'] = d3_1['gun_charging_volume'] / get_days_in_month(previous_month_str)
    d3_1 = d3_1['gun_charging_volume_d'].mean()
    d3 = f"{(d1 / d3_1 - 1) * 100:.2f}"
    data5.append(d3)
    data5

    # ### 本年数据

    # In[586]:


    d4_1 = DF_cba_org_data[(DF_cba_org_data['cba_month'].str[:4] == str(year)) & (DF_cba_org_data['cba_month'] <= M)].groupby('cba_month').agg({"gun_charging_volume": 'mean'}).reset_index().copy()
    d4_1['day'] = [get_days_in_month(i) for i in d4_1['cba_month']]
    d4_1['gun_charging_volume_d'] = d4_1['gun_charging_volume'] / d4_1['day']
    d4 = d4_1['gun_charging_volume_d'].mean()
    data5.append(round(d4, 2))
    data5

    # ### 同比增长

    # In[587]:


    d5_1 = DF_cba_org_data[(DF_cba_org_data['cba_month'].str[:4] == str(last_year)) & (DF_cba_org_data['cba_month'] <= last_year_month_str)].groupby('cba_month').agg({"gun_charging_volume": 'mean'}).reset_index().copy()
    d5_1['day'] = [get_days_in_month(i) for i in d5_1['cba_month']]
    d5_1['gun_charging_volume_d'] = d5_1['gun_charging_volume'] / d5_1['day']
    d5_1 = d5_1['gun_charging_volume_d'].mean()
    d5 = f'{(d4 / d5_1 - 1) * 100:.2f}'
    data5.append(d5)
    data5

    # ### 全省平均水平

    # In[588]:


    d6 = DF_province[DF_province['stat_time'] == M]['avg_daily_energy'].values[0]
    data5.append(d6)
    data5

    # ### 单枪充电量TOP1站类型

    # In[589]:


    d7 = d1_1[d1_1['cba_month'] == M].groupby('station_category').agg({'gun_charging_volume_d': 'mean'}).reset_index().sort_values(by='gun_charging_volume_d', ascending=False).iloc[0]['station_category']
    data5.append(d7)
    data5

    # ### 单枪充电量TOP1地级市

    # In[590]:


    d8 = d1_1.groupby('city').agg({'gun_charging_volume_d': 'mean'}).reset_index().sort_values(by='gun_charging_volume_d', ascending=False).iloc[0]['city']
    data5.append(d8)
    data5

    # ### 统计图数据

    # In[591]:


    d9_1 = DF_cba_org_data.groupby('cba_month').agg({'gun_charging_volume': 'mean'}).reset_index()
    d9_1['day'] = [get_days_in_month(i) for i in d9_1['cba_month']]
    d9_1['gun_charging_volume_d'] = d9_1['gun_charging_volume'] / d9_1['day']
    d9 = pd.merge(Data, d9_1, left_on='month', right_on='cba_month', how='left')[['month', 'gun_charging_volume_d']]
    d9 = pd.merge(d9, DF_province[['stat_time', 'avg_daily_energy']], left_on='month', right_on='stat_time', how='left')[['month', 'gun_charging_volume_d', 'avg_daily_energy']]
    d9.rename(columns={'gun_charging_volume_d': '公司单枪日均充电量', 'avg_daily_energy': '全省平均水平'}, inplace=True)
    d9['公司单枪日均充电量'] = d9['公司单枪日均充电量'].round(2)
    d9['全省平均水平'] = d9['全省平均水平'].astype('float')
    d9['全省平均水平'] = d9['全省平均水平'].round(2)

    # In[592]:


    d9 = d9.sort_values(by='month', ascending=True)

    # In[593]:


    DF2 = bar_chart(d9, 'month', 'kWh', M)

    # 生成数据表

    # In[594]:


    DF1 = pd.DataFrame(columns=['month_data', 'yoy_growth_1', 'mom_growth', 'year_data', 'yoy_growth_2',
                                'prov_mean',
                                'top1_type', 'top1_city'],
                       data=[data5])
    DF2 = bar_chart(d9, 'month', 'kWh', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF

    # In[595]:


    # 定义注释
    table_comment = "公司全景_核心监测指标_公司单枪日均充电量"
    column_comments = {
        'month_data': '本月数据',
        'yoy_growth_1': '同比增长',
        'mom_growth': '环比增长',
        'year_data': '本年数据',
        'yoy_growth_2': '同比增长',
        'prov_mean': '全省平均水平',
        'top1_type': '新增枪数TOP1站类型',
        'top1_city': '新增枪数TOP1城市',
        'YxisName': '纵坐标单位',
        'legendName': '线条名字',
        'axisData': '横坐标数据',
        'chartData': '统计图数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_gun_charging_volume",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 公司功率利用率

    # In[596]:


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

    # In[597]:


    t1 = str(last_year) + '%'
    t2 = str(year) + '%'
    sql = """
    select * from dp_province
    where stat_time like '%s' or stat_time like '%s'
    """ % (t1, t2)
    DF_province = SQL(sql)
    DF_province['avg_power_utilization'] = DF_province['avg_power_utilization'].astype('float')

    # In[598]:


    DF_province

    # In[599]:


    DF_cba_pue['days'] = DF_cba_pue['cba_month'].apply(get_days_in_month)

    # In[600]:


    DF_cba_pue['year'] = [i[:4] for i in DF_cba_pue['cba_month']]

    # In[601]:


    print('筛选前：', DF_cba_pue.shape)
    DF_cba_pue = DF_cba_pue[
        (DF_cba_pue['station_capacity'].notna()) &  # 剔除功率为空的异常值
        (DF_cba_pue['station_capacity'] > 0) &  # 剔除功率为0的异常值
        (DF_cba_pue['plat_data_charging_volume'].notna()) &  # 剔除为空的异常值
        (DF_cba_pue['plat_data_charging_volume'] != 0)  # 剔除平台电量为0的异常值
        ].copy()
    print('筛选后：', DF_cba_pue.shape)

    # In[602]:
    #=====20260122测试功率利用率计算方式不同带来的变化-新增开始1
    ceshi0122 = DF_cba_pue.groupby(by='cba_month',as_index=False).agg({'plat_data_charging_volume':'sum',
                                                                       'days':'sum',
                                                                       'station_capacity':'sum'})
    ceshi0122['pue'] = ceshi0122['plat_data_charging_volume'] / (ceshi0122['station_capacity'] * DF_cba_pue['days'] * 24)
    #=====20260122测试功率利用率计算方式不同带来的变化-新增结束1

    DF_cba_pue['pue'] = DF_cba_pue['plat_data_charging_volume'] / (DF_cba_pue['station_capacity'] * DF_cba_pue['days'] * 24)

    # In[603]:


    result_list = []

    # ### 本月数据

    # In[604]:
    #=====20260122测试功率利用率计算方式不同带来的变化-新增开始2
    # pue_value_1 = ceshi0122[ceshi0122['cba_month'] == M]['pue'].iloc[0]
    #pue_value = f"{pue_value_1 * 100:.2f}"
    # =====20260122测试功率利用率计算方式不同带来的变化-新增结束2（注意确认计算方法后下方两行要取消注释）


    pue_value_1 = DF_cba_pue[DF_cba_pue['cba_month'] == M]['pue'].mean()
    pue_value = f"{pue_value_1 * 100:.2f}"
    result_list.append(pue_value)
    result_list

    # ### 同比增长

    # In[605]:


    pue_last_year_1 = DF_cba_pue[DF_cba_pue['cba_month'] == last_year_month_str]['pue'].mean()
    pue_last_year = f"{(pue_value_1 / pue_last_year_1 - 1) * 100:.2f}"
    result_list.append(pue_last_year)
    result_list

    # ### 环比增长

    # In[606]:


    pue_prev_1 = DF_cba_pue[DF_cba_pue['cba_month'] == previous_month_str]['pue'].mean()
    pue_prev = f"{(pue_value_1 / pue_prev_1 - 1) * 100:.2f}"
    result_list.append(pue_prev)
    result_list

    # ### 本年数据

    # In[607]:


    pue_this_year_1 = DF_cba_pue[(DF_cba_pue['cba_month'] <= M) & (DF_cba_pue['year'] == str(year))]['pue'].mean()
    pue_this_year = f"{pue_this_year_1 * 100:.2f}"
    result_list.append(pue_this_year)
    result_list

    # ### 同比增长

    # In[608]:


    pue_last_year_1 = DF_cba_pue[(DF_cba_pue['cba_month'] <= last_year_month_str) & (DF_cba_pue['year'] == str(last_year))]['pue'].mean()
    pue_last_year = f"{(pue_this_year_1 / pue_last_year_1 - 1) * 100:.2f}"
    result_list.append(pue_last_year)
    result_list

    # ### 全省平均水平

    # In[609]:


    df_util = f"{float(DF_province[DF_province['stat_time'] == M]['avg_power_utilization'].values[0]) * 100:.2f}"
    result_list.append(df_util)
    result_list

    # ### 功率利用率top1站点类型

    # In[610]:


    top_station_category = DF_cba_pue[DF_cba_pue['cba_month'] == M].groupby('station_category').agg({'pue': 'mean'}).reset_index().sort_values(by='pue', ascending=False).iloc[0]['station_category']
    result_list.append(top_station_category)
    result_list

    # ### 功率利用率TOP1地级市

    # In[611]:


    top_station_city = DF_cba_pue[DF_cba_pue['cba_month'] == M].groupby('city').agg({'pue': 'mean'}).reset_index().sort_values(by='pue', ascending=False).iloc[0]['city']
    result_list.append(top_station_city)
    result_list

    # ### 统计图数据

    # In[612]:


    d1 = DF_cba_pue.groupby('cba_month').agg({'pue': 'mean'}).reset_index()

    # In[613]:


    d1 = pd.merge(Data, d1, left_on='month', right_on='cba_month', how='left')[['month', 'pue']]

    # In[614]:


    df = pd.merge(d1, DF_province, left_on='month', right_on='stat_time', how='left')[['month', 'pue', 'avg_power_utilization']]

    # In[615]:


    df['pue'] = [round(i, 2) for i in df['pue'] * 100]
    df['avg_power_utilization'] = [round(i, 2) for i in df['avg_power_utilization'].astype('float') * 100]

    # In[616]:


    df.rename(columns={'pue': '公司功率利用率', 'avg_power_utilization': '全省站点功率利用率平均水平'}, inplace=True)

    # In[617]:


    df = df.sort_values(by='month', ascending=True)

    # 生成数据表

    # In[618]:


    DF1 = pd.DataFrame(columns=['month_data', 'yoy_growth_1', 'mom_growth', 'year_data', 'yoy_growth_2', 'prov_mean', 'top1_type',
                                'top1_city']
                       , data=[result_list])

    # In[619]:


    DF2 = bar_chart(df, 'month', '%', M)

    # In[620]:


    DF = pd.concat([DF1, DF2], axis=1)
    DF

    # 上传数据库

    # In[621]:


    # 定义注释
    table_comment = "公司全景_核心监测指标_公司功率利用率"
    column_comments = {
        'month_data': '本月数据',
        'yoy_growth_1': '同比增长',
        'mom_growth': '环比增长',
        'year_data': '本年数据',
        'yoy_growth_2': '同比增长',
        'top1_type': '功率利用率TOP1站类型',
        'top1_city': '功率利用率TOP1城市',
        'prov_mean': '全省平均水平',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名字',
        'axisData': '横坐标数据',
        'chartData': '统计图数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_company_pue",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 公司分时段负荷统计

    # In[622]:


    # 获取自营站点当月充电量数据
    sql = f"""
    select * from 
    (select cs.station_no,cs.station_category,cs.city,cs.operation_status from 
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and  cs.operation_status in ('投运','退运')
    ) a 
    left join 
    (select charging_station_no,sum(peak_elec_cons) as peak_elec_cons ,
    sum(shoulder_elec_cons) as shoulder_elec_cons ,
    sum(flat_elec_cons) as flat_elec_cons,
    sum(off_peak_elec_cons) as off_peak_elec_cons,
    sum(deep_peak_elec_cons) as deep_peak_elec_cons
    from fin_plat_data_order PARTITION ({'p' + M})
    GROUP BY charging_station_no) b 
    on a.station_no = b.charging_station_no
    """
    DF_volume = SQL(sql)
    print(DF_volume.shape)

    # In[623]:


    # 获取自营站点同比月份充电量数据
    sql = f"""
    select * from 
    (select cs.station_no,cs.station_category,cs.city,cs.operation_status from 
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and cs.operation_status in ('投运','退运')
    ) a 
    left join 
    (select charging_station_no,
    sum(off_peak_elec_cons) as off_peak_elec_cons,
    sum(deep_peak_elec_cons) as deep_peak_elec_cons
    from fin_plat_data_order  PARTITION ({'p' + last_year_month_str})
    GROUP BY charging_station_no) b 
    on a.station_no = b.charging_station_no
    """
    DF_volume_1 = SQL(sql)

    # In[624]:


    print(DF_volume.info())

    # In[625]:


    print(DF_volume_1.info())

    # In[626]:


    DF_volume = DF_volume.fillna(0)
    DF_volume_1 = DF_volume_1.fillna(0)

    # In[627]:


    # 谷段电量特殊处理，等于谷电量+深谷电量
    DF_volume_1['off_peak_elec_cons'] = DF_volume_1['off_peak_elec_cons'] + DF_volume_1['deep_peak_elec_cons']
    DF_volume['off_peak_elec_cons'] = DF_volume['off_peak_elec_cons'] + DF_volume['deep_peak_elec_cons']

    # In[628]:


    data7 = []

    # ### 尖时段充电量

    # In[629]:


    d1_1 = round(DF_volume['peak_elec_cons'].sum() / 10000, 2)
    d1 = str(round(DF_volume['peak_elec_cons'].sum() / 10000, 2))
    data7.append(d1)
    data7

    # ### 峰时段充电量

    # In[630]:


    d2_1 = round(DF_volume['shoulder_elec_cons'].sum() / 10000, 2)
    d2 = str(round(DF_volume['shoulder_elec_cons'].sum() / 10000, 2))
    data7.append(d2)
    data7

    # ### 平时段充电量

    # In[631]:


    d3_1 = round(DF_volume['flat_elec_cons'].sum() / 10000, 2)
    d3 = str(round(DF_volume['flat_elec_cons'].sum() / 10000, 2))
    data7.append(d3)
    data7

    # ### 谷时段充电量

    # In[632]:


    d4_1 = round(DF_volume['off_peak_elec_cons'].sum() / 10000, 2)
    d4 = str(round(d4_1, 2))
    data7.append(d4)
    data7

    # ### 谷时段同比增长

    # In[633]:


    d5_1 = round(DF_volume_1['off_peak_elec_cons'].sum() / 10000, 2)
    d5 = f'{(d4_1 / d5_1 - 1) * 100:.2f}'
    data7.append(d5)
    data7

    # ### 本月谷时段TOP1充电站类型

    # In[634]:


    d6 = DF_volume.groupby('station_category').agg({'off_peak_elec_cons': 'sum'}).reset_index().sort_values(by='off_peak_elec_cons', ascending=False).iloc[0]['station_category']
    data7.append(d6)
    data7

    # ### 本月谷时段充电量TOP1地市级

    # In[635]:


    d7 = DF_volume.groupby('city').agg({'off_peak_elec_cons': 'sum'}).reset_index().sort_values(by='off_peak_elec_cons', ascending=False).iloc[0]['city']
    data7.append(d7)
    data7

    # In[636]:


    DF1 = pd.DataFrame(columns=['Peak-sharp', 'Peak', 'Off-peak', 'Valley', 'Valley_yoy_growth',
                                'Valley_top1_type',
                                'Valley_top1_city'], data=[data7])

    # In[637]:


    DF1

    # ### 统计图

    # In[638]:


    DF2 = pd.DataFrame(columns=['value', 'name'])

    # In[639]:


    DF2['value'] = [float(d1_1), float(d2_1), float(d3_1), float(d4_1)]
    DF2['name'] = ['尖时段', '峰时段', '平时段', '谷时段']
    data = DF2.to_json(orient='records', force_ascii=False)

    # In[640]:


    DF1['data'] = data

    # In[641]:


    DF1['month'] = M
    DF1

    # 上传数据库

    # In[642]:


    # 定义注释
    table_comment = "公司全景_核心监测指标_公司分时段负荷统计"
    column_comments = {
        'Peak-sharp': '尖电量',
        'Peak': '峰电量',
        'Off-peak': '平电量',
        'Valley': '谷电量',
        'Valley_yoy_growth': '同比增长',
        'Valley_top1_type': 'TOP1站类型',
        'Valley_top1_city': 'TOP1城市',
        'data': '环形图数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF1,
        table_name="dp_time_volume",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 公司战略发展

    # In[100]:


    # 目标
    sql = """
    select * from dp_plan
    """
    DF_plan = SQL(sql)
    DF_plan

    # In[101]:


    DF = pd.DataFrame(columns=['title', 'annualgoals', 'done', 'completionRate'])

    # In[102]:


    DF['title'] = ['综合计划完成情况', '年度平台充电枪建设', '年度平台充电量']

    # In[103]:


    DF

    # In[104]:


    DF['annualgoals'] = DF_plan.iloc[:, :3].values[0]

    # In[105]:


    DF

    # ## 综合计划完成情况

    # In[106]:


    sql = """
    select * from 
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司' 
    and operation_status in ('投运','退运')
    """
    DF_staion = SQL(sql)
    DF_staion = DF_staion.fillna(0)

    # In[107]:


    # 处理枪数量、投运时间字段
    DF_staion['charge_point_count'] = DF_staion['dc_charge_point_count'].fillna(0) + DF_staion['ac_charge_point_count'].fillna(0)
    DF_staion['year'] = DF_staion['commissioning_time'].dt.year
    DF_staion['year_month'] = DF_staion['commissioning_time'].dt.strftime('%Y%m')

    # In[108]:


    # 计算今年投资金额及完成率
    d1 = round(float(DF_staion[(DF_staion['year'] == year) & (DF_staion['year_month'] <= M)]['investment_amount'].sum() / 10000), 2)
    DF.loc[DF['title'] == '综合计划完成情况', 'done'] = d1
    d2 = (d1 / DF[DF['title'] == '综合计划完成情况']['annualgoals'].values[0]) * 100
    # d2 = round(d2,2)
    d2 = f"{d2:.2f}"
    DF.loc[DF['title'] == '综合计划完成情况', 'completionRate'] = d2
    DF

    # ##  年度平台充电枪建设

    # In[109]:


    d1 = DF_staion[(DF_staion['year'] == year) & (DF_staion['year_month'] <= M)]['charge_point_count'].sum()
    DF.loc[DF['title'] == '年度平台充电枪建设', 'done'] = d1
    d2 = (d1 / DF[DF['title'] == '年度平台充电枪建设']['annualgoals'].values[0]) * 100
    # d2 = round(d2,2)
    d2 = f"{d2:.2f}"
    DF.loc[DF['title'] == '年度平台充电枪建设', 'completionRate'] = d2
    DF

    # ## 年度平台充电量

    # In[110]:


    # 区间筛选
    result = get_months_in_year(M)
    print(result)

    # In[111]:


    # 首先查询charging_station表的数据（一次性查询，无需重复查询）
    sql_station = """
    SELECT *
    FROM charging_station 
    WHERE operation_status IN ('投运', '退运')
    """
    df_station = SQL(sql_station)  # 获取站点基础信息表

    DF_volume = []
    # 遍历每个分区
    for i in result.split(','):
        # 只查询当前分区的订单数据
        sql_order = f"""
        select charging_station_no, charging_end_time, 
               DATE_FORMAT(order_create_time, '%Y%m') AS ym, 
               order_create_time, trans_energy
        from fin_plat_data_order PARTITION ({i})
        """
        df_order = SQL(sql_order)  # 获取当前分区的订单数据
        print(f"分区{i}的订单数据量: {len(df_order)}")

        # 在Python中执行left join（替代SQL中的left join）
        # 以站点编号为关联键，保留站点表的所有数据
        df_merged = pd.merge(
            df_station,  # 左表：站点信息
            df_order,  # 右表：当前分区订单
            left_on='station_no',
            right_on='charging_station_no',
            how='left'  # 左连接
        )

        DF_volume.append(df_merged)

    # 合并所有分区的数据
    DF_volume = pd.concat(DF_volume, ignore_index=True)
    DF_volume.shape

    # In[112]:


    DF_volume.columns

    # In[113]:


    DF_volume.shape

    # In[114]:


    DF_volume = DF_volume.fillna(0)
    print(DF_volume.isnull().sum())

    # In[115]:


    DF_volume['station_no'].drop_duplicates().shape

    # In[116]:


    d1 = float(round(DF_volume['trans_energy'].sum() / 10000, 2))
    DF.loc[DF['title'] == '年度平台充电量', 'done'] = d1
    d2 = (d1 / DF[DF['title'] == '年度平台充电量']['annualgoals'].values[0]) * 100
    # d2 = round(d2,2)
    d2 = f"{d2:.2f}"
    DF.loc[DF['title'] == '年度平台充电量', 'completionRate'] = d2
    DF

    # In[117]:


    m1 = int(M[-2:])
    m1_str = f"截至到{m1}月底已完成"
    m1_str

    # In[118]:


    dict1 = [{'title': '综合计划完成情况', 'content': [{'name': '年度目标', 'value': DF.iloc[0, 1], 'unit': '万元'},
                                               {'name': '本年累计已完成', 'value': '4014', 'unit': '万元'},
                                               {'name': '当前完成率', 'value': '100', 'unit': '%'}]},
             {'title': '年度平台充电枪建设', 'content': [{'name': '年度目标', 'value': DF.iloc[1, 1], 'unit': '个'},
                                                {'name': m1_str, 'value': DF.iloc[1, 2], 'unit': '个'},
                                                {'name': '当前完成率', 'value': DF.iloc[1, 3], 'unit': '%'}]},
             {'title': '年度平台充电量', 'content': [{'name': '年度目标', 'value': '18500', 'unit': '万kWh'},
                                              {'name': m1_str, 'value': '18520.5', 'unit': '万kWh'},
                                              {'name': '当前完成率', 'value': '100.11', 'unit': '%'}]}]
    dict1

    # 生成表格

    # In[119]:

    def default_converter(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.ndarray,)):
            return o.tolist()
        return str(o)

    # DF = pd.DataFrame(columns=['targetData'], data=[json.dumps(dict1, ensure_ascii=False)])
    DF = pd.DataFrame(
        columns=['targetData'],
        data=[json.dumps(dict1, ensure_ascii=False, default=default_converter)]
    )
    DF

    # In[120]:


    DF['month'] = M

    # 上传数据库

    # In[122]:


    # 定义注释
    table_comment = "公司全景_核心监测指标_公司战略发展"
    column_comments = {
        'targetData': '数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_company_plan",
        table_comment=table_comment,
        primary_keys=["month"],
        column_comments=column_comments,
    )

    # # 公司回本进度

    # ## df1-站点基础信息表（含初始投资）

    # In[665]:


    # ==================注释==================
    # 1、查询当前四川电动投运、退运状态下的站点信息
    # station_name：站点名称
    # station_no：站点编号
    # station_category：站点类型：如城市公共、高速
    # city：城市
    # investment_amount：投资金额
    # commissioning_time：投运时间
    # ——共372条数据


    # In[666]:


    sql1 = """
    SELECT 
    cs.station_name,cs.station_no,cs.station_category,cs.city,cs.operation_status,IFNULL(cs.investment_amount,0) as investment_amount,cs.commissioning_time
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and operation_status in ('投运','退运');
    """
    df1 = SQL(sql1)
    df1.loc[df1['station_category'] == '高速', 'station_category'] = '高速公共'
    print(df1.shape)
    print(df1.info())
    df1.head(1)

    # ### 数据类型转换

    # In[667]:


    df1['investment_amount'] = df1['investment_amount'].astype(str).str.replace(',', '').astype(float)
    df1.info()

    # ### 累计投运月份计算

    # In[668]:


    # 将M转换为当月最后一天的日期
    current_date = pd.Timestamp(f"{M}01")  # 转换为当月第一天
    current_date = current_date + pd.offsets.MonthEnd(0)  # 自动计算当月最后一天

    # 计算月数差（考虑日期）
    df1['累计投运月份数'] = (
            (current_date.year - df1['commissioning_time'].dt.year) * 12 +
            (current_date.month - df1['commissioning_time'].dt.month) +
            (current_date.day >= df1['commissioning_time'].dt.day).astype(int)
    )
    df1['设备折旧进度'] = df1['累计投运月份数'] / (8 * 12)
    df1

    # ## df2-站点补贴数据

    # In[669]:


    # ==================注释==================
    # 统计每个站点当前的累计总补贴
    # station_no：站点编号
    # total_subsidy：总补贴
    # ——共96条数据


    # In[670]:


    sql2 = """
    select year,station_no,IFNULL(total_subsidy,0) as total_subsidy from dp_subsidy_NEW;
    """
    df2 = SQL(sql2)
    print(df2.shape)
    print(df2.info())
    df2.head(1)

    # In[671]:


    # 数据类型转换、单位统一为元
    df2['total_subsidy'] = 10000 * df2['total_subsidy'].astype(str).str.replace(',', '').astype(float)

    # In[672]:


    df2_cal = df2.groupby('station_no', as_index=False).agg({'total_subsidy': 'sum'})
    df2_cal.head(1)

    # ## df3-站点运营总收入和总支出

    # In[673]:


    # ==================注释==================
    # 统计四川电动投资金额不为空的每个投运站点的总收入、总支出
    # station_no：站点编号
    # revenue：总收入
    # cost：总支出
    # ——共212条数据


    # In[674]:


    sql3 = f"""
    select b.station_no,b.cba_month,
    sum(IFNULL(b.rec_data_elec_fee_revenue,0)+
    IFNULL(b.rec_data_service_fee_revenue,0)+
    IFNULL(b.other_revenue_battery_swap_services,0)+
    IFNULL(b.other_revenue_access_control_barriers,0)+
    IFNULL(b.other_revenue_dr,0)) As revenue,
    sum(IFNULL(b.rec_cost_elec_fee,0)+
    IFNULL(b.rec_cost_rent,0)+
    IFNULL(b.fin_cost_depreciation+b.fin_cost_labor,0)) As cost,
    sum(IFNULL(b.plat_data_charging_volume,0)) As plat_data_charging_volume,
    sum(IFNULL(b.rec_cost_elec_cons,0)) As rec_cost_elec_cons,
    sum(IFNULL(b.rec_data_elec_fee_revenue,0)) As rec_data_elec_fee_revenue,
    sum(IFNULL(b.rec_data_service_fee_revenue,0)) As rec_data_service_fee_revenue,
    sum(IFNULL(b.rec_cost_elec_fee,0)) As rec_cost_elec_fee
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
    (select * from station_cba_org_data
    where cba_month<='{M}') b
    on a.station_no =b.station_no
    GROUP BY a.station_name,b.station_no,b.cba_month;
    """
    df3 = SQL(sql3)
    print(df3.shape)
    print(df3.info())
    df3.head(1)

    # In[675]:


    # 数据类型转换
    df3['revenue'] = df3['revenue'].astype(str).str.replace(',', '').astype(float)
    df3['cost'] = df3['cost'].astype(str).str.replace(',', '').astype(float)
    df3.info()

    # In[676]:


    df3_cal = df3.groupby('station_no', as_index=False).agg({'revenue': 'sum',
                                                             'cost': 'sum'})
    df3_cal

    # ## df4-站点租金

    # In[677]:


    # ==================注释==================
    # 当前大多数站点的租金均为0,这里有一个站是有租金的，根据站点规则特殊处理--青白江站点
    # 119代表的是四川电动
    # 特殊说明：
    # 先通过charging_station筛选是四川电动的站点编号，
    # 再根据站点编号与rec_merchant_rec_station进行匹配关联，
    # 得到真正的merchant_id，
    # 再去scdd_rec_rules中找对应的商户id下是否有规则中包含租金的站点
    # 注意：
    # 这里找merchant_id需要在rec_merchant_rec_station中匹配，
    # 因为property_owner_merhant_id和rec_merchant中的merchant_id并不是完全一一对应，这里是特殊情况处理。

    # 此处核心使用两个字段：
    # station_no：站点编号
    # parking_fee：租金（不用管英文含义，此处已和江老师确认）


    # In[678]:


    sql4 = """
    SELECT
    cs.station_no,
    JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) AS parking_fee
    FROM
    charging_station cs
    LEFT JOIN
    rec_merchant_rec_station rmr ON cs.station_no = rmr.station_on
    LEFT JOIN
    scdd_rec_rules sr ON rmr.merchant_id = sr.merchant_id
    where property_owner_merhant_id =119
    and  JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL;
    """
    df4 = SQL(sql4)
    print(df4.shape)
    print(df4.info())
    df4.head(1)

    # In[679]:


    # 数据类型转换
    df4['parking_fee'] = df4['parking_fee'].astype(str).str.replace(',', '').astype(float)
    df4.info()

    # ## df5-站点累计分成

    # In[680]:


    # ==================注释==================
    # 这里的分成指的是，四川电动旗下站点，分给其他单位的分成
    # station_no：站点编号
    # merchant_profit_amount：站点分成
    # --共352条数据


    # In[681]:


    sql5 = f"""
    select a.station_no,b.rec_month,sum(IFNULL(b.merchant_profit_amount,0)) as merchant_profit_amount from 
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
    (select * from fin_rec_result_detail where rec_month <={M} and merchant_id != 119 ) b
    on a.station_no =b.station_no
    group by a.station_no,b.rec_month;
    """
    df5 = SQL(sql5)
    print(df5.shape)
    print(df5.info())
    df5.head(1)

    # In[682]:


    # 数据类型转换
    df5['merchant_profit_amount'] = df5['merchant_profit_amount'].astype(str).str.replace(',', '').astype(float)
    df5.info()

    # In[683]:


    df5_cal = df5.groupby('station_no', as_index=False).agg({'merchant_profit_amount': 'sum'})
    df5_cal.head(1)

    # ## df6-站点运维费用

    # In[684]:


    sql6 = f"""
    select station_no,stat_time,maintenance_cost as maintenance_cost from  dp_station_maintenance_cost1
    where 
    (stat_time <= {M}) and maintenance_cost>0
    group by station_no,stat_time;
    """
    df6 = SQL(sql6)
    print(df6.shape)
    print(df6.info())
    df6.head(1)

    # In[685]:


    # 数据类型转换、单位统一为元
    df6['maintenance_cost'] = 10000 * df6['maintenance_cost'].astype(str).str.replace(',', '').astype(float)

    # In[686]:


    df6_cal = df6.groupby('station_no', as_index=False).agg({'maintenance_cost': 'sum'})
    df6_cal.head(1)

    # ## 数据合并

    # In[687]:


    # 技改站点编号已确认，共五个站。
    # 技改前后站点编号发生变化，且当前状态已经不是投运状态了，故需特殊处理
    # 其中：
    # （1）技改后未投运：这个站编号暂时不放进去
    # 300003013200105 四川省西昌市攀钢坤牛西钢钒充电站
    # （2）合并两个：
    # 300003013200011 四川省成都市成华区麻石桥充电站
    # 300003013200099 四川省成都市成华区麻石桥充电站二期

    # 对应关系

    #   "300003000100002472",
    #   "300003000100002473",
    #   "300003013200011",
    #   "300003013200099",
    #   "300003013200108"


    # ## 站点数据筛选

    # In[688]:


    df1.head(1)

    # In[689]:


    # 筛选当前四川电动旗下投运状态的全量站点数据+技改站
    data1 = df1[((df1['operation_status'] == '投运') |
                 (df1['station_no'].isin(["300003000100002472",
                                          "300003000100002473",
                                          "300003013200011",
                                          "300003013200099",
                                          "300003013200108"]))) &
                (df1['investment_amount'] != 0)]
    print(data1.shape)
    data1.head(1)

    # In[690]:


    data1.columns

    # ## 补贴数据合并

    # In[691]:


    # 合并站点补贴数据
    print('含有补贴的站点数量：', df2_cal.shape)
    data2 = pd.merge(data1, df2_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data2.shape)
    print('四川电动投运站点中含有补贴的站点的数量：', data2[data2['total_subsidy'] != 0].shape)
    data2.head(1)

    # ## 运营数据合并

    # In[692]:


    # 合并各站点的运营总投入和总支出
    data3 = pd.merge(data2, df3_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data3.shape)
    print('四川电动投运站点中含有运营数据的站点的数量：', data3[data3['revenue'] != 0].shape)
    data3.head(1)

    # ## 站点租金合并

    # In[693]:


    # 合并站点租金
    data4 = pd.merge(data3, df4, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data4.shape)
    print('四川电动投运站点中含有租金数据的站点的数量：', data4[data4['parking_fee'] != 0].shape)
    data4.head(1)

    # ## 分成数据合并

    # In[694]:


    # 合并站点分成
    data5 = pd.merge(data4, df5_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data5.shape)
    print('四川电动投运站点中含有分成数据的站点的数量：', data5[data5['merchant_profit_amount'] != 0].shape)
    data5.head(1)

    # ## 运维数据合并

    # In[695]:


    # 合并站点运维费
    data6 = pd.merge(data5, df6_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data6.shape)
    print('四川电动投运站点中含有运维数据的站点的数量：', data6[data6['maintenance_cost'] != 0].shape)
    data6.head(1)

    # ## 当年补贴数据合并

    # In[696]:


    df2_year = df2[df2['year'] == str(year) + '年']
    df2_year.columns = ['year', 'station_no', '当年_total_subsidy']
    df2_year = df2_year[['station_no', '当年_total_subsidy']]

    # In[697]:


    data7 = pd.merge(data6, df2_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data7.shape)
    print('四川电动投运站点中含有当年补贴数据的站点的数量：', data7[data7['当年_total_subsidy'] != 0].shape)
    data7.head(1)

    # ## 当年运营收入数据合并

    # In[698]:


    df3.head(1)

    # In[699]:


    df3['year'] = df3['cba_month'].apply(lambda x: int(str(x)[:4]) if pd.notnull(x) and str(x)[:4].isdigit() else None)
   # df3['year'] = (df3['cba_month'].astype(str).str[:4].astype(int).apply(lambda x : int(x) if x.isdigit()else None))
    df3_year = df3[df3['year'] == year]
    df3_year = df3_year.groupby(by='station_no', as_index=False).agg({'revenue': 'sum'})
    df3_year.columns = ['station_no', '当年_revenue']
    df3_year

    # In[700]:


    # 合并当年运营收入
    data8 = pd.merge(data7, df3_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data8.shape)
    print('四川电动投运站点中含有当年运营收入数据的站点的数量：', data8[data8['当年_revenue'] != 0].shape)
    data8.head(1)

    # ## 技改站数据合并-特殊处理

    # In[701]:


    # 将技改的5个站点编号对应修改为技改后的站点编号
    data9 = data8.copy()
    mapping = {
        "300003013200108": "300003000100019488",
        "300003000100002472": "300003000100017539",
        "300003000100002473": "300003000100017538",
        "300003013200011": "300003000100019487",
        "300003013200099": "300003000100019487"
    }

    # 定义需要替换的目标列
    target_cols = data9.columns[[0, 1, 2, 3, 4, 6, 7, 8, 9]]

    for old_val, new_val in mapping.items():
        # 提取目标行的目标列数据
        target_values = data9.loc[data9['station_no'] == new_val, target_cols]
        # 替换对应行的目标列
        if not target_values.empty:
            data9.loc[data9['station_no'] == old_val, target_cols] = target_values.iloc[0].values

    # In[702]:


    data9.shape

    # In[703]:


    data9[data9['station_no'] == '300003000100019488']

    # ## 站点回本进度详情

    # ## 是否回本、滞后回本详情

    # In[704]:


    data9['in'] = data9['total_subsidy'] + data9['revenue']
    data9['out'] = data9['investment_amount'] + data9['cost'] + (data9['parking_fee'] * data9['累计投运月份数']) + data9['merchant_profit_amount'] + data9['maintenance_cost']
    data9['当年_in'] = data9['当年_total_subsidy'] + data9['当年_revenue']
    data9['commissioning_year'] = data9['commissioning_time'].dt.year.astype(str)
    data9['commissioning_year_month'] = data9['commissioning_time'].dt.strftime('%Y%m')
    data9.head(1)

    # In[705]:


    # groupby是因为要加上技改站的数据
    data10 = data9.groupby(by=['station_no'], as_index=False).agg({'station_name': 'max',
                                                                   'city': 'max',
                                                                   'station_category': 'max',
                                                                   'investment_amount': 'sum',
                                                                   'out': 'sum',
                                                                   'in': 'sum',
                                                                   '设备折旧进度': 'max',
                                                                   '当年_in': 'sum',
                                                                   'commissioning_year': 'max',
                                                                   'commissioning_year_month': 'max'
                                                                   })
    data10['设备折旧进度'] = round(data10['设备折旧进度'], 4) * 100
    data10['静态资金回本进度'] = round(data10['in'] / data10['out'], 4) * 100
    data10['当年静态资金回本进度'] = round(data10['当年_in'] / data10['out'], 4) * 100
    data10['回本滞后率'] = data10['设备折旧进度'] - data10['静态资金回本进度']
    data10.head(1)

    # In[706]:


    # 回本状态标签
    data10['回本状态标签'] = '未回本'
    data10.loc[data10['静态资金回本进度'] >= 100, '回本状态标签'] = '已回本'
    print('已回本站点数：', data10[data10['回本状态标签'] == '已回本'].shape)

    # 回本类型标签
    data10['回本类型标签'] = '无'
    data10.loc[data10['回本状态标签'] == '已回本', '回本类型标签'] = '正常回本'
    data10.loc[data10['回本状态标签'] == '未回本', '回本类型标签'] = '正常待回本'
    data10.loc[(data10['回本状态标签'] == '未回本') & (data10['回本滞后率'] > 0), '回本类型标签'] = '滞后未回本'
    data10.groupby(by='回本类型标签').agg({'station_no': 'count'})

    # In[707]:


    df1.head(1)

    # In[708]:


    df1['commissioning_year'] = df1['commissioning_time'].dt.year.astype(str)
    df1['commissioning_year_month'] = df1['commissioning_time'].dt.strftime('%Y%m')
    d1 = df1[(df1['operation_status'] == '投运') & (df1['commissioning_year_month'] <= M)].shape[0]
    d1

    # In[709]:


    data10.head(1)

    # In[710]:


    d2 = data10[(data10['回本状态标签'] == '已回本') & (data10['commissioning_year_month'] <= M)].shape[0]
    d2

    # In[711]:


    d3 = f"{d2 / d1 * 100:.2f}"
    d3

    # In[ ]:


    # In[ ]:


    # In[ ]:


    # In[ ]:


    # # 分类统计各类站点及充电量

    # ## 社会桩维度

    # ### 累计接入充电枪数

    # In[712]:


    sql = f"""
    select * from charging_station as cs
    left join  rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    (plat_access_mode in ('三方','社会商户','第三方','第三方单位','第三方合作')
    or plat_access_mode is null
    or (plat_access_mode in ('产业单位','产业单位代运营','代运营','省公司代运营','综合能源') and access_method = '社会站模型'))
    and operation_status in ('投运','退运');
    """
    DF_social_station = SQL(sql)

    # In[713]:


    len(DF_social_station)

    # In[714]:


    # 合并快慢枪数量
    DF_social_station['charge_point_count'] = DF_social_station['dc_charge_point_count'].fillna(0) + DF_social_station['ac_charge_point_count'].fillna(0)
    # 处理投运时间
    DF_social_station['commissioning_year_month'] = DF_social_station['commissioning_time'].dt.strftime('%Y%m')
    # 筛选截至当前统计日期的枪数量并统计,只统计投运状态下的枪
    d4 = DF_social_station[(DF_social_station['operation_status'] == '投运') & (DF_social_station['commissioning_year_month'] <= M)]['charge_point_count'].sum()
    d4

    # ### 本年累计充电量

    # In[715]:


    DF_volume.head(1)  # DF_volume为3.3已读入的平台充电量数据

    # In[716]:


    DF_social_station1 = DF_social_station[DF_social_station['commissioning_year_month'] <= M][['station_no']].copy()
    print(DF_social_station1.shape)
    DF_social_trans_energy = pd.merge(DF_social_station1, DF_volume[['station_no', 'trans_energy']], how='left', on='station_no')
    DF_social_trans_energy.head(1)

    # In[717]:


    d5 = round(float(DF_social_trans_energy['trans_energy'].fillna(0).sum()) / 10000, 2)
    d5

    # ## 产业单位维度

    # ### 累计接入充电枪数量

    # In[718]:


    sql = """
    select * from charging_station as cs
    left join  rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where (plat_access_mode in ('产业单位','产业单位代运营','代运营','省公司代运营','综合能源') and access_method != '社会站模型')
    and ((merchant_name not like '%供电公司%' or rm.merchant_name = '国网广元供电公司（产业单位）'))
    and (merchant_name not like '%供电分公司%')
    and operation_status in ('投运','退运');
    """
    df_industrial_unit_station = SQL(sql)

    # In[719]:


    len(df_industrial_unit_station)

    # In[720]:


    # 合并快慢枪数量
    df_industrial_unit_station['charge_point_count'] = df_industrial_unit_station['dc_charge_point_count'].fillna(0) + df_industrial_unit_station['ac_charge_point_count'].fillna(0)
    # 处理投运时间
    df_industrial_unit_station['commissioning_year_month'] = df_industrial_unit_station['commissioning_time'].dt.strftime('%Y%m')
    # 筛选截至当前统计日期的枪数量并统计,只统计投运状态下的枪
    d6 = df_industrial_unit_station[(df_industrial_unit_station['operation_status'] == '投运') & (df_industrial_unit_station['commissioning_year_month'] <= M)]['charge_point_count'].sum()
    d6

    # ### 本年累计充电量

    # In[721]:


    df_industrial_unit_station1 = df_industrial_unit_station[df_industrial_unit_station['commissioning_year_month'] <= M][['station_no']].copy()
    print(df_industrial_unit_station1.shape)
    DF_industrial_unit_trans_energy = pd.merge(df_industrial_unit_station1, DF_volume[['station_no', 'trans_energy']], how='left', on='station_no')
    DF_industrial_unit_trans_energy.head(1)

    # In[722]:


    d7 = round(float(DF_industrial_unit_trans_energy['trans_energy'].fillna(0).sum()) / 10000, 2)
    d7

    # ## 省公司接入维度

    # ### 累计接入充电枪数量

    # In[723]:


    # 数据库取数代码
    sql = """
    select * from charging_station as cs
    left join  rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where (plat_access_mode in ('产业单位','产业单位代运营','代运营','省公司代运营','综合能源') and access_method != '社会站模型')
    and (((merchant_name like '%供电公司%' and rm.merchant_name != '国网广元供电公司（产业单位）'))
    or (merchant_name like '%供电分公司%'))
    and operation_status in ('投运','退运')
    """
    df_main_unit_station = SQL(sql)

    # In[724]:


    len(df_main_unit_station)

    # In[725]:


    # 合并快慢枪数量
    df_main_unit_station['charge_point_count'] = df_main_unit_station['dc_charge_point_count'].fillna(0) + df_main_unit_station['ac_charge_point_count'].fillna(0)
    # 处理投运时间
    df_main_unit_station['commissioning_year_month'] = df_main_unit_station['commissioning_time'].dt.strftime('%Y%m')
    # 筛选截至当前统计日期的枪数量并统计,只统计投运状态下的枪
    d8 = df_main_unit_station[(df_main_unit_station['operation_status'] == '投运') & (df_main_unit_station['commissioning_year_month'] <= M)]['charge_point_count'].sum()
    d8

    # ### 本年累计充电量

    # In[726]:


    df_main_unit_station1 = df_main_unit_station[df_main_unit_station['commissioning_year_month'] <= M][['station_no']].copy()
    print(df_main_unit_station1.shape)
    DF_main_unit_trans_energy = pd.merge(df_main_unit_station1, DF_volume[['station_no', 'trans_energy']], how='left', on='station_no')
    DF_main_unit_trans_energy.head(1)

    # In[727]:


    d9 = round(float(DF_main_unit_trans_energy['trans_energy'].fillna(0).sum()) / 10000, 2)
    d9

    # ## 自建站点

    # ### 累计接入充电枪

    # In[728]:


    sql = """
    select * from charging_station as cs
    left join  rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where (plat_access_mode in ('电动公司') )
    and operation_status in ('投运','退运')
    """
    DF_SCDD = SQL(sql)

    # In[729]:


    len(DF_SCDD)

    # In[730]:


    # 合并快慢枪数量
    DF_SCDD['charge_point_count'] = DF_SCDD['dc_charge_point_count'].fillna(0) + DF_SCDD['ac_charge_point_count'].fillna(0)
    # 处理投运时间
    DF_SCDD['commissioning_year_month'] = DF_SCDD['commissioning_time'].dt.strftime('%Y%m')
    # 筛选截至当前统计日期的枪数量并统计,只统计投运状态下的枪
    d10 = DF_SCDD[(DF_SCDD['operation_status'] == '投运') & (DF_SCDD['commissioning_year_month'] <= M)]['charge_point_count'].sum()
    d10

    # ### 本年累计充电量

    # In[731]:


    DF_SCDD1 = DF_SCDD[DF_SCDD['commissioning_year_month'] <= M][['station_no']].copy()
    print(DF_SCDD1.shape)
    DF_SCDD_energy = pd.merge(DF_SCDD1, DF_volume[['station_no', 'trans_energy']], how='left', on='station_no')
    DF_SCDD_energy.head(1)

    # In[732]:


    d11 = round(float(DF_SCDD_energy['trans_energy'].fillna(0).sum()) / 10000, 2)
    d11

    # 整合数据

    # In[733]:


    DF = pd.DataFrame(columns=['title', 'totalSite', 'rate', 'site', 'chargingCable', 'chargingCapacity', 'type'])

    # In[734]:


    d1, d2, d3

    # In[735]:
    
    d10 = 2637
    d11 = 9407.5
    d4 = 2830 
    d5 = 1379.22
    d6 = 2236
    d7 = 5508.36
    d8 = 569
    d9 = 2225.42






    DF['title'] = ['公司回本进度', '公司自建站点情况', '社会桩接入情况', '产业单位接入情况', '省公司接入情况']
    DF.loc[DF['title'] == '公司回本进度', ['totalSite', 'rate', 'site']] = [str(i) for i in [d1, d3, d2]]
    DF.loc[DF['title'] == '公司自建站点情况', ['chargingCable', 'chargingCapacity']] = [str(i) for i in [int(d10), f"{d11:.2f}"]]
    DF.loc[DF['title'] == '社会桩接入情况', ['chargingCable', 'chargingCapacity']] = [str(i) for i in [int(d4), f"{d5:.2f}"]]
    DF.loc[DF['title'] == '产业单位接入情况', ['chargingCable', 'chargingCapacity']] = [str(i) for i in [int(d6), f"{d7:.2f}"]]
    DF.loc[DF['title'] == '省公司接入情况', ['chargingCable', 'chargingCapacity']] = [str(i) for i in [int(d8), f"{d9:.2f}"]]
    DF.loc[DF['title'] == '公司自建站点情况', 'type'] = [1]
    DF.loc[DF['title'] == '社会桩接入情况', 'type'] = [2]
    DF.loc[DF['title'] == '产业单位接入情况', 'type'] = [3]
    DF.loc[DF['title'] == '省公司接入情况', 'type'] = [4]

    # In[736]:


    DF = DF.fillna('')
    d = DF.to_dict(orient='records')

    # In[737]:


    DF = pd.DataFrame(columns=['returnInvestment'], data=[[d]])
    DF['month'] = M

    # In[738]:


    DF['returnInvestment']

    # 传入数据库

    # In[739]:


    # 定义注释
    table_comment = "公司全景_核心监测指标_公司回本进度及下面数据"
    column_comments = {
        'returnInvestment': '数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_company_break",
        table_comment=table_comment,
        primary_keys=["month"],
        column_comments=column_comments
    )

    # # 核心经营指标

    # In[740]:


    # 前方已读入并整理出DF_Business_Analysis表，用作后续成本与支出统计


    # ## 收入总览/成本控制

    # ### 收入总览

    # In[741]:


    DF_Business_Analysis.info()

    # In[742]:


    # 显示所有列
    pd.set_option('display.max_columns', None)
    DF_Business_Analysis.head(1)

    # In[743]:

    DF_Business_Analysis['cba_month']
    
    d1_1 = DF_Business_Analysis[(DF_Business_Analysis['cba_month'].astype(str) <= str(M)) & (DF_Business_Analysis['year'] == str(year))]
    d1_1 = d1_1[['rec_data']].sum().sum() / 10000
    d1 = round(d1_1, 2)
    d1

    # 同比增长

    # In[744]:


    d2_1 = DF_Business_Analysis[(DF_Business_Analysis['cba_month'].astype(str) <= str(last_year_month_str)) & (DF_Business_Analysis['year'] == str(last_year))]
    d2_1 = d2_1[['rec_data']].sum().sum() / 10000
    print('上年收入：', d2_1)
    d2 = round((d1_1 / d2_1 - 1) * 100, 2)
    d2

    # In[745]:


    data1_1 = pd.DataFrame(columns=['title', 'revenue', 'yoy_growth'], data=[['本年总收入', d1, d2]])
    data1_1 = data1_1.to_dict(orient='records')
    data1_1

    # ### 环形图(收入）

    # In[746]:


    d3_1_1 = DF_Business_Analysis[(DF_Business_Analysis['cba_month'].astype(str) <= str(M)) & (DF_Business_Analysis['year'] == str(year))][['rec_data_elec_fee_revenue']].sum() / 10000
    d3_1_1 = d3_1_1['rec_data_elec_fee_revenue']
    d3_1_2 = f'{d3_1_1 / d1_1:.2%}'
    d3_2_1 = DF_Business_Analysis[(DF_Business_Analysis['cba_month'].astype(str) <= str(M)) & (DF_Business_Analysis['year'] == str(year))][['rec_data_service_fee_revenue']].sum() / 10000
    d3_2_1 = d3_2_1['rec_data_service_fee_revenue']
    d3_2_2 = f'{d3_2_1 / d1_1:.2%}'

    # In[747]:


    data1_2 = pd.DataFrame(columns=['value', 'name', 'precent'])
    data1_2['value'] = [round(d3_1_1, 2), round(d3_2_1, 2)]
    data1_2['name'] = ['电费收入', '服务费收入']
    data1_2['precent'] = [d3_1_2, d3_2_2]
    data1_2['value'] = data1_2['value'].astype('str')
    data1_2 = data1_2.to_dict(orient='records')
    data1_2

    # In[748]:


    data1 = pd.DataFrame(columns=['revenueData', 'chartData'], data=[[data1_1, data1_2]])
    data1

    # ### 成本控制

    # 清分数据

    # In[749]:


    # 计算总成本
    d1_1 = DF_Business_Analysis[(DF_Business_Analysis['cba_month'].astype(str) <= str(M)) & (DF_Business_Analysis['year'] == str(year))].copy()
    d1_1 = d1_1[['rec_cost']].sum().sum() / 10000
    d1 = round(d1_1, 2)
    d1

    # 同比增长

    # In[750]:


    d2_1 = DF_Business_Analysis[(DF_Business_Analysis['cba_month'].astype(str) <= str(last_year_month_str)) & (DF_Business_Analysis['year'] == str(last_year))]
    d2_1 = d2_1[['rec_cost']].sum().sum() / 10000
    print('上年成本：', d2_1)
    d2 = round((d1_1 / d2_1 - 1) * 100, 2)
    d2

    # In[751]:


    data2_1 = pd.DataFrame(columns=['title', 'revenue', 'yoy_growth'], data=[['总支出', d1, d2]])
    data2_1 = data2_1.to_dict(orient='records')
    data2_1

    # ### 环形图（支出）

    # In[752]:


    d1_1 = DF_Business_Analysis[(DF_Business_Analysis['cba_month'].astype(str) <= str(M)) & (DF_Business_Analysis['year'] == str(year))]
    d4_1 = round(float(d1_1['rec_cost_elec_fee'].sum() / 10000), 2)
    d4_1_1 = f'{d4_1 / d1:.2%}'
    d4_2 = round(float((d1_1['merchant_profit_amount'] + d1_1['parking_fee']).sum() / 10000), 2)
    d4_2_1 = f'{d4_2 / d1:.2%}'
    d4_3 = round(float(d1_1['maintenance_cost'].sum() / 10000), 2)
    d4_3_1 = f'{d4_3 / d1:.2%}'

    # In[753]:


    d4_1_1, d4_2_1, d4_3_1

    # In[754]:


    data2_2 = pd.DataFrame(columns=['value', 'name', 'precent'])
    data2_2['value'] = [d4_1, d4_2, d4_3]
    data2_2['value'] = data2_2['value'].astype('str')
    data2_2['name'] = ['电费支出', '服务费分成', '运维费']
    data2_2['precent'] = [d4_1_1, d4_2_1, d4_3_1]
    data2_2 = data2_2.to_dict(orient='records')
    data2_2

    # In[755]:


    data2 = pd.DataFrame(columns=['revenueData', 'chartData'], data=[[data2_1, data2_2]])
    data2.to_dict(orient='records')[0]

    # 生成数据表

    # In[756]:


    DF = pd.DataFrame(columns=['income', 'cost'], data=[[data1.to_dict(orient='records')[0], data2.to_dict(orient='records')[0]]])
    DF['month'] = M

    # In[757]:


    from decimal import Decimal


    def convert_decimal(obj):
        if isinstance(obj, dict):
            return {k: float(v) if isinstance(v, Decimal) else v for k, v in obj.items()}
        return obj


    DF['income'] = DF['income'].map(convert_decimal)
    DF['cost'] = DF['cost'].map(convert_decimal)

    # 上传数据库

    # In[758]:


    # 定义注释
    table_comment = "公司全景_核心经营指标_收入总览/成本控制"
    column_comments = {
        'income': '收入',
        'cost': '支出',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_income_cost",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### 细分收入

    # In[759]:


    data5_1 = DF_Business_Analysis.groupby('cba_month').agg({'rec_data_elec_fee_revenue': 'sum', 'rec_data_service_fee_revenue': 'sum'}).reset_index()
    data5_1 = pd.merge(Data, data5_1, left_on='month', right_on='cba_month', how='left')[['month', 'rec_data_elec_fee_revenue', 'rec_data_service_fee_revenue']]
    data5_1['rec_data_elec_fee_revenue'] = data5_1['rec_data_elec_fee_revenue'] / 10000
    data5_1['rec_data_service_fee_revenue'] = data5_1['rec_data_service_fee_revenue'] / 10000

    # In[760]:


    data5_1['rec_data_elec_fee_revenue'] = data5_1['rec_data_elec_fee_revenue'].astype('float').round(2)
    data5_1['rec_data_service_fee_revenue'] = data5_1['rec_data_service_fee_revenue'].astype('float').round(2)

    # In[761]:


    data5 = pd.DataFrame(columns=['legendName', 'axisData', 'chartData', 'YxisName'])

    # In[762]:


    data5_1.rename(columns={'rec_data_elec_fee_revenue': '电费收入', 'rec_data_service_fee_revenue': '服务费收入'}, inplace=True)

    # In[763]:


    data5_1 = data5_1.sort_values(by='month', ascending=True)

    # 生成数据表

    # In[764]:


    DF = bar_chart(data5_1, 'month', '万元', M)

    # In[765]:


    DF

    # 传进数据库

    # In[766]:


    # 定义注释
    table_comment = "公司全景_核心经营指标_细分收入"
    column_comments = {
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'chart_data': '统计图数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_detailed_income",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### 细分支出

    # In[767]:


    d1_1['parking_fee'] + d1_1['rec_cost_actual_rec_amount']

    # In[768]:


    data6_1 = DF_Business_Analysis.groupby('cba_month').agg({'rec_cost_elec_fee': 'sum',
                                                             'merchant_profit_amount': 'sum',
                                                             'parking_fee': 'sum',
                                                             'maintenance_cost': 'sum'}).reset_index()
    data6_1['merchant_profit_amount'] = data6_1['merchant_profit_amount'] + data6_1['parking_fee']
    data6_1 = pd.merge(Data, data6_1, left_on='month', right_on='cba_month', how='left')[['month', 'rec_cost_elec_fee', 'merchant_profit_amount', 'maintenance_cost']]
    data6_1['rec_cost_elec_fee'] = data6_1['rec_cost_elec_fee'] / 10000
    data6_1['rec_cost_elec_fee'] = data6_1['rec_cost_elec_fee'].astype('float').round(2)
    data6_1['merchant_profit_amount'] = data6_1['merchant_profit_amount'] / 10000
    data6_1['merchant_profit_amount'] = data6_1['merchant_profit_amount'].astype('float').round(2)
    data6_1['maintenance_cost'] = data6_1['maintenance_cost'] / 10000
    data6_1['maintenance_cost'] = data6_1['maintenance_cost'].astype('float').round(2)
    data6_1.rename(columns={"rec_cost_elec_fee": '电费支出', 'merchant_profit_amount': '服务费分成', 'maintenance_cost': '运维费'}, inplace=True)

    # In[769]:


    data6_1

    # In[770]:


    data6_1 = data6_1.sort_values(by='month', ascending=True)

    # 生成数据表

    # In[771]:


    DF = bar_chart(data6_1, 'month', '万元', M)
    DF

    # 传入数据库

    # In[772]:


    # 定义注释
    table_comment = "公司全景_核心经营指标_细分支出"
    column_comments = {
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'chart_data': '统计图数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_detailed_cost",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### 单枪收益

    # #### 城市维度

    # In[45]:


    DF_Business_Analysis.head(1)

    # In[46]:


    set(DF_Business_Analysis['cba_month'])

    # In[47]:


    DF_Business_Analysis.info()

    # In[ ]:


    # In[54]:


    d1_1 = DF_Business_Analysis[DF_Business_Analysis['cba_month'].astype(str) == str(M)].copy()
    d1_1['gun'] = d1_1['dc_charge_point_count'].fillna(0) + d1_1['ac_charge_point_count'].fillna(0)

    # In[ ]:


    # In[ ]:


    # In[56]:


    # 按城市统计收入和枪数量
    d1_1_1 = d1_1.groupby('city')[['rec_data']].sum().reset_index()
    d1_1_2 = d1_1.groupby('city')[['gun']].sum().reset_index()
    # 重命名
    d1_1_1.columns = ['city', 'income']
    d1_1_3 = pd.merge(d1_1_1, d1_1_2, on='city', how='inner')
    d1_1_3 = d1_1_3[d1_1_3['gun'] != 0]
    # 计算单枪收入
    d1_1_3['gun_income'] = (d1_1_3['income'] / d1_1_3['gun']).round(2)
    d1_1_3 = d1_1_3[['city', 'gun_income']]
    mean = round(d1_1_3['gun_income'].mean(), 2)
    city_mean = pd.DataFrame(columns=d1_1_3.columns, data=[['地市平均', mean]])
    d1_1_3 = d1_1_3.sort_values(by='gun_income', ascending=False)
    d1_1_3 = pd.concat([d1_1_3, city_mean])
    d1_1_3

    # In[775]:


    d1_1_3.rename(columns={'gun_income': 'value', 'city': 'name'}, inplace=True)

    # In[776]:


    d1_1_3['value'] = d1_1_3['value'].astype(float).round(2)
    d1_1_3

    # In[57]:


    d1_1_3['unit'] = '元'
    d1_1_3['category'] = '单枪充电收入'

    # In[58]:


    s = d1_1_3.to_dict(orient='records')

    # In[59]:


    s

    # 生成数据表

    # In[60]:


    DF = pd.DataFrame(columns=['singleShotGains'], data=[[s]])
    DF['month'] = M

    # In[61]:


    DF

    # 传入数据库

    # In[782]:


    # 定义注释
    table_comment = "公司全景_核心经营指标_单枪充电收入（城市）"
    column_comments = {
        'singleShotGains': '数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_income_gun_city",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # #### 站点类型

    # In[123]:


    d1_1 = DF_Business_Analysis[DF_Business_Analysis['cba_month'].astype(str) == str(M)].copy()
    d1_1['gun'] = d1_1['dc_charge_point_count'].fillna(0) + d1_1['ac_charge_point_count'].fillna(0)

    # In[125]:


    d1_1_1 = d1_1.groupby('station_category')[['rec_data']].sum().reset_index()
    d1_1_2 = d1_1.groupby('station_category')[['gun']].sum().reset_index()
    d1_1_1.columns = ['station_category', 'income']
    d1_1_3 = pd.merge(d1_1_1[['station_category', 'income']], d1_1_2, on='station_category', how='inner')
    d1_1_3 = d1_1_3[d1_1_3['gun'] != 0]
    d1_1_3['单枪充电收入'] = (d1_1_3['income'] / d1_1_3['gun']).round(2)
    d1_1_3 = d1_1_3[['station_category', '单枪充电收入']]
    d1_1_3.sort_values(by='单枪充电收入', ignore_index=True, inplace=True)
    mean = round(d1_1_3['单枪充电收入'].mean(), 2)
    station_category_mean = pd.DataFrame(columns=d1_1_3.columns, data=[['类型平均', mean]])
    d1_1_3 = pd.concat([d1_1_3, station_category_mean])
    d1_1_3['单枪充电收入'] = d1_1_3['单枪充电收入'].astype(float).round(2)
    d1_1_3

    # In[126]:


    DF = bar_chart(d1_1_3, 'station_category', '单枪充电收入（类型）', M)

    # In[127]:


    DF

    # In[128]:


    # 新增计算-算环比变化情况_柱形图加环比情况颜色
    d2_1 = DF_Business_Analysis[DF_Business_Analysis['cba_month'].astype(str) == str(previous_month_str)].copy()
    d2_1['gun'] = d2_1['dc_charge_point_count'].fillna(0) + d2_1['ac_charge_point_count'].fillna(0)

    d2_1_1 = d2_1.groupby('station_category')[['rec_data']].sum().reset_index()
    d2_1_2 = d2_1.groupby('station_category')[['gun']].sum().reset_index()
    d2_1_1.columns = ['station_category', 'income']
    d2_1_3 = pd.merge(d2_1_1[['station_category', 'income']], d2_1_2, on='station_category', how='inner')
    d2_1_3 = d2_1_3[d2_1_3['gun'] != 0]
    d2_1_3['单枪充电收入'] = (d2_1_3['income'] / d2_1_3['gun']).round(2)
    d2_1_3 = d2_1_3[['station_category', '单枪充电收入']]
    mean = round(d2_1_3['单枪充电收入'].mean(), 2)
    station_category_mean = pd.DataFrame(columns=d2_1_3.columns, data=[['类型平均', mean]])
    d2_1_3 = pd.concat([d2_1_3, station_category_mean])
    d2_1_3['单枪充电收入'] = d2_1_3['单枪充电收入'].astype(float).round(2)
    d2_1_3.columns = ['station_category', '上月单枪充电收入']
    d2_1_3

    # In[129]:


    sequential_df = pd.merge(d1_1_3, d2_1_3, how='inner', on='station_category')
    sequential_df['环比情况'] = (sequential_df['单枪充电收入'] - sequential_df['上月单枪充电收入']) / sequential_df['上月单枪充电收入']
    sequential_df

    # In[130]:


    declineValue = []
    riseValue = []
    averageValue = ['类型平均']
    for i in range(sequential_df.shape[0] - 1):
        if sequential_df.iloc[i, -1] >= 0:
            riseValue.append(sequential_df.iloc[i, 0])
        else:
            declineValue.append(sequential_df.iloc[i, 0])
    print(declineValue, riseValue, averageValue)

    # In[131]:


    DF['declineValue'] = json.dumps(declineValue, ensure_ascii=False)
    DF['riseValue'] = json.dumps(riseValue, ensure_ascii=False)
    DF['averageValue'] = json.dumps(averageValue, ensure_ascii=False)
    DF

    # In[132]:


    # 定义注释
    table_comment = "公司全景_核心经营指标_单枪收益（站点类型）"
    column_comments = {
        'singleShotGains': '数据',
        'month': '分析月份'
    }
    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_income_gun_type",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 地图

    # In[788]:


    # 自建站点
    sql = """
    SELECT
    ds.* ,cs.city
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    LEFT JOIN dp_station_low_lat ds ON ds.station_no = cs.station_no 
    WHERE
    rm.plat_access_mode = '电动公司' 
    AND cs.operation_status = '投运'
    """
    DF_SCDD_1 = SQL(sql)
    DF_SCDD_1['type'] = 1
    len(DF_SCDD_1)

    # In[789]:


    # 社会桩
    sql = """
    SELECT 
    ds.*,cs.city
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    LEFT JOIN dp_station_low_lat ds ON ds.station_no = cs.station_no
    where 
    (plat_access_mode in ('三方','社会商户','第三方','第三方单位','第三方合作')
    or plat_access_mode is null
    or (plat_access_mode in ('产业单位','产业单位代运营','代运营','省公司代运营','综合能源') and access_method = '社会站模型'))
    and cs.operation_status ='投运';
    """
    DF_SCDD_2 = SQL(sql)
    DF_SCDD_2['type'] = 2
    len(DF_SCDD_2)

    # In[790]:


    # 产业单位接入
    sql = """
    SELECT 
    ds.*,cs.city
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    LEFT JOIN dp_station_low_lat ds ON ds.station_no = cs.station_no
    where 
    (plat_access_mode in ('产业单位','产业单位代运营','代运营','省公司代运营','综合能源') and access_method != '社会站模型')
    and ((merchant_name not like '%供电公司%' or rm.merchant_name = '国网广元供电公司（产业单位）'))
    and (merchant_name not like '%供电分公司%')
    and cs.operation_status in ('投运');
    """
    DF_SCDD_3 = SQL(sql)
    DF_SCDD_3['type'] = 3
    len(DF_SCDD_3)

    # In[791]:


    # 主业单位接入
    sql = """
    SELECT 
    rm.merchant_name,
    ds.*,cs.city
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    LEFT JOIN dp_station_low_lat ds ON ds.station_no = cs.station_no
    where 
    ((plat_access_mode in ('产业单位','产业单位代运营','代运营','省公司代运营','综合能源') and access_method != '社会站模型')
    and (((merchant_name like '%供电公司%' and rm.merchant_name != '国网广元供电公司（产业单位）'))
    or (merchant_name like '%供电分公司%')))
    and cs.operation_status in ('投运')
    """
    DF_SCDD_4 = SQL(sql)
    DF_SCDD_4['type'] = 4
    len(DF_SCDD_4)

    # In[792]:


    DF_SCDD = pd.concat([DF_SCDD_1, DF_SCDD_2, DF_SCDD_3, DF_SCDD_4])

    # In[793]:


    len(DF_SCDD)

    # In[794]:


    DF_SCDD = DF_SCDD.fillna(0)

    # In[795]:


    DF_SCDD = DF_SCDD[DF_SCDD['lon'] != 0]

    # In[796]:


    len(DF_SCDD)

    # In[797]:


    DF_SCDD = DF_SCDD.drop_duplicates(['lon', 'Lat'])

    # In[798]:


    len(DF_SCDD)

    # In[799]:


    DF_SCDD = DF_SCDD[['station_name', 'city', 'lon', 'Lat', 'type']]

    # In[800]:


    DF_SCDD.head(2)

    # In[801]:


    DF_SCDD

    # In[ ]:


    # In[802]:


    lon_lat = []
    for i in range(len(DF_SCDD)):
        lon_lat.append([DF_SCDD.iloc[i]['lon'], DF_SCDD.iloc[i]['Lat']])

    # In[803]:


    df = pd.DataFrame(columns=['value', 'type'])

    # In[804]:


    len(DF_SCDD[['type']])

    # In[805]:


    df['type'] = DF_SCDD['type']
    df['value'] = lon_lat
    # df['name'] =DF_SCDD['station_name']


    # In[806]:


    DF = pd.DataFrame(columns=['mapData'])

    # In[807]:


    DF['mapData'] = [df.to_dict(orient='records')]

    # In[808]:


    DF['month'] = M

    # In[809]:


    DF

    # In[810]:


    print(DF.iloc[0, 0])

    # In[811]:


    # 定义注释
    table_comment = "公司全景_地图"
    column_comments = {
        'mapData': '地图数据',
        'month': '分析月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_company_map",
        table_comment=table_comment,
        column_comments=column_comments
    )




