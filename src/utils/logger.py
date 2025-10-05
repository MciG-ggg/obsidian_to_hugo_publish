"""
日志模块
提供结构化日志记录功能，替代print输出
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# 日志级别映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}


def setup_logger(name='hugo_publisher', log_file=None, level='INFO', 
                format_string=None):
    """
    设置日志记录器
    :param name: 日志记录器名称
    :param log_file: 日志文件路径，如果为None则只输出到控制台
    :param level: 日志级别
    :param format_string: 日志格式字符串
    :return: 配置好的日志记录器
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
    
    # 避免重复添加处理器
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(format_string)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 全局日志记录器实例
logger = setup_logger()


def set_log_level(level):
    """
    设置日志级别
    :param level: 日志级别字符串
    """
    global logger
    logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))


def set_log_file(log_file):
    """
    设置日志文件
    :param log_file: 日志文件路径
    """
    global logger
    # 重新创建logger以添加文件处理器
    logger = setup_logger(log_file=log_file)


def debug(message):
    """记录调试信息"""
    logger.debug(message)


def info(message):
    """记录信息"""
    logger.info(message)


def warning(message):
    """记录警告"""
    logger.warning(message)


def error(message):
    """记录错误"""
    logger.error(message)


def critical(message):
    """记录严重错误"""
    logger.critical(message)


def exception(message):
    """记录异常信息"""
    logger.exception(message)