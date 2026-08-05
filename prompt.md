[typeMonitoringOverview.py]('./modules/typeMonitoringOverview.py')

请你查看这个py文件下的 这三张表的数据的生成过程
dp_scdd_Infrastructure & dp_Operational_status & dp_operations_chart
当最后插入的数据字段 含有“功率利用率”时，请抛弃前面广功率利用率的计算逻辑，转而使用SELECT
      pue.*,
      cs.station_category
    FROM dp_pue_capacity_utilization pue
    LEFT JOIN charging_station cs
      ON pue.station_code COLLATE utf8mb4_unicode_ci 
      = cs.station_no COLLATE utf8mb4_unicode_ci
    WHERE pue.data_category = '四川电动'
其中这个表中的capacity_utilization_rate 字段即为 功率利用率无需再计算 即拿即用
的建表语句如下： CREATE TABLE IF NOT EXISTS `dp_pue_capacity_utilization` (
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
    `time_utilization_rate` DECIMAL(9, 6) NULL COMMENT '时长利用率',
    `capacity_utilization_rate` DECIMAL(9, 6) NULL COMMENT '容量利用率',
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




cs.merchant_nature = "电动公司"

涉及到功率利用率的 ：
四川电动旗下充电基础设施建设现状 dp_scdd_Infrastructure 、 运营情况 dp_Operational_status 、近一年运营趋势 dp_operations_chart






