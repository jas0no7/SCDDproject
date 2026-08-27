#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import pymysql

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# MySQL配置
DB_CONFIG = {
    "host": "10.177.58.100",
    "port": 1106,
    "user": "root",
    "password": "edac123456",
    "database": "scdd_db",
    "charset": "utf8mb4",
}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


# 容量利用率
CREATE_CAPACITY_UTILIZATION_SQL = """
CREATE TABLE IF NOT EXISTS `dp_station_tech_upgrade_mapping` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `old_code` VARCHAR(50) NOT NULL COMMENT '技改前编号',
  `old_name` VARCHAR(200) NOT NULL COMMENT '技改前名称',
  `new_code` VARCHAR(50) NOT NULL COMMENT '技改后编号',
  `new_name` VARCHAR(200) NOT NULL COMMENT '技改后名称',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_old_code` (`old_code`),
  KEY `idx_new_code` (`new_code`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='充电站技改映射表';
"""


CREATE_TABLE_SQLS = [
    CREATE_CAPACITY_UTILIZATION_SQL,
]


def create_tables(conn):
    with conn.cursor() as cursor:
        for sql in CREATE_TABLE_SQLS:
            cursor.execute(sql)
    conn.commit()


def main():
    conn = None
    try:
        conn = get_connection()
        create_tables(conn)
        logger.info("=" * 50)
        logger.info("建表任务完成！")
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("建表任务失败")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
