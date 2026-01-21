import pandas as pd
import numpy as np
import pymysql
from datetime import datetime,date
import os
from dateutil.parser import parse
import json
from pandas.tseries.offsets import MonthBegin
import calendar
from dateutil.relativedelta import relativedelta
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
import re


def SQL(sql):
    conn = pymysql.connect(
        #host='192.168.0.193',# 数据库地址
        host='10.177.58.100',
        #host='192.168.0.223',
        user='root',  # 用户名
        password='edac123456',  # 密码
        database='scdd_db',  # 数据库名
        port=1106  # 端口
    )
    cursor = conn.cursor()  # 创建游标对象

    cursor.execute(sql)
    price_data1 = cursor.fetchall()  # 获取查询结果，并转化为数据框
    columns_list1 = [desc[0] for desc in cursor.description]  # 从游标中提取列名
    D_F = pd.DataFrame(price_data1, columns=columns_list1)  # 转换为DataFrame并添加列名

    # # 查数完成后：
    conn.commit()  # 提交后，锁释放，事务结束
    cursor.close()  # 关闭游标
    conn.close()  # 关闭数据库连接
    return D_F


from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# 全局变量，用于存储自定义月份
CUSTOM_MONTH = None


def Statistical_Time():
    # 如果设置了自定义月份，使用自定义月份
    if CUSTOM_MONTH:
        M = CUSTOM_MONTH
    else:
        #默认行为：使用当前时间的前一个月
        M = date.today().strftime('%Y%m')  # 获取当前时间

        dt = datetime.strptime(M, "%Y%m")
        # 如果当前是 1 月（如 '202501'），则上个月是去年 12 月
        if dt.month == 1:
            M = f"{dt.year - 1}12"
        else:
            M = f"{dt.year}{dt.month - 1:02d}"  # :02d 补零

    dt = datetime.strptime(M, "%Y%m")
    year = dt.year
    month = dt.month

    # 直接减 1 年
    last_year = year - 1
    last_year_month_str = f"{year - 1}{month:02d}"

    if month == 1:
        previous_year = year - 1
        previous_month = 12
    else:
        previous_year = year
        previous_month = month - 1
    previous_month_str = f"{previous_year:04d}{previous_month:02d}"

    # 计算下个月
    if month == 12:
        P_M = f"{year + 1}01"
    else:
        P_M = f"{year}{month + 1:02d}"

    return M, previous_month_str, year, last_year, last_year_month_str, P_M

def import_data_with_cursor(df, table_name, table_comment=None, column_comments=None,
                            append_data=False, update_columns=True, longtext_columns=None, primary_keys=None):
    """
    将 DataFrame 数据导入到 MySQL 表中，确保主键能正确更新为新列。
    """
    # 初始化数据库连接
    # conn = pymysql.connect(
    #     host='192.168.0.215',
    #     user='root',
    #     password='edac123456',
    #     database='scdd_db',
    #     port=1206
    # )
    conn = pymysql.connect(
        #     host='192.168.0.193',# 数据库地址
        # host='10.177.58.100',
        host='10.177.58.100',
        user='root',  # 用户名
        password='edac123456',  # 密码
        database='scdd_db',  # 数据库名
        port=1206  # 端口
    )
    cursor = conn.cursor()

    # 处理可选参数默认值
    longtext_columns = longtext_columns or []
    primary_keys = primary_keys or []
    target_pk_set = set(primary_keys)  # 目标主键集合（用于对比）

    # 验证主键有效性
    if primary_keys:
        # 检查主键列是否存在
        invalid_keys = [key for key in primary_keys if key not in df.columns]
        if invalid_keys:
            raise ValueError(f"主键列不存在于DataFrame中: {', '.join(invalid_keys)}")

        # 检查数据中是否有NULL值
        null_check = df[primary_keys].isnull().any()
        null_columns = null_check[null_check].index.tolist()
        if null_columns:
            raise ValueError(f"主键列包含NULL值，无法设置主键: {', '.join(null_columns)}")

    # 数据类型映射
    dtype_mapping = {
        'int64': 'INT',
        'float64': 'FLOAT',
        'datetime64[ns]': 'DATETIME',
        'object': 'TEXT'
    }

    # 检查表是否存在
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
    """, (table_name,))
    table_exists = cursor.fetchone()[0] > 0

    if not table_exists:
        # 新建表逻辑
        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            sql_type = 'TEXT'

            if col in primary_keys:
                sql_type = 'VARCHAR(255) NOT NULL'
            elif col in longtext_columns:
                sql_type = 'LONGTEXT'
            else:
                for key, value in dtype_mapping.items():
                    if key in dtype:
                        sql_type = value
                        break

            col_comment = f" COMMENT '{column_comments[col]}'" if (column_comments and col in column_comments) else ""
            columns.append(f'`{col}` {sql_type}{col_comment}')

        primary_key_sql = f", PRIMARY KEY (`{('`,`'.join(primary_keys))}`)" if primary_keys else ""
        table_comment_sql = f" COMMENT='{table_comment}'" if table_comment else ""

        create_sql = f"""
            CREATE TABLE `{table_name}` (
                {', '.join(columns)}{primary_key_sql}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4{table_comment_sql}
        """
        try:
            cursor.execute(create_sql)
            print(f"成功创建表 {table_name}")
            if primary_keys:
                print(f"已设置主键: {', '.join(primary_keys)}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"表 {table_name} 已存在，继续执行")
                table_exists = True
            else:
                print(f"创建表失败: {e}")
                raise

    else:
        print(f"表 {table_name} 已存在，继续执行")

        if update_columns:
            # 获取当前表列
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            current_columns = [row[0] for row in cursor.fetchall()]

            # 添加新列（如station_no1）
            new_columns = [col for col in df.columns if col not in current_columns]
            for col in new_columns:
                dtype = str(df[col].dtype)
                sql_type = 'TEXT'

                if col in primary_keys:
                    sql_type = 'VARCHAR(255) NOT NULL'
                elif col in longtext_columns:
                    sql_type = 'LONGTEXT'
                else:
                    for key, value in dtype_mapping.items():
                        if key in dtype:
                            sql_type = value
                            break

                col_comment = f" COMMENT '{column_comments[col]}'" if (column_comments and col in column_comments) else ""
                try:
                    cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{col}` {sql_type}{col_comment}")
                    print(f"添加列 {col} 成功")
                except Exception as e:
                    print(f"添加列 {col} 失败: {e}")

            # 删除多余列
            drop_columns = [col for col in current_columns if col not in df.columns]
            for col in drop_columns:
                try:
                    cursor.execute(f"ALTER TABLE `{table_name}` DROP COLUMN `{col}`")
                    print(f"删除列 {col} 成功")
                except Exception as e:
                    print(f"删除列 {col} 失败: {e}")

        # 主键列类型修正（确保VARCHAR(255)且非空）
        if primary_keys:
            for col in primary_keys:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (col,))
                col_info = cursor.fetchone()
                if col_info:
                    current_type = col_info[1].upper()
                    if ('TEXT' in current_type or 'BLOB' in current_type) or 'NOT NULL' not in current_type:
                        try:
                            cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` VARCHAR(255) NOT NULL")
                            print(f"主键列 {col} 类型修正为 VARCHAR(255) NOT NULL")
                        except Exception as e:
                            print(f"修正主键列 {col} 失败: {e}")
                            raise

        # 处理LONGTEXT列
        for col in longtext_columns:
            if col in df.columns:
                try:
                    cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` LONGTEXT")
                    print(f"列 {col} 设为 LONGTEXT 成功")
                except Exception as e:
                    print(f"设置 {col} 为 LONGTEXT 失败: {e}")

        # 处理主键设置（核心优化部分）
        if primary_keys:
            # 获取当前数据库名
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()[0]

            # 检查当前是否有主键
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.table_constraints
                WHERE table_schema = %s AND table_name = %s AND constraint_type = 'PRIMARY KEY'
            """, (current_db, table_name))
            has_primary_key = cursor.fetchone()[0] > 0
            print(f"当前表是否有主键: {has_primary_key}")  # 新增日志

            # 获取当前主键列
            current_pk = []
            if has_primary_key:
                cursor.execute("""
                    SELECT k.column_name FROM information_schema.table_constraints t
                    JOIN information_schema.key_column_usage k
                        ON t.constraint_name = k.constraint_name
                        AND t.table_schema = k.table_schema
                        AND t.table_name = k.table_name
                    WHERE t.table_schema = %s AND t.table_name = %s AND t.constraint_type = 'PRIMARY KEY'
                """, (current_db, table_name))
                current_pk = [row[0] for row in cursor.fetchall()]
            current_pk_set = set(current_pk)
            print(f"当前主键列: {current_pk}, 目标主键列: {primary_keys}")  # 新增日志

            # 核心优化1：强制判断主键是否需要更新（即使查询结果异常）
            need_update_pk = False
            if not has_primary_key:
                need_update_pk = True  # 无主键时需要设置
            elif current_pk_set != target_pk_set:
                need_update_pk = True  # 主键不一致时需要更新
            # 特殊场景：目标主键包含新列（如station_no1）时强制更新
            elif not target_pk_set.issubset(current_pk_set):
                need_update_pk = True

            print(f"是否需要更新主键: {need_update_pk}")  # 新增日志

            # 主键不匹配时删除旧主键
            if need_update_pk and has_primary_key:
                try:
                    cursor.execute(f"ALTER TABLE `{table_name}` DROP PRIMARY KEY")
                    print(f"已删除旧主键: {', '.join(current_pk)}")
                    has_primary_key = False  # 标记为无主键
                except Exception as e:
                    print(f"删除旧主键失败: {e}")
                    raise

            # 设置新主键
            if need_update_pk:
                # 再次确保主键列类型正确
                for col in primary_keys:
                    cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (col,))
                    col_info = cursor.fetchone()
                    if col_info and ('VARCHAR(255)' not in col_info[1].upper() or 'NOT NULL' not in col_info[1].upper()):
                        try:
                            cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` VARCHAR(255) NOT NULL")
                            print(f"强制修正 {col} 为 VARCHAR(255) NOT NULL")
                        except Exception as e:
                            print(f"强制修正 {col} 失败: {e}")
                            raise

                # 创建新主键
                try:
                    cursor.execute(f"ALTER TABLE `{table_name}` ADD PRIMARY KEY (`{('`,`'.join(primary_keys))}`)")
                    print(f"成功设置新主键: {', '.join(primary_keys)}")
                except Exception as e:
                    print(f"设置新主键失败: {e}")
                    raise


    if table_exists and not append_data:
        try:
            cursor.execute(f"TRUNCATE TABLE `{table_name}`")
            print(f"表 {table_name} 已清空（append_data=False，覆盖模式）")
        except Exception as e:
            print(f"清空表 {table_name} 失败: {e}")
            raise

    # 更新表注释
    if table_comment:
        try:
            cursor.execute(f"ALTER TABLE `{table_name}` COMMENT = '{table_comment}'")
            print(f"表 {table_name} 注释更新成功")
        except Exception as e:
            print(f"更新表注释失败: {e}")

    # 更新列注释
    if column_comments:
        for col, comment in column_comments.items():
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (col,))
            if cursor.fetchone():
                try:
                    cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                    create_sql = cursor.fetchone()[1]
                    match = re.search(f"`{col}`\\s+([^\\s,]+)", create_sql)
                    if match:
                        col_type = match.group(1)
                        if col in primary_keys and 'NOT NULL' not in col_type:
                            col_type += ' NOT NULL'
                        cursor.execute(f"""
                            ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` {col_type} COMMENT '{comment}'
                        """)
                        print(f"列 {col} 注释更新成功")
                except Exception as e:
                    print(f"更新 {col} 注释失败: {e}")

    # 插入数据（补全中断的逻辑）
    if not df.empty:
        # 处理长文本列（列表/字典转JSON字符串）
        for col in longtext_columns:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else str(x)
                )

        # 对齐表列和数据列（确保插入的列与表结构一致）
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        table_cols = [row[0] for row in cursor.fetchall()]
        df_insert = df.reindex(columns=table_cols, fill_value=None)

        # 生成插入语句（动态匹配表列）
        cols_str = ', '.join([f'`{col}`' for col in table_cols])
        placeholders = ', '.join(['%s'] * len(table_cols))
        insert_sql = f"INSERT INTO `{table_name}` ({cols_str}) VALUES ({placeholders})"

        # 处理数据（确保主键列无NULL，其他列按类型适配）
        data = []
        for row in df_insert.values:
            processed_row = []
            for i, value in enumerate(row):
                col_name = table_cols[i]
                # 主键列不允许NULL，替换为空字符串（避免插入失败）
                if col_name in primary_keys and pd.isna(value):
                    processed_row.append('')
                # 列表/字典类型（未被长文本处理的兜底）
                elif isinstance(value, (list, dict)):
                    processed_row.append(json.dumps(value, ensure_ascii=False))
                # NULL值（MySQL用None表示NULL）
                elif pd.isna(value):
                    processed_row.append(None)
                # 其他类型直接保留（如int、float、str）
                else:
                    processed_row.append(value)
            data.append(tuple(processed_row))

        # 批量执行插入（高效导入）
        try:
            cursor.executemany(insert_sql, data)
            print(f"成功导入 {len(data)} 行数据到表 {table_name}")
        except Exception as e:
            print(f"数据导入失败: {e}")
            conn.rollback()  # 插入失败回滚事务
            raise
    else:
        print("DataFrame为空，无需插入数据")

    # 事务提交与连接关闭（收尾逻辑，避免资源泄漏）
    try:
        conn.commit()
        print(f"表 {table_name} 数据导入事务已提交")
    except Exception as e:
        print(f"事务提交失败: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
        print(f"数据库连接已关闭（表：{table_name}）")



# def import_data_with_cursor(df, table_name, table_comment=None, column_comments=None,
#                             append_data=False, update_columns=True, longtext_columns=None, primary_keys=None):
#     """
#     将 DataFrame 数据导入到 MySQL 表中，确保主键能正确更新为新列。
#     """
#     # 初始化数据库连接
#     conn = pymysql.connect(
#         host='10.177.58.100',
#         user='root',
#         password='edac123456',
#         database='scdd_db',
#         port=1106
#     )
#     cursor = conn.cursor()
#
#     # 处理可选参数默认值
#     longtext_columns = longtext_columns or []
#     primary_keys = primary_keys or []
#     target_pk_set = set(primary_keys)  # 目标主键集合（用于对比）
#
#     # 验证主键有效性
#     if primary_keys:
#         # 检查主键列是否存在
#         invalid_keys = [key for key in primary_keys if key not in df.columns]
#         if invalid_keys:
#             raise ValueError(f"主键列不存在于DataFrame中: {', '.join(invalid_keys)}")
#
#         # 检查数据中是否有NULL值
#         null_check = df[primary_keys].isnull().any()
#         null_columns = null_check[null_check].index.tolist()
#         if null_columns:
#             raise ValueError(f"主键列包含NULL值，无法设置主键: {', '.join(null_columns)}")
#
#     # 数据类型映射
#     dtype_mapping = {
#         'int64': 'INT',
#         'float64': 'FLOAT',
#         'datetime64[ns]': 'DATETIME',
#         'object': 'TEXT'
#     }
#
#     # 检查表是否存在
#     cursor.execute("""
#         SELECT COUNT(*) FROM information_schema.tables
#         WHERE table_schema = DATABASE() AND table_name = %s
#     """, (table_name,))
#     table_exists = cursor.fetchone()[0] > 0
#
#     if not table_exists:
#         # 新建表逻辑（与之前一致）
#         columns = []
#         for col in df.columns:
#             dtype = str(df[col].dtype)
#             sql_type = 'TEXT'
#
#             if col in primary_keys:
#                 sql_type = 'VARCHAR(255) NOT NULL'
#             elif col in longtext_columns:
#                 sql_type = 'LONGTEXT'
#             else:
#                 for key, value in dtype_mapping.items():
#                     if key in dtype:
#                         sql_type = value
#                         break
#
#             col_comment = f" COMMENT '{column_comments[col]}'" if (column_comments and col in column_comments) else ""
#             columns.append(f'`{col}` {sql_type}{col_comment}')
#
#         primary_key_sql = f", PRIMARY KEY (`{('`,`'.join(primary_keys))}`)" if primary_keys else ""
#         table_comment_sql = f" COMMENT='{table_comment}'" if table_comment else ""
#
#         create_sql = f"""
#             CREATE TABLE `{table_name}` (
#                 {', '.join(columns)}{primary_key_sql}
#             ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4{table_comment_sql}
#         """
#         try:
#             cursor.execute(create_sql)
#             print(f"成功创建表 {table_name}")
#             if primary_keys:
#                 print(f"已设置主键: {', '.join(primary_keys)}")
#         except Exception as e:
#             if "already exists" in str(e).lower():
#                 print(f"表 {table_name} 已存在，继续执行")
#                 table_exists = True
#             else:
#                 print(f"创建表失败: {e}")
#                 raise
#
#     else:
#         print(f"表 {table_name} 已存在，继续执行")
#
#         if update_columns:
#             # 获取当前表列
#             cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
#             current_columns = [row[0] for row in cursor.fetchall()]
#
#             # 添加新列（如station_no1）
#             new_columns = [col for col in df.columns if col not in current_columns]
#             for col in new_columns:
#                 dtype = str(df[col].dtype)
#                 sql_type = 'TEXT'
#
#                 if col in primary_keys:
#                     sql_type = 'VARCHAR(255) NOT NULL'
#                 elif col in longtext_columns:
#                     sql_type = 'LONGTEXT'
#                 else:
#                     for key, value in dtype_mapping.items():
#                         if key in dtype:
#                             sql_type = value
#                             break
#
#                 col_comment = f" COMMENT '{column_comments[col]}'" if (column_comments and col in column_comments) else ""
#                 try:
#                     cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{col}` {sql_type}{col_comment}")
#                     print(f"添加列 {col} 成功")
#                 except Exception as e:
#                     print(f"添加列 {col} 失败: {e}")
#
#             # 删除多余列
#             drop_columns = [col for col in current_columns if col not in df.columns]
#             for col in drop_columns:
#                 try:
#                     cursor.execute(f"ALTER TABLE `{table_name}` DROP COLUMN `{col}`")
#                     print(f"删除列 {col} 成功")
#                 except Exception as e:
#                     print(f"删除列 {col} 失败: {e}")
#
#         # 主键列类型修正（确保VARCHAR(255)且非空）
#         if primary_keys:
#             for col in primary_keys:
#                 cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (col,))
#                 col_info = cursor.fetchone()
#                 if col_info:
#                     current_type = col_info[1].upper()
#                     if ('TEXT' in current_type or 'BLOB' in current_type) or 'NOT NULL' not in current_type:
#                         try:
#                             cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` VARCHAR(255) NOT NULL")
#                             print(f"主键列 {col} 类型修正为 VARCHAR(255) NOT NULL")
#                         except Exception as e:
#                             print(f"修正主键列 {col} 失败: {e}")
#                             raise
#
#         # 处理LONGTEXT列
#         for col in longtext_columns:
#             if col in df.columns:
#                 try:
#                     cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` LONGTEXT")
#                     print(f"列 {col} 设为 LONGTEXT 成功")
#                 except Exception as e:
#                     print(f"设置 {col} 为 LONGTEXT 失败: {e}")
#
#         # 处理主键设置（核心优化部分）
#         if primary_keys:
#             # 获取当前数据库名
#             cursor.execute("SELECT DATABASE()")
#             current_db = cursor.fetchone()[0]
#
#             # 检查当前是否有主键
#             cursor.execute("""
#                 SELECT COUNT(*) FROM information_schema.table_constraints
#                 WHERE table_schema = %s AND table_name = %s AND constraint_type = 'PRIMARY KEY'
#             """, (current_db, table_name))
#             has_primary_key = cursor.fetchone()[0] > 0
#             print(f"当前表是否有主键: {has_primary_key}")  # 新增日志
#
#             # 获取当前主键列
#             current_pk = []
#             if has_primary_key:
#                 cursor.execute("""
#                     SELECT k.column_name FROM information_schema.table_constraints t
#                     JOIN information_schema.key_column_usage k
#                         ON t.constraint_name = k.constraint_name
#                         AND t.table_schema = k.table_schema
#                         AND t.table_name = k.table_name
#                     WHERE t.table_schema = %s AND t.table_name = %s AND t.constraint_type = 'PRIMARY KEY'
#                 """, (current_db, table_name))
#                 current_pk = [row[0] for row in cursor.fetchall()]
#             current_pk_set = set(current_pk)
#             print(f"当前主键列: {current_pk}, 目标主键列: {primary_keys}")  # 新增日志
#
#             # 核心优化1：强制判断主键是否需要更新（即使查询结果异常）
#             need_update_pk = False
#             if not has_primary_key:
#                 need_update_pk = True  # 无主键时需要设置
#             elif current_pk_set != target_pk_set:
#                 need_update_pk = True  # 主键不一致时需要更新
#             # 特殊场景：目标主键包含新列（如station_no1）时强制更新
#             elif not target_pk_set.issubset(current_pk_set):
#                 need_update_pk = True
#
#             print(f"是否需要更新主键: {need_update_pk}")  # 新增日志
#
#             # 主键不匹配时删除旧主键
#             if need_update_pk and has_primary_key:
#                 try:
#                     cursor.execute(f"ALTER TABLE `{table_name}` DROP PRIMARY KEY")
#                     print(f"已删除旧主键: {', '.join(current_pk)}")
#                     has_primary_key = False  # 标记为无主键
#                 except Exception as e:
#                     print(f"删除旧主键失败: {e}")
#                     raise
#
#             # 提前清空表数据（如果需要）
#             # if not append_data:
#             #     try:
#             #         cursor.execute(f"TRUNCATE TABLE `{table_name}`")
#             #         print(f"提前清空表 {table_name} 数据，确保无NULL值干扰主键设置")
#             #     except Exception as e:
#             #         print(f"提前清空表失败: {e}")
#             #         raise
#             if not append_data:
#                 try:
#                     cursor.execute(f"TRUNCATE TABLE `{table_name}`")
#                     print(f"提前清空表 {table_name} 数据（无论是否设置主键）")
#                 except Exception as e:
#                     print(f"提前清空表失败: {e}")
#                     raise
#
#             # 设置新主键
#             if need_update_pk:
#                 # 再次确保主键列类型正确
#                 for col in primary_keys:
#                     cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (col,))
#                     col_info = cursor.fetchone()
#                     if col_info and ('VARCHAR(255)' not in col_info[1].upper() or 'NOT NULL' not in col_info[1].upper()):
#                         try:
#                             cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` VARCHAR(255) NOT NULL")
#                             print(f"强制修正 {col} 为 VARCHAR(255) NOT NULL")
#                         except Exception as e:
#                             print(f"强制修正 {col} 失败: {e}")
#                             raise
#
#                 # 创建新主键
#                 try:
#                     cursor.execute(f"ALTER TABLE `{table_name}` ADD PRIMARY KEY (`{('`,`'.join(primary_keys))}`)")
#                     print(f"成功设置新主键: {', '.join(primary_keys)}")
#                 except Exception as e:
#                     print(f"设置新主键失败: {e}")
#                     raise
#
#     # 更新表注释
#     if table_comment:
#         try:
#             cursor.execute(f"ALTER TABLE `{table_name}` COMMENT = '{table_comment}'")
#             print(f"表 {table_name} 注释更新成功")
#         except Exception as e:
#             print(f"更新表注释失败: {e}")
#
#     # 更新列注释
#     if column_comments:
#         for col, comment in column_comments.items():
#             cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (col,))
#             if cursor.fetchone():
#                 try:
#                     cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
#                     create_sql = cursor.fetchone()[1]
#                     match = re.search(f"`{col}`\\s+([^\\s,]+)", create_sql)
#                     if match:
#                         col_type = match.group(1)
#                         if col in primary_keys and 'NOT NULL' not in col_type:
#                             col_type += ' NOT NULL'
#                         cursor.execute(f"""
#                             ALTER TABLE `{table_name}` MODIFY COLUMN `{col}` {col_type} COMMENT '{comment}'
#                         """)
#                         print(f"列 {col} 注释更新成功")
#                 except Exception as e:
#                     print(f"更新 {col} 注释失败: {e}")
#
#     # 插入数据
#     if not df.empty:
#         # 处理长文本列
#         for col in longtext_columns:
#             if col in df.columns:
#                 df[col] = df[col].apply(
#                     lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else str(x)
#                 )
#
#         # 对齐表列和数据列
#         cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
#         table_cols = [row[0] for row in cursor.fetchall()]
#         df_insert = df.reindex(columns=table_cols, fill_value=None)
#
#         # 生成插入语句
#         cols_str = ', '.join([f'`{col}`' for col in table_cols])
#         placeholders = ', '.join(['%s'] * len(table_cols))
#         insert_sql = f"INSERT INTO `{table_name}` ({cols_str}) VALUES ({placeholders})"
#
#         # 处理数据（确保主键列无NULL）
#         data = []
#         for row in df_insert.values:
#             processed = []
#             for i, x in enumerate(row):
#                 col_name = table_cols[i]
#                 if col_name in primary_keys and pd.isna(x):
#                     processed.append('')  # 替换为非NULL值
#                 elif isinstance(x, (list, dict)):
#                     processed.append(json.dumps(x, ensure_ascii=False))
#                 elif pd.isna(x):
#                     processed.append(None)
#                 else:
#                     processed.append(x)
#             data.append(tuple(processed))
#
#         # 执行插入
#         try:
#             cursor.executemany(insert_sql, data)
#             print(f"成功导入 {len(data)} 行数据到 {table_name}")
#         except Exception as e:
#             print(f"数据导入失败: {e}")
#             raise
#
#     # 提交并关闭连接
#     conn.commit()
#     cursor.close()
#     conn.close()
#

