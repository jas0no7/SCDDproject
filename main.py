
import threading
import argparse
import re

import modules.config as config

from loguru import logger
from modules.cityPublic_typeMonitoring import runcityPublic_typeMonitoring
from modules.keyStationExternalCompetition import runkeyStationExternalCompetition
from modules.techUpgradeStation import runtechUpgradeStation
from modules.techUpgradePaybackForecast import runtechUpgradePaybackForecast
from modules.typeMonitoringOverview import runtypeMonitoringOverview
from modules.companyWarningStations import runcompanyWarningStations
from modules.companyWarningOverview import runcompanyWarningOverview
from modules.industryAndProvincialCompany import runindustryAndProvincialCompany
from modules.keyStationInternalCompetition import runkeyStationInternalCompetition
from modules.panoramaOverview import runpanoramaOverview
from modules.socialCharger import runsocialCharger

import os
import logging
from datetime import datetime

# 创建日志目录
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# 获取当前时间作为日志文件名的一部分（精确到秒）
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file_path = os.path.join(log_dir, f"scdd_{timestamp}.log")

# 配置日志写入文件 + 控制台
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(threadName)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),  # 写入文件（带时间戳）
        logging.StreamHandler()  # 同时输出到控制台
    ]
)


def run():
    # 定义所有线程
    threads = [
        threading.Thread(target=runtypeMonitoringOverview, name="类型监测概览"),
        threading.Thread(target=runtechUpgradeStation, name="技改站点"),
        threading.Thread(target=runcityPublic_typeMonitoring, name="类型监测-城市公共"),
        threading.Thread(target=runtechUpgradePaybackForecast, name="技改站点回本周期预测"),
        threading.Thread(target=runkeyStationExternalCompetition, name="重点站点外部竞争"),
        threading.Thread(target=runpanoramaOverview, name="全景概览"),###通过
        threading.Thread(target=runsocialCharger, name="社会桩"),#通过
        threading.Thread(target=runindustryAndProvincialCompany, name="产业及省公司接入"),###通过
        threading.Thread(target=runcompanyWarningStations, name="公司预警-站点"),###通过
        threading.Thread(target=runcompanyWarningOverview, name="公司预警-概览"),## 通过
        threading.Thread(target=runkeyStationInternalCompetition, name="重点站点内部竞争"),##通过
    ]

    # 启动所有线程
    for t in threads:
        t.start()

    # 等待所有线程执行完毕
    for t in threads:
        t.join()

    logger.success("所有程序执行完毕")

def parse_report_month(value):
    """校验命令行传入的分析月份。"""
    if not re.fullmatch(r'\d{6}', value) or not 1 <= int(value[4:]) <= 12 or int(value[:4]) == 0:
        raise argparse.ArgumentTypeError('月份必须为有效的 YYYYMM 格式，例如 202609')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='运行四川电动数据分析任务')
    parser.add_argument('month', nargs='?', type=parse_report_month,
                        help='分析月份，格式为 YYYYMM；不传则使用上个月')
    args = parser.parse_args()
    config.CUSTOM_MONTH = args.month
    run()
