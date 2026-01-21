import pymysql
from pymysql import Error


def get_db_connection():
    """
    建立数据库连接
    """
    try:
        connection = pymysql.connect(
            host='10.177.58.100',
            user='root',
            password='edac123456',
            database='scdd_db',
            port=1106,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("成功连接到数据库")
        return connection
    except Error as e:
        print(f"连接数据库时出错: {e}")
        return None


def get_dp_tables(connection):
    """
    获取所有以'dp'开头的表
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'dp%'")
            tables = [list(table.values())[0] for table in cursor.fetchall()]
        return tables
    except Error as e:
        print(f"查询表时出错: {e}")
        return []


def delete_all_dp_tables(connection, tables):
    """
    删除所有以'dp'开头的表
    """
    if not tables:
        print("没有找到以'dp'开头的表")
        return

    print("找到以下以'dp'开头的表，将全部删除:")
    for i, table in enumerate(tables, 1):
        print(f"{i}. {table}")

    # 确认删除
    confirm = input("\n确认要删除以上所有表吗？此操作不可逆！(输入'YES'确认，其他键取消): ")
    if confirm != 'YES':
        print("操作已取消")
        return

    success_count = 0
    fail_count = 0

    try:
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f"DROP TABLE {table}")
                    print(f"已成功删除表: {table}")
                    success_count += 1
                except Error as e:
                    print(f"删除表 {table} 时出错: {e}")
                    fail_count += 1

        # 提交事务
        connection.commit()

    except Error as e:
        print(f"执行删除操作时出错: {e}")
        # 发生错误时回滚
        connection.rollback()

    print(f"\n删除操作完成: 成功 {success_count} 个, 失败 {fail_count} 个")


def main():
    # 建立数据库连接
    connection = get_db_connection()
    if not connection:
        return

    try:
        # 获取所有以'dp'开头的表
        all_tables = get_dp_tables(connection)

        # 直接删除所有表
        delete_all_dp_tables(connection, all_tables)

    except Exception as e:
        print(f"程序执行过程中发生错误: {e}")
    finally:
        if connection:
            connection.close()
            print("数据库连接已关闭")


if __name__ == "__main__":
    main()