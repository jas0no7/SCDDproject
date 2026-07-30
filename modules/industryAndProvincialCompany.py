from logs.log_decorator import log_execution
from loguru import logger
from SCDDproject.modules.config import SQL,import_data_with_cursor,Statistical_Time

@log_execution
def runindustryAndProvincialCompany():
    logger.info(f"开始产业及省公司接入")
    import pandas as pd
    from datetime import datetime
    import json
    from pandas.tseries.offsets import MonthBegin
    import calendar
    from datetime import timedelta

    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)


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

    # In[9]:


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


    # In[10]:


    M_days = get_days_in_month(M)
    M_days


    # ## 获取截至当月全年的天数

    # In[11]:


    def days_from_year_start(M):
        # 解析M为年份和月份
        year = int(M[:4])  # 提取前4位作为年份
        month = int(M[4:])  # 提取后2位作为月份

        # 计算当月最后一天（如202505的最后一天是2025-05-31）
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        # 下个月第一天减去1天，得到当月最后一天
        last_day = datetime(next_year, next_month, 1) - timedelta(days=1)

        # 今年第一天（如2025-01-01）
        first_day = datetime(year, 1, 1)

        # 总天数 = 最后一天 - 第一天 + 1（包含首尾两天）
        total_days = (last_day - first_day).days + 1

        return total_days


    # In[12]:


    total_days = days_from_year_start(M)
    total_days


    # ## sql分区筛选

    # In[13]:


    def generate_result_str(df):
        # 用于查询当前月份及之前共12月的订单数据
        # 从DataFrame中提取month列并转换为字符串
        months = df['month'].astype(str)
        # 每个月份前添加"p"前缀
        prefixed_months = ['p' + month for month in months]
        # 用", "连接所有元素形成最终字符串
        result = ', '.join(prefixed_months)
        return result


    # 示例用法：
    # 假设你的DataFrame名为df
    result = generate_result_str(Data)

    result = result + ', ' + 'p' + last_year_month_str
    print(result)

    # # 初始数据读取及预处理

    # ## 站点基础信息表

    # ### 数据读入

    # In[14]:


    sql1 = """
    select * from charging_station as cs
    left join  rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    """
    Basic_Data = SQL(sql1)

    # In[15]:


    print(Basic_Data.info())

    # ### 投运时间年月提取

    # In[16]:


    Basic_Data['commissioning_year'] = Basic_Data['commissioning_time'].dt.year.astype(str)
    Basic_Data['commissioning_year_month'] = Basic_Data['commissioning_time'].dt.strftime('%Y%m')

    # ### 枪数量统计

    # In[17]:


    Basic_Data['charge_count'] = Basic_Data['dc_charge_point_count'].fillna(0) + Basic_Data['ac_charge_point_count'].fillna(0)
    print(Basic_Data.info())

    # ### 空值填充

    # In[18]:


    Basic_Data['station_capacity'] = Basic_Data['station_capacity'].fillna(0)

    # ### 四类站点归属单位类型划分

    # In[19]:


    Basic_Data['归属单位'] = '暂无'

    # 社会站
    condition1 = (
        # 条件1：plat_access_mode在指定的"社会站相关"列表中
            Basic_Data['plat_access_mode'].isin(['三方', '社会商户', '第三方', '第三方单位', '第三方合作']) |

            # 条件2：plat_access_mode为空值（对应SQL的is null）
            Basic_Data['plat_access_mode'].isna() |

            # 条件3：plat_access_mode在产业单位列表中且access_method为社会站模型
            (Basic_Data['plat_access_mode'].isin(['产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源']) &
             (Basic_Data['access_method'] == '社会站模型'))
    )
    Basic_Data.loc[condition1, '归属单位'] = '社会站'

    # 产业单位
    condition2 = (
        # 第一个条件：plat_access_mode在指定列表中，且access_method不等于'社会站模型'
            (Basic_Data['plat_access_mode'].isin(['产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源'])) &
            (Basic_Data['access_method'] != '社会站模型') &

            # 第二个条件：merchant_name不包含'供电公司'，或者等于特定值
            ((~Basic_Data['merchant_name'].str.contains('供电公司', na=False)) |
             (Basic_Data['merchant_name'] == '国网广元供电公司（产业单位）')) &

            # 第三个条件：merchant_name不包含'供电分公司'
            (~Basic_Data['merchant_name'].str.contains('供电分公司', na=False))
    )
    Basic_Data.loc[condition2, '归属单位'] = '产业单位'

    # 主业单位
    condition3 = (
        # 第一个主要条件：plat_access_mode在指定列表中且access_method不等于社会站模型
            (Basic_Data['plat_access_mode'].isin(['产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源'])) &
            (Basic_Data['access_method'] != '社会站模型') &

            # 第二个主要条件：满足以下两个子条件之一
            (
                # 子条件1：merchant_name包含'供电公司'且不等于特定值
                    (Basic_Data['merchant_name'].str.contains('供电公司', na=False) &
                     (Basic_Data['merchant_name'] != '国网广元供电公司（产业单位）')) |

                    # 子条件2：merchant_name包含'供电分公司'
                    Basic_Data['merchant_name'].str.contains('供电分公司', na=False)
            )
    )
    Basic_Data.loc[condition3, '归属单位'] = '主业单位'

    # 自营站点
    condition4 = Basic_Data['plat_access_mode'].isin(['电动公司'])
    Basic_Data.loc[condition4, '归属单位'] = '自营站'

    # In[20]:


    print('当前各类型投运站点数量分布情况：\n',
          Basic_Data[(Basic_Data['commissioning_year_month'] <= M) & (Basic_Data['operation_status'] == '投运')].groupby(by='归属单位').agg({'station_no': 'count'}))

    # ### 商户名称规范及合并

    # In[21]:


    # 合并1：
    merchant_names1 = [
        '四川巴中和兴电力有限责任公司平昌分公司',
        '四川巴中和兴电力有限责任公司南江分公司'
    ]

    Basic_Data.loc[
        Basic_Data['merchant_name'].isin(merchant_names1),
        'merchant_name'
    ] = '巴中和兴电力有限责任公司'

    # 合并2
    merchant_names2 = [
        '四川南充恒通电力有限公司供电服务分公司',
        '四川南充恒通电力有限公司南部县分公司'
    ]

    Basic_Data.loc[
        Basic_Data['merchant_name'].isin(merchant_names2),
        'merchant_name'
    ] = '四川南充恒通电力有限公司'

    # 替换1--将未匹配到商户的站点对应商户名称暂时修改为其他
    Basic_Data.loc[Basic_Data['merchant_name'].isna(), 'merchant_name'] = '其他'

    # In[22]:


    set(Basic_Data[Basic_Data['归属单位'] == '自营站']['merchant_name'])

    # ## 平台订单历史一年数据读取

    # In[23]:


    Order_Data = []
    for i in result.split(','):
        sql = f"""
        select charging_station_no,
        charging_end_time,
        DATE_FORMAT(order_create_time, '%Y%m') AS ym,
        order_create_time,
        trans_energy,
        trans_amount 
        from fin_plat_data_order PARTITION ({i})
        """
        df = SQL(sql)
        print(len(df), i)
        Order_Data.append(df)
    Order_Data = pd.concat(Order_Data)
    print(Order_Data.info())
    print(Order_Data.shape)

    # In[24]:


    Order_Data.head(1)

    # In[25]:


    # 时间及列名处理
    Order_Data['year'] = Order_Data['ym'].astype(str).str[:4]
    Order_Data.columns = ['station_no', 'charging_end_time', 'ym', 'order_create_time', 'trans_energy', 'trans_amount', 'year']
    Order_Data.head(1)

    # In[26]:


    # 空值处理
    Order_Data['trans_energy'] = Order_Data['trans_energy'].fillna(0)
    Order_Data['trans_amount'] = Order_Data['trans_amount'].fillna(0)

    # In[27]:


    # 重新建立索引
    Order_Data = Order_Data.reset_index(drop=True)

    # In[28]:


    Order_Data['trans_energy'] = Order_Data['trans_energy'].astype(float)
    Order_Data['trans_amount'] = Order_Data['trans_amount'].astype(float)

    # ## 站点经纬度数据读取

    # In[29]:


    sql2 = """
    select * from dp_station_low_lat
    """
    low_lat_Data = SQL(sql2)

    # In[30]:


    low_lat_Data.info()

    # In[31]:


    low_lat_Data.head(2)

    # # 顶部四个指标

    # ## 产业单位

    # In[32]:


    # 注意，枪数量只看投运，功率利用率、充电量、收入应该看投运+退运


    # ### 数据计算

    # In[33]:


    # 累计接入充电枪数
    d1 = int(Basic_Data[
                 (Basic_Data['归属单位'] == '产业单位') &
                 (Basic_Data['commissioning_year_month'] <= M) &
                 (Basic_Data['operation_status'] == '投运')
                 ]['charge_count'].sum())
    print('累计接入充电枪数：', d1)

    # 本年功率利用率
    # 1、获取当前月份及之前投运站点的信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no', 'station_name', 'station_capacity']]

    # 2、筛选订单表中当年且当前月份之前的数据
    df2 = Order_Data[(Order_Data['year'] == '2025') & (Order_Data['ym'] <= M)]

    # 3、按站点编号统计当年各站点的充电量数据
    gb1 = df2.groupby(by='station_no', as_index=False).agg({'trans_energy': 'sum',
                                                            'trans_amount': 'sum'})
    # 4、匹配产业单位对应站点电量数据
    df3 = pd.merge(df1[df1['station_capacity'] != 0], gb1[gb1['trans_energy'] != 0], how='left', on='station_no').fillna(0)
    df3 = df3[df3['trans_energy'] != 0]
    df3['功率利用率'] = df3['trans_energy'] / (df3['station_capacity'] * total_days * 24)
    d2 = round(df3['功率利用率'].mean() * 100, 2)
    print('本年功率利用率：', d2)

    # 本年累计充电量
    df4 = pd.merge(df1, gb1, how='left', on='station_no').fillna(0)
    d3 = round(df4['trans_energy'].sum() / 10000, 2)
    print('本年累计充电量：', d3)

    # 本年充电收入
    d4 = round(df4['trans_amount'].sum() / 10000, 2)
    print('本年充电收入：', d4)

    # In[34]:


    DF = pd.DataFrame()
    x1 = [
        {'title': '累计接入充电枪数', 'value': d1, 'unit': '个'},
        {'title': '本年功率利用率', 'value': d2, 'unit': '%'},
        {'title': '本年累计充电量', 'value': d3, 'unit': '万kWh'},
        {'title': '本年累计充电收入', 'value': d4, 'unit': '万元'}]
    x1 = json.dumps(x1, ensure_ascii=False)
    DF = pd.DataFrame({
        'target': [x1],
        'month': [M]
    })
    DF

    # ### 数据存储

    # In[35]:


    # 定义注释
    table_comment = "产业单位接入情况页-产业单位接入情况-顶部的4个重点展示数据"
    column_comments = {
        'target': '重点指标展示1',
        'month': '年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_TopKeyMetrics1",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位

    # In[36]:


    # 注意，枪数量只看投运，功率利用率、充电量、收入应该看投运+退运


    # ### 数据计算

    # In[37]:


    # 累计接入充电枪数
    d1 = int(Basic_Data[
                 (Basic_Data['归属单位'] == '主业单位') &
                 (Basic_Data['commissioning_year_month'] <= M) &
                 (Basic_Data['operation_status'] == '投运')
                 ]['charge_count'].sum())
    print('累计接入充电枪数：', d1)

    # 本年功率利用率
    # 1、获取当前月份及之前投运站点的信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no', 'station_name', 'station_capacity']]

    # 2、筛选订单表中当年且当前月份之前的数据
    df2 = Order_Data[(Order_Data['year'] == '2025') & (Order_Data['ym'] <= M)]

    # 3、按站点编号统计当年各站点的充电量数据
    gb1 = df2.groupby(by='station_no', as_index=False).agg({'trans_energy': 'sum',
                                                            'trans_amount': 'sum'})
    # 4、匹配主业单位对应站点电量数据
    df3 = pd.merge(df1[df1['station_capacity'] != 0], gb1[gb1['trans_energy'] != 0], how='left', on='station_no').fillna(0)
    df3['功率利用率'] = df3['trans_energy'] / (df3['station_capacity'] * total_days * 24)
    d2 = round(df3['功率利用率'].mean() * 100, 2)
    print('本年功率利用率：', d2)

    # 本年累计充电量
    df4 = pd.merge(df1, gb1, how='left', on='station_no').fillna(0)
    d3 = round(df4['trans_energy'].sum() / 10000, 2)
    print('本年累计充电量：', d3)

    # 本年充电收入
    d4 = round(df4['trans_amount'].sum() / 10000, 2)
    print('本年充电收入：', d4)

    # In[38]:


    DF = pd.DataFrame()
    x1 = [
        {'title': '累计接入充电枪数', 'value': d1, 'unit': '个'},
        {'title': '本年功率利用率', 'value': d2, 'unit': '%'},
        {'title': '本年累计充电量', 'value': d3, 'unit': '万kWh'},
        {'title': '本年累计充电收入', 'value': d4, 'unit': '万元'}]
    x1 = json.dumps(x1, ensure_ascii=False)
    DF = pd.DataFrame({
        'target': [x1],
        'month': [M]
    })
    DF

    # ### 数据存储

    # In[39]:


    # 定义注释
    table_comment = "主业单位接入情况页-主业单位接入情况-顶部的4个重点展示数据"
    column_comments = {
        'target': '重点指标展示2',
        'month': '年月'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_TopKeyMetrics1",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 第一板块-累计接入充电枪数

    # ## 产业单位-区域维度

    # ### 数据计算

    # In[40]:


    # 累计接入充电枪数
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'] == '投运')
        ][['city', 'charge_count', 'station_no']]

    gb1 = df1.groupby(by='city', as_index=False).agg({'charge_count': 'sum'})
    gb1.sort_values(by='charge_count', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['city', 'gun_acc', 'rank']
    gb1['gun_acc'] = gb1['gun_acc'].astype('int')
    gb1 = gb1[gb1['gun_acc'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "城市", "prop": "city"}, {"name": "累计接入充电枪数量（个）", "prop": "gun_acc"}, {"name": "城市排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['city']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['gun_acc'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '个'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['累计接入充电枪数量'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['city'].tolist()
    illustrate = f"产业单位接入充电枪数量区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = int(gb1['gun_acc'].mean())
    # xAxis = json.dumps([xAxis], ensure_ascii=False)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[41]:


    # 定义注释
    table_comment = "产业单位接入情况页_中间地图左侧_平台累计接入充电枪数_区域维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Num_Qy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-区域维度

    # ### 数据计算

    # In[42]:


    # 累计接入充电枪数
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'] == '投运')
        ][['city', 'charge_count', 'station_no']]

    gb1 = df1.groupby(by='city', as_index=False).agg({'charge_count': 'sum'})
    gb1.sort_values(by='charge_count', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['city', 'gun_acc', 'rank']
    gb1['gun_acc'] = gb1['gun_acc'].astype('int')
    gb1 = gb1[gb1['gun_acc'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "城市", "prop": "city"}, {"name": "累计接入充电枪数量（个）", "prop": "gun_acc"}, {"name": "城市排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['city']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['gun_acc'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '个'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['累计接入充电枪数量'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['city'].tolist()
    illustrate = f"主业单位接入充电枪数量区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = int(gb1['gun_acc'].mean())
    # xAxis = json.dumps([xAxis], ensure_ascii=False)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[43]:


    # 定义注释
    table_comment = "主业单位接入情况页_中间地图左侧_平台累计接入充电枪数_区域维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Num_Qy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 产业单位-运营商维度

    # ### 数据计算

    # In[44]:


    # 累计接入充电枪数
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'] == '投运')
        ][['merchant_name', 'charge_count', 'station_no']]

    gb1 = df1.groupby(by='merchant_name', as_index=False).agg({'charge_count': 'sum'})
    gb1.sort_values(by='charge_count', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['merchant_name', 'gun_acc', 'rank']
    gb1['gun_acc'] = gb1['gun_acc'].astype('int')
    gb1 = gb1[gb1['gun_acc'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "运营商", "prop": "merchant_name"}, {"name": "累计接入充电枪数量（个）", "prop": "gun_acc"}, {"name": "运营商排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['merchant_name']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['gun_acc'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '个'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['累计接入充电枪数量'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['merchant_name'].tolist()
    illustrate = f"产业单位接入充电枪数量运营商维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = int(gb1['gun_acc'].mean())
    # xAxis = json.dumps([xAxis], ensure_ascii=False)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[45]:


    # 定义注释
    table_comment = "产业单位接入情况页_平台累计接入充电枪数_运营商维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Num_Yy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-运营商维度

    # ### 数据计算

    # In[46]:


    # 累计接入充电枪数
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'] == '投运')
        ][['merchant_name', 'charge_count', 'station_no']]

    gb1 = df1.groupby(by='merchant_name', as_index=False).agg({'charge_count': 'sum'})
    gb1.sort_values(by='charge_count', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['merchant_name', 'gun_acc', 'rank']
    gb1['gun_acc'] = gb1['gun_acc'].astype('int')
    gb1 = gb1[gb1['gun_acc'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "运营商", "prop": "merchant_name"}, {"name": "累计接入充电枪数量（个）", "prop": "gun_acc"}, {"name": "运营商排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['merchant_name']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['gun_acc'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '个'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['累计接入充电枪数量'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['merchant_name'].tolist()
    illustrate = f"主业单位接入充电枪数量运营商维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = int(gb1['gun_acc'].mean())
    # xAxis = json.dumps([xAxis], ensure_ascii=False)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[47]:


    # 定义注释
    table_comment = "主业单位接入情况页_平台累计接入充电枪数_运营商维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Num_Yy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 产业单位-时间维度

    # ### 数据计算

    # In[48]:


    # 累计接入充电枪数
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'] == '投运')
        ][['commissioning_year_month', 'charge_count', 'station_no']]
    # 分组统计每个年月投运的枪数量
    df2 = df1.groupby(by='commissioning_year_month', as_index=False).agg({'charge_count': 'sum'})

    # 将近12个月份升序排序
    df3 = Data.sort_values(by='month').reset_index(drop=True)

    # 计算累计值
    df3['cumulative_charge_count'] = df3['month'].apply(
        lambda x: df2[df2['commissioning_year_month'] <= x]['charge_count'].sum()
    )
    df3['cumulative_charge_count'] = df3['cumulative_charge_count'].astype('int')

    # 生成chartData
    chartData = json.dumps([list(df3['cumulative_charge_count'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成statisticsData
    # 同比
    a1 = int(df1[df1['commissioning_year_month'] <= last_year_month_str]['charge_count'].sum())
    a2 = int(df1['charge_count'].sum())
    a3 = round((a2 - a1) / a1 * 100, 2)
    statisticsData = [{"title": "当前累计接入充电枪", "value": a2, "unit": "个"},
                      {"title": "累计同比增长", "value": a3, "unit": "%"}]
    statisticsData = json.dumps(statisticsData, ensure_ascii=False)
    print('statisticsData：\n', statisticsData)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成axisData
    axisData = json.dumps(list(df3['month']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成条形图单位
    YxisName = '个'
    print('YxisName：\n', YxisName)

    # 生成条形图单位
    legendName = [["平台累计接入充电枪数"]]
    print('legendName：\n', legendName)

    DF = pd.DataFrame({
        'chartData': chartData,
        'statisticsData': statisticsData,
        'month': month,
        'axisData': axisData,
        'YxisName': YxisName,
        'legendName': legendName
    })
    DF

    # ### 数据存储

    # In[49]:


    # 定义注释
    table_comment = "产业单位接入情况页_平台累计接入充电枪数_时间维度"
    column_comments = {
        'chartData': '统计图数据',
        'statisticsData': '表格下面文字部分',
        'month': '分析月份',
        'axisData': '横坐标数据',
        'YxisName': '单位',
        'legendName': '指标标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Num_Zd",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-时间维度

    # ### 数据计算

    # In[50]:


    # 累计接入充电枪数
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'] == '投运')
        ][['commissioning_year_month', 'charge_count', 'station_no']]
    # 分组统计每个年月投运的枪数量
    df2 = df1.groupby(by='commissioning_year_month', as_index=False).agg({'charge_count': 'sum'})

    # 将近12个月份升序排序
    df3 = Data.sort_values(by='month').reset_index(drop=True)

    # 计算累计值
    df3['cumulative_charge_count'] = df3['month'].apply(
        lambda x: df2[df2['commissioning_year_month'] <= x]['charge_count'].sum()
    )
    df3['cumulative_charge_count'] = df3['cumulative_charge_count'].astype('int')

    # 生成chartData
    chartData = json.dumps([list(df3['cumulative_charge_count'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成statisticsData
    # 同比
    a1 = int(df1[df1['commissioning_year_month'] <= last_year_month_str]['charge_count'].sum())
    a2 = int(df1['charge_count'].sum())
    a3 = round((a2 - a1) / a1 * 100, 2)
    statisticsData = [{"title": "当前累计接入充电枪", "value": a2, "unit": "个"},
                      {"title": "累计同比增长", "value": a3, "unit": "%"}]
    statisticsData = json.dumps(statisticsData, ensure_ascii=False)
    print('statisticsData：\n', statisticsData)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成axisData
    axisData = json.dumps(list(df3['month']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成条形图单位
    YxisName = '个'
    print('YxisName：\n', YxisName)

    # 生成条形图单位
    legendName = [["平台累计接入充电枪数"]]
    print('legendName：\n', legendName)

    DF = pd.DataFrame({
        'chartData': chartData,
        'statisticsData': statisticsData,
        'month': month,
        'axisData': axisData,
        'YxisName': YxisName,
        'legendName': legendName
    })
    DF

    # ### 数据存储

    # In[51]:


    # 定义注释
    table_comment = "主业单位接入情况页_平台累计接入充电枪数_时间维度"
    column_comments = {
        'chartData': '统计图数据',
        'statisticsData': '表格下面文字部分',
        'month': '分析月份',
        'axisData': '横坐标数据',
        'YxisName': '单位',
        'legendName': '指标标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Num_Zd",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 第二板块-本月充电量

    # ## 产业单位-区域维度

    # ### 数据计算

    # In[52]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['city', 'station_no']]

    # 本月充电量
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_energy': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)

    gb1 = df3.groupby(by='city', as_index=False).agg({'trans_energy': 'sum'})
    gb1.sort_values(by='trans_energy', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['city', 'energy', 'rank']
    gb1['energy'] = round(gb1['energy'], 2)
    gb1 = gb1[gb1['energy'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "城市", "prop": "city"}, {"name": "本月充电量（kWh）", "prop": "energy"}, {"name": "城市排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['city']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['energy'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = 'kWh'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['本月充电量（kWh）'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['city'].tolist()
    illustrate = f"产业单位本月充电量区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['energy'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[53]:


    # 定义注释
    table_comment = "产业单位接入情况页_平台本月充电量_区域维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Elec_Qy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-区域维度

    # ### 数据计算

    # In[54]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['city', 'station_no']]

    # 本月充电量
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_energy': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)

    gb1 = df3.groupby(by='city', as_index=False).agg({'trans_energy': 'sum'})
    gb1.sort_values(by='trans_energy', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['city', 'energy', 'rank']
    gb1['energy'] = round(gb1['energy'], 2)
    gb1 = gb1[gb1['energy'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "城市", "prop": "city"}, {"name": "本月充电量（kWh）", "prop": "energy"}, {"name": "城市排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['city']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['energy'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = 'kWh'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['本月充电量（kWh）'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['city'].tolist()
    illustrate = f"主业单位本月充电量区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['energy'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[55]:


    # 定义注释
    table_comment = "主业单位接入情况页_平台本月充电量_区域维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Elec_Qy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 产业单位-运营商维度

    # ### 数据计算

    # In[56]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['merchant_name', 'station_no']]

    # 本月充电量
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_energy': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)

    gb1 = df3.groupby(by='merchant_name', as_index=False).agg({'trans_energy': 'sum'})
    gb1.sort_values(by='trans_energy', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['merchant_name', 'energy', 'rank']
    gb1['energy'] = round(gb1['energy'], 2)
    gb1 = gb1[gb1['energy'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "运营商", "prop": "merchant_name"}, {"name": "本月充电量（kWh）", "prop": "energy"}, {"name": "运营商排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['merchant_name']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['energy'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = 'kWh'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['本月充电量（kWh）'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['merchant_name'].tolist()
    illustrate = f"产业单位本月充电量运营商维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['energy'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[57]:


    # 定义注释
    table_comment = "产业单位接入情况页_平台本月充电量_运营商维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Elec_Yy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-运营商维度

    # ### 数据计算

    # In[58]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['merchant_name', 'station_no']]

    # 本月充电量
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_energy': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)

    gb1 = df3.groupby(by='merchant_name', as_index=False).agg({'trans_energy': 'sum'})
    gb1.sort_values(by='trans_energy', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['merchant_name', 'energy', 'rank']
    gb1['energy'] = round(gb1['energy'], 2)
    gb1 = gb1[gb1['energy'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "运营商", "prop": "merchant_name"}, {"name": "本月充电量（kWh）", "prop": "energy"}, {"name": "运营商排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['merchant_name']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['energy'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = 'kWh'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['本月充电量（kWh）'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['merchant_name'].tolist()
    illustrate = f"主业单位本月充电量运营商维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['energy'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[59]:


    # 定义注释
    table_comment = "主业单位接入情况页_平台本月充电量_运营商维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Elec_Yy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 产业单位-时间维度

    # ### 数据计算

    # In[60]:


    # 月充电量
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no']]
    # 本月充电量
    df2 = Order_Data.groupby(by=['station_no', 'ym'], as_index=False).agg({'trans_energy': 'sum'})
    df2 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    gb1 = df2.groupby(by='ym', as_index=False).agg({'trans_energy': 'sum'})
    gb1.columns = ['month', 'trans_energy']
    gb1['trans_energy'] = round(gb1['trans_energy'], 2)

    # 将近12个月份升序排序并获取对应数据
    df3 = Data.sort_values(by='month').reset_index(drop=True)
    df3 = pd.merge(df3, gb1, how='left', on='month').fillna(0)

    # 生成chartData
    chartData = json.dumps([list(df3['trans_energy'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成statisticsData
    # 同比
    a1 = round(gb1.loc[gb1['month'] == last_year_month_str, 'trans_energy'].values[0], 2)
    a2 = round(gb1.loc[gb1['month'] == M, 'trans_energy'].values[0], 2)
    a3 = round((a2 - a1) / a1 * 100, 2)
    statisticsData = [{"title": "本月充电量", "value": a2, "unit": "kWh"},
                      {"title": "同比增长", "value": a3, "unit": "%"}]
    statisticsData = json.dumps(statisticsData, ensure_ascii=False)
    print('statisticsData：\n', statisticsData)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成axisData
    axisData = json.dumps(list(df3['month']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成条形图单位
    YxisName = 'kWh'
    print('YxisName：\n', YxisName)

    # 生成条形图单位
    legendName = [["月充电量"]]
    print('legendName：\n', legendName)

    DF = pd.DataFrame({
        'chartData': chartData,
        'statisticsData': statisticsData,
        'month': month,
        'axisData': axisData,
        'YxisName': YxisName,
        'legendName': legendName
    })
    DF

    # ### 数据存储

    # In[61]:


    # 定义注释
    table_comment = "产业单位接入情况页_中间地图左侧_平台本月充电量_站点维度"
    column_comments = {
        'chartData': '统计图数据',
        'statisticsData': '表格下面文字部分',
        'month': '分析月份',
        'axisData': '横坐标数据',
        'YxisName': '单位',
        'legendName': '指标标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Elec_Zd",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-时间维度

    # ### 数据计算

    # In[62]:


    # 累计接入充电枪数
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no']]
    # 本月充电量
    df2 = Order_Data.groupby(by=['station_no', 'ym'], as_index=False).agg({'trans_energy': 'sum'})
    df2 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    gb1 = df2.groupby(by='ym', as_index=False).agg({'trans_energy': 'sum'})
    gb1.columns = ['month', 'trans_energy']
    gb1['trans_energy'] = round(gb1['trans_energy'], 2)

    # 将近12个月份升序排序并获取对应数据
    df3 = Data.sort_values(by='month').reset_index(drop=True)
    df3 = pd.merge(df3, gb1, how='left', on='month').fillna(0)

    # 生成chartData
    chartData = json.dumps([list(df3['trans_energy'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成statisticsData
    # 同比
    a1 = round(gb1.loc[gb1['month'] == last_year_month_str, 'trans_energy'].values[0], 2)
    a2 = round(gb1.loc[gb1['month'] == M, 'trans_energy'].values[0], 2)
    a3 = round((a2 - a1) / a1 * 100, 2)
    statisticsData = [{"title": "本月充电量", "value": a2, "unit": "kWh"},
                      {"title": "同比增长", "value": a3, "unit": "%"}]
    statisticsData = json.dumps(statisticsData, ensure_ascii=False)
    print('statisticsData：\n', statisticsData)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成axisData
    axisData = json.dumps(list(df3['month']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成条形图单位
    YxisName = 'kWh'
    print('YxisName：\n', YxisName)

    # 生成条形图单位
    legendName = [["月充电量"]]
    print('legendName：\n', legendName)

    DF = pd.DataFrame({
        'chartData': chartData,
        'statisticsData': statisticsData,
        'month': month,
        'axisData': axisData,
        'YxisName': YxisName,
        'legendName': legendName
    })
    DF

    # ### 数据存储

    # In[63]:


    # 定义注释
    table_comment = "主业单位接入情况页_中间地图左侧_平台本月充电量_站点维度"
    column_comments = {
        'chartData': '统计图数据',
        'statisticsData': '表格下面文字部分',
        'month': '分析月份',
        'axisData': '横坐标数据',
        'YxisName': '单位',
        'legendName': '指标标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Elec_Zd",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 第三板块-功率利用率

    # ## 产业单位-区域维度

    # ### 数据计算

    # In[64]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['city', 'station_no', 'station_capacity']]
    # 剔除退运功率为0的站点
    df1 = df1[df1['station_capacity'] > 0]

    # 本月充电量
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_energy': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    df3 = df3[df3['trans_energy'] != 0]
    df3['power_rate'] = round((df3['trans_energy'] / (df3['station_capacity'] * M_days * 24)) * 100, 2)

    gb1 = df3.groupby(by='city', as_index=False).agg({'power_rate': 'mean'})
    gb1.sort_values(by='power_rate', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['city', 'pue', 'rank']
    gb1['pue'] = round(gb1['pue'], 2)
    gb1 = gb1[gb1['pue'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "城市", "prop": "city"}, {"name": "功率利用率（%）", "prop": "pue"}, {"name": "城市排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['city']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['pue'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '%'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['平均功率利用率'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['city'].tolist()
    illustrate = f"产业单位本月功率利用率区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['pue'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[65]:


    # 定义注释
    table_comment = "产业单位接入情况页_平台功率利用率_区域维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Power_Qy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-区域维度

    # ### 数据计算

    # In[66]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['city', 'station_no', 'station_capacity']]
    # 剔除退运功率为0的站点
    df1 = df1[df1['station_capacity'] > 0]

    # 本月充电量
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_energy': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    df3 = df3[df3['trans_energy'] != 0]
    df3['power_rate'] = round((df3['trans_energy'] / (df3['station_capacity'] * M_days * 24)) * 100, 2)

    gb1 = df3.groupby(by='city', as_index=False).agg({'power_rate': 'mean'})
    gb1.sort_values(by='power_rate', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['city', 'pue', 'rank']
    gb1['pue'] = round(gb1['pue'], 2)
    gb1 = gb1[gb1['pue'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "城市", "prop": "city"}, {"name": "功率利用率（%）", "prop": "pue"}, {"name": "城市排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['city']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['pue'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '%'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['平均功率利用率'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['city'].tolist()
    illustrate = f"主业单位本月功率利用率区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['pue'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[67]:


    # 定义注释
    table_comment = "主业单位接入情况页_平台功率利用率_区域维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Power_Qy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 产业单位-运营商维度

    # ### 数据计算

    # In[68]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['merchant_name', 'station_no', 'station_capacity']]
    # 剔除退运功率为0的站点
    df1 = df1[df1['station_capacity'] > 0]

    # 本月充电量
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_energy': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    df3 = df3[df3['trans_energy'] != 0]
    df3['power_rate'] = round((df3['trans_energy'] / (df3['station_capacity'] * M_days * 24)) * 100, 2)

    gb1 = df3.groupby(by='merchant_name', as_index=False).agg({'power_rate': 'mean'})
    gb1.sort_values(by='power_rate', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['operator', 'pue', 'rank']
    gb1['pue'] = round(gb1['pue'], 2)
    gb1 = gb1[gb1['pue'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "运营商", "prop": 'operator'}, {"name": "功率利用率（%）", "prop": "pue"}, {"name": "运营商排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['operator']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['pue'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '%'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['平均功率利用率'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['operator'].tolist()
    illustrate = f"产业单位本月功率利用率区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['pue'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[69]:


    # 定义注释
    table_comment = "产业单位接入情况页_中间地图左侧_平台功率利用率_运营商维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Power_Yy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-运营商维度

    # ### 数据计算

    # In[70]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['merchant_name', 'station_no', 'station_capacity']]
    # 剔除退运功率为0的站点
    df1 = df1[df1['station_capacity'] > 0]

    # 本月充电量
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_energy': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    df3 = df3[df3['trans_energy'] != 0]
    df3['power_rate'] = round((df3['trans_energy'] / (df3['station_capacity'] * M_days * 24)) * 100, 2)

    gb1 = df3.groupby(by='merchant_name', as_index=False).agg({'power_rate': 'mean'})
    gb1.sort_values(by='power_rate', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['operator', 'pue', 'rank']
    gb1['pue'] = round(gb1['pue'], 2)
    gb1 = gb1[gb1['pue'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "运营商", "prop": 'operator'}, {"name": "功率利用率（%）", "prop": "pue"}, {"name": "运营商排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['operator']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['pue'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '%'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['平均功率利用率'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['operator'].tolist()
    illustrate = f"主业单位本月功率利用率区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['pue'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[71]:


    # 定义注释
    table_comment = "主业单位接入情况页_中间地图左侧_平台功率利用率_运营商维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Power_Yy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 产业单位-时间维度

    # ### 数据计算

    # In[72]:


    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no', 'station_capacity']]

    # 每月充电量
    df2 = Order_Data.groupby(by=['station_no', 'ym'], as_index=False).agg({'trans_energy': 'sum'})
    df2 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    gb1 = df2.groupby(by=['ym', 'station_no'], as_index=False).agg({'trans_energy': 'sum', 'station_capacity': 'max'})
    gb1 = gb1[(gb1['trans_energy'] != 0) & (gb1['ym'] != 0) & (gb1['station_capacity'] != 0)].reset_index(drop=True)

    # 循环获取每行月份对应的总天数
    gb1['pue'] = 0
    for i in range(gb1.shape[0]):
        day = get_days_in_month(gb1.loc[i, 'ym'])
        gb1.loc[i, 'pue'] = round((gb1.loc[i, 'trans_energy'] / (gb1.loc[i, 'station_capacity'] * day * 24)) * 100, 2)
    gb1 = gb1.groupby(by='ym', as_index=False).agg({'pue': 'mean'})
    gb1['pue'] = round(gb1['pue'], 2)
    gb1.columns = ['month', 'pue']

    # 将近12个月份升序排序并获取对应数据
    df3 = Data.sort_values(by='month').reset_index(drop=True)
    df3 = pd.merge(df3, gb1, how='left', on='month').fillna(0)

    # 生成chartData
    chartData = json.dumps([list(df3['pue'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成statisticsData
    # 同比
    a1 = round(gb1.loc[gb1['month'] == last_year_month_str, 'pue'].values[0], 2)
    a2 = round(gb1.loc[gb1['month'] == M, 'pue'].values[0], 2)
    a3 = round((a2 - a1) / a1 * 100, 2)
    statisticsData = [{"title": "本月功率利用率", "value": a2, "unit": "%"},
                      {"title": "同比增长", "value": a3, "unit": "%"}]
    statisticsData = json.dumps(statisticsData, ensure_ascii=False)
    print('statisticsData：\n', statisticsData)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成axisData
    axisData = json.dumps(list(df3['month']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成条形图单位
    YxisName = '%'
    print('YxisName：\n', YxisName)

    # 生成条形图单位
    legendName = [["平均功率利用率"]]
    print('legendName：\n', legendName)

    DF = pd.DataFrame({
        'chartData': chartData,
        'statisticsData': statisticsData,
        'month': month,
        'axisData': axisData,
        'YxisName': YxisName,
        'legendName': legendName
    })
    DF

    # ### 数据存储

    # In[73]:


    # 定义注释
    table_comment = "产业单位接入情况页_平台功率利用率_站点维度"
    column_comments = {
        'chartData': '统计图数据',
        'statisticsData': '表格下面文字部分',
        'month': '分析月份',
        'axisData': '横坐标数据',
        'YxisName': '单位',
        'legendName': '指标标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Power_Zd",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-时间维度

    # ### 数据计算

    # In[74]:


    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no', 'station_capacity']]

    # 每月充电量
    df2 = Order_Data.groupby(by=['station_no', 'ym'], as_index=False).agg({'trans_energy': 'sum'})
    df2 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    gb1 = df2.groupby(by=['ym', 'station_no'], as_index=False).agg({'trans_energy': 'sum', 'station_capacity': 'max'})
    gb1 = gb1[(gb1['trans_energy'] != 0) & (gb1['ym'] != 0) & (gb1['station_capacity'] != 0)].reset_index(drop=True)

    # 循环获取每行月份对应的总天数
    gb1['pue'] = 0
    for i in range(gb1.shape[0]):
        day = get_days_in_month(gb1.loc[i, 'ym'])
        gb1.loc[i, 'pue'] = round((gb1.loc[i, 'trans_energy'] / (gb1.loc[i, 'station_capacity'] * day * 24)) * 100, 2)
    gb1 = gb1.groupby(by='ym', as_index=False).agg({'pue': 'mean'})
    gb1['pue'] = round(gb1['pue'], 2)
    gb1.columns = ['month', 'pue']

    # 将近12个月份升序排序并获取对应数据
    df3 = Data.sort_values(by='month').reset_index(drop=True)
    df3 = pd.merge(df3, gb1, how='left', on='month').fillna(0)

    # 生成chartData
    chartData = json.dumps([list(df3['pue'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成statisticsData
    # 同比
    a1 = round(gb1.loc[gb1['month'] == last_year_month_str, 'pue'].values[0], 2)
    a2 = round(gb1.loc[gb1['month'] == M, 'pue'].values[0], 2)
    a3 = round((a2 - a1) / a1 * 100, 2)
    statisticsData = [{"title": "本月功率利用率", "value": a2, "unit": "%"},
                      {"title": "同比增长", "value": a3, "unit": "%"}]
    statisticsData = json.dumps(statisticsData, ensure_ascii=False)
    print('statisticsData：\n', statisticsData)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成axisData
    axisData = json.dumps(list(df3['month']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成条形图单位
    YxisName = '%'
    print('YxisName：\n', YxisName)

    # 生成条形图单位
    legendName = [["平均功率利用率"]]
    print('legendName：\n', legendName)

    DF = pd.DataFrame({
        'chartData': chartData,
        'statisticsData': statisticsData,
        'month': month,
        'axisData': axisData,
        'YxisName': YxisName,
        'legendName': legendName
    })
    DF

    # ### 数据存储

    # In[75]:


    # 定义注释
    table_comment = "主业单位接入情况页_平台功率利用率_站点维度"
    column_comments = {
        'chartData': '统计图数据',
        'statisticsData': '表格下面文字部分',
        'month': '分析月份',
        'axisData': '横坐标数据',
        'YxisName': '单位',
        'legendName': '指标标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Power_Zd",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 第四板块-本月充电收入

    # ## 产业单位-区域维度

    # ### 数据计算

    # In[76]:


    Order_Data.head(1)

    # In[77]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['city', 'station_no']]

    # 本月充电收入
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_amount': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)

    gb1 = df3.groupby(by='city', as_index=False).agg({'trans_amount': 'sum'})
    gb1.sort_values(by='trans_amount', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['city', 'amount', 'rank']
    gb1['amount'] = round(gb1['amount'], 2)
    gb1 = gb1[gb1['amount'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "城市", "prop": "city"}, {"name": "本月充电收入（元）", "prop": "amount"}, {"name": "城市排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['city']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['amount'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '元'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['本月充电收入'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['city'].tolist()
    illustrate = f"产业单位本月充电收入区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['amount'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[78]:


    # 定义注释
    table_comment = "产业单位接入情况页_平台充电收入_区域维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Inco_Qy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-区域维度

    # ### 数据计算

    # In[79]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['city', 'station_no']]

    # 本月充电收入
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_amount': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)

    gb1 = df3.groupby(by='city', as_index=False).agg({'trans_amount': 'sum'})
    gb1.sort_values(by='trans_amount', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['city', 'amount', 'rank']
    gb1['amount'] = round(gb1['amount'], 2)
    gb1 = gb1[gb1['amount'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "城市", "prop": "city"}, {"name": "本月充电收入（元）", "prop": "amount"}, {"name": "城市排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['city']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['amount'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '元'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['本月充电收入'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['city'].tolist()
    illustrate = f"主业单位本月充电收入区域维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['amount'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[80]:


    # 定义注释
    table_comment = "主业单位接入情况页_平台充电收入_区域维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Inco_Qy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:


    # In[ ]:


    # In[ ]:


    # In[ ]:


    # ## 产业单位-运营商维度

    # ### 数据计算

    # In[81]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['merchant_name', 'station_no']]

    # 本月充电收入
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_amount': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)

    gb1 = df3.groupby(by='merchant_name', as_index=False).agg({'trans_amount': 'sum'})
    gb1.sort_values(by='trans_amount', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['merchant_name', 'amount', 'rank']
    gb1['amount'] = round(gb1['amount'], 2)
    gb1 = gb1[gb1['amount'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "运营商", "prop": "merchant_name"}, {"name": "本月充电收入（元）", "prop": "amount"}, {"name": "运营商排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['merchant_name']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['amount'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '元'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['本月充电收入'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['merchant_name'].tolist()
    illustrate = f"产业单位本月充电收入运营商维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['amount'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[82]:


    # 定义注释
    table_comment = "产业单位接入情况页_平台本月充电收入_运营商维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Inco_Yy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-运营商维度

    # ### 数据计算

    # In[83]:


    # 站点基础信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['merchant_name', 'station_no']]

    # 本月充电收入
    df2 = Order_Data[Order_Data['ym'] == M].groupby(by='station_no',
                                                    as_index=False).agg({'trans_amount': 'sum'})
    df3 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)

    gb1 = df3.groupby(by='merchant_name', as_index=False).agg({'trans_amount': 'sum'})
    gb1.sort_values(by='trans_amount', ascending=False, inplace=True)
    gb1.reset_index(inplace=True, drop=True)
    gb1['rank'] = gb1.index + 1
    gb1.columns = ['merchant_name', 'amount', 'rank']
    gb1['amount'] = round(gb1['amount'], 2)
    gb1 = gb1[gb1['amount'] > 0]

    # 生成表格内容
    dict_list = gb1.to_dict(orient='records')
    tableData = json.dumps(dict_list, ensure_ascii=False)
    print('tableData：\n', tableData)

    # 生成列名和中文对应关系
    dict_list2 = [{"name": "运营商", "prop": "merchant_name"}, {"name": "本月充电收入（元）", "prop": "amount"}, {"name": "运营商排名", "prop": "rank"}]
    tableColumn = json.dumps(dict_list2, ensure_ascii=False)
    print('tableColumn：\n', tableColumn)

    # 生成右侧条形图的标签
    gb2 = gb1.head(5).sort_values(by='rank', ascending=False)
    axisData = json.dumps(list(gb2['merchant_name']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成右侧条形图的数据
    chartData = json.dumps([list(gb2['amount'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成条形图单位
    YxisName = '元'
    print('YxisName：\n', YxisName)

    # 生成条形图鼠标指上去的标签文本
    legendName = json.dumps(['本月充电收入'], ensure_ascii=False)
    print('legendName：\n', legendName)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成表格下面文字部分
    top3_cities = gb1.head(3)['merchant_name'].tolist()
    illustrate = f"主业单位本月充电收入运营商维度TOP3：{('、').join(top3_cities)}"
    print('illustrate：\n', illustrate)

    # 生成平均值数据
    xAxis = round(gb1['amount'].mean(), 2)
    print('xAxis：\n', xAxis)

    # 生成平均值标签
    markLineName = '平均值'
    print('markLineName：\n', markLineName)

    DF = pd.DataFrame({
        'tableData': tableData,
        'tableColumn': tableColumn,
        'axisData': axisData,
        'chartData': chartData,
        'YxisName': YxisName,
        'legendName': legendName,
        'month': month,
        'illustrate': illustrate,
        'xAxis': xAxis,
        'markLineName': markLineName,
    })
    DF

    # ### 数据存储

    # In[84]:


    # 定义注释
    table_comment = "主业单位接入情况页_平台本月充电收入_运营商维度"
    column_comments = {
        'tableData': '表格数据',
        'tableColumn': '表头',
        'axisData': '条形图标签',
        'chartData': '条形图数据',
        'YxisName': '纵坐标单位',
        'legendName': '线条名称',
        'month': '分析月份',
        'illustrate': '表格下面文字部分',
        'xAxis': '平均值数据',
        'markLineName': '平均值标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Inco_Yy",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:


    # In[ ]:


    # ## 产业单位-时间维度

    # ### 数据计算

    # In[85]:


    # 累计接入充电枪数
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no']]
    # 本月充电收入
    df2 = Order_Data.groupby(by=['station_no', 'ym'], as_index=False).agg({'trans_amount': 'sum'})
    df2 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    gb1 = df2.groupby(by='ym', as_index=False).agg({'trans_amount': 'sum'})
    gb1.columns = ['month', 'trans_amount']
    gb1['trans_amount'] = round(gb1['trans_amount'], 2)

    # 将近12个月份升序排序并获取对应数据
    df3 = Data.sort_values(by='month').reset_index(drop=True)
    df3 = pd.merge(df3, gb1, how='left', on='month').fillna(0)

    # 生成chartData
    chartData = json.dumps([list(df3['trans_amount'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成statisticsData
    # 同比
    a1 = round(gb1.loc[gb1['month'] == last_year_month_str, 'trans_amount'].values[0], 2)
    a2 = round(gb1.loc[gb1['month'] == M, 'trans_amount'].values[0], 2)
    a3 = round((a2 - a1) / a1 * 100, 2)
    statisticsData = [{"title": "本月充电收入", "value": a2, "unit": "元"},
                      {"title": "同比增长", "value": a3, "unit": "%"}]
    statisticsData = json.dumps(statisticsData, ensure_ascii=False)
    print('statisticsData：\n', statisticsData)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成axisData
    axisData = json.dumps(list(df3['month']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成条形图单位
    YxisName = '元'
    print('YxisName：\n', YxisName)

    # 生成条形图单位
    legendName = [["月充电收入"]]
    print('legendName：\n', legendName)

    DF = pd.DataFrame({
        'chartData': chartData,
        'statisticsData': statisticsData,
        'month': month,
        'axisData': axisData,
        'YxisName': YxisName,
        'legendName': legendName
    })
    DF

    # ### 数据存储

    # In[86]:


    # 定义注释
    table_comment = "产业单位接入情况页_平台本月充电收入_站点维度"
    column_comments = {
        'chartData': '统计图数据',
        'statisticsData': '表格下面文字部分',
        'month': '分析月份',
        'axisData': '横坐标数据',
        'YxisName': '单位',
        'legendName': '指标标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_Left_Charge_Inco_Zd",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ## 主业单位-时间维度

    # ### 数据计算

    # In[87]:


    # 累计接入充电枪数
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no']]
    # 本月充电收入
    df2 = Order_Data.groupby(by=['station_no', 'ym'], as_index=False).agg({'trans_amount': 'sum'})
    df2 = pd.merge(df1, df2, how='left', on='station_no').fillna(0)
    gb1 = df2.groupby(by='ym', as_index=False).agg({'trans_amount': 'sum'})
    gb1.columns = ['month', 'trans_amount']
    gb1['trans_amount'] = round(gb1['trans_amount'], 2)

    # 将近12个月份升序排序并获取对应数据
    df3 = Data.sort_values(by='month').reset_index(drop=True)
    df3 = pd.merge(df3, gb1, how='left', on='month').fillna(0)

    # 生成chartData
    chartData = json.dumps([list(df3['trans_amount'])], ensure_ascii=False)
    print('chartData：\n', chartData)

    # 生成statisticsData
    # 同比
    a1 = round(gb1.loc[gb1['month'] == last_year_month_str, 'trans_amount'].values[0], 2)
    a2 = round(gb1.loc[gb1['month'] == M, 'trans_amount'].values[0], 2)
    a3 = round((a2 - a1) / a1 * 100, 2)
    statisticsData = [{"title": "本月充电收入", "value": a2, "unit": "元"},
                      {"title": "同比增长", "value": a3, "unit": "%"}]
    statisticsData = json.dumps(statisticsData, ensure_ascii=False)
    print('statisticsData：\n', statisticsData)

    # 生成当月月份
    month = [M]
    print('month：\n', month)

    # 生成axisData
    axisData = json.dumps(list(df3['month']), ensure_ascii=False)
    print('axisData：\n', axisData)

    # 生成条形图单位
    YxisName = '元'
    print('YxisName：\n', YxisName)

    # 生成条形图单位
    legendName = [["月充电收入"]]
    print('legendName：\n', legendName)

    DF = pd.DataFrame({
        'chartData': chartData,
        'statisticsData': statisticsData,
        'month': month,
        'axisData': axisData,
        'YxisName': YxisName,
        'legendName': legendName
    })
    DF

    # ### 数据存储

    # In[88]:


    # 定义注释
    table_comment = "主业单位接入情况页_平台本月充电收入_站点维度"
    column_comments = {
        'chartData': '统计图数据',
        'statisticsData': '表格下面文字部分',
        'month': '分析月份',
        'axisData': '横坐标数据',
        'YxisName': '单位',
        'legendName': '指标标签'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_main_unit_Left_Charge_Inco_Zd",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # # 页面下方全篇联动

    # ## 4个横幅指标

    # ### siteData-产业-rc1

    # In[89]:


    # 1、获取当前月份及之前投运站点的信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '产业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no', 'station_name', 'station_capacity', 'charge_count', 'merchant_name']]

    # 2、筛选订单表中当年且当前月份之前的数据
    df2 = Order_Data[(Order_Data['year'] == '2025') & (Order_Data['ym'] <= M)]

    # 3、按站点编号统计当年各站点的充电量数据
    gb1 = df2.groupby(by='station_no', as_index=False).agg({'trans_energy': 'sum',
                                                            'trans_amount': 'sum'})
    # 4、匹配产业单位对应站点电量数据
    df3 = pd.merge(df1[df1['station_capacity'] != 0], gb1[gb1['trans_energy'] != 0], how='left', on='station_no').fillna(0)
    df3 = df3[df3['trans_energy'] != 0]

    # 5、特殊处理功率利用率，先算站点数据再求平均
    df3['pue'] = round((df3['trans_energy'] / (df3['station_capacity'] * total_days * 24)) * 100, 2)

    df4 = df3.groupby(by='merchant_name', as_index=False).agg({'trans_energy': 'sum',
                                                               'trans_amount': 'sum',
                                                               'charge_count': 'sum',
                                                               'pue': 'mean'})
    df4['charge_day_energy'] = df4['trans_energy'] / (df4['charge_count'] * total_days)
    df4 = df4[['merchant_name', 'trans_energy', 'trans_amount', 'charge_day_energy', 'pue']]
    df4.columns = ['单位名称', '本年单位累计充电量', '本年单位累计充电收入', '本年单位单枪日均充电量', '本年单位功率利用率']
    df4 = df4.fillna(0)
    df4


    # In[90]:


    def convert_row_to_json(row):
        # 构建字典列表（同之前的结构）
        data_list = [
            {
                "title": "本年单位累计充电量",
                "value": round(row['本年单位累计充电量'] / 10000, 2),
                "unit": "万kWh"
            },
            {
                "title": "本年单位累计充电收入",
                "value": round(row['本年单位累计充电收入'] / 10000, 2),
                "unit": "万元"
            },
            {
                "title": "本年单位单枪日均充电量",
                "value": round(row['本年单位单枪日均充电量'], 2),
                "unit": "kWh"
            },
            {
                "title": "本年单位功率利用率",
                "value": round(row['本年单位功率利用率'], 2),
                "unit": "%"
            }
        ]
        # 将列表转换为JSON字符串（ensure_ascii=False保证中文正常显示）
        return json.dumps(data_list, ensure_ascii=False)


    # 生成结果数据框rc1
    rc1 = pd.DataFrame()
    rc1['单位名称'] = df4['单位名称']
    rc1['siteData'] = df4.apply(convert_row_to_json, axis=1)

    # 显示结果
    rc1

    # In[91]:


    print(rc1.iloc[1, 1])

    # ### siteData-主业-rz1

    # In[92]:


    # 1、获取当前月份及之前投运站点的信息
    df1 = Basic_Data[
        (Basic_Data['归属单位'] == '主业单位') &
        (Basic_Data['commissioning_year_month'] <= M) &
        (Basic_Data['operation_status'].isin(['投运', '退运']))
        ][['station_no', 'station_name', 'station_capacity', 'charge_count', 'merchant_name']]

    # 2、筛选订单表中当年且当前月份之前的数据
    df2 = Order_Data[(Order_Data['year'] == '2025') & (Order_Data['ym'] <= M)]

    # 3、按站点编号统计当年各站点的充电量数据
    gb1 = df2.groupby(by='station_no', as_index=False).agg({'trans_energy': 'sum',
                                                            'trans_amount': 'sum'})
    # 4、匹配主业单位对应站点电量数据
    df3 = pd.merge(df1[df1['station_capacity'] != 0], gb1[gb1['trans_energy'] != 0], how='left', on='station_no').fillna(0)
    df3 = df3[df3['trans_energy'] != 0]

    # 5、特殊处理功率利用率，先算站点数据再求平均
    df3['pue'] = round((df3['trans_energy'] / (df3['station_capacity'] * total_days * 24)) * 100, 2)

    df4 = df3.groupby(by='merchant_name', as_index=False).agg({'trans_energy': 'sum',
                                                               'trans_amount': 'sum',
                                                               'charge_count': 'sum',
                                                               'pue': 'mean'})
    df4['charge_day_energy'] = df4['trans_energy'] / (df4['charge_count'] * total_days)
    df4 = df4[['merchant_name', 'trans_energy', 'trans_amount', 'charge_day_energy', 'pue']]
    df4.columns = ['单位名称', '本年单位累计充电量', '本年单位累计充电收入', '本年单位单枪日均充电量', '本年单位功率利用率']
    df4 = df4.fillna(0)
    df4


    # In[93]:


    def convert_row_to_json(row):
        # 构建字典列表（同之前的结构）
        data_list = [
            {
                "title": "本年单位累计充电量",
                "value": round(row['本年单位累计充电量'] / 10000, 2),
                "unit": "万kWh"
            },
            {
                "title": "本年单位累计充电收入",
                "value": round(row['本年单位累计充电收入'] / 10000, 2),
                "unit": "万元"
            },
            {
                "title": "本年单位单枪日均充电量",
                "value": round(row['本年单位单枪日均充电量'], 2),
                "unit": "kWh"
            },
            {
                "title": "本年单位功率利用率",
                "value": round(row['本年单位功率利用率'], 2),
                "unit": "%"
            }
        ]
        # 将列表转换为JSON字符串（ensure_ascii=False保证中文正常显示）
        return json.dumps(data_list, ensure_ascii=False)


    # 生成结果数据框rz1
    rz1 = pd.DataFrame()
    rz1['单位名称'] = df4['单位名称']
    rz1['siteData'] = df4.apply(convert_row_to_json, axis=1)

    # 显示结果
    rz1

    # In[94]:


    print(rz1.iloc[1, 1])

    # ## 统计数据准备

    # In[95]:


    df1 = Basic_Data[(Basic_Data['operation_status'] == '投运') &
                     (Basic_Data['station_capacity'] > 0) &
                     (Basic_Data['charge_count'] > 0) &
                     (Basic_Data['merchant_name'] != '其他') &
                     (Basic_Data['commissioning_year_month'] <= M)][['station_no',
                                                                     'merchant_name',
                                                                     'station_capacity',
                                                                     'charge_count',
                                                                     '归属单位']].copy()
    print('截至目前的单位统计总数（不包括次月更新站点）：', len(set(df1['merchant_name'])))

    # In[96]:


    df1.head(2)

    # In[97]:


    # 关联站点基础信息表与订单信息表
    df2 = pd.merge(df1, Order_Data, how='left', on='station_no')
    df2.head(1)

    # In[98]:


    Basic_Data.columns

    # In[99]:


    # 先按照站点编号汇总数据,确保每个月的站点功率数据不重复
    gb1 = df2.groupby(by=['station_no', 'ym'], as_index=False).agg({'trans_energy': 'sum',
                                                                    'trans_amount': 'sum',
                                                                    'merchant_name': 'max',
                                                                    '归属单位': 'max'})

    gb1 = pd.merge(gb1, Basic_Data[['station_no', 'station_capacity', 'charge_count']], how='left', on='station_no')
    # 循环获取每行月份对应的总天数
    gb1['pue'] = 0
    for i in range(gb1.shape[0]):
        day = get_days_in_month(gb1.loc[i, 'ym'])
        gb1.loc[i, 'pue'] = round((gb1.loc[i, 'trans_energy'] / (gb1.loc[i, 'station_capacity'] * day * 24)) * 100, 2)

    # In[100]:


    gb2 = gb1.groupby(by=['merchant_name', '归属单位', 'ym'], as_index=False).agg({'trans_energy': 'sum',
                                                                               'trans_amount': 'sum',
                                                                               'charge_count': 'sum',
                                                                               'station_capacity': 'sum',
                                                                               'pue': 'mean',
                                                                               'station_no': 'count'})
    gb2.columns = ['merchant_name', '归属单位', 'ym',
                   'trans_energy', 'trans_amount', 'charge_count',
                   'station_capacity', 'pue', 'station_count']
    # 计算单枪日均充电量
    # 循环获取每行月份对应的总天数
    gb2['charge_day_energy'] = 0
    for i in range(gb2.shape[0]):
        day = get_days_in_month(gb2.loc[i, 'ym'])
        gb2.loc[i, 'charge_day_energy'] = round((gb2.loc[i, 'trans_energy'] / (gb2.loc[i, 'charge_count'] * day)), 2)
    gb2

    # ## 站点月均充电量

    # In[101]:


    df1 = gb2[['merchant_name', '归属单位', 'ym', 'trans_energy']].copy()
    df1['trans_energy'] = round(df1['trans_energy'], 2)
    # 计算平均值
    df2 = gb2.groupby(by='ym', as_index=False).agg({'trans_energy': 'sum', 'merchant_name': 'count'})
    df2['avg_trans_energy'] = round(df2['trans_energy'] / df2['merchant_name'], 2)
    df2 = df2[['ym', 'avg_trans_energy']]
    # 数据合并
    df3 = pd.merge(df1, df2, how='left', on='ym')

    # 计算环比增长率
    df3 = df3.sort_values(['merchant_name', 'ym'])  # 确保数据按商户和月份排序
    df3['mom_growth_rate'] = round(df3.groupby('merchant_name')['trans_energy'].pct_change() * 100, 2)
    df3 = df3.fillna(0)
    df3.head(5)

    # In[102]:


    # 1. 准备排名数据 - 计算M月份各商户的trans_energy排名
    # 筛选M月份的数据
    df_m = df3[df3['ym'] == M]
    # 计算M月份的商户总数
    total_merchants = df_m.drop_duplicates(subset=['merchant_name', '归属单位']).shape[0]
    # 按trans_energy降序排序并生成排名
    df_m = df_m.sort_values('trans_energy', ascending=False)
    df_m['rank'] = range(1, len(df_m) + 1)
    # 创建排名字典：商户名称 -> 排名/总数
    rank_dict = {name: f"{rank}/{total_merchants}"
                 for name, rank in zip(df_m['merchant_name'], df_m['rank'])}
    rank_dict

    # ### chart1-产业-rc2

    # In[103]:


    # 2. 按商户分组处理数据
    df4 = df3[(df3['归属单位'] == '产业单位') & (df3['ym'] != last_year_month_str)]
    groups = df4.groupby('merchant_name')
    r = []

    for merchant, group in groups:
        # 按月份排序
        group = group.sort_values('ym')

        # 提取所需数据列表
        axis_data = group['ym'].tolist()
        trans_energy = group['trans_energy'].tolist()
        avg_energy = group['avg_trans_energy'].tolist()
        growth_rates = group['mom_growth_rate'].tolist()

        # 获取M月份的统计数据
        m_data = group[group['ym'] == M].iloc[0] if M in group['ym'].values else None
        current_trans = m_data['trans_energy'] if m_data is not None else None
        current_avg = m_data['avg_trans_energy'] if m_data is not None else None
        current_rank = rank_dict.get(merchant, f"0/{total_merchants}")

        # 构建统计数据
        statistics = [
            {"title": "本月度此商户月充电量为", "value": f"{current_trans:.2f}" if current_trans else "N/A", "unit": "kWh"},
            {"title": "本月度平台商户平均水平为", "value": f"{current_avg:.2f}" if current_avg else "N/A", "unit": "kWh"},
            {"title": "本月度此商户（含产业、省公司、社会商户与四川电动）排名", "value": current_rank, "unit": " "}
        ]

        # 构建图表数据字典
        chart_data = {
            "legendName": ["月充电量", "平台商户平均水平", "同比增长率"],
            "axisData": axis_data,
            "chartData": [trans_energy, avg_energy, growth_rates],
            "yAxisLeftName": "kWh",
            "statisticsData": statistics
        }

        # 添加到结果列表
        r.append({
            "单位名称": merchant,
            "chart1": json.dumps(chart_data, ensure_ascii=False)
        })

    # 3. 创建最终数据框rc2
    rc2 = pd.DataFrame(r)

    # 显示结果
    rc2

    # In[104]:


    rc2.iloc[-1, 1]

    # ### chart1-主业-rz2

    # In[105]:


    # 2. 按商户分组处理数据
    df4 = df3[(df3['归属单位'] == '主业单位') & (df3['ym'] != last_year_month_str)]
    groups = df4.groupby('merchant_name')
    r = []

    for merchant, group in groups:
        # 按月份排序
        group = group.sort_values('ym')

        # 提取所需数据列表
        axis_data = group['ym'].tolist()
        trans_energy = group['trans_energy'].tolist()
        avg_energy = group['avg_trans_energy'].tolist()
        growth_rates = group['mom_growth_rate'].tolist()

        # 获取M月份的统计数据
        m_data = group[group['ym'] == M].iloc[0] if M in group['ym'].values else None
        current_trans = m_data['trans_energy'] if m_data is not None else None
        current_avg = m_data['avg_trans_energy'] if m_data is not None else None
        current_rank = rank_dict.get(merchant, f"0/{total_merchants}")

        # 构建统计数据
        statistics = [
            {"title": "本月度此商户月充电量为", "value": f"{current_trans:.2f}" if current_trans else "N/A", "unit": "kWh"},
            {"title": "本月度平台商户平均水平为", "value": f"{current_avg:.2f}" if current_avg else "N/A", "unit": "kWh"},
            {"title": "本月度此商户（含产业、省公司、社会商户与四川电动）排名", "value": current_rank, "unit": " "}
        ]

        # 构建图表数据字典
        chart_data = {
            "legendName": ["月充电量", "平台商户平均水平", "同比增长率"],
            "axisData": axis_data,
            "chartData": [trans_energy, avg_energy, growth_rates],
            "yAxisLeftName": "kWh",
            "statisticsData": statistics
        }

        # 添加到结果列表
        r.append({
            "单位名称": merchant,
            "chart1": json.dumps(chart_data, ensure_ascii=False)
        })

    # 3. 创建最终数据框rz2
    rz2 = pd.DataFrame(r)

    # 显示结果
    rz2

    # In[106]:


    rz2.iloc[0, 1]

    # ## 站点月均充电收入

    # In[107]:


    df1 = gb2[['merchant_name', '归属单位', 'ym', 'trans_amount']].copy()
    df1['trans_amount'] = round(df1['trans_amount'], 2)
    # 计算平均值
    df2 = gb2.groupby(by='ym', as_index=False).agg({'trans_amount': 'sum', 'merchant_name': 'count'})
    df2['avg_trans_amount'] = round(df2['trans_amount'] / df2['merchant_name'], 2)
    df2 = df2[['ym', 'avg_trans_amount']]
    # 数据合并
    df3 = pd.merge(df1, df2, how='left', on='ym')

    # 计算环比增长率
    df3 = df3.sort_values(['merchant_name', 'ym'])  # 确保数据按商户和月份排序
    df3['mom_growth_rate'] = round(df3.groupby('merchant_name')['trans_amount'].pct_change() * 100, 2)
    df3 = df3.fillna(0)
    df3.head(5)

    # In[108]:


    # 1. 准备排名数据 - 计算M月份各商户的trans_amount排名
    # 筛选M月份的数据
    df_m = df3[df3['ym'] == M]
    # 计算M月份的商户总数
    total_merchants = df_m.drop_duplicates(subset=['merchant_name', '归属单位']).shape[0]
    # 按trans_amount降序排序并生成排名
    df_m = df_m.sort_values('trans_amount', ascending=False)
    df_m['rank'] = range(1, len(df_m) + 1)
    # 创建排名字典：商户名称 -> 排名/总数
    rank_dict = {name: f"{rank}/{total_merchants}"
                 for name, rank in zip(df_m['merchant_name'], df_m['rank'])}
    rank_dict

    # ### chart4-产业-rc3

    # In[109]:


    # 2. 按商户分组处理数据
    df4 = df3[(df3['归属单位'] == '产业单位') & (df3['ym'] != last_year_month_str)]
    groups = df4.groupby('merchant_name')
    r = []

    for merchant, group in groups:
        # 按月份排序
        group = group.sort_values('ym')

        # 提取所需数据列表
        axis_data = group['ym'].tolist()
        trans_amount = group['trans_amount'].tolist()
        avg_energy = group['avg_trans_amount'].tolist()
        growth_rates = group['mom_growth_rate'].tolist()

        # 获取M月份的统计数据
        m_data = group[group['ym'] == M].iloc[0] if M in group['ym'].values else None
        current_trans = m_data['trans_amount'] if m_data is not None else None
        current_avg = m_data['avg_trans_amount'] if m_data is not None else None
        current_rank = rank_dict.get(merchant, f"0/{total_merchants}")

        # 构建统计数据
        statistics = [
            {"title": "本月度此商户月充电收入为", "value": f"{current_trans:.2f}" if current_trans else "N/A", "unit": "元"},
            {"title": "本月度平台商户平均水平为", "value": f"{current_avg:.2f}" if current_avg else "N/A", "unit": "元"},
            {"title": "本月度此商户（含产业、省公司、社会商户与四川电动）排名", "value": current_rank, "unit": " "}
        ]

        # 构建图表数据字典
        chart_data = {
            "legendName": ["月充电收入", "平台商户平均水平", "同比增长率"],
            "axisData": axis_data,
            "chartData": [trans_amount, avg_energy, growth_rates],
            "yAxisLeftName": "元",
            "statisticsData": statistics
        }

        # 添加到结果列表
        r.append({
            "单位名称": merchant,
            "chart4": json.dumps(chart_data, ensure_ascii=False)
        })

    # 3. 创建最终数据框rc2
    rc3 = pd.DataFrame(r)

    # 显示结果
    rc3

    # In[110]:


    rc3.iloc[0, 1]

    # ### chart4-主业-rz3

    # In[111]:


    # 2. 按商户分组处理数据
    df4 = df3[(df3['归属单位'] == '主业单位') & (df3['ym'] != last_year_month_str)]
    groups = df4.groupby('merchant_name')
    r = []

    for merchant, group in groups:
        # 按月份排序
        group = group.sort_values('ym')

        # 提取所需数据列表
        axis_data = group['ym'].tolist()
        trans_amount = group['trans_amount'].tolist()
        avg_energy = group['avg_trans_amount'].tolist()
        growth_rates = group['mom_growth_rate'].tolist()

        # 获取M月份的统计数据
        m_data = group[group['ym'] == M].iloc[0] if M in group['ym'].values else None
        current_trans = m_data['trans_amount'] if m_data is not None else None
        current_avg = m_data['avg_trans_amount'] if m_data is not None else None
        current_rank = rank_dict.get(merchant, f"0/{total_merchants}")

        # 构建统计数据
        statistics = [
            {"title": "本月度此商户月充电收入为", "value": f"{current_trans:.2f}" if current_trans else "N/A", "unit": "元"},
            {"title": "本月度平台商户平均水平为", "value": f"{current_avg:.2f}" if current_avg else "N/A", "unit": "元"},
            {"title": "本月度此商户（含产业、省公司、社会商户与四川电动）排名", "value": current_rank, "unit": " "}
        ]

        # 构建图表数据字典
        chart_data = {
            "legendName": ["月充电收入", "平台商户平均水平", "同比增长率"],
            "axisData": axis_data,
            "chartData": [trans_amount, avg_energy, growth_rates],
            "yAxisLeftName": "元",
            "statisticsData": statistics
        }

        # 添加到结果列表
        r.append({
            "单位名称": merchant,
            "chart4": json.dumps(chart_data, ensure_ascii=False)
        })

    # 3. 创建最终数据框rc2
    rz3 = pd.DataFrame(r)

    # 显示结果
    rz3

    # In[112]:


    rz3.iloc[0, 1]

    # ## 站点单枪日均充电量

    # In[113]:


    gb2.head(1)

    # In[114]:


    df1 = gb2[['merchant_name', '归属单位', 'ym', 'charge_day_energy']].copy()
    df1['charge_day_energy'] = round(df1['charge_day_energy'], 2)
    # 计算平均值
    df2 = gb2.groupby(by='ym', as_index=False).agg({'charge_day_energy': 'mean'})
    df2['charge_day_energy'] = round(df2['charge_day_energy'], 2)
    df2.columns = ['ym', 'avg_charge_day_energy']
    # 数据合并
    df3 = pd.merge(df1, df2, how='left', on='ym')

    # 计算环比增长率
    df3 = df3.sort_values(['merchant_name', 'ym'])  # 确保数据按商户和月份排序
    df3['mom_growth_rate'] = round(df3.groupby('merchant_name')['charge_day_energy'].pct_change() * 100, 2)
    df3 = df3.fillna(0)
    df3.head(5)

    # In[115]:


    # 1. 准备排名数据 - 计算M月份各商户的charge_day_energy排名
    # 筛选M月份的数据
    df_m = df3[df3['ym'] == M]
    # 计算M月份的商户总数
    total_merchants = df_m.drop_duplicates(subset=['merchant_name', '归属单位']).shape[0]
    # 按charge_day_energy降序排序并生成排名
    df_m = df_m.sort_values('charge_day_energy', ascending=False)
    df_m['rank'] = range(1, len(df_m) + 1)
    # 创建排名字典：商户名称 -> 排名/总数
    rank_dict = {name: f"{rank}/{total_merchants}"
                 for name, rank in zip(df_m['merchant_name'], df_m['rank'])}
    rank_dict

    # ### chart2-产业-rc4

    # In[116]:


    # 2. 按商户分组处理数据
    df4 = df3[(df3['归属单位'] == '产业单位') & (df3['ym'] != last_year_month_str)]
    groups = df4.groupby('merchant_name')
    r = []

    for merchant, group in groups:
        # 按月份排序
        group = group.sort_values('ym')

        # 提取所需数据列表
        axis_data = group['ym'].tolist()
        charge_day_energy = group['charge_day_energy'].tolist()
        avg_energy = group['avg_charge_day_energy'].tolist()
        growth_rates = group['mom_growth_rate'].tolist()

        # 获取M月份的统计数据
        m_data = group[group['ym'] == M].iloc[0] if M in group['ym'].values else None
        current_trans = m_data['charge_day_energy'] if m_data is not None else None
        current_avg = m_data['avg_charge_day_energy'] if m_data is not None else None
        current_rank = rank_dict.get(merchant, f"0/{total_merchants}")

        # 构建统计数据
        statistics = [
            {"title": "本月度此商户单枪日均充电量为", "value": f"{current_trans:.2f}" if current_trans else "N/A", "unit": "kWh"},
            {"title": "本月度平台商户平均水平为", "value": f"{current_avg:.2f}" if current_avg else "N/A", "unit": "kWh"},
            {"title": "本月度此商户（含产业、省公司、社会商户与四川电动）排名", "value": current_rank, "unit": " "}
        ]

        # 构建图表数据字典
        chart_data = {
            "legendName": ["单枪日均充电量", "平台商户平均水平", "同比增长率"],
            "axisData": axis_data,
            "chartData": [charge_day_energy, avg_energy, growth_rates],
            "yAxisLeftName": "kWh",
            "statisticsData": statistics
        }

        # 添加到结果列表
        r.append({
            "单位名称": merchant,
            "chart2": json.dumps(chart_data, ensure_ascii=False)
        })

    # 3. 创建最终数据框rc2
    rc4 = pd.DataFrame(r)

    # 显示结果
    rc4

    # In[117]:


    rc4.iloc[0, 1]

    # ### chart2-主业-rz4

    # In[118]:


    # 2. 按商户分组处理数据
    df4 = df3[(df3['归属单位'] == '主业单位') & (df3['ym'] != last_year_month_str)]
    groups = df4.groupby('merchant_name')
    r = []

    for merchant, group in groups:
        # 按月份排序
        group = group.sort_values('ym')

        # 提取所需数据列表
        axis_data = group['ym'].tolist()
        charge_day_energy = group['charge_day_energy'].tolist()
        avg_energy = group['avg_charge_day_energy'].tolist()
        growth_rates = group['mom_growth_rate'].tolist()

        # 获取M月份的统计数据
        m_data = group[group['ym'] == M].iloc[0] if M in group['ym'].values else None
        current_trans = m_data['charge_day_energy'] if m_data is not None else None
        current_avg = m_data['avg_charge_day_energy'] if m_data is not None else None
        current_rank = rank_dict.get(merchant, f"0/{total_merchants}")

        # 构建统计数据
        statistics = [
            {"title": "本月度此商户单枪日均充电量为", "value": f"{current_trans:.2f}" if current_trans else "N/A", "unit": "kWh"},
            {"title": "本月度平台商户平均水平为", "value": f"{current_avg:.2f}" if current_avg else "N/A", "unit": "kWh"},
            {"title": "本月度此商户（含产业、省公司、社会商户与四川电动）排名", "value": current_rank, "unit": " "}
        ]

        # 构建图表数据字典
        chart_data = {
            "legendName": ["单枪日均充电量", "平台商户平均水平", "同比增长率"],
            "axisData": axis_data,
            "chartData": [charge_day_energy, avg_energy, growth_rates],
            "yAxisLeftName": "kWh",
            "statisticsData": statistics
        }

        # 添加到结果列表
        r.append({
            "单位名称": merchant,
            "chart2": json.dumps(chart_data, ensure_ascii=False)
        })

    # 3. 创建最终数据框rc2
    rz4 = pd.DataFrame(r)

    # 显示结果
    rz4

    # In[119]:


    rz4.iloc[0, 1]

    # ## 站点月均功率利用率

    # In[120]:


    gb2.head(1)

    # In[121]:


    df1 = gb2[['merchant_name', '归属单位', 'ym', 'pue']].copy()
    df1['pue'] = round(df1['pue'], 2)
    # 计算平均值
    df2 = gb2.groupby(by='ym', as_index=False).agg({'pue': 'mean'})
    df2['pue'] = round(df2['pue'], 2)
    df2.columns = ['ym', 'avg_pue']
    # 数据合并
    df3 = pd.merge(df1, df2, how='left', on='ym')

    # 计算环比增长率
    df3 = df3.sort_values(['merchant_name', 'ym'])  # 确保数据按商户和月份排序
    df3['mom_growth_rate'] = round(df3.groupby('merchant_name')['pue'].pct_change() * 100, 2)
    df3 = df3.fillna(0)
    df3.head(5)

    # In[122]:


    # 1. 准备排名数据 - 计算M月份各商户的pue排名
    # 筛选M月份的数据
    df_m = df3[df3['ym'] == M]
    # 计算M月份的商户总数
    total_merchants = df_m.drop_duplicates(subset=['merchant_name', '归属单位']).shape[0]
    # 按pue降序排序并生成排名
    df_m = df_m.sort_values('pue', ascending=False)
    df_m['rank'] = range(1, len(df_m) + 1)
    # 创建排名字典：商户名称 -> 排名/总数
    rank_dict = {name: f"{rank}/{total_merchants}"
                 for name, rank in zip(df_m['merchant_name'], df_m['rank'])}
    rank_dict

    # ### chart3-产业-rc5

    # In[123]:


    # 2. 按商户分组处理数据
    df4 = df3[(df3['归属单位'] == '产业单位') & (df3['ym'] != last_year_month_str)]
    groups = df4.groupby('merchant_name')
    r = []

    for merchant, group in groups:
        # 按月份排序
        group = group.sort_values('ym')

        # 提取所需数据列表
        axis_data = group['ym'].tolist()
        pue = group['pue'].tolist()
        avg_energy = group['avg_pue'].tolist()
        growth_rates = group['mom_growth_rate'].tolist()

        # 获取M月份的统计数据
        m_data = group[group['ym'] == M].iloc[0] if M in group['ym'].values else None
        current_trans = m_data['pue'] if m_data is not None else None
        current_avg = m_data['avg_pue'] if m_data is not None else None
        current_rank = rank_dict.get(merchant, f"0/{total_merchants}")

        # 构建统计数据
        statistics = [
            {"title": "本月度此商户功率利用率为", "value": f"{current_trans:.2f}" if current_trans else "N/A", "unit": "%"},
            {"title": "本月度平台商户平均水平为", "value": f"{current_avg:.2f}" if current_avg else "N/A", "unit": "%"},
            {"title": "本月度此商户（含产业、省公司、社会商户与四川电动）排名", "value": current_rank, "unit": " "}
        ]

        # 构建图表数据字典
        chart_data = {
            "legendName": ["功率利用率", "平台商户平均水平", "同比增长率"],
            "axisData": axis_data,
            "chartData": [pue, avg_energy, growth_rates],
            "yAxisLeftName": "%",
            "statisticsData": statistics
        }

        # 添加到结果列表
        r.append({
            "单位名称": merchant,
            "chart3": json.dumps(chart_data, ensure_ascii=False)
        })

    # 3. 创建最终数据框rc2
    rc5 = pd.DataFrame(r)

    # 显示结果
    rc5

    # In[124]:


    rc5.iloc[4, 1]

    # ### chart3-主业-rz5

    # In[125]:


    # 2. 按商户分组处理数据
    df4 = df3[(df3['归属单位'] == '主业单位') & (df3['ym'] != last_year_month_str)]
    groups = df4.groupby('merchant_name')
    r = []

    for merchant, group in groups:
        # 按月份排序
        group = group.sort_values('ym')

        # 提取所需数据列表
        axis_data = group['ym'].tolist()
        pue = group['pue'].tolist()
        avg_energy = group['avg_pue'].tolist()
        growth_rates = group['mom_growth_rate'].tolist()

        # 获取M月份的统计数据
        m_data = group[group['ym'] == M].iloc[0] if M in group['ym'].values else None
        current_trans = m_data['pue'] if m_data is not None else None
        current_avg = m_data['avg_pue'] if m_data is not None else None
        current_rank = rank_dict.get(merchant, f"0/{total_merchants}")

        # 构建统计数据
        statistics = [
            {"title": "本月度此商户功率利用率为", "value": f"{current_trans:.2f}" if current_trans else "N/A", "unit": "%"},
            {"title": "本月度平台商户平均水平为", "value": f"{current_avg:.2f}" if current_avg else "N/A", "unit": "%"},
            {"title": "本月度此商户（含产业、省公司、社会商户与四川电动）排名", "value": current_rank, "unit": " "}
        ]

        # 构建图表数据字典
        chart_data = {
            "legendName": ["功率利用率", "平台商户平均水平", "同比增长率"],
            "axisData": axis_data,
            "chartData": [pue, avg_energy, growth_rates],
            "yAxisLeftName": "%",
            "statisticsData": statistics
        }

        # 添加到结果列表
        r.append({
            "单位名称": merchant,
            "chart3": json.dumps(chart_data, ensure_ascii=False)
        })

    # 3. 创建最终数据框rc2
    rz5 = pd.DataFrame(r)

    # 显示结果
    rz5

    # In[126]:


    rz5.iloc[0, 1]

    # ## 地图经纬度数据

    # In[127]:


    Basic_Data.columns

    # In[128]:


    df1 = Basic_Data[(Basic_Data['operation_status'] == '投运') &
                     (Basic_Data['station_capacity'] > 0) &
                     (Basic_Data['charge_count'] > 0) &
                     (Basic_Data['merchant_name'] != '其他') &
                     (Basic_Data['commissioning_year_month'] <= M)][['station_no',
                                                                     'merchant_name',
                                                                     'city',
                                                                     '归属单位']].copy()
    print('截至目前的单位统计总数（不包括次月更新站点）：', len(set(df1['merchant_name'])))

    # In[129]:


    df2 = pd.merge(df1, low_lat_Data, how='left', on='station_no')
    df2.dropna(inplace=True)
    print(df2.info())
    df2.head(1)

    # ### mapData-产业-rc6

    # In[130]:


    df3 = df2[df2['归属单位'] == '产业单位'][['merchant_name', 'city', 'lon', 'Lat']].reset_index(drop=True)


    # 定义转换函数，将每组数据转换为指定格式的列表
    def convert_group(group):
        # 构建格式列表
        data_list = [
            {"name": row['city'], "value": [row['lon'], row['Lat']]}
            for _, row in group.iterrows()
        ]
        # 转换为JSON字符串，确保中文正常显示
        return json.dumps(data_list, ensure_ascii=False)


    # 按merchant_name分组，并应用转换函数
    grouped = df3.groupby('merchant_name').apply(convert_group).reset_index()

    # 重命名列名得到最终数据框df4
    rc6 = grouped.rename(columns={
        'merchant_name': '单位名称',
        0: 'mapData'  # 存储JSON格式数据的列
    })

    # 显示结果
    rc6

    # In[131]:


    rc6.iloc[0, 1]

    # ### mapData-主业-rz6

    # In[132]:


    df3 = df2[df2['归属单位'] == '主业单位'][['merchant_name', 'city', 'lon', 'Lat']].reset_index(drop=True)


    # 定义转换函数，将每组数据转换为指定格式的列表
    def convert_group(group):
        # 构建格式列表
        data_list = [
            {"name": row['city'], "value": [row['lon'], row['Lat']]}
            for _, row in group.iterrows()
        ]
        # 转换为JSON字符串，确保中文正常显示
        return json.dumps(data_list, ensure_ascii=False)


    # 按merchant_name分组，并应用转换函数
    grouped = df3.groupby('merchant_name').apply(convert_group).reset_index()

    # 重命名列名得到最终数据框df4
    rz6 = grouped.rename(columns={
        'merchant_name': '单位名称',
        0: 'mapData'  # 存储JSON格式数据的列
    })

    # 显示结果
    rz6

    # In[133]:


    rz6.iloc[0, 1]

    # ## 筛选框下信息

    # ### 数据准备

    # In[134]:


    gb2.columns

    # In[135]:


    df1 = gb2[['merchant_name', '归属单位',
               'ym', 'trans_amount', 'station_count',
               'station_capacity', 'charge_day_energy', 'charge_count']].copy()
    df2 = df1[df1['ym'] == M].reset_index(drop=True)
    df2['charge_amount'] = df2['trans_amount'] / df2['charge_count']
    df2['charge_amount'] = round(df2['charge_amount'], 2)
    df2

    # In[136]:


    # 1. 按merchant_name分组聚合，计算所需指标
    grouped = df2.groupby(['merchant_name', '归属单位']).agg({
        'charge_day_energy': 'sum',  # 用于chargeRank排名
        'charge_amount': 'sum',  # 用于incomeRank排名
        'station_count': 'sum',  # siteCount
        'station_capacity': 'sum',  # totalPower
        'charge_count': 'sum'  # chargerCount
    }).rename(columns={
        'merchant_name': 'total_count',
        'station_count': 'siteCount',
        'station_capacity': 'totalPower',
        'charge_count': 'chargerCount'
    }).reset_index()
    # 单独计算单位数量，因为德阳明源电力集团有限公司智网服务分公司特殊情况，既有产业单位，又有社会站
    grouped['total_count'] = df2.drop_duplicates(subset=['merchant_name', '归属单位']).shape[0]

    # 2. 计算排名（降序，最大的值排名为1）
    grouped['chargeRank'] = grouped['charge_day_energy'].rank(ascending=False, method='min').astype(int)
    grouped['incomeRank'] = grouped['charge_amount'].rank(ascending=False, method='min').astype(int)


    # 3. 定义转换函数，生成目标格式并转为JSON
    def format_to_json(row):
        result = {
            "data": {
                "chargeRank": row['chargeRank'],
                "incomeRank": row['incomeRank'],
                "totalChargeStations": row['total_count'],
                "totalEconomyStations": row['total_count'],
                "chargerCount": row['chargerCount'],
                "totalPower": row['totalPower'],
                "siteCount": row['siteCount'],
                "unitName": row['merchant_name']
            },
            "titles": {
                "chargeRanking": "站点单枪日均充电量排名",
                "incomeRanking": "站点单枪充电收入排名"
            },
            "labels": {
                "chargerCount": "充电枪(终端)数量",
                "totalPower": "总额定功率",
                "siteCount": "站点数量",
                "unitName": "单位名称"
            },
            "units": {
                "chargeRank": "名",
                "chargeRankTotal": "个",
                "incomeRank": "名",
                "incomeRankTotal": "个",
                "station": "个",
                "piece": "个",
                "kw": "kW"
            }
        }
        return json.dumps(result, ensure_ascii=False)


    # 4. 生成最终数据框df3
    grouped['basicData'] = grouped.apply(format_to_json, axis=1)
    df3 = grouped[['merchant_name', '归属单位', 'basicData']].copy()
    df3.columns = ['单位名称', '归属单位', 'basicData']
    # 显示结果
    df3

    # ### basicData-产业-rc7

    # In[137]:


    rc7 = df3[df3['归属单位'] == '产业单位'].reset_index(drop=True)[['单位名称', 'basicData']]
    rc7

    # ### basicData-主业-rz7

    # In[138]:


    rz7 = df3[df3['归属单位'] == '主业单位'].reset_index(drop=True)[['单位名称', 'basicData']]
    rz7

    # ## 联动数据合并存储

    # ### 产业单位存储

    # In[139]:


    DF = pd.merge(rc1, rc2, how='left', on='单位名称')
    DF = pd.merge(DF, rc3, how='left', on='单位名称')
    DF = pd.merge(DF, rc4, how='left', on='单位名称')
    DF = pd.merge(DF, rc5, how='left', on='单位名称')
    DF = pd.merge(DF, rc6, how='left', on='单位名称')
    DF = pd.merge(DF, rc7, how='left', on='单位名称')
    DF.rename(columns={'单位名称': 'name'}, inplace=True)
    DF['month'] = M
    DF

    # In[140]:


    # 定义注释
    table_comment = "产业单位_重点单位相关数据（联动）"
    column_comments = {
        'name': '站点名字',
        'siteData': '地图下方4组数据',
        'chart1': '站点每月充电量',
        'chart2': '站点单枪日均充电量',
        'chart3': '站点每月功率利用率',
        'chart4': '站点每月充电收入',
        'basicData': '搜索下面的基本数据',
        'month': '统计年份',
        'mapData': '地图数据'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_industrial_unit_interconnected",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # ### 主业单位存储

    # In[141]:


    DF = pd.merge(rz1, rz2, how='left', on='单位名称')
    DF = pd.merge(DF, rz3, how='left', on='单位名称')
    DF = pd.merge(DF, rz4, how='left', on='单位名称')
    DF = pd.merge(DF, rz5, how='left', on='单位名称')
    DF = pd.merge(DF, rz6, how='left', on='单位名称')
    DF = pd.merge(DF, rz7, how='left', on='单位名称')
    DF.rename(columns={'单位名称': 'name'}, inplace=True)
    DF['month'] = M
    DF

    # In[142]:


    # 定义注释
    table_comment = "主业单位_重点单位相关数据（联动）"
    column_comments = {
        'name': '站点名字',
        'siteData': '地图下方4组数据',
        'chart1': '站点每月充电量',
        'chart2': '站点单枪日均充电量',
        'chart3': '站点每月功率利用率',
        'chart4': '站点每月充电收入',
        'basicData': '搜索下面的基本数据',
        'month': '统计年份',
        'mapData': '地图数据'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_unit_interconnected",
        table_comment=table_comment,
        column_comments=column_comments
    )

    # In[ ]:


    # In[ ]:





