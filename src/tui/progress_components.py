"""
进度监控仪表板组件
提供实时进度显示、性能监控、错误统计等功能
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    ProgressBar, Static, Label, Button, Log,
    DataTable, Footer, Sparkline
)
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message

# 尝试导入psutil用于系统监控
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from src.i18n.i18n import t
from src.utils.logger import info as log_info, error as log_error


@dataclass
class ProgressState:
    """进度状态数据类"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    current_task: str = ""
    start_time: Optional[float] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)


class ProgressMonitor:
    """进度监控核心类"""

    def __init__(self, total_tasks: int = 0):
        self.state = ProgressState(total_tasks=total_tasks)
        self._callbacks: List[Callable] = []

    def set_total_tasks(self, total: int):
        """设置总任务数"""
        self.state.total_tasks = total
        self._notify_callbacks()

    def complete_task(self, task_name: str = ""):
        """完成一个任务"""
        if self.state.completed_tasks + self.state.failed_tasks < self.state.total_tasks:
            self.state.completed_tasks += 1
            self.state.current_task = task_name
            self._notify_callbacks()

    def fail_task(self, error_message: str, task_name: str = ""):
        """任务失败"""
        if self.state.completed_tasks + self.state.failed_tasks < self.state.total_tasks:
            self.state.failed_tasks += 1
            self.state.errors.append({
                "timestamp": time.time(),
                "task": task_name,
                "message": error_message
            })
            self._notify_callbacks()

    def reset(self):
        """重置进度"""
        self.state = ProgressState()
        self._notify_callbacks()

    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.state.total_tasks == 0:
            return 0.0
        processed = self.state.completed_tasks + self.state.failed_tasks
        return (processed / self.state.total_tasks) * 100

    def get_elapsed_time(self) -> float:
        """获取已用时间"""
        if not self.state.start_time:
            return 0.0
        return time.time() - self.state.start_time

    def get_estimated_total_time(self) -> float:
        """估算总时间"""
        elapsed = self.get_elapsed_time()
        if elapsed == 0 or self.state.completed_tasks == 0:
            return 0.0

        processed = self.state.completed_tasks + self.state.failed_tasks
        if processed == 0:
            return 0.0

        # 基于当前速度估算总时间
        time_per_task = elapsed / processed
        return time_per_task * self.state.total_tasks

    def get_remaining_time(self) -> float:
        """获取剩余时间"""
        total_estimated = self.get_estimated_total_time()
        elapsed = self.get_elapsed_time()
        return max(0, total_estimated - elapsed)

    def is_completed(self) -> bool:
        """检查是否完成"""
        processed = self.state.completed_tasks + self.state.failed_tasks
        return processed >= self.state.total_tasks and self.state.total_tasks > 0

    def add_callback(self, callback: Callable):
        """添加进度更新回调"""
        self._callbacks.append(callback)

    def _notify_callbacks(self):
        """通知所有回调函数"""
        for callback in self._callbacks:
            try:
                callback(self.state)
            except Exception as e:
                log_error(f"Progress callback error: {e}")


class ProcessingProgress(Static):
    """处理进度显示组件"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._progress_percentage = 0.0
        self._processing_speed = 0.0
        self._remaining_time = 0.0
        self._last_update_time = time.time()
        self._last_processed_count = 0

    @property
    def progress_percentage(self) -> float:
        return self._progress_percentage

    @property
    def processing_speed(self) -> float:
        return self._processing_speed

    @property
    def remaining_time(self) -> float:
        return self._remaining_time

    def compose(self) -> ComposeResult:
        yield Container(
            Label(t("progress.processing_progress"), classes="metric-label"),
            ProgressBar(
                id="processing-progress-bar",
                show_eta=True,
                show_percentage=True
            ),
            Horizontal(
                Label(t("progress.speed"), classes="metric-label"),
                Label("0 文件/分钟", id="processing-speed"),
            ),
            Horizontal(
                Label(t("progress.remaining"), classes="metric-label"),
                Label("--:--:--", id="remaining-time"),
            )
        )

    def update_progress(self, processed: int, total: int):
        """更新进度"""
        if total == 0:
            return

        current_time = time.time()
        self._progress_percentage = (processed / total) * 100

        # 计算处理速度（文件/分钟）
        time_diff = current_time - self._last_update_time
        if time_diff > 1.0:  # 每秒更新一次速度
            files_processed = processed - self._last_processed_count
            if time_diff > 0:
                self._processing_speed = (files_processed / time_diff) * 60
                self._last_update_time = current_time
                self._last_processed_count = processed

        # 更新UI（如果已挂载）
        try:
            progress_bar = self.query_one("#processing-progress-bar", ProgressBar)
            progress_bar.progress = self._progress_percentage
        except:
            pass  # 组件未挂载或查询失败

        try:
            speed_label = self.query_one("#processing-speed", Label)
            speed_label.update(f"{self._processing_speed:.1f} {t('progress.files_per_minute')}")
        except:
            pass

    def update_remaining_time(self, seconds: float):
        """更新剩余时间"""
        self._remaining_time = seconds

        # 更新UI（如果已挂载）
        try:
            time_label = self.query_one("#remaining-time", Label)
            if seconds <= 0:
                time_label.update("--:--:--")
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                time_label.update(f"{hours:02d}:{minutes:02d}:{secs:02d}")
        except:
            pass


class CurrentOperationStatus(Container):
    """当前操作状态组件"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_operation = t("status.idle")
        self._is_active = False
        self._logs: List[Dict[str, Any]] = []

    @property
    def current_operation(self) -> str:
        return self._current_operation

    @property
    def is_active(self) -> bool:
        return self._is_active

    def compose(self) -> ComposeResult:
        yield Container(
            Label(t("status.current_operation"), classes="metric-label"),
            Label(self._current_operation, id="current-operation-text"),
            Log(id="operation-log", auto_scroll=True, max_lines=10)
        )

    def set_operation(self, operation: str):
        """设置当前操作"""
        self._current_operation = operation
        self._is_active = (operation != t("status.idle"))

        # 更新UI（如果已挂载）
        try:
            operation_label = self.query_one("#current-operation-text", Label)
            operation_label.update(operation)
        except:
            pass

    def add_log(self, message: str, level: str = "info"):
        """添加操作日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "message": message,
            "level": level
        }
        self._logs.append(log_entry)

        # 添加到Log组件（如果已挂载）
        try:
            log_widget = self.query_one("#operation-log", Log)
            formatted_message = f"[{timestamp}] {message}"
            log_widget.write_line(formatted_message)
        except:
            pass

    def get_logs(self, level: Optional[str] = None, min_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取日志"""
        if not level and not min_level:
            return self._logs.copy()

        level_priority = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}

        if level:
            return [log for log in self._logs if log["level"] == level]

        if min_level:
            min_priority = level_priority.get(min_level, 0)
            return [log for log in self._logs
                   if level_priority.get(log["level"], 0) >= min_priority]

    def clear_logs(self):
        """清空日志"""
        self._logs.clear()
        try:
            log_widget = self.query_one("#operation-log", Log)
            log_widget.clear()
        except:
            pass


class CpuGauge(Static):
    """CPU使用率仪表盘（使用ProgressBar模拟）"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cpu_usage = 0.0

    @property
    def cpu_usage(self) -> float:
        return self._cpu_usage

    def compose(self) -> ComposeResult:
        yield ProgressBar(id="cpu-progress", show_percentage=True)

    def update_cpu(self, usage: float):
        """更新CPU使用率"""
        self._cpu_usage = usage
        try:
            progress_bar = self.query_one("#cpu-progress", ProgressBar)
            progress_bar.progress = usage
        except:
            pass


class MemoryGauge(Static):
    """内存使用率仪表盘（使用ProgressBar模拟）"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._memory_usage = 0.0

    @property
    def memory_usage(self) -> float:
        return self._memory_usage

    def compose(self) -> ComposeResult:
        yield ProgressBar(id="memory-progress", show_percentage=True)

    def update_memory(self, usage: float):
        """更新内存使用率"""
        self._memory_usage = usage
        try:
            progress_bar = self.query_one("#memory-progress", ProgressBar)
            progress_bar.progress = usage
        except:
            pass


