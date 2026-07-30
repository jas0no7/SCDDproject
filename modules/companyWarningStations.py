from logs.log_decorator import log_execution
from loguru import logger
from SCDDproject.modules.config import SQL,import_data_with_cursor,Statistical_Time


@log_execution
def runcompanyWarningStations():
    logger.info(f"开始执行公司预警-预警站点页面")

    import pandas as pd
    import numpy as np
    import json
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)

    # 定义计算近三个月函数
    def get_prev_month(month_str):
        """获取前一个月的字符串表示（格式：YYYYMM）"""
        year = int(month_str[:4])
        month = int(month_str[4:])
        if month == 1:
            return f"{year - 1}12"
        else:
            return f"{year}{month - 1:02d}"

    prev1 = get_prev_month(M)  # 前一个月
    prev2 = get_prev_month(prev1)  # 前两个月
    M, prev1, prev2

    # ## 数据导入数据库函数

    # In[7]:

    # In[8]:

    # 定义计算近三个月函数
    def get_prev_month(month_str):
        """获取前一个月的字符串表示（格式：YYYYMM）"""
        year = int(month_str[:4])
        month = int(month_str[4:])
        if month == 1:
            return f"{year - 1}12"
        else:
            return f"{year}{month - 1:02d}"

    prev1 = get_prev_month(M)  # 前一个月
    prev2 = get_prev_month(prev1)  # 前两个月
    recent_three_months = [prev2, prev1, M]
    print(recent_three_months)

    # # 数据读取

    # In[9]:

    # CREATE TABLE `station_cba_org_data` (
    #   `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'id',
    #   `station_no` varchar(100) NOT NULL COMMENT '充电站编码',
    #   `cba_month` varchar(6) NOT NULL COMMENT '分析月份YYYYMM',
    #   `plat_data_charging_count` int(11) DEFAULT NULL COMMENT '平台数据_充电次数',
    #   `plat_data_charging_volume` double DEFAULT NULL COMMENT '平台数据-平台充电量',
    #   `plat_data_elec_fee_revenue` decimal(20,2) DEFAULT NULL COMMENT '平台数据_平台电费收入',
    #   `plat_data_service_revenue` decimal(20,2) DEFAULT NULL COMMENT '平台数据-平台服务费收入',
    #   `rec_data_charging_count` int(11) DEFAULT NULL COMMENT '清分数据_清分充电次数',
    #   `rec_data_charging_volume` double DEFAULT NULL COMMENT '清分数据_清分充电量',
    #   `rec_data_elec_fee_revenue` decimal(20,2) DEFAULT NULL COMMENT '清分数据_清分电费收入',
    #   `rec_data_service_fee_revenue` decimal(20,2) DEFAULT NULL COMMENT '清分数据_清分服务费收入',
    #   `other_revenue_battery_swap_services` decimal(20,2) DEFAULT NULL COMMENT '其它收入_换电服务费',
    #   `other_revenue_op_subsidies` decimal(20,2) DEFAULT NULL COMMENT '其它收入_运营补贴',
    #   `other_revenue_build_subsidies` decimal(20,2) DEFAULT NULL COMMENT '其它收入_建设补贴',
    #   `other_revenue_access_control_barriers` decimal(20,2) DEFAULT NULL COMMENT '其它收入_道闸',
    #   `other_revenue_dr` decimal(20,2) DEFAULT NULL COMMENT '其它收入_需求响应',
    #   `rec_cost_elec_cons` double DEFAULT NULL COMMENT '清分成本_用电电量',
    #   `rec_cost_elec_fee` decimal(20,2) DEFAULT NULL COMMENT '清分成本_用电电费',
    #   `rec_cost_actual_rec_amount` decimal(20,2) DEFAULT NULL COMMENT '清分成本_清分费(实际清分金额)',
    #   `rec_cost_plat_service` decimal(20,2) DEFAULT NULL COMMENT '清分成本_平台服务费',
    #   `rec_cost_rent` decimal(20,2) DEFAULT NULL COMMENT '清分成本_租金',
    #   `om_cost_om` decimal(20,2) DEFAULT NULL COMMENT '运维成本_运维费',
    #   `om_cost_spare_parts` decimal(20,2) DEFAULT NULL COMMENT '运维成本_备件费用',
    #   `om_cost_op_project` decimal(20,2) DEFAULT NULL COMMENT '运维成本_运维项目',
    #   `fin_cost_depreciation` decimal(20,2) DEFAULT NULL COMMENT '财务成本_折旧',
    #   `fin_cost_labor` decimal(20,2) DEFAULT NULL COMMENT '财务成本_人工',
    #   `gross_profit` decimal(20,2) DEFAULT NULL COMMENT '利润',
    #   `analysis_pue` varchar(50) DEFAULT NULL COMMENT '分析_功率利用率',
    #   `analysis_tue` varchar(50) DEFAULT NULL COMMENT '分析_时间利用率',
    #   `analysis_avg_daily_port_energy` varchar(50) DEFAULT NULL COMMENT '分析_单枪日均电量',
    #   `analysis_payback_period` varchar(50) DEFAULT NULL COMMENT '分析_回收周期',
    #   `analysis_elec_cost_per_kwh` varchar(50) DEFAULT NULL COMMENT '分析_每度电电费',
    #   `analysis_service_cost_per_kwh` varchar(50) DEFAULT NULL COMMENT '分析_每度电服务费',
    #   `analysis_asset_loss` varchar(50) DEFAULT NULL COMMENT '分析_资损',
    #   `analysis_elec_loss` varchar(50) DEFAULT NULL COMMENT '分析_损耗_电损',
    #   `analysis_fee_loss` varchar(50) DEFAULT NULL COMMENT '分析_损耗_费损',
    #   `add_time` datetime DEFAULT NULL COMMENT '生成时间',
    #   `meter_account_no` varchar(1000) DEFAULT NULL,
    #   PRIMARY KEY (`id`) USING BTREE,
    #   KEY `idx_station_no` (`station_no`) USING BTREE,
    #   KEY `idx_cba_month` (`cba_month`) USING BTREE
    # ) ENGINE=InnoDB AUTO_INCREMENT=92666 DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC COMMENT='充电站成本效益-原始数据';

    # In[ ]:

    # In[ ]:

    # ## df1-站点基础信息表（含初始投资）

    sql1 = """
    SELECT 
    cs.station_name,
    cs.station_no,
    cs.station_category,
    cs.city,
    cs.operation_status,
    IFNULL(cs.investment_amount,0) as investment_amount,
    cs.commissioning_time,
    IFNULL(cs.station_capacity,0) as station_capacity,
    IFNULL(cs.dc_charge_point_count,0)+IFNULL(cs.ac_charge_point_count,0) as 'charge_count',
    cs.station_address
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

    # In[12]:

    df1['commissioning_year_month'] = df1['commissioning_time'].dt.strftime('%Y%m')
    print('筛选投运时间前：', df1.shape)
    df1 = df1[df1['commissioning_year_month'] <= M]
    print('筛选投运时间后：', df1.shape)

    # In[13]:

    print('当前投运站点：', df1[df1['operation_status'] == '投运'].shape[0])
    print('当前含有初始投资的投运站点：', df1[(df1['operation_status'] == '投运') & df1['investment_amount'] != 0].shape[0])

    # ### 数据类型转换

    # In[14]:

    df1['investment_amount'] = df1['investment_amount'].astype(str).astype(float)
    df1.info()

    # ### 累计投运月份计算

    # In[15]:

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
    df1['commissioning_time'] = df1['commissioning_time'].dt.date
    df1

    # In[16]:

    df1.info()

    # ## df2-站点补贴数据

    # In[17]:

    # ==================注释==================
    # 统计每个站点当前的累计总补贴
    # station_no：站点编号
    # total_subsidy：总补贴
    # ——共96条数据

    # In[18]:

    sql2 = """
    select year,station_no,IFNULL(total_subsidy,0) as total_subsidy from dp_subsidy_NEW;
    """
    df2 = SQL(sql2)
    print(df2.shape)
    print(df2.info())
    df2.head(1)

    # In[19]:

    # 数据类型转换、单位统一为元
    df2['total_subsidy'] = 10000 * df2['total_subsidy'].astype(str).str.replace(',', '').astype(float)

    # In[20]:

    df2_cal = df2.groupby('station_no', as_index=False).agg({'total_subsidy': 'sum'})
    df2_cal.head(1)

    # ## df3-站点运营总收入和总支出

    # In[21]:

    # ==================注释==================
    # 统计四川电动投资金额不为空的每个投运站点的总收入、总支出
    # station_no：站点编号
    # revenue：总收入
    # cost：总支出
    # ——共212条数据

    # In[22]:

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

    # In[23]:

    # 数据类型转换
    df3['revenue'] = df3['revenue'].astype(str).astype(float)
    df3['cost'] = df3['cost'].astype(str).astype(float)
    df3['plat_data_charging_volume'] = df3['plat_data_charging_volume'].astype(str).astype(float)
    df3['rec_cost_elec_cons'] = df3['rec_cost_elec_cons'].astype(str).astype(float)
    df3['rec_data_elec_fee_revenue'] = df3['rec_data_elec_fee_revenue'].astype(str).astype(float)
    df3['rec_data_service_fee_revenue'] = df3['rec_data_service_fee_revenue'].astype(str).astype(float)
    df3['rec_cost_elec_fee'] = df3['rec_cost_elec_fee'].astype(str).astype(float)
    df3.info()

    # In[24]:

    df3_cal = df3.groupby('station_no', as_index=False).agg({'revenue': 'sum',
                                                             'cost': 'sum'})
    df3_cal

    # ## df4-站点租金

    # In[25]:

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

    # In[26]:

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

    # In[27]:

    # 数据类型转换
    df4['parking_fee'] = df4['parking_fee'].astype(str).str.replace(',', '').astype(float)
    df4.info()

    # ## df5-站点累计分成

    # In[28]:

    # ==================注释==================
    # 这里的分成指的是，四川电动旗下站点，分给其他单位的分成
    # station_no：站点编号
    # merchant_profit_amount：站点分成
    # --共352条数据

    # In[29]:

    sql5 = f"""
    select a.station_no,
    b.rec_month,
    sum(IFNULL(b.merchant_profit_amount,0)) as merchant_profit_amount,
    sum(IFNULL(b.dd_profit_amount,0)) as dd_profit_amount
    from 
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

    # In[30]:

    # 数据类型转换
    df5['merchant_profit_amount'] = df5['merchant_profit_amount'].astype(str).str.replace(',', '').astype(float)
    df5['dd_profit_amount'] = df5['dd_profit_amount'].astype(str).str.replace(',', '').astype(float)
    df5.info()

    # In[31]:

    df5_cal = df5.groupby('station_no', as_index=False).agg({'merchant_profit_amount': 'sum'})
    df5_cal.head(1)

    # ## df6-站点运维费用

    # In[32]:

    sql6 = f"""
    select station_no,stat_time,IFNULL(maintenance_cost,0) as maintenance_cost from  dp_station_maintenance_cost1
    where 
    (stat_time <= {M}) and maintenance_cost>0
    group by station_no,stat_time;
    """
    df6 = SQL(sql6)
    print(df6.shape)
    print(df6.info())
    df6.head(1)

    # In[33]:

    # 数据类型转换、单位统一为元
    df6['maintenance_cost'] = 10000 * df6['maintenance_cost'].astype(str).str.replace(',', '').astype(float)

    # In[34]:

    df6_cal = df6.groupby('station_no', as_index=False).agg({'maintenance_cost': 'sum'})
    df6_cal.head(1)

    # ## df7-站点一次成功率数据

    # In[35]:

    sql7 = f"""select station_code,IFNULL(success_rate,0) as success_rate,stat_time from dp_success_rate"""
    df7 = SQL(sql7)
    df7['stat_time'] = df7['stat_time'].str.replace('-', '')
    df7.columns = ['站点编号', '一次成功率', '年月']
    df7

    # ## df8-站点设备可用率

    # In[36]:

    sql8 = """
    select time,station_name,station_code,pile_status,normal_duration,operation_duration,city from dp_operation_duration
    """
    df8 = SQL(sql8)
    df8['年月'] = df8['time'].str[:6]
    df8['可用率'] = df8['normal_duration'].astype('int') / df8['operation_duration'].astype('int')
    df8 = df8[['station_code', '年月', '可用率']]
    df8.columns = ['站点编号', '年月', '设备可用率']
    df8

    # ## df9-站点电价、服务费数据

    # In[37]:

    sql9 = f"""
    select b.station_no,b.cba_month,
    sum(IFNULL(b.rec_data_charging_volume,0)) as '充电量',
    sum(IFNULL(b.rec_data_elec_fee_revenue,0)) as '电费收入',
    sum(IFNULL(b.rec_data_service_fee_revenue,0)) as '服务费收入'
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
    df9 = SQL(sql9)
    # 数据类型转换
    df9['充电量'] = df9['充电量'].astype(str).astype(float)
    df9['电费收入'] = df9['电费收入'].astype(str).astype(float)
    df9['服务费收入'] = df9['服务费收入'].astype(str).astype(float)

    df9['站点充电电费'] = df9['电费收入'] / df9['充电量']
    df9['站点充电服务费'] = df9['服务费收入'] / df9['充电量']
    df9 = df9[['station_no', 'cba_month', '站点充电电费', '站点充电服务费']]
    df9.columns = ['站点编号', '年月', '站点充电电费', '站点充电服务费']
    df9.head(5)

    # ## df10-外部竞争站点电价、服务费数据

    # In[38]:

    sql10 = f"""
    select a.dd_station_id,a.sjg_station_id,b.date,b.electricity_fee,b.service_fee 
    from 
    dp_KeyStations_CompetitorStationsCodeMapping as a
    left join
    dp_ProvincialSupervisionPlatform as b
    on a.sjg_station_id = b.station_id
    where b.date in {tuple(recent_three_months)}
    """
    print(sql10)
    df10 = SQL(sql10)
    df10.columns = ['站点编号', '竞争站点编号', '年月', '竞争站点充电电费', '竞争站点充电服务费']
    df10.info()

    # # 数据合并

    # In[39]:

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

    # In[40]:

    df1.head(1)

    # In[41]:

    df1[df1['operation_status'] == '投运'].shape

    # In[42]:

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

    # In[43]:

    data1 = data1[['station_name', 'station_no', 'station_category',
                   'city', 'operation_status', 'investment_amount',
                   'commissioning_time', '累计投运月份数', '设备折旧进度']]

    # ## 补贴数据合并

    # In[44]:

    # 合并站点补贴数据
    print('含有补贴的站点数量：', df2_cal.shape)
    data2 = pd.merge(data1, df2_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data2.shape)
    print('四川电动投运站点中含有补贴的站点的数量：', data2[data2['total_subsidy'] != 0].shape)
    data2.head(1)

    # ## 运营数据合并

    # In[45]:

    # 合并各站点的运营总投入和总支出
    data3 = pd.merge(data2, df3_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data3.shape)
    print('四川电动投运站点中含有运营数据的站点的数量：', data3[data3['revenue'] != 0].shape)
    data3.head(1)

    # ## 站点租金合并

    # In[46]:

    # 合并站点租金
    data4 = pd.merge(data3, df4, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data4.shape)
    print('四川电动投运站点中含有租金数据的站点的数量：', data4[data4['parking_fee'] != 0].shape)
    data4.head(1)

    # ## 分成数据合并

    # In[47]:

    # 合并站点分成
    data5 = pd.merge(data4, df5_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data5.shape)
    print('四川电动投运站点中含有分成数据的站点的数量：', data5[data5['merchant_profit_amount'] != 0].shape)
    data5.head(1)

    # ## 运维数据合并

    # In[48]:

    # 合并站点运维费
    data6 = pd.merge(data5, df6_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data6.shape)
    print('四川电动投运站点中含有运维数据的站点的数量：', data6[data6['maintenance_cost'] != 0].shape)
    data6.head(1)

    # ## 当年补贴数据合并

    # In[49]:

    df2_year = df2[df2['year'] == str(year) + '年']
    df2_year.columns = ['year', 'station_no', '当年_total_subsidy']
    df2_year = df2_year[['station_no', '当年_total_subsidy']]

    # In[50]:

    data7 = pd.merge(data6, df2_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data7.shape)
    print('四川电动投运站点中含有当年补贴数据的站点的数量：', data7[data7['当年_total_subsidy'] != 0].shape)
    data7.head(1)

    # ## 当年运营收入数据合并

    # In[51]:

    df3.head(1)

    # In[52]:
    df3['cba_month'].replace('None', pd.NA, inplace=True)
    df3.dropna(subset=['cba_month'], inplace=True)
    df3['year'] = df3['cba_month'].astype(str).str[:4].astype(int)
    df3_year = df3[df3['year'] == year]
    df3_year = df3_year.groupby(by='station_no', as_index=False).agg({'revenue': 'sum'})
    df3_year.columns = ['station_no', '当年_revenue']
    df3_year

    # In[53]:

    # 合并当年运营收入
    data8 = pd.merge(data7, df3_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data8.shape)
    print('四川电动投运站点中含有当年运营收入数据的站点的数量：', data8[data8['当年_revenue'] != 0].shape)
    data8.head(1)

    # # 技改站数据合并-特殊处理

    # In[54]:

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

    # In[55]:

    data9.shape

    # In[56]:

    data9[data9['station_no'] == '300003000100019488']

    # # 站点回本进度详情

    # ## 是否回本、滞后回本详情

    # In[57]:

    data9['in'] = data9['total_subsidy'] + data9['revenue']
    data9['out'] = data9['investment_amount'] + data9['cost'] + (data9['parking_fee'] * data9['累计投运月份数']) + data9['merchant_profit_amount'] + data9['maintenance_cost']
    data9['当年_in'] = data9['当年_total_subsidy'] + data9['当年_revenue']
    data9.head(1)

    # In[58]:

    # groupby是因为要加上技改站的数据
    data10 = data9.groupby(by=['station_no'], as_index=False).agg({'station_name': 'max',
                                                                   'city': 'max',
                                                                   'station_category': 'max',
                                                                   'investment_amount': 'sum',
                                                                   'out': 'sum',
                                                                   'in': 'sum',
                                                                   '设备折旧进度': 'max',
                                                                   '当年_in': 'sum'
                                                                   })
    data10['设备折旧进度'] = round(data10['设备折旧进度'], 4) * 100
    data10['静态资金回本进度'] = round(data10['in'] / data10['out'], 4) * 100
    data10['当年静态资金回本进度'] = round(data10['当年_in'] / data10['out'], 4) * 100
    data10['回本滞后率'] = data10['设备折旧进度'] - data10['静态资金回本进度']
    data10.head(1)

    # In[59]:

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

    # In[60]:

    data10.groupby(by='回本状态标签').agg({'station_no': 'count'})

    # ## 超预期回本详情

    # In[61]:

    no_list = data10[data10['静态资金回本进度'] >= 100]['station_no'].to_list()
    for i in no_list:
        # 技改数据特殊处理
        if i == '300003000100019488':
            x1 = df1[df1['station_no'].isin(['300003000100019488', '300003013200108'])]
        elif i == '300003000100017539':
            x1 = df1[df1['station_no'].isin(['300003000100017539', '300003000100002472'])]
        elif i == '300003000100017538':
            x1 = df1[df1['station_no'].isin(['300003000100017538', '300003000100002473'])]
        elif i == '300003000100019487':
            x1 = df1[df1['station_no'].isin(['300003000100019487', '300003013200011', '300003013200099'])]
        else:
            x1 = df1[df1['station_no'] == i]
        # 生成站点从投运开始的年月码表
        x1 = x1[['station_no', 'commissioning_time']]
        end_year = int(M[:4])
        end_month = int(M[4:])
        end_date = pd.Timestamp(end_year, end_month, 1)
        x2_data = []  # 存储结果的列表
        for _, row in x1.iterrows():  # 遍历x1的每一行
            station = row['station_no']
            start_date = row['commissioning_time']
            current = pd.Timestamp(start_date.year, start_date.month, 1)  # 生成从开始月份到截止月份的所有月份
            while current <= end_date:
                x2_data.append({
                    'station_no': station,
                    'month': current.strftime('%Y%m')
                })  # 格式化为'YYYYMM'并添加到列表
                if current.month == 12:
                    current = pd.Timestamp(current.year + 1, 1, 1)  # 移动到下个月
                else:
                    current = pd.Timestamp(current.year, current.month + 1, 1)
        x2 = pd.DataFrame(x2_data)  # 转换为数据框

        # 初始投资金额合并
        x2 = pd.merge(x2, df1[['station_no', 'investment_amount']], how='left', on='station_no')

        # 补贴数据合并-按年月拆分
        x2['year'] = x2['month'].astype(str).str[:4]  # 提取年份数据
        df2['year_1'] = df2['year'].astype(str).str[:4]  # 提取年份数据
        x3 = pd.merge(x2, df2, how='left', left_on=['station_no', 'year'], right_on=['station_no', 'year_1']).fillna(0)
        x3 = x3[['station_no', 'month', 'total_subsidy', 'year_x', 'investment_amount']]
        x3.columns = ['station_no', 'month', 'total_subsidy', 'year', 'investment_amount']
        x3_gb1 = x3.groupby(by=['station_no', 'year'], as_index=False).agg({'month': 'count',
                                                                            'total_subsidy': 'max',
                                                                            'investment_amount': 'max'})
        x3_gb1['total_subsidy_month'] = x3_gb1['total_subsidy'] / x3_gb1['month']
        x4 = pd.merge(x3[['station_no', 'year', 'month', 'investment_amount']],
                      x3_gb1[['station_no', 'year', 'total_subsidy_month']], how='left', on=['station_no', 'year'])

        # 站点运营收入和支出数据合并
        x5 = pd.merge(x4, df3, how='left', left_on=['station_no', 'month'], right_on=['station_no', 'cba_month'])

        # 站点租金数据合并
        x6 = pd.merge(x5, df4, how='left', on='station_no').fillna(0)

        # 站点分成数据合并
        x7 = pd.merge(x6, df5, how='left', left_on=['station_no', 'month'], right_on=['station_no', 'rec_month']).fillna(0)

        # 站点运维数据合并
        x8 = pd.merge(x7, df6, how='left', left_on=['station_no', 'month'], right_on=['station_no', 'stat_time']).fillna(0)

        # 站点每月的总收入和总支出
        x8['月总收入'] = x8['total_subsidy_month'] + x8['revenue']
        x8['月总支出'] = x8['cost'] + x8['parking_fee'] + x8['merchant_profit_amount'] + x8['maintenance_cost']

        # 算累计，还要加上初始投资金额
        x8['当月累计收入'] = x8['月总收入'].cumsum()
        x8['当月累计支出'] = x8['月总支出'].cumsum()
        x8['当月累计支出(含初始投资)'] = x8['当月累计支出'] + x8['investment_amount']

        # 技改站数据特殊合并
        x9 = x8.groupby(by=['station_no', 'month'], as_index=False).agg({'当月累计支出(含初始投资)': 'sum',
                                                                         '当月累计收入': 'sum'})
        x9['是否回本'] = '否'
        x9.loc[x9['当月累计支出(含初始投资)'] <= x9['当月累计收入'], '是否回本'] = '是'

        # 判断回本周期是否超过5年
        for j in range(x9.shape[0]):
            if x9.loc[j, '是否回本'] == '是':
                continue
        if j < (5 * 12):  # 如果小于
            data10.loc[data10['station_no'] == i, '回本类型标签'] = '超预期回本'

            # In[62]:

    data10.groupby(by='回本类型标签').agg({'station_no': 'count'})

    # In[63]:

    data10.columns = ['站点编号', '站点名称', '所属区域',
                      '站点类型', '总投资（万元）', '总成本（万元）',
                      '总收入（万元）', '设备折旧进度（%）', '今年总收入（万元）',
                      '静态投资回本进度（%）', '今年静态投资回本进度（%）',
                      '回本滞后率（%）', '回本状态标签', '回本类型标签']

    # ## 数据统一保留两位小数处理

    # In[64]:

    # 将金额的数据全部转换为万元
    data10['总投资（万元）'] = round(data10['总投资（万元）'] / 10000, 2)
    data10['总成本（万元）'] = round(data10['总成本（万元）'] / 10000, 2)
    data10['总收入（万元）'] = round(data10['总收入（万元）'] / 10000, 2)
    data10['今年总收入（万元）'] = round(data10['今年总收入（万元）'] / 10000, 2)

    # 全部转换为两位小数
    data10['总投资（万元）'] = (data10['总投资（万元）'] * 100).round().astype(int) / 100
    data10['总成本（万元）'] = (data10['总成本（万元）'] * 100).round().astype(int) / 100
    data10['总收入（万元）'] = (data10['总收入（万元）'] * 100).round().astype(int) / 100
    data10['设备折旧进度（%）'] = (data10['设备折旧进度（%）'] * 100).round().astype(int) / 100
    data10['今年总收入（万元）'] = (data10['今年总收入（万元）'] * 100).round().astype(int) / 100
    data10['静态投资回本进度（%）'] = (data10['静态投资回本进度（%）'] * 100).round().astype(int) / 100
    data10['今年静态投资回本进度（%）'] = (data10['今年静态投资回本进度（%）'] * 100).round().astype(int) / 100
    data10['回本滞后率（%）'] = (data10['回本滞后率（%）'] * 100).round().astype(int) / 100

    # In[65]:

    data10.head(1)

    # # 预警站点数据详情

    # In[66]:

    data11 = data10[data10['回本类型标签'] == '滞后未回本']
    print('预警站点总数：', data11.shape[0])

    # # 顶部表格

    # ## 数据计算

    # In[67]:

    # 预警站点基础信息合并
    a1 = data11[['站点名称', '站点编号', '静态投资回本进度（%）', '总投资（万元）']]
    a2 = df1[['station_no', 'station_address', 'station_category', 'station_capacity']]
    a2.columns = ['站点编号', '站点地址', '站点类型', '站点容量']
    d1 = pd.merge(a1, a2, how='left', on='站点编号')
    d1['单瓦造价'] = round((d1['总投资（万元）'] * 10000) / (d1['站点容量'] * 1000), 2)

    # 预警站点当月运营数据合并
    a3 = df3[df3['cba_month'] == M][['station_no', 'rec_data_elec_fee_revenue', 'rec_data_service_fee_revenue', 'rec_cost_elec_fee']]
    a3.columns = ['站点编号', '电费收入', '服务费收入', '电费支出']
    d2 = pd.merge(d1, a3, how='left', on='站点编号')

    # 服务费分成数据合并
    a4 = df5[df5['rec_month'] == M][['station_no', 'merchant_profit_amount']]
    a4.columns = ['站点编号', '分成']
    d3 = pd.merge(d2, a4, how='left', on='站点编号').fillna(0)

    # 租金数据合并
    a5 = df4.copy()
    a5.columns = ['站点编号', '租金']
    d4 = pd.merge(d3, a5, how='left', on='站点编号').fillna(0)

    # 运维费数据合并
    a6 = df6[df6['stat_time'] == M][['station_no', 'maintenance_cost']]
    a6.columns = ['站点编号', '运维费']
    d5 = pd.merge(d4, a6, how='left', on='站点编号').fillna(0)

    # 总收入及占比
    d5['总收入'] = d5['电费收入'] + d5['服务费收入']
    d5['电费收入占比'] = round((d5['电费收入'] / d5['总收入']) * 100, 2)
    d5['服务费收入占比'] = round((d5['服务费收入'] / d5['总收入']) * 100, 2)

    # 总支出及占比
    d5['总支出'] = d5['电费支出'] + d5['分成'] + d5['租金'] + d5['运维费']
    d5['服务费分成/场地租金'] = d5['分成'] + d5['租金']
    d5['电费支出占比'] = round((d5['电费支出'] / d5['总支出']) * 100, 2)
    d5['服务费分成/场地租金占比'] = round((d5['服务费分成/场地租金'] / d5['总支出']) * 100, 2)
    d5['运维费占比'] = round((d5['运维费'] / d5['总支出']) * 100, 2)
    d5 = d5.fillna(0)
    d6 = d5[['站点编号', '站点名称', '站点类型',
             '站点地址', '总投资（万元）', '单瓦造价',
             '静态投资回本进度（%）', '电费收入', '电费收入占比',
             '服务费收入', '服务费收入占比',
             '电费支出', '电费支出占比',
             '服务费分成/场地租金', '服务费分成/场地租金占比',
             '运维费', '运维费占比']]
    d6.head(2)

    # ## 前端格式转换

    # In[68]:

    # 提取去重后的站点名称筛选列表
    site_name_filters = d6['站点名称'].drop_duplicates().tolist()
    print('site_name_filters：\n', site_name_filters)
    # 提取去重后的站点类型筛选列表
    site_type_filters = d6['站点类型'].drop_duplicates().tolist()
    print('site_type_filters：\n', site_type_filters)

    # In[69]:

    Database_Table1 = d6.copy()
    Database_Table1['siteNameFilters'] = [site_name_filters] * Database_Table1.shape[0]
    Database_Table1['siteTypeFilters'] = [site_type_filters] * Database_Table1.shape[0]
    Database_Table1['month'] = [M] * Database_Table1.shape[0]

    # 重命名
    Database_Table1.columns = ['siteNum', 'siteName', 'siteType',
                               'siteAddress', 'totalInvestment', 'singleWattCost',
                               'recoveryProgress', 'electricityRevenueAmount', 'electricityRevenuePercentage',
                               'serviceChargeAmount', 'serviceChargePercentage',
                               'electricityBillsAmount', 'electricityBillsPercentage',
                               'venueRentalAmount', 'venueRentalPercentage', 'oMAmount', 'oMPercentage',
                               'siteNameFilters', 'siteTypeFilters', 'month']
    Database_Table1.head(2)

    # ## 数据存储

    # In[70]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警站点页_顶部表格数据"
    column_comments = {
        'siteNum': '站点编号',
        'siteName': '站点名称',
        'siteType': '站点类型',
        'siteAddress': '站点地址',
        'totalInvestment': '总投资',
        'singleWattCost': '单瓦造价',
        'recoveryProgress': '静态投资回本进度',
        'electricityRevenueAmount': '当月收入-电费收入-金额',
        'electricityRevenuePercentage': '当月收入-电费收入-占比',
        'serviceChargeAmount': '当月收入-服务费收入-金额',
        'serviceChargePercentage': '当月收入-服务费收入-占比',
        'electricityBillsAmount': '当月成本-电费支出-金额',
        'electricityBillsPercentage': '当月成本-电费支出-占比',
        'venueRentalAmount': '当月成本-服务费成分/场地租金-金额',
        'venueRentalPercentage': '当月成本-服务费成分/场地租金-占比',
        'oMAmount': '当月成本-运维费-金额',
        'oMPercentage': '当月成本-运维费-占比',
        'siteNameFilters': '站点名称筛选',
        'siteTypeFilters': '站点类型筛选',
        'month': '分析年月'
    }
    Database_Table1 = Database_Table1.replace([np.inf, -np.inf], 0).replace({np.nan: None})

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table1,
        table_name="dp_WarningSite_TopTable",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # # 累计站点回本情况

    # ## 数据计算

    # In[71]:

    d1 = data11[['站点编号', '静态投资回本进度（%）', '设备折旧进度（%）', '回本滞后率（%）']]
    d1.columns = ['站点编号', '静态投资回本进度', '设备折旧进度', '回本滞后率']
    d1.reset_index(drop=True, inplace=True)
    d1.head(2)

    # In[72]:

    def create_pie_data(row):
        # 构建 pieChartData 列表
        pie_data = [
            {"value": f"{row['静态投资回本进度']}", "name": "静态投资回本进度"},
            {"value": f"{row['设备折旧进度']}", "name": "设备折旧进度"},
            {"value": f"{row['回本滞后率']}", "name": "回本滞后率"}
        ]
        # 转换为 JSON 格式字符串
        return json.dumps(pie_data, ensure_ascii=False)

    # 创建新数据框
    Database_Table2 = pd.DataFrame()
    Database_Table2['siteNum'] = d1['站点编号']
    Database_Table2['pieChartData'] = d1.apply(create_pie_data, axis=1)
    Database_Table2['month'] = M
    Database_Table2

    # ## 数据存储

    # In[73]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警站点页_站点回本情况_三个环形图数据"
    column_comments = {
        'siteNum': '站点编号',
        'pieChartData': '绘图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table2,
        table_name="dp_WarningSite_CostRecoveryStatus",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # # 问题诊断

    # In[74]:

    # 定义函数计算同类型同规模的指标均值
    def calculate_similar_avg(row, df, col):
        """
        row:用作映射每一行
        df:具体计算的原始数据框
        col:具体计算的列名
        """
        # 当前站点的类型和容量
        current_type = row['站点类型']
        current_capacity = row['站点容量']
        current_id = row['站点编号']

        # 计算容量的20%范围
        lower_bound = current_capacity * 0.8
        upper_bound = current_capacity * 1.2

        # 筛选同类型且容量在范围内的站点
        mask = (df['站点类型'] == current_type) & \
               (df['站点容量'] >= lower_bound) & \
               (df['站点容量'] <= upper_bound)
        #     & \(df['站点编号'] != current_id)  # 排除当前站点自身

        # 计算这些站点的单瓦造价平均值
        similar_stations = df[mask]
        return similar_stations[col].mean()

    # In[75]:

    # 定义函数计算同类型同规模站点在对应年月的指标平均值（排除自身）
    # 作用于需要对比近三个月数据的情况
    def calculate_similar_ratio_mean(row, df, col):
        # 获取当前行的关键信息
        current_id = row['站点编号']
        current_type = row['站点类型']
        current_capacity = row['站点容量']
        current_yearmonth = row['年月']

        # 计算容量的20%范围（80%-120%）
        lower_bound = current_capacity * 0.8
        upper_bound = current_capacity * 1.2

        # 筛选条件：同类型、同规模范围、同年月、不同站点编号（排除自身）
        mask = (df['站点类型'] == current_type) & \
               (df['站点容量'] >= lower_bound) & \
               (df['站点容量'] <= upper_bound) & \
               (df['年月'] == current_yearmonth)
        #     & \(df['站点编号'] != current_id)

        # 筛选符合条件的站点
        similar_stations = df[mask]

        # 计算平均值，若没有符合条件的站点则返回NaN
        if len(similar_stations) > 0:
            return similar_stations[col].mean()
        else:
            return 0

    # ## 投资维度

    # In[76]:

    a1 = data10[['站点编号', '总投资（万元）']]
    a2 = df1[['station_no', 'station_category', 'station_capacity']]
    a2.columns = ['站点编号', '站点类型', '站点容量']
    Station_Data1 = pd.merge(a1, a2, how='left', on='站点编号')
    Station_Data1['单瓦造价'] = round((Station_Data1['总投资（万元）'] * 10000) / (Station_Data1['站点容量'] * 1000), 2)
    Station_Data1

    # In[77]:

    # 复制数据到Station_Data2
    Station_Data2 = Station_Data1.copy()

    # 应用函数，为每个站点计算平均值并添加到新列
    Station_Data2['同类型同规模单瓦造价平均值'] = Station_Data2.apply(
        lambda row: calculate_similar_avg(row, Station_Data1, '单瓦造价'), axis=1
    )
    # 添加"是否高于平均值"列
    Station_Data2['单瓦造价是否高于平均水平'] = Station_Data2.apply(
        lambda row: '是' if row['单瓦造价'] > row['同类型同规模单瓦造价平均值'] else '否',
        axis=1
    )
    # 显示结果
    Station_Data2

    # ## 运维维度

    # In[78]:

    a1 = df6[df6['stat_time'] == '202504'][['station_no', 'maintenance_cost']]
    a1.columns = ['站点编号', '运维费']
    Station_Data3 = pd.merge(Station_Data2, a1, how='left').fillna(0)
    Station_Data3['单瓦运维成本'] = round(Station_Data3['运维费'] / Station_Data3['站点容量'], 2)
    Station_Data3

    # In[79]:

    # 复制数据到Station_Data2
    Station_Data4 = Station_Data3.copy()

    # 应用函数，为每个站点计算平均值并添加到新列
    Station_Data4['同类型同规模单瓦运维成本均值'] = Station_Data4.apply(
        lambda row: calculate_similar_avg(row, Station_Data4, '单瓦运维成本'), axis=1
    )
    # 添加"是否高于平均值"列
    Station_Data4['单瓦运维成本是否高于平均值'] = Station_Data4.apply(
        lambda row: '是' if row['单瓦运维成本'] > row['同类型同规模单瓦运维成本均值'] else '否',
        axis=1
    )
    # 显示结果
    Station_Data4

    # ## 设备维度

    # ### 一次成功率

    # In[80]:

    sd1 = Station_Data4[['站点编号', '站点类型', '站点容量']]
    # 重复原数据框行，每个站点重复3次（对应3个年月）
    sd1_repeated = sd1.loc[np.repeat(sd1.index, len(recent_three_months))].reset_index(drop=True)
    # 创建年月列，按列表顺序循环赋值
    sd1_repeated['年月'] = np.tile(recent_three_months, len(sd1))
    # 得到目标数据框sd2,即每个站点编号对应3个年月的行
    sd2 = sd1_repeated

    # 合并各站点编号、年月对应的站点类型
    sd4 = pd.merge(sd2, df7, how='left', on=['站点编号', '年月']).fillna(0)

    # 将数据转换为数值型
    sd4['一次成功率'] = sd4['一次成功率'].astype(str).str.replace('%', '').astype(float, errors='ignore')
    sd4['一次成功率'] = round(sd4['一次成功率'], 2)

    # 筛选近三个月的数据
    sd5 = sd4[sd4['年月'].isin(recent_three_months)].copy()  # recent_three_months由前面定义好的函数生成，为最近三个月的月份

    # 由于一次成功率的数据是按桩统计的，故这里按照站点需要求平均值
    sd6 = sd5.groupby(by=['站点编号', '站点类型', '年月'], as_index=False).agg({'一次成功率': 'mean'})
    sd6['是否低于95%'] = '否'
    sd6.loc[sd6['一次成功率'] < 95, '是否低于95%'] = '是'

    sd7 = sd6[sd6['是否低于95%'] == '是'].groupby(by='站点编号', as_index=False).agg({'是否低于95%': 'count'})
    sd7['一次成功率是否连续三月低于指标'] = '否'
    sd7.loc[sd7['是否低于95%'] == 3, '一次成功率是否连续三月低于指标'] = '是'

    sd8 = pd.merge(sd6, sd7[['站点编号', '一次成功率是否连续三月低于指标']], how='left', on='站点编号')
    sd8.loc[sd8['一次成功率是否连续三月低于指标'].isna(), '一次成功率是否连续三月低于指标'] = '否'
    sd8.info()

    # In[81]:

    Station_Data5 = pd.merge(Station_Data4, sd8[sd8['年月'] == M][['站点编号',
                                                                 '一次成功率',
                                                                 '是否低于95%',
                                                                 '一次成功率是否连续三月低于指标']],
                             how='left', on='站点编号').fillna(0)
    Station_Data5['设备一次成功率指标'] = 95
    Station_Data5

    # ### 设备可用率

    # In[82]:

    sd1 = Station_Data5[['站点编号', '站点类型', '站点容量']]
    # 重复原数据框行，每个站点重复3次（对应3个年月）
    sd1_repeated = sd1.loc[np.repeat(sd1.index, len(recent_three_months))].reset_index(drop=True)
    # 创建年月列，按列表顺序循环赋值
    sd1_repeated['年月'] = np.tile(recent_three_months, len(sd1))
    # 得到目标数据框sd2,即每个站点编号对应3个年月的行
    sd2 = sd1_repeated

    # 合并各站点编号对应的站点类型
    sd4 = pd.merge(sd2, df8, how='left', on=['站点编号', '年月']).fillna(0)

    # 将数据转换为数值型
    sd4['设备可用率'] = sd4['设备可用率'] * 100
    sd4['设备可用率'] = round(sd4['设备可用率'], 2)

    # 筛选近三个月的数据
    sd5 = sd4[sd4['年月'].isin(recent_three_months)].copy()

    # 确认设备可用率的数据是按站统计的
    sd6 = sd5.groupby(by=['站点编号', '站点类型', '年月'], as_index=False).agg({'设备可用率': 'mean'})
    sd6['是否低于99%'] = '否'
    sd6.loc[sd6['设备可用率'] < 99, '是否低于99%'] = '是'

    sd7 = sd6[sd6['是否低于99%'] == '是'].groupby(by='站点编号', as_index=False).agg({'是否低于99%': 'count'})
    sd7['设备可用率是否连续三月低于指标'] = '否'
    sd7.loc[sd7['是否低于99%'] == 3, '设备可用率是否连续三月低于指标'] = '是'

    sd8 = pd.merge(sd6, sd7[['站点编号', '设备可用率是否连续三月低于指标']], how='left', on='站点编号')
    sd8.loc[sd8['设备可用率是否连续三月低于指标'].isna(), '设备可用率是否连续三月低于指标'] = '否'
    sd8.info()

    # In[83]:

    Station_Data6 = pd.merge(Station_Data5, sd8[sd8['年月'] == M][['站点编号',
                                                                 '设备可用率',
                                                                 '是否低于99%',
                                                                 '设备可用率是否连续三月低于指标']],
                             how='left', on='站点编号').fillna(0)
    Station_Data6['设备可用率指标'] = 99
    Station_Data6

    # ## 场地分成维度

    # In[84]:

    sd1 = Station_Data6[['站点编号', '站点类型', '站点容量']]
    # 重复原数据框行，每个站点重复3次（对应3个年月）
    sd1_repeated = sd1.loc[np.repeat(sd1.index, len(recent_three_months))].reset_index(drop=True)
    # 创建年月列，按列表顺序循环赋值
    sd1_repeated['年月'] = np.tile(recent_three_months, len(sd1))
    # 得到目标数据框sd2,即每个站点编号对应3个年月的行
    sd2 = sd1_repeated

    # 获取分成数据
    sd3 = df5.copy()
    sd3.columns = ['站点编号', '年月', '商户分成', '电动公司分成']
    sd3['站点场地其它商户分成占比'] = sd3['商户分成'] / (sd3['商户分成'] + sd3['电动公司分成'])
    sd3['站点场地其它商户分成占比'] = round(sd3['站点场地其它商户分成占比'], 2)

    # 合并各站点编号、年月对应的站点分成数据
    sd4 = pd.merge(sd2, sd3[['站点编号', '年月', '站点场地其它商户分成占比']], how='left', on=['站点编号', '年月']).fillna(0)

    # 筛选近三个月的数据
    sd5 = sd4[sd4['年月'].isin(recent_three_months)].copy()
    sd5 = sd5.replace(-np.inf, 0)

    # 复制df5到sd6
    sd6 = sd5.copy()
    # 应用函数计算平均值并新增到sd6
    sd6['同类型同规模其他商户分成占比均值'] = sd6.apply(lambda row: calculate_similar_ratio_mean(row, sd5, '站点场地其它商户分成占比'), axis=1)
    sd6

    # In[85]:

    sd6['分成是否高于平均值'] = '否'
    sd6.loc[sd6['站点场地其它商户分成占比'] > sd6['同类型同规模其他商户分成占比均值'], '分成是否高于平均值'] = '是'

    sd7 = sd6[sd6['分成是否高于平均值'] == '是'].groupby(by='站点编号', as_index=False).agg({'分成是否高于平均值': 'count'})
    sd7['分成是否连续三月高于指标'] = '否'
    sd7.loc[sd7['分成是否高于平均值'] == 3, '分成是否连续三月高于指标'] = '是'

    sd8 = pd.merge(sd6[sd6['年月'] == M], sd7[['站点编号', '分成是否连续三月高于指标']], how='left', on='站点编号')
    sd8.loc[sd8['分成是否连续三月高于指标'].isna(), '分成是否连续三月高于指标'] = '否'

    Station_Data7 = pd.merge(Station_Data6, sd8[['站点编号', '站点场地其它商户分成占比',
                                                 '同类型同规模其他商户分成占比均值',
                                                 '分成是否高于平均值', '分成是否连续三月高于指标']],
                             how='left', on='站点编号').fillna(0)
    Station_Data7

    # ## 损耗维度

    # In[86]:

    sd1 = Station_Data7[['站点编号', '站点类型', '站点容量']]
    # 重复原数据框行，每个站点重复3次（对应3个年月）
    sd1_repeated = sd1.loc[np.repeat(sd1.index, len(recent_three_months))].reset_index(drop=True)
    # 创建年月列，按列表顺序循环赋值
    sd1_repeated['年月'] = np.tile(recent_three_months, len(sd1))
    # 得到目标数据框sd2,即每个站点编号对应3个年月的行
    sd2 = sd1_repeated

    sd3 = df3[['station_no', 'cba_month', 'plat_data_charging_volume', 'rec_cost_elec_cons']].copy()
    sd3.columns = ['站点编号', '年月', '平台充电量', '用电电量']
    # sd3.to_excel('./电损数据核查.xlsx')
    sd3['电损'] = 1 - (sd3['平台充电量'] / sd3['用电电量'])

    sd3 = sd3.fillna(0)
    # 剔除电损异常值
    sd3 = sd3[(sd3['电损'] > 0) & (sd3['电损'] < 1)]
    sd3['电损'] = round(sd3['电损'], 4)

    # 合并各站点编号对应的站点类型
    sd4 = pd.merge(sd2, sd3[['站点编号', '年月', '电损']], how='left', on=['站点编号', '年月']).fillna(0)

    # 筛选近三个月的数据
    sd5 = sd4[sd4['年月'].isin(recent_three_months)].copy()
    sd5 = sd5.replace(-np.inf, 0)

    # 复制df5到sd6
    sd6 = sd5.copy()
    # 应用函数计算平均值并新增到sd6
    sd6['同类型同规模站点电损均值'] = sd6.apply(lambda row: calculate_similar_ratio_mean(row, sd5, '电损'), axis=1)
    sd6

    # In[87]:

    sd6['电损是否高于平均值'] = '否'
    sd6.loc[sd6['电损'] > sd6['同类型同规模站点电损均值'], '电损是否高于平均值'] = '是'

    sd7 = sd6[sd6['电损是否高于平均值'] == '是'].groupby(by='站点编号', as_index=False).agg({'电损是否高于平均值': 'count'})
    sd7['电损是否连续三月高于指标'] = '否'
    sd7.loc[sd7['电损是否高于平均值'] == 3, '电损是否连续三月高于指标'] = '是'

    sd8 = pd.merge(sd6[sd6['年月'] == M], sd7[['站点编号', '电损是否连续三月高于指标']], how='left', on='站点编号')
    sd8.loc[sd8['电损是否连续三月高于指标'].isna(), '电损是否连续三月高于指标'] = '否'

    Station_Data8 = pd.merge(Station_Data7, sd8[['站点编号', '电损',
                                                 '同类型同规模站点电损均值',
                                                 '电损是否高于平均值', '电损是否连续三月高于指标']],
                             how='left', on='站点编号').fillna(0)
    Station_Data8

    # In[88]:

    Station_Data8.info()

    # ## 市场价格维度

    # In[89]:

    a1 = df9[df9['年月'].isin(recent_three_months)].copy()
    a2 = df10[df10['年月'].isin(recent_three_months)].copy()
    sd1 = pd.merge(Station_Data8[['站点编号', '站点类型', '站点容量']], a1, how='left', on='站点编号')
    sd2 = pd.merge(sd1, a2, how='left', on=['站点编号', '年月'])
    sd2

    # In[90]:

    sd2.info()

    # ### 充电电费

    # In[91]:

    # 基础数据获取
    sd3 = sd2[['站点编号', '竞争站点编号', '站点类型', '站点容量', '年月', '站点充电电费', '竞争站点充电电费']]

    # 计算外部竞争的对比均值
    sd4 = sd3[sd3['竞争站点编号'].notna()]
    sd4 = sd4.groupby(by=['站点编号', '年月'], as_index=False).agg({'竞争站点充电电费': 'mean'})
    sd4.columns = ['站点编号', '年月', '充电电费对比均值']
    sd4['充电电费对比均值'] = round(sd4['充电电费对比均值'], 2)

    sd4['充电电费对比类型'] = '外部竞争'

    # 应用函数计算同类型同规模平均值并新增到sd5
    sd5 = sd3.copy()
    sd5['同类型同规模站点充电电费均值'] = sd5.apply(lambda row: calculate_similar_ratio_mean(row, sd5, '站点充电电费'), axis=1)
    sd5 = sd5[sd5['竞争站点编号'].isna()][['年月', '站点编号', '同类型同规模站点充电电费均值']]
    sd5.columns = ['年月', '站点编号', '充电电费对比均值']
    sd5['充电电费对比均值'] = round(sd5['充电电费对比均值'], 2)

    sd5['充电电费对比类型'] = '同类型同规模'

    # 生成用于合并数据的码表
    sd6 = sd3[['站点编号', '站点类型', '站点容量', '年月', '站点充电电费']].drop_duplicates()
    sd6['站点充电电费'] = round(sd6['站点充电电费'], 2)

    # 将对比数据合并
    sd7 = pd.concat([sd4, sd5], axis=0)

    # 合并为可计算的表
    sd8 = pd.merge(sd6, sd7, how='left', on=['站点编号', '年月'])
    sd8

    # In[92]:

    sd8['站点充电电费是否高于平均值'] = '否'
    sd8.loc[sd8['站点充电电费'] > sd8['充电电费对比均值'], '站点充电电费是否高于平均值'] = '是'

    sd9 = sd8[sd8['站点充电电费是否高于平均值'] == '是'].groupby(by='站点编号', as_index=False).agg({'站点充电电费是否高于平均值': 'count'})
    sd9['充电电费是否连续三月高于指标'] = '否'
    sd9.loc[sd9['站点充电电费是否高于平均值'] == 3, '站点充电电费是否连续三月高于指标'] = '是'

    sd10 = pd.merge(sd8[sd8['年月'] == M], sd9[['站点编号', '站点充电电费是否连续三月高于指标']], how='left', on='站点编号')
    sd10.loc[sd10['站点充电电费是否连续三月高于指标'].isna(), '站点充电电费是否连续三月高于指标'] = '否'

    Station_Data9 = pd.merge(Station_Data8, sd10[['站点编号', '站点充电电费', '充电电费对比类型',
                                                  '充电电费对比均值',
                                                  '站点充电电费是否高于平均值',
                                                  '站点充电电费是否连续三月高于指标']],
                             how='left', on='站点编号').fillna(0)
    Station_Data9

    # ### 充电服务费

    # In[93]:

    sd2.head(1)

    # In[94]:

    # 基础数据获取
    sd3 = sd2[['站点编号', '竞争站点编号', '站点类型', '站点容量', '年月', '站点充电服务费', '竞争站点充电服务费']]

    # 计算外部竞争的对比均值
    sd4 = sd3[sd3['竞争站点编号'].notna()]
    sd4 = sd4.groupby(by=['站点编号', '年月'], as_index=False).agg({'竞争站点充电服务费': 'mean'})
    sd4.columns = ['站点编号', '年月', '充电服务费对比均值']
    sd4['充电服务费对比类型'] = '外部竞争'
    sd4['充电服务费对比均值'] = round(sd4['充电服务费对比均值'], 2)

    # 应用函数计算同类型同规模平均值并新增到sd5
    sd5 = sd3.copy()
    sd5['同类型同规模站点充电服务费均值'] = sd5.apply(lambda row: calculate_similar_ratio_mean(row, sd5, '站点充电服务费'), axis=1)
    sd5 = sd5[sd5['竞争站点编号'].isna()][['年月', '站点编号', '同类型同规模站点充电服务费均值']]
    sd5.columns = ['年月', '站点编号', '充电服务费对比均值']
    sd5['充电服务费对比类型'] = '同类型同规模'
    sd5['充电服务费对比均值'] = round(sd5['充电服务费对比均值'], 2)

    # 生成用于合并数据的码表
    sd6 = sd3[['站点编号', '站点类型', '站点容量', '年月', '站点充电服务费']].drop_duplicates()
    sd6['站点充电服务费'] = round(sd6['站点充电服务费'], 2)

    # 将对比数据合并
    sd7 = pd.concat([sd4, sd5], axis=0)

    # 合并为可计算的表
    sd8 = pd.merge(sd6, sd7, how='left', on=['站点编号', '年月'])
    sd8

    # In[95]:

    sd8['站点充电服务费是否高于平均值'] = '否'
    sd8.loc[sd8['站点充电服务费'] > sd8['充电服务费对比均值'], '站点充电服务费是否高于平均值'] = '是'

    sd9 = sd8[sd8['站点充电服务费是否高于平均值'] == '是'].groupby(by='站点编号', as_index=False).agg({'站点充电服务费是否高于平均值': 'count'})
    sd9['充电服务费是否连续三月高于指标'] = '否'
    sd9.loc[sd9['站点充电服务费是否高于平均值'] == 3, '站点充电服务费是否连续三月高于指标'] = '是'

    sd10 = pd.merge(sd8[sd8['年月'] == M], sd9[['站点编号', '站点充电服务费是否连续三月高于指标']], how='left', on='站点编号')
    sd10.loc[sd10['站点充电服务费是否连续三月高于指标'].isna(), '站点充电服务费是否连续三月高于指标'] = '否'

    Station_Data10 = pd.merge(Station_Data9, sd10[['站点编号', '站点充电服务费', '充电服务费对比类型',
                                                   '充电服务费对比均值',
                                                   '站点充电服务费是否高于平均值',
                                                   '站点充电服务费是否连续三月高于指标']],
                              how='left', on='站点编号').fillna(0)
    Station_Data10.head(1)

    # In[96]:

    Station_Data10.info()

    # # 诊断说明

    # ## 投资维度

    # In[97]:

    Station_Data11 = Station_Data10.copy()

    # In[98]:

    Station_Data11['投资维度诊断结果'] = '暂无'
    for i in range(Station_Data11.shape[0]):
        # 站点取值
        a = Station_Data11.loc[i, '单瓦造价']
        # 同类型平均值
        b = Station_Data11.loc[i, '同类型同规模单瓦造价平均值']
        # 是否连续三月
        c = Station_Data11.loc[i, '单瓦造价是否高于平均水平']
        if a > b:
            s = '【预警级】 '
            s = s + '单瓦造价' + str(round(a, 2)) + '元/瓦'
            s = s + '（同类型同规模站点均值' + str(round(b, 2)) + '元/瓦），'
            s = s + '超出平均水平' + str(round((a - b) * 100 / b, 2)) + '%，初始投资偏高。'
            print(s)
        elif a < b:
            s = ''
            s = s + '单瓦造价' + str(round(a, 2)) + '元/瓦'
            s = s + '（同类型同规模站点均值' + str(round(b, 2)) + '元/瓦），'
            s = s + '低于平均水平' + str(abs(round((a - b) * 100 / b, 2))) + '%，初始投资较低。'
            print(s)
        else:
            s = ''
            s = s + '单瓦造价' + str(round(a, 2)) + '元/瓦'
            s = s + '（同类型同规模站点均值' + str(round(b, 2)) + '元/瓦），'
            s = s + '单瓦造价与同类型平均水平相等。'
            print(s)
        Station_Data11.loc[i, '投资维度诊断结果'] = s

    # ## 运维维度

    # In[99]:

    Station_Data11['运维维度诊断结果'] = '暂无'
    for i in range(Station_Data11.shape[0]):
        # 站点取值
        a = Station_Data11.loc[i, '单瓦运维成本']
        # 同类型平均值
        b = Station_Data11.loc[i, '同类型同规模单瓦运维成本均值']
        # 是否连续三月
        c = Station_Data11.loc[i, '单瓦运维成本是否高于平均值']
        if a > b:
            s = '【预警级】 '
            s = s + '单瓦运维成本' + str(round(a, 2)) + '元/瓦'
            s = s + '（同类型同规模站点均值' + str(round(b, 2)) + '元/瓦），'
            s = s + '超出平均水平' + str(round((a - b) * 100 / b, 2)) + '%，运维成本偏高。'
            print(s)
        elif a < b:
            s = ''
            s = s + '单瓦运维成本' + str(round(a, 2)) + '元/瓦'
            s = s + '（同类型同规模站点均值' + str(round(b, 2)) + '元/瓦），'
            s = s + '低于平均水平' + str(abs(round((a - b) * 100 / b, 2))) + '%，运维成本控制较好。'
            print(s)
        else:
            s = ''
            s = s + '单瓦运维成本' + str(round(a, 2)) + '元/瓦'
            s = s + '（同类型同规模站点均值' + str(round(b, 2)) + '元/瓦），'
            s = s + '单瓦运维成本与同类型平均水平相等。'
            print(s)
        Station_Data11.loc[i, '运维维度诊断结果'] = s

    # ## 设备维度

    # ### 一次成功率

    # In[100]:

    Station_Data11['设备维度诊断结果-一次成功率'] = '暂无'
    for i in range(Station_Data11.shape[0]):
        # 站点取值
        a = Station_Data11.loc[i, '一次成功率']
        # 同类型平均值
        b = 95
        # 是否连续三月
        c = Station_Data11.loc[i, '一次成功率是否连续三月低于指标']
        if c == '是':
            s = '【预警级】设备一次成功率连续3个月低于指标（ '
            s = s + '本月一次成功率为' + str(round(a, 2)) + '%/'
            s = s + '一次成功率指标为' + str(round(b, 2)) + '%），'
            s = s + '与指标相差' + str(abs(round(a - b, 2))) + '%。存在系统性设备隐患，建议开展设备专项检查。'
            print(s)
        elif a < b:
            s = '【提示级】设备一次成功率本月低于指标（ '
            s = s + '本月一次成功率为' + str(round(a, 2)) + '%/'
            s = s + '一次成功率指标为' + str(round(b, 2)) + '%），'
            s = s + '与指标相差' + str(abs(round(a - b, 2))) + '%。需重点关注此站点一次成功率指标次月是否恢复正常水平。'
            print(s)
        elif a > b:
            s = '设备一次成功率本月高于指标（ '
            s = s + '本月一次成功率为' + str(round(a, 2)) + '%/'
            s = s + '一次成功率指标为' + str(round(b, 2)) + '%），'
            s = s + '相较指标高' + str(abs(round(a - b, 2))) + '%。本月设备情况良好。'
            print(s)
        elif a == b:
            s = '设备一次成功率本月等于指标，但有一定提升空间'
            print(s)
        Station_Data11.loc[i, '设备维度诊断结果-一次成功率'] = s

    # ### 设备可用率

    # In[101]:

    Station_Data11['设备维度诊断结果-设备可用率'] = '暂无'
    for i in range(Station_Data11.shape[0]):
        # 站点取值
        a = Station_Data11.loc[i, '设备可用率']
        # 同类型平均值
        b = 99
        # 是否连续三月
        c = Station_Data11.loc[i, '设备可用率是否连续三月低于指标']
        if c == '是':
            s = '【预警级】设备可用率连续3个月低于指标（ '
            s = s + '本月设备可用率为' + str(round(a, 2)) + '%/'
            s = s + '设备可用率指标为' + str(round(b, 2)) + '%），'
            s = s + '与指标相差' + str(abs(round(a - b, 2))) + '%。存在系统性设备隐患，建议开展设备专项检查。'
            print(s)
        elif a < b:
            s = '【提示级】设备可用率本月低于指标（ '
            s = s + '本月设备可用率为' + str(round(a, 2)) + '%/'
            s = s + '设备可用率指标为' + str(round(b, 2)) + '%），'
            s = s + '与指标相差' + str(abs(round(a - b, 2))) + '%。需重点关注此站点设备可用率指标次月是否恢复正常水平。'
            print(s)
        elif a > b:
            s = '设备可用率本月高于指标（ '
            s = s + '本月设备可用率为' + str(round(a, 2)) + '%/'
            s = s + '设备可用率指标为' + str(round(b, 2)) + '%），'
            s = s + '相较指标高' + str(abs(round(a - b, 2))) + '%。本月设备情况良好。'
            print(s)
        elif a == b:
            s = '设备可用率本月等于指标，但有一定提升空间'
            print(s)
        Station_Data11.loc[i, '设备维度诊断结果-设备可用率'] = s

    # ## 市场价格维度

    # ### 充电电价

    # In[102]:

    Station_Data11['市场价格维度诊断结果-站点充电电费'] = '暂无'
    for i in range(Station_Data11.shape[0]):
        if Station_Data11.loc[i, '充电电费对比类型'] == '同类型同规模':
            # 站点取值
            a = Station_Data11.loc[i, '站点充电电费']
            # 同类型平均值
            b = Station_Data11.loc[i, '充电电费对比均值']
            # 是否连续三月
            c = Station_Data11.loc[i, '站点充电电费是否连续三月高于指标']
            if c == '是':
                s = '【预警级】站点充电电费连续3个月高于同类型同规模站点平均水平（ '
                s = s + '本月站点充电电费为' + str(round(a, 2)) + '元/度，'
                s = s + '同类型同规模站点的充电电费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '高于平均水平' + str(round((a - b) * 100 / b, 2)) + '%。站点连续三月处于高价区间，需结合价格对充电量影响程度，综合考虑充电收入情况，及时对电价进行调整。'
                print(s)
            elif a > b:
                s = '【提示级】站点充电电费本月高于同类型同规模站点平均水平（ '
                s = s + '本月站点充电电费为' + str(round(a, 2)) + '元/度，'
                s = s + '同类型同规模站点充电电费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '高于平均水平' + str(abs(round(a - b, 2))) + '%。需及时查看本月此站点高价区间对充电量的影响程度。'
                print(s)
            elif a < b:
                s = '站点充电电费本月低于同类型同规模站点平均水平（ '
                s = s + '本月站点充电电费为' + str(round(a, 2)) + '元/度，'
                s = s + '同类型同规模站点充电电费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '低于平均水平' + str(abs(round((a - b) * 100 / b, 2))) + '%。'
                print(s)
            elif a == b:
                s = '站点充电电费本月等于同类型同规模站点均值。'
                print(s)
            Station_Data11.loc[i, '市场价格维度诊断结果-站点充电电费'] = s
        elif Station_Data11.loc[i, '充电电费对比类型'] == '外部竞争':
            # 站点取值
            a = Station_Data11.loc[i, '站点充电电费']
            # 同类型平均值
            b = Station_Data11.loc[i, '充电电费对比均值']
            # 是否连续三月
            c = Station_Data11.loc[i, '站点充电电费是否连续三月高于指标']
            if c == '是':
                s = '【预警级】站点充电电费连续3个月高于竞争站点平均水平（ '
                s = s + '本月站点充电电费为' + str(round(a, 2)) + '元/度，'
                s = s + '竞争站点充电电费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '高于平均水平' + str(round((a - b) * 100 / b, 2)) + '%。站点连续三月处于高价区间，需结合价格对充电量影响程度，综合考虑充电收入情况，及时对电价进行调整。'
                print(s)
            elif a > b:
                s = '【提示级】站点充电电费本月高于竞争站点平均水平（ '
                s = s + '本月站点充电电费为' + str(round(a, 2)) + '元/度，'
                s = s + '竞争站点充电电费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '高于平均水平' + str(abs(round(a - b, 2))) + '%。需及时查看本月此站点高价区间对充电量的影响程度。'
                print(s)
            elif a < b:
                s = '站点充电电费本月低于竞争站点平均水平（ '
                s = s + '本月站点充电电费为' + str(round(a, 2)) + '元/度，'
                s = s + '竞争站点充电电费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '低于平均水平' + str(abs(round((a - b) * 100 / b, 2))) + '%。可适当调高充电电价。'
                print(s)
            elif a == b:
                s = '站点充电电费本月等于竞争站点均值。'
                print(s)
            Station_Data11.loc[i, '市场价格维度诊断结果-站点充电电费'] = s

    # ### 充电服务费

    # In[103]:

    Station_Data11['市场价格维度诊断结果-站点充电服务费'] = '暂无'
    for i in range(Station_Data11.shape[0]):
        if Station_Data11.loc[i, '充电服务费对比类型'] == '同类型同规模':
            # 站点取值
            a = Station_Data11.loc[i, '站点充电服务费']
            # 同类型平均值
            b = Station_Data11.loc[i, '充电服务费对比均值']
            # 是否连续三月
            c = Station_Data11.loc[i, '站点充电服务费是否连续三月高于指标']
            if c == '是':
                s = '【预警级】站点充电服务费连续3个月高于同类型同规模站点平均水平（ '
                s = s + '本月站点充电服务费为' + str(round(a, 2)) + '元/度，'
                s = s + '同类型同规模站点的充电服务费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '高于平均水平' + str(round((a - b) * 100 / b, 2)) + '%。站点连续三月处于高价区间，需结合价格对充电量影响程度，综合考虑充电收入情况，及时对充电服务费进行调整。'
                print(s)
            elif a > b:
                s = '【提示级】站点充电服务费本月高于同类型同规模站点平均水平（ '
                s = s + '本月站点充电服务费为' + str(round(a, 2)) + '元/度，'
                s = s + '同类型同规模站点充电服务费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '高于平均水平' + str(abs(round(a - b, 2))) + '%。需及时查看本月此站点高价区间对充电量的影响程度。'
                print(s)
            elif a < b:
                s = '站点充电服务费本月低于同类型同规模站点平均水平（ '
                s = s + '本月站点充电服务费为' + str(round(a, 2)) + '元/度，'
                s = s + '同类型同规模站点充电服务费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '低于平均水平' + str(abs(round((a - b) * 100 / b, 2))) + '%。'
                print(s)
            elif a == b:
                s = '站点充电服务费本月等于同类型同规模站点均值。'
                print(s)
            Station_Data11.loc[i, '市场价格维度诊断结果-站点充电服务费'] = s
        elif Station_Data11.loc[i, '充电服务费对比类型'] == '外部竞争':
            # 站点取值
            a = Station_Data11.loc[i, '站点充电服务费']
            # 同类型平均值
            b = Station_Data11.loc[i, '充电服务费对比均值']
            # 是否连续三月
            c = Station_Data11.loc[i, '站点充电服务费是否连续三月高于指标']
            if c == '是':
                s = '【预警级】站点充电服务费连续3个月高于竞争站点平均水平（ '
                s = s + '本月站点充电服务费为' + str(round(a, 2)) + '元/度，'
                s = s + '竞争站点充电服务费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '高于平均水平' + str(round((a - b) * 100 / b, 2)) + '%。站点连续三月处于高价区间，需结合价格对充电量影响程度，综合考虑充电收入情况，及时对充电服务费进行调整。'
                print(s)
            elif a > b:
                s = '【提示级】站点充电服务费本月高于竞争站点平均水平（ '
                s = s + '本月站点充电服务费为' + str(round(a, 2)) + '元/度，'
                s = s + '竞争站点充电服务费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '高于平均水平' + str(abs(round(a - b, 2))) + '%。需及时查看本月此站点高价区间对充电量的影响程度。'
                print(s)
            elif a < b:
                s = '站点充电服务费本月低于竞争站点平均水平（ '
                s = s + '本月站点充电服务费为' + str(round(a, 2)) + '元/度，'
                s = s + '竞争站点充电服务费均值为' + str(round(b, 2)) + '元/度），'
                s = s + '低于平均水平' + str(abs(round((a - b) * 100 / b, 2))) + '%。可适当调高充电充电服务费。'
                print(s)
            elif a == b:
                s = '站点充电服务费本月等于竞争站点均值。'
                print(s)
            Station_Data11.loc[i, '市场价格维度诊断结果-站点充电服务费'] = s

    # ## 场地分成维度

    # In[104]:

    Station_Data11['场地分成维度诊断结果'] = '暂无'
    for i in range(Station_Data11.shape[0]):
        # 站点取值
        a = Station_Data11.loc[i, '站点场地其它商户分成占比']
        # 同类型平均值
        b = Station_Data11.loc[i, '同类型同规模其他商户分成占比均值']
        # 是否连续三月
        c = Station_Data11.loc[i, '分成是否连续三月高于指标']
        if c == '是':
            s = '【预警级】站点场地其它商户分成占比连续3个月高于平均水平（ '
            s = s + '本月站点场地其它商户分成占比为' + str(round(a * 100, 2)) + '%，'
            s = s + '同类型同规模站点场地其它商户分成占比均值为' + str(round(b * 100, 2)) + '%），'
            s = s + '高于平均水平' + str(round((a - b) * 100 / b, 2)) + '%，建议启动合同条款复审。'
            print(s)
        elif a > b:
            s = '【提示级】本月站点场地其它商户分成占比高于平均水平（ '
            s = s + '本月站点场地其它商户分成占比为' + str(round(a * 100, 2)) + '%，'
            s = s + '同类型同规模站点场地其它商户分成占比均值为' + str(round(b * 100, 2)) + '%），'
            s = s + '高于平均水平' + str(round((a - b) * 100 / b, 2)) + '%，需持续关注分成比例。'
            print(s)
        elif a < b:
            s = '站点场地其它商户分成占比本月低于平均水平（ '
            s = s + '本月站点场地其它商户分成占比为' + str(round(a * 100, 2)) + '%，'
            s = s + '同类型同规模站点场地其它商户分成占比均值为' + str(round(b * 100, 2)) + '%），'
            s = s + '低于平均水平' + str(abs(round((a - b) * 100 / b, 2))) + '%，站点分成维度具备优势。'
            print(s)
        elif a == b:
            s = '本月站点场地其它商户分成占比等于同类型同规模站点均值。'
            print(s)
        Station_Data11.loc[i, '场地分成维度诊断结果'] = s

    # ## 损耗维度

    # In[105]:

    Station_Data11['损耗维度诊断结果'] = '暂无'
    for i in range(Station_Data11.shape[0]):
        # 站点取值
        a = Station_Data11.loc[i, '电损']
        # 同类型平均值
        b = Station_Data11.loc[i, '同类型同规模站点电损均值']
        # 是否连续三月
        c = Station_Data11.loc[i, '电损是否连续三月高于指标']
        if c == '是':
            s = '【预警级】站点电量损耗连续3个月高于指标（ '
            s = s + '本月电量损耗为' + str(round(a * 100, 2)) + '%，'
            s = s + '同类型同规模站点电量损耗均值为' + str(round(b * 100, 2)) + '%），'
            s = s + '高于平均水平' + str(round((a - b) * 100 / b, 2)) + '%。站点连续三月电量损耗高，需重点分析站点电量损耗高的原因。'
            print(s)
        elif a > b:
            s = '【提示级】本月设备电量损耗高于指标（ '
            s = s + '本月电量损耗为' + str(round(a * 100, 2)) + '%，'
            s = s + '同类型同规模站点电量损耗均值为' + str(round(b * 100, 2)) + '%），'
            s = s + '高于平均水平' + str(abs(round(a - b, 2))) + '%。单月指标偏离同类型站点基准，需关注损耗波动合理性。'
            print(s)
        elif a < b:
            s = '设备电量损耗本月低于指标（ '
            s = s + '本月电量损耗为' + str(round(a * 100, 2)) + '%，'
            s = s + '同类型同规模站点电量损耗均值为' + str(round(b * 100, 2)) + '%），'
            s = s + '低于平均水平' + str(abs(round((a - b) * 100 / b, 2))) + '%。电量损耗水平维持良好。'
            print(s)
        elif a == b:
            s = '本月设备电量损耗等于同类型同规模站点均值。'
            print(s)
        Station_Data11.loc[i, '损耗维度诊断结果'] = s

    # In[106]:

    Station_Data11.columns

    # # 复杂前端格式转换

    # ## 红黄绿灯板块

    # In[107]:

    # Station_Data11.to_excel('./Station_Data11.xlsx')

    # In[108]:

    Station_Data12 = pd.merge(Station_Data11, data10[['站点编号', '回本类型标签']], how='left', on=['站点编号'])
    Station_Data13 = Station_Data12[Station_Data12['回本类型标签'] == '滞后未回本']
    print(Station_Data13.shape)
    Station_Data13.reset_index(inplace=True, drop=True)
    Station_Data13.head(1)

    # ### 前端格式转换

    # In[109]:

    result_list = []
    for i in range(Station_Data13.shape[0]):
        # 投资维度
        if Station_Data13.loc[i, '单瓦造价是否高于平均水平'] == '是':
            grade = 2
        else:
            grade = 0
        a = round(Station_Data13.loc[i, '单瓦造价'], 2)
        dict1 = {'value': a, 'unit': '元/瓦', 'name': '站点单瓦造价', 'compare': ''}
        b = round(Station_Data13.loc[i, '同类型同规模单瓦造价平均值'], 2)
        dict2 = {'value': b, 'unit': '元/瓦', 'name': '同类型同规模站点单瓦造价均值', 'compare': ''}
        c = Station_Data13.loc[i, '单瓦造价是否高于平均水平']
        dict3 = {'value': 0, 'unit': '', 'name': '是否高于平均水平', 'compare': c}
        content = [dict1, dict2, dict3]
        data_list1 = [{'grade': grade, 'content': content}]
        dimensionData_dict1 = {'title': '投资维度', 'data': data_list1}
        #     print('投资维度：\n',dimensionData_dict1)

        # 运维维度
        if Station_Data13.loc[i, '单瓦运维成本是否高于平均值'] == '是':
            grade = 2
        else:
            grade = 0
        a = round(Station_Data13.loc[i, '单瓦运维成本'], 2)
        dict1 = {'value': a, 'unit': '元/瓦', 'name': '站点月度单瓦运维成本', 'compare': ''}
        b = round(Station_Data13.loc[i, '同类型同规模单瓦运维成本均值'], 2)
        dict2 = {'value': b, 'unit': '元/瓦', 'name': '同类型同规模站点月度单瓦运维成本均值', 'compare': ''}
        c = Station_Data13.loc[i, '单瓦运维成本是否高于平均值']
        dict3 = {'value': 0, 'unit': '', 'name': '是否高于平均水平', 'compare': c}
        content = [dict1, dict2, dict3]
        data_list2 = [{'grade': grade, 'content': content}]
        dimensionData_dict2 = {'title': '运维维度', 'data': data_list2}
        #     print('运维维度：\n',dimensionData_dict2)

        # 场地分成维度
        if Station_Data13.loc[i, '分成是否连续三月高于指标'] == '是':
            grade = 2
        elif Station_Data13.loc[i, '分成是否高于平均值'] == '是':
            grade = 1
        else:
            grade = 0
        a = round(Station_Data13.loc[i, '站点场地其它商户分成占比'] * 100, 2)
        dict1 = {'value': a, 'unit': '%', 'name': '站点月度场地其他商户分成占比', 'compare': ''}
        b = round(Station_Data13.loc[i, '同类型同规模其他商户分成占比均值'] * 100, 2)
        dict2 = {'value': b, 'unit': '%', 'name': '同类型同规模站点其他商户分成占比均值', 'compare': ''}
        c = Station_Data13.loc[i, '分成是否连续三月高于指标']
        dict3 = {'value': 0, 'unit': '', 'name': '是否连续三月高于平均水平', 'compare': c}
        content = [dict1, dict2, dict3]
        data_list3 = [{'grade': grade, 'content': content}]
        dimensionData_dict3 = {'title': '场地分成维度', 'data': data_list3}
        #     print('场地分成维度：\n',dimensionData_dict3)

        # 损耗维度
        if Station_Data13.loc[i, '电损是否连续三月高于指标'] == '是':
            grade = 2
        elif Station_Data13.loc[i, '电损是否高于平均值'] == '是':
            grade = 1
        else:
            grade = 0
        a = round(Station_Data13.loc[i, '电损'] * 100, 2)
        dict1 = {'value': a, 'unit': '%', 'name': '站点月度电量损耗', 'compare': ''}
        b = round(Station_Data13.loc[i, '同类型同规模站点电损均值'] * 100, 2)
        dict2 = {'value': b, 'unit': '%', 'name': '同类型同规模站点月度电量损耗均值', 'compare': ''}
        c = Station_Data13.loc[i, '电损是否连续三月高于指标']
        dict3 = {'value': 0, 'unit': '', 'name': '是否连续三月高于平均水平', 'compare': c}
        content = [dict1, dict2, dict3]
        data_list4 = [{'grade': grade, 'content': content}]
        dimensionData_dict4 = {'title': '损耗维度', 'data': data_list4}
        #     print('损耗维度：\n',dimensionData_dict4)

        # 设备维度
        # 一次成功率
        if Station_Data13.loc[i, '一次成功率是否连续三月低于指标'] == '是':
            grade = 2
        elif Station_Data13.loc[i, '是否低于95%'] == '是':
            grade = 1
        else:
            grade = 0
        a = round(Station_Data13.loc[i, '一次成功率'], 2)
        dict1 = {'value': a, 'unit': '%', 'name': '站点设备一次成功率', 'compare': ''}
        b = 95.0
        dict2 = {'value': b, 'unit': '%', 'name': '设备一次成功率指标', 'compare': ''}
        c = Station_Data13.loc[i, '一次成功率是否连续三月低于指标']
        dict3 = {'value': 0, 'unit': '', 'name': '是否连续三月低于指标', 'compare': c}
        content = [dict1, dict2, dict3]
        data_list5_1 = [{'grade': grade, 'content': content}]
        # 设备可用率
        if Station_Data13.loc[i, '设备可用率是否连续三月低于指标'] == '是':
            grade = 2
        elif Station_Data13.loc[i, '是否低于99%'] == '是':
            grade = 1
        else:
            grade = 0
        a = round(Station_Data13.loc[i, '设备可用率'], 2)
        dict1 = {'value': a, 'unit': '%', 'name': '站点设备可用率', 'compare': ''}
        b = 99.0
        dict2 = {'value': b, 'unit': '%', 'name': '设备可用率指标', 'compare': ''}
        c = Station_Data13.loc[i, '设备可用率是否连续三月低于指标']
        dict3 = {'value': 0, 'unit': '', 'name': '是否连续三月低于指标', 'compare': c}
        content = [dict1, dict2, dict3]
        data_list5_2 = [{'grade': grade, 'content': content}]
        # 合并两个子维度
        data_list5 = [data_list5_1[0], data_list5_2[0]]
        dimensionData_dict5 = {'title': '设备维度', 'data': data_list5}
        #     print('设备维度：\n',dimensionData_dict5)

        # 市场价格维度
        # 充电电价
        if Station_Data13.loc[i, '站点充电电费是否连续三月高于指标'] == '是':
            grade = 2
        elif Station_Data13.loc[i, '站点充电电费是否高于平均值'] == '是':
            grade = 1
        else:
            grade = 0
        a = round(Station_Data13.loc[i, '站点充电电费'], 2)
        dict1 = {'value': a, 'unit': '元/度', 'name': '站点充电电价', 'compare': ''}
        b = round(Station_Data13.loc[i, '充电电费对比均值'], 2)
        if Station_Data13.loc[i, '充电电费对比类型'] == '同类型同规模':
            dict2 = {'value': b, 'unit': '元/度', 'name': '同类型同规模站点充电电价均值', 'compare': ''}
        else:
            dict2 = {'value': b, 'unit': '元/度', 'name': '外部竞争站点充电电价均值', 'compare': ''}
        c = Station_Data13.loc[i, '站点充电电费是否连续三月高于指标']
        dict3 = {'value': 0, 'unit': '', 'name': '是否连续三月高于平均水平', 'compare': c}
        content = [dict1, dict2, dict3]
        data_list6_1 = [{'grade': grade, 'content': content}]
        # 充电服务费
        if Station_Data13.loc[i, '站点充电服务费是否连续三月高于指标'] == '是':
            grade = 2
        elif Station_Data13.loc[i, '站点充电服务费是否高于平均值'] == '是':
            grade = 1
        else:
            grade = 0
        a = round(Station_Data13.loc[i, '站点充电服务费'], 2)
        dict1 = {'value': a, 'unit': '元/度', 'name': '站点充电服务费', 'compare': ''}
        b = round(Station_Data13.loc[i, '充电服务费对比均值'], 2)
        if Station_Data13.loc[i, '充电服务费对比类型'] == '同类型同规模':
            dict2 = {'value': b, 'unit': '元/度', 'name': '同类型同规模站点充电服务费均值', 'compare': ''}
        else:
            dict2 = {'value': b, 'unit': '元/度', 'name': '外部竞争站点充电服务费均值', 'compare': ''}
        c = Station_Data13.loc[i, '站点充电服务费是否连续三月高于指标']
        dict3 = {'value': 0, 'unit': '', 'name': '是否连续三月高于平均水平', 'compare': c}
        content = [dict1, dict2, dict3]
        data_list6_2 = [{'grade': grade, 'content': content}]
        # 合并两个子维度
        data_list6 = [data_list6_1[0], data_list6_2[0]]
        dimensionData_dict6 = {'title': '市场价格维度', 'data': data_list6}
        #     print('市场价格维度：\n',dimensionData_dict6)
        result_dict = {'siteNum': Station_Data13.loc[i, '站点编号'],
                       'dimensionData': [dimensionData_dict1,
                                         dimensionData_dict2,
                                         dimensionData_dict3,
                                         dimensionData_dict4,
                                         dimensionData_dict5,
                                         dimensionData_dict6],
                       'month': M}
        result_list.append(result_dict)

    Database_Table3 = pd.DataFrame(result_list)
    Database_Table3['dimensionData'] = Database_Table3['dimensionData'].apply(json.dumps, ensure_ascii=False)
    Database_Table3.head(2)

    # ### 数据存储

    # In[110]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警站点页_六大维度对比数据"
    column_comments = {
        'siteNum': '站点编号',
        'dimensionData': '六大维度对比绘图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table3,
        table_name="dp_WarningSite_SixDimensionalComparison",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # ## 末尾文字版问题诊断板块

    # ### 前端格式转换

    # In[111]:

    sd1 = Station_Data13[['站点编号', '投资维度诊断结果',
                          '运维维度诊断结果',
                          '设备维度诊断结果-一次成功率',
                          '设备维度诊断结果-设备可用率',
                          '市场价格维度诊断结果-站点充电电费',
                          '市场价格维度诊断结果-站点充电服务费',
                          '场地分成维度诊断结果',
                          '损耗维度诊断结果']]

    # In[112]:

    def convert_to_frontend_format(df):
        # 定义列名与维度的映射关系
        dimension_mapping = {
            "投资维度": "投资维度诊断结果",
            "运维维度": "运维维度诊断结果",
            "场地分成维度": "场地分成维度诊断结果",
            "损耗维度": "损耗维度诊断结果",
            "设备维度": [
                "设备维度诊断结果-一次成功率",
                "设备维度诊断结果-设备可用率"
            ],
            "市场价格维度": [
                "市场价格维度诊断结果-站点充电电费",
                "市场价格维度诊断结果-站点充电服务费"
            ]
        }

        result = []
        # 遍历每一行数据
        for _, row in df.iterrows():
            site_data = {
                "siteNum": row["站点编号"],
                "problemDiagnosis": [],
                'month': M
            }

            # 处理每个维度
            for title, cols in dimension_mapping.items():
                # 处理单列维度（投资、运维、场地分成、损耗）
                if isinstance(cols, str):
                    content = row[cols] if pd.notna(row[cols]) else ""
                    # 确定level值
                    if "【预警级】" in content:
                        level = 2
                        content = content.replace("【预警级】", "")
                    elif "【提示级】" in content:
                        level = 1
                        content = content.replace("【提示级】", "")
                    else:
                        level = 0
                    # 添加到诊断列表
                    site_data["problemDiagnosis"].append({
                        "title": title,
                        "data": [{"level": level, "content": content}]
                    })

                # 处理多列维度（设备、市场价格）
                elif isinstance(cols, list):
                    data_list = []
                    for col in cols:
                        content = row[col] if pd.notna(row[col]) else ""
                        # 确定level值
                        if "【预警级】" in content:
                            level = 2
                            content = content.replace("【预警级】", "")
                        elif "【提示级】" in content:
                            level = 1
                            content = content.replace("【提示级】", "")
                        else:
                            level = 0
                        data_list.append({"level": level, "content": content})
                    # 添加到诊断列表
                    site_data["problemDiagnosis"].append({
                        "title": title,
                        "data": data_list
                    })

            result.append(site_data)

        return result

    frontend_result = convert_to_frontend_format(sd1)
    Database_Table4 = pd.DataFrame(frontend_result)
    Database_Table4['problemDiagnosis'] = Database_Table4['problemDiagnosis'].apply(json.dumps, ensure_ascii=False)
    Database_Table4

    # frontend_data_json = json.dumps(frontend_result, ensure_ascii=False)
    # Database_Table4 = pd.DataFrame({'result':[frontend_data_json],'month':[M]})
    # Database_Table4

    # In[113]:

    Database_Table4.iloc[0, 1]

    # ### 数据存储

    # In[114]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警站点页_六大维度诊断结果文字"
    column_comments = {
        'siteNum': '站点编号',
        'problemDiagnosis': '问题诊断文字展示内容',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table4,
        table_name="dp_WarningSite_DiagnosticResults_Text",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # ## 问题诊断雷达图板块

    # ### 数据计算

    # In[115]:

    sd1 = Station_Data13[['站点编号', '单瓦造价', '单瓦运维成本',
                          '一次成功率', '设备可用率', '站点场地其它商户分成占比',
                          '电损', '站点充电电费', '站点充电服务费',
                          '同类型同规模单瓦造价平均值', '同类型同规模单瓦运维成本均值',
                          '设备一次成功率指标', '设备可用率指标',
                          '同类型同规模其他商户分成占比均值', '同类型同规模站点电损均值',
                          '充电电费对比均值', '充电服务费对比均值']]

    # In[116]:

    # 计算8个指标与对比均值之间的比例关系 (自身-平均)/平均
    def cal_proportionality(sd1):
        d1 = sd1.copy()
        d1['投资_x'] = (d1['单瓦造价'] - d1['同类型同规模单瓦造价平均值']) / d1['同类型同规模单瓦造价平均值']
        d1['运维_x'] = (d1['单瓦运维成本'] - d1['同类型同规模单瓦运维成本均值']) / d1['同类型同规模单瓦运维成本均值']
        d1['场地分成_x'] = (d1['站点场地其它商户分成占比'] - d1['同类型同规模其他商户分成占比均值']) / d1['同类型同规模其他商户分成占比均值']
        d1['损耗_x'] = (d1['电损'] - d1['同类型同规模站点电损均值']) / d1['同类型同规模站点电损均值']
        d1['设备_成功率_x'] = (d1['一次成功率'] - d1['设备一次成功率指标']) / d1['设备一次成功率指标']
        d1['设备_可用率_x'] = (d1['设备可用率'] - d1['设备可用率指标']) / d1['设备可用率指标']
        d1['市场价格_电费_x'] = (d1['站点充电电费'] - d1['充电电费对比均值']) / d1['充电电费对比均值']
        d1['市场价格_服务费_x'] = (d1['站点充电服务费'] - d1['充电服务费对比均值']) / d1['充电服务费对比均值']

        # 2. 合并相关指标
        d1['设备_x'] = d1['设备_成功率_x'] + d1['设备_可用率_x']
        d1['市场价格_x'] = d1['市场价格_电费_x'] + d1['市场价格_服务费_x']
        return d1

    sd2 = cal_proportionality(sd1)
    sd3 = sd2[['站点编号', '投资_x', '运维_x', '场地分成_x', '损耗_x', '设备_x', '市场价格_x']]
    sd3 = sd3.fillna(0)
    sd3.head(1)

    # In[117]:

    # 将六个维度的数据进行横向映射，大于0的维度，数据映射为1-2，等于0的映射为1，小于0的映射为0-1
    def normalize(sd3):
        d1 = sd3[['投资_x', '运维_x', '场地分成_x', '损耗_x', '设备_x', '市场价格_x']].copy()
        result_list = []
        for i in range(d1.shape[0]):
            list1 = list(d1.iloc[i, :])
            lista = [i for i in list1 if i > 0]
            if len(lista) > 0:
                max_data = max([i for i in lista if i > 0])
            listb = [i for i in list1 if i < 0]
            if len(listb) > 0:
                min_data = min([i for i in listb if i < 0])
            new_list = []
            for i in list1:
                if i == 0:
                    new_list.append(1)
                elif i > 0:
                    new_list.append(round(1 + (i / max_data), 2))
                else:
                    new_list.append(round((i - min_data) / (-min_data), 2))
            result_list.append(new_list)
        result = pd.DataFrame(result_list, columns=d1.columns)
        result['站点编号'] = sd3[['站点编号']]
        return result

    normalized_sd3 = normalize(sd3)
    normalized_sd3

    # In[118]:

    normalized_sd3.info()

    # ### 前端格式转换

    # In[119]:

    def process_station_data(normalized_sd3):
        # 前端格式转换
        d1 = normalized_sd3.copy()
        result = []
        indicator_names = ['投资', '运维', '场地分成', '损耗', '设备', '市场价格']
        for _, row in d1.iterrows():
            # 站点数据和对比数据
            site_values = [
                row['投资_x'],
                row['运维_x'],
                row['场地分成_x'],
                row['损耗_x'],
                row['设备_x'],
                row['市场价格_x']
            ]
            compare_values = [1, 1, 1, 1, 1, 1]  # 对比水平都是1

            # 判断优势劣势维度
            advantage_dims = []
            disadvantage_dims = []

            # 投资维度：小于等于1为优势
            if row['投资_x'] <= 1:
                advantage_dims.append('投资')
            else:
                disadvantage_dims.append('投资')

            # 运维维度：小于等于1为优势
            if row['运维_x'] <= 1:
                advantage_dims.append('运维')
            else:
                disadvantage_dims.append('运维')

            # 场地分成维度：小于等于1为优势
            if row['场地分成_x'] <= 1:
                advantage_dims.append('场地分成')
            else:
                disadvantage_dims.append('场地分成')

            # 损耗维度：小于等于1为优势
            if row['损耗_x'] <= 1:
                advantage_dims.append('损耗')
            else:
                disadvantage_dims.append('损耗')

            # 设备维度：大于等于1为优势
            if row['设备_x'] >= 1:
                advantage_dims.append('设备')
            else:
                disadvantage_dims.append('设备')

            # 市场价格维度：小于等于1为优势
            if row['市场价格_x'] <= 1:
                advantage_dims.append('市场价格')
            else:
                disadvantage_dims.append('市场价格')

            # 构建problemDiagnosis
            problem_diagnosis = []
            if advantage_dims:
                problem_diagnosis.append({
                    "name": "优势维度",
                    "content": "、".join(advantage_dims)
                })
            if disadvantage_dims:
                problem_diagnosis.append({
                    "name": "劣势维度",
                    "content": "、".join(disadvantage_dims)
                })
            problem_diagnosis.append({
                "name": "备注",
                "content": "运维、损耗、投资、设备、场地分成维度与同类型同规模站点平均水平进行对比；市场价格维度，具有竞争站点的，与周边竞争站点平均水平进行对比，无竞争站点的，与同类型同规模站点平均水平进行对比"
            })

            # 构建最终结果
            result.append({
                "siteNum": str(row['站点编号']),
                "radarData": [
                    {
                        "value": site_values,
                        "name": "站点水平"
                    },
                    {
                        "value": compare_values,
                        "name": "对比水平"
                    }
                ],
                "indicator": [{"name": name} for name in indicator_names],
                "problemDiagnosis": problem_diagnosis,
                'month': M
            })

        return result

    # # 调用函数处理数据
    frontend_data = process_station_data(normalized_sd3)

    Database_Table5 = pd.DataFrame(frontend_data)
    Database_Table5['radarData'] = Database_Table5['radarData'].apply(json.dumps, ensure_ascii=False)
    Database_Table5['indicator'] = Database_Table5['indicator'].apply(json.dumps, ensure_ascii=False)
    Database_Table5['problemDiagnosis'] = Database_Table5['problemDiagnosis'].apply(json.dumps, ensure_ascii=False)
    Database_Table5.head(2)

    # ### 数据存储

    # In[120]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警站点页_六大维度雷达图"
    column_comments = {
        'siteNum': '站点编号',
        'radarData': '雷达图数据',
        'indicator': '雷达图标签',
        'problemDiagnosis': '优劣势维度结论',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table5,
        table_name="dp_WarningSite_RadarChart",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # In[ ]:

    # In[ ]:

    # In[ ]:




