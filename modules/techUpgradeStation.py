from logs.log_decorator import log_execution
from loguru import logger
from modules.config import SQL,import_data_with_cursor,Statistical_Time



@log_execution
def runtechUpgradeStation():
    from loguru import logger
    logger.info("开始执行技改站点页面")
    M, previous_month_str, year, last_year, last_year_month_str, P_M = Statistical_Time()
    P_M = P_M[:4] + '-' + P_M[4:]
    print(M, previous_month_str, year, last_year, last_year_month_str, P_M)
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

    from loguru import logger

    pd.options.display.float_format = '{:.6f}'.format

    # In[6]:

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

    # ### 合并

    # In[7]:

    def find_nearest_record(station_name, target_month, df):
        subset = df[
            (df['station_name'] == station_name) &
            (
                    (df['per_fault_rate'] != 0) |
                    (df['per_offline_rate'] != 0) |
                    (df['per_outage_rate'] != 0) |
                    (df['per_station_success_rate'] != 0)
            )
            ].copy()

        if subset.empty:
            return None

        subset['stat_time'] = subset['stat_time'].astype(int)
        target_month = int(target_month)

        subset['month_diff'] = (subset['stat_time'] - target_month).abs()
        nearest_record = subset.sort_values('month_diff').iloc[0]
        return nearest_record

    # In[ ]:

    # ### 天数

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

    Data = generate_months(M, 11)
    # ## sql

    # ### 基本信息

    # In[11]:

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

    # In[12]:

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

    # In[13]:

    sql = """
    SELECT
      station_no,
      SUM(CAST(point_count AS UNSIGNED)) AS total_guns,
      -- 站点整体额定功率（所有桩功率总和）
      SUM(CAST(power AS DECIMAL(10,2))) AS total_power,

      -- 交流桩数量
      SUM(CASE WHEN current_type = '交流' THEN 1 ELSE 0 END) AS ac_count,

      -- 直流桩数量
      SUM(CASE WHEN current_type = '直流' THEN 1 ELSE 0 END) AS dc_count,

      -- 交流平均功率
      CASE 
        WHEN SUM(CASE WHEN current_type = '交流' THEN 1 ELSE 0 END) = 0 THEN 0
        ELSE ROUND(
          SUM(CAST(power AS DECIMAL(10,2))) / 
          SUM(CASE WHEN current_type = '交流' THEN 1 ELSE 0 END), 2)
      END AS avg_ac_power,

      -- 直流平均功率
      CASE 
        WHEN SUM(CASE WHEN current_type = '直流' THEN 1 ELSE 0 END) = 0 THEN 0
        ELSE ROUND(
          SUM(CAST(power AS DECIMAL(10,2))) / 
          SUM(CASE WHEN current_type = '直流' THEN 1 ELSE 0 END), 2)
      END AS avg_dc_power,

      -- 设备厂商列表
      GROUP_CONCAT(DISTINCT manufacturer) AS manufacturers

    FROM
      charging_station_point
    WHERE
      station_no IN (
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
    GROUP BY
      station_no;
    """
    DF_ab = SQL(sql)

    # In[14]:

    DF_ab

    # In[15]:

    sql = """
    select * from 
    (SELECT 
    cs.*
    FROM
    charging_station cs
    LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    where 
    rm.merchant_name = '国网电动汽车服务（四川）有限公司'
    and  cs.operation_status in ('投运','退运')
    and cs.station_no IN (
        "300003000100002472",
        "300003000100002473",
        "300003000100017538",
        "300003000100017539",
        "300003000100019487",
        "300003000100019488",
        "300003013200011",
        "300003013200099",
        "300003013200108"
    )) a
    left join 
    (select * from station_cba_org_data ) b
    on a.station_no =b.station_no
    """
    DF_cba_org_data = SQL(sql)

    # ### 厂商名称

    # In[16]:

    # sql = """
    # select * from
    # (select station_no,station_category from  charging_station) c
    # right join
    # (select time,station_name,station_code,pile_status,normal_duration,operation_duration,city,pile_manufacturer from dp_operation_duration
    # ) d
    # on c.station_no = d.station_code
    # """
    # DF_operation_duration0 = SQL(sql)

    # In[17]:

    sql = """
    SELECT
      station_code,
      station_name,
      stat_time,
      sum(operation_duration) as operation,
      sum(fault_duration) as fault ,
      sum(outage_duration) as outage,
      sum(offline_duration) as offline
    FROM
      dp_operation_duration
    WHERE
      station_code IN (
        '300003000100002472',
        '300003000100002473',
        '300003000100017538',
        '300003000100017539',
        '300003000100019487',
        '300003000100019488',
        '300003013200011',
        '300003013200099',
        '300003013200108'
      )
    group by
    station_code,
      station_name,
      stat_time
    """
    DF_operation = SQL(sql)

    # ### 一次成功率

    # In[18]:

    sql = '''
    SELECT
      cs.station_no,
      cs.station_name,
      dsr.stat_time,
      ROUND(
        AVG(CAST(REPLACE(dsr.success_rate, '%', '') AS DECIMAL(10,4)) / 100),
        4
        ) AS station_success_rate
    FROM
      dp_success_rate dsr
    INNER JOIN charging_station cs
      ON dsr.station_code = cs.station_no
    WHERE
      station_no IN (
        '300003000100002472',
        '300003000100002473',
        '300003000100017538',
        '300003000100017539',
        '300003000100019487',
        '300003000100019488',
        '300003013200011',
        '300003013200099',
        '300003013200108'
      )
    GROUP BY
      cs.station_category,
      cs.station_no,
      cs.station_name,
      dsr.stat_time
    '''
    DF_success = SQL(sql)

    # In[19]:

    DF_success['stat_time'] = DF_success['stat_time'].str.replace('-', '')

    # ### 功率利用率

    # In[20]:

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
      and cs.operation_status in ('投运','退运')
    """
    DF_cba_pue = SQL(sql)

    # ### 单枪日均充电量

    # In[21]:

    def generate_begin_end(start_month: str, end_month: str):
        """
        输入起始月份和终止月份（格式: YYYYMM），返回两个列表:
        begin1: 每个月的开始时间
        end1: 每个月的结束时间
        """
        begin1 = []
        end1 = []
        start_date = datetime.strptime(start_month, "%Y%m")
        end_date = datetime.strptime(end_month, "%Y%m")

        current_date = start_date
        while current_date <= end_date:
            month_start = current_date.strftime("%Y-%m-01 00:00:00")
            next_month = current_date + relativedelta(months=1)
            month_end = (next_month - relativedelta(seconds=1)).strftime("%Y-%m-%d 23:59:59")

            begin1.append(month_start)
            end1.append(month_end)

            current_date = next_month

        return begin1, end1

    # In[22]:

    begin1, end1 = generate_begin_end("202205", M)

    # In[ ]:

    # In[ ]:

    # In[23]:

    # 假设你已经连接了数据库，并且 `SQL` 函数可以执行SQL并返回一个DataFrame
    logger.info("开始执行sql查询")
    start_time = datetime.now()  # ⬅ 开始计时

    # 1. 准备查询参数
    charging_station_nos = [
        "300003000100002472",
        "300003000100002473",
        "300003000100017538",
        "300003000100017539",
        "300003000100019487",
        "300003000100019488",
        "300003013200011",
        "300003013200099",
        "300003013200108"
    ]

    # 2. 查询小表
    sql_cs = f"""
        SELECT station_no, station_name
        FROM charging_station
        WHERE station_no IN ({', '.join([f"'{s}'" for s in charging_station_nos])})
    """
    df_cs = SQL(sql_cs)

    sql_cba = f"""
        SELECT station_no, cba_month, rec_cost_elec_cons
        FROM station_cba_org_data
        WHERE station_no IN ({', '.join([f"'{s}'" for s in charging_station_nos])})
          AND cba_month BETWEEN '{min(begin1)[:7].replace('-', '')}' AND '{max(end1)[:7].replace('-', '')}'
    """
    df_cba = SQL(sql_cba)

    station_map = df_cs.set_index('station_no')['station_name'].to_dict()
    cba_map = df_cba.set_index(['station_no', 'cba_month'])['rec_cost_elec_cons'].to_dict()

    # 3. 循环分批查询主表
    df_all = []
    for i in range(len(begin1)):
        sql_main = f"""
            SELECT
                fp.charging_station_no,
                fp.order_create_time,
                fp.charging_gun_no,
                fp.order_id,
                fp.trans_energy,
                fp.trans_amount,
                fp.charging_start_time,
                fp.charging_end_time
            FROM fin_plat_data_order fp
            WHERE fp.charging_station_no IN ({', '.join([f"'{s}'" for s in charging_station_nos])})
              AND fp.order_create_time BETWEEN '{begin1[i]}' AND '{end1[i]}'
        """
        df_d = SQL(sql_main)
        print(len(df_d), begin1[i], end1[i])

        # 日期列转换
        df_d['charging_start_time'] = pd.to_datetime(df_d['charging_start_time'])
        df_d['charging_end_time'] = pd.to_datetime(df_d['charging_end_time'])
        df_d['order_create_time'] = pd.to_datetime(df_d['order_create_time'], errors='coerce')
        df_d['ym'] = df_d['order_create_time'].dt.strftime('%Y%m')

        # 添加站点名称
        df_d['charging_station_name'] = df_d['charging_station_no'].map(station_map)

        # 聚合：按 station_no + ym
        df_agg = df_d.groupby(['charging_station_no', 'charging_station_name', 'ym']).agg(
            order_count=pd.NamedAgg(column='order_id', aggfunc='count'),
            trans_energy=pd.NamedAgg(column='trans_energy', aggfunc='sum'),
            trans_amount=pd.NamedAgg(column='trans_amount', aggfunc='sum'),
            total_used_hours=pd.NamedAgg(
                column='charging_start_time',
                aggfunc=lambda x: ((df_d.loc[x.index, 'charging_end_time'] - x).dt.total_seconds().sum()) / 3600
            )
        ).reset_index()

        # 映射 rec_cost_elec_cons
        df_agg['rec_cost_elec_cons'] = df_agg.apply(
            lambda row: cba_map.get((row['charging_station_no'], row['ym'])), axis=1
        )

        df_all.append(df_agg)

    # 4. 合并所有结果
    if df_all:
        df_final = pd.concat(df_all, ignore_index=True)
        print(len(df_final))
    else:
        df_final = pd.DataFrame()  # 空结果集处理

    end_time = datetime.now()
    elapsed_time = end_time - start_time
    logger.success(f"SQL 查询和代码处理完毕，共计运行 {elapsed_time.total_seconds():.2f} 秒")

    # In[24]:

    df_final[['total_used_hours', 'charging_station_name', 'ym']]

    # In[25]:

    DF_ab['gun_count'] = DF_ab['total_guns']

    # In[26]:

    DF_ab

    # In[27]:

    df_d1 = df_final.merge(
        DF_ab[['station_no', 'total_power', 'gun_count']],
        left_on='charging_station_no',  # df_d1里对应的列名
        right_on='station_no',  # DF_ab里对应的列名
        how='left'
    )

    # In[28]:

    df_d1 = df_d1.merge(
        DF_cba_pue[['station_no', 'plat_data_charging_volume', 'cba_month']],
        left_on=['charging_station_no', 'ym'],
        right_on=['station_no', 'cba_month'],
        how="left"
    )

    # In[ ]:

    # In[29]:

    # 计算电损率
    df_d1['electricity_loss_ratio'] = df_d1.apply(
        lambda row: 1 - float(row['plat_data_charging_volume']) / float(row['rec_cost_elec_cons'])
        if row['rec_cost_elec_cons'] and row['rec_cost_elec_cons'] != 0 else None,
        axis=1
    )

    # ## 站点信息

    # In[30]:

    DF_charging_station['total_charging_point'] = DF_charging_station['dc_charge_point_count'] + DF_charging_station['ac_charge_point_count']

    # In[31]:

    after_stations_list = [
        "四川省成都市彭州市濛阳镇供电所公共充电站",
        "沪蓉高速遂宁服务区公共充电站（成都方向）",
        "沪蓉高速遂宁服务区公共充电站（上海方向）",
        "四川省成都市成华区麻石桥城市公共充电站"
    ]

    # In[32]:

    selected_columns = [
        'station_name',
        'station_category',
        'station_address',
        'station_capacity',
        'total_charging_point',
        'investment_amount',
        'commissioning_time'
    ]

    # In[33]:

    DF_basic_info = DF_charging_station.loc[
        DF_charging_station['station_name'].isin(after_stations_list),
        selected_columns
    ]

    # In[34]:

    DF_basic_info

    # # 技改前后信息对比

    # In[35]:

    DF_ab

    # In[36]:

    DF_ab1 = pd.merge(DF_ab, DF_charging_station, on='station_no', how='inner')
    DF_ab1 = DF_ab1[['station_name', 'total_power', 'ac_count', 'dc_count', 'avg_ac_power', 'avg_dc_power', 'manufacturers', 'total_guns']]

    # In[37]:

    reform_pairs = [
        ('四川省成都市彭州市濛阳镇供电所电动汽车充电站', '四川省成都市彭州市濛阳镇供电所公共充电站'),
        ('沪蓉高速遂宁服务区公共充电站成都方向', '沪蓉高速遂宁服务区公共充电站（成都方向）'),
        ('沪蓉高速遂宁服务区公共充电站上海方向', '沪蓉高速遂宁服务区公共充电站（上海方向）'),
        ('四川省成都市成华区麻石桥充电站', '四川省成都市成华区麻石桥城市公共充电站'),
        ('四川省成都市成华区麻石桥充电站二期', '四川省成都市成华区麻石桥城市公共充电站'),
    ]

    # In[38]:

    records = []

    for old_name, new_name in reform_pairs:
        # 找出技改前后的行（各只取第一条记录）
        old_row = DF_ab1[DF_ab1['station_name'] == old_name].iloc[0] if not DF_ab1[DF_ab1['station_name'] == old_name].empty else None
        new_row = DF_ab1[DF_ab1['station_name'] == new_name].iloc[0] if not DF_ab1[DF_ab1['station_name'] == new_name].empty else None

        # 如果两边都能找到，组合结果
        if old_row is not None and new_row is not None:
            combined = {
                'pre_station_name': old_name,
                'pre_station_capacity': old_row['total_power'],
                'pre_ac_power': old_row['avg_ac_power'],
                'pre_dc_power': old_row['avg_dc_power'],
                'pre_ac_count': old_row['ac_count'],
                'pre_dc_count': old_row['dc_count'],
                'pre_manufacturer': old_row['manufacturers'],
                'pre_guns': old_row['total_guns'],

                'post_station_name': new_name,
                'post_station_capacity': new_row['total_power'],
                'post_ac_power': new_row['avg_ac_power'],
                'post_dc_power': new_row['avg_dc_power'],
                'post_ac_count': new_row['ac_count'],
                'post_dc_count': new_row['dc_count'],
                'post_manufacturer': new_row['manufacturers'],
                'post_guns': new_row['total_guns'],
            }
            records.append(combined)

    reform_df = pd.DataFrame(records)

    # In[39]:

    reform_df


    # In[41]:

    M[4:]

    # In[42]:

    M_2023 = '2023' + M[4:]

    # In[43]:

    M_2023

    # In[44]:

    Data_pre = generate_months(M_2023, 11)

    # In[45]:

    Data_pre

    # ## 设备质量

    # In[46]:

    DF_operation['fault_rate'] = DF_operation['fault'] / DF_operation['operation']
    DF_operation['outage_rate'] = DF_operation['outage'] / DF_operation['operation']
    DF_operation['offline_rate'] = DF_operation['offline'] / DF_operation['operation']

    # In[47]:

    DF_operation1 = DF_operation[['station_name', 'station_code', 'stat_time', 'fault_rate', 'outage_rate', 'offline_rate']].copy()

    # In[48]:

    DF_operation2 = pd.merge(
        DF_success,
        DF_operation1,
        left_on=['station_no', 'stat_time', 'station_name'],
        right_on=['station_code', 'stat_time', 'station_name'],
        how='left'
    )

    # In[49]:

    DF_operation2 = DF_operation2[['station_no', 'station_name', 'stat_time', 'fault_rate', 'offline_rate', 'outage_rate', 'station_success_rate']]

    # In[50]:

    DF_operation2 = DF_operation2.fillna(0)

    # In[51]:

    DF_operation2

    # In[52]:

    # DF_operation_rate['故障率'] = (DF_operation_rate['fault_duration'] / DF_operation_rate['operation_duration']).round(4)
    # DF_operation_rate['停运率'] = (DF_operation_rate['outage_duration'] / DF_operation_rate['operation_duration']).round(4)
    # DF_operation_rate['离线率'] = (DF_operation_rate['offline_duration'] / DF_operation_rate['operation_duration']).round(4)

    # DF_operation_rate['month_start'] = pd.to_datetime(DF_operation_rate['time'].str[:8], format='%Y%m%d', errors='coerce')

    # # 转成年月整数 YYYYMM
    # DF_operation_rate['month_int'] = DF_operation_rate['month_start'].dt.strftime('%Y%m').astype(int)

    # In[53]:

    # # 合并表，左表为 DF_operation_rate，右表为 DF_charging_station
    # DF_operation_rate = DF_operation_rate.merge(
    #     DF_charging_station[['station_no', 'commissioning_time', 'downtime']],
    #     how='left',
    #     left_on='station_code',  # operation_rate 中的字段
    #     right_on='station_no'  # charging_station 中的字段
    # )

    # In[54]:

    # downtime_map = {
    #     '四川省成都市彭州市濛阳镇供电所电动汽车充电站': '202404',
    #     '四川省成都市成华区麻石桥充电站': '202404',
    #     '四川省成都市成华区麻石桥充电站二期': '202404',
    #     '沪蓉高速遂宁服务区公共充电站成都方向': '202312',
    #     '沪蓉高速遂宁服务区公共充电站上海方向': '202312',
    # }

    # In[55]:

    # DF_operation_rate['downtime'] = DF_operation_rate['station_name'].map(downtime_map)
    # # 提取前6位字符作为 month
    # DF_operation_rate['month'] = DF_operation_rate['time'].str[:6]

    # In[56]:

    reform_post_stations = [
        "300003000100017538",
        "300003000100017539",
        "300003000100019487",
        "300003000100019488"
    ]
    # [
    #     '四川省成都市彭州市濛阳镇供电所公共充电站',
    #     '沪蓉高速遂宁服务区公共充电站（成都方向）',
    #     '沪蓉高速遂宁服务区公共充电站（上海方向）',
    #     '四川省成都市成华区麻石桥城市公共充电站',
    # ]

    #
    reform_per_stations = [
        "300003000100002472",
        "300003000100002473",
        "300003013200011",
        "300003013200099",
        "300003013200108"
    ]
    # [
    #     '四川省成都市彭州市濛阳镇供电所电动汽车充电站',
    #     '沪蓉高速遂宁服务区公共充电站成都方向',
    #     '沪蓉高速遂宁服务区公共充电站上海方向',
    #     '四川省成都市成华区麻石桥充电站',
    #     '四川省成都市成华区麻石桥充电站二期',
    # ]

    # In[57]:
    # 提取 Data['month'] 列为一个列表
    months = Data['month'].tolist()

    # In[58]:

    # 使用 isin 判断月份和站点是否符合要求
    DF_operation_post = DF_operation2[
        DF_operation2['station_no'].isin(reform_post_stations)
    ]

    # In[59]:

    DF_operation_per = DF_operation2[DF_operation2['station_no'].isin(reform_per_stations)]

    # In[ ]:

    # In[60]:

    DF_operation_post = DF_operation_post.rename(columns={
        "fault_rate": "post_fault_rate",
        "offline_rate": "post_offline_rate",
        "outage_rate": "post_outage_rate",
        "station_success_rate": "post_station_success_rate",
    })

    # In[61]:

    DF_operation_per = DF_operation_per.rename(columns={
        "fault_rate": "per_fault_rate",
        "offline_rate": "per_offline_rate",
        "outage_rate": "per_outage_rate",
        "station_success_rate": "per_station_success_rate",
    })

    # In[62]:

    DF_operation_per

    # In[63]:

    DF_operation_post

    # In[64]:

    # results_pre = []

    # all_before_stations = DF_operation_per['station_name'].unique()

    # for before_station in all_before_stations:
    #     for target_month in Data['month']:
    #         # 先尝试找目标月份数据
    #         candidate = DF_operation_per[
    #             (DF_operation_per['station_name'] == before_station) &
    #             (DF_operation_per['stat_time'] == target_month)
    #         ]

    #         if not candidate.empty:
    #             # 判断是否全0
    #             row = candidate.iloc[0]
    #             if any([
    #                 row['per_fault_rate'] != 0,
    #                 row['per_offline_rate'] != 0,
    #                 row['per_outage_rate'] != 0,
    #                 row['per_station_success_rate'] != 0
    #             ]):
    #                 record = row
    #             else:
    #                 # 全0，找最近非0
    #                 record = find_nearest_record(before_station, target_month, DF_operation_per)
    #         else:
    #             # 无数据，找最近非0
    #             record = find_nearest_record(before_station, target_month, DF_operation_per)

    #         if record is None:
    #             # 找不到非0数据，填0
    #             result = {
    #                 'station_name': before_station,
    #                 'stat_time': target_month,
    #                 'per_fault_rate': 0,
    #                 'per_offline_rate': 0,
    #                 'per_outage_rate': 0,
    #                 'per_station_success_rate': 0,
    #             }
    #         else:
    #             result = {
    #                 'station_name': before_station,
    #                 'stat_time': target_month,
    #                 'per_fault_rate': record['per_fault_rate'],
    #                 'per_offline_rate': record['per_offline_rate'],
    #                 'per_outage_rate': record['per_outage_rate'],
    #                 'per_station_success_rate': record['per_station_success_rate'],
    #             }

    #         results_pre.append(result)

    # DF_pre_final = pd.DataFrame(results_pre)

    # In[65]:

    Data_pre

    # In[ ]:

    # In[ ]:

    # In[66]:

    # 获取所有技改前站点编号
    pre_stations = DF_operation_per['station_name'].unique()

    # 创建所有站点和目标月份的笛卡尔积
    import itertools

    all_combinations_pre = list(itertools.product(pre_stations, Data_pre['month']))
    df_all_pre = pd.DataFrame(all_combinations_pre, columns=['station_name', 'stat_time'])

    # 合并真实数据，缺失的补 0
    DF_pre_final = pd.merge(
        df_all_pre,
        DF_operation_per,
        on=['station_name', 'stat_time'],
        how='left'
    )

    # 将缺失的指标值补 0
    for col in ['per_fault_rate', 'per_offline_rate', 'per_outage_rate', 'per_station_success_rate']:
        DF_pre_final[col] = DF_pre_final[col].fillna(0)

    # In[67]:

    DF_pre_final['stat_time'] = DF_pre_final['stat_time'].astype(str)

    # 方法 1：简单字符串替换（2022->2024, 2023->2025）
    DF_pre_final['stat_time'] = (
        DF_pre_final['stat_time'].astype(str).str.replace('2022','2024').str.replace('2023','2025')
    )

    # In[68]:

    # 获取所有技改后站点编号
    post_stations = DF_operation_post['station_name'].unique()

    # 创建所有站点和目标月份的笛卡尔积
    import itertools

    all_combinations = list(itertools.product(post_stations, Data['month']))
    df_all = pd.DataFrame(all_combinations, columns=['station_name', 'stat_time'])

    # 合并真实数据，缺失的补 0
    DF_post_final = pd.merge(
        df_all,
        DF_operation_post,
        on=['station_name', 'stat_time'],
        how='left'
    )

    # 将缺失的指标值补 0
    for col in ['post_fault_rate', 'post_offline_rate', 'post_outage_rate', 'post_station_success_rate']:
        DF_post_final[col] = DF_post_final[col].fillna(0)

    # In[69]:

    def compare_station_quality(DF_pre_final, DF_post_final, pre_name, post_name):
        pre_df = DF_pre_final.loc[
            DF_pre_final['station_name'] == pre_name,
            ['per_fault_rate', 'per_offline_rate', 'per_outage_rate', 'per_station_success_rate', 'stat_time']
        ].copy()

        post_df = DF_post_final.loc[
            DF_post_final['station_name'] == post_name,
            ['post_fault_rate', 'post_offline_rate', 'post_outage_rate', 'post_station_success_rate', 'stat_time']
        ].copy()

        merged = pd.merge(pre_df, post_df, on="stat_time", how="left")
        merged['station_name'] = pre_name  # 统一保留技改前名称
        return merged

    # In[70]:

    shebeishiliang = pd.concat([
        compare_station_quality(DF_pre_final, DF_post_final, before, after)
        for before, after in reform_pairs
    ], ignore_index=True)

    # In[ ]:

    # ### 平均值

    # In[71]:

    columns_to_average = [
        'per_fault_rate', 'per_offline_rate', 'per_outage_rate',
        'per_station_success_rate', 'post_fault_rate', 'post_offline_rate',
        'post_outage_rate', 'post_station_success_rate'
    ]
    shebeishiliang[columns_to_average] = shebeishiliang[columns_to_average].astype(float)
    grouped_means = (
        shebeishiliang
            .groupby('station_name')[columns_to_average]
            .mean()  # 默认会跳过 NaN
            .reset_index()
            .fillna(0)  # 如果整列都是 NaN，结果是 NaN，这里再补 0
    )

    # In[72]:

    grouped_means

    # ## 运营效率

    # ### 时长利用率

    # In[73]:

    df_d1['days'] = df_d1['ym'].apply(get_days_in_month)

    # In[74]:

    df_d1.columns

    # In[75]:

    df_d1['time_rate'] = (
            df_d1['total_used_hours'] / (
            df_d1['gun_count'].astype(float) * df_d1['days'].astype(float) * 24
    )
    )

    # In[ ]:

    # ### 功率利用率

    # In[ ]:

    # In[76]:

    df_d1['pue'] = df_d1['plat_data_charging_volume'].astype(float) / (
            df_d1['total_power'].astype(float) * df_d1['days'].astype(float) * 24
    )

    # ### 单枪日均充电量

    # In[77]:

    df_d1['per_gun'] = (
            df_d1['plat_data_charging_volume'].astype(float) /
            df_d1['gun_count'].astype(float) /
            df_d1['days'].astype(float)
    )

    # In[78]:

    df_d1

    # In[79]:

    operating_efficiency = df_d1[['charging_station_no', 'charging_station_name', 'ym', 'time_rate', 'per_gun', 'pue']]

    # In[80]:

    post_operating_efficiency = operating_efficiency[
        operating_efficiency['charging_station_no'].isin(reform_post_stations)
    ]

    # In[81]:

    post_operating_efficiency = post_operating_efficiency.rename(columns={
        "charging_station_name": "station_name",
        "ym": "month",
        "time_rate": "post_time_rate",
        "per_gun": "post_per_gun",
        "pue": "post_pue",
    })

    # In[82]:

    pre_operating_efficiency = operating_efficiency[
        operating_efficiency['charging_station_no'].isin(reform_per_stations)
    ]

    # In[83]:

    pre_operating_efficiency = pre_operating_efficiency.rename(columns={
        "charging_station_name": "station_name",
        "ym": "month",
        "time_rate": "pre_time_rate",
        "per_gun": "pre_per_gun",
        "pue": "pre_pue",
    })

    # In[84]:

    # 获取所有技改前站点编号
    pre_stations = pre_operating_efficiency['station_name'].unique()

    # 创建所有站点和目标月份的笛卡尔积
    import itertools

    all_combinations_pre = list(itertools.product(pre_stations, Data_pre['month']))
    df_all_pre = pd.DataFrame(all_combinations_pre, columns=['station_name', 'month'])

    # 合并真实数据，缺失的补 0
    DF_pre_yunying_final = pd.merge(
        df_all_pre,
        pre_operating_efficiency,
        on=['station_name', 'month'],
        how='left'
    )

    # 将缺失的指标值补 0
    for col in ['pre_time_rate', 'pre_per_gun', 'pre_pue']:
        DF_pre_yunying_final[col] = DF_pre_yunying_final[col].fillna(0)

    # In[85]:

    DF_pre_yunying_final['month'] = DF_pre_yunying_final['month'].astype(str)
    DF_pre_yunying_final['month'] =(
         DF_pre_yunying_final['month']
                .str.replace('2022','2024')
                .str.replace('2023','2025')
    )

    # In[86]:

    # 获取所有技改后站点编号
    post_stations = post_operating_efficiency['station_name'].unique()

    # 创建所有站点和目标月份的笛卡尔积
    import itertools

    all_combinations = list(itertools.product(post_stations, Data['month']))
    df_all = pd.DataFrame(all_combinations, columns=['station_name', 'month'])

    # 合并真实数据，缺失的补 0
    DF_post_yunying_final = pd.merge(
        df_all,
        post_operating_efficiency,
        on=['station_name', 'month'],
        how='left'
    )

    # 将缺失的指标值补 0
    for col in ['post_time_rate', 'post_per_gun', 'post_pue']:
        DF_post_yunying_final[col] = DF_post_yunying_final[col].fillna(0)

    # In[ ]:

    # In[87]:

    def compare_station_efficiency(pre_operating_efficiency, post_operating_efficiency, pre_name, post_name):
        # 取前数据
        pre_df = pre_operating_efficiency.loc[
            pre_operating_efficiency['station_name'] == pre_name,
            ['pre_time_rate', 'pre_per_gun', 'pre_pue', 'month']
        ].copy()

        # 取后数据
        post_df = post_operating_efficiency.loc[
            post_operating_efficiency['station_name'] == post_name,
            ['post_time_rate', 'post_per_gun', 'post_pue', 'month']
        ].copy()

        # 合并，基于月份对比
        merged = pd.merge(pre_df, post_df, on="month", how="left")

        # 增加站点名对照

        merged['station_name'] = pre_name

        return merged

    # In[88]:

    yunyingxiaolv = pd.concat([
        compare_station_efficiency(DF_pre_yunying_final, DF_post_yunying_final, before, after)
        for before, after in reform_pairs
    ], ignore_index=True)

    # In[89]:

    yunyingxiaolv = yunyingxiaolv[['pre_time_rate', 'pre_per_gun', 'pre_pue', 'month', 'post_time_rate',
                                   'post_per_gun', 'post_pue', 'station_name']]

    # In[90]:

    columns_to_average = [
        'pre_time_rate', 'pre_per_gun', 'pre_pue',
        'post_time_rate', 'post_per_gun', 'post_pue'
    ]

    # 强制转换为 float
    yunyingxiaolv[columns_to_average] = yunyingxiaolv[columns_to_average].astype(float)

    # 然后再 groupby + mean
    yunyingxiaolv_means = (
        yunyingxiaolv
            .groupby('station_name')[columns_to_average]
            .mean()
            .reset_index()
            .fillna(0)
    )

    # In[91]:

    yunyingxiaolv_means

    # ## 经济效益

    # In[92]:

    df_d1.columns

    # In[93]:

    xiaoxi = df_d1[['charging_station_no', 'charging_station_name', 'electricity_loss_ratio', 'ym', 'order_count', 'trans_amount']]

    # In[94]:

    xiaoxi = xiaoxi.fillna(0)

    # In[95]:

    post_xiaoxi = xiaoxi[
        xiaoxi['charging_station_no'].isin(reform_post_stations)
    ]

    # In[96]:

    pre_xiaoxi = xiaoxi[
        xiaoxi['charging_station_no'].isin(reform_per_stations)
    ]

    # In[97]:

    post_xiaoxi = post_xiaoxi.rename(columns={
        "charging_station_name": "station_name",
        "ym": "month",
        "electricity_loss_ratio": "post_electricity_loss_ratio",
        "order_count": "post_post_order_count",
        "trans_amount": "post_trans_amount",
    })

    # In[98]:

    pre_xiaoxi = pre_xiaoxi.rename(columns={
        "charging_station_name": "station_name",
        "ym": "month",
        "electricity_loss_ratio": "pre_electricity_loss_ratio",
        "order_count": "pre_post_order_count",
        "trans_amount": "pre_trans_amount",
    })

    # In[99]:

    # 获取所有技改前站点编号
    pre_stations = pre_xiaoxi['station_name'].unique()

    # 创建所有站点和目标月份的笛卡尔积
    import itertools

    all_combinations_pre = list(itertools.product(pre_stations, Data_pre['month']))
    df_all_pre = pd.DataFrame(all_combinations_pre, columns=['station_name', 'month'])  # 列名保持一致

    # 合并真实数据，缺失的补 0
    DF_pre_xiaoxi_final = pd.merge(
        df_all_pre,
        pre_xiaoxi,
        on=['station_name', 'month'],
        how='left'
    )

    # 将缺失的指标值补 0
    for col in ['pre_electricity_loss_ratio', 'pre_post_order_count', 'pre_trans_amount']:
        DF_pre_xiaoxi_final[col] = DF_pre_xiaoxi_final[col].fillna(0)

    # In[100]:

    DF_pre_xiaoxi_final['month'] = DF_pre_xiaoxi_final['month'].astype(str)
    DF_pre_xiaoxi_final['month'] = (
         DF_pre_xiaoxi_final['month']
                .str.replace('2022','2024')
                .str.replace('2023','2025')
    )

    # In[101]:

    # 获取所有技改后站点编号
    post_stations = post_xiaoxi['station_name'].unique()

    # 创建所有站点和目标月份的笛卡尔积
    import itertools

    all_combinations = list(itertools.product(post_stations, Data['month']))
    df_all = pd.DataFrame(all_combinations, columns=['station_name', 'month'])  # 注意列名保持一致

    # 合并真实数据，缺失的补 0
    DF_post_xiaoxi_final = pd.merge(
        df_all,
        post_xiaoxi,
        on=['station_name', 'month'],
        how='left'
    )

    # 将缺失的指标值补 0
    for col in ['post_electricity_loss_ratio', 'post_post_order_count', 'post_trans_amount']:
        DF_post_xiaoxi_final[col] = DF_post_xiaoxi_final[col].fillna(0)

    # In[102]:

    def compare_station_xiaoxi(pre_xiaoxi, post_xiaoxi, pre_name, post_name):
        # 获取前数据
        pre_df = pre_xiaoxi.loc[
            pre_xiaoxi['station_name'] == pre_name,
            ['pre_electricity_loss_ratio', 'pre_post_order_count', 'pre_trans_amount', 'month']
        ].copy()

        # 获取后数据
        post_df = post_xiaoxi.loc[
            post_xiaoxi['station_name'] == post_name,
            ['post_electricity_loss_ratio', 'post_post_order_count', 'post_trans_amount', 'month']
        ].copy()

        # 按月份合并
        merged = pd.merge(pre_df, post_df, on='month', how='left')

        # 添加站点名称列

        merged['station_name'] = pre_name

        return merged

    # In[103]:

    jingjixiaoyi = pd.concat([
        compare_station_xiaoxi(DF_pre_xiaoxi_final, DF_post_xiaoxi_final, before, after)
        for before, after in reform_pairs
    ], ignore_index=True)

    # ### 单瓦效益

    # In[104]:

    this_year = f"{M[:4]}年"

    # In[105]:

    this_year

    # In[106]:

    # sql = """
    # SELECT
    # cs.station_name,cs.station_no,cs.investment_amount,cs.commissioning_time,cs.station_category
    # FROM
    # charging_station cs
    # LEFT JOIN rec_merchant rm ON cs.property_owner_merhant_id = rm.merchant_id
    # where
    # cs.station_no IN ( "300003000100002472", "300003000100002473", "300003000100017538", "300003000100017539", "300003000100019487", "300003000100019488", "300003013200011", "300003013200099", "300003013200108" )

    # """
    # DF_station = SQL(sql)

    this_year = f"{M[:4]}年"

    sql = f"""
    select year,station_no,IFNULL(total_subsidy,0) as total_subsidy from dp_subsidy_NEW
    where year = '{this_year}'
    """
    DF_subsidy = SQL(sql)

    sql = f"""
    SELECT 
      b.station_no,
      a.station_name,
      b.cba_month,
      SUM(
        IFNULL(b.rec_data_elec_fee_revenue,0)
        + IFNULL(b.rec_data_service_fee_revenue,0)
        + IFNULL(b.other_revenue_battery_swap_services,0)
        + IFNULL(b.other_revenue_op_subsidies,0)
        + IFNULL(b.other_revenue_build_subsidies,0)
        + IFNULL(b.other_revenue_access_control_barriers,0)
        + IFNULL(b.other_revenue_dr,0)
      ) AS revenue,
      SUM(
        IFNULL(b.rec_cost_elec_fee,0)
        + IFNULL(b.rec_cost_actual_rec_amount,0)
        + IFNULL(b.rec_cost_plat_service,0)
        + IFNULL(b.rec_cost_rent,0)
        + IFNULL(b.om_cost_om,0)
        + IFNULL(b.om_cost_spare_parts,0)
        + IFNULL(b.om_cost_op_project,0)
        + IFNULL(b.fin_cost_depreciation,0)
        + IFNULL(b.fin_cost_labor,0)
      ) AS cost
    FROM (
      SELECT cs.*
      FROM charging_station cs
      WHERE cs.station_no IN (
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
    ) a
    LEFT JOIN (
      SELECT *
      FROM station_cba_org_data
      WHERE cba_month <= '{M}'
    ) b
    ON a.station_no = b.station_no
    GROUP BY a.station_name, b.station_no, b.cba_month;
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
    # if int(M[4:])==12:
    #     M_next = str(int(M[:4])+1)+'01'
    # else:
    #     M_next = M[:4]+str(int(M[4:])+1).rjust(2, "0")

    sql = f"""
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
    fin_rec_result_detail = SQL(sql)

    sql = f"""
    select station_no,stat_time,maintenance_cost as maintenance_cost from  dp_station_maintenance_cost1
    where 
    (stat_time <= {M}) and maintenance_cost>0
    group by station_no,stat_time;
    """
    DF_maintenance = SQL(sql)

    DF_maintenance = (
        DF_maintenance
            .groupby(['station_no', 'stat_time'])
            .agg({'maintenance_cost': 'sum'})
            .reset_index()
    )

    # DF_1 = pd.merge(DF_station,DF_cost_revenue,on='station_no',how='left')
    DF_1 = DF_cost_revenue.copy()

    # 处理投运时间字段
    DF_rent = DF_rent[['station_no', 'parking_fee']]
    DF_rent['parking_fee'] = DF_rent['parking_fee'].astype('float')
    DF_1 = pd.merge(DF_1, DF_rent, on='station_no', how='left')
    DF_1 = DF_1[DF_1['cba_month'] <= M]
    DF_1 = pd.merge(DF_1, DF_maintenance,
                    left_on=['station_no', 'cba_month'],
                    right_on=['station_no', 'stat_time'],
                    how='left')
    d1 = len(DF_1)
    DF_1 = DF_1.T.drop_duplicates().T

    fin_rec_result_detail = fin_rec_result_detail.fillna(0)
    fin_rec_result_detail = fin_rec_result_detail[['station_no', 'merchant_profit_amount', 'rec_month']]
    # fin_rec_result_detail =fin_rec_result_detail.rename(columns={'rec_month':'year_month'})
    fin_rec_result_detail = (
        fin_rec_result_detail
            .groupby(['station_no', 'rec_month'])
            .agg({'merchant_profit_amount': 'sum'})
            .reset_index()
    )

    DF_1 = pd.merge(DF_1, fin_rec_result_detail, left_on=['station_no', 'cba_month'],
                    right_on=['station_no', 'rec_month'],
                    how='left')
    DF_1 = DF_1.fillna(0)

    DF_1['revenue'] = DF_1['revenue'].astype('float')
    DF_1['cost'] = DF_1['cost'].astype('float') + DF_1['parking_fee']
    DF_1['merchant_profit_amount'] = DF_1['merchant_profit_amount'].astype('float')
    DF = pd.merge(DF_1, DF_subsidy, on='station_no', how='left')
    DF = DF.fillna(0)
    DF['in'] = DF['revenue'].astype('float')
    DF['out'] = DF['cost'].astype('float') + DF['merchant_profit_amount'].astype('float') + DF['maintenance_cost'].astype('float')
    DF['income'] = DF['in'] - DF['out']

    # In[107]:


    # In[108]:

    DF_watt1 = DF[['station_no', 'station_name', 'income', 'cba_month']]

    # In[109]:

    DF_ab

    # In[110]:

    DF_watt = DF_watt1.merge(
        DF_ab[['station_no', 'total_power']],
        on='station_no',
        how='left'
    )

    # In[111]:

    # 假设 station_capacity 单位是 kW
    DF_watt['capacity_watt'] = DF_watt['total_power'].astype(float)
    DF_watt['income'] = DF_watt['income'].astype(float)
    # 单瓦效益（元/W）
    DF_watt['benefit_per_watt'] = DF_watt['income'] / DF_watt['capacity_watt'] / 1000

    # In[112]:

    DF_watt

    # In[113]:

    DF_watt.loc[(DF_watt['station_no'] == "300003000100017538") & (DF_watt['cba_month'] == M),
                ['station_no', 'station_name', 'income', 'cba_month', 'total_power', 'capacity_watt', 'benefit_per_watt']]

    # In[114]:

    DF_watt

    # In[115]:

    post_DF_watt = DF_watt[
        DF_watt['station_no'].isin(reform_post_stations)
    ]

    # In[116]:

    pre_DF_watt = DF_watt[
        DF_watt['station_no'].isin(reform_per_stations)
    ]

    # In[117]:

    post_DF_watt = post_DF_watt.rename(columns={
        "cba_month": "month",
        "benefit_per_watt": "post_benefit_per_watt",
    })

    # In[118]:

    pre_DF_watt = pre_DF_watt.rename(columns={
        "cba_month": "month",
        "benefit_per_watt": "pre_benefit_per_watt",
    })

    # In[ ]:

    # In[119]:

    # 获取所有技改前站点编号
    pre_stations = pre_DF_watt['station_name'].unique()

    # 创建所有站点和目标月份的笛卡尔积
    import itertools

    all_combinations_pre = list(itertools.product(pre_stations, Data_pre['month']))
    df_all_pre = pd.DataFrame(all_combinations_pre, columns=['station_name', 'month'])  # 列名保持一致

    # 合并真实数据，缺失的补 0
    DF_pre_DF_watt_final = pd.merge(
        df_all_pre,
        pre_DF_watt,
        on=['station_name', 'month'],
        how='left'
    )

    # 将缺失的指标值补 0
    for col in ['pre_benefit_per_watt']:
        DF_pre_DF_watt_final[col] = DF_pre_DF_watt_final[col].fillna(0)

    # In[120]:

    DF_pre_DF_watt_final['month'] = DF_pre_DF_watt_final['month'].astype(str)
    DF_pre_DF_watt_final['month'] =  (
         DF_pre_DF_watt_final['month']
                .str.replace('2022','2024')
                .str.replace('2023','2025')
    )

    # In[121]:

    # 获取所有技改后站点编号
    post_stations = post_DF_watt['station_name'].unique()

    # 创建所有站点和目标月份的笛卡尔积
    import itertools

    all_combinations = list(itertools.product(post_stations, Data['month']))
    df_all = pd.DataFrame(all_combinations, columns=['station_name', 'month'])  # 注意列名保持一致

    # 合并真实数据，缺失的补 0
    DF_post_DF_watt_final = pd.merge(
        df_all,
        post_DF_watt,
        on=['station_name', 'month'],
        how='left'
    )

    # 将缺失的指标值补 0
    for col in ['post_benefit_per_watt']:
        DF_post_DF_watt_final[col] = DF_post_DF_watt_final[col].fillna(0)

    # In[122]:

    def compare_station_DF_watt(DF_pre_DF_watt_final, DF_post_DF_watt_final, pre_name, post_name):
        # 获取前数据
        pre_df = DF_pre_DF_watt_final.loc[
            DF_pre_DF_watt_final['station_name'] == pre_name,
            ['pre_benefit_per_watt', 'month']
        ].copy()

        # 获取后数据
        post_df = DF_post_DF_watt_final.loc[
            DF_post_DF_watt_final['station_name'] == post_name,
            ['post_benefit_per_watt', 'month']
        ].copy()

        # 按月份合并
        merged = pd.merge(pre_df, post_df, on='month', how='left')

        # 添加站点名称列

        merged['station_name'] = pre_name

        return merged

    # In[123]:

    watt_enconomy = pd.concat([
        compare_station_DF_watt(DF_pre_DF_watt_final, DF_post_DF_watt_final, before, after)
        for before, after in reform_pairs
    ], ignore_index=True)

    # In[124]:

    jingjixiaoyi = jingjixiaoyi.merge(
        watt_enconomy,
        on=['station_name', 'month'],
        how='left'
    )

    # In[125]:

    jingjixiaoyi.columns

    # ### 平均值

    # In[126]:

    #############################2025年7月30日21:26:02##########################################################################

    # In[127]:

    jingjixiaoyi = jingjixiaoyi[['pre_electricity_loss_ratio', 'pre_post_order_count',
                                 'pre_trans_amount', 'month', 'post_electricity_loss_ratio',
                                 'post_post_order_count', 'post_trans_amount',
                                 'station_name', 'pre_benefit_per_watt', 'post_benefit_per_watt']]

    # In[128]:

    columns_to_average = [
        'pre_electricity_loss_ratio', 'pre_post_order_count',
        'pre_trans_amount', 'post_electricity_loss_ratio',
        'post_post_order_count', 'post_trans_amount',
        'pre_benefit_per_watt', 'post_benefit_per_watt'
    ]
    jingjixiaoyi[columns_to_average] = jingjixiaoyi[columns_to_average].astype(float)
    jingjixiaoyi_means = (
        jingjixiaoyi
            .groupby('station_name')[columns_to_average]
            .mean()  # 默认就会跳过 NaN
            .reset_index()
            .fillna(0)  # 如果某站点全是 NaN，就补 0
    )

    # In[129]:

    jingjixiaoyi_means

    # # 技改成效总览

    # In[130]:

    from functools import reduce

    # In[131]:

    dfs = [grouped_means, yunyingxiaolv_means, jingjixiaoyi_means]

    df_merged = reduce(lambda left, right: pd.merge(left, right, on='station_name', how='outer'), dfs)

    # In[132]:

    DF_station_info = DF_charging_station[['station_no', 'station_name', 'station_address', 'investment_amount', 'station_category']].copy()

    # # 数据更新进数据库

    # ## 成效总览

    # In[133]:

    DF_station_info

    # In[134]:

    df_merged

    # In[135]:

    df_change_result = df_merged.merge(
        DF_station_info[['station_name', 'station_category', 'station_no']],  # 包含 station_name
        on='station_name',
        how='left'
    )

    # In[136]:

    df_change_result.columns

    # In[137]:

    df_change_result['post_trans_amount'] = df_change_result['post_trans_amount'] / 10000
    df_change_result['pre_trans_amount'] = df_change_result['pre_trans_amount'] / 10000

    # In[138]:

    df_change_result['charge_form'] = '扩容、升级、迁址'

    # In[139]:

    df_change_result['station_category'].unique()

    # In[140]:

    def series_to_str(s):
        return ", ".join(s.astype(str).tolist())

    # 构建站点维度的数据
    station_data = []
    for idx, row in df_change_result.iterrows():
        station_data.append({
            "siteNum": row['station_no'],
            "siteName": row['station_name'],
            "siteType": row['station_category'],  # 站点类型
            "technologicalTransformation": row['charge_form'],  # 技改形式

            # 故障率
            "previousFailureRate": f"{float(row['per_fault_rate']) * 100:.2f}",  # 技改前
            "afterFailureRate": f"{float(row['post_fault_rate']) * 100:.2f}",  # 技改后

            # 停运率
            "previousOutageRate": f"{float(row['per_outage_rate']) * 100:.2f}",  # 技改前
            "afterOutageRate": f"{float(row['post_outage_rate']) * 100:.2f}",  # 技改后

            # 离线率
            "previousOfflineRate": f"{float(row['per_offline_rate']) * 100:.2f}",  # 技改前
            "afterOfflineRate": f"{float(row['post_offline_rate']) * 100:.2f}",  # 技改后

            # 一次成功率
            "previousSuccessRate": f"{float(row['per_station_success_rate']) * 100:.2f}",  # 技改前
            "afterSuccessRate": f"{float(row['post_station_success_rate']) * 100:.2f}",  # 技改后

            # 功率利用率
            "previousPowerUtilization": f"{float(row['pre_pue']) * 100:.2f}",  # 技改前
            "afterPowerUtilization": f"{float(row['post_pue']) * 100:.2f}",  # 技改后

            # 时长利用率
            "previousDurationUtilization": f"{float(row['pre_time_rate']) * 100 :.2f}",  # 技改前
            "afterDurationUtilization": f"{float(row['post_time_rate']) * 100 :.2f}",  # 技改后

            # 单枪日均充电量
            "previousChargeCapacity": f"{float(row['pre_per_gun']):.2f}",  # 技改前
            "afterChargeCapacity": f"{float(row['post_per_gun']):.2f}",  # 技改后

            # 订单数量
            "previousOrderQuantity": int(float(row['pre_post_order_count'])),  # 技改前
            "afterOrderQuantity": int(float(row['post_post_order_count'])),  # 技改后

            # 电量消耗
            "previousPowerConsumption": f"{float(row['pre_electricity_loss_ratio']) * 100:.2f}",  # 技改前
            "afterPowerConsumption": f"{float(row['post_electricity_loss_ratio']) * 100:.2f}",  # 技改后

            # 充电收入
            "previousChargingRevenue": f"{float(row['pre_trans_amount']) :.2f}",  # 技改前
            "afterChargingRevenue": f"{float(row['post_trans_amount']) :.2f}",  # 技改后

            # 单瓦效益
            "previousSingleWattBenefits": f"{float(row['pre_benefit_per_watt']) :.2f}",  # 技改前
            "afterSingleWattBenefits": f"{float(row['post_benefit_per_watt']) :.2f}"  # 技改后
        })

    # 构建最终结构（直接扁平化 tableData）
    result = {
        "siteNameFilters": [
            "四川省成都市彭州市濛阳镇供电所电动汽车充电站",
            "四川省成都市成华区麻石桥充电站",
            "四川省成都市成华区麻石桥充电站二期",
            "沪蓉高速遂宁服务区公共充电站上海方向",
            "沪蓉高速遂宁服务区公共充电站成都方向"
        ],
        "technologicalTransformationFilters": ["迁址", "扩容", "升级"],
        "siteTypeFilters": ["城市公共", "高速公共", "重卡专用"],
        "tableData": station_data
    }

    # In[141]:

    result

    # In[142]:

    # 表和字段注释
    table_comment = "技改站点_技改成效总览"
    column_comments = {
        'result': '技改成效总览',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_jigai_all",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )



    # ## 技改前后信息对比

    # In[ ]:

    # In[143]:

    no_ad_inv = DF_charging_station[['station_no', 'station_name', 'station_address', 'investment_amount']]

    # In[144]:

    # 给 pre_station_name 对应的列赋值
    reform_df = reform_df.merge(
        no_ad_inv[['station_name', 'station_no', 'station_address', 'investment_amount']],
        how='left',
        left_on='pre_station_name',
        right_on='station_name'
    )

    # 重命名新合并列名，避免冲突
    reform_df.rename(columns={
        'station_no': 'pre_station_no',
        'station_address': 'pre_station_address',
        'investment_amount': 'pre_investment_amount'
    }, inplace=True)

    # 删除多余的合并键列
    reform_df.drop(columns=['station_name'], inplace=True)

    # 给 post_station_name 对应的列赋值，重复类似操作
    reform_df = reform_df.merge(
        no_ad_inv[['station_name', 'station_no', 'station_address', 'investment_amount']],
        how='left',
        left_on='post_station_name',
        right_on='station_name',
        suffixes=('', '_post')
    )

    # 重命名为对应的post列
    reform_df.rename(columns={
        'station_no': 'post_station_no',
        'station_address': 'post_station_address',
        'investment_amount': 'post_investment_amount'
    }, inplace=True)

    # 删除多余的合并键列
    reform_df.drop(columns=['station_name'], inplace=True)

    # In[145]:

    reform_df['post_investment_amount'] = reform_df['post_investment_amount'] + reform_df['pre_investment_amount']

    # In[146]:

    reform_df['post_investment_amount'] = reform_df['post_investment_amount'] / 10000
    reform_df['pre_investment_amount'] = reform_df['pre_investment_amount'] / 10000

    # In[147]:

    # import pandas as pd

    # df456 = reform_df.copy()

    # def judge_reform(row):
    #     result = []
    #     # 扩容 or 缩容 —— 用 station_capacity
    #     if row["post_station_capacity"] > row["pre_station_capacity"]:
    #         result.append("扩容")
    #     elif row["post_station_capacity"] < row["pre_station_capacity"]:
    #         result.append("缩容")

    #     # 升级 —— 投资额变多
    #     if (row["post_investment_amount"] -  row["pre_investment_amount"]) > 0:
    #         result.append("升级")

    #     # 迁址 —— 名称或地址不同
    #     if (row["pre_station_name"] != row["post_station_name"]) or \
    #        (row["pre_station_address"] != row["post_station_address"]):
    #         result.append("迁址")

    #     return "、".join(result) if result else "无变化"

    # df456["reform_type"] = df.apply(judge_reform, axis=1)

    # In[148]:

    # jigaixingshi = df456[['pre_station_no','post_station_no','reform_type','pre_station_name','post_station_name']]

    # In[149]:

    reform_df.columns

    # In[152]:

    import pandas as pd

    def to_str(val):
        return "" if val is None else str(val)

    def with_unit(value, unit):
        if pd.isna(value):
            return "--"
        return f"{value}{unit}"
    # 假设 reform_df 已有数据，取前两行做示例
    df_sample = reform_df

    duibi = []
    for i, row in df_sample.iterrows():
        entry = {

            "siteNum": row["pre_station_no"],  # 或者用 post_station_no，看你需求
            "tableData": [
                {
                    "technological": "技改前",
                    "siteName": to_str(row.get("pre_station_name")),
                    "siteAddress": to_str(row.get("pre_station_address")),
                    "amountInvested": with_unit(row.get("pre_investment_amount"), " 万元"),
                    "totalRatedPower": with_unit(row.get("pre_station_capacity"), " kW"),
                    "averagePower": [
                        {"name": "交流桩", "value": to_str(row.get("pre_ac_power")), "unit": "kW"},
                        {"name": "直流桩", "value": to_str(row.get("pre_dc_power")), "unit": "kW"}
                    ],
                    "devices": [
                        {"name": "交流桩", "value": to_str(row.get("pre_ac_count")), "unit": "个"},
                        {"name": "直流桩", "value": to_str(row.get("pre_dc_count")), "unit": "个"},
                        {"name": "充电枪", "value": to_str(row.get("pre_guns")), "unit": "个"}
                    ],
                    "manufacturers": to_str(row.get("pre_manufacturer"))
                },
                {
                    "technological": "技改后",
                    "siteName": to_str(row.get("post_station_name")),
                    "siteAddress": to_str(row.get("post_station_address")),
                    "amountInvested": with_unit(row.get("post_investment_amount"), " 万元"),
                    "totalRatedPower": with_unit(row.get("post_station_capacity"), " kW"),
                    "averagePower": [
                        {"name": "交流桩", "value": to_str(row.get("post_ac_power")), "unit": "kW"},
                        {"name": "直流桩", "value": to_str(row.get("post_dc_power")), "unit": "kW"}
                    ],
                    "devices": [
                        {"name": "交流桩", "value": to_str(row.get("post_ac_count")), "unit": "个"},
                        {"name": "直流桩", "value": to_str(row.get("post_dc_count")), "unit": "个"},
                        {"name": "充电枪", "value": to_str(row.get("post_guns")), "unit": "个"}
                    ],
                    "manufacturers": to_str(row.get("post_manufacturer"))
                }
            ]
        }
        duibi.append(entry)

    # In[153]:

    duibi

    # In[154]:

    # tech_duibi

    # In[155]:

    # duibi

    # In[156]:

    # 表和字段注释
    table_comment = "技改站点_技改前后信息对比"
    column_comments = {
        'result': '技改前后信息对比',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(duibi, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_jigai_comparison",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )



    # In[ ]:

    # In[ ]:

    # In[ ]:

    # ## 预计回本周期

    # In[ ]:

    # ## 技改成效

    # ### 设备质量

    # In[157]:

    # step1:先把每个表都组装好站点编号

    # In[158]:

    shebeishiliang = shebeishiliang.merge(
        DF_station_info[['station_name', 'station_no']],  # 包含 station_name
        on='station_name',
        how='left'
    )
    grouped_means = grouped_means.merge(
        DF_station_info[['station_name', 'station_no']],  # 包含 station_name
        on='station_name',
        how='left'
    )
    yunyingxiaolv = yunyingxiaolv.merge(
        DF_station_info[['station_name', 'station_no']],  # 包含 station_name
        on='station_name',
        how='left'
    )
    yunyingxiaolv_means = yunyingxiaolv_means.merge(
        DF_station_info[['station_name', 'station_no']],  # 包含 station_name
        on='station_name',
        how='left'
    )
    jingjixiaoyi = jingjixiaoyi.merge(
        DF_station_info[['station_name', 'station_no']],  # 包含 station_name
        on='station_name',
        how='left'
    )
    jingjixiaoyi_means = jingjixiaoyi_means.merge(
        DF_station_info[['station_name', 'station_no']],  # 包含 station_name
        on='station_name',
        how='left'
    )

    # In[159]:

    shebeishiliang.columns

    # In[160]:

    shebeishiliang['per_outage_rate'] = shebeishiliang['per_outage_rate']
    shebeishiliang['post_outage_rate'] = shebeishiliang['post_outage_rate']

    # In[161]:

    indicators = {
        "故障率(%)": ("per_fault_rate", "post_fault_rate"),
        "停运率(%)": ("per_outage_rate", "post_outage_rate"),
        "离线率(%)": ("per_offline_rate", "post_offline_rate"),
        "一次成功率(%)": ("per_station_success_rate", "post_station_success_rate"),
    }

    equipment_quality = []

    for idx, row_mean in grouped_means.iterrows():
        site_no = row_mean['station_no']

        # 分月份数据
        df_detail = shebeishiliang[shebeishiliang['station_no'] == site_no].sort_values('stat_time')
        # 把 YYYYMM 转成 "X月"
        months = [f"{int(str(m)[-2:])}月" for m in df_detail['stat_time'].tolist()]

        # tableData 均值，统一转换为浮点数百分比
        tableData = [
            {
                "title": "故障率(%)",
                "content": [
                    {"name": "技改前（均值）", "value": f"{float(row_mean['per_fault_rate']) * 100:.2f}"},
                    {"name": "技改后（均值）", "value": f"{float(row_mean['post_fault_rate']) * 100:.2f}"},
                ]
            },
            {
                "title": "停运率(%)",
                "content": [
                    {"name": "技改前（均值）", "value": f"{float(row_mean['per_outage_rate']) * 100:.2f}"},
                    {"name": "技改后（均值）", "value": f"{float(row_mean['post_outage_rate']) * 100:.2f}"},
                ]
            },
            {
                "title": "离线率(%)",
                "content": [
                    {"name": "技改前（均值）", "value": f"{float(row_mean['per_offline_rate']) * 100:.2f}"},
                    {"name": "技改后（均值）", "value": f"{float(row_mean['post_offline_rate']) * 100:.2f}"},
                ]
            },
            {
                "title": "一次成功率(%)",
                "content": [
                    {"name": "技改前（均值）", "value": f"{float(row_mean['per_station_success_rate']) * 100:.2f}"},
                    {"name": "技改后（均值）", "value": f"{float(row_mean['post_station_success_rate']) * 100:.2f}"},
                ]
            }
        ]

        option = list(indicators.keys())
        data_list = []

        for key, (pre_col, post_col) in indicators.items():
            # 转换为浮点数并填充缺失值
            pre_values = df_detail[pre_col].fillna(0).apply(float).tolist()
            post_values = df_detail[post_col].fillna(0).apply(float).tolist()

            # 如果值在0~1之间，则乘100
            if max(pre_values + post_values) <= 1:
                pre_values = [v * 100 for v in pre_values]
                post_values = [v * 100 for v in post_values]

            # 保留两位小数
            pre_values = [round(v, 2) for v in pre_values]
            post_values = [round(v, 2) for v in post_values]

            data_list.append({
                "radio": key,
                "yAxisLeftName": "%",
                "legendName": ["技改前", "技改后"],
                "axisData": months,
                "chartData": [pre_values, post_values],
            })

        equipment_quality.append({
            "siteNum": site_no,
            "tableData": tableData,
            "option": option,
            "data": data_list
        })

    # In[162]:

    # equipment_quality

    # In[163]:

    # 表和字段注释
    table_comment = "技改站点_技改成效_设备质量"
    column_comments = {
        'result': '技改成效_设备质量',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(equipment_quality, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_jigai_result_equipment_quality",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )



    # ### 运营效率

    # In[164]:

    yunyingxiaolv_means

    # In[165]:

    yunyingxiaolv

    # In[166]:

    indicators = {
        "功率利用率(%)": ("pre_pue", "post_pue"),
        "时长利用率(%)": ("pre_time_rate", "post_time_rate"),
        "单枪日均充电量(kWh)": ("pre_per_gun", "post_per_gun"),
    }

    unit_dict = {
        "功率利用率(%)": "%",
        "时长利用率(%)": "%",
        "单枪日均充电量(kWh)": "kWh",
    }

    operating_efficiency = []

    for idx, row_mean in yunyingxiaolv_means.iterrows():
        site_no = row_mean['station_no']

        # 分月份数据
        df_detail = yunyingxiaolv[yunyingxiaolv['station_no'] == site_no].sort_values('month')
        # 把 YYYYMM 转成 "X月"
        months = [f"{int(str(m)[-2:])}月" for m in df_detail['month'].tolist()]

        # tableData 均值
        tableData = []
        for key, (pre_col, post_col) in indicators.items():
            pre_val = row_mean.get(pre_col, 0)
            post_val = row_mean.get(post_col, 0)

            # 如果是百分比指标且 <=1 则乘100
            if key in ["功率利用率(%)", "时长利用率(%)"] and max(pre_val, post_val) <= 1:
                pre_val *= 100
                post_val *= 100

            tableData.append({
                "title": key,
                "content": [
                    {"name": "技改前（均值）", "value": f"{pre_val:.2f}"},
                    {"name": "技改后（均值）", "value": f"{post_val:.2f}"},
                ]
            })

        option = list(indicators.keys())
        data_list = []

        for key, (pre_col, post_col) in indicators.items():
            # 安全取值并填充缺失
            pre_values = df_detail.get(pre_col, pd.Series([0] * len(df_detail))).fillna(0).apply(float).tolist()
            post_values = df_detail.get(post_col, pd.Series([0] * len(df_detail))).fillna(0).apply(float).tolist()

            # 百分比指标统一乘100
            if key in ["功率利用率(%)", "时长利用率(%)"] and max(pre_values + post_values) <= 1:
                pre_values = [v * 100 for v in pre_values]
                post_values = [v * 100 for v in post_values]

            # 保留两位小数
            pre_values = [round(v, 2) for v in pre_values]
            post_values = [round(v, 2) for v in post_values]

            data_list.append({
                "radio": key,
                "yAxisLeftName": unit_dict.get(key, ""),
                "legendName": ["技改前", "技改后"],
                "axisData": months,
                "chartData": [pre_values, post_values],
            })

        operating_efficiency.append({
            "siteNum": site_no,
            "tableData": tableData,
            "option": option,
            "data": data_list
        })

    # In[167]:

    # 表和字段注释
    table_comment = "技改站点_技改成效_运营效率"
    column_comments = {
        'result': '技改成效_运营效率',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(operating_efficiency, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_jigai_result_operating_efficiency",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )



    # ### 经济效益

    # In[168]:

    jingjixiaoyi_means

    # In[169]:

    indicators = {
        "订单数量(单)": ("pre_post_order_count", "post_post_order_count"),
        "电损(%)": ("pre_electricity_loss_ratio", "post_electricity_loss_ratio"),
        "充电收入(元)": ("pre_trans_amount", "post_trans_amount"),
        "单瓦效益（元）": ("pre_benefit_per_watt", "post_benefit_per_watt"),
    }

    unit_dict = {
        "订单数量(单)": "单",
        "电损(%)": "%",
        "充电收入(元)": "元",
        "单瓦效益（元）": "元",
    }

    economic_benefits = []

    for idx, row_mean in jingjixiaoyi_means.iterrows():
        site_no = row_mean['station_no']

        # 分月份数据，并格式化为 X月
        df_detail = jingjixiaoyi[jingjixiaoyi['station_no'] == site_no].sort_values('month')
        months = [f"{int(str(m)[-2:])}月" for m in df_detail['month'].tolist()]

        # tableData 均值
        tableData = []
        for key, (pre_col, post_col) in indicators.items():
            pre_val = row_mean.get(pre_col, 0)
            post_val = row_mean.get(post_col, 0)

            # 百分比指标处理
            if key == "电损(%)" and max(pre_val, post_val) <= 1:
                pre_val *= 100
                post_val *= 100

            # 整数指标转换
            if key == "订单数量(单)":
                pre_val = int(pre_val)
                post_val = int(post_val)

            tableData.append({
                "title": key,
                "content": [
                    {
                        "name": "技改前（均值）",
                        "value": f"{pre_val:.2f}" if isinstance(pre_val, float) else f"{pre_val}"
                    },
                    {
                        "name": "技改后（均值）",
                        "value": f"{post_val:.2f}" if isinstance(post_val, float) else f"{post_val}"
                    },
                ]
            })

        option = list(indicators.keys())
        data_list = []

        for key, (pre_col, post_col) in indicators.items():
            # 安全获取列
            pre_values = df_detail.get(pre_col, pd.Series([0] * len(df_detail))).fillna(0).apply(float).tolist()
            post_values = df_detail.get(post_col, pd.Series([0] * len(df_detail))).fillna(0).apply(float).tolist()

            # 百分比指标统一乘100
            if key == "电损(%)" and max(pre_values + post_values) <= 1:
                pre_values = [v * 100 for v in pre_values]
                post_values = [v * 100 for v in post_values]

            # 保留两位小数
            pre_values = [round(v, 2) for v in pre_values]
            post_values = [round(v, 2) for v in post_values]

            data_list.append({
                "radio": key,
                "yAxisLeftName": unit_dict.get(key, ""),
                "legendName": ["技改前", "技改后"],
                "axisData": months,
                "chartData": [pre_values, post_values],
            })

        economic_benefits.append({
            "siteNum": site_no,
            "tableData": tableData,
            "option": option,
            "data": data_list
        })

    # In[170]:

    # 表和字段注释
    table_comment = "技改站点_技改成效_经济效率"
    column_comments = {
        'result': '技改成效_经济效率',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(economic_benefits, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_jigai_result_economic_benefits",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )


    # In[ ]:

    # In[ ]:










