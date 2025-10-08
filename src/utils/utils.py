"""
工具模块
包含项目中使用的各种工具函数
"""

# Import print functions from cli_utils to avoid duplication
from .cli_utils import (
    print_step,
    print_success, 
    print_error,
    print_warning,
    print_info,
    print_header,
    print_formatted_output
)


def set_log_file(log_file):
    """
    设置日志文件
    :param log_file: 日志文件路径
    """
    from .logger import set_log_file as logger_set_log_file
    logger_set_log_file(log_file)


def set_log_level(level):
    """
    设置日志级别
    :param level: 日志级别
    """
    from .logger import set_log_level as logger_set_log_level
    logger_set_log_level(level)