class PerformanceMetrics(Container):
    """性能指标监控组件"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cpu_usage = 0.0
        self._memory_usage = 0.0
        self._processing_speed = 0.0
        self._performance_history: List[Dict[str, float]] = []
        self._processing_times: List[float] = []
        self._update_task = None

    @property
    def cpu_usage(self) -> float:
        return self._cpu_usage

    @property
    def memory_usage(self) -> float:
        return self._memory_usage

    @property
    def processing_speed(self) -> float:
        return self._processing_speed

    def compose(self) -> ComposeResult:
        yield Container(
            Label(t("metrics.performance"), classes="metric-label"),
            Horizontal(
                Vertical(
                    Label(t("metrics.cpu"), classes="metric-label"),
                    CpuGauge(id="cpu-gauge"),
                ),
                Vertical(
                    Label(t("metrics.memory"), classes="metric-label"),
                    MemoryGauge(id="memory-gauge"),
                ),
                Vertical(
                    Label(t("metrics.speed_chart"), classes="metric-label"),
                    Sparkline([], id="speed-sparkline", summary_function=None),
                )
            )
        )

    def on_mount(self) -> None:
        """组件挂载时启动监控"""
        self._update_task = self.set_interval(1.0, self.update_metrics)

    def on_unmount(self) -> None:
        """组件卸载时停止监控"""
        if self._update_task:
            self._update_task.cancel()

    def update_metrics(self):
        """更新性能指标"""
        if not PSUTIL_AVAILABLE:
            return

        try:
            # 获取CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            self._cpu_usage = cpu_percent

            # 获取内存使用率
            memory = psutil.virtual_memory()
            self._memory_usage = memory.percent

            # 记录性能历史
            self._performance_history.append({
                "timestamp": time.time(),
                "cpu": cpu_percent,
                "memory": memory.percent,
                "speed": self._processing_speed
            })

            # 保持历史记录在合理范围内
            if len(self._performance_history) > 100:
                self._performance_history.pop(0)

            # 更新UI
            self._update_ui()

        except Exception as e:
            log_error(f"Failed to update performance metrics: {e}")

    def _update_ui(self):
        """更新UI显示"""
        try:
            cpu_gauge = self.query_one("#cpu-gauge", CpuGauge)
            cpu_gauge.update_cpu(self._cpu_usage)
        except:
            pass

        try:
            memory_gauge = self.query_one("#memory-gauge", MemoryGauge)
            memory_gauge.update_memory(self._memory_usage)
        except:
            pass

        try:
            sparkline = self.query_one("#speed-sparkline", Sparkline)
            speed_history = [entry["speed"] for entry in self._performance_history[-50:]]
            sparkline.data = speed_history
        except:
            pass

    def record_processing_time(self, processing_time: float):
        """记录处理时间"""
        self._processing_times.append(processing_time)

        # 保持处理时间记录在合理范围内
        if len(self._processing_times) > 1000:
            self._processing_times.pop(0)

    def update_processing_speed(self, files_per_minute: float):
        """更新处理速度"""
        self._processing_speed = files_per_minute
        self._update_ui()  # 立即更新UI

    def get_average_processing_time(self) -> float:
        """获取平均处理时间"""
        if not self._processing_times:
            return 0.0
        return sum(self._processing_times) / len(self._processing_times)

    def get_performance_history(self) -> List[Dict[str, float]]:
        """获取性能历史记录"""
        return self._performance_history.copy()

    def reset_metrics(self):
        """重置指标"""
        self._performance_history.clear()
        self._processing_times.clear()


class OperationControls(Container):
    """操作控制组件"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._can_pause = False
        self._can_resume = False
        self._can_cancel = False
        self._is_running = False
        self._is_paused = False
        self._is_cancelled = False
        self._is_completed = False

    @property
    def can_pause(self) -> bool:
        return self._can_pause

    @property
    def can_resume(self) -> bool:
        return self._can_resume

    @property
    def can_cancel(self) -> bool:
        return self._can_cancel

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    @property
    def is_completed(self) -> bool:
        return self._is_completed

    class OperationControl(Message):
        """操作控制消息"""
        def __init__(self, action: str) -> None:
            super().__init__()
            self.action = action

    def compose(self) -> ComposeResult:
        yield Container(
            Label(t("controls.operations"), classes="metric-label"),
            Horizontal(
                Button(
                    t("controls.start"),
                    id="start-btn",
                    variant="primary",
                    disabled=False
                ),
                Button(
                    t("controls.pause"),
                    id="pause-btn",
                    variant="warning",
                    disabled=True
                ),
                Button(
                    t("controls.resume"),
                    id="resume-btn",
                    variant="success",
                    disabled=True
                ),
                Button(
                    t("controls.cancel"),
                    id="cancel-btn",
                    variant="error",
                    disabled=True
                )
            )
        )

    def _update_button_states(self):
        """更新按钮状态"""
        try:
            pause_btn = self.query_one("#pause-btn", Button)
            pause_btn.disabled = not self._can_pause
        except:
            pass

        try:
            resume_btn = self.query_one("#resume-btn", Button)
            resume_btn.disabled = not self._can_resume
        except:
            pass

        try:
            cancel_btn = self.query_one("#cancel-btn", Button)
            cancel_btn.disabled = not self._can_cancel
        except:
            pass

        try:
            start_btn = self.query_one("#start-btn", Button)
            start_btn.disabled = self._is_running or self._is_paused
        except:
            pass

    def on_button_pressed(self, event: Button.Pressed):
        """处理按钮按下事件"""
        button_id = event.button.id

        if button_id == "start-btn":
            self.start_operation()
        elif button_id == "pause-btn":
            self.pause_operation()
        elif button_id == "resume-btn":
            self.resume_operation()
        elif button_id == "cancel-btn":
            self.cancel_operation()

        # 发送控制消息
        self.post_message(self.OperationControl(button_id.replace("-btn", "")))

    def start_operation(self):
        """开始操作"""
        self._is_running = True
        self._is_paused = False
        self._is_cancelled = False
        self._is_completed = False

        self._can_pause = True
        self._can_resume = False
        self._can_cancel = True

        self._update_button_states()

    def pause_operation(self):
        """暂停操作"""
        self._is_running = False
        self._is_paused = True

        self._can_pause = False
        self._can_resume = True
        self._can_cancel = True

        self._update_button_states()

    def resume_operation(self):
        """恢复操作"""
        self._is_running = True
        self._is_paused = False

        self._can_pause = True
        self._can_resume = False
        self._can_cancel = True

        self._update_button_states()

    def cancel_operation(self):
        """取消操作"""
        self._is_running = False
        self._is_paused = False
        self._is_cancelled = True

        self._can_pause = False
        self._can_resume = False
        self._can_cancel = False

        self._update_button_states()

    def complete_operation(self):
        """完成操作"""
        self._is_running = False
        self._is_paused = False
        self._is_completed = True

        self._can_pause = False
        self._can_resume = False
        self._can_cancel = False

        self._update_button_states()


class ErrorStatistics(Container):
    """错误统计和成功计数组件"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._total_errors = 0
        self._success_count = 0
        self._error_rate = 0.0
        self._errors: List[Dict[str, Any]] = []
        self._error_categories: Dict[str, int] = {}
        self._recovery_attempts: List[Dict[str, Any]] = []

    @property
    def total_errors(self) -> int:
        return self._total_errors

    @property
    def success_count(self) -> int:
        return self._success_count

    @property
    def error_rate(self) -> float:
        return self._error_rate

    def compose(self) -> ComposeResult:
        yield Container(
            Label(t("errors.statistics"), classes="metric-label"),
            Horizontal(
                Vertical(
                    Label(t("errors.total"), classes="metric-label"),
                    Label("0", id="total-errors"),
                ),
                Vertical(
                    Label(t("errors.success_rate"), classes="metric-label"),
                    Label("100%", id="success-rate"),
                ),
                Vertical(
                    Label(t("errors.error_rate"), classes="metric-label"),
                    Label("0%", id="error-rate"),
                )
            ),
            DataTable(id="error-details", cursor_type="row")
        )

    def on_mount(self) -> None:
        """组件挂载时初始化表格"""
        self._setup_error_table()

    def _setup_error_table(self):
        """设置错误详情表格"""
        try:
            table = self.query_one("#error-details", DataTable)
            table.add_columns(t("errors.time"), t("errors.category"), t("errors.message"))
        except:
            pass

    def add_error(self, message: str, category: str = "general", timestamp: Optional[float] = None):
        """添加错误"""
        if timestamp is None:
            timestamp = time.time()

        error_entry = {
            "timestamp": timestamp,
            "message": message,
            "category": category
        }

        self._errors.append(error_entry)

        # 更新错误分类统计
        if category not in self._error_categories:
            self._error_categories[category] = 0
        self._error_categories[category] += 1

        # 更新统计
        self._total_errors += 1
        self._update_error_rate()
        self._update_error_table()

    def record_recovery_attempt(self, error_message: str, success: bool):
        """记录恢复尝试"""
        self._recovery_attempts.append({
            "timestamp": time.time(),
            "error_message": error_message,
            "success": success
        })

    def increment_success_count(self):
        """增加成功计数"""
        self._success_count += 1
        self._update_error_rate()
        self._update_success_rate_display()

    def _update_error_rate(self):
        """更新错误率"""
        total_operations = self._success_count + self._total_errors
        if total_operations == 0:
            self._error_rate = 0.0
        else:
            self._error_rate = (self._total_errors / total_operations) * 100

    def _update_ui(self):
        """更新UI显示"""
        try:
            total_errors_label = self.query_one("#total-errors", Label)
            total_errors_label.update(str(self._total_errors))
        except:
            pass

        self._update_error_rate_display()
        self._update_success_rate_display()

    def _update_error_rate_display(self):
        """更新错误率显示"""
        try:
            error_rate_label = self.query_one("#error-rate", Label)
            error_rate_label.update(f"{self._error_rate:.1f}%")
        except:
            pass

    def _update_success_rate_display(self):
        """更新成功率显示"""
        total_operations = self._success_count + self._total_errors
        if total_operations == 0:
            success_rate = 100.0
        else:
            success_rate = (self._success_count / total_operations) * 100

        try:
            success_rate_label = self.query_one("#success-rate", Label)
            success_rate_label.update(f"{success_rate:.1f}%")
        except:
            pass

    def _update_error_table(self):
        """更新错误详情表格"""
        try:
            table = self.query_one("#error-details", DataTable)
            table.clear()

            # 显示最近的10个错误
            recent_errors = self._errors[-10:] if len(self._errors) > 10 else self._errors

            for error in recent_errors:
                time_str = datetime.fromtimestamp(error["timestamp"]).strftime("%H:%M:%S")
                table.add_row(time_str, error["category"], error["message"])
        except:
            pass

    def get_error_categories(self) -> Dict[str, int]:
        """获取错误分类统计"""
        return self._error_categories.copy()

    def get_error_details(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取错误详情"""
        return self._errors[-limit:] if len(self._errors) > limit else self._errors.copy()

    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计"""
        total_attempts = len(self._recovery_attempts)
        successful_recoveries = sum(1 for attempt in self._recovery_attempts if attempt["success"])

        recovery_rate = (successful_recoveries / total_attempts * 100) if total_attempts > 0 else 0

        return {
            "total_attempts": total_attempts,
            "successful_recoveries": successful_recoveries,
            "recovery_rate": recovery_rate
        }

    def clear_errors(self):
        """清空错误记录"""
        self._errors.clear()
        self._error_categories.clear()
        self._total_errors = 0
        self._success_count = 0
        self._error_rate = 0.0
        self._update_error_table()
        self._update_success_rate_display()
        self._update_ui()


class ProgressDashboard(Container):
    """进度监控仪表板主组件"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress_monitor = ProgressMonitor()
        self._setup_callbacks()

    def compose(self) -> ComposeResult:
        """组合所有进度监控组件"""
        yield Container(
            Label(t("dashboard.progress_monitor"), classes="metric-label"),

            # 处理进度显示
            ProcessingProgress(id="processing-progress", classes="btop-panel"),

            # 当前操作状态
            CurrentOperationStatus(id="operation-status", classes="btop-panel"),

            # 性能指标
            PerformanceMetrics(id="performance-metrics", classes="btop-panel"),

            # 操作控制
            OperationControls(id="operation-controls", classes="btop-panel"),

            # 错误统计
            ErrorStatistics(id="error-statistics", classes="btop-panel")
        )

    def _setup_callbacks(self):
        """设置进度监控回调"""
        def on_progress_update(state: ProgressState):
            """处理进度更新"""
            try:
                # 更新处理进度
                processing_progress = self.query_one("#processing-progress", ProcessingProgress)
                processed = state.completed_tasks + state.failed_tasks
                processing_progress.update_progress(processed, state.total_tasks)

                # 更新剩余时间
                remaining_time = self.progress_monitor.get_remaining_time()
                processing_progress.update_remaining_time(remaining_time)
            except:
                pass  # 组件未挂载

        self.progress_monitor.add_callback(on_progress_update)

    def start_monitoring(self, total_tasks: int):
        """开始监控"""
        self.progress_monitor.reset()
        self.progress_monitor.set_total_tasks(total_tasks)
        self.progress_monitor.state.start_time = time.time()

        # 设置操作状态
        try:
            operation_status = self.query_one("#operation-status", CurrentOperationStatus)
            operation_status.set_operation(t("status.processing"))
        except:
            pass

        # 启动操作控制
        try:
            operation_controls = self.query_one("#operation-controls", OperationControls)
            operation_controls.start_operation()
        except:
            pass

    def complete_task(self, task_name: str = ""):
        """完成任务"""
        self.progress_monitor.complete_task(task_name)

        # 增加成功计数
        try:
            error_stats = self.query_one("#error-statistics", ErrorStatistics)
            error_stats.increment_success_count()
        except:
            pass

    def fail_task(self, error_message: str, task_name: str = ""):
        """任务失败"""
        self.progress_monitor.fail_task(error_message, task_name)

        # 添加到错误统计
        try:
            error_stats = self.query_one("#error-statistics", ErrorStatistics)
            error_stats.add_error(error_message, "processing")
        except:
            pass

        # 添加到操作日志
        try:
            operation_status = self.query_one("#operation-status", CurrentOperationStatus)
            operation_status.add_log(f"任务失败: {error_message}", "error")
        except:
            pass

    def add_operation_log(self, message: str, level: str = "info"):
        """添加操作日志"""
        try:
            operation_status = self.query_one("#operation-status", CurrentOperationStatus)
            operation_status.add_log(message, level)
        except:
            pass

    def complete_monitoring(self):
        """完成监控"""
        try:
            operation_status = self.query_one("#operation-status", CurrentOperationStatus)
            operation_status.set_operation(t("status.completed"))
        except:
            pass

        try:
            operation_controls = self.query_one("#operation-controls", OperationControls)
            operation_controls.complete_operation()
        except:
            pass

        self.add_operation_log(t("status.all_tasks_completed"), "info")

    def reset_dashboard(self):
        """重置仪表板"""
        self.progress_monitor.reset()

        # 重置各组件
        try:
            error_stats = self.query_one("#error-statistics", ErrorStatistics)
            error_stats.clear_errors()
        except:
            pass

        try:
            operation_status = self.query_one("#operation-status", CurrentOperationStatus)
            operation_status.set_operation(t("status.idle"))
            operation_status.clear_logs()
        except:
            pass

        try:
            performance_metrics = self.query_one("#performance-metrics", PerformanceMetrics)
            performance_metrics.reset_metrics()
        except:
            pass