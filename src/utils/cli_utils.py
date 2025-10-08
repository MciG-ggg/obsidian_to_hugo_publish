"""
CLI Utilities Module
Contains command-line interface utilities and helper functions
"""

from typing import Any, Dict, List, Optional, Tuple, Union
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


class CLIColors:
    """Class containing color codes for CLI output"""
    GREEN = COLOR_GREEN
    RED = COLOR_RED
    YELLOW = COLOR_YELLOW
    BLUE = COLOR_BLUE
    BOLD = COLOR_BOLD
    DIM = COLOR_DIM
    ITALIC = COLOR_ITALIC
    UNDERLINE = COLOR_UNDERLINE
    RESET = COLOR_RESET
    CYAN = COLOR_CYAN
    MAGENTA = COLOR_MAGENTA


def print_step(step_num: int, message: str) -> None:
    """
    打印带编号的步骤信息，同时记录日志
    Print step information with number, and log at the same time
    """
    step_text = t("step_prefix", step_num=step_num)
    output = f"\n{CLIColors.BLUE}{CLIColors.BOLD}{step_text}{CLIColors.RESET} {message}"
    print(output)
    log_info(f"[STEP {step_num}] {message}")


def print_success(message: str) -> None:
    """
    打印成功信息，同时记录日志
    Print success information and log at the same time
    """
    success_prefix = t("success_prefix")
    output = f"{CLIColors.GREEN}{success_prefix} {message}{CLIColors.RESET}"
    print(output)
    log_info(f"SUCCESS: {message}")


def print_error(message: str) -> None:
    """
    打印错误信息，同时记录日志
    Print error information and log at the same time
    """
    error_prefix = t("error_prefix")
    output = f"{CLIColors.RED}{error_prefix} {message}{CLIColors.RESET}"
    print(output)
    log_error(f"ERROR: {message}")


def print_warning(message: str) -> None:
    """
    打印警告信息，同时记录日志
    Print warning information and log at the same time
    """
    warning_prefix = t("warning_prefix")
    output = f"{CLIColors.YELLOW}{warning_prefix} {message}{CLIColors.RESET}"
    print(output)
    log_warning(f"WARNING: {message}")


def print_info(message: str) -> None:
    """
    打印普通信息，同时记录日志
    Print regular information and log at the same time
    """
    info_prefix = t("info_prefix")
    output = f"{CLIColors.CYAN}{info_prefix} {message}{CLIColors.RESET}"
    print(output)
    log_info(message)


def print_header(message: str) -> None:
    """
    打印标题信息
    Print header information
    """
    header_output = f"\n{CLIColors.MAGENTA}{CLIColors.BOLD}{message}{CLIColors.RESET}"
    separator = f"{CLIColors.DIM}{'='*len(message)}{CLIColors.RESET}\n"
    print(header_output)
    print(separator)
    log_info(f"HEADER: {message}")


