from logs.log_decorator import log_execution
from loguru import logger
from modules.config import SQL,import_data_with_cursor,Statistical_Time



@log_execution
def runkeyStationInternalCompetition():
    logger.info(f"开始执行重点站点内部竞争页面")

    import pandas as pd
    import numpy as np
    import pymysql
    from datetime import datetime, date
    import os
    from dateutil.parser import parse
    import json
    from pandas.tseries.offsets import MonthBegin
    import calendar
    from dateutil.relativedelta import relativedelta
    from sklearn.preprocessing import StandardScaler
    from sklearn.preprocessing import MinMaxScaler

    # ## 数据导入数据库

    # In[229]:

    import pandas as pd
    import json
    import re
    import pymysql  # 确保导入pymysql
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)

    def get_months_in_year(month_str):
        """获取指定月份及其当年之前的所有月份，返回元组格式"""
        year = int(month_str[:4])
        month = int(month_str[4:])

        # 生成从1月到指定月份的所有月份，并转换为元组
        months = tuple(int(f"{year}{m:02d}") for m in range(1, month + 1))

        placeholders = ", ".join([f"p{p}" for p in months])

        return placeholders

    # # 指标计算

    # In[233]:

    # 从M中解析年份和月份
    year = int(M[:4])  # 取前4位作为年份，如'202505' -> 2025
    month = int(M[4:])  # 取后2位作为月份，如'202505' -> 5
    # 使用calendar.monthrange获取当月天数
    # monthrange返回元组(当月第一天是星期几, 当月天数)，取第二个值
    _, days_in_month = calendar.monthrange(year, month)

    # ## 数据读取

    # ### df1-站点基础信息表（含初始投资）

    sql1 = """
    SELECT 
        cs.station_name,
        cs.station_no,
        cs.station_category,
        cs.city,
        cs.operation_status,
        IFNULL(cs.investment_amount, 0) as investment_amount,
        cs.commissioning_time
    FROM
        charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        rm.merchant_name = '国网电动汽车服务（四川）有限公司'
        AND cs.operation_status IN ('投运', '退运')
        AND DATE_FORMAT(cs.commissioning_time, '%Y%m') < '{}'
    """.format(M)

    df1 = SQL(sql1)
    df1.loc[df1['station_category'] == '高速', 'station_category'] = '高速公共'
    df1 = df1[df1['station_category'].isin(['高速公共', '城市公共', '重卡专用'])]
    print("df1.shape:==================================================================================")
    print(df1.head())
    print(df1.shape)
    print(df1.info())
    df1.head(1)
    counts = df1['station_category'].value_counts()
    print(counts)

    # #### 数据类型转换

    # In[238]:

    df1['investment_amount'] = df1['investment_amount'].astype(str).str.replace(',', '').astype(float)
    df1.info()

    # #### 累计投运月份计算

    # In[239]:

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

    # ### df2-站点补贴数据

    # In[240]:

    # ==================注释==================
    # 统计每个站点当前的累计总补贴
    # station_no：站点编号
    # total_subsidy：总补贴
    # ——共96条数据

    # In[241]:

    sql2 = """
    select year,station_no,IFNULL(total_subsidy,0) as total_subsidy from dp_subsidy_NEW;
    """
    df2 = SQL(sql2)
    print(df2.shape)
    print(df2.info())
    df2.head(1)

    # In[242]:

    # 数据类型转换、单位统一为元
    df2['total_subsidy'] = 10000 * df2['total_subsidy'].astype(str).str.replace(',', '').astype(float)

    # In[243]:

    df2_cal = df2.groupby('station_no', as_index=False).agg({'total_subsidy': 'sum'})
    df2_cal.head(1)

    # ### df3-站点运营总收入和总支出

    # In[244]:

    # ==================注释==================
    # 统计四川电动投资金额不为空的每个投运站点的总收入、总支出
    # station_no：站点编号
    # revenue：总收入
    # cost：总支出
    # ——共212条数据

    # In[245]:

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

    # In[246]:

    # 数据类型转换
    df3['revenue'] = df3['revenue'].astype(str).str.replace(',', '').astype(float)
    df3['cost'] = df3['cost'].astype(str).str.replace(',', '').astype(float)
    df3.info()

    # In[247]:

    df3_cal = df3.groupby('station_no', as_index=False).agg({'revenue': 'sum',
                                                             'cost': 'sum'})
    df3_cal

    # ### df4-站点租金

    # In[248]:

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

    # In[249]:

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

    # In[250]:

    # 数据类型转换
    df4['parking_fee'] = df4['parking_fee'].astype(str).str.replace(',', '').astype(float)
    df4.info()

    # ### df5-站点累计分成

    # In[251]:

    # ==================注释==================
    # 这里的分成指的是，四川电动旗下站点，分给其他单位的分成
    # station_no：站点编号
    # merchant_profit_amount：站点分成
    # --共352条数据

    # In[252]:

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

    # In[253]:

    # 数据类型转换
    df5['merchant_profit_amount'] = df5['merchant_profit_amount'].astype(str).str.replace(',', '').astype(float)
    df5.info()

    # In[254]:

    df5_cal = df5.groupby('station_no', as_index=False).agg({'merchant_profit_amount': 'sum'})
    df5_cal.head(1)

    # ### df6-站点运维费用

    # In[255]:

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

    # In[256]:

    # 数据类型转换、单位统一为元
    df6['maintenance_cost'] = 10000 * df6['maintenance_cost'].astype(str).str.replace(',', '').astype(float)

    # In[257]:

    df6_cal = df6.groupby('station_no', as_index=False).agg({'maintenance_cost': 'sum'})
    df6_cal.head(1)

    # ### df7-额定功率、充电枪数量

    # In[258]:

    sql7 = """
    SELECT 
    cs.station_name,cs.station_no,cs.station_category,operation_status,cs.station_capacity,cs.dc_charge_point_count,cs.ac_charge_point_count
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and operation_status in ('投运','退运');
    """
    df7 = SQL(sql7)
    df7.loc[df7['station_category'] == '高速', 'station_category'] = '高速公共'
    df7 = df7[df7['station_category'].isin(['高速公共', '城市公共', '重卡专用'])]
    print(df7.shape)
    print(df7.info())
    df7.head(1)

    # In[259]:

    # 充电枪数量=直流加交流
    df7['ac_dc_charge_point_count'] = df7['dc_charge_point_count'].fillna(0) + df7['ac_charge_point_count'].fillna(0)

    # ### df8-电量、电费、服务费

    # In[260]:

    sql8 = f"""
    select * from 
    (SELECT 
    cs.station_no,station_category,station_name
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and  cs.operation_status in ('投运','退运')) a
    left join 
    (select station_no,cba_month,plat_data_charging_volume,rec_data_elec_fee_revenue,rec_cost_elec_fee,rec_data_service_fee_revenue from station_cba_org_data where cba_month in ('{M}','{previous_month_str}') ) b
    on a.station_no =b.station_no
    """
    df8 = SQL(sql8)
    df8.loc[df8['station_category'] == '高速', 'station_category'] = '高速公共'
    df8 = df8[df8['station_category'].isin(['高速公共', '城市公共', '重卡专用'])]
    # 有两个重复的站编码列，此处进行删除
    df8 = df8.iloc[:, [0, 1, 2, 4, 5, 6, 7, 8]]
    print(df8.shape)
    print(df8.info())
    df8.head(1)

    # In[261]:

    # 将空值变为0
    columns_to_fill = ['rec_data_elec_fee_revenue', 'rec_cost_elec_fee',
                       'rec_data_service_fee_revenue', 'plat_data_charging_volume']

    for col in columns_to_fill:
        df8[col] = df8[col].fillna(0)
    # 数据类型转换
    df8['rec_data_elec_fee_revenue'] = df8['rec_data_elec_fee_revenue'].astype(float)
    df8['rec_cost_elec_fee'] = df8['rec_cost_elec_fee'].astype(float)
    df8['rec_data_service_fee_revenue'] = df8['rec_data_service_fee_revenue'].astype(float)

    # #### 度电电费差计算

    # In[262]:

    df8['dif_in_elec'] = df8['rec_data_elec_fee_revenue'].fillna(0) / df8['plat_data_charging_volume'] - df8['rec_cost_elec_fee'].fillna(0) / df8['plat_data_charging_volume']
    df8['dif_in_elec'] = df8['dif_in_elec'].fillna(0)

    print(df8.shape)
    print(df8.info())
    df8.head(1)

    # #### 月充电量的环比计算

    # In[263]:

    # 创建副本避免修改原始数据
    df8 = df8.copy()

    # 初始化新列，默认值为 NaN
    df8['cost_elec_cons_mom'] = np.nan

    # 步骤1: 为上月数据设置环比为0
    df8.loc[df8['cba_month'] == previous_month_str, 'cost_elec_cons_mom'] = 0

    # 步骤2: 计算当月数据的环比
    # 获取所有需要计算环比的站点列表
    stations = df8['station_no'].unique()

    # 循环处理每个站点
    for station in stations:
        # 获取该站点当前月的数据
        current_month_data = df8[(df8['station_no'] == station) & (df8['cba_month'] == M)]

        # 获取该站点上月的数据
        previous_month_data = df8[(df8['station_no'] == station) & (df8['cba_month'] == previous_month_str)]

        # 只有当上月和当月数据都存在时才计算环比
        if not current_month_data.empty and not previous_month_data.empty:
            # 提取电量值
            current_cons = current_month_data['plat_data_charging_volume'].values[0]
            previous_cons = previous_month_data['plat_data_charging_volume'].values[0]

            # 避免除数为零
            if previous_cons != 0:
                mom = (current_cons - previous_cons) / previous_cons
            else:
                mom = np.nan  # 上月电量为0，无法计算环比

            # 更新环比值
            df8.loc[(df8['station_no'] == station) & (df8['cba_month'] == M), 'cost_elec_cons_mom'] = mom

    # 步骤3: 处理特殊情况 - 当月有数据但上月无数据
    # 对于这些站点，环比设为0
    mask_current = (df8['cba_month'] == M) & (df8['cost_elec_cons_mom'].isna())
    df8.loc[mask_current, 'cost_elec_cons_mom'] = 0

    # 步骤4: 格式化环比为百分比
    df8['cost_elec_cons_mom'] = (df8['cost_elec_cons_mom'] * 100).round(2)

    # 验证结果
    print("\n环比计算完成:")
    print(f"上月({previous_month_str})数据量: {len(df8[df8['cba_month'] == previous_month_str])}")
    print(f"当月({M})数据量: {len(df8[df8['cba_month'] == M])}")
    print(f"已计算环比的数据量: {len(df8[df8['cba_month'] == M].dropna(subset=['cost_elec_cons_mom']))}")
    print(df8.shape)
    print(df8.info())
    df8.head(1)

    # #### 月充电服务费的环比计算

    # In[264]:



    # 创建服务费环比列，初始化为 NaN
    df8['service_fee_revenue_mom'] = np.nan

    # 步骤1: 为上月数据设置环比为0
    df8.loc[df8['cba_month'] == previous_month_str, 'service_fee_revenue_mom'] = 0

    # 步骤2: 计算当月数据的环比
    # 获取所有需要计算环比的站点列表
    stations = df8['station_no'].unique()

    # 循环处理每个站点
    for station in stations:
        # 获取该站点当前月的数据
        current_month_data = df8[(df8['station_no'] == station) & (df8['cba_month'] == M)]

        # 获取该站点上月的数据
        previous_month_data = df8[(df8['station_no'] == station) & (df8['cba_month'] == previous_month_str)]

        # 只有当上月和当月数据都存在时才计算环比
        if not current_month_data.empty and not previous_month_data.empty:
            # 提取服务费值
            current_fee = current_month_data['rec_data_service_fee_revenue'].values[0]
            previous_fee = previous_month_data['rec_data_service_fee_revenue'].values[0]

            # 计算环比
            mom = (current_fee - previous_fee) / previous_fee

            # 更新环比值
            df8.loc[(df8['station_no'] == station) & (df8['cba_month'] == M), 'service_fee_revenue_mom'] = mom

    # 步骤3: 处理特殊情况 - 当月有数据但上月无数据或上月为0
    # 对于这些站点，环比设为0
    mask_current = (df8['cba_month'] == M) & (df8['service_fee_revenue_mom'].isna())
    df8.loc[mask_current, 'service_fee_revenue_mom'] = 0

    # 步骤4: 格式化环比为百分比
    df8['service_fee_revenue_mom'] = (df8['service_fee_revenue_mom'] * 100).round(2)

    # 验证结果
    print("\n服务费环比计算完成:")
    print(f"上月({previous_month_str})数据量: {len(df8[df8['cba_month'] == previous_month_str])}")
    print(f"当月({M})数据量: {len(df8[df8['cba_month'] == M])}")
    print(f"环比为0的数据量: {len(df8[df8['service_fee_revenue_mom'] == 0])}")

    print(df8.shape)
    print(df8.info())
    df8.head(1)

    # ### df9-外部竞争站点数据读取

    # In[265]:

    # 获取需要查询的station_id列表
    unique_station_nos = df8['station_no'].unique().tolist()

    # 构建SQL查询语句
    sql9 = f"""
    SELECT 
        p.date,
        p.station_id,
        p.electricity_quantity,
        p.charging_num,
        p.service_fee,
        m.dd_station_id
    FROM 
        dp_ProvincialSupervisionPlatform p
    INNER JOIN 
        dp_KeyStations_CompetitorStationsCodeMapping m
    ON 
        p.station_id = m.sjg_station_id
    WHERE 
        m.dd_station_id IN ({','.join([f"'{s}'" for s in unique_station_nos])})
    """

    # 执行SQL查询
    df9 = SQL(sql9)

    # 替换空值为0
    df9['electricity_quantity'] = df9['electricity_quantity'].fillna(0)
    df9['service_fee'] = df9['service_fee'].fillna(0)

    # 验证结果
    print(df9.shape)
    print(df9.info())
    df9.head(1)

    # 查看service_fee等于0的行数
    zero_count = (df9['service_fee'] == 0).sum()
    print(f"service_fee等于0的行数: {zero_count}")

    # ## 累计回本进度数据合并

    # In[266]:

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

    # ### 站点数据筛选

    # In[267]:

    df1.head(1)

    # In[268]:

    # 筛选当前四川电动旗下投运状态的全量站点数据+技改站
    data1 = df1[((df1['operation_status'] == '投运') |
                 (df1['station_no'].isin(["300003000100002472",
                                          "300003000100002473",
                                          "300003013200011",
                                          "300003013200099",
                                          "300003013200108"])))]
    print(data1.shape)
    data1.head(1)

    # ### 补贴数据合并

    # In[269]:

    # 合并站点补贴数据
    print('含有补贴的站点数量：', df2_cal.shape)
    data2 = pd.merge(data1, df2_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data2.shape)
    print('四川电动投运站点中含有补贴的站点的数量：', data2[data2['total_subsidy'] != 0].shape)
    data2.head(1)

    # ### 运营数据合并

    # In[270]:

    # 合并各站点的运营总投入和总支出
    data3 = pd.merge(data2, df3_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data3.shape)
    print('四川电动投运站点中含有运营数据的站点的数量：', data3[data3['revenue'] != 0].shape)
    data3.head(1)

    # ### 站点租金合并

    # In[271]:

    # 合并站点租金
    data4 = pd.merge(data3, df4, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data4.shape)
    print('四川电动投运站点中含有租金数据的站点的数量：', data4[data4['parking_fee'] != 0].shape)
    data4.head(1)

    # ### 分成数据合并

    # In[272]:

    # 合并站点分成
    data5 = pd.merge(data4, df5_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data5.shape)
    print('四川电动投运站点中含有分成数据的站点的数量：', data5[data5['merchant_profit_amount'] != 0].shape)
    data5.head(1)

    # ### 运维数据合并

    # In[273]:

    # 合并站点运维费
    data6 = pd.merge(data5, df6_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data6.shape)
    print('四川电动投运站点中含有运维数据的站点的数量：', data6[data6['maintenance_cost'] != 0].shape)
    data6.head(1)

    # ### 当年补贴数据合并

    # In[274]:

    df2_year = df2[df2['year'] == str(year) + '年']
    df2_year.columns = ['year', 'station_no', '当年_total_subsidy']
    df2_year = df2_year[['station_no', '当年_total_subsidy']]

    # In[275]:

    data7 = pd.merge(data6, df2_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data7.shape)
    print('四川电动投运站点中含有当年补贴数据的站点的数量：', data7[data7['当年_total_subsidy'] != 0].shape)
    data7.head(1)

    # ### 当年运营收入数据合并

    # In[276]:

    df3.head(1)

    # In[277]:
    df3['cba_month'].replace('None', pd.NA, inplace=True)
    df3.dropna(subset=['cba_month'], inplace=True)
    df3['year'] = df3['cba_month'].astype(str).str[:4].astype(int)
    df3_year = df3[df3['year'] == year]
    df3_year = df3_year.groupby(by='station_no', as_index=False).agg({'revenue': 'sum'})
    df3_year.columns = ['station_no', '当年_revenue']
    df3_year

    # In[278]:

    # 合并当年运营收入
    data8 = pd.merge(data7, df3_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data8.shape)
    print('四川电动投运站点中含有当年运营收入数据的站点的数量：', data8[data8['当年_revenue'] != 0].shape)
    data8.head(1)

    # ### 技改站数据合并-特殊处理

    # In[279]:

    # 此处将旧站（左）的数据替换成新站（右）的数据，但是初始投资额这一列没有替换，因为初始投资额要相加

    # In[280]:

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

    # In[281]:

    data9.shape

    # In[282]:

    data9[data9['station_no'] == '300003000100019488']

    # ### 站点回本进度详情

    # In[283]:

    data9['in'] = data9['total_subsidy'].astype('float') + data9['revenue'].astype('float')
    data9['out'] = data9['investment_amount'].astype('float') + data9['cost'].astype('float') + (data9['parking_fee'] * data9['累计投运月份数']).astype('float') + data9['merchant_profit_amount'].astype('float') + data9['maintenance_cost'].astype('float')
    data9.head(1)

    # In[284]:

    # groupby是因为要加上技改站的数据
    data10 = data9.groupby(by=['station_no'], as_index=False).agg({'station_name': 'max',
                                                                   'city': 'max',
                                                                   'station_category': 'max',
                                                                   'investment_amount': 'sum',
                                                                   'out': 'sum',
                                                                   'in': 'sum',
                                                                   '设备折旧进度': 'max',
                                                                   })
    data10['设备折旧进度'] = round(data10['设备折旧进度'], 4) * 100
    data10['静态资金回本进度'] = round(data10['in'] / data10['out'], 4) * 100
    data10['设备折旧进度'] = data10['设备折旧进度'].round(2)
    data10['静态资金回本进度'] = data10['静态资金回本进度'].round(2)
    # 把investment_amount为0的站点的'静态资金回本进度'设置为0
    data10.loc[data10['investment_amount'] == 0, '静态资金回本进度'] = 0
    # 将'静态资金回本进度'列的空值填充为0
    data10['静态资金回本进度'] = data10['静态资金回本进度'].fillna(0)
    print(data10.info())

    # In[285]:

    # 将'静态资金回本进度'列中的inf和-inf替换为0
    data10['静态资金回本进度'] = data10['静态资金回本进度'].replace(np.inf, 0)
    data10['静态资金回本进度'] = data10['静态资金回本进度'].replace([np.inf, -np.inf], 0)

    # In[286]:

    # 检查指定列的空值数量
    null_check = data10[['station_name', 'station_no', 'station_category', 'city']].isnull().sum()

    # 打印结果
    print("空值统计:")
    print(null_check)

    # 检查是否存在任何空值
    if null_check.any():
        print("\n存在空值")
    else:
        print("\n没有空值")

    # ### 前端格式转换

    # In[287]:

    import json  # 需要导入 json 模块

    # 构建数据列表
    data_list = []
    for _, row in data10.iterrows():
        site_data = {
            "siteNum": row['station_no'],
            "pieChartData1": [
                {
                    "name": "静态投资回收进度",
                    "value": row['静态资金回本进度'],
                    "unit": "%"
                }
            ],
            "pieChartData2": [
                {
                    "name": "设备折旧进度",
                    "value": row['设备折旧进度'],
                    "unit": "%"
                }
            ],
            "month": M
        }

        # 将 pieChartData1 和 pieChartData2 转换为 JSON 字符串
        site_data["pieChartData1"] = json.dumps(site_data["pieChartData1"], ensure_ascii=False)
        site_data["pieChartData2"] = json.dumps(site_data["pieChartData2"], ensure_ascii=False)

        data_list.append(site_data)

    # 创建最终结果表
    Database_Table3 = pd.DataFrame(data_list)

    # 输出结果
    Database_Table3

    # ### 数据存储

    # In[288]:

    import pymysql
    from pymysql.cursors import DictCursor

    def create_table():
        # 数据库连接配置
        conn = pymysql.connect(
            host='192.168.0.223',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4'  # 确保支持特殊字符
        )

        try:
            with conn.cursor() as cursor:
                # 创建表的SQL语句，使用LONGTEXT类型存储长文本
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS dp_KeyStation_Cumulative_profit_recovery_progress (
                    data LONGTEXT COMMENT '六大维度对比数据',
                    month VARCHAR(6) COMMENT '分析年月，格式建议为YYYYMM'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='六大维度对比数据表';
                """

                # 执行SQL语句
                cursor.execute(create_table_sql)
                print("表创建成功或已存在")

            # 提交事务
            conn.commit()

        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"创建表时发生错误: {e}")
        finally:
            # 关闭数据库连接
            if conn:
                conn.close()

    if __name__ == "__main__":
        create_table()

    # In[289]:

    # 数据存储
    # 定义注释
    table_comment = "重点站点页-累计回本进度统计"
    column_comments = {
        'siteNum': '站点编号',
        'pieChartData1': '静态投资回收进度',
        'pieChartData2': '设备折旧进度',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table3,
        table_name="dp_KeyStation_Cumulative_profit_recovery_progress",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']  # 指定主键
    )

    # ## 月度收支平衡点

    # ### 当月收入计算

    # In[290]:

    # 步骤1：处理df1创建df1_process
    condition = (df1['operation_status'] == '投运') | (df1['station_no'].isin([
        "300003000100002472", "300003000100002473", "300003013200011",
        "300003013200099", "300003013200108"
    ]))
    df1_process = df1[condition].copy()

    print(df1_process.shape)
    print(df1_process.info())

    # In[291]:

    # 步骤2：创建income1基础表
    income1 = df3[df3['station_no'].isin(df1_process['station_no'])][
        ['station_no', 'cba_month', 'revenue', 'cost']
    ].copy()
    print(income1.shape)
    print(income1.info())

    # In[292]:

    # 步骤3：合并parking_fee
    parking_fee_map = df4.set_index('station_no')['parking_fee'].to_dict()
    income1['parking_fee'] = income1['station_no'].map(parking_fee_map)
    print(income1.shape)
    print(income1.info())

    # In[293]:

    # 步骤4：合并merchant_profit_amount
    # 将rec_month转换为与cba_month相同的字符串格式
    df5_temp = df5.copy()
    df5_temp['cba_month'] = df5_temp['rec_month'].astype(str)
    income1 = pd.merge(
        income1,
        df5_temp[['station_no', 'cba_month', 'merchant_profit_amount']],
        on=['station_no', 'cba_month'],
        how='left'
    )

    # In[294]:

    # 步骤5：合并maintenance_cost
    # 将stat_time转换为与cba_month相同的字符串格式
    df6_temp = df6.copy()
    df6_temp['cba_month'] = df6_temp['stat_time'].astype(str)
    income1 = pd.merge(
        income1,
        df6_temp[['station_no', 'cba_month', 'maintenance_cost']],
        on=['station_no', 'cba_month'],
        how='left'
    )
    print(income1.shape)
    print(income1.info())

    # In[295]:

    # 处理缺失值（未匹配到的费用设为0）
    income1['merchant_profit_amount'] = income1['merchant_profit_amount'].fillna(0)
    income1['maintenance_cost'] = income1['maintenance_cost'].fillna(0)
    income1['parking_fee'] = income1['parking_fee'].fillna(0)
    print(income1.shape)
    print(income1.info())

    # In[296]:

    # 步骤6：计算当月收入
    income1['income'] = (income1['revenue'] - income1['cost'] - income1['parking_fee'] - income1['merchant_profit_amount'] - income1['maintenance_cost'])
    print(income1.info())

    # In[297]:

    # 定义目标station_no列表（去重）
    target_stations = ["300003000100019488", "300003000100017539", "300003000100017538", "300003000100019487"]


    # 注意：多个条件用&连接，每个条件需用()包裹
    mask = (income1['station_no'].isin(target_stations)) & (income1['cba_month'] == M )

    # 提取符合条件的行，保留station_no、cba_month、income列（便于核对）
    result = income1[mask][['station_no', 'cba_month', 'income']]

    # 显示结果
    print(result)

    # In[298]:

    # 步骤7：创建income2（最近12个月数据）
    # 计算目标月份范围（从M-11个月到M）
    year = int(M[:4])
    month = int(M[4:6])

    # 生成12个月份的列表（从M-11到M）
    target_months = []
    for i in range(-11, 1):  # 从-11到0（共12个月）
        # 计算相对月份偏移
        total_months = year * 12 + month - 1 + i  # 转换为总月数计算
        offset_year = total_months // 12
        offset_month = total_months % 12 + 1
        target_months.append(f"{offset_year}{offset_month:02d}")

    print(target_months)

    # 筛选数据
    income2 = income1[income1['cba_month'].astype(str).isin(target_months)].copy()
    print(income2.shape)
    print(income2.info())
    print(income2['cba_month'].unique())

    # ### 盈亏平衡点计算

    # In[299]:

    # 第一步：创建balance1表
    # 添加year列
    income1['year'] = income1['cba_month'].astype(str).str[:4]

    # 按station_no和year分组求和
    balance1 = income1.groupby(['station_no', 'year']).agg({
        'revenue': 'sum',
        'cost': 'sum',
        'parking_fee': 'sum',
        'merchant_profit_amount': 'sum',
        'maintenance_cost': 'sum'
    }).reset_index()
    print(balance1.shape)
    print(balance1.info())

    # In[300]:

    # 第二步：匹配total_subsidy
    # 创建df2的映射字典
    subsidy_map = df2.set_index(['station_no', 'year'])['total_subsidy'].to_dict()

    # 匹配到balance1
    balance1['total_subsidy'] = balance1.apply(lambda row: subsidy_map.get((row['station_no'], row['year']), 0), axis=1)
    print(balance1.shape)
    print(balance1.info())

    # In[301]:

    # 第三步：计算except_investment_amount（累计值）
    # 先对每个站点按年份排序
    balance1 = balance1.sort_values(['station_no', 'year'])

    # 创建用于存储累计值的列
    balance1['except_investment_amount'] = 0.0

    # 对每个站点单独计算累计值
    for station in balance1['station_no'].unique():
        # 筛选当前站点的数据
        station_mask = balance1['station_no'] == station
        station_df = balance1[station_mask].copy()

        # 初始化累计值
        cum_revenue = 0.0
        cum_cost = 0.0
        cum_parking = 0.0
        cum_merchant = 0.0
        cum_maintenance = 0.0
        cum_subsidy = 0.0

        # 按年份顺序计算累计值
        for i, row in station_df.iterrows():
            # 计算到当前年份之前的累计值
            balance1.at[i, 'except_investment_amount'] = (
                    cum_subsidy +
                    cum_revenue -
                    cum_cost -
                    cum_parking -
                    cum_merchant -
                    cum_maintenance
            )

            # 更新累计值（加上当前年份的值）
            cum_revenue += row['revenue']
            cum_cost += row['cost']
            cum_parking += row['parking_fee']
            cum_merchant += row['merchant_profit_amount']
            cum_maintenance += row['maintenance_cost']
            cum_subsidy += row['total_subsidy']

    print(balance1.shape)
    print(balance1.info())

    # In[302]:

    # 第四步：匹配investment_amount和commissioning_time
    # 创建df1的映射字典
    investment_map = df1.set_index('station_no')['investment_amount'].to_dict()
    commissioning_map = df1.set_index('station_no')['commissioning_time'].to_dict()

    # 匹配到balance1
    balance1['investment_amount'] = balance1['station_no'].map(investment_map)
    balance1['commissioning_time'] = balance1['station_no'].map(commissioning_map)

    print(balance1.shape)
    print(balance1.info())

    # In[303]:

    # 第五步：计算投运时间和累计月份

    # 确保commissioning_time是字符串类型
    if not pd.api.types.is_string_dtype(balance1['commissioning_time']):
        balance1['commissioning_time'] = balance1['commissioning_time'].astype(str)

    # 提取投运时间的前7个字符（格式：YYYY-MM）并删除横杠
    balance1['投运时间'] = balance1['commissioning_time'].str[:7].str.replace('-', '')

    # # 对于转换失败的记录，填充默认值
    # balance1['投运时间'] = balance1['投运时间'].fillna('190001')

    # 计算今年之前的累计投运月份
    def calculate_prev_months(row):
        try:
            # 提取投运年份和月份
            start_str = row['投运时间']
            if len(start_str) < 6:  # 确保字符串长度足够
                return 0
            start_year = int(start_str[:4])
            start_month = int(start_str[4:6])

            # 提取当前年份
            current_year = int(row['year'])

            # 计算到去年12月的累计月份
            end_year = current_year - 1
            end_month = 12

            # 计算总月份数
            total_months = (end_year - start_year) * 12 + (end_month - start_month + 1)

            # 确保结果非负
            return max(total_months, 0)
        except Exception as e:
            # 打印错误行和错误信息
            print(f"Error in row: station_no={row['station_no']}, year={row['year']}, commissioning_time={row['commissioning_time']}")
            print(f"Error details: {e}")
            return 0  # 返回默认值

    balance1['今年之前的累计投运月份'] = balance1.apply(calculate_prev_months, axis=1)

    # 验证结果
    print(balance1.shape)
    print(balance1.info())

    # In[304]:

    # 第六步：创建balance2表
    balance2 = balance1[['station_no', 'year', 'total_subsidy', 'except_investment_amount', 'investment_amount', '今年之前的累计投运月份']].copy()

    # In[305]:

    # 第七步：处理技改站点
    balance3 = balance2.copy()
    mapping = {
        "300003013200108": "300003000100019488",
        "300003000100002472": "300003000100017539",
        "300003000100002473": "300003000100017538",
        "300003013200011": "300003000100019487",
        "300003013200099": "300003000100019487"
    }

    # 定义需要替换的目标列（除了investment_amount全都替换）
    target_cols = ['station_no', 'year', 'total_subsidy', 'except_investment_amount', '今年之前的累计投运月份']

    # 替换技改站点数据
    for old_val, new_val in mapping.items():
        # 获取新站点的数据（只取第一行）
        new_data = balance3[balance3['station_no'] == new_val].iloc[0] if not balance3[balance3['station_no'] == new_val].empty else None

        if new_data is not None:
            # 替换旧站点的数据
            mask = balance3['station_no'] == old_val
            balance3.loc[mask, 'station_no'] = new_val
            balance3.loc[mask, 'year'] = new_data['year']
            balance3.loc[mask, 'total_subsidy'] = new_data['total_subsidy']
            balance3.loc[mask, 'except_investment_amount'] = new_data['except_investment_amount']
            balance3.loc[mask, '今年之前的累计投运月份'] = new_data['今年之前的累计投运月份']

    # 分组聚合（investment_amount求和，其他取最大值）
    balance4 = balance3.groupby(['station_no', 'year']).agg({
        'total_subsidy': 'max',
        'except_investment_amount': 'max',
        'investment_amount': 'sum',
        '今年之前的累计投运月份': 'max'
    }).reset_index()

    # 验证结果
    print(balance4.shape)
    print(balance4.info())

    # In[306]:

    count = len(balance4[balance4['今年之前的累计投运月份'] > 96])
    print(f"'今年之前的累计投运月份'大于96的记录共有 {count} 条")

    # In[307]:

    # 第八步：计算balance（盈亏平衡点）
    balance4['balance'] = (balance4['investment_amount'] - balance4['total_subsidy'] - balance4['except_investment_amount']) / (8 * 12 - balance4['今年之前的累计投运月份'])

    # 将balance和'今年之前的累计投运月份'同时匹配到income2
    # 添加income2的year列
    income2['year'] = income2['cba_month'].astype(str).str[:4]

    # 创建匹配键
    income2['match_key'] = income2['station_no'].astype(str) + '_' + income2['year'].astype(str)
    balance4['match_key'] = balance4['station_no'].astype(str) + '_' + balance4['year'].astype(str)

    # 创建包含两列的映射字典
    columns_map = balance4.set_index('match_key')[['balance', '今年之前的累计投运月份']].to_dict('index')

    # 同时匹配两列到income2
    income2['balance'] = income2['match_key'].apply(lambda x: columns_map.get(x, {}).get('balance'))
    income2['今年之前的累计投运月份'] = income2['match_key'].apply(lambda x: columns_map.get(x, {}).get('今年之前的累计投运月份'))

    # 清理临时列
    income2.drop(['year', 'match_key'], axis=1, inplace=True)

    # 验证结果
    print(income2.shape)
    print(income2.info())

    # In[308]:

    # 统计balance列值小于0的记录数量
    count_negative_balance = income2[income2['balance'] < 0].shape[0]

    # 打印结果
    print(f"balance列值小于0的记录共有 {count_negative_balance} 个")

    # In[309]:

    # 删除balance列为空的行
    income2 = income2.dropna(subset=['balance'])

    # 验证结果
    print(income2.shape)
    print(income2.info())
    print(income2['cba_month'].unique())

    # In[310]:

    # 检查指定列的空值数量
    null_check = income2[['station_no', 'cba_month']].isnull().sum()

    # 打印结果
    print("空值统计:")
    print(null_check)

    # 检查是否存在任何空值
    if null_check.any():
        print("\n存在空值")
    else:
        print("\n没有空值")

    # ### 前端格式转换

    # In[311]:

    import json  # 需要导入 json 模块

    # 步骤1: 生成axisData（始终不变）
    axisData = [str(int(month[4:])) + "月" for month in target_months]  # 去除前导零

    # 确保income2包含以下列: 'station_no', '今年之前的累计投运月份', 'balance', 'income', 'cba_month'

    # 创建data10中站点回本进度的映射字典
    recovery_progress_dict = data10.set_index('station_no')['静态资金回本进度'].to_dict()

    # 按站点分组处理
    results = []
    for site_num, group in income2.groupby('station_no'):
        # 获取该站点的回本进度
        recovery_progress = recovery_progress_dict.get(site_num, 0)

        # 判断1：回本进度=0
        if recovery_progress == 0:
            results.append({
                "siteNum": site_num,
                "barChartData": {
                    "axisData": axisData,
                    "chartData": [[0] * 12, [0] * 12],
                    "legendName": ["当月毛利", "站点盈亏平衡点"],
                    "yAxisLeftName": "元",
                    "yAxisRightName": "元"
                },
                "profitPoint": {
                    "content": [{"title": "此站点缺少初始投资金额的数据", "value": ""}],
                    "remark": "备注:盈亏平衡点是指在预设8年回收周期条件下，站点运营期间的总成本(含初始投资)均摊至每月后的单位成本值，当月收入达到该值时即实现收支平衡"
                },
                "month": M
            })
            # 将字典转换为 JSON 字符串
            results[-1]["barChartData"] = json.dumps(results[-1]["barChartData"], ensure_ascii=False)
            results[-1]["profitPoint"] = json.dumps(results[-1]["profitPoint"], ensure_ascii=False)
            continue  # 跳过后续处理

        # 判断2：回本进度>100
        if recovery_progress > 100:
            results.append({
                "siteNum": site_num,
                "barChartData": {
                    "axisData": axisData,
                    "chartData": [[0] * 12, [0] * 12],
                    "legendName": ["当月毛利", "站点盈亏平衡点"],
                    "yAxisLeftName": "元",
                    "yAxisRightName": "元"
                },
                "profitPoint": {
                    "content": [{"title": "此站点已回本", "value": ""}],
                    "remark": "备注:盈亏平衡点是指在预设8年回收周期条件下，站点运营期间的总成本(含初始投资)均摊至每月后的单位成本值，当月收入达到该值时即实现收支平衡"
                },
                "month": M
            })
            # 将字典转换为 JSON 字符串
            results[-1]["barChartData"] = json.dumps(results[-1]["barChartData"], ensure_ascii=False)
            results[-1]["profitPoint"] = json.dumps(results[-1]["profitPoint"], ensure_ascii=False)
            continue  # 跳过后续处理

        # 获取最新月份数据（target_months最后一个月份对应的数据）
        latest_data = group.iloc[-1] if not group.empty else None

        # 判断3：运营时长>96个月
        if latest_data is not None and latest_data['今年之前的累计投运月份'] > 96:
            results.append({
                "siteNum": site_num,
                "barChartData": {
                    "axisData": axisData,
                    "chartData": [[0] * 12, [0] * 12],
                    "legendName": ["当月毛利", "站点盈亏平衡点"],
                    "yAxisLeftName": "元",
                    "yAxisRightName": "元"
                },
                "profitPoint": {
                    "content": [{"title": "此站点累计运营时长已超过八年", "value": ""}],
                    "remark": "备注:盈亏平衡点是指在预设8年回收周期条件下，站点运营期间的总成本(含初始投资)均摊至每月后的单位成本值，当月收入达到该值时即实现收支平衡"
                },
                "month": M
            })
            # 将字典转换为 JSON 字符串
            results[-1]["barChartData"] = json.dumps(results[-1]["barChartData"], ensure_ascii=False)
            results[-1]["profitPoint"] = json.dumps(results[-1]["profitPoint"], ensure_ascii=False)
            continue  # 跳过后续处理

        # 判断4：balance<0且静态资金回本进度≥100
        elif latest_data is not None and latest_data['balance'] < 0 and recovery_progress >= 100:
            results.append({
                "siteNum": site_num,
                "barChartData": {
                    "axisData": axisData,
                    "chartData": [[0] * 12, [0] * 12],
                    "legendName": ["当月毛利", "站点盈亏平衡点"],
                    "yAxisLeftName": "元",
                    "yAxisRightName": "元"
                },
                "profitPoint": {
                    "content": [{"title": "此站点已回本", "value": ""}],
                    "remark": "备注:盈亏平衡点是指在预设8年回收周期条件下，站点运营期间的总成本(含初始投资)均摊至每月后的单位成本值，当月收入达到该值时即实现收支平衡"
                },
                "month": M
            })
            # 将字典转换为 JSON 字符串
            results[-1]["barChartData"] = json.dumps(results[-1]["barChartData"], ensure_ascii=False)
            results[-1]["profitPoint"] = json.dumps(results[-1]["profitPoint"], ensure_ascii=False)
            continue  # 跳过后续处理

        # 判断5：balance<0且静态资金回本进度<100
        elif latest_data is not None and latest_data['balance'] < 0 and recovery_progress < 100:
            # 按target_months顺序填充income和balance
            income_vals = [0] * 12
            balance_vals = [0] * 12

            # 创建月份到索引位置的映射
            month_to_index = {month: idx for idx, month in enumerate(target_months)}

            # 填充实际数据
            for _, row in group.iterrows():
                if row['cba_month'] in month_to_index:
                    idx = month_to_index[row['cba_month']]
                    income_vals[idx] = row['income']
                    balance_vals[idx] = row['balance']

            # 修改balance_vals：让balance＜0的值等于该cba_month前面balance＞0的值
            last_positive_balance = None
            for i in range(len(balance_vals)):
                if balance_vals[i] > 0:
                    last_positive_balance = balance_vals[i]
                elif balance_vals[i] < 0 and last_positive_balance is not None:
                    balance_vals[i] = last_positive_balance

            # 获取cba_month中的年份
            cba_years = set()
            for cba in group['cba_month']:
                if pd.notna(cba) and len(str(cba)) >= 4:
                    year = str(cba)[:4]
                    cba_years.add(year)

            # 对年份排序
            sorted_years = sorted(cba_years)

            # 准备平衡点值
            year_values = []
            for year in sorted_years:
                # 获取该年最新的cba_month记录
                year_records = group[group['cba_month'].astype(str).str.startswith(year)]
                if not year_records.empty:
                    # 找到该年最大的月份
                    max_month = year_records['cba_month'].max()
                    # 获取该月份的balance值
                    balance_val = year_records[year_records['cba_month'] == max_month]['balance'].values[0]
                    year_values.append(balance_val)  # 这里先不转换为字符串，用于后续判断

            # 构建标题和值
            if len(sorted_years) > 1:
                year_title = f"{sorted_years[0]}/{sorted_years[1]}年"
                if len(year_values) >= 2:
                    # 检查第二个值是否为负数
                    if year_values[1] < 0:
                        year_value = f"{int(year_values[0])}元"  # 只显示第一个值
                    else:
                        year_value = f"{int(year_values[0])}元/{int(year_values[1])}元"
                else:
                    year_value = "--元/--元"
            elif sorted_years:
                year_title = f"{sorted_years[0]}年"
                year_value = f"{int(year_values[0])}元" if year_values else "--元"
            else:
                year_title = "----/----年"
                year_value = "--元/--元"

            # 计算盈利/亏损月份
            profit_months = []
            loss_months = []

            # 只考虑有实际数据的月份
            for _, row in group.iterrows():
                if row['cba_month'] in month_to_index:
                    month_str = axisData[month_to_index[row['cba_month']]]
                    if row['income'] >= row['balance']:
                        profit_months.append(month_str)
                    else:
                        loss_months.append(month_str)

            profit_str = "、".join(profit_months) if profit_months else "--月"
            loss_str = "、".join(loss_months) if loss_months else "--月"

            # 更新后的content结构
            bar_chart_data = {
                "axisData": axisData,
                "chartData": [income_vals, balance_vals],
                "legendName": ["当月毛利", "站点盈亏平衡点"],
                "yAxisLeftName": "元",
                "yAxisRightName": "元"
            }

            profit_point_data = {
                "content": [
                    {"title": "此站点曾达成回本，当前已回落至未回本", "value": ""},
                    {"title": f"{year_title}站点盈亏平衡点", "value": year_value},
                    {"title": "达到盈亏平衡点", "value": profit_str},
                    {"title": "未达到盈亏平衡点", "value": loss_str}
                ],
                "remark": "备注:盈亏平衡点是指在预设8年回收周期条件下，站点运营期间的总成本(含初始投资)均摊至每月后的单位成本值，当月收入达到该值时即实现收支平衡"
            }

            results.append({
                "siteNum": site_num,
                "barChartData": json.dumps(bar_chart_data, ensure_ascii=False),
                "profitPoint": json.dumps(profit_point_data, ensure_ascii=False),
                "month": M
            })
            continue

        # 判断6：正常站点
        else:
            # 按target_months顺序填充income和balance
            income_vals = [0] * 12
            balance_vals = [0] * 12

            # 创建月份到索引位置的映射
            month_to_index = {month: idx for idx, month in enumerate(target_months)}

            # 填充实际数据
            for _, row in group.iterrows():
                if row['cba_month'] in month_to_index:
                    idx = month_to_index[row['cba_month']]
                    income_vals[idx] = row['income']
                    balance_vals[idx] = row['balance']

            # 获取cba_month中的年份
            cba_years = set()
            for cba in group['cba_month']:
                if pd.notna(cba) and len(str(cba)) >= 4:
                    year = str(cba)[:4]
                    cba_years.add(year)

            # 对年份排序
            sorted_years = sorted(cba_years)

            # 准备平衡点值
            year_values = []
            for year in sorted_years:
                # 获取该年最新的cba_month记录
                year_records = group[group['cba_month'].astype(str).str.startswith(year)]
                if not year_records.empty:
                    # 找到该年最大的月份
                    max_month = year_records['cba_month'].max()
                    # 获取该月份的balance值
                    balance_val = year_records[year_records['cba_month'] == max_month]['balance'].values[0]
                    year_values.append(str(int(balance_val)))

            # 构建标题和值
            if len(sorted_years) > 1:
                year_title = f"{sorted_years[0]}/{sorted_years[1]}年"
                year_value = f"{year_values[0]}元/{year_values[1]}元" if len(year_values) >= 2 else "--元/--元"
            elif sorted_years:
                year_title = f"{sorted_years[0]}年"
                year_value = f"{year_values[0]}元" if year_values else "--元"
            else:
                year_title = "----/----年"
                year_value = "--元/--元"

            # 计算盈利/亏损月份
            profit_months = []
            loss_months = []

            # 只考虑有实际数据的月份
            for _, row in group.iterrows():
                if row['cba_month'] in month_to_index:
                    month_str = axisData[month_to_index[row['cba_month']]]
                    if row['income'] >= row['balance']:
                        profit_months.append(month_str)
                    else:
                        loss_months.append(month_str)

            profit_str = "、".join(profit_months) if profit_months else "--月"
            loss_str = "、".join(loss_months) if loss_months else "--月"

            # 更新后的content结构
            bar_chart_data = {
                "axisData": axisData,
                "chartData": [income_vals, balance_vals],
                "legendName": ["当月毛利", "站点盈亏平衡点"],
                "yAxisLeftName": "元",
                "yAxisRightName": "元"
            }

            profit_point_data = {
                "content": [
                    {"title": f"{year_title}站点盈亏平衡点", "value": year_value},
                    {"title": "达到盈亏平衡点", "value": profit_str},
                    {"title": "未达到盈亏平衡点", "value": loss_str}
                ],
                "remark": "备注:盈亏平衡点是指在预设8年回收周期条件下，站点运营期间的总成本(含初始投资)均摊至每月后的单位成本值，当月收入达到该值时即实现收支平衡"
            }

            results.append({
                "siteNum": site_num,
                "barChartData": json.dumps(bar_chart_data, ensure_ascii=False),
                "profitPoint": json.dumps(profit_point_data, ensure_ascii=False),
                "month": M
            })

    # 创建最终表，每行包含一个站点的完整数据
    Database_Table5 = pd.DataFrame(results)

    # 输出结果
    Database_Table5

    # In[312]:

    Database_Table5.drop_duplicates(subset=['siteNum', 'month'])

    # ### 数据存储

    # In[313]:

    import pymysql
    from pymysql.cursors import DictCursor

    def create_table():
        # 数据库连接配置
        conn = pymysql.connect(
            host='192.168.0.223',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4'  # 确保支持特殊字符
        )

        try:
            with conn.cursor() as cursor:
                # 创建表的SQL语句，使用LONGTEXT类型存储长文本
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS dp_KeyStation_Break_even_point (
                    data LONGTEXT COMMENT '六大维度对比数据',
                    month VARCHAR(6) COMMENT '分析年月，格式建议为YYYYMM'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='六大维度对比数据表';
                """

                # 执行SQL语句
                cursor.execute(create_table_sql)
                print("表创建成功或已存在")

            # 提交事务
            conn.commit()

        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"创建表时发生错误: {e}")
        finally:
            # 关闭数据库连接
            if conn:
                conn.close()

    if __name__ == "__main__":
        create_table()

    # In[314]:

    # 数据存储
    # 定义注释

    print(Database_Table5.head(5))


    table_comment = "重点站点页-月度收支平衡点"
    column_comments = {
        'siteNum': '站点编号',
        'barChartData': '图中数据',
        'profitPoint': '右边数据及备注',
        'month': '分析年月'
    
    }

   
    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table5,
        table_name="dp_KeyStation_Break_even_point",
        table_comment=table_comment,
        column_comments=column_comments,
       # primary_keys=['month']  # 指定主键
       primary_keys=['siteNum', 'month']  # 指定主键
    )

    # ## 重点站点基础信息概览

    # ### 四川电动数据合并

    # In[315]:

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

    # In[316]:

    # 筛选当前四川电动旗下投运状态的全量站点数据+技改站
    basic1 = df7[((df7['operation_status'] == '投运') |
                  (df7['station_no'].isin(["300003000100002472",
                                           "300003000100002473",
                                           "300003013200011",
                                           "300003013200099",
                                           "300003013200108"])))]
    print(basic1.shape)
    basic1.head(1)

    # In[317]:

    # 保留basic1中的station_category，删除df8中的station_category
    df8 = df8.drop(columns=['station_category', 'station_name'])
    # 合并站点电量、电费、服务费的数据
    basic2 = pd.merge(basic1, df8, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', basic2.shape)
    basic2.head(1)

    # #### 单枪日均充电量计算

    # In[318]:

    # 动态计算月份天数（兼容闰年）
    basic2['month_days'] = basic2['cba_month'].apply(
        lambda x: pd.Timestamp(int(str(x)[:4]), int(str(x)[-2:]), 1).days_in_month
        if pd.notna(x) and str(x).isdigit() and len(str(x)) >= 6 else 0
    )

    # 单枪日均充电量=月充电量 / (当月天数 × 枪数量)
    basic2['daily_charge_per_point'] = np.where(
        (basic2['month_days'] > 0) & (basic2['ac_dc_charge_point_count'] > 0),
        basic2['plat_data_charging_volume'] / (basic2['month_days'] * basic2['ac_dc_charge_point_count']),
        np.nan
    )

    # 将NaN值设为0
    basic2['daily_charge_per_point'] = basic2['daily_charge_per_point'].fillna(0)
    print(basic2.shape)
    basic2.head(1)

    # #### 单枪日均充电量的环比计算

    # In[319]:

    # 创建副本避免修改原始数据
    basic2 = basic2.copy()

    # 初始化新列，默认值为 NaN
    basic2['charge_per_point_mom'] = np.nan

    # 步骤1: 为上月数据设置环比为0
    basic2.loc[basic2['cba_month'] == previous_month_str, 'charge_per_point_mom'] = 0

    # 步骤2: 计算当月数据的环比
    # 获取所有需要计算环比的站点列表
    stations = basic2['station_no'].unique()

    # 循环处理每个站点
    for station in stations:
        # 获取该站点当前月的数据
        current_month_data = basic2[(basic2['station_no'] == station) & (basic2['cba_month'] == M)]

        # 获取该站点上月的数据
        previous_month_data = basic2[(basic2['station_no'] == station) & (basic2['cba_month'] == previous_month_str)]

        # 只有当上月和当月数据都存在时才计算环比
        if not current_month_data.empty and not previous_month_data.empty:
            # 提取单枪日均充电量值
            current_value = current_month_data['daily_charge_per_point'].values[0]
            previous_value = previous_month_data['daily_charge_per_point'].values[0]

            # 避免除数为零
            if previous_value != 0:
                mom = (current_value - previous_value) / previous_value
            else:
                # 上月值为0的特殊情况，设置为0
                mom = 0

            # 更新环比值
            basic2.loc[(basic2['station_no'] == station) & (basic2['cba_month'] == M), 'charge_per_point_mom'] = mom

    # 步骤3: 处理特殊情况 - 当月有数据但上月无数据
    # 对于这些站点，环比设为0
    mask_current = (basic2['cba_month'] == M) & (basic2['charge_per_point_mom'].isna())
    basic2.loc[mask_current, 'charge_per_point_mom'] = 0

    # 步骤4: 格式化环比为百分比
    basic2['charge_per_point_mom'] = (basic2['charge_per_point_mom'] * 100).round(2)

    # 验证结果
    print("\n单枪日均充电量环比计算完成:")
    print(f"上月({previous_month_str})数据量: {len(basic2[basic2['cba_month'] == previous_month_str])}")
    print(f"当月({M})数据量: {len(basic2[basic2['cba_month'] == M])}")
    print(f"已计算环比的数据量: {len(basic2[basic2['cba_month'] == M].dropna(subset=['charge_per_point_mom']))}")
    print(basic2.shape)
    print(basic2.info())

    # #### 度电服务费计算

    # In[320]:

    # 添加新列：度电服务费
    basic2['service_fee_per_kwh'] = np.where(
        basic2['plat_data_charging_volume'] == 0,  # 检查月充电量是否为0
        0,  # 如果为0，则服务费设为0
        basic2['rec_data_service_fee_revenue'] / basic2['plat_data_charging_volume']  # 否则计算服务费/充电量
    )

    # 输出验证信息
    print(f"度电服务费为0的: {len(basic2[basic2['service_fee_per_kwh'] == 0])}")
    print(f"月充电量为0的: {len(basic2[basic2['plat_data_charging_volume'] == 0])}")
    print(basic2.shape)
    print(basic2.info())
    basic2.head(1)

    # #### 度电服务费的环比计算

    # In[321]:

    # 创建数据副本避免修改原始数据
    basic2 = basic2.copy()

    # 初始化新列，默认值为 NaN
    basic2['service_fee_per_kwh_mom'] = np.nan

    # 步骤1: 为上月数据设置环比为0
    basic2.loc[basic2['cba_month'] == previous_month_str, 'service_fee_per_kwh_mom'] = 0

    # 步骤2: 计算当月数据的环比
    # 获取所有需要计算环比的场站列表
    stations = basic2['station_no'].unique()

    # 循环处理每个场站
    for station in stations:
        # 获取该场站当前月的数据
        current_month_data = basic2[(basic2['station_no'] == station) & (basic2['cba_month'] == M)]

        # 获取该场站上月的数据
        previous_month_data = basic2[(basic2['station_no'] == station) & (basic2['cba_month'] == previous_month_str)]

        # 只有当上月和当月数据都存在时才计算环比
        if not current_month_data.empty and not previous_month_data.empty:
            # 提取度电服务费值
            current_fee = current_month_data['service_fee_per_kwh'].values[0]
            previous_fee = previous_month_data['service_fee_per_kwh'].values[0]

            # 避免除数为零
            if previous_fee != 0:
                mom = (current_fee - previous_fee) / previous_fee
            else:
                # 上月值为0的特殊情况，设置为0
                mom = 0

            # 更新环比值
            basic2.loc[(basic2['station_no'] == station) & (basic2['cba_month'] == M), 'service_fee_per_kwh_mom'] = mom

    # 步骤3: 处理特殊情况 - 当月有数据但上月无数据
    # 对于这些场站，环比设为0
    mask_current = (basic2['cba_month'] == M) & (basic2['service_fee_per_kwh_mom'].isna())
    basic2.loc[mask_current, 'service_fee_per_kwh_mom'] = 0

    # 步骤4: 格式化环比为百分比
    basic2['service_fee_per_kwh_mom'] = (basic2['service_fee_per_kwh_mom'] * 100).round(2)

    # 输出验证信息
    print("度电服务费环比计算完成:")
    print(f"上月({previous_month_str})数据量: {len(basic2[basic2['cba_month'] == previous_month_str])}")
    print(f"当月({M})数据量: {len(basic2[basic2['cba_month'] == M])}")
    print(f"已计算环比的数据量: {len(basic2[basic2['cba_month'] == M].dropna(subset=['service_fee_per_kwh_mom']))}")
    print(f"环比为0的数据量: {len(basic2[basic2['service_fee_per_kwh_mom'] == 0])}")
    print(basic2.shape)
    print(basic2.info())
    basic2.head(1)

    # In[322]:

    # 记录删除前的行数
    original_count = len(basic2)

    # 删除指定月份的行
    basic2 = basic2[basic2['cba_month'] != previous_month_str]

    # 验证结果
    print(f"删除行数: {original_count - len(basic2)}")
    print(basic2.shape)
    print(basic2.info())

    # ### 外部竞争站点平均水平计算

    # #### 月充电量平均水平

    # In[323]:

    # 步骤1: 计算每个dd_station_id的平均充电量
    com_avg = df9.groupby('dd_station_id')['electricity_quantity'].mean()
    com_avg.name = 'com_avg_cost_elec_cons'  # 直接命名Series

    print(f"计算了 {len(com_avg)} 个场站的平均值")

    # 步骤2: 将结果映射到basic2
    original_count = len(basic2)
    basic2['com_avg_cost_elec_cons'] = basic2['station_no'].map(com_avg)

    # 步骤3: 处理缺失值
    # 统计无法匹配的数量
    unmatched_count = basic2['com_avg_cost_elec_cons'].isna().sum()
    print(f"无法匹配的场站数量: {unmatched_count}")

    # 用0填充缺失值
    basic2['com_avg_cost_elec_cons'] = basic2['com_avg_cost_elec_cons'].fillna(0)

    # 步骤4: 验证结果
    print(basic2.shape)

    # #### 月充电服务费平均水平

    # In[324]:

    # 步骤1：计算月充电服务费：将service_fee列与electricity_quantity列相乘
    df9['service_fee_month'] = df9['service_fee'] * df9['electricity_quantity']

    # 步骤2: 计算每个dd_station_id的平均充电服务费
    com_service_avg = df9.groupby('dd_station_id')['service_fee_month'].mean()
    com_service_avg.name = 'com_avg_data_service_fee_revenue'  # 直接命名Series

    print(f"计算了 {len(com_service_avg)} 个场站的平均值")

    # 步骤3: 将结果映射到basic2
    original_count = len(basic2)
    basic2['com_avg_data_service_fee_revenue'] = basic2['station_no'].map(com_service_avg)

    # 步骤4: 处理缺失值
    # 统计无法匹配的数量
    unmatched_count = basic2['com_avg_data_service_fee_revenue'].isna().sum()

    # 用0填充缺失值
    basic2['com_avg_data_service_fee_revenue'] = basic2['com_avg_data_service_fee_revenue'].fillna(0)
    print(f"无法匹配的场站数量: {unmatched_count}")

    # 步骤5: 验证结果
    print(basic2.shape)
    print(basic2.info())
    basic2.head(1)

    # #### 竞争站点单枪日均充电量计算

    # In[325]:

    # 日期处理函数（YYYYMM格式）
    def get_days_in_month(date_str):
        try:
            y = int(str(date_str)[:4])
            m = int(str(date_str)[4:6])
            return pd.Timestamp(y, m, 1).days_in_month
        except:
            return 0

    # 计算月天数
    df9['days_in_month'] = df9['date'].apply(get_days_in_month)

    # 确保创建浮点类型的列
    df9 = df9.assign(com_daily_charge_per_point=0.0)

    # 计算单枪日均充电量
    valid_mask = (
            df9['electricity_quantity'].notna() &
            df9['charging_num'].notna() &
            (df9['charging_num'] > 0) &
            (df9['days_in_month'] > 0)
    )

    df9.loc[valid_mask, 'com_daily_charge_per_point'] = (
            df9.loc[valid_mask, 'electricity_quantity'].astype(float) /
            (df9.loc[valid_mask, 'charging_num'].astype(float) *
             df9.loc[valid_mask, 'days_in_month'].astype(float))
    )

    # 验证结果
    print(df9.shape)
    print(df9.info())
    df9.head(1)

    # #### 单枪日均充电量平均水平

    # In[326]:

    # 步骤1：计算每个dd_station_id的平均单枪日均充电量
    com_avg = df9[df9['com_daily_charge_per_point'] != 0].groupby('dd_station_id')['com_daily_charge_per_point'].mean()
    com_avg.name = 'com_avg_daily_charge_per_point'  # 直接命名Series

    # 步骤2：将结果映射到basic2
    # 使用map方法避免创建额外列
    basic2['com_avg_daily_charge_per_point'] = basic2['station_no'].map(com_avg)

    # 步骤3：统计未匹配数量并填充0
    unmatched_count = basic2['com_avg_daily_charge_per_point'].isna().sum()
    basic2['com_avg_daily_charge_per_point'] = basic2['com_avg_daily_charge_per_point'].fillna(0)

    # 步骤4：输出结果
    print(f"成功匹配站点数: {len(basic2) - unmatched_count}")
    print(f"未匹配站点数: {unmatched_count} (已填充为0)")
    print(basic2.shape)
    print(basic2.info())

    # #### 竞争站点度电服务费匹配

    # In[327]:

    df9 = df9.rename(columns={'service_fee': 'com_service_fee_per_kwh'})

    # 验证结果
    print(df9.shape)
    print(df9.info())
    df9.head(1)

    # In[328]:

    # 步骤1：计算每个dd_station_id的平均度电服务费
    com_avg = df9[df9['com_service_fee_per_kwh'] != 0].groupby('dd_station_id')['com_service_fee_per_kwh'].mean()
    com_avg.name = 'com_avg_service_fee_per_kwh'
    # 步骤2：将结果映射到basic2
    # 使用map方法避免创建额外列
    basic2['com_avg_service_fee_per_kwh'] = basic2['station_no'].map(com_avg)

    # 步骤3：统计未匹配数量并填充0
    unmatched_count = basic2['com_avg_service_fee_per_kwh'].isna().sum()
    basic2['com_avg_service_fee_per_kwh'] = basic2['com_avg_service_fee_per_kwh'].fillna(0)

    # 步骤4：输出结果
    print(f"成功匹配站点数: {len(basic2) - unmatched_count}")
    print(f"未匹配站点数: {unmatched_count} (已填充为0)")

    print(basic2.shape)
    print(basic2.info())

    # #### 技改站点数据合并

    # In[329]:

    # 步骤1: 从data11中提取所需列
    data10_subset = data10[['station_no', 'investment_amount', '设备折旧进度', '静态资金回本进度']]

    # 步骤2: 使用内连接合并basic2和data10_subset
    basic3 = pd.merge(
        basic2,
        data10_subset,
        on='station_no',
        how='inner'  # 内连接，只保留两表共有的station_no
    )
    print(basic3.shape)
    print(basic3.info())

    # ### 单瓦造价计算

    # In[330]:

    # 添加新列pricePkW（单瓦造价）
    basic3['pricePkW'] = 0.0  # 初始化为0.0

    # 创建有效计算掩码（只处理站点容量大于0的记录）
    valid_mask = (
            basic3['investment_amount'].notna() &
            basic3['station_capacity'].notna() &
            (basic3['station_capacity'] > 0)  # 只处理容量大于0的站点
    )

    # 对有效记录计算单瓦造价
    basic3.loc[valid_mask, 'pricePkW'] = (
            basic3.loc[valid_mask, 'investment_amount'] /
            (basic3.loc[valid_mask, 'station_capacity'] * 1000)
    )
    print(basic3.shape)
    print(basic3.info())

    # ### 单瓦效益计算

    # 单瓦效益=单瓦收入-单瓦支出  单瓦收入=当月的运营收入/额定功率  单瓦支出=（当月的运营支出+当月运维费+当月租金）/额定功率

    # In[331]:

    # 1. 筛选income1中cba_month等于M的行
    filtered_income = income1[income1['cba_month'] == M][['station_no', 'income']]

    # 2. 通过station_no将筛选结果与basic3匹配，并添加income列
    basic3 = basic3.merge(filtered_income, on='station_no', how='left')

    # In[332]:

    # 单瓦效益计算
    basic3['benefits'] = basic3.apply(
        lambda row: row['income'] / row['station_capacity'] / 1000 if row['station_capacity'] != 0 else 0,
        axis=1
    )
    print(basic3.shape)
    print(basic3.info())

    # In[333]:

    def check_all_columns_for_inf(df):
        """
        检查DataFrame所有数值列中的无穷大值

        参数:
        df: pandas DataFrame

        返回:
        包含每列无穷大值数量的Series
        """
        # 选择数值列
        numeric_columns = df.select_dtypes(include=[np.number]).columns

        # 检查每个数值列中的无穷大值
        inf_counts = {}
        for col in numeric_columns:
            inf_counts[col] = np.isinf(df[col]).sum()

        # 创建Series并过滤掉没有无穷大值的列
        inf_series = pd.Series(inf_counts)
        inf_series = inf_series[inf_series > 0]

        if len(inf_series) > 0:
            print("以下列包含无穷大值:")
            print(inf_series)
        else:
            print("所有数值列中均未发现无穷大值")

        return inf_series

    # 使用示例
    inf_results = check_all_columns_for_inf(basic3)

    # In[334]:

    # 将无穷大值替换为 0
    basic3['service_fee_revenue_mom'] = basic3['service_fee_revenue_mom'].replace([np.inf, -np.inf], 0)

    # In[335]:

    # 检查指定列的空值数量
    null_check = basic3[['station_name', 'station_no', 'station_category', 'operation_status']].isnull().sum()

    # 打印结果
    print("空值统计:")
    print(null_check)

    # 检查是否存在任何空值
    if null_check.any():
        print("\n存在空值")
    else:
        print("\n没有空值")

    # In[336]:

    # 所有数据保留两位小数
    basic3['pricePkW'] = basic3['pricePkW'].round(2)
    basic3['benefits'] = basic3['benefits'].round(2)
    basic3['设备折旧进度'] = basic3['设备折旧进度'].round(2)
    basic3['静态资金回本进度'] = basic3['静态资金回本进度'].round(2)
    basic3['plat_data_charging_volume'] = basic3['plat_data_charging_volume'].round(2)
    basic3['cost_elec_cons_mom'] = basic3['cost_elec_cons_mom'].round(2)
    basic3['com_avg_cost_elec_cons'] = basic3['com_avg_cost_elec_cons'].round(2)
    basic3['daily_charge_per_point'] = basic3['daily_charge_per_point'].round(2)
    basic3['charge_per_point_mom'] = basic3['charge_per_point_mom'].round(2)
    basic3['com_avg_daily_charge_per_point'] = basic3['com_avg_daily_charge_per_point'].round(2)
    basic3['rec_data_elec_fee_revenue'] = basic3['rec_data_elec_fee_revenue'].round(2)
    basic3['rec_cost_elec_fee'] = basic3['rec_cost_elec_fee'].round(2)
    basic3['dif_in_elec'] = basic3['dif_in_elec'].round(2)
    basic3['rec_data_service_fee_revenue'] = basic3['rec_data_service_fee_revenue'].round(2)
    basic3['service_fee_revenue_mom'] = basic3['service_fee_revenue_mom'].round(2)
    basic3['com_avg_data_service_fee_revenue'] = basic3['com_avg_data_service_fee_revenue'].round(2)
    basic3['service_fee_per_kwh'] = basic3['service_fee_per_kwh'].round(2)
    basic3['service_fee_per_kwh_mom'] = basic3['service_fee_per_kwh_mom'].round(2)
    basic3['com_avg_service_fee_per_kwh'] = basic3['com_avg_service_fee_per_kwh'].round(2)

    # ### 前端格式转换

    # In[337]:

    import json  # 需要导入 json 模块

    # 创建站点名称筛选器（去重）
    siteNameFilters = list(basic3['station_name'].unique())

    # 创建站点类型筛选器（去重）
    siteTypeFilters = list(basic3['station_category'].unique())

    # 将筛选器列表转换为 JSON 字符串
    siteNameFilters_json = json.dumps(siteNameFilters, ensure_ascii=False)
    siteTypeFilters_json = json.dumps(siteTypeFilters, ensure_ascii=False)

    # 按静态资金回本进度降序排序
    basic3_sorted = basic3.sort_values('静态资金回本进度', ascending=False)

    # 构建表数据（按排序后的顺序）
    tableData = []
    for _, row in basic3_sorted.iterrows():  # 使用排序后的DataFrame
        site_data = {
            "siteNameFilters": siteNameFilters_json,  # 使用转换后的 JSON 字符串
            "siteTypeFilters": siteTypeFilters_json,  # 使用转换后的 JSON 字符串
            "siteNum": row['station_no'],
            "siteName": row['station_name'],
            "siteType": row['station_category'],
            "ratedPower": row['station_capacity'],
            "ChargingCablesNum": row['ac_dc_charge_point_count'],
            "singleWattCost": row['pricePkW'],
            "singleWattBenefits": row['benefits'],
            "recoveryProgress": row['静态资金回本进度'],
            "depreciationProgress": row['设备折旧进度'],
            "monthlyChargeValue": row['plat_data_charging_volume'],
            "monthlyChargeChain": row['cost_elec_cons_mom'],
            "monthlyChargeAverage": row['com_avg_cost_elec_cons'],
            "SingleGunValue": row['daily_charge_per_point'],
            "SingleGunChain": row['charge_per_point_mom'],
            "SingleGunAverage": row['com_avg_daily_charge_per_point'],
            "monthlyCharge": row['rec_data_elec_fee_revenue'],
            "monthlyPayment": row['rec_cost_elec_fee'],
            "electricityBillDifference": row['dif_in_elec'],
            "serviceChargeValue": row['rec_data_service_fee_revenue'],
            "serviceChargeChain": row['service_fee_revenue_mom'],
            "serviceChargeAverage": row['com_avg_data_service_fee_revenue'],
            "electricityValue": row['service_fee_per_kwh'],
            "electricityChain": row['service_fee_per_kwh_mom'],
            "electricityAverage": row['com_avg_service_fee_per_kwh'],
            "month": M  # 添加月份列
        }
        tableData.append(site_data)

    # 创建最终结果表
    Database_Table2 = pd.DataFrame(tableData)

    # 输出结果
    Database_Table2

    # ### 数据存储

    # In[338]:

    import pymysql
    from pymysql.cursors import DictCursor

    def create_table():
        # 数据库连接配置
        conn = pymysql.connect(
            host='192.168.0.223',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4'  # 确保支持特殊字符
        )

        try:
            with conn.cursor() as cursor:
                # 创建表的SQL语句，使用LONGTEXT类型存储长文本
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS dp_KeyStation_Cumulative_profit_recovery_progress (
                    result LONGTEXT COMMENT '六大维度对比数据',
                    month VARCHAR(6) COMMENT '分析年月，格式建议为YYYYMM'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='六大维度对比数据表';
                """

                # 执行SQL语句
                cursor.execute(create_table_sql)
                print("表创建成功或已存在")

            # 提交事务
            conn.commit()

        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"创建表时发生错误: {e}")
        finally:
            # 关闭数据库连接
            if conn:
                conn.close()

    if __name__ == "__main__":
        create_table()

    # In[339]:

    # 数据存储
    # 定义注释
    table_comment = "重点站点页-重点站点基础信息概览"
    column_comments = {
        'siteNameFilters': '站点名称筛选器',
        'siteTypeFilters': '站点类型筛选器',
        'siteNum': '站点编号',
        'siteName': '站点名称',
        'siteType': '站点类型',
        'ratedPower': '站容量',
        'ChargingCablesNum': '充电枪数量',
        'singleWattCost': '单瓦造价',
        'singleWattBenefits': '单瓦效益',
        'recoveryProgress': '静态投资回收进度',
        'depreciationProgress': '设备折旧进度',
        'monthlyChargeValue': '月充电量-当月数值',
        'monthlyChargeChain': '月充电量-环比',
        'monthlyChargeAverage': '月充电量-外部竞争',
        'SingleGunValue': '单枪日均充电量-当月数值',
        'SingleGunChain': '单枪日均充电量-环比',
        'SingleGunAverage': '单枪日均充电量-外部竞争',
        'monthlyCharge': '月充电电费',
        'monthlyPayment': '月缴纳电费',
        'electricityBillDifference': '度电电费差',
        'serviceChargeValue': '月充电服务费-当月数值',
        'serviceChargeChain': '月充电服务费-环比',
        'serviceChargeAverage': '月充电服务费-外部竞争',
        'electricityValue': '度电服务费-当月数值',
        'electricityChain': '度电服务费-环比',
        'electricityAverage': '度电服务费-外部竞争',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table2,
        table_name="dp_KeyStation_Basic_Information",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # ## 内部竞争力

    # ### 排名函数定义

    # In[340]:

    # 排名函数
    def Rank(D, C, C1):
        D_1 = D[D['station_category'] == '高速公共']
        D_1 = D_1.copy()
        D_1[C1] = D_1[C].rank(ascending=False, method='dense').astype('Int64')
        D_2 = D[D['station_category'] == '城市公共']
        D_2 = D_2.copy()
        D_2[C1] = D_2[C].rank(ascending=False, method='dense').astype('Int64')
        D_3 = D[D['station_category'] == '重卡专用']
        D_3 = D_3.copy()
        D_3[C1] = D_3[C].rank(ascending=False, method='dense').astype('Int64')
        return D_1, D_2, D_3

    # ### TOPSIS函数定义

    # In[341]:

    # 定义TOPSIS函数
    def cal_topsis(d, name, w):
        d1 = d.copy()
        l = d1[name]  # 保留标签列
        del d1[name]

        # 指标正向化处理（假设电量损耗是负向指标）
        # 注意：电量损耗需要取倒数正向化
        if 'electrical_loss_1' in d1.columns:
            d1['electrical_loss_1'] = 1 / d1['electrical_loss_1']  # 负向指标正向化

        # 归一化处理
        d1 = pd.DataFrame(MinMaxScaler().fit_transform(d1), columns=d1.columns)

        # 计算正负理想
        Z = pd.DataFrame([d1.min(), d1.max()], index=['负理想解', '正理想解'])

        # 计算距离（使用权重）
        result = d1.copy()
        result['负理想解距离'] = np.sqrt(((d1 - Z.loc['负理想解']) ** 2 * w).sum(axis=1))
        result['正理想解距离'] = np.sqrt(((d1 - Z.loc['正理想解']) ** 2 * w).sum(axis=1))

        # 计算综合得分 - 添加零分母保护
        denominator = result['负理想解距离'] + result['正理想解距离']
        # 当分母为零时（所有值相同），设置得分为0.5
        result['综合得分'] = np.where(denominator > 0, result['负理想解距离'] / denominator, 0.5)

        # 调整分数范围
        scaler = MinMaxScaler(feature_range=(60, 100))
        result['综合得分(调整)'] = scaler.fit_transform(result[['综合得分']])

        # 计算排名
        result['排名'] = result['综合得分(调整)'].rank(ascending=False, method='dense').astype(int)

        # 插入标识列
        result.insert(0, name, l)
        return result

    # In[377]:

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
    AND DATE_FORMAT(cs.commissioning_time, '%Y%m') < '{}'
    """.format(M)
    DF_SCDD = SQL(sql)

    # ### 建设规模

    # In[378]:

    

    DF_SCDD['charge_point_count'] = (DF_SCDD['charge_point_count'].apply(lambda x:x if isinstance(x,str) else '直流0|交流0').apply(lambda x:x if '|' in x else '直流0|交流0').apply(lambda x:x.split('|')[0].replace('直流','').strip()).apply(lambda x:int(x)if x.isdigit() else 0) + DF_SCDD['charge_point_count'].apply(lambda x : x if isinstance (x,str) else '直流0|交流0').apply(lambda x:x if '|' in x else '直流0|交流0').apply(lambda x:x.split('|')[0].replace('直流','').strip()).apply(lambda x:int(x)if x.isdigit() else 0))
    # 将总桩数列转换为float格式
    DF_SCDD['charge_point_count'] = DF_SCDD['charge_point_count'].astype(float)
    DF_SCDD['charge_point_count_kW'] = DF_SCDD['station_capacity'] / DF_SCDD['charge_point_count'].replace(0,np.nan)
    DF_SCDD['charge_point_count_kW'] = DF_SCDD['charge_point_count_kW'].replace([np.inf,-np.inf],np.nan).fillna(0)

    print(DF_SCDD.info())

    # #### 桩数量

    # In[379]:

    charge_point_count_1, charge_point_count_2, charge_point_count_3 = Rank(DF_SCDD, 'charge_point_count', 'point_count_rank')

    # #### 单桩额定功率

    # In[380]:

    charge_point_count_kW_rank_1, charge_point_count_kW_rank_2, charge_point_count_kW_rank_3 = Rank(DF_SCDD, 'charge_point_count_kW', 'charge_point_count_kW_rank')

    # In[381]:

    # 建立新表并提取指定列
    df_build_1 = charge_point_count_kW_rank_1[['station_no', 'station_category', 'station_name', 'charge_point_count_kW', 'charge_point_count_kW_rank']].copy()
    df_build_2 = charge_point_count_kW_rank_2[['station_no', 'station_category', 'station_name', 'charge_point_count_kW', 'charge_point_count_kW_rank']].copy()
    df_build_3 = charge_point_count_kW_rank_3[['station_no', 'station_category', 'station_name', 'charge_point_count_kW', 'charge_point_count_kW_rank']].copy()

    # 匹配charge_point_count_1的指定列到df_build_1，基于station_no进行匹配
    df_build_1 = df_build_1.merge(charge_point_count_1[['station_no', 'charge_point_count', 'point_count_rank']], on='station_no', how='left')
    df_build_2 = df_build_2.merge(charge_point_count_2[['station_no', 'charge_point_count', 'point_count_rank']], on='station_no', how='left')
    df_build_3 = df_build_3.merge(charge_point_count_3[['station_no', 'charge_point_count', 'point_count_rank']], on='station_no', how='left')

    # In[382]:

    # 计算三个子集的平均值（保留2位小数）
    df_build_1_avg1 = round(df_build_1['charge_point_count'].mean(), 2)
    df_build_2_avg1 = round(df_build_2['charge_point_count'].mean(), 2)
    df_build_3_avg1 = round(df_build_3['charge_point_count'].mean(), 2)

    df_build_1_avg2 = round(df_build_1['charge_point_count_kW'].mean(), 2)
    df_build_2_avg2 = round(df_build_2['charge_point_count_kW'].mean(), 2)
    df_build_3_avg2 = round(df_build_3['charge_point_count_kW'].mean(), 2)

    print(df_build_1.info())
    print(df_build_2.info())
    print(df_build_3.info())

    # #### 前端格式转换

    # In[383]:

    import json  # 需要导入 json 模块

    def generate_axis_chart_data(df, station_no, rank_col, value_col):
        """生成axisData和chartData"""
        # 按排名排序（保留原始顺序处理重复排名）
        sorted_df = df.sort_values(by=rank_col, ascending=True)
        total_stations = len(df)

        # 获取前三名
        top3 = sorted_df.head(3)
        axis_data = []
        chart_data = []
        included_station_nos = set()

        # 添加前三名
        for i, (_, row) in enumerate(top3.iterrows(), 1):
            axis_data.append(f"TOP{i} {row['station_name']}")
            chart_data.append(row[value_col])
            included_station_nos.add(row['station_no'])

        # 获取当前站点的信息
        current_row = df[df['station_no'] == station_no].iloc[0]
        itself_name = f"TOP{current_row[rank_col]} {current_row['station_name']}"

        # 添加当前站点（如果不在前三且站点数>3）
        if total_stations > 3 and station_no not in included_station_nos:
            axis_data.append(itself_name)
            chart_data.append(current_row[value_col])

        # 反转axisData和chartData的顺序
        axis_data.reverse()
        chart_data.reverse()

        return axis_data, [chart_data], itself_name

    def generate_bar_chart_data(df, station_no, source_name, avg_dict):
        """为单个站点生成barChartData"""
        bar_chart_data = []

        # 桩数量
        axis_data, chart_data, itself_name = generate_axis_chart_data(
            df, station_no, "point_count_rank", "charge_point_count"
        )
        bar_chart_data.append({
            "radio": "桩数量",
            "legendName": ["桩数量："],
            "axisData": axis_data,
            "itselfName": itself_name,
            "chartData": chart_data,
            "yAxisName": "个",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["桩数量"])
        })

        # 单桩功率
        axis_data, chart_data, itself_name = generate_axis_chart_data(
            df, station_no, "charge_point_count_kW_rank", "charge_point_count_kW"
        )
        bar_chart_data.append({
            "radio": "单桩功率",
            "legendName": ["单桩功率："],
            "axisData": axis_data,
            "itselfName": itself_name,
            "chartData": chart_data,
            "yAxisName": "kW",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["单桩功率"])
        })

        return bar_chart_data

    # 创建平均值映射字典
    avg_dict = {
        "df_build_1": {
            "桩数量": df_build_1_avg1,
            "单桩功率": df_build_1_avg2
        },
        "df_build_2": {
            "桩数量": df_build_2_avg1,
            "单桩功率": df_build_2_avg2
        },
        "df_build_3": {
            "桩数量": df_build_3_avg1,
            "单桩功率": df_build_3_avg2
        }
    }

    # 将options转换为JSON字符串
    options_json = json.dumps(["桩数量", "单桩功率"], ensure_ascii=False)

    # 生成最终数据
    final_data = []

    # 处理df_build_1（高速公共）
    for station_no in df_build_1['station_no']:
        bar_chart_data = generate_bar_chart_data(df_build_1, station_no, "df_build_1", avg_dict)
        # 将BarChartData转换为JSON字符串
        bar_chart_data_json = json.dumps(bar_chart_data, ensure_ascii=False)

        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": bar_chart_data_json,  # 使用转换后的JSON字符串
            "month": M  # 添加月份列
        })

    # 处理df_build_2（城市公共）
    for station_no in df_build_2['station_no']:
        bar_chart_data = generate_bar_chart_data(df_build_2, station_no, "df_build_2", avg_dict)
        # 将BarChartData转换为JSON字符串
        bar_chart_data_json = json.dumps(bar_chart_data, ensure_ascii=False)

        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": bar_chart_data_json,  # 使用转换后的JSON字符串
            "month": M  # 添加月份列
        })

    # 处理df_build_3（重卡专用）
    for station_no in df_build_3['station_no']:
        bar_chart_data = generate_bar_chart_data(df_build_3, station_no, "df_build_3", avg_dict)
        # 将BarChartData转换为JSON字符串
        bar_chart_data_json = json.dumps(bar_chart_data, ensure_ascii=False)

        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": bar_chart_data_json,  # 使用转换后的JSON字符串
            "month": M  # 添加月份列
        })

    # 创建最终DataFrame
    Database_Table9 = pd.DataFrame(final_data)

    # 输出结果
    Database_Table9

    # #### 数据存储

    # In[384]:

    import pymysql
    from pymysql.cursors import DictCursor

    def create_table():
        # 数据库连接配置
        conn = pymysql.connect(
            host='192.168.0.223',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4'  # 确保支持特殊字符
        )

        try:
            with conn.cursor() as cursor:
                # 创建表的SQL语句，使用LONGTEXT类型存储长文本
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS dp_KeyStation_Internal_competitiveness_Build (
                    data LONGTEXT COMMENT '六大维度对比数据',
                    month VARCHAR(6) COMMENT '分析年月，格式建议为YYYYMM'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='六大维度对比数据表';
                """

                # 执行SQL语句
                cursor.execute(create_table_sql)
                print("表创建成功或已存在")

            # 提交事务
            conn.commit()

        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"创建表时发生错误: {e}")
        finally:
            # 关闭数据库连接
            if conn:
                conn.close()

    if __name__ == "__main__":
        create_table()

    # In[385]:

    # 数据存储
    # 定义注释
    table_comment = "重点站点页-内部竞争力-建设规模"
    column_comments = {
        'siteNum': '站点编号',
        'options': '筛选器',
        'BarChartData': '条形图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table9,
        table_name="dp_KeyStation_Internal_competitiveness_Build",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # ### 经济效益

    # In[386]:

    # 步骤1：提取需要的列到新DataFrame
    DF_ECO = data10[['station_no', 'station_name', 'station_category', '设备折旧进度', '静态资金回本进度']].copy()

    # 将'静态资金回本进度'列中的inf和-inf替换为0
    DF_ECO['静态资金回本进度'] = DF_ECO['静态资金回本进度'].replace(np.inf, 0)
    DF_ECO['静态资金回本进度'] = DF_ECO['静态资金回本进度'].replace([np.inf, -np.inf], 0)

    # 找出DF_SCDD中存在但DF_ECO中不存在的站点
    mask = ~DF_SCDD[['station_no', 'station_name']].apply(tuple, axis=1).isin(DF_ECO[['station_no', 'station_name']].apply(tuple, axis=1))
    new_stations = DF_SCDD.loc[mask, ['station_no', 'station_name', 'station_category']].copy()

    # 添加缺失的列并填充默认值
    new_stations['设备折旧进度'] = 0.0
    new_stations['静态资金回本进度'] = 0.0

    # 将新行追加到DF_ECO（保持原有列顺序）
    DF_ECO = pd.concat([DF_ECO, new_stations], ignore_index=True)

    # 步骤2：使用Rank函数对两个进度指标分别排序
    # 对设备折旧进度排序
    D1_1, D1_2, D1_3 = Rank(DF_ECO, '设备折旧进度', '设备折旧进度_rank')

    # 对静态资金回本进度排序
    D2_1, D2_2, D2_3 = Rank(DF_ECO, '静态资金回本进度', '静态资金回本进度_rank')

    # 创建三个独立的DataFrame
    # 高速公共站点
    df_eco1 = D1_1[['station_no', 'station_name', 'station_category', '设备折旧进度', '设备折旧进度_rank']]
    df_eco1 = df_eco1.merge(D2_1[['station_no', '静态资金回本进度', '静态资金回本进度_rank']], on='station_no', how='left')

    # 城市公共站点
    df_eco2 = D1_2[['station_no', 'station_name', 'station_category', '设备折旧进度', '设备折旧进度_rank']]
    df_eco2 = df_eco2.merge(D2_2[['station_no', '静态资金回本进度', '静态资金回本进度_rank']], on='station_no', how='left')

    # 重卡专用站点
    df_eco3 = D1_3[['station_no', 'station_name', 'station_category', '设备折旧进度', '设备折旧进度_rank']]
    df_eco3 = df_eco3.merge(D2_3[['station_no', '静态资金回本进度', '静态资金回本进度_rank']], on='station_no', how='left')

    # 步骤3：在每个DataFrame中计算经济效益得分
    df_eco1['经济效益得分'] = df_eco1['静态资金回本进度'] - df_eco1['设备折旧进度']
    df_eco2['经济效益得分'] = df_eco2['静态资金回本进度'] - df_eco2['设备折旧进度']
    df_eco3['经济效益得分'] = df_eco3['静态资金回本进度'] - df_eco3['设备折旧进度']

    # 步骤4：在每个DataFrame中应用TOPSIS算法
    # 高速公共站点
    # 高速公共站点
    topsis_df1 = df_eco1[['station_no', '经济效益得分']].copy()
    print("topsis_df1 shape:", topsis_df1.shape)
    print(topsis_df1.head())  # 看前几行数据
    topsis_result1 = cal_topsis(topsis_df1, 'station_no', [1])
    df_eco1 = df_eco1.merge(topsis_result1[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 城市公共站点
    topsis_df2 = df_eco2[['station_no', '经济效益得分']].copy()
    print("topsis_df2 shape:", topsis_df2.shape)
    print(topsis_df2.head())
    topsis_result2 = cal_topsis(topsis_df2, 'station_no', [1])
    df_eco2 = df_eco2.merge(topsis_result2[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 重卡专用站点
    topsis_df3 = df_eco3[['station_no', '经济效益得分']].copy()
    print("topsis_df3 shape:", topsis_df3.shape)
    print(topsis_df3.head())
    topsis_result3 = cal_topsis(topsis_df3, 'station_no', [1])
    df_eco3 = df_eco3.merge(topsis_result3[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')


    # 现在有三个独立的DataFrame：
    # df_eco1 - 高速公共站点
    # df_eco2 - 城市公共站点
    # df_eco3 - 重卡专用站点
    print(df_eco1.info())

    # In[387]:

    # 检查指定列的空值数量
    null_check = df_eco3[['station_name', 'station_no', 'station_category']].isnull().sum()

    # 打印结果
    print("空值统计:")
    print(null_check)

    # 检查是否存在任何空值
    if null_check.any():
        print("\n存在空值")
    else:
        print("\n没有空值")

    # In[388]:

    ### 1. 筛选出data1中investment_amount=0的station_no
    zero_invest_stations = data1[data1['investment_amount'] == 0]['station_no'].unique()

    # 2. 对三个表分别处理：匹配到的station_no将'综合得分(调整)'设为0
    df_eco1.loc[df_eco1['station_no'].isin(zero_invest_stations), '综合得分(调整)'] = 0
    df_eco2.loc[df_eco2['station_no'].isin(zero_invest_stations), '综合得分(调整)'] = 0
    df_eco3.loc[df_eco3['station_no'].isin(zero_invest_stations), '综合得分(调整)'] = 0

    # In[389]:

    # 计算三个子集的平均值（保留2位小数）
    df_eco1_avg1 = round(df_eco1['设备折旧进度'].mean(), 2)
    df_eco2_avg1 = round(df_eco2['设备折旧进度'].mean(), 2)
    df_eco3_avg1 = round(df_eco3['设备折旧进度'].mean(), 2)

    df_eco1_avg2 = round(df_eco1['静态资金回本进度'].mean(), 2)
    df_eco2_avg2 = round(df_eco2['静态资金回本进度'].mean(), 2)
    df_eco3_avg2 = round(df_eco3['静态资金回本进度'].mean(), 2)

    # In[390]:

    # 综合得分平均值（保留2位小数）
    df_eco1_avg = round(df_eco1['综合得分(调整)'].mean(), 2)
    df_eco2_avg = round(df_eco2['综合得分(调整)'].mean(), 2)
    df_eco3_avg = round(df_eco3['综合得分(调整)'].mean(), 2)

    # #### 前端格式转换

    # In[394]:

    import json  # 需要导入json库

    def generate_axis_chart_data(df, station_no, rank_col, value_col):
        """生成axisData和chartData"""
        # 按排名排序
        sorted_df = df.sort_values(by=rank_col, ascending=True)
        total_stations = len(df)

        # 获取前三名
        top3 = sorted_df.head(3)
        axis_data = []
        chart_data = []
        included_station_nos = set()

        # 添加前三名
        for i, (_, row) in enumerate(top3.iterrows(), 1):
            axis_data.append(f"TOP{i} {row['station_name']}")
            chart_data.append(row[value_col])
            included_station_nos.add(row['station_no'])

        # 添加当前站点（如果不在前三且站点数>3）
        current_row = df[df['station_no'] == station_no].iloc[0]
        if total_stations > 3 and station_no not in included_station_nos:
            axis_data.append(f"TOP{current_row[rank_col]} {current_row['station_name']}")
            chart_data.append(current_row[value_col])

        # 反转axisData和chartData的顺序
        axis_data.reverse()
        chart_data.reverse()

        return axis_data, [chart_data], f"TOP{current_row[rank_col]} {current_row['station_name']}"

    def generate_bar_chart_data(df, station_no, source_name, avg_dict):
        """为单个站点生成BarChartData"""
        bar_chart_data = []

        # 经济效益得分
        axis_data, chart_data, itself_name = generate_axis_chart_data(
            df, station_no, "排名", "综合得分(调整)"
        )
        bar_chart_data.append({
            "radio": "经济效益得分",
            "legendName": ["经济效益得分："],
            "axisData": axis_data,
            "itselfName": itself_name,
            "chartData": chart_data,
            "yAxisName": "",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["经济效益得分"]),
            "remark": ["经济效益得分根据静态投资回收进度减去设备折旧进度，通过TOPSIS算法进行评分。"]
        })

        # 静态投资回收进度
        axis_data, chart_data, itself_name = generate_axis_chart_data(
            df, station_no, "静态资金回本进度_rank", "静态资金回本进度"
        )
        bar_chart_data.append({
            "radio": "静态投资回收进度",
            "legendName": ["静态投资回收进度："],
            "axisData": axis_data,
            "itselfName": itself_name,
            "chartData": chart_data,
            "yAxisName": "%",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["静态投资回收进度"]),
            "remark": ["经济效益得分根据静态投资回收进度减去设备折旧进度，通过TOPSIS算法进行评分。"]
        })

        # 设备折旧进度
        axis_data, chart_data, itself_name = generate_axis_chart_data(
            df, station_no, "设备折旧进度_rank", "设备折旧进度"
        )
        bar_chart_data.append({
            "radio": "设备折旧进度",
            "legendName": ["设备折旧进度："],
            "axisData": axis_data,
            "itselfName": itself_name,
            "chartData": chart_data,
            "yAxisName": "%",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["设备折旧进度"]),
            "remark": ["经济效益得分根据静态投资回收进度减去设备折旧进度，通过TOPSIS算法进行评分。"]
        })

        return bar_chart_data

    # 创建平均值映射字典
    avg_dict = {
        "df_eco1": {
            "经济效益得分": df_eco1_avg,
            "静态投资回收进度": df_eco1_avg2,
            "设备折旧进度": df_eco1_avg1
        },
        "df_eco2": {
            "经济效益得分": df_eco2_avg,
            "静态投资回收进度": df_eco2_avg2,
            "设备折旧进度": df_eco2_avg1
        },
        "df_eco3": {
            "经济效益得分": df_eco3_avg,
            "静态投资回收进度": df_eco3_avg2,
            "设备折旧进度": df_eco3_avg1
        }
    }

    # 将options转换为JSON字符串
    options_json = json.dumps(["经济效益得分", "静态投资回收进度", "设备折旧进度"], ensure_ascii=False)

    # 生成最终数据
    final_data = []

    # 处理df_eco1（高速公共）
    for station_no in df_eco1['station_no']:
        bar_chart_data = generate_bar_chart_data(df_eco1, station_no, "df_eco1", avg_dict)
        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": json.dumps(bar_chart_data, ensure_ascii=False),  # 转换为JSON字符串并保留中文字符
            "month": M
        })

    # 处理df_eco2（城市公共）
    for station_no in df_eco2['station_no']:
        bar_chart_data = generate_bar_chart_data(df_eco2, station_no, "df_eco2", avg_dict)
        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": json.dumps(bar_chart_data, ensure_ascii=False),
            "month": M
        })

    # 处理df_eco3（重卡专用）
    for station_no in df_eco3['station_no']:
        bar_chart_data = generate_bar_chart_data(df_eco3, station_no, "df_eco3", avg_dict)
        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": json.dumps(bar_chart_data, ensure_ascii=False),
            "month": M
        })

    # 创建最终DataFrame
    Database_Table6 = pd.DataFrame(final_data)

    # 输出结果
    Database_Table6

    # #### 数据存储

    # In[395]:

    import pymysql
    from pymysql.cursors import DictCursor

    def create_table():
        # 数据库连接配置
        conn = pymysql.connect(
            host='192.168.0.223',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4'  # 确保支持特殊字符
        )

        try:
            with conn.cursor() as cursor:
                # 创建表的SQL语句，使用LONGTEXT类型存储长文本
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS dp_KeyStation_Internal_Economic_benefits (
                    data LONGTEXT COMMENT '六大维度对比数据',
                    month VARCHAR(6) COMMENT '分析年月，格式建议为YYYYMM'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='六大维度对比数据表';
                """

                # 执行SQL语句
                cursor.execute(create_table_sql)
                print("表创建成功或已存在")

            # 提交事务
            conn.commit()

        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"创建表时发生错误: {e}")
        finally:
            # 关闭数据库连接
            if conn:
                conn.close()

    if __name__ == "__main__":
        create_table()

    # In[396]:

    # 数据存储
    # 定义注释
    table_comment = "重点站点页-内部竞争力-经济效益"
    column_comments = {
        'siteNum': '站点编号',
        'options': '筛选器',
        'BarChartData': '条形图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table6,
        table_name="dp_KeyStation_Internal_Economic_benefits",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # ### 设备质量

    # #### 一次成功率

    # In[397]:

    sql = f"""select station_code,success_rate from dp_success_rate
    where stat_time='{M}'"""
    df_success_rate = SQL(sql)

    # In[398]:

    # 空值填充后，转换为浮点数并保留两位小数
    df_success_rate['success_rate'] = df_success_rate['success_rate'].fillna('0%')
    df_success_rate['success_rate'] = df_success_rate['success_rate'].apply(
        lambda x: round(float(x.split('%')[0]), 2)  # 新增round()保留两位小数
    )

    # In[399]:

    df_success_rate_1 = df_success_rate.groupby('station_code').agg({'success_rate': 'mean'}).reset_index()

    # In[400]:

    # 对分组后的平均值也保留两位小数
    df_success_rate_1['success_rate'] = df_success_rate_1['success_rate'].round(2)

    # In[401]:

    df_success_rate_2 = pd.merge(DF_SCDD, df_success_rate_1, left_on='station_no', right_on='station_code', how='left')

    # In[402]:

    df_success_rate_2['success_rate'] = df_success_rate_2['success_rate'].fillna(0)
    # 将'success_rate'列转换为float格式
    df_success_rate_2['success_rate'] = df_success_rate_2['success_rate'].astype(float)

    # In[403]:

    success_rate_rank_1, success_rate_rank_2, success_rate_rank_3 = Rank(df_success_rate_2, 'success_rate', 'success_rate_rank')

    # In[404]:

    print(success_rate_rank_1.shape)
    print(success_rate_rank_2.shape)
    print(success_rate_rank_3.shape)
    success_rate_rank_3.head()

    # In[405]:

    # 计算三个子集的平均值（保留2位小数）
    success_rate_rank_1_avg = round(success_rate_rank_1['success_rate'].mean(), 2)
    success_rate_rank_2_avg = round(success_rate_rank_2['success_rate'].mean(), 2)
    success_rate_rank_3_avg = round(success_rate_rank_3['success_rate'].mean(), 2)

    # #### 设备可用率

    # In[406]:

    sql = f"""
    select time,station_name,station_code,pile_status,normal_duration,operation_duration,city from dp_operation_duration
    where time like '{M}%'
    """
    DF_operation_duration = SQL(sql)

    # In[407]:

    DF_operation_duration['可用率'] = DF_operation_duration['normal_duration'].astype('int') / DF_operation_duration['operation_duration'].astype('int')

    # In[408]:

    DF_operation_duration['可用率'] = (DF_operation_duration['可用率'] * 100).astype(float)

    # In[409]:

    print(DF_operation_duration.info())

    # In[410]:

    DF_operation_duration_1 = DF_operation_duration.groupby('station_code').agg({'可用率': 'mean'}).reset_index()

    # In[411]:

    DF_operation_duration_2 = pd.merge(DF_SCDD, DF_operation_duration_1, left_on='station_no', right_on='station_code', how='left')

    # In[412]:

    DF_operation_duration_2['可用率'] = DF_operation_duration_2['可用率'].fillna(0)

    # In[413]:

    ky_rank_1, ky_rank_2, ky_rank_3 = Rank(DF_operation_duration_2, '可用率', 'ky_rank')

    # In[414]:

    print(ky_rank_1.shape)
    print(ky_rank_2.shape)
    print(ky_rank_3.shape)
    ky_rank_3.head()

    # In[415]:

    # 计算三个子集的平均值（保留2位小数）
    ky_rank_1_avg = round(ky_rank_1['可用率'].mean(), 2)
    ky_rank_2_avg = round(ky_rank_2['可用率'].mean(), 2)
    ky_rank_3_avg = round(ky_rank_3['可用率'].mean(), 2)

    # #### 电量损耗

    # 电损 = 1-平台电量/用电电量
    # 平台电量=station_cba_org_data.plat_data_charging_volume
    # 用电电量=station_cba_org_data.plat_data_charging_volume

    # In[416]:

    sql = f"""
    select * from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and  cs.operation_status in ('投运')) a
    left join 
    (select * from station_cba_org_data where cba_month  ={M} ) b
    on a.station_no =b.station_no
    """
    DF_cba_org_data = SQL(sql)

    # In[417]:

    df_plat_data_charging_volume = DF_cba_org_data[['station_no', 'plat_data_charging_volume', 'rec_cost_elec_cons']].iloc[:, 1:]

    # In[418]:

    df_plat_data_charging_volume_1 = pd.merge(DF_SCDD, df_plat_data_charging_volume, on='station_no', how='left')

    # In[419]:

    DF_volume = DF_cba_org_data[['station_no', 'plat_data_charging_volume', 'rec_cost_elec_cons']].iloc[:, 1:]

    # In[420]:

    DF_volume['plat_data_charging_volume'] = DF_volume['plat_data_charging_volume'].fillna(0)

    # In[421]:

    # 按station_no分组，对plat_data_charging_volume和rec_cost_elec_cons两列分别求和
    DF_volume_1 = DF_volume.groupby(['station_no']).agg(
        {
            'plat_data_charging_volume': 'sum',  # 平台充电量列求和
            'rec_cost_elec_cons': 'sum'  # 电费成本消耗列求和
        }
    ).reset_index()

    # In[422]:

    DF_volume_1 = pd.merge(DF_SCDD, DF_volume_1, on='station_no', how='left')

    # In[423]:

    DF_volume_1 = DF_volume_1[['station_no', 'plat_data_charging_volume', 'rec_cost_elec_cons']]
    print(DF_volume_1.shape)
    print(DF_volume_1.info())

    # In[424]:

    # 从df_plat_data_charging_volume_1中提取需要的列，创建df_electrical_loss
    df_electrical_loss = df_plat_data_charging_volume_1[['merchant_name', 'station_no', 'station_category', 'plat_data_charging_volume', 'rec_cost_elec_cons']].copy()

    # 将DF_volume_1中的trans_energy合并到df_electrical_loss，通过station_no匹配
    # 使用left join确保保留df_electrical_loss的所有行
    df_electrical_loss = pd.merge(df_electrical_loss, DF_volume_1[['station_no', 'plat_data_charging_volume', 'rec_cost_elec_cons']], how='left')
    print(df_electrical_loss.shape)
    print(df_electrical_loss.info())

    # In[425]:

    # 填充空值为0并确保为数值型
    df_electrical_loss['plat_data_charging_volume'] = df_electrical_loss['plat_data_charging_volume'].fillna(0).astype(float)
    df_electrical_loss['rec_cost_elec_cons'] = df_electrical_loss['rec_cost_elec_cons'].fillna(0).astype(float)
    print(df_electrical_loss.shape)
    print(df_electrical_loss.info())

    # In[426]:

    # 计算电损并转换为保留两位小数的百分比形式（无百分号）
    df_electrical_loss['electrical_loss'] = df_electrical_loss.apply(
        lambda row:
        # 用电电量为0时，电损=1（代表100%）
        1 if row['rec_cost_elec_cons'] == 0
        # 正常计算：(1 - 平台电量/用电电量) * 100 并保留两位小数
        else round((1 - (float(row['plat_data_charging_volume']) / float(row['rec_cost_elec_cons']))) * 100, 2),
        axis=1
    )
    print(df_electrical_loss.shape)
    print(df_electrical_loss.info())

    # In[427]:

    electrical_loss_rank_1, electrical_loss_rank_2, electrical_loss_rank_3 = Rank(df_electrical_loss, 'electrical_loss', 'electrical_loss_rank')
    print(electrical_loss_rank_1.info())

    # In[428]:

    # 计算三个子集的平均值（保留2位小数）
    electrical_loss_rank_1_avg = round(electrical_loss_rank_1['electrical_loss'].mean(), 2)
    electrical_loss_rank_2_avg = round(electrical_loss_rank_2['electrical_loss'].mean(), 2)
    electrical_loss_rank_3_avg = round(electrical_loss_rank_3['electrical_loss'].mean(), 2)

    # #### 设备质量得分

    # In[429]:

    # 创建三个表（按充电站类型分类）
    # 高速公共 (df_equip_1)
    df_equip_1 = success_rate_rank_1[['station_name', 'station_no', 'station_category', 'success_rate', 'success_rate_rank']].copy()
    df_equip_1 = pd.merge(df_equip_1, ky_rank_1[['station_no', '可用率', 'ky_rank']], on='station_no', how='left')
    df_equip_1 = pd.merge(df_equip_1, electrical_loss_rank_1[['station_no', 'electrical_loss', 'electrical_loss_rank']], on='station_no', how='left')

    # 城市公共 (df_equip_2)
    df_equip_2 = success_rate_rank_2[['station_name', 'station_no', 'station_category', 'success_rate', 'success_rate_rank']].copy()
    df_equip_2 = pd.merge(df_equip_2, ky_rank_2[['station_no', '可用率', 'ky_rank']], on='station_no', how='left')
    df_equip_2 = pd.merge(df_equip_2, electrical_loss_rank_2[['station_no', 'electrical_loss', 'electrical_loss_rank']], on='station_no', how='left')

    # 重卡专用 (df_equip_3)
    df_equip_3 = success_rate_rank_3[['station_name', 'station_no', 'station_category', 'success_rate', 'success_rate_rank']].copy()
    df_equip_3 = pd.merge(df_equip_3, ky_rank_3[['station_no', '可用率', 'ky_rank']], on='station_no', how='left')
    df_equip_3 = pd.merge(df_equip_3, electrical_loss_rank_3[['station_no', 'electrical_loss', 'electrical_loss_rank']], on='station_no', how='left')

    # 设置均等权重 (三个指标权重均为1/3)
    weights = np.array([1 / 3, 1 / 3, 1 / 3])

    # 分别对三类充电站进行TOPSIS评价
    # 高速公共
    topsis_1 = cal_topsis(df_equip_1[['station_no', 'success_rate', '可用率', 'electrical_loss']].copy(), 'station_no', weights)
    df_equip_1 = pd.merge(df_equip_1, topsis_1[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 城市公共
    topsis_2 = cal_topsis(df_equip_2[['station_no', 'success_rate', '可用率', 'electrical_loss']].copy(), 'station_no', weights)
    df_equip_2 = pd.merge(df_equip_2, topsis_2[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 重卡专用
    topsis_3 = cal_topsis(df_equip_3[['station_no', 'success_rate', '可用率', 'electrical_loss']].copy(), 'station_no', weights)
    df_equip_3 = pd.merge(df_equip_3, topsis_3[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 现在三个数据框都新增了最后两列：综合得分(调整)和排名

    # In[430]:

    # 现在有三个独立的DataFrame：
    # df_equip_1 - 高速公共站点
    # df_equip_2 - 城市公共站点
    # df_equip_3 - 重卡专用站点
    print(df_equip_1.shape)
    print(df_equip_2.shape)
    print(df_equip_3.shape)
    print(df_equip_3.info())

    # In[431]:

    # 计算三个子集的平均值（保留2位小数）
    df_equip_1_avg = round(df_equip_1['综合得分(调整)'].mean(), 2)
    df_equip_2_avg = round(df_equip_2['综合得分(调整)'].mean(), 2)
    df_equip_3_avg = round(df_equip_3['综合得分(调整)'].mean(), 2)

    df_equip_1_avg1 = round(df_equip_1['success_rate'].mean(), 2)
    df_equip_2_avg1 = round(df_equip_2['success_rate'].mean(), 2)
    df_equip_3_avg1 = round(df_equip_3['success_rate'].mean(), 2)

    df_equip_1_avg2 = round(df_equip_1['可用率'].mean(), 2)
    df_equip_2_avg2 = round(df_equip_2['可用率'].mean(), 2)
    df_equip_3_avg2 = round(df_equip_3['可用率'].mean(), 2)

    df_equip_1_avg3 = round(df_equip_1['electrical_loss'].mean(), 2)
    df_equip_2_avg3 = round(df_equip_2['electrical_loss'].mean(), 2)
    df_equip_3_avg3 = round(df_equip_3['electrical_loss'].mean(), 2)

    # #### 前端格式转换

    # In[433]:

    import json  # 需要导入json库

    def generate_axis_chart_data(df, station_no, rank_col, value_col):
        """生成axisData和chartData"""
        # 按排名排序
        sorted_df = df.sort_values(by=rank_col, ascending=True)
        total_stations = len(df)

        # 获取前三名
        top3 = sorted_df.head(3)
        axis_data = []
        chart_data = []
        included_station_nos = set()

        # 添加前三名
        for i, (_, row) in enumerate(top3.iterrows(), 1):
            axis_data.append(f"TOP{i} {row['station_name']}")
            chart_data.append(row[value_col])
            included_station_nos.add(row['station_no'])

        # 获取当前站点的信息
        current_row = df[df['station_no'] == station_no].iloc[0]
        itself_name = f"TOP{current_row[rank_col]} {current_row['station_name']}"

        # 添加当前站点（如果不在前三且站点数>3）
        if total_stations > 3 and station_no not in included_station_nos:
            axis_data.append(itself_name)
            chart_data.append(current_row[value_col])

        # 反转axisData和chartData的顺序
        axis_data.reverse()
        chart_data.reverse()

        return axis_data, [chart_data], itself_name

    def generate_bar_chart_data(df, station_no, source_name, avg_dict):
        """为单个站点生成BarChartData"""
        bar_chart_data = []

        # 设备质量得分
        axis_data, chart_data, itself_name = generate_axis_chart_data(
            df, station_no, "排名", "综合得分(调整)"
        )
        bar_chart_data.append({
            "radio": "设备质量得分",
            "legendName": ["设备质量得分："],
            "axisData": axis_data,
            "itselfName": itself_name,
            "chartData": chart_data,
            "yAxisName": "",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["设备质量得分"]),
            "remark": ["设备质量得分利用均权法为一次成功率、设备可用率、电量损耗三个指标赋权，再通过TOPSISI算法进行评分。"]
        })

        # 一次成功率
        axis_data, chart_data, itself_name = generate_axis_chart_data(
            df, station_no, "success_rate_rank", "success_rate"
        )
        bar_chart_data.append({
            "radio": "一次成功率",
            "legendName": ["一次成功率："],
            "axisData": axis_data,
            "itselfName": itself_name,
            "chartData": chart_data,
            "yAxisName": "%",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["一次成功率"]),
            "remark": ["设备质量得分利用均权法为一次成功率、设备可用率、电量损耗三个指标赋权，再通过TOPSISI算法进行评分。"]
        })

        # 设备可用率
        axis_data, chart_data, itself_name = generate_axis_chart_data(
            df, station_no, "ky_rank", "可用率"
        )
        bar_chart_data.append({
            "radio": "设备可用率",
            "legendName": ["设备可用率："],
            "axisData": axis_data,
            "itselfName": itself_name,
            "chartData": chart_data,
            "yAxisName": "%",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["设备可用率"]),
            "remark": ["设备质量得分利用均权法为一次成功率、设备可用率、电量损耗三个指标赋权，再通过TOPSISI算法进行评分。"]
        })

        # 电量损耗
        axis_data, chart_data, itself_name = generate_axis_chart_data(
            df, station_no, "electrical_loss_rank", "electrical_loss"
        )
        bar_chart_data.append({
            "radio": "电量损耗",
            "legendName": ["电量损耗："],
            "axisData": axis_data,
            "itselfName": itself_name,
            "chartData": chart_data,
            "yAxisName": "%",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["电量损耗"]),
            "remark": ["设备质量得分利用均权法为一次成功率、设备可用率、电量损耗三个指标赋权，再通过TOPSISI算法进行评分。"]
        })

        return bar_chart_data

    # 创建平均值映射字典
    avg_dict = {
        "df_equip_1": {
            "设备质量得分": df_equip_1_avg,
            "一次成功率": df_equip_1_avg1,
            "设备可用率": df_equip_1_avg2,
            "电量损耗": df_equip_1_avg3
        },
        "df_equip_2": {
            "设备质量得分": df_equip_2_avg,
            "一次成功率": df_equip_2_avg1,
            "设备可用率": df_equip_2_avg2,
            "电量损耗": df_equip_2_avg3
        },
        "df_equip_3": {
            "设备质量得分": df_equip_3_avg,
            "一次成功率": df_equip_3_avg1,
            "设备可用率": df_equip_3_avg2,
            "电量损耗": df_equip_3_avg3
        }
    }

    # 将options转换为JSON字符串
    options_json = json.dumps(["设备质量得分", "一次成功率", "设备可用率", "电量损耗"], ensure_ascii=False)

    # 生成最终数据
    final_data = []

    # 处理df_equip_1（高速公共）
    for station_no in df_equip_1['station_no']:
        bar_chart_data = generate_bar_chart_data(df_equip_1, station_no, "df_equip_1", avg_dict)
        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": json.dumps(bar_chart_data, ensure_ascii=False),  # 转换为JSON字符串并保留中文字符
            "month": M  # 添加月份列
        })

    # 处理df_equip_2（城市公共）
    for station_no in df_equip_2['station_no']:
        bar_chart_data = generate_bar_chart_data(df_equip_2, station_no, "df_equip_2", avg_dict)
        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": json.dumps(bar_chart_data, ensure_ascii=False),
            "month": M  # 添加月份列
        })

    # 处理df_equip_3（重卡专用）
    for station_no in df_equip_3['station_no']:
        bar_chart_data = generate_bar_chart_data(df_equip_3, station_no, "df_equip_3", avg_dict)
        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": json.dumps(bar_chart_data, ensure_ascii=False),
            "month": M  # 添加月份列
        })

    # 创建最终DataFrame
    Database_Table7 = pd.DataFrame(final_data)

    # 输出结果
    Database_Table7

    # #### 数据存储

    # In[434]:

    import pymysql
    from pymysql.cursors import DictCursor

    def create_table():
        # 数据库连接配置
        conn = pymysql.connect(
            host='192.168.0.223',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4'  # 确保支持特殊字符
        )

        try:
            with conn.cursor() as cursor:
                # 创建表的SQL语句，使用LONGTEXT类型存储长文本
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS dp_KeyStation_Internal_competitiveness_Equipment_quality (
                    data LONGTEXT COMMENT '六大维度对比数据',
                    month VARCHAR(6) COMMENT '分析年月，格式建议为YYYYMM'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='六大维度对比数据表';
                """

                # 执行SQL语句
                cursor.execute(create_table_sql)
                print("表创建成功或已存在")

            # 提交事务
            conn.commit()

        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"创建表时发生错误: {e}")
        finally:
            # 关闭数据库连接
            if conn:
                conn.close()

    if __name__ == "__main__":
        create_table()

    # In[435]:

    # 数据存储
    # 定义注释
    table_comment = "重点站点页-内部竞争力-设备质量"
    column_comments = {
        'siteNum': '站点编号',
        'options': '筛选器',
        'BarChartData': '条形图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table7,
        table_name="dp_KeyStation_Internal_competitiveness_Equipment_quality",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # ### 使用效率

    # #### 功率利用率

    # In[436]:

    get_days_in_month(M)

    # 查看station_capacity为0的行数
    zero_capacity_count = len(DF_cba_org_data[DF_cba_org_data['station_capacity'] == 0])
    print(zero_capacity_count)

    # In[437]:

    DF_cba_org_data['pue'] = DF_cba_org_data['plat_data_charging_volume'].astype(float) / DF_cba_org_data['station_capacity'].astype(float) / 24 / get_days_in_month(M)

    # 将pue列中的inf和-inf替换为0
    DF_cba_org_data['pue'] = DF_cba_org_data['pue'].replace([np.inf, -np.inf], 0)

    # In[438]:

    DF_pue_1 = DF_cba_org_data[['station_no', 'pue']]

    # In[439]:

    DF_pue_1 = DF_pue_1.iloc[:, 1:]

    # In[440]:

    DF_pue_2 = pd.merge(DF_SCDD, DF_pue_1, on='station_no', how='left')

    # In[441]:

    DF_pue_2['pue'] = DF_pue_2['pue'].fillna(0)

    # In[442]:

    DF_pue_2['pue'] = (DF_pue_2['pue'] * 100).astype(float)

    # In[443]:

    pue_rank_1, pue_rank_2, pue_rank_3 = Rank(DF_pue_2, 'pue', 'pue_rank')

    # In[444]:

    print(pue_rank_1.info())

    # #### 时长利用率

    # In[445]:

    # 分别提取两个表的数据
    sql_station = f"""
    select 
        cs.station_no,
        cs.station_category,
        (cs.dc_charge_point_count + cs.ac_charge_point_count) as point_count,
        cs.operation_status 
    from charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where rm.merchant_name = '国网电动汽车服务（四川）有限公司'
        and cs.operation_status in ('投运')
    """

    sql_orders = f"""
    select 
        charging_station_no,
        charging_start_time,
        charging_end_time
    from fin_plat_data_order PARTITION ({'p' + M})
    """

    # 分别获取DataFrame
    DF_station = SQL(sql_station)
    DF_orders = SQL(sql_orders)

    # 在Notebook中进行左连接
    DF_time = DF_station.merge(
        DF_orders,
        left_on='station_no',
        right_on='charging_station_no',
        how='left'
    )

    # 确保列名正确
    DF_time = DF_time[['station_no', 'station_category', 'point_count', 'operation_status',
                       'charging_station_no', 'charging_start_time', 'charging_end_time']]

    print(DF_time.info())

    # In[446]:

    DF_time_1 = DF_time[DF_time['charging_end_time'].notna()]

    # In[447]:

    DF_time_1 = DF_time_1.copy()
    DF_time_1['charging_time'] = DF_time_1['charging_end_time'].apply(lambda x: datetime.strptime(str(x), "%Y-%m-%d %H:%M:%S")) - DF_time_1['charging_start_time'].apply(lambda x: datetime.strptime(str(x), "%Y-%m-%d %H:%M:%S"))

    # In[448]:

    DF_time_1['point_count'] = DF_time_1['point_count'].astype(float)

    # In[449]:

    DF_time_1['charging_time'] = DF_time_1['charging_time'].apply(lambda x: x.total_seconds() / 3600)

    # In[450]:

    # 同时计算每个station_no的总充电时间，同时取相同station_no的point_count的平均值
    DF_time_2 = DF_time_1.groupby('station_no').agg(
        total_charging_time=('charging_time', 'sum'),
        total_point_count=('point_count', 'mean')
    ).reset_index()

    print(DF_time_2.info())

    # In[451]:

    # # 将DF_change添加到DF_time_2后面
    # DF_combined = pd.concat([DF_time_2, DF_change], ignore_index=True)
    # # 合并前的不同站点数量
    # unique_stations_before_df_time_2 = DF_time_2['station_no'].nunique()
    # # 合并后的不同站点数量
    # unique_stations_after = DF_combined['station_no'].nunique()
    # print(f"DF_time_2 中的不同站点数量: {unique_stations_before_df_time_2}")
    # print(f"合并后的数据框中的不同站点数量: {unique_stations_after}")

    # In[452]:

    # 计算时长利用率
    DF_time_2['charging_time_rate'] = DF_time_2['total_charging_time'] / (DF_time_2['total_point_count'] * 24 * days_in_month)

    # In[453]:

    DF_time_2 = pd.merge(DF_SCDD, DF_time_2, on='station_no', how='left')

    # In[454]:

    # 只保留指定的列，其他列会被自动删除
    DF_time_2 = DF_time_2[['merchant_name', 'station_no', 'station_name', 'station_category', 'charging_time_rate']]

    # In[455]:

    DF_time_2['charging_time_rate'] = DF_time_2['charging_time_rate'].fillna(0)

    # In[456]:

    DF_time_2['charging_time_rate'] = (DF_time_2['charging_time_rate'] * 100).astype(float)

    # In[457]:

    charging_time_rate_1, charging_time_rate_2, charging_time_rate_3 = Rank(DF_time_2, 'charging_time_rate', 'charging_time_rate_rank')

    # In[458]:

    print(DF_time_2.info())

    # #### 单枪充电量

    # In[459]:

    # 定义需要排除的station_no列表
    exclude_stations = ["300003000100002472", "300003000100002473", "300003013200011", "300003013200099", "300003013200108"]

    # 筛选出不在排除列表中的行，保存到df_gun_charging_volume
    df_gun_charging_volume = basic2[~basic2['station_no'].isin(exclude_stations)].copy()

    df_gun_charging_volume['daily_charge_per_point'] = df_gun_charging_volume['daily_charge_per_point'].fillna(0)

    gun_charging_volume_rank_1, gun_charging_volume_rank_2, gun_charging_volume_rank_3 = Rank(df_gun_charging_volume, 'daily_charge_per_point', 'daily_charge_per_point_rank')

    # In[460]:

    print(gun_charging_volume_rank_1.shape)
    print(gun_charging_volume_rank_2.shape)
    print(gun_charging_volume_rank_3.shape)

    # #### 功率效能比

    # In[461]:

    # 计算必要的统计量
    pue_mean = DF_cba_org_data['pue'].mean()  # 功率利用率平均值
    pue_max = DF_cba_org_data['pue'].max()  # 功率利用率最大值
    print(pue_mean)
    print(pue_max)
    # 计算功率效能比
    # 公式: (当前pue - pue平均值) / (pue最大值 - pue平均值)
    # 处理分母为0的情况
    if pue_max - pue_mean == 0:
        # 当最大值等于平均值时，所有值相同，效能比设为0
        DF_cba_org_data['pue_max_mean'] = 0.0
    else:
        DF_cba_org_data['pue_max_mean'] = (DF_cba_org_data['pue'] - pue_mean) / (pue_max - pue_mean)

    # DF_cba_org_data表中有两列station_no，此处作相应处理，只保留一列
    # 获取所有列名
    columns = DF_cba_org_data.columns.tolist()
    # 找到第一个名为 'station_no' 的列索引
    station_no_index = columns.index('station_no')

    # 创建新表，只包含第一列 station_no 和其他需要的列
    df_pue_max_mean = DF_cba_org_data.iloc[:, [station_no_index] + [columns.index('station_category'), columns.index('station_name'), columns.index('pue_max_mean')]].copy()

    # 重命名列，避免混淆
    df_pue_max_mean.columns = ['station_no', 'station_category', 'station_name', 'pue_max_mean']

    df_pue_max_mean['pue_max_mean'] = df_pue_max_mean['pue_max_mean'].fillna(0)

    # In[462]:

    # df_pue_max_mean['pue_max_mean'] = (df_pue_max_mean['pue_max_mean'] * 100).astype(float)
    df_pue_max_mean['pue_max_mean'] = df_pue_max_mean['pue_max_mean'].round(2)

    # In[463]:

    pue_max_mean_rank_1, pue_max_mean_rank_2, pue_max_mean_rank_3 = Rank(df_pue_max_mean, 'pue_max_mean', 'pue_max_mean_rank')

    # In[464]:

    print(pue_max_mean_rank_1.shape)
    print(pue_max_mean_rank_2.shape)
    print(pue_max_mean_rank_3.shape)
    print(pue_max_mean_rank_1.info())

    # #### 使用效率得分

    # In[465]:

    # 创建三个表（按充电站类型分类）
    # 高速公共 (df_use_1)
    df_use_1 = pue_rank_1[['station_name', 'station_no', 'station_category', 'pue', 'pue_rank']].copy()
    df_use_1 = pd.merge(df_use_1, charging_time_rate_1[['station_no', 'charging_time_rate', 'charging_time_rate_rank']], on='station_no', how='left')
    df_use_1 = pd.merge(df_use_1, gun_charging_volume_rank_1[['station_no', 'daily_charge_per_point', 'daily_charge_per_point_rank']], on='station_no', how='left')
    df_use_1 = pd.merge(df_use_1, pue_max_mean_rank_1[['station_no', 'pue_max_mean', 'pue_max_mean_rank']], on='station_no', how='left')

    # 城市公共 (df_use_2)
    df_use_2 = pue_rank_2[['station_name', 'station_no', 'station_category', 'pue', 'pue_rank']].copy()
    df_use_2 = pd.merge(df_use_2, charging_time_rate_2[['station_no', 'charging_time_rate', 'charging_time_rate_rank']], on='station_no', how='left')
    df_use_2 = pd.merge(df_use_2, gun_charging_volume_rank_2[['station_no', 'daily_charge_per_point', 'daily_charge_per_point_rank']], on='station_no', how='left')
    df_use_2 = pd.merge(df_use_2, pue_max_mean_rank_2[['station_no', 'pue_max_mean', 'pue_max_mean_rank']], on='station_no', how='left')

    # 重卡专用 (df_use_3)
    df_use_3 = pue_rank_3[['station_name', 'station_no', 'station_category', 'pue', 'pue_rank']].copy()
    df_use_3 = pd.merge(df_use_3, charging_time_rate_3[['station_no', 'charging_time_rate', 'charging_time_rate_rank']], on='station_no', how='left')
    df_use_3 = pd.merge(df_use_3, gun_charging_volume_rank_3[['station_no', 'daily_charge_per_point', 'daily_charge_per_point_rank']], on='station_no', how='left')
    df_use_3 = pd.merge(df_use_3, pue_max_mean_rank_3[['station_no', 'pue_max_mean', 'pue_max_mean_rank']], on='station_no', how='left')

    # 设置均等权重（四个指标权重均为1/4）
    weights = np.array([0.25, 0.25, 0.25, 0.25])

    # 分别对三类充电站进行TOPSIS评价
    # 高速公共
    df_use_1[['pue', 'charging_time_rate', 'daily_charge_per_point', 'pue_max_mean']] = (
        df_use_1[['pue', 'charging_time_rate', 'daily_charge_per_point', 'pue_max_mean']]
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
    )
    topsis_1 = cal_topsis(df_use_1[['station_no', 'pue', 'charging_time_rate', 'daily_charge_per_point', 'pue_max_mean']].copy(), 'station_no', weights)
    df_use_1 = pd.merge(df_use_1, topsis_1[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 城市公共
    df_use_2[['pue', 'charging_time_rate', 'daily_charge_per_point', 'pue_max_mean']] = (
        df_use_2[['pue', 'charging_time_rate', 'daily_charge_per_point', 'pue_max_mean']]
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
    )
    topsis_2 = cal_topsis(df_use_2[['station_no', 'pue', 'charging_time_rate', 'daily_charge_per_point', 'pue_max_mean']].copy(), 'station_no', weights)
    df_use_2 = pd.merge(df_use_2, topsis_2[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 重卡专用
    df_use_3[['pue', 'charging_time_rate', 'daily_charge_per_point', 'pue_max_mean']] = (
        df_use_3[['pue', 'charging_time_rate', 'daily_charge_per_point', 'pue_max_mean']]
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
    )
    topsis_3 = cal_topsis(df_use_3[['station_no', 'pue', 'charging_time_rate', 'daily_charge_per_point', 'pue_max_mean']].copy(), 'station_no', weights)
    df_use_3 = pd.merge(df_use_3, topsis_3[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 现在三个数据框都新增了最后两列：综合得分(调整)和排名

    # In[466]:

    print(df_use_1.shape)
    print(df_use_2.shape)
    print(df_use_3.shape)

    # In[467]:

    # 计算三个子集的平均值（保留2位小数）
    df_use_1_avg = round(df_use_1['综合得分(调整)'].mean(), 2)
    df_use_2_avg = round(df_use_2['综合得分(调整)'].mean(), 2)
    df_use_3_avg = round(df_use_3['综合得分(调整)'].mean(), 2)

    df_use_1_avg1 = round(pue_rank_1['pue'].mean(), 2)
    df_use_2_avg1 = round(pue_rank_2['pue'].mean(), 2)
    df_use_3_avg1 = round(pue_rank_3['pue'].mean(), 2)

    df_use_1_avg2 = round(charging_time_rate_1['charging_time_rate'].mean(), 2)
    df_use_2_avg2 = round(charging_time_rate_2['charging_time_rate'].mean(), 2)
    df_use_3_avg2 = round(charging_time_rate_3['charging_time_rate'].mean(), 2)

    df_use_1_avg3 = round(gun_charging_volume_rank_1['daily_charge_per_point'].mean(), 2)
    df_use_2_avg3 = round(gun_charging_volume_rank_2['daily_charge_per_point'].mean(), 2)
    df_use_3_avg3 = round(gun_charging_volume_rank_3['daily_charge_per_point'].mean(), 2)

    df_use_1_avg4 = round(pue_max_mean_rank_1['pue_max_mean'].mean(), 2)
    df_use_2_avg4 = round(pue_max_mean_rank_1['pue_max_mean'].mean(), 2)
    df_use_3_avg4 = round(pue_max_mean_rank_1['pue_max_mean'].mean(), 2)

    # #### 前端格式转换

    # In[468]:

    import pandas as pd
    import numpy as np
    import json

    def generate_axis_chart_data(df, station_no, rank_col, value_col):
        """生成axisData和chartData"""
        # 按排名排序（保留原始顺序处理重复排名）
        sorted_df = df.sort_values(by=rank_col, ascending=True)
        total_stations = len(df)

        # 获取前三名
        top3 = sorted_df.head(3)
        axis_data = []
        chart_data = []
        included_station_nos = set()

        # 添加前三名
        for i, (_, row) in enumerate(top3.iterrows(), 1):
            axis_data.append(f"TOP{i} {row['station_name']}")
            chart_data.append(row[value_col])
            included_station_nos.add(row['station_no'])

        # 添加当前站点（如果不在前三且站点数>3）
        current_row = df[df['station_no'] == station_no].iloc[0]
        if total_stations > 3 and station_no not in included_station_nos:
            axis_data.append(f"TOP{current_row[rank_col]} {current_row['station_name']}")
            chart_data.append(current_row[value_col])

        # 反转axisData和chartData的顺序
        axis_data.reverse()
        chart_data.reverse()

        return axis_data, [chart_data]

    def generate_bar_chart_data(df, station_no, source_name, avg_dict):
        """为单个站点生成BarChartData"""
        bar_chart_data = []
        remark = [
            '功率效能比=（功率利用率-功率利用率平均值）/(功率利用率最大值-功率利用率平均值）',
            '使用效率得分利用均权法为功率利用率、时长利用率、单枪充电量、功率效能比4个指标赋权，再通过TOPSISI算法进行评分。'
        ]

        # 获取当前站点信息
        current_row = df[df['station_no'] == station_no].iloc[0]

        # 使用效率得分
        axis_data, chart_data = generate_axis_chart_data(
            df, station_no, "排名", "综合得分(调整)"
        )
        itself_name = f"TOP{current_row['排名']} {current_row['station_name']}"
        bar_chart_data.append({
            "radio": "使用效率得分",
            "legendName": ["使用效率得分："],
            "axisData": axis_data,
            "chartData": chart_data,
            "yAxisName": "",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["使用效率得分"]),
            "remark": remark,
            "itselfName": itself_name
        })

        # 功率利用率
        axis_data, chart_data = generate_axis_chart_data(
            df, station_no, "pue_rank", "pue"
        )
        itself_name = f"TOP{current_row['pue_rank']} {current_row['station_name']}"
        bar_chart_data.append({
            "radio": "功率利用率",
            "legendName": ["功率利用率："],
            "axisData": axis_data,
            "chartData": chart_data,
            "yAxisName": "%",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["功率利用率"]),
            "remark": remark,
            "itselfName": itself_name
        })

        # 时长利用率
        axis_data, chart_data = generate_axis_chart_data(
            df, station_no, "charging_time_rate_rank", "charging_time_rate"
        )
        itself_name = f"TOP{current_row['charging_time_rate_rank']} {current_row['station_name']}"
        bar_chart_data.append({
            "radio": "时长利用率",
            "legendName": ["时长利用率："],
            "axisData": axis_data,
            "chartData": chart_data,
            "yAxisName": "%",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["时长利用率"]),
            "remark": remark,
            "itselfName": itself_name
        })

        # 单枪日均充电量
        axis_data, chart_data = generate_axis_chart_data(
            df, station_no, "daily_charge_per_point_rank", "daily_charge_per_point"
        )
        itself_name = f"TOP{current_row['daily_charge_per_point_rank']} {current_row['station_name']}"
        bar_chart_data.append({
            "radio": "单枪日均充电量",
            "legendName": ["单枪日均充电量："],
            "axisData": axis_data,
            "chartData": chart_data,
            "yAxisName": "kWh",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["单枪日均充电量"]),
            "remark": remark,
            "itselfName": itself_name
        })

        # 功率效能比
        axis_data, chart_data = generate_axis_chart_data(
            df, station_no, "pue_max_mean_rank", "pue_max_mean"
        )
        itself_name = f"TOP{current_row['pue_max_mean_rank']} {current_row['station_name']}"
        bar_chart_data.append({
            "radio": "功率效能比",
            "legendName": ["功率效能比："],
            "axisData": axis_data,
            "chartData": chart_data,
            "yAxisName": "",
            "markLineName": "平均值",
            "xAxis": str(avg_dict[source_name]["功率效能比"]),
            "remark": remark,
            "itselfName": itself_name
        })

        return bar_chart_data

    # 创建平均值映射字典
    avg_dict = {
        "df_use_1": {
            "使用效率得分": df_use_1_avg,
            "功率利用率": df_use_1_avg1,
            "时长利用率": df_use_1_avg2,
            "单枪日均充电量": df_use_1_avg3,
            "功率效能比": df_use_1_avg4
        },
        "df_use_2": {
            "使用效率得分": df_use_2_avg,
            "功率利用率": df_use_2_avg1,
            "时长利用率": df_use_2_avg2,
            "单枪日均充电量": df_use_2_avg3,
            "功率效能比": df_use_2_avg4
        },
        "df_use_3": {
            "使用效率得分": df_use_3_avg,
            "功率利用率": df_use_3_avg1,
            "时长利用率": df_use_3_avg2,
            "单枪日均充电量": df_use_3_avg3,
            "功率效能比": df_use_3_avg4
        }
    }

    # 将options转换为JSON字符串
    options_json = json.dumps(["使用效率得分", "功率利用率", "时长利用率", "单枪日均充电量", "功率效能比"], ensure_ascii=False)

    # 生成最终数据
    final_data = []

    # 处理df_use_1（高速公共）
    for station_no in df_use_1['station_no']:
        bar_chart_data = generate_bar_chart_data(df_use_1, station_no, "df_use_1", avg_dict)
        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": json.dumps(bar_chart_data, ensure_ascii=False),  # 转换为JSON字符串并保留中文字符
            "month": M  # 添加月份列
        })

    # 处理df_use_2（城市公共）
    for station_no in df_use_2['station_no']:
        bar_chart_data = generate_bar_chart_data(df_use_2, station_no, "df_use_2", avg_dict)
        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": json.dumps(bar_chart_data, ensure_ascii=False),
            "month": M  # 添加月份列
        })

    # 处理df_use_3（重卡专用）
    for station_no in df_use_3['station_no']:
        bar_chart_data = generate_bar_chart_data(df_use_3, station_no, "df_use_3", avg_dict)
        final_data.append({
            "siteNum": station_no,
            "options": options_json,  # 使用转换后的JSON字符串
            "BarChartData": json.dumps(bar_chart_data, ensure_ascii=False),
            "month": M  # 添加月份列
        })

    # 创建最终DataFrame
    Database_Table8 = pd.DataFrame(final_data)

    # 输出结果
    Database_Table8

    # #### 数据存储

    # In[469]:

    import pymysql
    from pymysql.cursors import DictCursor

    def create_table():
        # 数据库连接配置
        conn = pymysql.connect(
            host='192.168.0.223',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4'  # 确保支持特殊字符
        )

        try:
            with conn.cursor() as cursor:
                # 创建表的SQL语句，使用LONGTEXT类型存储长文本
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS dp_KeyStation_Internal_competitiveness_use (
                    data LONGTEXT COMMENT '六大维度对比数据',
                    month VARCHAR(6) COMMENT '分析年月，格式建议为YYYYMM'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='六大维度对比数据表';
                """

                # 执行SQL语句
                cursor.execute(create_table_sql)
                print("表创建成功或已存在")

            # 提交事务
            conn.commit()

        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"创建表时发生错误: {e}")
        finally:
            # 关闭数据库连接
            if conn:
                conn.close()

    if __name__ == "__main__":
        create_table()

    # In[470]:

    # 数据存储
    # 定义注释
    table_comment = "重点站点页-内部竞争力-使用效率"
    column_comments = {
        'siteNum': '站点编号',
        'options': '筛选器',
        'BarChartData': '条形图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table8,
        table_name="dp_KeyStation_Internal_competitiveness_use",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # ### 运营画像

    # In[471]:

    # 1、高速公共
    df_operation_1 = df_eco1[['station_no', 'station_name', 'station_category', '综合得分(调整)']].copy()
    df_operation_1 = df_operation_1.rename(columns={'综合得分(调整)': '经济效益'})

    # 添加设备质量得分
    df_operation_1 = pd.merge(df_operation_1, df_equip_1[['station_no', '综合得分(调整)']].rename(columns={'综合得分(调整)': '设备质量'}), on='station_no', how='left')

    # 添加使用效率得分
    df_operation_1 = pd.merge(df_operation_1, df_use_1[['station_no', '综合得分(调整)']].rename(columns={'综合得分(调整)': '使用效率'}), on='station_no', how='left')

    # 使用TOPSIS计算最终评分
    topsis_operation_1 = cal_topsis(df_operation_1[['station_no', '经济效益', '设备质量', '使用效率']].copy(), 'station_no', np.array([1 / 3, 1 / 3, 1 / 3]))

    # 添加最终评分和排名
    df_operation_1 = pd.merge(df_operation_1, topsis_operation_1[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 2、城市公共
    df_operation_2 = df_eco2[['station_no', 'station_name', 'station_category', '综合得分(调整)']].copy()
    df_operation_2 = df_operation_2.rename(columns={'综合得分(调整)': '经济效益'})

    # 添加设备质量得分
    df_operation_2 = pd.merge(df_operation_2, df_equip_2[['station_no', '综合得分(调整)']].rename(columns={'综合得分(调整)': '设备质量'}), on='station_no', how='left')

    # 添加使用效率得分
    df_operation_2 = pd.merge(df_operation_2, df_use_2[['station_no', '综合得分(调整)']].rename(columns={'综合得分(调整)': '使用效率'}), on='station_no', how='left')

    # 使用TOPSIS计算最终评分
    topsis_operation_2 = cal_topsis(df_operation_2[['station_no', '经济效益', '设备质量', '使用效率']].copy(), 'station_no', np.array([1 / 3, 1 / 3, 1 / 3]))

    # 添加最终评分和排名
    df_operation_2 = pd.merge(df_operation_2, topsis_operation_2[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 重复相同过程处理重卡专用类型
    df_operation_3 = df_eco3[['station_no', 'station_name', 'station_category', '综合得分(调整)']].copy()
    df_operation_3 = df_operation_3.rename(columns={'综合得分(调整)': '经济效益'})

    df_operation_3 = pd.merge(df_operation_3, df_equip_3[['station_no', '综合得分(调整)']].rename(columns={'综合得分(调整)': '设备质量'}), on='station_no', how='left')

    df_operation_3 = pd.merge(df_operation_3, df_use_3[['station_no', '综合得分(调整)']].rename(columns={'综合得分(调整)': '使用效率'}), on='station_no', how='left')

    topsis_operation_3 = cal_topsis(df_operation_3[['station_no', '经济效益', '设备质量', '使用效率']].copy(), 'station_no', np.array([1 / 3, 1 / 3, 1 / 3]))

    df_operation_3 = pd.merge(df_operation_3, topsis_operation_3[['station_no', '综合得分(调整)', '排名']], on='station_no', how='left')

    # 查看结果
    print(df_operation_1.shape)
    print(df_operation_2.shape)
    print(df_operation_3.shape)
    print(df_operation_1.info())

    # In[472]:

    # 保留两位小数
    df_operation_1['经济效益'] = df_operation_1['经济效益'].round(2)
    df_operation_2['经济效益'] = df_operation_2['经济效益'].round(2)
    df_operation_3['经济效益'] = df_operation_3['经济效益'].round(2)

    df_operation_1['设备质量'] = df_operation_1['设备质量'].round(2)
    df_operation_2['设备质量'] = df_operation_2['设备质量'].round(2)
    df_operation_3['设备质量'] = df_operation_3['设备质量'].round(2)

    df_operation_1['使用效率'] = df_operation_1['使用效率'].round(2)
    df_operation_2['使用效率'] = df_operation_2['使用效率'].round(2)
    df_operation_3['使用效率'] = df_operation_3['使用效率'].round(2)

    df_operation_1['综合得分(调整)'] = df_operation_1['综合得分(调整)'].round(2)
    df_operation_2['综合得分(调整)'] = df_operation_2['综合得分(调整)'].round(2)
    df_operation_3['综合得分(调整)'] = df_operation_3['综合得分(调整)'].round(2)

    # In[473]:

    def add_advantages_disadvantages(df):
        # 计算三个指标的平均值
        eco_mean = df['经济效益'].mean()
        equip_mean = df['设备质量'].mean()
        use_mean = df['使用效率'].mean()

        # 初始化优势劣势列为空字符串
        df['优势'] = ''
        df['劣势'] = ''

        # 遍历每一行数据
        for idx, row in df.iterrows():
            advantages = []  # 存储优势指标
            disadvantages = []  # 存储劣势指标

            # 检查经济效益
            if row['经济效益'] > eco_mean:
                advantages.append('经济效益')
            elif row['经济效益'] < eco_mean:
                disadvantages.append('经济效益')

            # 检查设备质量
            if row['设备质量'] > equip_mean:
                advantages.append('设备质量')
            elif row['设备质量'] < equip_mean:
                disadvantages.append('设备质量')

            # 检查使用效率
            if row['使用效率'] > use_mean:
                advantages.append('使用效率')
            elif row['使用效率'] < use_mean:
                disadvantages.append('使用效率')

            # 将列表转换为字符串，用'、'分隔
            df.at[idx, '优势'] = '、'.join(advantages)
            df.at[idx, '劣势'] = '、'.join(disadvantages)

        return df

    # 应用函数到三个表
    df_operation_1 = add_advantages_disadvantages(df_operation_1)
    df_operation_2 = add_advantages_disadvantages(df_operation_2)
    df_operation_3 = add_advantages_disadvantages(df_operation_3)

    # 打印结果验证
    df_operation_2.info()

    # In[474]:

    # 计算三个子集的平均值（保留2位小数）
    df_operation_1_avg = round(df_operation_1['综合得分(调整)'].mean(), 2)
    df_operation_2_avg = round(df_operation_2['综合得分(调整)'].mean(), 2)
    df_operation_3_avg = round(df_operation_3['综合得分(调整)'].mean(), 2)

    # In[475]:

    df_operation_1_avg1 = round(df_operation_1['经济效益'].mean(), 2)
    df_operation_2_avg1 = round(df_operation_2['经济效益'].mean(), 2)
    df_operation_3_avg1 = round(df_operation_3['经济效益'].mean(), 2)

    df_operation_1_avg2 = round(df_operation_1['设备质量'].mean(), 2)
    df_operation_2_avg2 = round(df_operation_2['设备质量'].mean(), 2)
    df_operation_3_avg2 = round(df_operation_3['设备质量'].mean(), 2)

    df_operation_1_avg3 = round(df_operation_1['使用效率'].mean(), 2)
    df_operation_2_avg3 = round(df_operation_2['使用效率'].mean(), 2)
    df_operation_3_avg3 = round(df_operation_3['使用效率'].mean(), 2)

    # #### 前端格式转换

    # In[476]:

    import pandas as pd
    import numpy as np
    import json

    def generate_radar_data(df, station_no, source_name, avg_dict):
        """生成雷达图数据"""
        # 获取当前站点数据
        current_row = df[df['station_no'] == station_no].iloc[0]

        # 当前站点数据
        current_value = [
            current_row['经济效益'],
            current_row['设备质量'],
            current_row['使用效率']
        ]

        # 同类型平均水平数据
        avg_values = avg_dict[source_name]["radar_avg"]

        return [
            {"value": current_value, "name": current_row['station_name']},
            {"value": avg_values, "name": "同类型平均水平"}
        ]

    def generate_axis_chart_data(df, station_no):
        """生成柱状图的axisData和chartData"""
        # 按排名排序
        sorted_df = df.sort_values(by='排名', ascending=True)
        total_stations = len(df)

        # 获取前三名
        top3 = sorted_df.head(3)
        axis_data = []
        chart_data = []
        included_station_nos = set()

        # 添加前三名
        for i, (_, row) in enumerate(top3.iterrows(), 1):
            axis_data.append(f"TOP{i} {row['station_name']}")
            chart_data.append(row['综合得分(调整)'])
            included_station_nos.add(row['station_no'])

        # 添加当前站点（如果不在前三且站点数>3）
        current_row = df[df['station_no'] == station_no].iloc[0]
        if total_stations > 3 and station_no not in included_station_nos:
            axis_data.append(f"TOP{current_row['排名']} {current_row['station_name']}")
            chart_data.append(current_row['综合得分(调整)'])

        # 反转axisData和chartData的顺序
        axis_data.reverse()
        chart_data.reverse()

        return axis_data, [chart_data]

    def generate_illustrate(df, station_no, source_name, avg_dict):
        """生成说明数据"""
        # 获取当前站点数据
        current_row = df[df['station_no'] == station_no].iloc[0]

        # 站点总数
        total_stations = len(df)

        return [
            {
                "title": "站点综合得分",
                "value": str(round(current_row['综合得分(调整)'], 2)),
                "unit": "分",
                "trend": ""
            },
            {
                "title": "站点内部排名",
                "value": f"{current_row['排名']}/{total_stations}",
                "unit": "",
                "trend": ""
            },
            {
                "title": "",
                "value": "",
                "unit": "",
                "trend": [
                    {"name": "站点优势", "content": current_row['优势']},
                    {"name": "站点劣势", "content": current_row['劣势']}
                ]
            }
        ]

    # 创建平均值映射字典
    avg_dict = {
        "df_operation_1": {
            "radar_avg": [df_operation_1_avg1, df_operation_1_avg2, df_operation_1_avg3],
            "bar_avg": df_operation_1_avg
        },
        "df_operation_2": {
            "radar_avg": [df_operation_2_avg1, df_operation_2_avg2, df_operation_2_avg3],
            "bar_avg": df_operation_2_avg
        },
        "df_operation_3": {
            "radar_avg": [df_operation_3_avg1, df_operation_3_avg2, df_operation_3_avg3],
            "bar_avg": df_operation_3_avg
        }
    }

    # 生成最终数据
    final_data = []

    # 处理df_operation_1（高速公共）
    for station_no in df_operation_1['station_no']:
        # 获取当前站点数据
        current_row = df_operation_1[df_operation_1['station_no'] == station_no].iloc[0]

        # 生成雷达图数据
        radar_data = generate_radar_data(df_operation_1, station_no, "df_operation_1", avg_dict)

        # 生成柱状图数据
        axis_data, chart_data = generate_axis_chart_data(df_operation_1, station_no)

        # 生成说明数据
        illustrate = generate_illustrate(df_operation_1, station_no, "df_operation_1", avg_dict)

        # 生成itselfName
        itself_name = f"TOP{current_row['排名']} {current_row['station_name']}"

        # 构建barChartData字典
        bar_chart_data = {
            "legendName": ["综合得分："],
            "axisData": axis_data,
            "chartData": chart_data,
            "yAxisName": "",
            "markLineName": "平均值",
            "xAxis": avg_dict["df_operation_1"]["bar_avg"],
            "itselfName": itself_name
        }

        final_data.append({
            "siteNum": station_no,
            "radarData": json.dumps(radar_data, ensure_ascii=False),  # 转换为JSON字符串
            "indicator": json.dumps([  # 转换为JSON字符串
                {"name": "经济效益"},
                {"name": "设备质量"},
                {"name": "使用效率"}
            ], ensure_ascii=False),
            "barChartData": json.dumps(bar_chart_data, ensure_ascii=False),  # 转换为JSON字符串
            "illustrate": json.dumps(illustrate, ensure_ascii=False)  # 转换为JSON字符串
        })

    # 处理df_operation_2（城市公共）
    for station_no in df_operation_2['station_no']:
        # 获取当前站点数据
        current_row = df_operation_2[df_operation_2['station_no'] == station_no].iloc[0]

        # 生成雷达图数据
        radar_data = generate_radar_data(df_operation_2, station_no, "df_operation_2", avg_dict)

        # 生成柱状图数据
        axis_data, chart_data = generate_axis_chart_data(df_operation_2, station_no)

        # 生成说明数据
        illustrate = generate_illustrate(df_operation_2, station_no, "df_operation_2", avg_dict)

        # 生成itselfName
        itself_name = f"TOP{current_row['排名']} {current_row['station_name']}"

        # 构建barChartData字典
        bar_chart_data = {
            "legendName": ["综合得分："],
            "axisData": axis_data,
            "chartData": chart_data,
            "yAxisName": "",
            "markLineName": "平均值",
            "xAxis": avg_dict["df_operation_2"]["bar_avg"],
            "itselfName": itself_name
        }

        final_data.append({
            "siteNum": station_no,
            "radarData": json.dumps(radar_data, ensure_ascii=False),  # 转换为JSON字符串
            "indicator": json.dumps([  # 转换为JSON字符串
                {"name": "经济效益"},
                {"name": "设备质量"},
                {"name": "使用效率"}
            ], ensure_ascii=False),
            "barChartData": json.dumps(bar_chart_data, ensure_ascii=False),  # 转换为JSON字符串
            "illustrate": json.dumps(illustrate, ensure_ascii=False)  # 转换为JSON字符串
        })

    # 处理df_operation_3（重卡专用）
    for station_no in df_operation_3['station_no']:
        # 获取当前站点数据
        current_row = df_operation_3[df_operation_3['station_no'] == station_no].iloc[0]

        # 生成雷达图数据
        radar_data = generate_radar_data(df_operation_3, station_no, "df_operation_3", avg_dict)

        # 生成柱状图数据
        axis_data, chart_data = generate_axis_chart_data(df_operation_3, station_no)

        # 生成说明数据
        illustrate = generate_illustrate(df_operation_3, station_no, "df_operation_3", avg_dict)

        # 生成itselfName
        itself_name = f"TOP{current_row['排名']} {current_row['station_name']}"

        # 构建barChartData字典
        bar_chart_data = {
            "legendName": ["综合得分："],
            "axisData": axis_data,
            "chartData": chart_data,
            "yAxisName": "",
            "markLineName": "平均值",
            "xAxis": avg_dict["df_operation_3"]["bar_avg"],
            "itselfName": itself_name
        }

        final_data.append({
            "siteNum": station_no,
            "radarData": json.dumps(radar_data, ensure_ascii=False),  # 转换为JSON字符串
            "indicator": json.dumps([  # 转换为JSON字符串
                {"name": "经济效益"},
                {"name": "设备质量"},
                {"name": "使用效率"}
            ], ensure_ascii=False),
            "barChartData": json.dumps(bar_chart_data, ensure_ascii=False),  # 转换为JSON字符串
            "illustrate": json.dumps(illustrate, ensure_ascii=False)  # 转换为JSON字符串
        })

    # 创建最终DataFrame
    Database_Table10 = pd.DataFrame(final_data)
    Database_Table10['month'] = M

    Database_Table10

    # #### 数据存储

    # In[477]:

    import pymysql
    from pymysql.cursors import DictCursor

    def create_table():
        # 数据库连接配置
        conn = pymysql.connect(
            host='192.168.0.223',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4'  # 确保支持特殊字符
        )

        try:
            with conn.cursor() as cursor:
                # 创建表的SQL语句，使用LONGTEXT类型存储长文本
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS dp_Keystation_Internal_Competitiveness_Operation (
                    month VARCHAR(6) COMMENT '分析年月，格式建议为YYYYMM'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='六大维度对比数据表';
                """

                # 执行SQL语句
                cursor.execute(create_table_sql)
                print("表创建成功或已存在")

            # 提交事务
            conn.commit()

        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"创建表时发生错误: {e}")
        finally:
            # 关闭数据库连接
            if conn:
                conn.close()

    if __name__ == "__main__":
        create_table()

    # In[478]:

    # 数据存储
    # 定义注释
    table_comment = "重点站点页-内部竞争力-运营画像"
    column_comments = {
        'siteNum': '站点编号',
        'radarData': '雷达图数据',
        'indicator': '雷达图指标',
        'barChartData': '条形图数据',
        'illustrate': '站点综合评价',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table10,
        table_name="dp_Keystation_Internal_Competitiveness_Operation",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # ## 三类充电站数量统计

    # In[479]:

    highspeed_count = len(DF_SCDD[DF_SCDD['station_category'] == '高速公共'])
    urban_count = len(DF_SCDD[DF_SCDD['station_category'] == '城市公共'])
    truck_count = len(DF_SCDD[DF_SCDD['station_category'] == '重卡专用'])

    # 打印结果
    print(f"高速公共: {highspeed_count}座")
    print(f"城市公共: {urban_count}座")
    print(f"重卡专用: {truck_count}座")

    # In[480]:

    # 定义需要筛选的station_category列表
    target_types = ['城市公共', '高速公共', '重卡专用']

    # 筛选符合条件的数据并保存到data11
    data11 = data10[data10['station_category'].isin(target_types)].copy()
    data11.shape

    # ### 前端格式转换

    # In[481]:

    # 构建前端需要的数据结构
    targetData = [
        {"title": "高速公共充电站点数量", "value": highspeed_count, "unit": "座"},
        {"title": "城市公共充电站点数量", "value": urban_count, "unit": "座"},
        {"title": "重卡专用充电站点数量", "value": truck_count, "unit": "座"}
    ]
    print(targetData)

    # 将列表转换为紧凑格式的JSON字符串（无换行符）
    json_output = json.dumps(targetData, ensure_ascii=False)

    # 创建最终结果表
    Database_Table1 = pd.DataFrame({
        'targetData': [json_output],
        'month': [M]  # 假设M是当前月份变量
    })

    # 输出结果
    Database_Table1

    # ### 数据存储

    # In[482]:

    # 数据存储
    # 定义注释
    table_comment = "重点站点页-三类充电站数量统计"
    column_comments = {
        'targetData': '三类充电站数量统计',
        'month': '分析年月'
    }
    print("Database_Table1:")
    print(Database_Table1.head(20))
    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table1,
        table_name="dp_KeyStation_Statistics_ChargingStations",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['month']
    )

    # ## 站点充电详情

    # In[483]:

    # 步骤1: 根据预定义变量M生成时间范围
    year = int(str(M)[:4])
    month = int(str(M)[4:6])

    # 计算当月的第一天和最后一天
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - pd.Timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - pd.Timedelta(days=1)

    # 格式化为字符串
    start_time = first_day.strftime("%Y-%m-%d 00:00:00")
    end_time = last_day.strftime("%Y-%m-%d 23:59:59")

    print(f"筛选订单时间范围: {start_time} 至 {end_time}")

    # 步骤2: 筛选订单数据
    order_query = f"""
    SELECT charging_point_no, charging_station_no, order_create_time, trans_energy
    FROM fin_plat_data_order
    WHERE order_create_time BETWEEN '{start_time}' AND '{end_time}'
    """
    df_order = SQL(order_query)

    # 步骤3: 获取充电桩信息
    point_query = """
    SELECT point_no, station_no, current_type
    FROM charging_station_point
    """
    df_point = SQL(point_query)

    # 步骤4: 合并数据
    abnormal_pile1 = pd.merge(
        df_point,
        df_order,
        left_on=['station_no', 'point_no'],
        right_on=['charging_station_no', 'charging_point_no'],
        how='inner'
    )

    # 步骤5：提取abnormal_pile1中高速公共、城市公共、重卡专用的
    valid_station_nos = df1['station_no'].unique()
    abnormal_pile2 = abnormal_pile1[abnormal_pile1['station_no'].isin(valid_station_nos)]

    # 步骤6: 统计current_type为空的数量
    null_current_type_count = abnormal_pile2['current_type'].isna().sum()
    print(f"合并后记录数: {len(abnormal_pile2)}")
    print(f"current_type为空的数量: {null_current_type_count}")
    abnormal_pile3 = abnormal_pile2.dropna(subset=['current_type']).copy()
    abnormal_pile3.info()

    # In[484]:

    # 提取DF_SCDD中所有存在的station_no，形成一个集合（提高查询效率）
    valid_stations = set(data11['station_no'])

    # 筛选出abnormal_pile3中station_no存在于DF_SCDD中的行
    abnormal_pile3 = abnormal_pile3[abnormal_pile3['station_no'].isin(valid_stations)]

    abnormal_pile3.info()

    # In[485]:

    # 数据类型转换
    abnormal_pile3['trans_energy'] = abnormal_pile1['trans_energy'].astype(str).str.replace(',', '').astype(float)
    abnormal_pile3.info()

    # In[486]:

    # 对abnormal_pile3表进行聚类求和
    abnormal_pile4 = abnormal_pile3.groupby(['point_no', 'station_no']).agg({
        'trans_energy': 'sum',
        'current_type': 'first'  # 保留第一个出现的current_type值
    }).reset_index()

    # 确保列的顺序正确
    abnormal_pile4 = abnormal_pile4[['point_no', 'station_no', 'current_type', 'trans_energy']]

    # 月充电量保留两位小数
    abnormal_pile4['trans_energy'] = abnormal_pile4['trans_energy'].round(2)

    abnormal_pile4.info()

    # In[487]:

    # 步骤1：计算分组平均值
    df = abnormal_pile4.copy()
    df['trans_energy_avg'] = df.groupby(['station_no', 'current_type'])['trans_energy'].transform('mean')

    # 步骤2：计算60%平均值
    df['trans_energy_avg60'] = df['trans_energy_avg'] * 0.6

    # 步骤3：添加判断列
    df['judgment'] = df.apply(
        lambda row: '异常' if row['trans_energy'] < row['trans_energy_avg60'] else '正常',
        axis=1
    )

    print(df.info())
    df.head()

    # In[488]:

    abnormal_count = (df['judgment'] == '异常').sum()
    print(f"judgment为'异常'的数量是: {abnormal_count}")

    # ### 前端格式转换

    # In[489]:

    # 创建空列表存储结果
    data_list = []

    # 按站点编号分组处理
    for site_num, group in df.groupby('station_no'):
        # 创建充电桩列表
        charging_list = []

        # 首先添加异常桩（abnormal=0），然后添加正常桩（abnormal=1）
        # 先处理异常桩
        abnormal_rows = group[group['judgment'] == '异常']
        for _, row in abnormal_rows.iterrows():
            charging_list.append({
                "number": row['point_no'],
                "chargeCapacity": row['trans_energy'],
                "abnormal": 0  # 异常桩
            })

        # 然后处理正常桩
        normal_rows = group[group['judgment'] != '异常']
        for _, row in normal_rows.iterrows():
            charging_list.append({
                "number": row['point_no'],
                "chargeCapacity": row['trans_energy'],
                "abnormal": 1  # 正常桩
            })

        # 统计充电桩数量
        # 快充桩：current_type='直流'
        fast_count = len(group[group['current_type'] == '直流'])
        # 慢充桩：current_type='交流'
        slow_count = len(group[group['current_type'] == '交流'])

        # 统计异常充电桩数量
        # 异常快充桩：直流且异常
        fast_abnormal_count = len(group[(group['current_type'] == '直流') & (group['judgment'] == '异常')])
        # 异常慢充桩：交流且异常
        slow_abnormal_count = len(group[(group['current_type'] == '交流') & (group['judgment'] == '异常')])

        # 创建站点描述文本
        site_charging_detail = (
            f"统计时间内此站点快充桩共{fast_count}个、慢充桩共{slow_count}个，"
            f"其中异常的快充桩共{fast_abnormal_count}个、慢充桩共{slow_abnormal_count}个。"
        )

        # 创建站点数据结构，将siteCharging转换为JSON字符串
        site_data = {
            "siteNum": site_num,
            "siteCharging": json.dumps(charging_list, ensure_ascii=False),  # 转换为JSON字符串
            "siteChargingDetail": site_charging_detail,
            "month": M
        }

        data_list.append(site_data)

    # 创建最终结果表
    Database_Table4 = pd.DataFrame(data_list)

    # 输出结果
    Database_Table4

    # ### 数据存储

    # In[490]:

    import pymysql
    from pymysql.cursors import DictCursor

    def create_table():
        # 数据库连接配置
        conn = pymysql.connect(
            host='192.168.0.223',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4'  # 确保支持特殊字符
        )

        try:
            with conn.cursor() as cursor:
                # 创建表的SQL语句，使用LONGTEXT类型存储长文本
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS dp_keystation_charging_post_details (
                    month VARCHAR(6) COMMENT '分析年月，格式建议为YYYYMM'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站点充电桩详情';
                """

                # 执行SQL语句
                cursor.execute(create_table_sql)
                print("表创建成功或已存在")

            # 提交事务
            conn.commit()

        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"创建表时发生错误: {e}")
        finally:
            # 关闭数据库连接
            if conn:
                conn.close()

    if __name__ == "__main__":
        create_table()

    # In[491]:

    # 数据存储
    # 定义注释
    table_comment = "重点站点页-站点充电详情"
    column_comments = {
        'siteNum': '站点充电详情',
        'siteCharging': '站点充电详情',
        'siteChargingDetail': '站点充电详情',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table4,
        table_name="dp_KeyStation_charging_post_Details",
        table_comment=table_comment,
        column_comments=column_comments,
        primary_keys=['siteNum', 'month']
    )

    # In[ ]:





