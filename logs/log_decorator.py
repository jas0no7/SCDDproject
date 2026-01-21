# --coding:utf-8--
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def log_execution(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"开始执行 {func.__name__}，参数={args}, {kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"完成 {func.__name__}，返回值类型={type(result)}")
            return result
        except Exception as e:
            logger.exception(f"{func.__name__} 执行出错: {e}")
            raise
    return wrapper
