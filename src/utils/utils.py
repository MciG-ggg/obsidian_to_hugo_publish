"""
工具模块
包含项目中使用的各种工具函数
"""

from ..i18n.i18n import t
from .logger import info as log_info, error as log_error, warning as log_warning, debug as log_debug

# ANSI 颜色代码
COLOR_GREEN = "\033[92m"    # 成功信息
COLOR_RED = "\033[91m"      # 错误信息
COLOR_YELLOW = "\033[93m"   # 警告和提示
COLOR_BLUE = "\033[94m"     # 步骤和进度
COLOR_BOLD = "\033[1m"      # 粗体
COLOR_DIM = "\033[2m"       # 暗色
COLOR_ITALIC = "\033[3m"    # 斜体
COLOR_UNDERLINE = "\033[4m" # 下划线
COLOR_RESET = "\033[0m"     # 重置颜色
COLOR_CYAN = "\033[96m"     # 信息提示
COLOR_MAGENTA = "\033[95m"  # 强调


def print_step(step_num, message):
    """打印带编号的步骤信息，同时记录日志"""
    step_text = t("step_prefix", step_num=step_num)
    output = f"\n{COLOR_BLUE}{COLOR_BOLD}{step_text}{COLOR_RESET} {message}"
    print(output)
    log_info(f"[STEP {step_num}] {message}")

def print_success(message):
    """打印成功信息，同时记录日志"""
    success_prefix = t("success_prefix")
    output = f"{COLOR_GREEN}{success_prefix} {message}{COLOR_RESET}"
    print(output)
    log_info(f"SUCCESS: {message}")

def print_error(message):
    """打印错误信息，同时记录日志"""
    error_prefix = t("error_prefix")
    output = f"{COLOR_RED}{error_prefix} {message}{COLOR_RESET}"
    print(output)
    log_error(f"ERROR: {message}")

def print_warning(message):
    """打印警告信息，同时记录日志"""
    warning_prefix = t("warning_prefix")
    output = f"{COLOR_YELLOW}{warning_prefix} {message}{COLOR_RESET}"
    print(output)
    log_warning(f"WARNING: {message}")

def print_info(message):
    """打印普通信息，同时记录日志"""
    info_prefix = t("info_prefix")
    output = f"{COLOR_CYAN}{info_prefix} {message}{COLOR_RESET}"
    print(output)
    log_info(message)

def print_header(message):
    """打印标题信息"""
    header_output = f"\n{COLOR_MAGENTA}{COLOR_BOLD}{message}{COLOR_RESET}"
    separator = f"{COLOR_DIM}{'='*len(message)}{COLOR_RESET}\n"
    print(header_output)
    print(separator)
    log_info(f"HEADER: {message}")