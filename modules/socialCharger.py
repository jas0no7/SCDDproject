from logs.log_decorator import log_execution
from loguru import logger
from modules.config import SQL,import_data_with_cursor,Statistical_Time

@log_execution
def runsocialCharger():
    logger.info(f"开始执行社会桩页面")
    import pandas as pd
    import numpy as np
    import json
    from pandas.tseries.offsets import MonthBegin
    import calendar
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)

    # In[2]:


    pd.set_option('display.max_colwidth', None)  # 设置为None表示不限制长度



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


    # In[8]:


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


    # ## 站点维度计算

    # In[9]:


    def Site_Dimension_1(sql, time_column, M_DF, cal_str, col_1, s1, s2, M, last_year_month_str):
        """
        ==此函数为累计接入统计函数==
        sql:数据库取数代码
        time_column：时间对应列名
        M_DF：要展示的12个年月
        cal_str：要统计的字段名称
        col_1:结果数据的列名
        s1：文本参数
        s2:文本参数单位
        M:当前年月
        last_year_month_str：同比年月
        """
        # 获取数据源
        d1 = sql
        #     d1[cal_str] = d1[cal_str].fillna(0)
        #     print(len(d1))
        # 时间数据转换，确保YM列可以用作与M_DF（横轴）连接
        d1[time_column] = pd.to_datetime(d1[time_column])  # 确保是 datetime 类型
        d1['YM'] = d1[time_column].dt.strftime('%Y%m')
        gb1 = d1.groupby(by='YM', as_index=False).agg({cal_str: 'sum'})
        gb1.columns = ['YM', 'sum']
        # 对每个month值计算累计sum
        d2 = M_DF.copy()
        d2['累计值'] = M_DF['month'].apply(lambda i: gb1[gb1['YM'] <= i]['sum'].sum())
        d2.columns = ['时间', col_1]
        # 同比计算
        x1 = d2.loc[d2['时间'].astype(str) == M, col_1].values[0]  # 当前月累计值
        x2 = gb1.loc[gb1['YM'] <= last_year_month_str, 'sum'].sum()  # 去年同期累计值
        x3 = ((x1 - x2) / x2) * 100  # 增长率（百分比）
        S1 = x1
        S2 = round(float(x3), 2)  # 增长率（保留2位小数）
        return d2, S1, S2, x1


    # In[10]:


    def Site_Dimension_2(sql, time_column, M_DF, cal_str, col_1, s1, s2, M, last_year_month_str):
        """
        ==此函数为当月数据统计函数==
        sql:数据库取数代码
        time_column：时间对应列名
        M_DF：要展示的12个年月
        cal_str：要统计的字段名称
        col_1:结果数据的列名
        s1：文本参数
        s2:文本参数单位
        M:当前年月
        last_year_month_str：同比年月
        """
        # 获取数据源
        d1 = sql
        #     d1[cal_str] = d1[cal_str].fillna(0)
        gb1 = d1.groupby(by=time_column, as_index=False).agg({cal_str: 'sum'})
        gb1.columns = ['时间', 'sum']
        d2 = pd.merge(M_DF, gb1, how='left', left_on='month', right_on='时间')
        d2 = d2[['month', 'sum']]
        d2.columns = ['时间', col_1]
        d2[col_1] = [float(i) for i in d2[col_1]]
        x1 = d2.loc[d2['时间'].astype(str) == M, col_1].values[0]
        x2 = gb1.loc[gb1['时间'] == last_year_month_str, 'sum'].values[0]
        x1 = round(float(x1), 2)
        x2 = round(float(x2), 2)
        x3 = ((x1 - x2) / x2) * 100
        S1 = round(float(x1), 2)
        S2 = round(float(x3), 2)
        return d2, S1, S2, x1


    # In[11]:


    def Site_Dimension_3(df, time_column, M_DF, cal_str, col_1, s1, s2, M, last_year_month_str):
        """
        ==此函数为当月数据统计函数==
        sql:数据库取数代码
        time_column：时间对应列名
        M_DF：要展示的12个年月
        cal_str：要统计的字段名称
        col_1:结果数据的列名
        s1：文本参数
        s2:文本参数单位
        M:当前年月
        last_year_month_str：同比年月
        """
        # 获取数据源
        d1 = df
        #     d1[cal_str] = d1[cal_str].fillna(0)
        gb1 = d1.groupby(by=time_column, as_index=False).agg({cal_str: 'mean'})
        gb1.columns = ['时间', 'mean']
        d2 = pd.merge(M_DF, gb1, how='left', left_on='month', right_on='时间')
        d2['mean'] = d2['mean'].round(2)
        d2 = d2[['month', 'mean']]
        d2.columns = ['时间', col_1]
        d2[col_1] = [float(i) for i in d2[col_1]]
        x1 = d2.loc[d2['时间'].astype(str) == M, col_1].values[0]
        x2 = gb1.loc[gb1['时间'] == last_year_month_str, 'mean'].values[0]
        x1 = round(float(x1), 2)
        x2 = round(float(x2), 2)
        x3 = ((x1 - x2) / x2) * 100
        S1 = round(float(x1), 2)
        S2 = round(float(x3), 2)
        return d2, S1, S2, x1


    # ## 区域维度计算

    # In[12]:


    def City_Dimension_1(sql, cal_str, s1, s2, col_1):
        """
        ==此函数为累计接入统计函数==
        sql:数据库取数代码
        cal_str：要统计的字段名称
        s1:文本参数1
        s2:文本参数2
        """
        # 获取数据源
        d1 = sql
        # 按需要分类的字段进行分组统计：城市/运营商
        gb1 = d1.groupby(by='city', as_index=False).agg({cal_str: 'sum'})
        gb1.columns = ['city', 'sum']
        # 排序
        gb1.sort_values(by='sum', ascending=False, inplace=True, ignore_index=True)
        gb1['排名'] = [i for i in range(1, (gb1.shape[0]) + 1)]
        gb1.columns = ['城市', col_1, '城市排名']
        m = round(gb1[col_1].mean(), 2)
        gb2 = pd.concat([pd.DataFrame(data=[['平均值', m]], columns=['城市', col_1]), gb1.iloc[:5, :2]])
        gb2.sort_values(by=col_1, ascending=False, inplace=True, ignore_index=True)
        S1 = f'平台{s1}接入{s2}区域维度TOP3：{gb1.iloc[0, 0]}、{gb1.iloc[1, 0]}、{gb1.iloc[2, 0]}'
        # 反转gb2的顺序
        gb2 = gb2.iloc[::-1].reset_index(drop=True)
        return gb1, gb2, S1


    # In[13]:


    def City_Dimension_2(sql, time_column, M, cal_str, s1, s2, col_1):
        """
        ==此函数为当月数据统计函数==
        sql:数据库取数代码
        M：统计当月的时间点
        time_column：时间对应列名
        cal_str：要统计的字段名称
        """
        d1 = sql
        #     d1[cal_str] = d1[cal_str].fillna(0)
        d2 = d1.loc[d1[time_column].astype(str) == str(M), :]
        gb1 = d2.groupby(by='city', as_index=False).agg({cal_str: 'sum'})
        gb1.columns = ['city', 'sum']
        # 排序
        gb1.sort_values(by='sum', ascending=False, inplace=True, ignore_index=True)
        gb1['排名 '] = [i for i in range(1, (gb1.shape[0]) + 1)]
        gb1.columns = ['城市', col_1, '城市排名']
        gb1[col_1] = gb1[col_1].astype('float')
        m = round(gb1[col_1].mean(), 2)
        gb2 = pd.concat([pd.DataFrame(data=[['平均值', m]], columns=['城市', col_1]), gb1.iloc[:5, :2]])
        gb2.sort_values(by=col_1, ascending=False, inplace=True, ignore_index=True)
        gb2[col_1] = gb2[col_1].astype('float')
        S1 = f'平台{s1}本月{s2}区域维度TOP3：{gb1.iloc[0, 0]}、{gb1.iloc[1, 0]}、{gb1.iloc[2, 0]}'
        # 反转gb2的顺序
        gb2 = gb2.iloc[::-1].reset_index(drop=True)
        return gb1, gb2, S1


    # In[14]:


    def City_Dimension_3(df, time_column, M, cal_str, s1, s2, col_1):
        """
        ==此函数为当月数据统计函数==
        sql:数据库取数代码
        M：统计当月的时间点
        time_column：时间对应列名
        cal_str：要统计的字段名称
        """
        d1 = df
        #     d1[cal_str] = d1[cal_str].fillna(0)
        d2 = d1.loc[d1[time_column].astype(str) == str(M), :]
        gb1 = d2.groupby(by='city', as_index=False).agg({cal_str: 'mean'})
        gb1.columns = ['city', 'mean']
        gb1['mean'] = gb1['mean'].round(2)
        # 排序
        gb1.sort_values(by='mean', ascending=False, inplace=True, ignore_index=True)
        gb1['排名 '] = [i for i in range(1, (gb1.shape[0]) + 1)]
        gb1.columns = ['城市', col_1, '城市排名']
        gb1[col_1] = gb1[col_1].astype('float')
        m = round(gb1[col_1].mean(), 2)
        gb2 = pd.concat([pd.DataFrame(data=[['平均值', m]], columns=['城市', col_1]), gb1.iloc[:5, :2]])
        gb2.sort_values(by=col_1, ascending=False, inplace=True, ignore_index=True)
        gb2[col_1] = gb2[col_1].astype('float')
        S1 = f'平台{s1}本月{s2}区域维度TOP3：{gb1.iloc[0, 0]}、{gb1.iloc[1, 0]}、{gb1.iloc[2, 0]}'
        # 反转gb2的顺序
        gb2 = gb2.iloc[::-1].reset_index(drop=True)
        return gb1, gb2, S1


    # ## 运营商维度

    # In[15]:


    def Operator_Dimension_1(sql, cal_str, s1, s2, col_1):
        """
        ==此函数为累计接入统计函数==
        sql:数据库取数代码
        cal_str：要统计的字段名称
        s1:文本参数1
        s2:文本参数2
        """
        # 获取数据源
        d1 = sql
        #     d1[cal_str] = d1[cal_str].fillna(0)
        # 按需要分类的字段进行分组统计：城市/运营商
        gb1 = d1.groupby(by='merchant_name', as_index=False).agg({cal_str: 'sum'})
        # 合并特殊产业单位
        #     for i in range(0,gb1.shape[0]):
        #         if gb1.iloc[i,0] in ['四川巴中和兴电力有限责任公司平昌分公司',
        #                              '四川巴中和兴电力有限责任公司南江分公司',
        #                              '巴中和兴电力有限责任公司']:
        #             gb1.iloc[i,0] = '四川巴中和兴电力有限责任公司'
        #         if gb1.iloc[i,0] in ['四川南充恒通电力有限公司供电服务分公司',
        #                              '四川南充恒通电力有限公司南部县分公司']:
        #             gb1.iloc[i,0] = '四川南充恒通电力有限公司'
        # 重新按最新产业单位分组统计
        gb2 = gb1.groupby(by='merchant_name', as_index=False).agg({cal_str: 'sum'})
        gb2.columns = ['merchant_name', 'sum']
        # 排序
        gb2.sort_values(by='sum', ascending=False, inplace=True, ignore_index=True)
        gb2['排名 '] = [i for i in range(1, (gb2.shape[0]) + 1)]
        gb2.columns = ['运营商', col_1, '运营商排名']
        m = round(gb2[col_1].mean(), 2)
        gb3 = pd.concat([pd.DataFrame(data=[['平均值', m]], columns=['运营商', col_1]), gb2.iloc[:5, :2]])
        gb3.sort_values(by=col_1, ascending=False, inplace=True, ignore_index=True)
        S1 = f'平台{s1}接入{s2}运营商维度TOP3：{gb2.iloc[0, 0]}、{gb2.iloc[1, 0]}、{gb2.iloc[2, 0]}'
        # 反转gb3的顺序
        gb3 = gb3.iloc[::-1].reset_index(drop=True)
        return gb2, gb3, S1


    # In[16]:


    def Operator_Dimension_2(sql, time_column, M, cal_str, s1, s2, col_1):
        """
        ==此函数为当月接入统计函数==
        sql:数据库取数代码
        cal_str：要统计的字段名称
        """
        # 获取数据源
        d1 = sql
        d1[cal_str] = d1[cal_str].fillna(0)
        d1 = d1.loc[d1[time_column].astype(str) == str(M), :]
        # 按需要分类的字段进行分组统计：城市/运营商
        gb1 = d1.groupby(by='merchant_name', as_index=False).agg({cal_str: 'sum'})
        # 合并特殊产业单位
        #     for i in range(0,gb1.shape[0]):
        #         if gb1.iloc[i,0] in ['四川巴中和兴电力有限责任公司平昌分公司',
        #                              '四川巴中和兴电力有限责任公司南江分公司',
        #                              '巴中和兴电力有限责任公司']:
        #             gb1.iloc[i,0] = '四川巴中和兴电力有限责任公司'
        #         if gb1.iloc[i,0] in ['四川南充恒通电力有限公司供电服务分公司',
        #                              '四川南充恒通电力有限公司南部县分公司']:
        #             gb1.iloc[i,0] = '四川南充恒通电力有限公司'
        # 重新按最新产业单位分组统计
        gb2 = gb1.groupby(by='merchant_name', as_index=False).agg({cal_str: 'sum'})
        gb2.columns = ['merchant_name', 'sum']
        # 排序
        gb2.sort_values(by='sum', ascending=False, inplace=True, ignore_index=True)
        gb2['排名 '] = [i for i in range(1, (gb2.shape[0]) + 1)]
        gb2.columns = ['运营商', col_1, '运营商排名']
        gb2[col_1] = gb2[col_1].astype('float')
        m = round(gb2[col_1].mean(), 2)
        gb3 = pd.concat([pd.DataFrame(data=[['平均值', m]], columns=['运营商', col_1]), gb2.iloc[:5, :2]])
        gb3.sort_values(by=col_1, ascending=False, inplace=True, ignore_index=True)
        gb3[col_1] = gb3[col_1].astype('float')
        S1 = f'平台{s1}本月{s2}运营商维度TOP3：{gb2.iloc[0, 0]}、{gb2.iloc[1, 0]}、{gb2.iloc[2, 0]}'
        # 反转gb3的顺序
        gb3 = gb3.iloc[::-1].reset_index(drop=True)
        return gb2, gb3, S1


    # In[17]:


    def Operator_Dimension_3(df, time_column, M, cal_str, s1, s2, col_1):
        """
        ==此函数为当月接入统计函数==
        sql:数据库取数代码
        cal_str：要统计的字段名称
        """
        # 获取数据源
        d1 = df
        d1[cal_str] = d1[cal_str].fillna(0)
        d1 = d1.loc[d1[time_column].astype(str) == str(M), :]
        # 按需要分类的字段进行分组统计：城市/运营商
        gb1 = d1.groupby(by='merchant_name', as_index=False).agg({cal_str: 'mean'})
        # 合并特殊产业单位
        #     for i in range(0,gb1.shape[0]):
        #         if gb1.iloc[i,0] in ['四川巴中和兴电力有限责任公司平昌分公司',
        #                              '四川巴中和兴电力有限责任公司南江分公司',
        #                              '巴中和兴电力有限责任公司']:
        #             gb1.iloc[i,0] = '四川巴中和兴电力有限责任公司'
        #         if gb1.iloc[i,0] in ['四川南充恒通电力有限公司供电服务分公司',
        #                              '四川南充恒通电力有限公司南部县分公司']:
        #             gb1.iloc[i,0] = '四川南充恒通电力有限公司'
        # 重新按最新产业单位分组统计
        gb2 = gb1.groupby(by='merchant_name', as_index=False).agg({cal_str: 'mean'})
        gb2.columns = ['merchant_name', 'mean']
        gb2['mean'] = gb2['mean'].round(2)
        # 排序
        gb2.sort_values(by='mean', ascending=False, inplace=True, ignore_index=True)
        gb2['排名 '] = [i for i in range(1, (gb2.shape[0]) + 1)]
        gb2.columns = ['运营商', col_1, '运营商排名']
        gb2[col_1] = gb2[col_1].astype('float')
        m = round(gb2[col_1].mean(), 2)
        gb3 = pd.concat([pd.DataFrame(data=[['平均值', m]], columns=['运营商', col_1]), gb2.iloc[:5, :2]])
        gb3.sort_values(by=col_1, ascending=False, inplace=True, ignore_index=True)
        gb3[col_1] = gb3[col_1].astype('float')
        S1 = f'平台{s1}本月{s2}运营商维度TOP3：{gb2.iloc[0, 0]}、{gb2.iloc[1, 0]}、{gb2.iloc[2, 0]}'
        # 反转gb3的顺序
        gb3 = gb3.iloc[::-1].reset_index(drop=True)
        return gb2, gb3, S1


    # ## 柱状图

    # In[18]:


    def bar_chart(df, axis, YxisName, m):
        axisData = df[axis].tolist()
        chartData = [df[col].tolist() for col in [i for i in df.columns if axis not in i]]
        YxisName = YxisName
        legendName = [i for i in df.columns if axis not in i]
        L = [axisData, chartData, YxisName, legendName]
        #     print(L)
        DF = pd.DataFrame(columns=['axisData', 'chartData', 'YxisName', 'legendName'], data=[L])
        DF['month'] = m
        DF = DF.fillna(0)
        return DF


    # In[19]:


    def bar_chart_1(df, axis, YxisName, m):
        axisData = df[axis].tolist()
        chartData = [df[col].tolist() for col in [i for i in df.columns if axis not in i]]
        YxisName = YxisName
        legendName = [i for i in df.columns if axis not in i]
        L = [axisData, chartData, YxisName, legendName]
        #     print(L)
        DF = pd.DataFrame(columns=['axisData', 'chartData', 'YxisName', 'legendName'], data=[L])
        DF['month'] = m
        DF = DF.fillna(0)
        return DF


    # ## 对应文字描述1

    # In[20]:


    def word(V, DF1):
        DF2_1 = pd.DataFrame(columns=['title', 'value', 'unit'], data=V)
        DF2_1.to_json(orient='records', force_ascii=False)
        DF2 = pd.DataFrame(columns=['statisticsData'], data=[DF2_1.to_json(orient='records', force_ascii=False)])
        DF = pd.concat([DF1, DF2], axis=1)
        return DF


    # ## 转平均值

    # In[21]:


    def AVG_(R3, C1, C2):
        v = round(R3[R3[C1] == '平均值'][C2].values[0], 2)
        R3 = R3[R3[C1] != '平均值']
        R3['平均值'] = v
        return R3


    # ## sql分区筛选

    # In[22]:


    def get_months_in_year(month_str):
        """获取指定月份及其当年之前的所有月份，返回元组格式"""
        year = int(month_str[:4])
        month = int(month_str[4:])

        # 生成从1月到指定月份的所有月份，并转换为元组
        months = tuple(int(f"{year}{m:02d}") for m in range(1, month + 1))

        placeholders = ", ".join([f"p{p}" for p in months])

        return placeholders


    # 获取统计年月以及倒推的11个年月的数据框
    M_DF = generate_months(M, 11)
    M_DF['month']

    # In[26]:


    M_DF


    # In[27]:


    def extend_12months_backward_with_days(df, month_col='month'):
        """
        扩展数据表：从最早月份往前补足12个月，并计算每个月份的天数

        参数:
            df: pd.DataFrame 原始数据（必须包含month_col列）
            month_col: str 月份列名（YYYYMM格式）

        返回:
            pd.DataFrame 包含原始数据和前12个月的新数据表，并增加 `days_in_month` 列
        """
        # 标准化月份格式（处理数字/字符串混合情况）
        df = df.copy()
        df[month_col] = df[month_col].astype(str)

        # 找到最早月份（按数值排序确保正确）
        earliest_month = df[month_col].sort_values().iloc[0]
        year, month = int(earliest_month[:4]), int(earliest_month[4:6])

        # 生成需要补充的月份序列（往前12个月）
        months_to_add = []
        for _ in range(12):
            # 月份递减
            month -= 1
            if month == 0:
                month = 12
                year -= 1
            months_to_add.append(f"{year}{month:02d}")

        # 创建补充数据的DataFrame（反转顺序使时间正序）
        supplement_df = pd.DataFrame({
            month_col: months_to_add[::-1]  # 反转得到从远到近的顺序
        })

        # 合并原始数据（保留所有原始列）
        result = pd.concat([supplement_df, df], ignore_index=True)

        # 去重（确保原始数据不会被补充数据覆盖）
        result = result.drop_duplicates(subset=[month_col], keep='last')

        # 计算每个月份的天数
        result['days'] = result[month_col].apply(
            lambda x: calendar.monthrange(int(x[:4]), int(x[4:6]))[1]
        )

        # 按月份排序
        return result.sort_values(month_col).reset_index(drop=True)


    # In[28]:


    M_DF_1 = extend_12months_backward_with_days(M_DF, month_col='month')

    # In[29]:


    M_DF_1

    # In[30]:


    begin = []
    end = []
    for i in range(len(M_DF_1)):
        begin.append(str(M_DF_1.iloc[i]['month'])[:4] + '-' + str(M_DF_1.iloc[i]['month'])[4:] + '-' + '01' + ' ' + '00:00:00')
        end.append(str(M_DF_1.iloc[i]['month'])[:4] + '-' + str(M_DF_1.iloc[i]['month'])[4:] + '-' + str(str(M_DF_1.iloc[i]['days'])) + ' ' + '23:59:59')

    # In[31]:


    result_data = M_DF_1.iloc[-13:]

    # In[32]:


    begin1 = []
    end1 = []
    for i in range(len(result_data)):
        begin1.append(str(result_data.iloc[i]['month'])[:4] + '-' + str(result_data.iloc[i]['month'])[4:] + '-' + '01' + ' ' + '00:00:00')
        end1.append(str(result_data.iloc[i]['month'])[:4] + '-' + str(result_data.iloc[i]['month'])[4:] + '-' + str(str(result_data.iloc[i]['days'])) + ' ' + '23:59:59')

    # In[33]:


    begin1, end1

    # ## 平台累计接入充电枪数板块

    # In[34]:


    # 数据库取数代码
    sql1 = f"""
    SELECT
        rm.merchant_name,
        rm.plat_access_mode,
        cs.*,
        IFNULL(cs.dc_charge_point_count, 0) + IFNULL(cs.ac_charge_point_count, 0) AS charge_point_gun_count
    FROM
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        -- 筛选条件：三种情况
        (
            -- 情况1：plat_access_mode在指定的第三方/社会商户类别中
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR
            -- 情况2：plat_access_mode为NULL（未设置接入模式）
            rm.plat_access_mode IS NULL
            OR
            -- 情况3：特定接入模式且access_method为'社会站模型'
            (
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 其他基础筛选条件
        AND cs.operation_status IN ('投运')
        AND cs.commissioning_time < '{P_M}'
    """
    # 时间对应列名
    time_column1 = 'commissioning_time'
    # 要统计的字段名称
    cal_str1 = 'charge_point_gun_count'
    df = SQL(sql1)

    # In[35]:


    DATA = []

    # ### 站点维度

    # In[36]:


    # 函数调用
    R1, S1, S2, x1 = Site_Dimension_1(df, time_column1, M_DF, cal_str1, '平台累计接入充电枪数', '充电枪', '个', M, last_year_month_str)
    print('S1:', S1)
    print('S2:', S2)

    # 平台累计接入充电枪数

    # In[37]:


    DATA.append(S1)  # 单位：个
    DATA

    # In[38]:


    R1 = R1.sort_values(by='时间', ascending=True)

    # In[39]:


    # R1.loc[R1['时间']=='202505','平台累计接入充电枪数'] = 1090


    # In[40]:


    R1

    # In[41]:


    DF1 = bar_chart(R1, "时间", '个', M)

    # In[42]:


    V = [['当前累计接入充电枪', S1, '个'], ['累计同比增长', S2, '%']]
    DF = word(V, DF1)

    # In[43]:


    DF

    # 传入数据库

    # In[44]:


    # 定义注释
    table_comment = "社会桩_社会桩全局数据_平台累计接入充电枪数（站点维度）"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_gun_station",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 区域维度

    # In[45]:


    # 函数调用
    R2, R3, S3 = City_Dimension_1(df, cal_str1, '社会桩', '站点数量', '累计接入充电枪数量（个）')
    print('R2：\n', R2)
    print('R3：\n', R3)
    print('S3：\n', S3)

    # In[46]:


    R2

    # In[47]:


    R2 = R2.rename(columns={'城市': 'city', '累计接入充电枪数量（个）': 'gun_acc', '城市排名': 'rank'})
    tableData = R2.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['城市', 'city'], ['累计接入充电枪数量（个）', 'gun_acc'], ['城市排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1

    # In[48]:


    # R3 = AVG_(R3,'城市','累计接入充电枪数量（个）')


    # In[49]:


    avg = R3[R3['城市'] == '平均值']['累计接入充电枪数量（个）'].values[0]
    R3 = R3[R3['城市'] != '平均值']

    # In[50]:


    DF2 = bar_chart(R3, "城市", '个', M)

    # In[51]:


    DF = pd.concat([DF1, DF2], axis=1)

    # In[52]:


    DF['illustrate'] = S3
    DF

    # In[53]:


    DF['xAxis'] = avg
    DF['markLineName'] = '平均值'

    # In[54]:


    DF

    # 传入数据库

    # In[55]:


    table_comment = "社会桩_社会桩全局数据_平台累计接入充电枪数（区域维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_gun_city",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 运营商维度

    # In[56]:


    # 函数调用
    R4, R5, S4 = Operator_Dimension_1(df, cal_str1, '社会桩', '站点数量', '累计接入充电枪数量（个）')
    print('R4：\n', R4)
    print('R5：\n', R5)
    print('S4：\n', S4)

    # In[57]:


    R4

    # In[58]:


    R4 = R4.rename(columns={'运营商': 'operator', '累计接入充电枪数量（个）': 'gun_acc', '运营商排名': 'rank'})
    tableData = R4.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['运营商', 'operator'], ['累计接入充电枪数量（个）', 'gun_acc'], ['运营商排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1

    # In[59]:


    avg = R5[R5['运营商'] == '平均值']['累计接入充电枪数量（个）'].values[0]
    R5 = R5[R5['运营商'] != '平均值']

    # In[60]:


    # R5 = AVG_(R5,'运营商','累计接入充电枪数量（个）')
    DF2 = bar_chart(R5, "运营商", '个', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF['illustrate'] = S4
    DF

    # In[61]:


    DF['xAxis'] = avg
    DF['markLineName'] = '平均值'

    # 传进数据库

    # In[62]:


    table_comment = "社会桩_社会桩全局数据_平台累计接入充电枪数（运营商维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_gun_operator",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ## 平台功率利用率

    # In[63]:


    # 首先提取充电站基本信息（这部分不随时间变化，只需提取一次）
    sql_station = f"""
    SELECT
        rm.merchant_name,
        rm.plat_access_mode,
        cs.*
    FROM
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        -- 筛选条件
        (
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR rm.plat_access_mode IS NULL
            OR (
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 其他基础条件
        AND cs.operation_status IN ('投运','退运')
        AND cs.commissioning_time < '{P_M}'
    """

    # 获取充电站数据
    DF_station = SQL(sql_station)

    # In[64]:


    # 初始化空列表存储结果
    df = []

    # 循环处理不同时间范围
    for i in range(len(begin1)):
        # 提取订单数据（按时间范围）
        sql_orders = f"""
        select 
            charging_station_no,
            DATE_FORMAT(order_create_time, '%Y%m') AS ym,
            sum(trans_energy) as trans_energy,
            sum(trans_amount) as trans_amount 
        from fin_plat_data_order 
        where order_create_time BETWEEN '{begin1[i]}' AND '{end1[i]}'
        GROUP BY charging_station_no, DATE_FORMAT(order_create_time, '%Y%m')
        """

        # 获取订单数据
        DF_orders = SQL(sql_orders)
        print(f"{begin1[i]} 到 {end1[i]}")

        # 在内存中进行左连接
        df1 = DF_station.merge(
            DF_orders,
            left_on='station_no',
            right_on='charging_station_no',
            how='left'
        )

        # 添加到结果列表
        df.append(df1)
        print(f"合并后得到 {len(df1)} 条记录")

    # 合并所有时间段的结果
    df = pd.concat(df)
    print(f"合并所有时间段后总记录数: {len(df)}")

    # 过滤掉ym为空的记录
    df = df[~df['ym'].isna()]
    print(f"过滤掉ym为空后记录数: {len(df)}")

    # 合并M_DF_1数据
    df = pd.merge(df, M_DF_1, left_on='ym', right_on='month', how='left')
    print(f"最终记录数: {len(df)}")

    # In[65]:


    df['trans_energy'] = df['trans_energy'].astype(float)
    df['station_capacity'] = df['station_capacity'].astype(float)
    df['days'] = df['days'].astype(float)

    df['pue'] = 0.0

    df['pue'] = np.where(df['station_capacity'] == 0, 0, 100 * df['trans_energy'] / df['station_capacity'] / df['days'] / 24)
    # 时间对应列名
    time_column2 = 'ym'

    # 要展示的12个年月-已生成，无需重复修改

    # 要统计的字段名称
    cal_str2 = 'pue'
    df['pue'] = df['pue'].astype('float')

    # In[66]:


    print(df.info())

    # ### 站点维度

    # In[67]:


    R6, S5, S6, x2 = Site_Dimension_3(df, time_column2, M_DF, cal_str2, '平台功率利用率', '功率利用率', '%', M, last_year_month_str)
    print('R6:', R6)
    print('S5:', S5)
    print('S6:', S6)
    print(x2)

    # In[68]:


    R6 = R6.sort_values(by='时间', ascending=True)

    # In[69]:


    x2 = round(R6[R6['时间'].str.contains(str(year))]['平台功率利用率'].mean(), 2)

    # In[70]:


    DATA.append(x2)  # 单位：把
    DATA

    # In[71]:


    DF1 = bar_chart(R6, "时间", '%', M)
    V = [['当前平台功率利用率', S5, '%'], ['累计同比增长', S6, '%']]
    DF = word(V, DF1)
    DF

    # In[72]:


    # 定义注释
    table_comment = "社会桩_社会桩全局数据_平台功率利用率（站点维度）"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_pue",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 区域维度

    # In[73]:


    R7, R8, S7 = City_Dimension_3(df, time_column2, M, cal_str2, '社会桩', '站均功率利用率', '站均功率利用率（%）')
    print('R7：\n', R7)
    print('R8：\n', R8)
    print('S7：\n', S7)

    # In[74]:


    R7 = R7.rename(columns={'城市': 'city', '站均功率利用率（%）': 'pue', '城市排名': 'rank'})
    tableData = R7.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['城市', 'city'], ['站均功率利用率（%）', 'pue'], ['城市排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1
    avg = R8[R8['城市'] == '平均值']['站均功率利用率（%）'].values[0]
    R8 = R8[R8['城市'] != '平均值']
    # R8 = AVG_(R8,'城市','累计接入额定功率（kW）')
    DF2 = bar_chart(R8, "城市", '%', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF['illustrate'] = S7
    DF

    # In[75]:


    DF['xAxis'] = avg
    DF['markLineName'] = '平均值'

    # In[76]:


    # 定义注释
    table_comment = "社会桩_社会桩全局数据_平台功率利用率（区域维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_pue_city",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 运营商维度

    # In[77]:


    # 函数调用
    R9, R10, S8 = Operator_Dimension_3(df, time_column2, M, cal_str2, '社会桩', '站均功率利用率', '站均功率利用率（%）')
    print('R9：\n', R9)
    print('R10：\n', R10)
    print('S8：\n', S8)

    # In[78]:


    R9 = R9.rename(columns={'运营商': 'operator', '站均功率利用率（%）': 'pue', '运营商排名': 'rank'})
    tableData = R9.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['运营商', 'operator'], ['站均功率利用率（%）', 'pue'], ['运营商排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1

    # In[79]:


    avg = R10[R10['运营商'] == '平均值']['站均功率利用率（%）'].values[0]
    R10 = R10[R10['运营商'] != '平均值']

    # In[80]:


    # R10 = AVG_(R10,'运营商','累计接入额定功率（kW）')
    DF2 = bar_chart(R10, "运营商", '%', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF['illustrate'] = S8
    DF

    # In[81]:


    DF['xAxis'] = avg
    DF['markLineName'] = '平均值'

    # In[82]:


    table_comment = "社会桩_社会桩全局数据_平台功率利用率（运营商维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_pue_operator",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ## 平台本月充电量板块

    # In[83]:


    # 时间对应列名
    time_column3 = 'ym'

    # 要统计的字段名称
    cal_str3 = 'trans_energy'

    # ### 站点维度

    # In[84]:


    # 函数调用
    R10, S9, S10, x3 = Site_Dimension_2(df, time_column3, M_DF, cal_str3, '平台月充电量', '充电量', 'kWh', M, last_year_month_str)
    R10['平台月充电量'] = R10['平台月充电量'].round(2)
    print('S9:', S9)
    print('S10:', S10)
    print('R10:\n', R10)
    print(x3)

    # In[85]:


    R10 = R10.sort_values(by='时间', ascending=True)

    # In[86]:


    x3 = round(R10[R10['时间'].str.contains(str(year))]['平台月充电量'].sum(), 2)

    # In[87]:


    DATA.append(x3)  # 单位：把
    DATA

    # In[88]:


    DF1 = bar_chart(R10, "时间", 'kWh', M)
    V = [['平台本月充电量', S9, 'kWh'], ['累计同比增长', S10, '%']]
    DF = word(V, DF1)
    DF

    # In[89]:


    DF

    # In[90]:


    # 定义注释
    table_comment = "社会桩_社会桩全局数据_平台本月充电量（站点维度）"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_energy_station",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 区域维度

    # In[91]:


    # 函数调用
    R11, R12, S11 = City_Dimension_2(df, time_column3, M, cal_str3, '社会桩', '充电量', '本月充电量（kWh）')
    print('R11:\n', R11)
    print('R12:\n', R12)
    print('S11:\n', S11)

    # In[92]:


    R11 = R11.rename(columns={'城市': 'city', '本月充电量（kWh）': 'energy', '城市排名': 'rank'})
    tableData = R11.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['城市', 'city'], [' 本月充电量（kWh）', 'energy'], ['城市排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1
    avg = R12[R12['城市'] == '平均值']['本月充电量（kWh）'].values[0]
    R12 = R12[R12['城市'] != '平均值']
    # R12 = AVG_(R12,'城市','本月充电量（kWh）')
    DF2 = bar_chart(R12, "城市", 'kWh', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF['illustrate'] = S11
    DF

    # In[93]:


    DF['xAxis'] = avg
    DF['markLineName'] = '平均值'

    # In[94]:


    # 定义注释
    table_comment = "社会桩_社会桩全局数据_平台本月充电量（区域维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_energy_city",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 运营商维度

    # In[95]:


    # 函数调用
    R13, R14, S12 = Operator_Dimension_2(df, time_column3, M, cal_str3, '社会桩', '充电量', '本月充电量（kWh）')
    print('R13:\n', R13)
    print('R14:\n', R14)
    print('S12:\n', S12)

    # In[96]:


    R13 = R13.rename(columns={'运营商': 'operator', '本月充电量（kWh）': 'energy', '运营商排名': 'rank'})
    tableData = R13.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['运营商', 'operator'], ['本月充电量（kWh）', 'energy'], ['运营商排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1

    # In[97]:


    avg = R14[R14['运营商'] == '平均值']['本月充电量（kWh）'].values[0]
    R14 = R14[R14['运营商'] != '平均值']

    # In[98]:


    # R14 = AVG_(R14,'运营商','本月充电量（kWh）')
    DF2 = bar_chart(R14, "运营商", 'kWh', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF['illustrate'] = S12
    DF

    # In[99]:


    DF['xAxis'] = avg
    DF['markLineName'] = '平均值'

    # In[100]:


    table_comment = "社会桩_社会桩全局数据_平台本月充电量（运营商维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_energy_operator",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ## 平台本月经济收入

    # In[101]:


    # 时间对应列名
    time_column4 = 'ym'

    # 要统计的字段名称
    cal_str4 = 'trans_amount'

    # ### 站点维度

    # In[102]:


    # 函数调用
    R15, S13, S14, x4 = Site_Dimension_2(df, time_column4, M_DF, cal_str4, '平台本月经济收入', '经济收入', '元', M, last_year_month_str)
    print('S13:', S13)
    print('S14:', S14)
    print('R15:\n', R15)

    # In[103]:


    R15 = R15.sort_values(by='时间', ascending=True)

    # In[104]:


    # DATA.append(x4)  #单位：把
    # DATA


    # In[105]:


    DF1 = bar_chart(R15, "时间", '元', M)
    V = [['平台本月经济收入', S13, '元'], ['累计同比增长', S14, '%']]
    DF = word(V, DF1)
    DF

    # In[106]:


    # 定义注释
    table_comment = "社会桩_社会桩全局数据_平台经济收入（站点维度）"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_amount_station",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 区域维度

    # In[107]:


    # 函数调用
    R16, R17, S15 = City_Dimension_2(df, time_column4, M, cal_str4, '社会桩', '经济收入', '本月经济收入（元）')
    print('R16:\n', R16)
    print('R17:\n', R17)
    print('S15:\n', S15)

    # In[108]:


    R16 = R16.rename(columns={'城市': 'city', '本月经济收入（元）': 'amount', '城市排名': 'rank'})
    tableData = R16.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['城市', 'city'], ['本月经济收入（元）', 'amount'], ['城市排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1
    # R17 = AVG_(R17,'城市','本月经济收入（元）')
    DF2 = bar_chart(R17, "城市", '元', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF['illustrate'] = S15
    DF

    # In[109]:


    # 定义注释
    table_comment = "社会桩_社会桩全局数据_平台本月经济收入（区域维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_amount_city",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 运营商维度

    # In[110]:


    # 函数调用
    R18, R19, S16 = Operator_Dimension_2(df, time_column4, M, cal_str4, '社会桩', '经济收入', '本月经济收入（元）')
    print('R18:\n', R18)
    print('R19:\n', R19)
    print('S16:\n', S16)

    # In[111]:


    R18 = R18.rename(columns={'运营商': 'operator', '本月经济收入（元）': 'amount', '运营商排名': 'rank'})
    tableData = R18.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['运营商', 'operator'], ['本月经济收入（元）', 'amount'], ['运营商排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1

    # In[112]:


    # R19 = AVG_(R19,'运营商','本月经济收入（元）')
    DF2 = bar_chart(R19, "运营商", '元', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF['illustrate'] = S16
    DF

    # In[113]:


    table_comment = "社会桩_社会桩全局数据_平台本月经济收入（运营商维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_amount_operator",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ## 本月公司分成收入

    # In[114]:


    # 首先提取充电站基本信息（这部分不随时间变化，只需提取一次）
    sql_station = f"""
    SELECT
        rm.merchant_name,
        rm.plat_access_mode,
        cs.*
    FROM
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        -- 筛选条件（三种情况）
        (
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR rm.plat_access_mode IS NULL
            OR (
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 必要的基础条件
        AND cs.operation_status IN ('投运')
        AND cs.commissioning_time < '{P_M}'
    """

    # 获取充电站数据
    DF_station = SQL(sql_station)
    print(f"获取到 {len(DF_station)} 条充电站记录")

    # In[115]:


    # 初始化空列表存储结果
    df = []

    # 循环处理每个月的数据
    for i in list(result_data['month']):
        # 提取收益数据（按月）
        sql_profit = f"""
        select 
            station_no,
            rec_month AS ym,
            sum(dd_profit_amount) AS dd_profit_amount
        from fin_rec_result_detail 
        where rec_month = {i}  
        GROUP BY station_no, rec_month
        """

        # 获取收益数据
        DF_profit = SQL(sql_profit)

        # 在内存中进行左连接
        df1 = DF_station.merge(
            DF_profit,
            left_on='station_no',
            right_on='station_no',
            how='left'
        )

        # 确保ym列存在（对于没有匹配收益记录的站点，ym会是NaN）
        df1['ym'] = df1.get('ym', i)  # 如果没有ym列，使用当前月份

        # 添加到结果列表
        df.append(df1)
        print(f"月份 {i}: 合并后得到 {len(df1)} 条记录")

    # 合并所有月份的结果
    df = pd.concat(df)
    print(f"合并所有月份后总记录数: {len(df)}")

    # 时间对应列名
    time_column5 = 'ym'

    # 要统计的字段名称
    cal_str5 = 'dd_profit_amount'

    # ### 站点维度

    # In[116]:


    # 函数调用
    R20, S17, S18, x5 = Site_Dimension_2(df, time_column5, M_DF, cal_str5, '公司分成收入', '分成收入', '元', M, last_year_month_str)
    print('R20:\n', R20)
    print('S17\n:', S17)
    print('S18\n:', S18)
    print(x5)

    # In[117]:


    R20 = R20.sort_values(by='时间', ascending=True)

    # In[118]:


    x5 = round(R20[R20['时间'].str.contains(str(year))]['公司分成收入'].sum(), 2)

    # In[119]:


    DATA.append(x5)

    # In[120]:


    DATA

    # In[121]:


    DF1 = bar_chart(R20, "时间", '元', M)
    V = [['平台本月公司分成收入', S17, '元'], ['累计同比增长', S18, '%']]
    DF = word(V, DF1)
    DF

    # In[122]:


    # 定义注释
    table_comment = "社会桩_社会桩全局数据_平台分成收入（站点维度）"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_profitAmount_station",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 区域维度

    # In[123]:


    # 函数调用
    R21, R22, S19 = City_Dimension_2(df, time_column5, M, cal_str5, '社会桩', '公司分成收入', '本月公司分成收入（元）')
    print('R21:\n', R21)
    print('R22:\n', R22)
    print('S19:\n', S19)

    # In[124]:


    R21 = R21.rename(columns={'城市': 'city', '本月公司分成收入（元）': 'amount', '城市排名': 'rank'})
    tableData = R21.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['城市', 'city'], ['本月公司分成收入（元）', 'amount'], ['城市排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1
    # R17 = AVG_(R17,'城市','本月经济收入（元）')
    avg = R22[R22['城市'] == '平均值']['本月公司分成收入（元）'].values[0]
    R22 = R22[R22['城市'] != '平均值']
    DF2 = bar_chart(R22, "城市", '元', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF['illustrate'] = S19
    DF

    # In[125]:


    DF['xAxis'] = avg
    DF['markLineName'] = '平均值'

    # In[126]:


    # 定义注释
    table_comment = "社会桩_社会桩全局数据_平台公司分成收入（区域维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_profitAmount_city",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ### 运营商维度

    # In[127]:


    # 函数调用
    R23, R24, S20 = Operator_Dimension_2(df, time_column5, M, cal_str5, '社会桩', '公司分成收入', '本月公司分成收入（元）')
    print('R23:\n', R23)
    print('R24:\n', R24)
    print('S20:\n', S20)

    # In[128]:


    R23 = R23.rename(columns={'运营商': 'operator', '本月公司分成收入（元）': 'amount', '运营商排名': 'rank'})
    tableData = R23.to_json(orient='records', force_ascii=False)
    tableColumn = pd.DataFrame(columns=['name', 'prop'], data=[['运营商', 'operator'], ['本月公司分成收入（元）', 'amount'], ['运营商排名', 'rank']]).to_json(orient='records', force_ascii=False)
    DF1 = pd.DataFrame(columns=['tableData', 'tableColumn'], data=[[tableData, tableColumn]])
    DF1

    # In[129]:


    avg = R24[R24['运营商'] == '平均值']['本月公司分成收入（元）'].values[0]
    R24 = R24[R24['运营商'] != '平均值']

    # In[130]:


    # R19 = AVG_(R19,'运营商','本月经济收入（元）')
    DF2 = bar_chart(R24, "运营商", '元', M)
    DF = pd.concat([DF1, DF2], axis=1)
    DF['illustrate'] = S20
    DF

    # In[131]:


    DF['xAxis'] = avg
    DF['markLineName'] = '平均值'

    # In[132]:


    table_comment = "社会桩_社会桩全局数据_平台公司分成收入（运营商维度）"
    column_comments = {
        'tableData': '左表-数据', 'tableColumn': '左表-表头',
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'illustrate': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_GlobalData_profitAmount_operator",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )


    # 提交
    # conn.commit()


    # # 右边

    # In[133]:


    def calculate_monthly_growth(df, date_col, value_col):
        """
        为DataFrame添加月度同比增长率列(YoY)，直接处理YYYYMM格式日期

        参数:
            df: pd.DataFrame
            value_col: str, 需要计算同比的数值列名
            date_col: str, 包含YYYYMM格式日期的列名（如202402）

        返回:
            pd.DataFrame 新增'_YoY'列的原DataFrame
        """
        df = df.copy()
        dates = df[date_col].astype(str)

        yoy = []
        for current_ym in dates:
            current_year = int(current_ym[:4])
            current_month = int(current_ym[4:6])

            # 计算去年同期年月
            last_year_ym = f"{current_year - 1}{current_month:02d}"

            if last_year_ym in dates.values:
                current_val = df.loc[dates == current_ym, value_col].values[0]
                last_year_val = df.loc[dates == last_year_ym, value_col].values[0]
                growth = (current_val / last_year_val) - 1
                yoy.append(growth)
            else:
                yoy.append(np.nan)

        df["YoY"] = yoy
        return df


    # In[134]:


    def add_rank_column(df, sort_column, rank_col_name='rank', ascending=False):
        """
        根据指定列排序并添加排名列

        参数:
            df: 输入的DataFrame
            sort_column: 要排序的列名
            rank_col_name: 新增排名列的名称(默认'rank')
            ascending: 是否升序排序(默认False，即降序)

        返回:
            排序并添加了排名列的新DataFrame
        """
        # 创建副本以避免修改原DataFrame
        result_df = df.copy()

        # 按指定列排序
        result_df = result_df.sort_values(by=sort_column, ascending=ascending)

        # 添加排名列
        result_df[rank_col_name] = result_df[sort_column].rank(method='min', ascending=False).astype(int)

        # 重置索引(可选)
        result_df = result_df.reset_index(drop=True)

        return result_df


    # In[135]:


    def imp_station(df, c1, c2, t1, t2, M_DF, no, R, M):
        d1 = pd.merge(M_DF, df.groupby(c1).agg({c2: 'mean'}).reset_index(), left_on='month', right_on=c1, how='left')[['month', c2]]
        d1 = d1.rename(columns={c2: t1})
        d2 = pd.merge(M_DF_1, df[df['station_no'] == no][[c1, c2]], left_on='month', right_on=c1, how='left')[['month', c2]]
        d2 = d2.fillna(0)
        d2 = d2.rename(columns={c2: t2})
        d2 = calculate_monthly_growth(d2, 'month', t2)
        d2.rename(columns={'YoY': '同比增长率'}, inplace=True)
        d2['同比增长率'] = d2['同比增长率'].apply(lambda x: round(x * 100, 2) if not pd.isna(x) else np.nan) #转化为百分比数据
        d2['同比增长率'] = d2['同比增长率'].fillna(0) #空值处理

        # 新增：替换无穷大为0
        d2['同比增长率'] = d2['同比增长率'].replace([np.inf, -np.inf], 0)

        d3 = pd.merge(d1, d2, on='month', how='left')
        d4 = df[df['ym'] == M][['station_no', c2]]
        d4 = add_rank_column(d4, c2)
        try:
            r = d4[d4['station_no'] == no]['rank'].values[0]
        except IndexError:
            # print("警告：数组为空，无法访问索引 0！")
            value = None  # 或其他默认值
            r = R

        x = round(d3[d3['month'] == M][t2].values[0], 2)
        T1 = round(d3[d3['month'] == M][t1].values[0], 2)
        T2 = str(r) + '/' + str(R)
        d3 = d3.fillna(0)
        return d3, T1, T2, x


    # In[136]:


    sql = f"""
    SELECT
        rm.merchant_name,
        rm.plat_access_mode,
        cs.*
    FROM
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        -- 核心筛选条件（三种情况）
        (
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR rm.plat_access_mode IS NULL  -- 接入模式为空的情况
            OR (
                -- 特定接入模式且access_method为社会站模型
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 必要的基础筛选条件
        AND cs.operation_status IN ('投运')
        AND cs.commissioning_time < '{P_M}'
    """
    df_station = SQL(sql)
    R = len(df_station)

    # In[137]:


    R

    # In[138]:


    df_NO = df_station = df_station[['station_no', 'station_name']]
    df_NO

    # In[139]:


    df_NO[df_NO['station_name'].isna()]

    # In[140]:


    DATA1 = []

    # ## 站点每月充电量

    # In[141]:


    # 首先提取充电站基本信息（这部分不随时间变化，只需提取一次）
    sql_station = f"""
    SELECT
        rm.merchant_name,
        rm.plat_access_mode,
        cs.*
    FROM
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        -- 筛选条件
        (
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR rm.plat_access_mode IS NULL
            OR (
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 基础筛选条件
        AND cs.operation_status IN ('投运','退运')
        AND cs.commissioning_time < '{P_M}'
    """

    # 获取充电站数据
    DF_station = SQL(sql_station)
    print(f"获取到 {len(DF_station)} 条充电站记录")

    # 初始化空列表存储结果
    DF_trans_energy = []

    # 循环处理不同时间范围
    for i in range(len(begin)):
        # 提取订单数据（按时间范围）
        sql_orders = f"""
        select 
            charging_station_no,
            DATE_FORMAT(order_create_time, '%Y%m') AS ym,
            sum(trans_energy) AS trans_energy,
            sum(trans_amount) AS trans_amount
        from fin_plat_data_order  
        where order_create_time BETWEEN '{begin[i]}' AND '{end[i]}'
        GROUP BY charging_station_no, DATE_FORMAT(order_create_time, '%Y%m')
        """

        # 获取订单数据
        DF_orders = SQL(sql_orders)

        # 在内存中进行内连接（inner join）
        df = DF_station.merge(
            DF_orders,
            left_on='station_no',
            right_on='charging_station_no',
            how='inner'  # 使用内连接，与原SQL一致
        )

        # 添加到结果列表
        DF_trans_energy.append(df)
        print(f"时间范围 {begin[i]} 到 {end[i]}: 合并后得到 {len(df)} 条记录")

    # 合并所有时间段的结果
    DF_trans_energy = pd.concat(DF_trans_energy)
    print(f"合并所有时间段后总记录数: {len(DF_trans_energy)}")

    # In[142]:


    DF_trans_energy['trans_energy'] = DF_trans_energy['trans_energy'].astype('float')

    # In[143]:


    DF_trans_energy[DF_trans_energy['trans_energy'] != 0]['station_no'].drop_duplicates()

    # In[144]:


    len(DF_trans_energy)

    # In[145]:


    DF = pd.DataFrame(columns=['axisData', 'chartData', 'YxisName', 'legendName', 'month', 'statisticsData', 'station_name', 'station_no'])

    # In[146]:


    df_NO

    # In[147]:


    data1 = []
    for i in range(len(df_NO)):
        no = df_NO.iloc[i]['station_no']
        station_name = df_NO.iloc[i]['station_name']
        # print(no, station_name)
        d3, T1, T2, x5 = imp_station(DF_trans_energy, 'ym', 'trans_energy', '社会桩接入站点平均水平', '月充电量', M_DF, no, R, M)
        data1.append(d3[d3['month'].str.contains(str(year))]['月充电量'].sum())  # 单位：把
        d3.fillna(0, inplace=True)
        d3 = d3.sort_values(by='month', ascending=True)
        DF1 = bar_chart(d3, 'month', 'kWh', M)
        V = [["本月度站点累计充电量为", str(x5), 'kWh'], ["社会桩接入站点平均水平为", str(T1), 'kWh'], ["本月度站点排名", T2, '']]
        DF2 = word(V, DF1)
        DF2['station_name'] = station_name
        DF2['station_no'] = no
        DF = pd.concat([DF, DF2])
        # print(no, station_name, '已运行完成')

    # In[148]:


    dp_social_import_energy = DF

    # In[149]:


    dp_social_import_energy

    # In[150]:


    # 定义注释
    table_comment = "社会桩_重点社会桩运营情况_站点每月充电量"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分',
        'station_name': '站点名称', 'station_no': '站点编号'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_import_energy",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ## 站点每月公司抽成

    # In[151]:


    # 首先提取充电站基本信息（这部分不随时间变化，只需提取一次）
    sql_station = f"""
    SELECT
        rm.merchant_name,
        rm.plat_access_mode,
        cs.*
    FROM
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        -- 核心筛选条件（三种情况）
        (
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR rm.plat_access_mode IS NULL
            OR (
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 必要的基础条件
        AND cs.operation_status IN ('投运','退运')
        AND cs.commissioning_time < '{P_M}'
    """

    # 获取充电站数据
    DF_station = SQL(sql_station)
    print(f"获取到 {len(DF_station)} 条充电站记录")

    # 初始化空列表存储结果
    DF_profit_amount = []

    # 循环处理每个月的数据
    for i in list(M_DF_1['month']):
        # 提取收益数据（按月）
        sql_profit = f"""
        select 
            station_no,
            rec_month AS ym,
            sum(dd_profit_amount) AS dd_profit_amount
        from fin_rec_result_detail 
        where rec_month = {i}
        GROUP BY station_no, rec_month
        """

        # 获取收益数据
        DF_profit = SQL(sql_profit)

        # 在内存中进行左连接
        df = DF_station.merge(
            DF_profit,
            left_on='station_no',
            right_on='station_no',
            how='left'
        )

        # 确保ym列存在（对于没有匹配收益记录的站点，ym会是NaN）
        # 这里不需要手动设置ym，因为原SQL是左连接，没有匹配的记录ym会自动为NaN

        # 添加到结果列表
        DF_profit_amount.append(df)
        print(f"月份 {i}: 合并后得到 {len(df)} 条记录")

    # 合并所有月份的结果
    DF_profit_amount = pd.concat(DF_profit_amount)
    print(f"合并所有月份后总记录数: {len(DF_profit_amount)}")

    # In[152]:


    DF_profit_amount['dd_profit_amount'] = DF_profit_amount['dd_profit_amount'].astype('float')

    # In[153]:


    DF = pd.DataFrame(columns=['axisData', 'chartData', 'YxisName', 'legendName', 'month', 'statisticsData', 'station_name', 'station_no'])
    data2 = []
    for i in range(len(df_NO)):
        no = df_NO.iloc[i]['station_no']
        station_name = df_NO.iloc[i]['station_name']
        print(no, station_name)
        d3, T1, T2, x6 = imp_station(DF_profit_amount, 'ym', 'dd_profit_amount', '社会桩接入站点平均水平', '月公司分成收入', M_DF, no, R, M)
        data2.append(d3[d3['month'].str.contains(str(year))]['月公司分成收入'].sum())  # 单位：把
        d3.fillna(0, inplace=True)
        d3 = d3.sort_values(by='month', ascending=True)
        DF1 = bar_chart(d3, 'month', '元', M)
        V = [['本月度站点累计分成收入为', str(x6), '元'], ['社会桩接入站点平均水平为', str(T1), '元'], ['本月度站点排名', T2, '']]
        DF2 = word(V, DF1)
        DF2['station_name'] = station_name
        DF2['station_no'] = no
        DF = pd.concat([DF, DF2])
        print(no, station_name, '已运行完成')
    dp_social_import_amount = DF

    # In[154]:


    len(DF)

    # In[155]:


    DF2

    # In[156]:


    # 定义注释
    table_comment = "社会桩_重点社会桩运营情况_站点每月公司抽成"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分',
        'station_no': '站点名称'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_import_amount",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ## 站点每月公司收入

    # In[157]:


    DF_sr_amount = DF_trans_energy
    DF_sr_amount['trans_amount'] = DF_sr_amount['trans_amount'].astype('float')

    # In[158]:


    len(DF_sr_amount)

    # In[ ]:


    # In[159]:


    DF = pd.DataFrame(columns=['axisData', 'chartData', 'YxisName', 'legendName', 'month', 'statisticsData', 'station_name', 'station_no'])
    data3 = []
    for i in range(len(df_NO)):
        no = df_NO.iloc[i]['station_no']
        station_name = df_NO.iloc[i]['station_name']
        print(no, station_name)
        d3, T1, T2, x7 = imp_station(DF_sr_amount, 'ym', 'trans_amount', '社会桩接入站点平均水平', '月充电收入', M_DF, no, R, M)
        data3.append(d3[d3['month'].str.contains(str(year))]['月充电收入'].sum())  # 单位：把
        d3.fillna(0, inplace=True)
        d3 = d3.sort_values(by='month', ascending=True)
        DF1 = bar_chart(d3, 'month', '元', M)
        V = [['本月度站点累计充电收入为', str(x7), '元'], ['社会桩接入站点平均水平为', str(T1), '元'], ['本月度站点排名', T2, '']]
        DF2 = word(V, DF1)
        DF2['station_name'] = station_name
        DF2['station_no'] = no
        DF = pd.concat([DF, DF2])
        print(no, station_name, '已运行完成')
    dp_social_sr_amount = DF

    # In[160]:


    len(DF)

    # In[161]:


    # 定义注释
    table_comment = "社会桩_重点社会桩运营情况_站点每月充电收入"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分',
        'station_no': '站点名称'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_sr_amount",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ## 站点单枪日均充电量

    # In[162]:


    DF_trans_energy['gun'] = DF_trans_energy['dc_charge_point_count'].fillna(0) + DF_trans_energy['ac_charge_point_count'].fillna(0)
    DF_trans_energy = DF_trans_energy[DF_trans_energy['gun'] != 0]
    DF_trans_energy = DF_trans_energy[DF_trans_energy['ym'].notna()]
    DF_trans_energy['day'] = DF_trans_energy['ym'].apply(get_days_in_month)
    DF_trans_energy['trans_energy'] = DF_trans_energy['trans_energy'].fillna(0)
    DF_trans_energy['trans_energy'] = DF_trans_energy['trans_energy'].astype('float')
    DF_trans_energy['trans_energy_day'] = DF_trans_energy['trans_energy'] / DF_trans_energy['gun'] / DF_trans_energy['day']

    # In[ ]:


    # In[163]:


    DF = pd.DataFrame(columns=['axisData', 'chartData', 'YxisName', 'legendName', 'month', 'statisticsData', 'station_name', 'station_no'])
    data4 = []
    for i in range(len(df_NO)):
        no = df_NO.iloc[i]['station_no']
        station_name = df_NO.iloc[i]['station_name']
        # print(no, station_name)
        d3, T1, T2, x7 = imp_station(DF_trans_energy, 'ym', 'trans_energy_day', '社会桩接入站点平均水平', '单枪日均充电量', M_DF, no, R, M)
        data4.append(d3[d3['month'].str.contains(str(year))]['单枪日均充电量'].mean())  # 单位：把
        d3.fillna(0, inplace=True)
        d3 = d3.sort_values(by='month', ascending=True)
        DF1 = bar_chart(d3, 'month', 'kWh', M)
        V = [['本月度站点单枪充电量为', str(x7), 'kWh'], ['社会桩接入站点平均水平为', str(T1), 'kWh'], ['本月度站点排名', T2, '']]
        DF2 = word(V, DF1)
        DF2['station_name'] = station_name
        DF2['station_no'] = no
        DF = pd.concat([DF, DF2])
        # print(no, station_name, '已运行完成', len(DF))
    dp_social_import_gun_energy = DF

    # In[164]:


    # 定义注释
    table_comment = "社会桩_重点社会桩运营情况_站点每月单枪日均充电量"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_import_gun_energy",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # ## 站点每月功率利用率

    # In[165]:


    DF_plat_data_order = DF_trans_energy

    # In[166]:


    DF_plat_data_order = DF_plat_data_order[DF_plat_data_order['station_capacity'] != 0]
    DF_plat_data_order = DF_plat_data_order[DF_plat_data_order['ym'].notna()]
    DF_plat_data_order['day'] = DF_plat_data_order['ym'].apply(get_days_in_month)
    DF_plat_data_order['trans_energy'] = DF_plat_data_order['trans_energy'].astype('float')
    DF_plat_data_order['pue'] = (DF_plat_data_order['trans_energy'] / DF_plat_data_order['station_capacity'] / DF_plat_data_order['day'] / 24)*100

    # In[ ]:


    # In[167]:


    DF = pd.DataFrame(columns=['axisData', 'chartData', 'YxisName', 'legendName', 'month', 'statisticsData', 'station_name', 'station_no'])
    data5 = []
    for i in range(len(df_NO)):
        no = df_NO.iloc[i]['station_no']
        station_name = df_NO.iloc[i]['station_name']
        # print(no, station_name)
        d3, T1, T2, x8 = imp_station(DF_plat_data_order, 'ym', 'pue', '社会桩接入站点平均水平', '站点功率利用率', M_DF, no, R, M)
        data5.append(d3[d3['month'].str.contains(str(year))]['站点功率利用率'].mean())  # 单位：个
        d3.fillna(0, inplace=True)
        d3 = d3.sort_values(by='month', ascending=True)
        DF1 = bar_chart(d3, 'month', '%', M)
        V = [['本月度站点功率利用率为', str(x8), '%'], ['社会桩接入站点平均水平为', str(T1), '%'], ['本月度站点排名', T2, '']]
        DF2 = word(V, DF1)
        DF2['station_name'] = station_name
        DF2['station_no'] = no
        DF = pd.concat([DF, DF2])
        # print(no, station_name, '已运行完成', len(DF))
    dp_social_import_pue = DF

    # In[168]:


    # 定义注释
    table_comment = "社会桩_重点社会桩运营情况_站点每月功率利用率"
    column_comments = {
        'chartData': '统计图数据',
        'yAxisName': '纵坐标单位',
        'LegendName': '线条名称',
        'axisData': '横坐标数据',
        'month': '分析月份',
        'statisticsData': '表格下面文字部分'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_import_pue",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # # 中间

    # ## 站点名字

    # In[169]:


    df_NO

    # ## 充电枪数、名字、地址、额定功率

    # In[170]:


    sql = f"""
    SELECT
        rm.merchant_name,
        rm.plat_access_mode,
        cs.*
    FROM
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        -- 核心筛选条件
        (
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR rm.plat_access_mode IS NULL
            OR (
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 基础业务条件
        AND cs.operation_status IN ('投运')
        AND cs.commissioning_time < '{P_M}'
    """
    df_gun = SQL(sql)

    # In[171]:


    len(df_gun)

    # In[172]:


    df_gun['gun'] = df_gun['dc_charge_point_count'].fillna(0) + df_gun['ac_charge_point_count'].fillna(0)

    # In[173]:


    df_gun = df_gun[['station_no', 'gun', 'station_address', 'station_capacity']]
    df_gun

    # In[174]:


    df_NO = pd.merge(df_NO, df_gun, on='station_no', how='left')

    # In[175]:


    sql = """
    select rt.merchant_name,rr.station_on as station_no from  rec_merchant rt left join rec_merchant_rec_station rr  on rt.merchant_id = rr.merchant_id
    
    """
    DF_rec_result_detail = SQL(sql)
    # DF_rec_result_detail = DF_rec_result_detail[DF_rec_result_detail['rec_month']==M]


    # In[176]:


    DF_rec_result_detail[DF_rec_result_detail['station_no'] == '300003001700001687']

    # In[177]:


    D = []
    for j in df_NO['station_no']:
        merchant_name = list(DF_rec_result_detail[DF_rec_result_detail['station_no'] == j]['merchant_name'].values)
        merchant_name_str = ''
        for i in merchant_name:
            merchant_name_str = merchant_name_str + i + '、'
        merchant_name_str = merchant_name_str[:-1]
        print(merchant_name_str)
        D.append([j, merchant_name_str])

    # In[178]:


    df_merchant = pd.DataFrame(columns=['station_no', 'merchant_name'], data=D)
    df_merchant

    # In[179]:


    df_NO = pd.merge(df_NO, df_merchant, on='station_no', how='left')

    # In[180]:


    sql = """
    select station_no,ddProfitRation,ddProfitRationP from dp_profit_sharing1;
    """
    df_gz = SQL(sql)

    # In[181]:


    df_gz['station_no'] = df_gz['station_no'].astype('str')

    # In[182]:


    df_gz

    # In[183]:


    df_NO = pd.merge(df_NO, df_gz, on='station_no', how='left')

    # In[184]:


    df_NO

    # ## 单枪经济收益排名

    # In[185]:


    begin[-1]

    # In[186]:


    # 首先提取充电站基本信息
    sql_station = f"""
    SELECT
        rm.merchant_name,
        rm.plat_access_mode,
        cs.*
    FROM
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        -- 核心筛选条件（三种情况）
        (
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR rm.plat_access_mode IS NULL
            OR (
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 必要的基础条件
        AND cs.operation_status IN ('投运')
        AND cs.commissioning_time < '{P_M}'
    """

    # 获取充电站数据
    DF_station = SQL(sql_station)
    print(f"获取到 {len(DF_station)} 条充电站记录")

    # 提取订单数据（指定时间范围）
    sql_orders = f"""
    select 
        charging_station_no,
        DATE_FORMAT(order_create_time, '%Y%m') AS ym,
        sum(trans_amount) AS trans_amount
    from fin_plat_data_order 
    where order_create_time BETWEEN '{begin[-1]}' AND '{end[-1]}' 
    GROUP BY charging_station_no, DATE_FORMAT(order_create_time, '%Y%m')
    """

    # 获取订单数据
    DF_orders = SQL(sql_orders)
    print(f"时间范围 {begin[-1]} 到 {end[-1]}: 获取到 {len(DF_orders)} 条订单记录")

    # 在内存中进行左连接
    df_amount = DF_station.merge(
        DF_orders,
        left_on='station_no',
        right_on='charging_station_no',
        how='left'
    )

    print(f"合并后得到 {len(df_amount)} 条记录")

    # In[187]:


    df_amount['gun'] = df_amount['dc_charge_point_count'].fillna(0) + df_amount['ac_charge_point_count'].fillna(0)

    # In[188]:


    df_amount_1 = df_amount[df_amount['ym'] == M]

    # In[189]:


    df_amount_1 = df_amount_1[df_amount_1['gun'] != 0]

    # In[190]:


    df_amount_1['gun_amount'] = df_amount_1['trans_amount'].fillna(0).astype('float') / df_amount['gun']

    # In[191]:


    df_amount_1['Rank'] = df_amount_1['gun_amount'].rank(method='min', ascending=False).astype(int)

    # In[192]:


    df_amount_1

    # In[193]:


    D = []
    for no in df_NO['station_no']:
        # print(no)
        try:
            r = df_amount_1[df_amount_1['station_no'] == no]['Rank'].values[0]
        except IndexError:
            # print("警告：数组为空，无法访问索引 0！")
            value = None  # 或其他默认值
            r = len(df_NO)
        D.append([no, r, len(df_NO)])

    # In[194]:


    df_gun_amount = pd.DataFrame(columns=['station_no', 'gun_amount_rank', 'amount'], data=D)

    # In[195]:


    df_gun_amount

    # In[196]:


    df_NO = pd.merge(df_NO, df_gun_amount, on='station_no', how='left')

    # ## 站点单枪日均充电量排名

    # In[197]:


    # 首先提取充电站基本信息
    sql_station = f"""
    SELECT
        rm.merchant_name,
        rm.plat_access_mode,
        cs.*
    FROM
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    WHERE 
        -- 核心筛选条件（三种情况）
        (
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR rm.plat_access_mode IS NULL
            OR (
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 必要的基础条件
        AND cs.operation_status IN ('投运')
        AND cs.commissioning_time < '{P_M}'
    """

    # 获取充电站数据
    DF_station = SQL(sql_station)
    print(f"获取到 {len(DF_station)} 条充电站记录")

    # 提取订单数据（指定时间范围）
    sql_orders = f"""
    select 
        charging_station_no,
        DATE_FORMAT(order_create_time, '%Y%m') AS ym,
        sum(trans_energy) AS trans_energy
    from fin_plat_data_order 
    where order_create_time BETWEEN '{begin[-1]}' AND '{end[-1]}' 
    GROUP BY charging_station_no, DATE_FORMAT(order_create_time, '%Y%m')
    """

    # 获取订单数据
    DF_orders = SQL(sql_orders)
    print(f"时间范围 {begin[-1]} 到 {end[-1]}: 获取到 {len(DF_orders)} 条订单记录")

    # 在内存中进行左连接
    DF_trans_energy = DF_station.merge(
        DF_orders,
        left_on='station_no',
        right_on='charging_station_no',
        how='left'
    )

    print(f"合并后得到 {len(DF_trans_energy)} 条记录")

    # In[198]:


    DF_trans_energy['gun'] = DF_trans_energy['dc_charge_point_count'].fillna(0) + DF_trans_energy['ac_charge_point_count'].fillna(0)
    DF_trans_energy = DF_trans_energy[DF_trans_energy['ym'] == M]
    DF_trans_energy = DF_trans_energy[DF_trans_energy['gun'] != 0]
    DF_trans_energy['trans_energy'] = DF_trans_energy['trans_energy'].fillna(0).astype('float') / df_amount['gun']
    DF_trans_energy['Rank'] = DF_trans_energy['trans_energy'].rank(method='min', ascending=False).astype(int)

    # In[199]:


    D = []
    for no in df_NO['station_no']:
        # print(no)
        try:
            r = DF_trans_energy[DF_trans_energy['station_no'] == no]['Rank'].values[0]
        except IndexError:
            # print("警告：数组为空，无法访问索引 0！")
            value = None  # 或其他默认值
            r = len(df_NO)
        D.append([no, r])

    # In[200]:


    len(D)

    # In[201]:


    df_gun_energy = pd.DataFrame(columns=['station_no', 'gun_energy_rank'], data=D)

    # In[202]:


    df_NO = pd.merge(df_NO, df_gun_energy, on='station_no', how='left')

    # In[203]:


    df_NO.head(1)

    # ## 合并数据

    # In[204]:


    df_NO.iloc[0]['amount']

    # In[205]:


    DF = pd.DataFrame(columns=['data', 'titles', 'labels', 'units', 'month', 'station_name', 'station_no'])
    for i in range(len(df_NO)):
        # print(df_NO.iloc[i]['station_name'], df_NO.iloc[i]['station_no'])
        titles = {'chargeRanking': '站点单枪日均充电量排名', 'incomeRanking': '站点单枪充电收入排名'}
        json_titles = titles
        #     print(json_titles)
        # labels参数
        labels = {'chargerCount': '充电枪(终端)数量', 'totalPower': '总额定功率',
                  'siteCount': '合作抽成比例'}
        json_labels = json.dumps(labels, ensure_ascii=False)
        #     print(json_labels)

        # units参数
        units = {'chargeRank': '名',
                 'chargeRankTotal': '个',
                 'incomeRank': '名',
                 'incomeRankTotal': '个',
                 'station': '个',
                 'piece': '个',
                 'kw': 'kw',
                 'siteCount': ''}
        json_units = json.dumps(units, ensure_ascii=False)
        data = pd.DataFrame()
        data = data.copy()
        #     data = pd.DataFrame()
        #     data = data.copy()
        data['chargeRank'] = [df_NO.iloc[i]['gun_energy_rank']]
        data['incomeRank'] = [df_NO.iloc[i]['gun_amount_rank']]
        data['totalChargeStations'] = [df_NO.iloc[i]['amount']]
        data['totalEconomyStations'] = [df_NO.iloc[i]['amount']]
        data['chargerCount'] = [df_NO.iloc[i]['gun']]
        data['totalPower'] = [df_NO.iloc[i]['station_capacity']]
        data['siteCount'] = [df_NO.iloc[i]['ddProfitRation']]
        data['imgUrl'] = [df_NO.iloc[i]['ddProfitRationP']]
        data['unitData'] = [pd.DataFrame(
            columns=['label', 'value'],
            data=[['站点名称', df_NO.iloc[i]['station_name']], ['站点地址', df_NO.iloc[i]['station_address']],
                  ['合作单位', df_NO.iloc[i]['merchant_name']]]).to_dict(orient='records')]
        data.fillna(0, inplace=True)
        json_data_list = []
        # 遍历数据框的每一行
        for index, row in data.iterrows():
            row_dict = {}
            for col in data.columns:
                row_dict[col] = row[col]
            #     json_data = json.dumps(row_dict, ensure_ascii=False)
            json_data_list.append(row_dict)
        # 创建新的数据框存储转换后的JSON数据
        new_data = pd.DataFrame({'json_data': json_data_list}).to_dict(orient='records')
        #     print(new_data)
        # print(data)
        DF1 = pd.DataFrame()
        DF1['data'] = json_data_list
        DF1['titles'] = [json_titles]
        DF1['labels'] = [json_labels]
        DF1['units'] = [json_units]
        DF1['month'] = M
        DF1['station_name'] = df_NO.iloc[i]['station_name']
        DF1['station_no'] = df_NO.iloc[i]['station_no']
        DF = pd.concat([DF, DF1])
        print('已完成')

    # In[206]:


    df_result = DF

    # In[207]:


    df_result

    # In[208]:


    # 定义注释
    table_comment = "社会桩接入情况页_地图下方文字内容"
    column_comments = {
        'month': '当前数据的统计年月',
        'titles': '排名前的文字说明',
        'labels': '展示指标的名称',
        'units': '展示指标的单位',
        'data': '各指标取值',
        'station_name': '站点名称'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_Map_Below_Text",
        #     cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # # 顶端

    # In[209]:


    DATA

    # In[210]:


    DF_TOP1 = [['累计接入充电枪数', str(DATA[0]), '个'],
               ['本年功率利用率', str(round(DATA[1], 2)), '%'],
               ['本年累计充电量', str(round(DATA[2] / 10000, 2)), '万kWh'],
               ['本年累计分成收入', str(round(DATA[3] / 10000, 2)), '万元'],
               ]

    # In[211]:


    # DF_TOP1


    # In[212]:


    DF_TOP2 = pd.DataFrame(columns=['target', 'station_name', 'station_no'])
    for i in range(len(df_NO)):
        data2 = [['本年站点累计充电量', str(round(data1[i], 2)), 'kWh'],
                 ['本年站点累计充电收入', str(round(data3[i] / 10000, 2)), '万元'],
                 ['本年站点单枪日均充电量', str(round(data4[i], 2)), 'kWh/枪'],
                 ['本年站点功率利用率', str(round(data5[i] * 100, 2)), '%']]
        DF2 = pd.DataFrame(columns=['title', 'value', 'unit'], data=data2)
        data2 = DF2.to_json(orient='records', force_ascii=False)
        df2 = pd.DataFrame(columns=['target'], data=[data2])
        df2['station_name'] = df_NO.iloc[i]['station_name']
        df2['station_no'] = df_NO.iloc[i]['station_no']
        DF_TOP2 = pd.concat([DF_TOP2, df2])

    # In[213]:


    DF_TOP2['month'] = M

    # In[ ]:


    # In[214]:


    DF1 = pd.DataFrame(columns=['title', 'value', 'unit'], data=DF_TOP1)
    data1 = DF1.to_json(orient='records', force_ascii=False)

    # In[215]:


    df1 = pd.DataFrame(columns=['target'], data=[data1])

    # In[216]:


    df1['month'] = M

    # In[217]:


    df1

    # In[218]:


    # 定义注释
    table_comment = "社会桩接入情况页_平台整体_顶部指标"
    column_comments = {
        'month': '当前数据的统计年月',
        'target': '指标'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=df1,
        table_name="dp_social_TOP1",
        #     cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
        ,
        append_data=False, update_columns=True
    )

    # 提交
    # conn.commit()


    # In[219]:


    #  定义注释
    table_comment = "社会桩接入情况页_重点站点_顶部指标"
    column_comments = {
        'month': '当前数据的统计年月',
        'target': '指标'
    }

    # 执行导入（覆盖数据，更新列结构）
    import_data_with_cursor(
        df=DF_TOP2,
        table_name="dp_social_TOP3",
        #     cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # # 联动

    # In[220]:


    DF_1 = dp_social_import_energy[dp_social_import_energy['month'] == M]
    DF_2 = dp_social_import_amount[dp_social_import_amount['month'] == M]
    DF_3 = dp_social_sr_amount[dp_social_sr_amount['month'] == M]
    DF_4 = dp_social_import_gun_energy[dp_social_import_gun_energy['month'] == M]
    DF_5 = dp_social_import_pue[dp_social_import_pue['month'] == M]
    DF_6 = DF_TOP2[DF_TOP2['month'] == M]

    # In[221]:


    DF_1['statisticsData'] = DF_1['statisticsData'].apply(json.loads)
    DF_2['statisticsData'] = DF_2['statisticsData'].apply(json.loads)
    DF_3['statisticsData'] = DF_3['statisticsData'].apply(json.loads)
    DF_4['statisticsData'] = DF_4['statisticsData'].apply(json.loads)
    DF_5['statisticsData'] = DF_5['statisticsData'].apply(json.loads)

    # In[222]:


    DF = pd.DataFrame(columns=['siteData', 'chart1', 'chart2', 'chart3', 'chart4', 'chart5', 'basicData', 'name', 'siteNumber'])
    for no in df_NO['station_no']:
        chart1 = DF_1[DF_1['station_no'] == no][['axisData', 'chartData', 'YxisName', 'legendName', 'statisticsData']].to_json(orient='records', force_ascii=False)[1:-1]
        chart2 = DF_2[DF_2['station_no'] == no][['axisData', 'chartData', 'YxisName', 'legendName', 'statisticsData']].to_json(orient='records', force_ascii=False)[1:-1]
        chart3 = DF_3[DF_3['station_no'] == no][['axisData', 'chartData', 'YxisName', 'legendName', 'statisticsData']].to_json(orient='records', force_ascii=False)[1:-1]
        chart4 = DF_4[DF_4['station_no'] == no][['axisData', 'chartData', 'YxisName', 'legendName', 'statisticsData']].to_json(orient='records', force_ascii=False)[1:-1]
        chart5 = DF_5[DF_5['station_no'] == no][['axisData', 'chartData', 'YxisName', 'legendName', 'statisticsData']].to_json(orient='records', force_ascii=False)[1:-1]
        chart6 = df_result[df_result['station_no'] == no][['data', 'titles', 'labels', 'units', 'station_name', 'station_no']].to_dict(orient='records')[0]
        chart7 = DF_TOP2[DF_TOP2['station_no'] == no]['target'].values[0]
        DF1 = pd.DataFrame(columns=['siteData', 'chart1', 'chart2', 'chart3', 'chart4', 'chart5', 'basicData'],
                           data=[[chart7, chart1, chart2, chart3, chart4, chart5, chart6]])
        DF1['name'] = df_NO[df_NO['station_no'] == no]['station_name'].values[0]
        DF1['siteNumber'] = no
        #     print(df_NO[df_NO['station_no']==no]['station_name'])
        DF = pd.concat([DF, DF1])

    # In[223]:


    DF['month'] = M

    # In[224]:


    DF['name']

    # ## 地图

    # In[225]:


    sql = f"""
    SELECT 
        rm.merchant_name,
        rm.plat_access_mode,
        ds.*
    FROM 
        charging_station cs
        LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
        LEFT JOIN dp_station_low_lat ds ON ds.station_no = cs.station_no
    WHERE 
        -- 核心筛选条件（三种情况）
        (
            rm.plat_access_mode IN ('三方', '社会商户', '第三方', '第三方单位', '第三方合作')
            OR rm.plat_access_mode IS NULL
            OR (
                rm.plat_access_mode IN ('产业单位', '产业单位代运营', '代运营', '省公司代运营', '综合能源')
                AND cs.access_method = '社会站模型'
            )
        )
        -- 必要的基础条件
        AND cs.operation_status IN ('投运')
        AND cs.commissioning_time < '{P_M}'
    """
    DF_unit = SQL(sql)

    # In[226]:


    DF_unit = DF_unit[DF_unit['lon'] != 0]
    lon_lat = []
    for i in range(len(DF_unit)):
        lon_lat.append([DF_unit.iloc[i]['lon'], DF_unit.iloc[i]['Lat']])
    DF_unit['value'] = lon_lat
    DF_unit.rename(columns={'station_name': 'name'}, inplace=True)
    DF_unit['type'] = 1
    mapData = []
    for i in DF['siteNumber']:
        print(i)
        x = DF_unit[DF_unit['station_no'] == i][["name", "value", "type"]].to_json(orient='records', force_ascii=False)
        print(x)
        mapData.append(x)

    # In[227]:


    DF['mapData'] = mapData

    # In[228]:


    DF['mapData'][1:2][0]

    # In[229]:


    DF.loc[DF['siteNumber'] == '300003001700000057', 'mapData'] = ['[{"name":"资阳市政府充电站","value":[104.626,30.1291],"type":1}]']

    # In[230]:


    DF[['mapData']]

    # In[231]:


    # chart1 = DF1[['axisData','chartData','YxisName','legendName','statisticsData']].to_json(orient='records', force_ascii=False)[1:-1]


    # In[232]:


    # chart2 = DF2[['axisData','chartData','YxisName','legendName','statisticsData']].to_json(orient='records', force_ascii=False)[1:-1]


    # In[233]:


    # chart3 = DF3[['axisData','chartData','YxisName','legendName','statisticsData']].to_json(orient='records', force_ascii=False)[1:-1]


    # In[234]:


    # chart4 = DF4[['axisData','chartData','YxisName','legendName','statisticsData']].to_json(orient='records', force_ascii=False)[1:-1]


    # In[235]:


    # DF = pd.DataFrame(columns=['siteData','chart1','chart2','chart3','chart4','basicData'],
    #              data=[[siteData,chart1,chart2,chart3,chart4,result]])


    # In[236]:


    # DF['name'] = data['name']


    # In[237]:


    # DF['siteNumber'] = data['siteNumber']


    # In[238]:


    # DF['month'] = M


    # In[239]:


    # DF['siteData']


    # In[240]:


    # DF


    # In[241]:


    DF

    # In[242]:


    table_comment = "社会桩_社会桩重点站点相关数据（联动）"
    column_comments = {
        'name': '站点名字',
        'siteNumber': '站点编号',
        'siteData': '地图下方4组数据',
        'chart1': '站点每月充电量',
        'chart2': '站点每月公司抽成',
        'chart3': '站点单枪日均充电量',
        'chart4': '站点每月功率利用率',
        'basicData': '搜索下面的基本数据', 'mapData': '地图数据',
        'month': '统计月份'
    }

    # 执行导入
    import_data_with_cursor(
        df=DF,
        table_name="dp_social_interconnected_all",
        #         cursor=cursor,
        table_comment=table_comment,
        column_comments=column_comments
    )

    # 提交
    # conn.commit()


    # In[ ]:


    # In[ ]:




