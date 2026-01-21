from logs.log_decorator import log_execution
from loguru import logger
from modules.config import SQL,import_data_with_cursor,Statistical_Time

@log_execution
def runcompanyWarningOverview():
    logger.info(f"开始执行公司预警概览页面")

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
    from itertools import product
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)
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

    # In[8]:

    df1['commissioning_year_month'] = df1['commissioning_time'].dt.strftime('%Y%m')
    print('筛选投运时间前：', df1.shape)
    df1 = df1[df1['commissioning_year_month'] <= M]
    print('筛选投运时间后：', df1.shape)

    # ### 数据类型转换

    # In[9]:

    df1['investment_amount'] = df1['investment_amount'].astype(str).str.replace(',', '').astype(float)
    df1.info()

    # ### 累计投运月份计算

    # In[10]:

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

    # In[11]:

    # ==================注释==================
    # 统计每个站点当前的累计总补贴
    # station_no：站点编号
    # total_subsidy：总补贴
    # ——共96条数据

    # In[12]:

    sql2 = """
    select year,station_no,IFNULL(total_subsidy,0) as total_subsidy from dp_subsidy_NEW;
    """
    df2 = SQL(sql2)
    print(df2.shape)
    print(df2.info())
    df2.head(1)

    # In[13]:

    # 数据类型转换、单位统一为元
    df2['total_subsidy'] = 10000 * df2['total_subsidy'].astype(str).str.replace(',', '').astype(float)

    # In[14]:

    df2_cal = df2.groupby('station_no', as_index=False).agg({'total_subsidy': 'sum'})
    df2_cal.head(1)

    # ## df3-站点运营总收入和总支出

    # In[15]:

    # ==================注释==================
    # 统计四川电动投资金额不为空的每个投运站点的总收入、总支出
    # station_no：站点编号
    # revenue：总收入
    # cost：总支出
    # ——共212条数据

    # In[16]:

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

    # In[17]:

    # 数据类型转换
    df3['revenue'] = df3['revenue'].astype(str).str.replace(',', '').astype(float)
    df3['cost'] = df3['cost'].astype(str).str.replace(',', '').astype(float)
    df3.info()

    # In[18]:

    df3_cal = df3.groupby('station_no', as_index=False).agg({'revenue': 'sum',
                                                             'cost': 'sum'})
    df3_cal

    # ## df4-站点租金

    # In[19]:

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

    # In[20]:

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

    # In[21]:

    # 数据类型转换
    df4['parking_fee'] = df4['parking_fee'].astype(str).str.replace(',', '').astype(float)
    df4.info()

    # ## df5-站点累计分成

    # In[22]:

    # ==================注释==================
    # 这里的分成指的是，四川电动旗下站点，分给其他单位的分成
    # station_no：站点编号
    # merchant_profit_amount：站点分成
    # --共352条数据

    # In[23]:

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

    # In[24]:

    # 数据类型转换
    df5['merchant_profit_amount'] = df5['merchant_profit_amount'].astype(str).str.replace(',', '').astype(float)
    df5.info()

    # In[25]:

    df5_cal = df5.groupby('station_no', as_index=False).agg({'merchant_profit_amount': 'sum'})
    df5_cal.head(1)

    # ## df6-站点运维费用

    # In[26]:

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

    # In[27]:

    df6[df6['station_no'] == '300003000100003226']

    # In[28]:

    # 数据类型转换、单位统一为元
    df6['maintenance_cost'] = 10000 * df6['maintenance_cost'].astype(str).str.replace(',', '').astype(float)

    # In[29]:

    df6_cal = df6.groupby('station_no', as_index=False).agg({'maintenance_cost': 'sum'})
    df6_cal.head(1)

    # # 数据合并

    # In[30]:

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

    # In[31]:

    df1.head(1)

    # In[32]:

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

    # In[33]:

    data1.columns

    # ## 补贴数据合并

    # In[34]:

    # 合并站点补贴数据
    print('含有补贴的站点数量：', df2_cal.shape)
    data2 = pd.merge(data1, df2_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data2.shape)
    print('四川电动投运站点中含有补贴的站点的数量：', data2[data2['total_subsidy'] != 0].shape)
    data2.head(1)

    # ## 运营数据合并

    # In[35]:

    # 合并各站点的运营总投入和总支出
    data3 = pd.merge(data2, df3_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data3.shape)
    print('四川电动投运站点中含有运营数据的站点的数量：', data3[data3['revenue'] != 0].shape)
    data3.head(1)

    # ## 站点租金合并

    # In[36]:

    # 合并站点租金
    data4 = pd.merge(data3, df4, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data4.shape)
    print('四川电动投运站点中含有租金数据的站点的数量：', data4[data4['parking_fee'] != 0].shape)
    data4.head(1)

    # ## 分成数据合并

    # In[37]:

    # 合并站点分成
    data5 = pd.merge(data4, df5_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data5.shape)
    print('四川电动投运站点中含有分成数据的站点的数量：', data5[data5['merchant_profit_amount'] != 0].shape)
    data5.head(1)

    # ## 运维数据合并

    # In[38]:

    # 合并站点运维费
    data6 = pd.merge(data5, df6_cal, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data6.shape)
    print('四川电动投运站点中含有运维数据的站点的数量：', data6[data6['maintenance_cost'] != 0].shape)
    data6.head(1)

    # ## 当年补贴数据合并

    # In[39]:

    df2_year = df2[df2['year'] == str(year) + '年']
    df2_year.columns = ['year', 'station_no', '当年_total_subsidy']
    df2_year = df2_year[['station_no', '当年_total_subsidy']]

    # In[40]:

    data7 = pd.merge(data6, df2_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data7.shape)
    print('四川电动投运站点中含有当年补贴数据的站点的数量：', data7[data7['当年_total_subsidy'] != 0].shape)
    data7.head(1)

    # ## 当年运营收入数据合并

    # In[41]:

    df3.head(1)

    # In[42]:
    df3['cba_month'].replace('None',pd.NA,inplace = True)
    df3.dropna(subset = ['cba_month'],inplace = True)

    df3['year'] = df3['cba_month'].astype(str).str[:4].astype(int)
    df3_year = df3[df3['year'] == year]
    df3_year = df3_year.groupby(by='station_no', as_index=False).agg({'revenue': 'sum'})
    df3_year.columns = ['station_no', '当年_revenue']
    df3_year

    # In[43]:

    # 合并当年运营收入
    data8 = pd.merge(data7, df3_year, how='left', on='station_no').fillna(0)
    print('合并后的投运的站点数量：', data8.shape)
    print('四川电动投运站点中含有当年运营收入数据的站点的数量：', data8[data8['当年_revenue'] != 0].shape)
    data8.head(1)

    # # 技改站数据合并-特殊处理

    # In[44]:

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

    # In[45]:

    data9[data9['station_no'] == '300003000100019487']

    # # 站点回本进度详情

    # ## 是否回本、滞后回本详情

    # In[46]:

    data9['in'] = data9['total_subsidy'] + data9['revenue']
    data9['out'] = data9['investment_amount'] + data9['cost'] + (data9['parking_fee'] * data9['累计投运月份数']) + data9['merchant_profit_amount'] + data9['maintenance_cost']
    data9['当年_in'] = data9['当年_total_subsidy'] + data9['当年_revenue']
    data9.head(1)

    # In[47]:

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

    # In[48]:

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

    # In[49]:

    data10.groupby(by='回本状态标签').agg({'station_no': 'count'})

    # ## 超预期回本详情

    # In[50]:

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

            # In[51]:

    data10.groupby(by='回本类型标签').agg({'station_no': 'count'})

    # In[52]:

    data10.columns = ['站点编号', '站点名称', '所属区域',
                      '站点类型', '总投资（万元）', '总成本（万元）',
                      '总收入（万元）', '设备折旧进度（%）', '今年总收入（万元）',
                      '静态投资回本进度（%）', '今年静态投资回本进度（%）',
                      '回本滞后率（%）', '回本状态标签', '回本类型标签']

    # ## 数据统一保留两位小数处理

    # In[53]:

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

    # # 展示数据计算、格式转换、储存

    # ## 站点回本进度详情表

    # In[54]:

    r = data10[['站点编号', '站点名称', '所属区域',
                '站点类型', '总投资（万元）', '总成本（万元）',
                '总收入（万元）', '静态投资回本进度（%）',
                '今年静态投资回本进度（%）', '设备折旧进度（%）',
                '回本滞后率（%）', '回本类型标签']]

    # ### r1-已回本站点

    # #### 数据计算

    # In[55]:

    r1 = r[r['回本类型标签'].isin(['超预期回本', '正常回本'])].copy()
    r1.drop('回本类型标签', axis=1, inplace=True)
    print(r1.shape)
    r1

    # #### 前端格式转换

    # In[56]:

    # 转为前端数据格式
    # 将DataFrame转换为字典列表（每行一个字典）
    r1.columns = ['id', 'siteName', 'region', 'siteType',
                  'investment', 'totalCost', 'revenue',
                  'PaybackProgress', 'annualReturn',
                  'depreciationProgress', 'paybackLagRate']
    tableData = r1.to_dict('records')
    # print(tableData)
    r1_json = json.dumps(tableData, ensure_ascii=False)
    # 打印结果（或返回给前端）
    # print(r1_json)
    r1_1 = pd.DataFrame({'siteNameFilters': [list(set(r1['siteName']))],
                         'regionFilters': [list(set(r1['region']))],
                         'siteTypeFilters': [list(set(r1['siteType']))],
                         'tableData': [tableData]})
    tableData1 = r1_1.to_dict('records')[0]
    r1_json_2 = json.dumps(tableData1, ensure_ascii=False)  # ,indent=2
    print(r1_json_2)
    Database_Table1 = pd.DataFrame({'result': r1_json_2, 'month': [M]})
    Database_Table1

    # #### 数据存储

    # In[57]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_站点回本进度详情_已回本站点"
    column_comments = {
        'const_tableData': '已回本站点详情表数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table1,
        table_name="dp_CompanyAlert_SiteRecovery_Detail_RecoveredSites",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### r2-正常待回本站点

    # #### 数据计算

    # In[58]:

    r2 = r[r['回本类型标签'].isin(['正常待回本'])].copy()
    r2.drop('回本类型标签', axis=1, inplace=True)
    print(r2.shape)
    r2.head(1)

    # #### 前端格式转换

    # In[59]:

    # #转为前端数据格式
    # # 将DataFrame转换为字典列表（每行一个字典）
    # r2.columns = ['id','siteName','region','siteType',
    #               'investment','totalCost','revenue',
    #               'PaybackProgress','annualReturn',
    #               'depreciationProgress','paybackLagRate']
    # tableData = r2.to_dict('records')
    # r2_json = json.dumps(tableData, ensure_ascii=False)
    # # 打印结果（或返回给前端）
    # print(r2_json)
    # Database_Table2 = pd.DataFrame({'const_tableData':r2_json,'month':[M]})
    # Database_Table2

    # In[60]:

    # 转为前端数据格式
    # 将DataFrame转换为字典列表（每行一个字典）
    r2.columns = ['id', 'siteName', 'region', 'siteType',
                  'investment', 'totalCost', 'revenue',
                  'PaybackProgress', 'annualReturn',
                  'depreciationProgress', 'paybackLagRate']
    tableData = r2.to_dict('records')
    # print(tableData)
    r2_json = json.dumps(tableData, ensure_ascii=False)
    # 打印结果（或返回给前端）
    # print(r2_json)
    r2_1 = pd.DataFrame({'siteNameFilters': [list(set(r2['siteName']))],
                         'regionFilters': [list(set(r2['region']))],
                         'siteTypeFilters': [list(set(r2['siteType']))],
                         'tableData': [tableData]})
    tableData1 = r2_1.to_dict('records')[0]
    r2_json_2 = json.dumps(tableData1, ensure_ascii=False)  # ,indent=2
    print(r2_json_2)
    Database_Table2 = pd.DataFrame({'result': r2_json_2, 'month': [M]})
    Database_Table2

    # #### 数据存储

    # In[61]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_站点回本进度详情_正常待回本"
    column_comments = {
        'const_tableData': '正常待回本站点详情表数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table2,
        table_name="dp_CompanyAlert_SiteRecovery_Detail_PendingSites",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### r3-滞后回本站点

    # #### 数据计算

    # In[62]:

    r3 = r[r['回本类型标签'].isin(['滞后未回本'])].copy()
    r3.drop('回本类型标签', axis=1, inplace=True)
    print(r3.shape)
    r3.head(1)

    # #### 前端格式转换

    # In[63]:

    # #转为前端数据格式
    # # 将DataFrame转换为字典列表（每行一个字典）
    # r3.columns = ['id','siteName','region','siteType',
    #               'investment','totalCost','revenue',
    #               'PaybackProgress','annualReturn',
    #               'depreciationProgress','paybackLagRate']
    # tableData = r3.to_dict('records')
    # r3_json = json.dumps(tableData, ensure_ascii=False)
    # # 打印结果（或返回给前端）
    # print(r3_json)
    # Database_Table3 = pd.DataFrame({'const_tableData':r3_json,'month':[M]})
    # Database_Table3

    # In[64]:

    # 转为前端数据格式
    # 将DataFrame转换为字典列表（每行一个字典）
    r3.columns = ['id', 'siteName', 'region', 'siteType',
                  'investment', 'totalCost', 'revenue',
                  'PaybackProgress', 'annualReturn',
                  'depreciationProgress', 'paybackLagRate']
    tableData = r3.to_dict('records')
    # print(tableData)
    r3_json = json.dumps(tableData, ensure_ascii=False)
    # 打印结果（或返回给前端）
    # print(r3_json)
    r3_1 = pd.DataFrame({'siteNameFilters': [list(set(r3['siteName']))],
                         'regionFilters': [list(set(r3['region']))],
                         'siteTypeFilters': [list(set(r3['siteType']))],
                         'tableData': [tableData]})
    tableData1 = r3_1.to_dict('records')[0]
    r3_json_2 = json.dumps(tableData1, ensure_ascii=False)  # ,indent=2
    print(r3_json_2)
    Database_Table3 = pd.DataFrame({'result': r3_json_2, 'month': [M]})
    Database_Table3

    # #### 数据存储

    # In[65]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_站点回本进度详情_滞后回本站点"
    column_comments = {
        'const_tableData': '滞后回本站点详情表数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table3,
        table_name="dp_CompanyAlert_SiteRecovery_Detail_DelayedSites",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 顶部三类站点占比数

    # In[66]:

    # 存在初始投资数据为0的情况，目前data10的数据基数实际只有212个，因此，需特殊处理得到全集352
    data11 = df1[df1['operation_status'] == '投运'][['station_no', 'station_name', 'city', 'station_category']]
    data11.columns = ['站点编号', '站点名称', '所属区域', '站点类型']
    data11 = pd.merge(data11, data10, how='left', on=['站点编号', '站点名称', '所属区域', '站点类型']).fillna(0)
    print(data11.shape)
    data11.head(1)

    # #### 数据计算

    # In[67]:

    # 已回本情况
    a1 = data11.shape[0]  # 站点总数
    a2 = data11[data11['回本状态标签'] == '已回本'].shape[0]
    rate = round((a2 / a1) * 100, 2)
    adict1 = {'name': '自营充电站共', 'value': a1, 'unit': '座'}
    adict2 = {'name': '已回本站点', 'value': a2, 'unit': '座'}
    adict3 = {'name': '回本率', 'value': rate, 'unit': '%'}
    adict4 = {'title': '已回本情况', 'content': [adict1, adict2, adict3]}
    print(adict4)

    # In[68]:

    # 未回本情况
    a1 = data11[data11['回本状态标签'] == '未回本'].shape[0]  # 未回本站点总数
    a2 = data11[data11['回本类型标签'] == '正常待回本'].shape[0]
    a3 = data11[data11['回本类型标签'] == '滞后未回本'].shape[0]
    rate1 = round((a2 / a1) * 100, 2)
    rate2 = round((a3 / a1) * 100, 2)
    bdict1 = {'name': '未回本站点共', 'value': a1, 'unit': '座'}
    bdict2 = {'name': '正常待回本站点共', 'value': a2, 'unit': '座'}
    bdict3 = {'name': '回本滞后站点共', 'value': a3, 'unit': '座'}
    bdict4 = {'name': '正常待回本率', 'value': rate1, 'unit': '%'}
    bdict5 = {'name': '回本滞后率', 'value': rate2, 'unit': '%'}
    bdict = {'title': '未回本情况', 'content': [bdict1, bdict2, bdict4, bdict3, bdict5]}
    print(bdict)

    # In[69]:

    r4_json = json.dumps([adict4, bdict], ensure_ascii=False)
    print(r4_json)
    Database_Table4 = pd.DataFrame({'targetData': r4_json, 'month': [M]})
    Database_Table4

    # #### 数据存储

    # In[70]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页-站点回本各类型数量占比"
    column_comments = {
        'targetData': '站点回本各类型数量占比',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table4,
        table_name="dp_CompanyAlert_SiteRecovery_QuantityProportion",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### r5-四川电动旗下充电站回本现状

    # #### 数据计算及格式转换

    # ##### json_2

    # In[71]:

    # 站点类型回本top3
    gb1_1 = data11.groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    gb1_2 = data11[data11['回本状态标签'] == '已回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    gb1 = pd.merge(gb1_1, gb1_2, how='left', on='站点类型')
    gb1.columns = ['站点类型', '总站点数量', '已回本站点数量']
    gb1['回本率'] = round((gb1['已回本站点数量'] / gb1['总站点数量']) * 100, 2)
    gb1.sort_values(by='回本率', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1.fillna(0, inplace=True)
    top3 = gb1.head(3)
    formatted_result = "、".join([f"{row['站点类型']}（{row['回本率']:.2f}%）" for _, row in top3.iterrows()])
    print(formatted_result)
    p2 = pd.DataFrame([['站点类型回本数量占比TOP3', formatted_result]], columns=['name', 'content'])
    p2

    # In[72]:

    # 地市区域回本top3
    gb1_1 = data11.groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})
    gb1_2 = data11[data11['回本状态标签'] == '已回本'].groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})
    gb1 = pd.merge(gb1_1, gb1_2, how='left', on='所属区域')
    gb1.columns = ['所属区域', '总站点数量', '已回本站点数量']
    gb1['回本率'] = round((gb1['已回本站点数量'] / gb1['总站点数量']) * 100, 2)
    gb1.sort_values(by='回本率', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1.fillna(0, inplace=True)
    top3 = gb1.head(3)
    formatted_result = "、".join([f"{row['所属区域']}（{row['回本率']:.2f}%）" for _, row in top3.iterrows()])
    print(formatted_result)
    p2 = pd.concat([p2, pd.DataFrame([['地市区域回本数量占比TOP3', formatted_result]], columns=['name', 'content'])], ignore_index=True)
    p2

    # In[73]:

    # 站点回本top3
    gb1 = data11[['站点名称', '静态投资回本进度（%）']].sort_values(by='静态投资回本进度（%）', ascending=False)
    gb1.reset_index(inplace=True, drop=True)
    gb1.fillna(0, inplace=True)
    top3 = gb1.head(3)
    formatted_result = "、".join([f"{row['站点名称']}（{row['静态投资回本进度（%）']:.2f}%）" for _, row in top3.iterrows()])
    print(formatted_result)
    p2 = pd.concat([p2, pd.DataFrame([['站点静态投资回本进度TOP3', formatted_result]], columns=['name', 'content'])], ignore_index=True)
    p2

    # In[74]:

    tableData = p2.to_dict('records')
    json_2 = json.dumps(tableData, ensure_ascii=False)
    print(json_2)

    # ##### json_4

    # In[75]:

    # 站点类型回本top3
    gb1_1 = data11[data11['回本状态标签'] == '未回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    gb1_2 = data11[data11['回本类型标签'] == '滞后未回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    gb1 = pd.merge(gb1_1, gb1_2, how='left', on='站点类型')
    gb1.columns = ['站点类型', '总站点数量', '已回本站点数量']
    gb1['回本率'] = round((gb1['已回本站点数量'] / gb1['总站点数量']) * 100, 2)
    gb1.sort_values(by='回本率', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1.fillna(0, inplace=True)
    top3 = gb1.head(3)
    formatted_result = "、".join([f"{row['站点类型']}（{row['回本率']:.2f}%）" for _, row in top3.iterrows()])
    print(formatted_result)
    p4 = pd.DataFrame([['站点类型回本滞后数量占比TOP3', formatted_result]], columns=['name', 'content'])
    p4

    # In[76]:

    # 地市区域回本top4
    gb1_1 = data11[data11['回本状态标签'] == '未回本'].groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})
    gb1_2 = data11[data11['回本类型标签'] == '滞后未回本'].groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})
    gb1 = pd.merge(gb1_1, gb1_2, how='left', on='所属区域')
    gb1.columns = ['所属区域', '总站点数量', '已回本站点数量']
    gb1['回本率'] = round((gb1['已回本站点数量'] / gb1['总站点数量']) * 100, 2)
    gb1.sort_values(by='回本率', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1.fillna(0, inplace=True)
    top3 = gb1.head(3)
    formatted_result = "、".join([f"{row['所属区域']}（{row['回本率']:.2f}%）" for _, row in top3.iterrows()])
    print(formatted_result)
    p4 = pd.concat([p4, pd.DataFrame([['地市区域回本滞后数量占比TOP3', formatted_result]], columns=['name', 'content'])], ignore_index=True)
    p4

    # In[77]:

    # 站点回本top4
    gb1 = data11[['站点名称', '回本滞后率（%）']].sort_values(by='回本滞后率（%）', ascending=False)
    gb1.reset_index(inplace=True, drop=True)
    gb1.fillna(0, inplace=True)
    top3 = gb1.head(3)
    formatted_result = "、".join([f"{row['站点名称']}（{row['回本滞后率（%）']:.2f}%）" for _, row in top3.iterrows()])
    print(formatted_result)
    p4 = pd.concat([p4, pd.DataFrame([['站点回本滞后率TOP3', formatted_result]], columns=['name', 'content'])], ignore_index=True)
    p4

    # In[78]:

    tableData = p4.to_dict('records')
    json_4 = json.dumps(tableData, ensure_ascii=False)
    print(json_4)

    # ##### r5_json

    # In[79]:

    statistics_list1 = json.loads(json_2)
    result_dict1 = {
        "title": "自营站点回本现状",
        "statistics": statistics_list1
    }

    statistics_list2 = json.loads(json_4)
    result_dict2 = {
        "title": "自营站点回本滞后情况",
        "statistics": statistics_list2
    }

    result_dict = [result_dict1, result_dict2]

    # 转化为最终的JSON格式
    r5_json = json.dumps(result_dict, ensure_ascii=False)
    # 查看方便代码
    # r5_json = json.dumps(result_dict, ensure_ascii=False,indent=2)
    print(r5_json)

    Database_Table5 = pd.DataFrame({'chargingStatus': r5_json, 'month': [M]})
    Database_Table5

    # #### 数据存储

    # In[80]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_四川电动旗下充电站回本现状_文字"
    column_comments = {
        'chargingStatus': '文字展示详情',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table5,
        table_name="dp_CompanyAlert_SiteRecovery_Text",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### r12-新增顶部表格数据

    # #### 数据计算

    # In[81]:

    data11.info()

    # In[82]:

    gb1 = data11[data11['总投资（万元）'] != 0].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    gb2 = data11[data11['回本状态标签'] == '已回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    gb3 = data11[data11['回本状态标签'] == '未回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    gb4 = data11[data11['回本类型标签'].isin(['正常待回本'])].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    gb5 = data11[data11['回本类型标签'] == '滞后未回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    gb1.columns = ['站点类型', '站点总数']
    gb2.columns = ['站点类型', '已回本站点']
    gb3.columns = ['站点类型', '未回本站点']
    gb4.columns = ['站点类型', '正常待回本站点']
    gb5.columns = ['站点类型', '回本滞后站点']
    result = pd.merge(gb1, gb2, how='left', on='站点类型')
    result = pd.merge(result, gb3, how='left', on='站点类型')
    result = pd.merge(result, gb4, how='left', on='站点类型')
    result = pd.merge(result, gb5, how='left', on='站点类型')
    result = result.fillna(0)
    result['已回本站点占比'] = round((result['已回本站点'] / result['站点总数']) * 100, 2)
    result['未回本站点占比'] = round((result['未回本站点'] / result['站点总数']) * 100, 2)
    result['正常待回本站点占比'] = round((result['正常待回本站点'] / result['未回本站点']) * 100, 2)
    result['回本滞后站点占比'] = round((result['回本滞后站点'] / result['未回本站点']) * 100, 2)
    result1 = result[['站点类型', '站点总数', '已回本站点',
                      '已回本站点占比', '未回本站点', '未回本站点占比',
                      '正常待回本站点', '正常待回本站点占比', '回本滞后站点', '回本滞后站点占比']]
    result1

    # In[83]:

    result1.columns = ['siteType', 'siteNum', 'ReturnedNum',
                       'ReturnedPercentage', 'NotReturnedNum',
                       'NotReturnedPercentage', 'WaitingNum',
                       'WaitingPercentage', 'lagNum', 'lagPercentage']
    tableData = result1.to_dict('records')
    json_12 = json.dumps(tableData, ensure_ascii=False)
    print(json_12)
    Database_Table12 = pd.DataFrame({'tableData': json_12, 'month': [M]})
    Database_Table12

    # #### 数据存储

    # In[84]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_顶部表格"
    column_comments = {
        'tableData': '表格数据详情',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table12,
        table_name="dp_CompanyAlert_Top_table",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 条形图展示-已回本情况

    # ### r6-站点类型

    # #### 数据计算

    # In[85]:

    # 站点类型回本top3
    r6_0 = data11[data11['回本状态标签'] == '已回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    r6_1 = data11[data11['回本类型标签'] == '正常回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    r6_2 = data11[data11['回本类型标签'] == '超预期回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    r6 = pd.merge(r6_0, r6_1, how='left', on='站点类型')
    r6 = pd.merge(r6, r6_2, how='left', on='站点类型')
    r6.columns = ['站点类型', '站点总数', '正常回本', '超预期回本']
    r6 = r6.sort_values(by='站点总数', ascending=False)
    r6.fillna(0, inplace=True)
    r6 = r6[['站点类型', '正常回本', '超预期回本']]
    r6

    # #### 前端格式转换

    # In[86]:

    # 1. 提取图例名称（固定）
    legendName = ['正常回本', '超预期回本']

    # 2. 提取x轴分类（站点类型）
    axisData = r6['站点类型'].tolist()

    # 3. 提取图表数据（正常回本、超预期回本的数值列表）
    normal_data = r6['正常回本'].tolist()
    exceed_data = r6['超预期回本'].tolist()
    chartData = [normal_data, exceed_data]

    # 4. 计算xAxis的值（正常回本+超预期回本全量数据的平均值）
    # 步骤1：合并两列数据为一个列表（全量数据）
    all_data = r6['正常回本'].tolist() + r6['超预期回本'].tolist()
    # 步骤2：计算平均值（总和 ÷ 数据个数）
    xAxis = round(sum(all_data) / r6.shape[0], 2)

    # 5. 其他字段
    yAxisName = "座"  # 按数据实际单位
    markLineName = '平均值'

    # 组合结果
    result = {
        "legendName": legendName,
        "axisData": axisData,
        "chartData": chartData,
        "yAxisName": yAxisName,
        #     "xAxis": xAxis,
        #     "markLineName": markLineName
    }

    # 转换为JSON
    r6_json = json.dumps(result, ensure_ascii=False)
    # r6_json = json.dumps(result, ensure_ascii=False, indent=2) #方便查看格式
    print(r6_json)

    Database_Table6 = pd.DataFrame({'data': r6_json, 'month': [M]})
    Database_Table6

    # #### 数据存储

    # In[87]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_已回本情况_站点类型条形图数据"
    column_comments = {
        'data': '条形图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table6,
        table_name="dp_CompanyAlert_BarChart_Recovered_SiteType",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### r7-地市区域

    # #### 数据计算

    # In[88]:

    # 所属区域回本top3
    r7_0 = data11[data11['回本状态标签'] == '已回本'].groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})

    r7_1 = data11[data11['回本类型标签'] == '正常回本'].groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})
    r7_2 = data11[data11['回本类型标签'] == '超预期回本'].groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})
    r7 = pd.merge(r7_0, r7_1, how='left', on='所属区域')
    r7 = pd.merge(r7, r7_2, how='left', on='所属区域')
    r7.columns = ['所属区域', '站点总数', '正常回本', '超预期回本']
    r7 = r7.sort_values(by='站点总数', ascending=False)
    r7.fillna(0, inplace=True)
    # r7 = r7[['所属区域','正常回本','超预期回本']].head(5)
    r7 = r7[['所属区域', '正常回本', '超预期回本']]
    r7

    # #### 前端格式转换

    # In[89]:

    # 1. 提取图例名称（固定）
    legendName = ['正常回本', '超预期回本']

    # 2. 提取x轴分类（所属区域）
    axisData = r7['所属区域'].tolist()

    # 3. 提取图表数据（正常回本、超预期回本的数值列表）
    normal_data = r7['正常回本'].tolist()
    exceed_data = r7['超预期回本'].tolist()
    chartData = [normal_data, exceed_data]

    # 4. 计算xAxis的值（正常回本+超预期回本全量数据的平均值）
    # 步骤1：合并两列数据为一个列表（全量数据）
    all_data = r7['正常回本'].tolist() + r7['超预期回本'].tolist()
    # 步骤2：计算平均值（总和 ÷ 数据个数）
    xAxis = round(sum(all_data) / r7.shape[0], 2)

    # 5. 其他字段
    yAxisName = "座"  # 按数据实际单位
    markLineName = '平均值'

    # 组合结果
    result = {
        "legendName": legendName,
        "axisData": axisData,
        "chartData": chartData,
        "yAxisName": yAxisName,
        #     "xAxis": xAxis,
        #     "markLineName": markLineName
    }

    # 转换为JSON
    r7_json = json.dumps(result, ensure_ascii=False)
    # r7_json = json.dumps(result, ensure_ascii=False, indent=2) #方便查看格式
    print(r7_json)

    Database_Table7 = pd.DataFrame({'data': r7_json, 'month': [M]})
    Database_Table7

    # #### 数据存储

    # In[90]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_已回本情况_地市区域条形图数据"
    column_comments = {
        'data': '条形图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table7,
        table_name="dp_CompanyAlert_BarChart_Recovered_city",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### r8-静态投资回收进度（已回本）

    # #### 数据计算及格式转换

    # In[91]:

    r8_0 = data11[data11['回本状态标签'] == '已回本'].groupby(by=['所属区域', '站点类型', '站点名称'], as_index=False).agg({'静态投资回本进度（%）': 'max'})
    print(r8_0.shape)
    list1 = list(set(r8_0['所属区域']))
    list1.insert(0, '全部区域')
    list2 = list(set(r8_0['站点类型']))
    list2.insert(0, '全部类型')
    # print(list1)
    # print(list2)
    # 生成所有可能的组合
    combinations = list(product(list1, list2))
    r8_1 = pd.DataFrame(combinations, columns=['urbanAreasValue', 'siteTypeValue'])
    r8_1['legendName'] = [['静态投资回本进度'] for _ in range(len(r8_1))]
    r8_1['axisData'] = '暂无'
    r8_1['chartData'] = '暂无'
    r8_1['yAxisName'] = '%'
    r8_1['xAxis'] = '无'
    r8_1['markLineName'] = '平均值'
    for i in range(r8_1.shape[0]):
        a = r8_1.iloc[i, 0]
        b = r8_1.iloc[i, 1]
        #     print(a,b)
        if (a == '全部区域') & (b == '全部类型'):
            r8_2 = r8_0.copy()
        elif (a == '全部区域') & (b != '全部类型'):
            r8_2 = r8_0.loc[r8_0['站点类型'] == b, :]
        elif (a != '全部区域') & (b == '全部类型'):
            r8_2 = r8_0.loc[r8_0['所属区域'] == a, :]
        else:
            r8_2 = r8_0.loc[(r8_0['所属区域'] == a) & (r8_0['站点类型'] == b), :]
        top5 = r8_2.sort_values(by='静态投资回本进度（%）', ascending=False).head(5)
        axisData = [f"TOP{j + 1} {name}" for j, name in enumerate(top5['站点名称'])]
        chartData = [top5['静态投资回本进度（%）'].tolist()]
        xAxis = round(r8_2['静态投资回本进度（%）'].mean(), 2)
        #     print(axisData)
        #     print(chartData)
        #     print(xAxis)
        r8_1.at[i, 'axisData'] = axisData
        r8_1.at[i, 'chartData'] = [chartData]
        r8_1.loc[i, 'xAxis'] = xAxis
        r8_1 = r8_1.fillna(0)
    tableData = r8_1.to_dict('records')
    r8_json = json.dumps(tableData, ensure_ascii=False)
    r8_json = json.dumps(tableData, ensure_ascii=False, indent=2)  # 方便查看格式
    # 打印结果（或返回给前端）
    print(r8_json)
    Database_Table8 = pd.DataFrame({'urbanAreasValue': [list1],
                                    'siteTypeValue': [list2],
                                    'data': r8_json,
                                    'month': [M]})
    Database_Table8

    # #### 数据存储

    # In[92]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_已回本情况_静态投资回收进度（已回本）条形图数据"
    column_comments = {
        'urbanAreasValue': '地市区域选项列表',
        'siteTypeValue': '站点类型选项列表',
        'data': '详细展示数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table8,
        table_name="dp_CompanyAlert_BarChart_Recovered_CityType",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 条形图展示-未回本情况

    # ### r9-站点类型

    # #### 数据计算

    # In[93]:

    # 站点类型回本top3
    r9_0 = data11[data11['回本状态标签'] == '未回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})

    r9_1 = data11[data11['回本类型标签'] == '正常待回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    r9_2 = data11[data11['回本类型标签'] == '滞后未回本'].groupby(by='站点类型', as_index=False).agg({'站点编号': 'count'})
    r9 = pd.merge(r9_0, r9_1, how='left', on='站点类型')
    r9 = pd.merge(r9, r9_2, how='left', on='站点类型')
    r9.columns = ['站点类型', '站点总数', '正常待回本', '滞后未回本']
    r9 = r9.sort_values(by='站点总数', ascending=False)
    r9.fillna(0, inplace=True)
    r9 = r9[['站点类型', '正常待回本', '滞后未回本']]
    r9

    # #### 前端格式转换

    # In[94]:

    # 1. 提取图例名称（固定）
    legendName = ['正常待回本', '回本滞后']

    # 2. 提取x轴分类（站点类型）
    axisData = r9['站点类型'].tolist()

    # 3. 提取图表数据（正常待回本、滞后未回本的数值列表）
    normal_data = r9['正常待回本'].tolist()
    exceed_data = r9['滞后未回本'].tolist()
    chartData = [normal_data, exceed_data]

    # 4. 计算xAxis的值（正常待回本+滞后未回本全量数据的平均值）
    # 步骤1：合并两列数据为一个列表（全量数据）
    all_data = r9['正常待回本'].tolist() + r9['滞后未回本'].tolist()
    # 步骤2：计算平均值（总和 ÷ 数据个数）
    xAxis = round(sum(all_data) / r9.shape[0], 2)  # 示例中总和=12，个数=12 → 12/12=1.0（见说明）

    # 5. 其他字段
    yAxisName = "座"  # 按数据实际单位
    markLineName = '平均值'

    # 组合结果
    result = {
        "legendName": legendName,
        "axisData": axisData,
        "chartData": chartData,
        "yAxisName": yAxisName,
        #     "xAxis": xAxis,
        #     "markLineName": markLineName
    }

    # 转换为JSON
    r9_json = json.dumps(result, ensure_ascii=False)
    # r9_json = json.dumps(result, ensure_ascii=False, indent=2) #方便查看格式
    print(r9_json)

    Database_Table9 = pd.DataFrame({'data': r9_json, 'month': [M]})
    Database_Table9

    # #### 数据存储

    # In[95]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_未回本情况_站点类型条形图数据"
    column_comments = {
        'data': '条形图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table9,
        table_name="dp_CompanyAlert_BarChart_PendingSites_SiteType",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### r10-地市区域

    # #### 数据计算

    # In[96]:

    # 所属区域回本top3
    r10_0 = data11[data11['回本状态标签'] == '未回本'].groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})

    r10_1 = data11[data11['回本类型标签'] == '正常待回本'].groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})
    r10_2 = data11[data11['回本类型标签'] == '滞后未回本'].groupby(by='所属区域', as_index=False).agg({'站点编号': 'count'})
    r10 = pd.merge(r10_0, r10_1, how='left', on='所属区域')
    r10 = pd.merge(r10, r10_2, how='left', on='所属区域')
    r10.columns = ['所属区域', '站点总数', '正常待回本', '滞后未回本']
    r10 = r10.sort_values(by='站点总数', ascending=False)
    r10.fillna(0, inplace=True)
    # r10 = r10[['所属区域','正常待回本','滞后未回本']].head(5)
    r10 = r10[['所属区域', '正常待回本', '滞后未回本']]
    r10

    # #### 前端格式转换

    # In[97]:

    # 1. 提取图例名称（固定）
    legendName = ['正常待回本', '回本滞后']

    # 2. 提取x轴分类（所属区域）
    axisData = r10['所属区域'].tolist()

    # 3. 提取图表数据（正常待回本、滞后未回本的数值列表）
    normal_data = r10['正常待回本'].tolist()
    exceed_data = r10['滞后未回本'].tolist()
    chartData = [normal_data, exceed_data]

    # 4. 计算xAxis的值（正常待回本+滞后未回本全量数据的平均值）
    # 步骤1：合并两列数据为一个列表（全量数据）
    all_data = r10['正常待回本'].tolist() + r10['滞后未回本'].tolist()
    # 步骤2：计算平均值（总和 ÷ 数据个数）
    xAxis = round(sum(all_data) / r10.shape[0], 2)  # 示例中总和=12，个数=12 → 12/12=1.0（见说明）

    # 5. 其他字段
    yAxisName = "座"  # 按数据实际单位
    markLineName = '平均值'

    # 组合结果
    result = {
        "legendName": legendName,
        "axisData": axisData,
        "chartData": chartData,
        "yAxisName": yAxisName,
        #     "xAxis": xAxis,
        #     "markLineName": markLineName
    }

    # 转换为JSON
    r10_json = json.dumps(result, ensure_ascii=False)
    # r10_json = json.dumps(result, ensure_ascii=False, indent=2) #方便查看格式
    print(r10_json)

    Database_Table10 = pd.DataFrame({'data': r10_json, 'month': [M]})
    Database_Table10

    # #### 数据存储

    # In[98]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_未回本情况_地市区域条形图数据"
    column_comments = {
        'data': '条形图数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table10,
        table_name="dp_CompanyAlert_BarChart_PendingSites_city",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### r11-静态投资回收进度（未回本）

    # #### 数据计算及格式转换

    # In[99]:

    r11_0 = data11[data11['回本状态标签'] == '未回本'].groupby(by=['所属区域', '站点类型', '站点名称'], as_index=False).agg({'静态投资回本进度（%）': 'max'})
    print(r11_0.shape)
    list1 = list(set(r11_0['所属区域']))
    list1.insert(0, '全部区域')
    list2 = list(set(r11_0['站点类型']))
    list2.insert(0, '全部类型')
    # print(list1)
    # print(list2)
    # 生成所有可能的组合
    combinations = list(product(list1, list2))
    r11_1 = pd.DataFrame(combinations, columns=['urbanAreasValue', 'siteTypeValue'])
    r11_1['legendName'] = [['静态投资回本进度'] for _ in range(len(r11_1))]
    r11_1['axisData'] = '暂无'
    r11_1['chartData'] = '暂无'
    r11_1['yAxisName'] = '%'
    r11_1['xAxis'] = '无'
    r11_1['markLineName'] = '平均值'
    for i in range(r11_1.shape[0]):
        a = r11_1.iloc[i, 0]
        b = r11_1.iloc[i, 1]
        #     print(a,b)
        if (a == '全部区域') & (b == '全部类型'):
            r11_2 = r11_0.copy()
        elif (a == '全部区域') & (b != '全部类型'):
            r11_2 = r11_0.loc[r11_0['站点类型'] == b, :]
        elif (a != '全部区域') & (b == '全部类型'):
            r11_2 = r11_0.loc[r11_0['所属区域'] == a, :]
        else:
            r11_2 = r11_0.loc[(r11_0['所属区域'] == a) & (r11_0['站点类型'] == b), :]
        top5 = r11_2.sort_values(by='静态投资回本进度（%）', ascending=False).head(5)
        axisData = [f"TOP{j + 1} {name}" for j, name in enumerate(top5['站点名称'])]
        chartData = [top5['静态投资回本进度（%）'].tolist()]
        xAxis = round(r11_2['静态投资回本进度（%）'].mean(), 2)
        #     print(axisData)
        #     print(chartData)
        #     print(xAxis)
        r11_1.at[i, 'axisData'] = axisData
        r11_1.at[i, 'chartData'] = [chartData]
        r11_1.loc[i, 'xAxis'] = xAxis
        r11_1 = r11_1.fillna(0)
    tableData = r11_1.to_dict('records')
    r11_json = json.dumps(tableData, ensure_ascii=False)
    # r11_json = json.dumps(tableData, ensure_ascii=False, indent=2) #方便查看格式
    # 打印结果（或返回给前端）
    print(r11_json)
    Database_Table11 = pd.DataFrame({'urbanAreasValue': [list1],
                                     'siteTypeValue': [list2],
                                     'data': r11_json,
                                     'month': [M]})
    Database_Table11

    # #### 数据存储

    # In[100]:

    # 数据存储
    # 定义注释
    table_comment = "公司预警_预警概览页_未回本情况_静态投资回收进度（未回本）条形图数据"
    column_comments = {
        'urbanAreasValue': '地市区域选项列表',
        'siteTypeValue': '站点类型选项列表',
        'data': '详细展示数据',
        'month': '分析年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=Database_Table11,
        table_name="dp_CompanyAlert_BarChart_PendingSites_CityType",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # In[ ]:

    # In[ ]:





