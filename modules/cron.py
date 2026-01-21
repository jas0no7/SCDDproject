import os
import sys
import json
import time
import datetime
import jsonpatch
import traceback
import threading

import requests
from loguru import logger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.blocking import BlockingScheduler

basa_path = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.pop(0)
sys.path.insert(0, basa_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.production')

from services import sql_query, services
from services.kafka_tools import kafka_producer
from settings.config import DATA_TYPE, DW_LAYOUT, ES_CONF
from common.production_es import local_es_helper
from common.redis_db import redis_connection_pool

# logger.add(
#     sink="./logs/cron.log",
#     level="INFO",
#     format="{time} | {level} | {message}",
#     filter=lambda record: record["extra"]["name"] == "cron_log",
#     enqueue=True,
#     rotation="00:00",
#     retention="3 days",
#     encoding="utf-8",
#     backtrace=True,
#     diagnose=True,
# )


# 根据entity_id在es种删除数据
def es_delete_by_entity_id(entity_id):
    delete_query = {
        "query": {
            "bool": {
                "must": [{"term": {"entity_id": entity_id}}]
            }
        }
    }
    local_es_helper.delete(index=ES_CONF.get('index'), body=delete_query)


# 根据entity_id在es写入或更新数据
def es_add_and_update_entity(insert_query, update_query, metadata, dataset_name_c):
    search_query = {"query": {"bool": {"must": [{"term": {"entity_id": insert_query["entity_id"]}}]}}}

    # 获取插入到向量库的数据
    # 加载JSON数据
    data = metadata

    # 提取字段名称或注释，如果注释为空则使用字段名
    field_comments_or_names = [col["COLUMN_COMMENT"] if col["COLUMN_COMMENT"] else col["COLUMN_NAME"] for col in data["COLUMN"]]

    # 创建字段字符串
    fields_str = "、".join(field_comments_or_names)

    # 表名和code
    table_name = data["TABLE_NAME"]
    table_comment = data["TABLE_COMMENT"]
    table_code = table_name.replace(' ', '_').lower()

    es_search_data = local_es_helper.search(
        index=ES_CONF.get('index'), body=search_query).get('hits', {}).get("hits", [])

    # 存在ES搜索结果，更新数据
    if es_search_data:
        es_id = es_search_data[0]['_id']
        local_es_helper.update(index=ES_CONF.get('index'), id=es_id, body=update_query)
    else:
        result = local_es_helper.insert(index=ES_CONF.get('index'), body=insert_query)
        es_id = result.get("_id", "")

        # 写入元数据到Kafka，通过ChatGPT生成概括内容
        kafka_metadata = {
            "entity_id": insert_query["entity_id"],
            "entity_code": insert_query["code"],
            "es_index": result.get("_index", ""),
            "es_id": es_id,
            "entity_metadata": metadata,
        }
        kafka_producer(kafka_metadata)


# 根据entity_id删除关联数据
def delete_entity_rel(entity_id: int, operate_es=True):
    """
    删除已有的数据实体信息及关联信息
    @param entity_id: 实体id
    @param operate_es: 操作ES数据，default=True
    @return:
    """
    try:
        sql_query.delete_entity(entity_id)
        sql_query.delete_entity_lineage(entity_id)
        sql_query.delete_entity_check(entity_id)

        # ES 内容删除
        if operate_es:
            es_delete_by_entity_id(entity_id)

    except Exception as e:
        error_data = {
            "status": "error",
            "app": "entity_mds_app",
            "file": "cron.py",
            "threading": threading.current_thread().name,
            "function": "delete_entity_rel",
            "data": {
                "entity_id": entity_id,
            },
            "message": traceback.format_exc()
        }
        logger.bind(name="cron_log").error(json.dumps(error_data))


# 根据entity_id更新元数据
def update_entity(
        entity: dict, dataset: dict, data_connect_conf: dict, data_domain_id: int, operate_es=True):
    """
    更新已有的数据实体信息
    @param entity: 实体信息dict
        {
            "entity_id": entity_id,
            "entity_name": entity_name,
            "entity_code": entity_code,
            "entity_tags": entity_tags,
            "create_at": create_at,
            "entity_metadata": entity_metadata
        }
    @param dataset: 数据集信息dict
        {
            "dataset_name": dataset_name,
            "data_type": data_type,
            "dw_layout": dw_layout,
        }
    @param data_connect_conf: 数据库连接信息
    @param data_domain_id: 数据域id
    @param operate_es: 操作ES数据，default=True
    @return:
    """
    entity_id = entity.get('entity_id', 0)
    entity_name = entity.get('entity_name', '')
    entity_code = entity.get('entity_code', '')
    entity_tags = entity.get('entity_tags', [])
    create_at = entity.get('create_at').strftime('%Y-%m-%d %H:%M:%S')
    entity_metadata = entity.get('entity_metadata', {})

    dataset_name = dataset.get('dataset_name', '')
    data_type = dataset.get('data_type', '')
    dw_layout = dataset.get('dw_layout', '')

    # 添加分布式锁
    lock_key = f"{data_connect_conf.get('database')}_{entity_code}"
    redis_connection_pool.acquire_lock(lock_key)
    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "redis_connection_pool.acquire_lock",
        "data": {
            "lock_key": lock_key,
        },
        "message": "zookeeper Locked."
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))

    # 获取实体最新的元数据信息
    metadata = services.get_entity_data(data_connect_conf, entity_code)
    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "services.get_entity_data",
        "data": {
            "data_connect_conf": data_connect_conf,
            "entity_code": entity_code,
            "metadata": metadata,
        },
        "message": ""
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))

    if metadata:
        # 实体元数据和最新元素据的差异数据
        metadata_diff = jsonpatch.JsonPatch.from_diff(entity_metadata, metadata)

        # 智能更新（除列注释外，所有数据以最新元数据为准）
        services.column_comment_update(metadata_diff, entity_metadata, metadata)
        info_data = {
            "status": "info",
            "app": "entity_mds_app",
            "file": "cron.py",
            "threading": threading.current_thread().name,
            "function": "services.column_comment_update",
            "data": {
                "metadata": metadata,
            },
            "message": ""
        }
        logger.bind(name="cron_log").info(json.dumps(info_data))

        # 更新实体数据库中的元数据信息
        sql_query.update_entity_metadata(entity_id, metadata)
        update_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 记录之前的数据到实体历史表中
        entity_version = datetime.datetime.now().strftime('%y%m%d%H%M%S')
        sql_query.add_entity_metadata_history(entity_id, entity_version, entity_metadata)

        if data_domain_id:
            # 获取实体的数据域信息
            entity_data_domains = sql_query.get_entity_data_domain(data_domain_id)
        else:
            entity_data_domains = []

        if operate_es:
            columns_list = []
            src_columns = metadata.get("COLUMN", [])
            for item in src_columns:
                columns_list.append({
                    "code": item.get("COLUMN_NAME", ""),
                    "name": item.get("COLUMN_COMMENT", ""),
                })

            insert_query = {
                "entity_id": entity_id,
                "entity_name": entity_name,
                "code": entity_code,
                "dataset_name": dataset_name,
                "data_domain_name": entity_data_domains,
                "data_type": data_type,
                "dw_layout": dw_layout,
                "columns": columns_list,
                "tags": entity_tags,
                "record_count": metadata['TABLE_ROWS'],
                "create_at": create_at,
                "update_at": update_at,
            }

            update_query = {
                "doc": {
                    "entity_name": entity_name,
                    "code": entity_code,
                    "dataset_name": dataset_name,
                    "record_count": metadata['TABLE_ROWS'],
                    "data_domain_name": entity_data_domains,
                    "data_type": data_type,
                    "dw_layout": dw_layout,
                    "tags": entity_tags,
                    "update_at": update_at
                }
            }

            es_add_and_update_entity(insert_query, update_query, metadata)

    # 释放zookeeper分布式锁
    redis_connection_pool.release_lock(lock_key)
    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "redis_connection_pool.release_lock",
        "data": {
            "lock_key": lock_key,
        },
        "message": ""
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))


# 根据entity_id新增实体
def add_entity(entity: dict, dataset: dict, data_connect_conf: dict, operate_es=True):
    """
    新增实体逻辑
    @param entity: 实体dict
    {
        "entity_code": entity_code,
        "entity_name": entity_name,
    }
    @param dataset: 数据集dict
        {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "data_type": data_type,
        "dw_layout": dw_layout,
    }
    @param data_connect_conf: 数据库连接信息
    @param operate_es: 操作ES数据，default=True
    @return:
    """

    entity_code = entity.get('entity_code', '')
    entity_name = entity.get('entity_name', '')

    dataset_id = int(dataset.get('dataset_id', 0))
    dataset_name = dataset.get('dataset_name', '')
    data_type = dataset.get('data_type', '')
    dw_layout = dataset.get('dw_layout', '')

    # 添加分布式锁
    lock_key = f"{data_connect_conf.get('database')}_{entity_code}"
    redis_connection_pool.acquire_lock(lock_key)
    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "redis_connection_pool.acquire_lock",
        "data": {
            "lock_key": lock_key,
        },
        "message": "zookeeper Locked."
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))

    # 获取实体最新的元数据信息
    metadata = services.get_entity_data(data_connect_conf, entity_code)
    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "services.get_entity_data",
        "data": {
            "data_connect_conf": data_connect_conf,
            "entity_code": entity_code,
            "metadata": metadata,
        },
        "message": ""
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))

    if metadata:
        update_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 先检查该实体是否存在，实体存在（不考虑实体状态）就更改元数据信息，实体不存在就新增实体信息
        exist_entity = sql_query.query_entity_status_by_code(e_code=entity_code, ds_id=dataset_id)
        if exist_entity:
            entity_id = exist_entity[0]
            create_at = exist_entity[1].strftime('%Y-%m-%d %H:%M:%S')
            sql_query.update_entity_metadata(exist_entity[0], metadata)
        else:
            sql_query.insert_entity(e_name=entity_name, e_code=entity_code, ds_id=dataset_id, metadata=metadata)
            entity_id = sql_query.get_entity_id(e_code=entity_code, ds_id=dataset_id)
            create_at = update_at

        if entity_id and operate_es:
            columns_list = []
            src_columns = metadata.get("COLUMN", [])
            for item in src_columns:
                columns_list.append({
                    "code": item.get("COLUMN_NAME", ""),
                    "name": item.get("COLUMN_COMMENT", ""),
                })

            insert_query = {
                "entity_id": entity_id,
                "entity_name": entity_name,
                "code": entity_code,
                "dataset_name": dataset_name,
                "data_domain_name": [],
                "data_type": data_type,
                "dw_layout": dw_layout,
                "columns": columns_list,
                "record_count": metadata['TABLE_ROWS'],
                "create_at": create_at,
                "update_at": update_at,
            }

            update_query = {"doc": {
                "entity_name": entity_name,
                "code": entity_code,
                "dataset_name": dataset_name,
                "record_count": metadata['TABLE_ROWS'],
                "data_type": data_type,
                "dw_layout": dw_layout,
                "update_at": create_at,
            }}

            es_add_and_update_entity(insert_query, update_query, metadata)

    # 释放zookeeper分布式锁
    redis_connection_pool.release_lock(lock_key)
    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "redis_connection_pool.release_lock",
        "data": {
            "lock_key": lock_key,
        },
        "message": ""
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))


# 元数据处理逻辑
def processing_entities(dataset: dict, data_connect_conf: dict):
    """
    处理实体信息
    @param dataset: 数据集信息 dict
    {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "data_type": data_type,
        "dw_layout": dw_layout,
        "status": status,
    }
    @param data_connect_conf: 数据库连接信息 dict
    @return:
    """
    dataset_id = int(dataset.get('dataset_id', 0))

    # 获取数据库的表信息
    mysql_table = services.get_mysql_table(data_connect_conf)
    # 数据仓库平台记录当前数据集下的有效实体信息
    entity_metadata = sql_query.get_all_entity(dataset_id)
    exclude_entity_list = sql_query.get_exclude_entity_list(dataset_id)
    ext_values = [item[2] for item in exclude_entity_list]
    print(f"extracted_values={ext_values}")
    entity_id_code_dict = {}
    entity_dict = {}

    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "",
        "data": {
            "dataset": dataset,
            "data_connect_conf": data_connect_conf,
            "table_metadata len": len(mysql_table),
            "entity_metadata len": len(entity_metadata),
        },
        "message": f"{threading.current_thread().name} start."
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))

    for item in entity_metadata:
        entity_id_code_dict[item[0]] = {'code': item[2], 'status': item[7]}
        entity_dict[item[0]] = item

    # 检查数据集是否有效
    if dataset['status']:
        if mysql_table:
            # add_entities = set(mysql_table.keys()) - {_['code'] for _ in entity_id_code_dict.values()}
            add_entities = set(mysql_table.keys()) - {_['code'] for _ in entity_id_code_dict.values()} - set(ext_values)
            delete_entities = {_['code'] for _ in entity_id_code_dict.values() if _['status']} - set(mysql_table.keys())
            exist_entities = set(mysql_table.keys()) & {_['code'] for _ in entity_id_code_dict.values() if _['status']}

            info_data = {
                "status": "info",
                "app": "entity_mds_app",
                "file": "cron.py",
                "threading": threading.current_thread().name,
                "function": "",
                "data": {
                    "add_entities len": len(add_entities),
                    "delete_entities len": len(delete_entities),
                    "exist_entities len": len(exist_entities),
                },
                "message": ""
            }
            logger.bind(name="cron_log").info(json.dumps(info_data))

            for item in add_entities:
                entity = {
                    "entity_code": item,
                    "entity_name": mysql_table.get(item, ''),
                }
                add_entity(entity=entity, dataset=dataset, data_connect_conf=data_connect_conf)

            if exist_entities:
                for e_id, e_item in entity_id_code_dict.items():
                    if e_item['status'] and e_item['code'] in exist_entities:
                        entity_data = entity_dict.get(e_id, ())
                        create_at = entity_data[3]
                        entity_metadata = json.loads(entity_data[4])
                        data_domain_id = entity_data[5]
                        tags = entity_data[6].strip(',').split(',') if entity_data[6] else []
                        entity = {
                            "entity_id": e_id,
                            "entity_name": mysql_table.get(e_item['code'], ''),
                            "entity_code": e_item['code'],
                            "entity_tags": tags,
                            "create_at": create_at,
                            "entity_metadata": entity_metadata
                        }
                        update_entity(
                            entity=entity, dataset=dataset, data_connect_conf=data_connect_conf,
                            data_domain_id=data_domain_id
                        )

            if delete_entities:
                for e_id, e_item in entity_id_code_dict.items():
                    if e_item['code'] in delete_entities:
                        delete_entity_rel(e_id)
    else:
        # 数据集已删除
        for item in entity_id_code_dict.keys():
            delete_entity_rel(item)

            info_data = {
                "status": "info",
                "app": "entity_mds_app",
                "file": "cron.py",
                "threading": threading.current_thread().name,
                "function": "",
                "data": {
                    "entity_id": item,
                    "entity_code": entity_id_code_dict[item],
                },
                "message": f"删除yddw_entity(实体表)和ES(yddw_entity)中对应的元数据."
            }
            logger.bind(name="cron_log").info(json.dumps(info_data))

    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "",
        "data": {
            "dataset": dataset,
            "data_connect_conf": data_connect_conf,
            "table_metadata len": len(mysql_table),
            "entity_metadata len": len(entity_metadata),
        },
        "message": f"{threading.current_thread().name} stop."
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))


# 定时任务多线程处理
def processing_datasets():
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_timestamp = int(time.mktime(time.strptime(start_time, "%Y-%m-%d %H:%M:%S")))

    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "processing_datasets",
        "data": {
            "start_time": start_time,
            "start_timestamp": int(start_timestamp),
        },
        "message": "processing_datasets start."
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))

    sql_data = sql_query.get_all_datasets()
    if sql_data:
        for item in sql_data:
            dataset = {
                "dataset_id": item[0],
                "dataset_name": item[1],
                "data_type": DATA_TYPE.get(item[2], ''),
                "dw_layout": DW_LAYOUT.get(item[3], ''),
                "status": item[5],
            }
            data_connect_conf = json.loads(item[4])

            thread = threading.Thread(
                target=processing_entities, name=f"Thread_{item[1]}", args=(dataset, data_connect_conf)
            )
            thread.start()

    stop_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stop_timestamp = int(time.mktime(time.strptime(stop_time, "%Y-%m-%d %H:%M:%S")))
    info_data = {
        "status": "info",
        "app": "entity_mds_app",
        "file": "cron.py",
        "threading": threading.current_thread().name,
        "function": "processing_datasets",
        "data": {
            "stop_time": stop_time,
            "stop_timestamp": int(stop_timestamp),
        },
        "message": f"processing_datasets stop, useing time {stop_timestamp - start_timestamp}s."
    }
    logger.bind(name="cron_log").info(json.dumps(info_data))


# if __name__ == '__main__':
#     sched = BlockingScheduler()
#
#     sched.add_job(
#         func=processing_datasets,
#         trigger=CronTrigger.from_crontab('0 */2 * * *'),
#         # 同一个任务同一时间最多只能有1个实例在运行
#         max_instances=1,
#     )
#
#     sched.start()
