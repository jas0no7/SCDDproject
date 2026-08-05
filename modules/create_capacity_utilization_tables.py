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
    "host": "192.168.0.217",
    "port": 1106,
    "user": "root",
    "password": "edac123456",
    "database": "scdd_db_v2",
    "charset": "utf8mb4",
}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


# 容量利用率
CREATE_CAPACITY_UTILIZATION_SQL = """
CREATE TABLE IF NOT EXISTS `dp_pue_capacity_utilization` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    `first_level_owner` VARCHAR(100) NOT NULL COMMENT '一级产权',
    `second_level_owner` VARCHAR(150) NOT NULL COMMENT '二级产权',
    `third_level_owner` VARCHAR(150) NOT NULL COMMENT '三级产权',
    `organization_type` VARCHAR(50) NOT NULL COMMENT '单位类型',
    `province` VARCHAR(50) NOT NULL COMMENT '行政省份',
    `city` VARCHAR(50) NOT NULL COMMENT '行政地市',
    `district_county` VARCHAR(50) NOT NULL COMMENT '行政区县',
    `station_code` VARCHAR(32) NOT NULL COMMENT '站编码',
    `station_name` VARCHAR(200) NOT NULL COMMENT '站名称',
    `station_address` VARCHAR(500) NOT NULL COMMENT '站地址',
    `commissioned_at` DATETIME NOT NULL COMMENT '站投运时间',
    `station_type` VARCHAR(50) NOT NULL COMMENT '站类型',
    `total_operating_hours` DECIMAL(14, 2) NOT NULL COMMENT '运行总时长(小时)',
    `total_charging_hours` DECIMAL(14, 2) NULL COMMENT '充电总时长(小时)',
    `time_utilization_rate` DECIMAL(9, 6) NULL COMMENT '时长利用率(%)',
    `capacity_utilization_rate` DECIMAL(9, 6) NULL COMMENT '容量利用率(%)',
    `total_capacity_kwh` DECIMAL(18, 3) NOT NULL COMMENT '总容量(千瓦时)',
    `total_charging_energy_kwh` DECIMAL(18, 3) NULL COMMENT '总充电量(千瓦时)',
    `data_category` VARCHAR(50) NOT NULL COMMENT '来源分类',
    `month` VARCHAR(6) NOT NULL COMMENT '月份',
    PRIMARY KEY (`id`),
    KEY `idx_station_code` (`station_code`),
    KEY `idx_region` (`province`, `city`, `district_county`),
    KEY `idx_commissioned_at` (`commissioned_at`),
    KEY `idx_data_category` (`data_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='容量利用率-定期维护';
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