def print_status(status: str, message: str, color: str = CLIColors.CYAN) -> None:
    """
    通用状态打印函数
    General status printing function
    """
    output = f"{color}{status}{CLIColors.RESET} {message}"
    print(output)


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    获取用户确认
    Get user confirmation
    """
    default_str = "Y/n" if default else "y/N"
    prompt = f"{CLIColors.YELLOW}{prompt} [{default_str}]{CLIColors.RESET} "
    
    try:
        response = input(prompt).strip().lower()
    except KeyboardInterrupt:
        print(f"\n{CLIColors.RED}{t('cancel_operation')}{CLIColors.RESET}")
        return False
    
    if not response:
        return default
    
    return response in ['y', 'yes', '是']


def format_list(items: List[str], prefix: str = "- ") -> str:
    """格式化列表输出"""
    """Format list output"""
    return "\n".join([f"{prefix}{item}" for item in items])


def print_table(headers: List[str], rows: List[List[Any]]) -> None:
    """
    以表格形式打印数据
    Print data in table format
    """
    # 计算每列的最大宽度
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(header)
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width)
    
    # 打印表头
    header_row = " | ".join(header.ljust(width) for header, width in zip(headers, col_widths))
    print(f"{CLIColors.BOLD}{header_row}{CLIColors.RESET}")
    print("-|-".join("-" * width for width in col_widths))
    
    # 打印数据行
    for row in rows:
        data_row = " | ".join(str(cell).ljust(width) for cell, width in zip(row, col_widths))
        print(data_row)


def print_progress_bar(current: int, total: int, bar_length: int = 50, status: str = "") -> None:
    """
    打印进度条
    Print a progress bar
    """
    if total == 0:
        return  # Avoid division by zero
    
    percent = float(current) / total
    filled_length = int(bar_length * percent)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    
    print(f'\r{CLIColors.CYAN}|{bar}| {percent * 100:.2f}% {status}{CLIColors.RESET}', end='', flush=True)
    
    if current == total:
        print()  # 换行


def get_user_choice(options: List[str], prompt: str = None) -> Tuple[Optional[int], Optional[str]]:
    """
    获取用户从多个选项中的选择
    Get user's choice from a list of options
    """
    if prompt is None:
        prompt = t("select_option_prompt")
    
    print_header(t("options_list_header"))
    for idx, option in enumerate(options):
        print(f"{CLIColors.BOLD}[{idx}]{CLIColors.RESET} {option}")
    
    while True:
        try:
            choice = input(f"\n{CLIColors.YELLOW}{prompt}{CLIColors.RESET}").strip()
            if choice.isdigit():
                choice_idx = int(choice)
                if 0 <= choice_idx < len(options):
                    return choice_idx, options[choice_idx]
                else:
                    print_error(t("selection_out_of_range"))
            else:
                # 如果用户输入的是选项内容，而不是数字
                for idx, option in enumerate(options):
                    if choice.lower() in option.lower():
                        return idx, option
                print_error(t("invalid_selection"))
        except (ValueError, KeyboardInterrupt):
            print_error(t("input_cancelled"))
            return None, None


def print_json_output(data: Any) -> None:
    """
    以JSON格式打印输出
    Print output in JSON format
    """
    import json
    print(json.dumps(data, ensure_ascii=False, indent=2))


def print_formatted_output(data: Any, format_type: str = "default") -> None:
    """
    根据指定格式打印输出
    Print output in specified format
    """
    if format_type == "json":
        print_json_output(data)
    elif format_type == "table" and isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            rows = [list(row.values()) for row in data]
            print_table(headers, rows)
        else:
            # 简单的一维列表
            print_table(["Item"], [[item] for item in data])
    else:
        # 默认格式
        if isinstance(data, list):
            for item in data:
                print(item)
        elif isinstance(data, dict):
            for key, value in data.items():
                print(f"{key}: {value}")
        else:
            print(data)


def handle_exception(e: Exception, context: str = "operation") -> None:
    """
    统一处理异常的函数
    Handle exceptions in a consistent way
    """
    error_msg = t("exception_occurred", context=context, error=str(e))
    print_error(error_msg)
    from .logger import exception as log_exception
    log_exception(f"{context} - Exception: {str(e)}")


def safe_input(prompt: str = "", input_type: type = str, default: Any = None, 
               validate: callable = None) -> Any:
    """
    安全获取用户输入的函数
    Safely get user input with type conversion and validation
    """
    while True:
        try:
            user_input = input(prompt).strip()
            
            if not user_input and default is not None:
                return default
            
            converted_input = input_type(user_input)
            
            if validate and not validate(converted_input):
                print_warning(t("invalid_input_validation"))
                continue
            
            return converted_input
        except ValueError:
            print_error(t("invalid_input_type", expected_type=input_type.__name__))
        except KeyboardInterrupt:
            print_error(t("input_cancelled"))
            return default