##旧函数




# def import_data_with_cursor(df, table_name, table_comment=None, column_comments=None,
#                             append_data=False, update_columns=True):
#     #     创建链接
#     conn = pymysql.connect(
#         host='192.168.0.223',  # 数据库地址
#         user='root',  # 用户名
#         password='edac123456',  # 密码
#         database='scdd_db',  # 数据库名
#         port=1106  # 端口
#     )
#     cursor = conn.cursor()  # 创建游标对象
#     """
#     将 DataFrame 数据导入到 MySQL 表中，自动处理表创建和注释。
#
#     参数:
#         df: pandas DataFrame, 要导入的数据
#         table_name: str, 目标表名
#         cursor: MySQL 游标对象
#         table_comment: str, 可选，表注释
#         column_comments: dict, 可选，列注释 {列名: 注释}
#         append_data: bool, 可选，True表示追加数据，False表示覆盖数据
#         update_columns: bool, 可选，True表示更新表结构以匹配DataFrame的列
#     """
#
#     # 定义数据类型映射
#     dtype_mapping = {
#         'int64': 'INT',
#         'float64': 'FLOAT',
#         'datetime64[ns]': 'DATETIME',
#         'object': 'TEXT',
#         'chart_data': 'LONGTEXT'  # 特别处理 chart_data 列
#     }
#
#     # 检查表是否存在
#     cursor.execute(f"""
#         SELECT COUNT(*)
#         FROM information_schema.tables
#         WHERE table_schema = DATABASE() AND table_name = '{table_name}';
#     """)
#     table_exists = cursor.fetchone()[0] > 0
#
#     if not table_exists:
#         # 创建表
#         columns = []
#         for col in df.columns:
#             dtype = str(df[col].dtype)
#             # 确定 SQL 数据类型
#             sql_type = 'TEXT'  # 默认类型
#             for key, value in dtype_mapping.items():
#                 if key in dtype or (key == 'chart_data' and col == 'chart_data'):
#                     sql_type = value
#                     break
#
#             # 添加列注释
#             col_comment = ""
#             if column_comments and col in column_comments:
#                 col_comment = f" COMMENT '{column_comments[col]}'"
#
#             columns.append(f'`{col}` {sql_type}{col_comment}')
#
#         # 添加表注释
#         table_comment_sql = f" COMMENT='{table_comment}'" if table_comment else ""
#
#         create_table_sql = f"""
#             CREATE TABLE `{table_name}` (
#                 {', '.join(columns)}
#             ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4{table_comment_sql};
#         """
#         try:
#             cursor.execute(create_table_sql)
#             print(f"成功创建表 {table_name}")
#         except Exception as e:
#             # 捕获错误并检查是否是表已存在的错误
#             if "Table '{}' already exists".format(table_name) in str(e):
#                 print(f"表 {table_name} 已存在，继续执行数据导入")
#                 table_exists = True  # 设置标志为True，继续执行导入
#             else:
#                 print(f"创建表失败: {e}")
#                 raise
#     else:
#         print(f"表 {table_name} 已存在，继续执行数据导入")
#
#         # 如果需要更新列结构
#         if update_columns:
#             # 获取当前表的列
#             cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
#             current_columns = [row[0] for row in cursor.fetchall()]
#
#             # 添加新列
#             new_columns = [col for col in df.columns if col not in current_columns]
#             for col in new_columns:
#                 dtype = str(df[col].dtype)
#                 sql_type = 'TEXT'  # 默认类型
#                 for key, value in dtype_mapping.items():
#                     if key in dtype or (key == 'chart_data' and col == 'chart_data'):
#                         sql_type = value
#                         break
#
#                 col_comment = ""
#                 if column_comments and col in column_comments:
#                     col_comment = f" COMMENT '{column_comments[col]}'"
#
#                 try:
#                     cursor.execute(f"""
#                         ALTER TABLE `{table_name}`
#                         ADD COLUMN `{col}` {sql_type}{col_comment};
#                     """)
#                     print(f"成功添加列 {col} 到表 {table_name}")
#                 except Exception as e:
#                     print(f"添加列 {col} 失败: {e}")
#
#             # 删除不存在的列
#             columns_to_drop = [col for col in current_columns if col not in df.columns]
#             for col in columns_to_drop:
#                 try:
#                     cursor.execute(f"""
#                         ALTER TABLE `{table_name}`
#                         DROP COLUMN `{col}`;
#                     """)
#                     print(f"成功删除列 {col} 从表 {table_name}")
#                 except Exception as e:
#                     print(f"删除列 {col} 失败: {e}")
#
#     # 表存在的情况下，确保 chart_data 列足够大
#     if 'chart_data' in df.columns:
#         try:
#             cursor.execute(f"""
#                 ALTER TABLE `{table_name}`
#                 MODIFY COLUMN `chart_data` LONGTEXT;
#             """)
#         except Exception as e:
#             print(f"修改 chart_data 列失败: {e}")
#
#     # 更新表注释
#     if table_comment:
#         try:
#             cursor.execute(f"""
#                 ALTER TABLE `{table_name}`
#                 COMMENT = '{table_comment}';
#             """)
#             print(f"成功更新表 {table_name} 的注释")
#         except Exception as e:
#             print(f"更新表注释失败: {e}")
#
#     # 更新列注释
#     if column_comments:
#         for col, comment in column_comments.items():
#             # 检查列是否存在
#             cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE '{col}'")
#             if cursor.fetchone():
#                 try:
#                     # 获取列的当前定义
#                     cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
#                     create_table_sql = cursor.fetchone()[1]
#
#                     # 查找列的当前类型
#                     import re
#                     pattern = re.compile(f"`{col}`\\s+([^\\s,]+)")
#                     match = pattern.search(create_table_sql)
#                     if match:
#                         column_type = match.group(1)
#                         # 更新列注释
#                         cursor.execute(f"""
#                             ALTER TABLE `{table_name}`
#                             MODIFY COLUMN `{col}` {column_type} COMMENT '{comment}';
#                         """)
#                         print(f"成功更新列 {col} 的注释")
#                 except Exception as e:
#                     print(f"更新列 {col} 注释失败: {e}")
#
#     # 如果选择覆盖数据且DataFrame不为空，则先清空表
#     if not append_data and not df.empty:
#         try:
#             cursor.execute(f"TRUNCATE TABLE `{table_name}`")
#             print(f"已清空表 {table_name} 中的数据")
#         except Exception as e:
#             print(f"清空表失败: {e}")
#             raise
#
#     # 插入数据
#     if not df.empty:
#         # 处理 chart_data 列，确保是字符串格式
#         if 'chart_data' in df.columns:
#             df['chart_data'] = df['chart_data'].apply(
#                 lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else str(x)
#             )
#
#         # 获取表的当前列
#         cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
#         table_columns = [row[0] for row in cursor.fetchall()]
#
#         # 确保DataFrame的列与表的列匹配
#         df_to_insert = df.copy()
#         # 添加表中存在但DataFrame中不存在的列
#         for col in table_columns:
#             if col not in df_to_insert.columns:
#                 df_to_insert[col] = None
#
#         # 只选择表中存在的列
#         df_to_insert = df_to_insert[table_columns]
#
#         # 准备插入语句
#         columns = ', '.join([f'`{col}`' for col in table_columns])
#         placeholders = ', '.join(['%s'] * len(table_columns))
#         insert_sql = f"""
#             INSERT INTO `{table_name}` ({columns})
#             VALUES ({placeholders});
#         """
#
#         # 处理数据中的 None 值
#         data = []
#         for row in df_to_insert.values:
#             processed_row = []
#             for x in row:
#                 if isinstance(x, (list, dict)):
#                     processed_row.append(json.dumps(x, ensure_ascii=False))
#                 elif pd.isna(x):
#                     processed_row.append(None)
#                 else:
#                     processed_row.append(x)
#             data.append(tuple(processed_row))
#
#         try:
#             cursor.executemany(insert_sql, data)
#             print(f"成功导入 {len(data)} 行数据到 {table_name}")
#         except Exception as e:
#             print(f"数据导入失败: {e}")
#             raise
#     conn.commit()  # 提交后，锁释放，事务结束
#     cursor.close()  # 关闭游标
#     conn.close()  # 关闭数据库连接
