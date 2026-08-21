[industryAndProvincialCompany.py](./modules/industryAndProvincialCompany.py)
请你查看一下数据表的数据生成过程，其中表中的部分指标是否都有与金额有关的指标？另外还有没有漏下的表
dp_industrial_unit_TopKeyMetrics1、dp_main_unit_TopKeyMetrics1
dp_industrial_unit_Left_Charge_Inco_Qy、dp_main_unit_Left_Charge_Inco_Qy
dp_industrial_unit_Left_Charge_Inco_Yy、dp_main_unit_Left_Charge_Inco_Yy
dp_industrial_unit_Left_Charge_Inco_Zd、dp_main_unit_Left_Charge_Inco_Zd
dp_industrial_unit_interconnected、dp_unit_interconnected、
dp_industrial_unit_Left_Charge_Inco_Qy、dp_main_unit_Left_Charge_Inco_Qy
dp_industrial_unit_Left_Charge_Inco_Yy、dp_main_unit_Left_Charge_Inco_Yy
dp_industrial_unit_Left_Charge_Inco_Zd、dp_main_unit_Left_Charge_Inco_Zd
dp_industrial_unit_interconnected、dp_unit_interconnected

1、顶部指标和联动表的年度订单被固定筛选为 2025，没有使用动态变量 year。当统计月份不是 2025
年时，“本年累计充电收入”会错误。[industryAndProvincialCompany.py (line 388)](/Users/zhangshuai/project_all/edac/业务五部/SCDDproject/modules/industryAndProvincialCompany.py:388)、[联动数据处 (line 3109)](/Users/zhangshuai/project_all/edac/业务五部/SCDDproject/modules/industryAndProvincialCompany.py:3109)

2、联动表 chart4 实际通过 pct_change()
计算环比，但图例写的是“同比增长率”。[industryAndProvincialCompany.py (line 3493)](/Users/zhangshuai/project_all/edac/业务五部/SCDDproject/modules/industryAndProvincialCompany.py:3493)

3、两张 Inco_Zd 直接通过 .values[0]读取当月和上年同期收入。缺少对应月份数据时会抛出索引异常，上年同期收入为 0
时同比计算也会出现除零问题。[industryAndProvincialCompany.py (line 2946)](/Users/zhangshuai/project_all/edac/业务五部/SCDDproject/modules/industryAndProvincialCompany.py:2946)

产业单位 = charge_station.merchant_nature in ("产业单位","综合能源")
省公司 = charge_station.merchant_nature = "电力公司"、

功率利用率 这个指标 不再使用 现有的计算规则，而是从 数据库中直接读取，读出来即用，capacity_utilization_rate 字段即为 功率利用率
其中
sql = """
select pue.*,cs.* from dp_pue_capacity_utilization pue left join charge_station cs
on pue.station_code = cs.station_id
where cs.merchant_nature in ("产业单位","综合能源","电力公司")
"

其中 dp_pue_capacity_utilization 表的数据库存在

连接地址：
192.168.0.217
端口：
1106
数据库名称：
scdd_db_v2
用户名
root
密码
edac123456  
你可以连上看看
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

改为一个更简洁的版本，从 scdd_rec_rules中 反编译出 清分规则，插入到 dp_profit_sharing1 中，
其中dp_profit_sharing1的字段为：CREATE TABLE `dp_profit_sharing1` (
`station_no` varchar(255) NOT NULL COMMENT '站点编号',
`merchant_name` text COMMENT '商户名称',
`ddProfitRation` text COMMENT '清分规则',
`ddProfitRationP` text COMMENT '图片地址',
PRIMARY KEY (`station_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站点清分规则码表';

`ddProfitRationP` text COMMENT '图片地址',要空着不填写，把清分规则填入到ddProfitRation中，如果改站点/商户没有清分规则就用‘备注’

# 直接生成清分规则表

## Summary

只修改 `modules/socialCharger_new.py`，在现有查询 `dp_profit_sharing1` 之前直接完成规则读取和写入，不增加额外模块或公共函数。

## Implementation

1. 执行 `SELECT`，从 `scdd_rec_rules` 读取：
    - `rules_id`
    - `merchant_id`
    - `biz_mode`
    - `profit_detail`

2. 解析 `profit_detail`：
    - 从 `stationNoS` 找到规则对应站点。
    - 将比例、时间节点、年度阶梯等转换为可读清分规则。
    - 有清分规则时使用反编译规则。
    - 没有清分规则时使用 JSON 的 `remark`。
    - 删除 `remark` 开头的 `备注：` 和换行。
    - 两者都没有时使用 `备注`。

3. 直接批量执行：

```sql
INSERT INTO dp_profit_sharing1
    (station_no, merchant_name, ddProfitRation, ddProfitRationP)
VALUES (%s, %s, %s, NULL) ON DUPLICATE KEY
UPDATE
    merchant_name =
VALUES (merchant_name), ddProfitRation =
VALUES (ddProfitRation), ddProfitRationP = NULL
```

4. 提交后继续执行原代码：

```python
sql = """
select station_no, ddProfitRation, ddProfitRationP
from dp_profit_sharing1;
"""
df_gz = SQL(sql)
```

## Verification

- 检查规则比例和时间档位反编译正确。
- 检查无规则站点使用清洗后的 `remark`。
- 检查 `ddProfitRationP` 始终为空。
- 检查写入提交发生在 `df_gz` 查询之前。
- 运行 Python 语法检查。


[companyWarningOverview.py](./modules/companyWarningOverview.py)


[companyWarningStations.py](./modules/companyWarningStations.py)
确认 此页面的筛选规则是否都变成了 “投运+停运”

确认筛选规则是否都变成了  charging_station.merchant_nature = '电动公司'





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
where cs.merchant_nature = '电动公司'
and JSON_UNQUOTE(JSON_EXTRACT(sr.profit_detail, '$.parkingFee')) IS NOT NULL;
"""






在OverviewTypeMonitoring页面中，存在一个bug，就是比如：近一年投资趋势等等所有的 双/三及以上 折线图。，当我 只选择一个类型时，折线图上标注的为 我选择的类型，但是我选择第二个类型后 我的数据会变成第二个类型的





那为什么 站点名称 ： 花荄镇联丰村停车场充电站 ，站编码 ：30751001700000141 在表 dp_profit_sharing1中 的数据是：
站点编号  商户名称  清分规则  图片地址
30751001700000141 米昂扬滕飞文化旅游有限公司  社会运营商暂未分成


但是 在页面上 显示的却是：图片加载失败
