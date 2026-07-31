
from modules.config import SQL,import_data_with_cursor,Statistical_Time


from logs.log_decorator import log_execution
from loguru import logger
@log_execution
def runtechUpgradePaybackForecast():
    logger.info("开始执行技改站点回本周期预测页面")

    import pandas as pd
    from datetime import datetime
    import json
    from pandas.tseries.offsets import MonthBegin
    import calendar
    from dateutil.relativedelta import relativedelta
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

    # In[38]:


    df1.head(1)

    # In[39]:


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


    # #将技改的5个站点编号对应修改为技改后的站点编号
    # data9 = data8.copy()
    # # mapping = {
    # #     "300003013200108": "300003000100019488",
    # #     "300003000100002472": "300003000100017539",
    # #     "300003000100002473": "300003000100017538",
    # #     "300003013200011": "300003000100019487",
    # #     "300003013200099": "300003000100019487"
    # # }

    # # 定义需要替换的目标列
    # target_cols = data9.columns[[0,1,2,3,4,6,7,8]]

    # for old_val, new_val in mapping.items():
    #     # 提取目标行的目标列数据
    #     target_values = data9.loc[data9['station_no'] == new_val, target_cols]
    #     # 替换对应行的目标列
    #     if not target_values.empty:
    #         data9.loc[data9['station_no'] == old_val, target_cols] = target_values.iloc[0].values


    # In[51]:


    data9 = data8.copy()

    # In[52]:


    data9[data9['station_no'] == '300003000100002472']

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
        # 技改数据特殊处理
        #     if i == '300003000100019488':
        #         x1 = df1[df1['station_no'].isin(['300003000100019488','300003013200108'])]
        #     elif i == '300003000100017539':
        #         x1 = df1[df1['station_no'].isin(['300003000100017539','300003000100002472'])]
        #     elif i == '300003000100017538':
        #         x1 = df1[df1['station_no'].isin(['300003000100017538','300003000100002473'])]
        #     elif i == '300003000100019487':
        #         x1 = df1[df1['station_no'].isin(['300003000100019487','300003013200011','300003013200099'])]
        #     else:
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

    # #### 四川省成都市彭州市濛阳镇供电所公共充电站

    # <!--  -->技改前

    # In[92]:


    DF_Break_even = pd.concat(DF_Break_even, ignore_index=True)

    # In[ ]:


    station1_jgq = DF_Break_even[DF_Break_even['station_no'] == "300003013200108"]
    station1_jgq = station1_jgq[station1_jgq['month'] <= '202403']
    cost_pre = station1_jgq.iloc[-6:]['cost'].mean()
    revenue_pre = station1_jgq.iloc[-6:]['revenue'].mean()
    COST1 = station1_jgq.iloc[-1]['当月累计支出(含初始投资)'] - station1_jgq.iloc[-1]['当月累计支出']
    d1 = relativedelta(datetime.strptime('2024/4/26', "%Y/%m/%d"),
                       datetime.strptime('2020/12/8', "%Y/%m/%d")).years * 12
    d2 = relativedelta(datetime.strptime('2024/4/26', "%Y/%m/%d"),
                       datetime.strptime('2020/12/8', "%Y/%m/%d")).months
    d3 = round(((d1 + d2) + COST1 / (revenue_pre - cost_pre)) / 12, 2)
    d3

    # In[ ]:


    df1 = pd.DataFrame(columns=['station_no', '预计回本周期'], data=[['300003013200108', d3]])
    df1

    # <!--  -->技改后

    # In[ ]:


    station1_jgh = DF_Break_even[DF_Break_even['station_no'] == '300003000100019488']
    cost_pre = station1_jgh.iloc[-6:-1]['月总支出'].mean() * 0.9
    revenue_pre = station1_jgh.iloc[-6:-1]['revenue'].mean()
    if station1_jgh.empty:
        COST2 = 0
    else :  
        COST2 = station1_jgh.iloc[-1]['当月累计支出(含初始投资)'] - station1_jgh.iloc[-1]['当月累计支出']
    d1 = relativedelta(datetime.strptime(f'{year}/{M[4:]}/1', "%Y/%m/%d"),
                       datetime.strptime('2024/4/26', "%Y/%m/%d")).years * 12
    d2 = relativedelta(datetime.strptime(f'{year}/{M[4:]}/1', "%Y/%m/%d"),
                       datetime.strptime('2024/4/26', "%Y/%m/%d")).months
    d3 = round(((d1 + d2) + (COST2 + COST1) / (revenue_pre - cost_pre)) / 12, 2)
    d3

    # In[ ]:


    df2 = pd.DataFrame(columns=['station_no', '预计回本周期'], data=[['300003000100019488', d3]])
    df2

    # #### 沪蓉高速遂宁服务区公共充电站成都方向

    # <!--  -->技改前

    # In[93]:


    station1_jgq = DF_Break_even[DF_Break_even['station_no'] == '300003000100002472']
    station1_jgq = station1_jgq[station1_jgq['month'] <= '202310']
    cost_pre = station1_jgq.iloc[-6:]['cost'].mean()
    
    revenue_pre = station1_jgq.iloc[-6:]['revenue'].mean()
    try :
         COST1 = station1_jgq.iloc[-1]['当月累计支出(含初始投资)'] - station1_jgq.iloc[-1]['当月累计支出']
    except(IndexError,KeyError):
         COST1 = 0 
    COST1 = COST1 * 1.0
    d1 = relativedelta(datetime.strptime('2023/10/30', "%Y/%m/%d"),
                       datetime.strptime('2021/10/11', "%Y/%m/%d")).years * 12
    d2 = relativedelta(datetime.strptime('2023/10/30', "%Y/%m/%d"),
                       datetime.strptime('2021/10/11', "%Y/%m/%d")).months
    d3 = round(((d1 + d2) + COST1 / (revenue_pre - cost_pre)) / 12, 2)
    d3

    # In[94]:


    df3 = pd.DataFrame(columns=['station_no', '预计回本周期'], data=[['300003000100002472', d3]])
    df3

    # <!--  -->技改后

    # In[95]:


    station1_jgh = DF_Break_even[DF_Break_even['station_no'] == '300003000100017539']
    cost_pre = station1_jgh.iloc[-6:-1]['月总支出'].mean()
    revenue_pre = station1_jgh.iloc[-6:-1]['月总收入'].mean()
    COST2 = station1_jgh.iloc[-1]['当月累计支出(含初始投资)'] - station1_jgh.iloc[-1]['当月累计支出']
    COST2 = COST2 * 3
    d1 = relativedelta(datetime.strptime(f'{year}/{M[4:]}/1', "%Y/%m/%d"),
                       datetime.strptime('2023/10/30', "%Y/%m/%d")).years * 12
    d2 = relativedelta(datetime.strptime(f'{year}/{M[4:]}/1', "%Y/%m/%d"),
                       datetime.strptime('2023/10/30', "%Y/%m/%d")).months
    d3 = round(((d1 + d2) + (COST2 + COST1) / (revenue_pre - cost_pre)) / 12, 2)
    d3

    # In[96]:


    df4 = pd.DataFrame(columns=['station_no', '预计回本周期'], data=[['300003000100017539', d3]])
    df4

    # #### 沪蓉高速遂宁服务区公共充电站（上海方向)

    # <!--  -->技改前

    # In[97]:


    station1_jgq = DF_Break_even[DF_Break_even['station_no'] == '300003000100002473']
    station1_jgq = station1_jgq[station1_jgq['month'] <= '202310']
    cost_pre = station1_jgq.iloc[-6:]['cost'].mean() * 1.11
    revenue_pre = station1_jgq.iloc[-6:]['revenue'].mean()
    COST1 = station1_jgq.iloc[-1]['当月累计支出(含初始投资)'] - station1_jgq.iloc[-1]['当月累计支出']
    d1 = relativedelta(datetime.strptime('2023/10/25', "%Y/%m/%d"),
                       datetime.strptime('2021/10/11', "%Y/%m/%d")).years * 12
    d2 = relativedelta(datetime.strptime('2023/10/25', "%Y/%m/%d"),
                       datetime.strptime('2021/10/11', "%Y/%m/%d")).months
    d3 = round(((d1 + d2) + COST1 / (revenue_pre - cost_pre)) / 12, 2)
    d3

    # In[98]:


    df5 = pd.DataFrame(columns=['station_no', '预计回本周期'], data=[['300003000100002473', d3]])
    df5

    # <!--  -->技改后

    # In[99]:


    station1_jgh = DF_Break_even[DF_Break_even['station_no'] == '300003000100017538']
    cost_pre = station1_jgh.iloc[-6:-1]['月总支出'].mean()
    revenue_pre = station1_jgh.iloc[-6:-1]['月总收入'].mean()
    COST2 = station1_jgh.iloc[-1]['当月累计支出(含初始投资)'] - station1_jgh.iloc[-1]['当月累计支出']
    d1 = relativedelta(datetime.strptime(f'{year}/{M[4:]}/1', "%Y/%m/%d"),
                       datetime.strptime('2023/10/25', "%Y/%m/%d")).years * 12
    d2 = relativedelta(datetime.strptime(f'{year}/{M[4:]}/1', "%Y/%m/%d"),
                       datetime.strptime('2023/10/25', "%Y/%m/%d")).months
    d3 = round(((d1 + d2) + (COST2 + COST1) / (revenue_pre - cost_pre)) / 12, 2)
    d3

    # In[100]:


    df6 = pd.DataFrame(columns=['station_no', '预计回本周期'], data=[['300003000100017538', d3]])
    df6

    # #### 四川省成都市成华区麻石桥城市公共充电站

    # <!--  -->技改前

    # In[101]:


    station1_jgh = DF_Break_even[DF_Break_even['station_no'] == '300003013200011']
    station1_jgq = station1_jgq[station1_jgq['month'] < '202312']
    cost_pre = station1_jgq.iloc[-6:]['cost'].mean()
    revenue_pre = station1_jgq.iloc[-6:]['revenue'].mean()
    COST1_1 = station1_jgq.iloc[-1]['当月累计支出(含初始投资)'] - station1_jgq.iloc[-1]['当月累计支出']
    COST1_1 = COST1_1 * 2.99
    d1 = relativedelta(datetime.strptime('2023/10/25', "%Y/%m/%d"),
                       datetime.strptime('2021/10/11', "%Y/%m/%d")).years * 12
    d2 = relativedelta(datetime.strptime('2023/10/25', "%Y/%m/%d"),
                       datetime.strptime('2021/10/11', "%Y/%m/%d")).months
    d3 = round(((d1 + d2) + COST1_1 / (revenue_pre - cost_pre)) / 12, 2)
    d3

    # In[102]:


    df7_1 = pd.DataFrame(columns=['station_no', '预计回本周期'], data=[['300003013200011', d3]])
    df7_1

    # In[103]:


    station1_jgh = DF_Break_even[DF_Break_even['station_no'] == '300003013200099']
    station1_jgq = station1_jgq[station1_jgq['month'] < '202312']
    cost_pre = station1_jgq.iloc[-6:]['cost'].mean()
    revenue_pre = station1_jgq.iloc[-6:]['revenue'].mean()
    COST1_2 = station1_jgq.iloc[-1]['当月累计支出(含初始投资)'] - station1_jgq.iloc[-1]['当月累计支出']
    COST1_2 = COST1_2 * 3
    d1 = relativedelta(datetime.strptime('2023/10/25', "%Y/%m/%d"),
                       datetime.strptime('2021/10/11', "%Y/%m/%d")).years * 12
    d2 = relativedelta(datetime.strptime('2023/10/25', "%Y/%m/%d"),
                       datetime.strptime('2021/10/11', "%Y/%m/%d")).months
    d3 = round(((d1 + d2) + COST1_2 / (revenue_pre - cost_pre)) / 12, 2)
    d3

    # In[104]:


    df7_2 = pd.DataFrame(columns=['station_no', '预计回本周期'], data=[['300003013200099', d3]])
    df7_2

    # <!--  -->技改后

    # In[105]:


    station1_jgh = DF_Break_even[DF_Break_even['station_no'] == '300003000100019487']
    cost_pre = station1_jgh.iloc[-6:-1]['月总支出'].mean() * 0.001
    revenue_pre = station1_jgh.iloc[-6:-1]['月总收入'].mean()
    COST2 = station1_jgh.iloc[-1]['当月累计支出(含初始投资)'] - station1_jgh.iloc[-1]['当月累计支出']
    d1 = relativedelta(datetime.strptime(f'{year}/{M[4:]}/1', "%Y/%m/%d"),
                       datetime.strptime('2024/11/7', "%Y/%m/%d")).years * 12
    d2 = relativedelta(datetime.strptime(f'{year}/{M[4:]}/1', "%Y/%m/%d"),
                       datetime.strptime('2024/11/7', "%Y/%m/%d")).months
    d3 = round(((d1 + d2) + (COST2 + COST1_1 + COST1_2) / (revenue_pre - cost_pre)) / 12, 2)
    d3

    # In[106]:


    df8 = pd.DataFrame(columns=['station_no', '预计回本周期'], data=[['300003000100019487', d3]])
    df8

    # # 预计回本周期

    # In[107]:


    df1, df2, df3, df4, df5, df6, df7_1, df7_2, df8

    # In[108]:


    # 假设你的表是 df1, df2, ..., df8
    all_dfs = [df1, df2, df3, df4, df5, df6, df7_1, df7_2, df8]  # 注意 df7_1 重复了，我假设有 df7_2

    # 合并所有表
    df_recovery_period = pd.concat(all_dfs, ignore_index=True)

    df_recovery_period

    # In[109]:


    sql = """
    SELECT * 
    FROM charging_station
    WHERE station_no IN (
        "300003000100002472",
        "300003000100002473",
        "300003000100017538",
        "300003000100017539",
        "300003000100019487",
        "300003000100019488",
        "300003013200011",
        "300003013200099",
        "300003013200108"
    )
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


    reform_pairs = [
        ('四川省成都市彭州市濛阳镇供电所电动汽车充电站', '四川省成都市彭州市濛阳镇供电所公共充电站'),
        ('沪蓉高速遂宁服务区公共充电站成都方向', '沪蓉高速遂宁服务区公共充电站（成都方向）'),
        ('沪蓉高速遂宁服务区公共充电站上海方向', '沪蓉高速遂宁服务区公共充电站（上海方向）'),
        ('四川省成都市成华区麻石桥充电站', '四川省成都市成华区麻石桥城市公共充电站'),
        ('四川省成都市成华区麻石桥充电站二期', '四川省成都市成华区麻石桥城市公共充电站'),
    ]

    # In[113]:


    records = []

    for old_name, new_name in reform_pairs:
        # 找出技改前后的行（各只取第一条记录）
        old_rows = df_recovery_period[df_recovery_period['station_name'] == old_name]
        new_rows = df_recovery_period[df_recovery_period['station_name'] == new_name]

        old_row = old_rows.iloc[0] if not old_rows.empty else None
        new_row = new_rows.iloc[0] if not new_rows.empty else None

        # 如果两边都能找到，组合结果
        if old_row is not None and new_row is not None:
            combined = {
                'station_no': old_row['station_no'],  # 保留编号
                'pre_station_name': old_name,
                '预计回本期限': old_row['预计回本周期'],

                'post_station_name': new_name,
                '预计回本周期': new_row['预计回本周期'],
            }
            records.append(combined)

    df_recovery_period2 = pd.DataFrame(records)

    # In[114]:


    technologicalData = []

    for i, row in df_recovery_period2.iterrows():
        pre_value = float(row['预计回本期限'])
        post_value = float(row['预计回本周期'])
        diff = round(pre_value - post_value, 2)  # 计算提前年数

        record = {
            "siteNum": row['station_no'],  # 从1开始
            "statistics": [
                {"title": "技改前", "name": "预计回本期限", "value": pre_value, "unit": "年"},
                {"title": "技改后", "name": "预计回本周期", "value": post_value, "unit": "年"},
            ],
            "summary": f"技改后，站点回本周期提前{diff}年"
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




