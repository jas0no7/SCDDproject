
from modules.config import SQL,import_data_with_cursor,Statistical_Time


from logs.log_decorator import log_execution
from loguru import logger
@log_execution
def runtechUpgradePaybackForecast():
    logger.info("开始执行技改站点回本周期预测页面")

    import pandas as pd
    import numpy as np
    import json
    from pandas.tseries.offsets import MonthBegin
    import calendar
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)







    def get_months_in_year(month_str):
        """获取指定月份及其当年之前的所有月份，返回元组格式"""
        year = int(month_str[:4])
        month = int(month_str[4:])

        # 生成从1月到指定月份的所有月份，并转换为元组
        months = tuple(int(f"{year}{m:02d}") for m in range(1, month + 1))

        placeholders =", ".join([f"p{p}" for p in months])

        return placeholders

    def bar_chart(df, axis, YxisName, m):
        axisData = df[axis].tolist()
        chartData = [df[col].tolist() for col in [i for i in df.columns if axis not in i]]
        YxisName = YxisName
        legendName = [i for i in df.columns if axis not in i]
        L = [axisData, chartData, YxisName, legendName]
        print(L)
        DF = pd.DataFrame(columns=['axisData', 'chartData', 'YxisName', 'legendName'], data=[L])
        DF['month'] = m
        return DF





    # ## 往前推11个月

    # In[11]:


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


    # In[12]:


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


    # In[13]:


    # 区间筛选
    result = get_months_in_year(M)
    result

    # In[14]:





    # 技改关系只从映射表读取；站点属性和经营数据仍从原始业务表读取。
    tech_upgrade_mapping = SQL("""
    SELECT old_code, new_code
    FROM dp_station_tech_upgrade_mapping
    ORDER BY id
    """)
    if tech_upgrade_mapping.empty:
        raise ValueError("dp_station_tech_upgrade_mapping 没有技改站点映射记录")

    mapping_columns = ['old_code', 'new_code']
    if tech_upgrade_mapping[mapping_columns].isna().any().any():
        raise ValueError("dp_station_tech_upgrade_mapping 存在空的映射字段")
    tech_upgrade_mapping[mapping_columns] = tech_upgrade_mapping[mapping_columns].astype(str).apply(
        lambda column: column.str.strip()
    )
    if (tech_upgrade_mapping[mapping_columns] == '').any().any():
        raise ValueError("dp_station_tech_upgrade_mapping 存在空的映射字段")

    mapped_station_codes = pd.concat([
        tech_upgrade_mapping['old_code'],
        tech_upgrade_mapping['new_code']
    ]).drop_duplicates().tolist()
    mapped_station_codes_sql = ', '.join(
        "'{}'".format(str(code).replace("'", "''")) for code in mapped_station_codes
    )

    sql1 = f"""
    SELECT 
    cs.station_name,cs.station_no,cs.station_category,cs.city,cs.operation_status,IFNULL(cs.investment_amount,0) as investment_amount,cs.commissioning_time
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where
    (rm.merchant_name = '国网电动汽车服务（四川）有限公司'
     OR cs.station_no IN ({mapped_station_codes_sql}))
    and (cs.operation_status in ('投运','退运')
         OR cs.station_no IN ({mapped_station_codes_sql}));
    """
    df1 = SQL(sql1)
    df1.loc[df1['station_category'] == '高速', 'station_category'] = '高速公共'
    print(df1.shape)
    print(df1.info())
    df1.head(1)

    # #### 数据类型转换

    # In[17]:


    df1['investment_amount'] = df1['investment_amount'].astype(str).str.replace(',', '').astype(float)
    df1.info()

    # #### 累计投运月份计算

    # In[18]:


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

    # In[19]:


    # ==================注释==================
    # 统计每个站点当前的累计总补贴
    # station_no：站点编号
    # total_subsidy：总补贴
    # ——共96条数据


    # In[20]:


    sql2 = """
    select year,station_no,IFNULL(total_subsidy,0) as total_subsidy from dp_subsidy_NEW;
    """
    df2 = SQL(sql2)
    print(df2.shape)
    print(df2.info())
    df2.head(1)

    # In[21]:


    # 数据类型转换、单位统一为元
    df2['total_subsidy'] = 10000 * df2['total_subsidy'].astype(str).str.replace(',', '').astype(float)

    # In[22]:


    df2_cal = df2.groupby('station_no', as_index=False).agg({'total_subsidy': 'sum'})
    df2_cal.head(1)

    # ### df3-站点运营总收入和总支出

    # In[23]:


    # ==================注释==================
    # 统计四川电动投资金额不为空的每个投运站点的总收入、总支出
    # station_no：站点编号
    # revenue：总收入
    # cost：总支出
    # ——共212条数据


    # In[24]:


    sql3 = f"""
    select b.station_no,b.cba_month,
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
    ((rm.merchant_name = '国网电动汽车服务（四川）有限公司'
      and cs.operation_status in ('投运','退运'))
     OR cs.station_no IN ({mapped_station_codes_sql}))
    and (cs.investment_amount is not null
         OR cs.station_no IN ({mapped_station_codes_sql}))) a
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

    # In[25]:


    # 数据类型转换
    df3['revenue'] = df3['revenue'].astype(str).str.replace(',', '').astype(float)
    df3['cost'] = df3['cost'].astype(str).str.replace(',', '').astype(float)
    df3.info()

    # In[26]:


    df3_cal = df3.groupby('station_no', as_index=False).agg({'revenue': 'sum',
                                                             'cost': 'sum'})
    df3_cal

    # ### df4-站点租金

    # In[27]:


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


    # In[28]:


    sql4 = f"""
    SELECT
    cs.station_no,
    JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) AS parking_fee
    FROM
    charging_station cs
    LEFT JOIN
    rec_merchant_rec_station rmr ON cs.station_no = rmr.station_on
    LEFT JOIN
    scdd_rec_rules sr ON rmr.merchant_id = sr.merchant_id
    where (cs.property_owner_merhant_id = 119
           OR cs.station_no IN ({mapped_station_codes_sql}))
    and  JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL;
    """
    df4 = SQL(sql4)
    print(df4.shape)
    print(df4.info())
    df4.head(1)

    # In[29]:


    # 数据类型转换
    df4['parking_fee'] = df4['parking_fee'].astype(str).str.replace(',', '').astype(float)
    df4.info()

    # ### df5-站点累计分成

    # In[30]:


    # ==================注释==================
    # 这里的分成指的是，四川电动旗下站点，分给其他单位的分成
    # station_no：站点编号
    # merchant_profit_amount：站点分成
    # --共352条数据


    # In[31]:


    sql5 = f"""
    select a.station_no,b.rec_month,sum(IFNULL(b.merchant_profit_amount,0)) as merchant_profit_amount from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where
    (rm.merchant_name = '国网电动汽车服务（四川）有限公司'
     OR cs.station_no IN ({mapped_station_codes_sql}))
    and (cs.operation_status in ('投运','退运')
         OR cs.station_no IN ({mapped_station_codes_sql}))
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

    # In[32]:


    # 数据类型转换
    df5['merchant_profit_amount'] = df5['merchant_profit_amount'].astype(str).str.replace(',', '').astype(float)
    df5.info()

    # In[33]:


    df5_cal = df5.groupby('station_no', as_index=False).agg({'merchant_profit_amount': 'sum'})
    df5_cal.head(1)

    # ### df6-站点运维费用

    # In[34]:


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

    # In[35]:


    # 数据类型转换、单位统一为元
    df6['maintenance_cost'] = 10000 * df6['maintenance_cost'].astype(str).str.replace(',', '').astype(float)

    # In[36]:


    df6_cal = df6.groupby('station_no', as_index=False).agg({'maintenance_cost': 'sum'})
    df6_cal.head(1)

    # ### 数据合并

    # In[37]:


    # 映射表只提供技改前后的编号和名称关系；业务数据仍全部来自原始查询。
    # ### 站点数据筛选

    # In[38]:


    df1.head(1)

    # In[39]:


    # 筛选当前四川电动旗下投运状态的全量站点数据+技改站
    mapped_station_mask = df1['station_no'].isin(mapped_station_codes)
    data1 = df1[((df1['operation_status'] == '投运') | mapped_station_mask) &
                ((df1['investment_amount'] != 0) | mapped_station_mask)]
    print(data1.shape)
    data1.head(1)

    # ### 补贴数据合并

    # In[40]:


    # 合并站点补贴数据
    print('含有补贴的站点数量：', df2_cal.shape)
    data2 = pd.merge(data1, df2_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data2.shape)
    print('四川电动投运站点中含有补贴的站点的数量：', data2[data2['total_subsidy'] != 0].shape)
    data2.head(1)

    # ### 运营数据合并

    # In[41]:


    # 合并各站点的运营总投入和总支出
    data3 = pd.merge(data2, df3_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data3.shape)
    print('四川电动投运站点中含有运营数据的站点的数量：', data3[data3['revenue'] != 0].shape)
    data3.head(1)

    # ### 站点租金合并

    # In[42]:


    # 合并站点租金
    data4 = pd.merge(data3, df4, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data4.shape)
    print('四川电动投运站点中含有租金数据的站点的数量：', data4[data4['parking_fee'] != 0].shape)
    data4.head(1)

    # ### 分成数据合并

    # In[43]:


    # 合并站点分成
    data5 = pd.merge(data4, df5_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data5.shape)
    print('四川电动投运站点中含有分成数据的站点的数量：', data5[data5['merchant_profit_amount'] != 0].shape)
    data5.head(1)

    # ### 运维数据合并

    # In[44]:


    # 合并站点运维费
    data6 = pd.merge(data5, df6_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data6.shape)
    print('四川电动投运站点中含有运维数据的站点的数量：', data6[data6['maintenance_cost'] != 0].shape)
    data6.head(1)

    # ### 当年补贴数据合并

    # In[45]:


    df2_year = df2[df2['year'] == str(year) + '年']
    df2_year.columns = ['year', 'station_no', '当年_total_subsidy']
    df2_year = df2_year[['station_no', '当年_total_subsidy']]

    # In[46]:


    data7 = pd.merge(data6, df2_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data7.shape)
    print('四川电动投运站点中含有当年补贴数据的站点的数量：', data7[data7['当年_total_subsidy'] != 0].shape)
    data7.head(1)

    # ### 当年运营收入数据合并

    # In[47]:


    df3.head(1)

    # In[48]:

    df3['cba_month'].replace('None',pd.NA,inplace=True)
    df3.dropna(subset = ['cba_month'],inplace = True)
    df3['year'] = df3['cba_month'].astype(str).str[:4].astype(int)
    df3_year = df3[df3['year'] == year]
    df3_year = df3_year.groupby(by='station_no', as_index=False).agg({'revenue': 'sum'})
    df3_year.columns = ['station_no', '当年_revenue']
    df3_year

    # In[49]:


    # 合并当年运营收入
    data8 = pd.merge(data7, df3_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data8.shape)
    print('四川电动投运站点中含有当年运营收入数据的站点的数量：', data8[data8['当年_revenue'] != 0].shape)
    data8.head(1)

    # ### 技改站数据合并-特殊处理

    # In[50]:


    data9 = data8.copy()

    # In[52]:


    # ### 站点回本进度详情

    # #### 是否回本、滞后回本详情

    # In[53]:


    data9['in'] = data9['total_subsidy'].astype('float') + data9['revenue'].astype('float')
    data9['out'] = data9['investment_amount'].astype('float') + data9['cost'].astype('float') + (data9['parking_fee'] * data9['累计投运月份数']).astype('float') + data9['merchant_profit_amount'].astype('float') + data9['maintenance_cost'].astype('float')
    data9['当年_in'] = data9['当年_total_subsidy'] + data9['当年_revenue']
    data9.head(1)

    # In[54]:


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

    # In[55]:


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

    # In[56]:


    data10.groupby(by='回本状态标签').agg({'station_no': 'count'})

    # In[57]:


    DF_2 = data10[data10['station_category'].isin(['城市公共', '高速公共', '重卡专用'])][['station_no', 'station_name', 'station_category', '静态资金回本进度', '设备折旧进度']]

    # In[58]:


    DF_2

    # In[ ]:


    # In[59]:


    data10

    # ## 月度收支平衡点

    # ### 每月营收

    # In[60]:


    DF_Break_even = []
    no_list = data10['station_no'].to_list()
    for i in no_list:
        x1 = df1[df1['station_no'] == i]
        #     #生成站点从投运开始的年月码表
        x1 = x1[['station_no', 'commissioning_time']]
        end_year = int(M[:4])
        end_month = int(M[4:])
        end_date = pd.Timestamp(end_year, end_month, 1)
        x2_data = []  # 存储结果的列表
        for _, row in x1.iterrows():  # 遍历x1的每一行
            station = row['station_no']
            start_date = row['commissioning_time']
            if pd.isna(start_date):
                logger.warning("站点投运时间缺失，跳过该站月度收支序列生成：站点={}", station)
                continue
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
        x2 = pd.DataFrame(x2_data, columns=['station_no', 'month'])
        if x2.empty:
            logger.warning("站点没有可计算的月度收支区间，跳过该站月度收支序列：站点={}", i)
            continue

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
        x8['月总收入'] = x8['total_subsidy_month'].astype('float') + x8['revenue'].astype('float')
        x8['月总支出'] = x8['cost'].astype('float') + x8['merchant_profit_amount'].astype('float') + x8['parking_fee'].astype('float') + x8['maintenance_cost'].astype('float')

        # 算累计，还要加上初始投资金额
        x8['当月累计收入'] = x8['月总收入'].cumsum()
        x8['当月累计支出'] = x8['月总支出'].cumsum()
        x8['当月累计支出(含初始投资)'] = x8['当月累计支出'] + x8['investment_amount']

        # 技改站数据特殊合并
        x9 = x8.groupby(by=['station_no', 'month'], as_index=False).agg({'cost': 'sum', 'parking_fee': 'sum',
                                                                         'merchant_profit_amount': 'sum', 'maintenance_cost': 'sum', 'total_subsidy_month': 'sum', 'revenue': 'sum', '月总收入': 'sum', '月总支出': 'sum',
                                                                         '当月累计收入': 'sum', '当月累计支出': 'sum', '当月累计支出(含初始投资)': 'sum'})

        DF_Break_even.append(x9)

    # #### 按技改映射关系计算预计回本周期

    # In[92]:


    break_even_columns = [
        'station_no', 'month', 'cost', 'parking_fee', 'merchant_profit_amount',
        'maintenance_cost', 'total_subsidy_month', 'revenue', '月总收入', '月总支出',
        '当月累计收入', '当月累计支出', '当月累计支出(含初始投资)'
    ]
    DF_Break_even = (
        pd.concat(DF_Break_even, ignore_index=True)
        if DF_Break_even else pd.DataFrame(columns=break_even_columns)
    )

    # 回本周期按映射表逐条计算；业务金额、月份和投运日期均来自原有业务表。
    station_metadata = df1[['station_no', 'commissioning_time', 'investment_amount']].copy()
    station_metadata['station_key'] = station_metadata['station_no'].astype(str).str.strip()
    station_metadata = station_metadata.drop_duplicates('station_key', keep='last')
    metadata_by_station = station_metadata.set_index('station_key').to_dict('index')

    def normalize_station_code(code):
        return '' if pd.isna(code) else str(code).strip()

    def normalize_month(value):
        digits = ''.join(char for char in str(value) if char.isdigit())
        return digits[:6] if len(digits) >= 6 else ''

    def month_start(value):
        if value is None or pd.isna(value):
            return pd.NaT
        normalized = normalize_month(value)
        if len(normalized) == 6:
            return pd.to_datetime(normalized, format='%Y%m', errors='coerce')
        parsed = pd.to_datetime(value, errors='coerce')
        if pd.isna(parsed):
            return pd.NaT
        return parsed.to_period('M').to_timestamp()

    history_by_station = {}
    if not DF_Break_even.empty:
        history_source = DF_Break_even.copy()
        history_source['station_key'] = history_source['station_no'].astype(str).str.strip()
        history_source['month_key'] = history_source['month'].map(normalize_month)
        history_source = history_source[history_source['month_key'].str.len() == 6]
        history_by_station = {
            code: group.sort_values('month_key').copy()
            for code, group in history_source.groupby('station_key', sort=False)
        }

    def history_for(code):
        return history_by_station.get(normalize_station_code(code), pd.DataFrame())

    def station_start_month(code, history):
        metadata = metadata_by_station.get(normalize_station_code(code), {})
        start = month_start(metadata.get('commissioning_time'))
        if pd.isna(start) and not history.empty:
            start = month_start(history.iloc[0]['month_key'])
        return start

    def investment_amount_for(code):
        station_key = normalize_station_code(code)
        metadata = metadata_by_station.get(station_key, {})
        amount = pd.to_numeric(metadata.get('investment_amount'), errors='coerce')
        if pd.notna(amount) and np.isfinite(float(amount)):
            return float(amount)

        history = history_for(code)
        if not history.empty:
            latest = history.iloc[-1]
            with_initial = pd.to_numeric(
                latest.get('当月累计支出(含初始投资)'), errors='coerce'
            )
            without_initial = pd.to_numeric(
                latest.get('当月累计支出'), errors='coerce'
            )
            if pd.notna(with_initial) and pd.notna(without_initial):
                amount = float(with_initial) - float(without_initial)
                if np.isfinite(amount):
                    return amount
        return None

    def estimate_payback_years(
        station_code,
        history,
        revenue_column,
        cost_column,
        investment,
        start_date,
        end_date,
        window_size,
        cutoff_month=None,
        exclusive_end_month=None,
        phase=''
    ):
        if history.empty:
            return np.nan

        eligible = history.copy()
        if cutoff_month:
            eligible = eligible[eligible['month_key'] <= cutoff_month]
        if exclusive_end_month:
            eligible = eligible[eligible['month_key'] < exclusive_end_month]
        sample = eligible.tail(window_size)
        if sample.empty or revenue_column not in sample or cost_column not in sample:
            return np.nan

        revenue = pd.to_numeric(sample[revenue_column], errors='coerce')
        cost = pd.to_numeric(sample[cost_column], errors='coerce')
        monthly_net = (revenue - cost).replace([np.inf, -np.inf], np.nan).dropna().mean()
        if pd.isna(monthly_net) or not np.isfinite(float(monthly_net)) or monthly_net <= 0:
            logger.warning(
                "技改回本周期缺少有效月均净收益，缺失项按 0 输出：站点={}，阶段={}",
                station_code,
                phase
            )
            return np.nan
        if investment is None or not np.isfinite(float(investment)):
            logger.warning(
                "技改回本周期缺少有效投资金额，缺失项按 0 输出：站点={}，阶段={}",
                station_code,
                phase
            )
            return np.nan

        start = month_start(start_date)
        if pd.isna(start):
            start = month_start(history.iloc[0]['month_key'])
        end = month_start(end_date)
        if pd.isna(end):
            end = month_start(sample.iloc[-1]['month_key'])
        if pd.isna(start) or pd.isna(end) or end < start:
            logger.warning(
                "技改回本周期缺少有效投运/截止月份，缺失项按 0 输出：站点={}，阶段={}",
                station_code,
                phase
            )
            return np.nan

        elapsed_months = (end.year - start.year) * 12 + end.month - start.month
        remaining_months = float(investment) / float(monthly_net)
        years = (elapsed_months + remaining_months) / 12
        return round(years, 2) if np.isfinite(years) else np.nan

    current_month_start = month_start(M)
    current_month_key = normalize_month(M)
    pre_results = []
    for mapping_row in tech_upgrade_mapping.itertuples(index=False):
        old_code = mapping_row.old_code
        new_code = mapping_row.new_code
        old_history = history_for(old_code)
        new_history = history_for(new_code)
        new_start = station_start_month(new_code, new_history)
        if pd.isna(new_start) and not old_history.empty:
            new_start = month_start(old_history.iloc[-1]['month_key'])
        cutoff_month = new_start.strftime('%Y%m') if not pd.isna(new_start) else None
        old_start = station_start_month(old_code, old_history)
        old_end = new_start
        if pd.isna(old_end) and not old_history.empty:
            old_end = month_start(old_history.iloc[-1]['month_key'])
        expected_before = estimate_payback_years(
            old_code,
            old_history,
            revenue_column='revenue',
            cost_column='cost',
            investment=investment_amount_for(old_code),
            start_date=old_start,
            end_date=old_end,
            window_size=6,
            cutoff_month=cutoff_month,
            phase='技改前'
        )
        pre_results.append({
            'station_no': old_code,
            '预计回本周期': expected_before
        })

    post_results = []
    for new_code in tech_upgrade_mapping['new_code'].drop_duplicates().tolist():
        new_history = history_for(new_code)
        new_start = station_start_month(new_code, new_history)
        related_old_codes = tech_upgrade_mapping.loc[
            tech_upgrade_mapping['new_code'] == new_code, 'old_code'
        ].drop_duplicates().tolist()
        related_investments = [investment_amount_for(code) for code in related_old_codes]
        new_investment = investment_amount_for(new_code)
        if new_investment is None or any(value is None for value in related_investments):
            total_investment = None
        else:
            total_investment = new_investment + sum(related_investments)

        expected_after = estimate_payback_years(
            new_code,
            new_history,
            revenue_column='月总收入',
            cost_column='月总支出',
            investment=total_investment,
            start_date=new_start,
            end_date=current_month_start,
            window_size=5,
            exclusive_end_month=current_month_key,
            phase='技改后'
        )
        post_results.append({
            'station_no': new_code,
            '预计回本周期': expected_after
        })

    df_recovery_period = pd.concat(
        [pd.DataFrame(pre_results), pd.DataFrame(post_results)],
        ignore_index=True
    )

    # In[109]:


    sql = f"""
    SELECT *
    FROM charging_station
    WHERE station_no IN ({mapped_station_codes_sql})
    """
    DF_charging_station = SQL(sql)

    # In[110]:


    df_recovery_period = df_recovery_period.merge(
        DF_charging_station[['station_name', 'station_no']],  # 包含 station_name
        on='station_no',
        how='left'
    )

    # In[111]:


    df_recovery_period

    # In[112]:


    # In[113]:


    pre_recovery_period = df_recovery_period.rename(columns={
        'station_no': 'old_code',
        'station_name': 'pre_station_name',
        '预计回本周期': '预计回本期限'
    })[['old_code', 'pre_station_name', '预计回本期限']]
    post_recovery_period = df_recovery_period.rename(columns={
        'station_no': 'new_code',
        'station_name': 'post_station_name'
    })[['new_code', 'post_station_name', '预计回本周期']].drop_duplicates(subset=['new_code'])

    df_recovery_period2 = tech_upgrade_mapping.merge(
        pre_recovery_period,
        on='old_code',
        how='left'
    ).merge(
        post_recovery_period,
        on='new_code',
        how='left'
    )

    period_columns = ['预计回本期限', '预计回本周期']
    df_recovery_period2[period_columns] = df_recovery_period2[period_columns].apply(
        pd.to_numeric, errors='coerce'
    ).replace([np.inf, -np.inf], np.nan)
    missing_period_mask = df_recovery_period2[period_columns].isna().any(axis=1)
    missing_period = df_recovery_period2.loc[missing_period_mask, ['old_code', 'new_code']]
    if not missing_period.empty:
        logger.warning(
            "{} 条技改映射缺少回本周期数据，缺失项按 0 输出。站点映射：{}",
            len(missing_period),
            missing_period.to_dict('records')
        )
    df_recovery_period2[period_columns] = df_recovery_period2[period_columns].fillna(0)
    df_recovery_period2['回本周期是否缺失'] = missing_period_mask.to_numpy()

    # In[114]:


    technologicalData = []

    for i, row in df_recovery_period2.iterrows():
        pre_value = float(row['预计回本期限'])
        post_value = float(row['预计回本周期'])
        diff = round(pre_value - post_value, 2)  # 计算提前年数
        summary = (
            "回本周期数据缺失，缺失项按0处理"
            if row['回本周期是否缺失']
            else f"技改后，站点回本周期提前{diff}年"
        )

        record = {
            "siteNum": row['old_code'],
            "statistics": [
                {"title": "技改前", "name": "预计回本期限", "value": pre_value, "unit": "年"},
                {"title": "技改后", "name": "预计回本周期", "value": post_value, "unit": "年"},
            ],
            "summary": summary
        }

        technologicalData.append(record)

    # In[115]:


    technologicalData

    # In[116]:


    # 表和字段注释
    table_comment = "技改站点_预计回本周期"
    column_comments = {
        'result': '预计回本周期',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(technologicalData, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_jigai_result_expectedPaybackPeriod",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )


    # In[ ]:
