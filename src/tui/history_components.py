"""
操作历史管理组件
提供文件选择历史、发布历史时间线、错误日志查看、操作统计等功能
"""

import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import Counter, defaultdict
import threading

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    DataTable, Static, Label, Button, Input, Log,
    ProgressBar, Footer, Tabs, TabbedContent, TabPane
)
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message

from src.i18n.i18n import t
from src.utils.logger import info as log_info, error as log_error, warning as log_warning


class HistoryManagerError(Exception):
    """历史管理器异常"""
    pass


@dataclass
class FileSelectionRecord:
    """文件选择记录"""
    timestamp: float
    files: List[str]
    count: int
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileSelectionRecord':
        return cls(**data)


@dataclass
class PublishOperationRecord:
    """发布操作记录"""
    timestamp: float
    files: List[str]
    status: str  # 'started', 'success', 'failed', 'cancelled'
    message: str
    duration: float = 0.0  # 操作持续时间（秒）
    files_count: int = 0
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PublishOperationRecord':
        return cls(**data)


@dataclass
class ErrorLogRecord:
    """错误日志记录"""
    timestamp: float
    message: str
    error_type: str  # 'processing', 'network', 'validation', 'system'
    severity: str = "error"  # 'debug', 'info', 'warning', 'error', 'critical'
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorLogRecord':
        return cls(**data)


class HistoryManager:
    """历史管理器 - 负责所有历史数据的存储和管理"""

    def __init__(self, history_file: Optional[Path] = None):
        """初始化历史管理器

        Args:
            history_file: 历史文件路径，如果为None则使用默认路径
        """
        if history_file is None:
            # 默认历史文件路径
            home_dir = Path.home()
            history_dir = home_dir / ".obsidian_hugo_publisher"
            history_dir.mkdir(exist_ok=True)
            history_file = history_dir / "history.json"

        self.history_file = Path(history_file)
        self._lock = threading.Lock()

        # 历史数据存储
        self.file_selection_history: List[FileSelectionRecord] = []
        self.publish_history: List[PublishOperationRecord] = []
        self.error_logs: List[ErrorLogRecord] = []
        self.operation_stats: Dict[str, Any] = {
            "total_sessions": 0,
            "total_files_processed": 0,
            "total_publish_time": 0.0,
            "last_activity": None
        }

        # 加载现有历史数据
        self.load_history()

    def load_history(self) -> None:
        """加载历史数据"""
        try:
            if not self.history_file.exists():
                log_info(f"历史文件不存在，创建新的: {self.history_file}")
                self._create_empty_history()
                return

            with self._lock:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError as e:
                        log_error(f"历史文件JSON格式错误: {e}")
                        self._create_empty_history()
                        return

                # 加载各部分历史数据
                self.file_selection_history = [
                    FileSelectionRecord.from_dict(record)
                    for record in data.get("file_selection_history", [])
                ]

                self.publish_history = [
                    PublishOperationRecord.from_dict(record)
                    for record in data.get("publish_history", [])
                ]

                self.error_logs = [
                    ErrorLogRecord.from_dict(record)
                    for record in data.get("error_logs", [])
                ]

                self.operation_stats = data.get("operation_stats", self.operation_stats)

                log_info(f"成功加载历史数据: {len(self.file_selection_history)} 选择记录, "
                        f"{len(self.publish_history)} 发布记录, {len(self.error_logs)} 错误记录")

        except Exception as e:
            log_error(f"加载历史数据失败: {e}")
            self._create_empty_history()

    def save_history(self) -> None:
        """保存历史数据"""
        try:
            with self._lock:
                # 确保目录存在
                self.history_file.parent.mkdir(parents=True, exist_ok=True)

                # 准备保存的数据
                data = {
                    "file_selection_history": [record.to_dict() for record in self.file_selection_history],
                    "publish_history": [record.to_dict() for record in self.publish_history],
                    "error_logs": [record.to_dict() for record in self.error_logs],
                    "operation_stats": self.operation_stats,
                    "last_saved": time.time()
                }

                # 临时文件写入，确保原子性
                temp_file = self.history_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # 原子性替换
                temp_file.replace(self.history_file)

                log_info("历史数据保存成功")

        except Exception as e:
            log_error(f"保存历史数据失败: {e}")
            raise HistoryManagerError(f"无法保存历史数据: {e}")

    def _create_empty_history(self) -> None:
        """创建空的历史文件"""
        self.file_selection_history = []
        self.publish_history = []
        self.error_logs = []
        self.operation_stats = {
            "total_sessions": 0,
            "total_files_processed": 0,
            "total_publish_time": 0.0,
            "last_activity": None
        }

        try:
            self.save_history()
        except Exception as e:
            log_error(f"创建空历史文件失败: {e}")

    def record_file_selection(self, selected_files: List[str], session_id: str = "") -> None:
        """记录文件选择"""
        try:
            record = FileSelectionRecord(
                timestamp=time.time(),
                files=selected_files.copy(),
                count=len(selected_files),
                session_id=session_id
            )

            self.file_selection_history.append(record)

            # 限制历史记录数量，防止无限增长
            max_records = 1000
            if len(self.file_selection_history) > max_records:
                self.file_selection_history = self.file_selection_history[-max_records:]

            # 更新统计
            self.operation_stats["last_activity"] = time.time()

            log_info(f"记录文件选择: {len(selected_files)} 个文件")

        except Exception as e:
            log_error(f"记录文件选择失败: {e}")

    def record_publish_operation(self, files: List[str], status: str, message: str,
                               duration: float = 0.0, session_id: str = "") -> None:
        """记录发布操作"""
        try:
            record = PublishOperationRecord(
                timestamp=time.time(),
                files=files.copy(),
                status=status,
                message=message,
                duration=duration,
                files_count=len(files),
                session_id=session_id
            )

            self.publish_history.append(record)

            # 限制历史记录数量
            max_records = 1000
            if len(self.publish_history) > max_records:
                self.publish_history = self.publish_history[-max_records:]

            # 更新统计
            self.operation_stats["last_activity"] = time.time()
            self.operation_stats["total_files_processed"] += len(files)
            if duration > 0:
                self.operation_stats["total_publish_time"] += duration

            log_info(f"记录发布操作: {status} - {message}")

        except Exception as e:
            log_error(f"记录发布操作失败: {e}")

    def record_error_log(self, message: str, error_type: str = "general",
                        severity: str = "error", context: Dict[str, Any] = None,
                        session_id: str = "") -> None:
        """记录错误日志"""
        try:
            record = ErrorLogRecord(
                timestamp=time.time(),
                message=message,
                error_type=error_type,
                severity=severity,
                context=context or {},
                session_id=session_id
            )

            self.error_logs.append(record)

            # 限制错误日志数量
            max_records = 2000
            if len(self.error_logs) > max_records:
                self.error_logs = self.error_logs[-max_records:]

            # 更新统计
            self.operation_stats["last_activity"] = time.time()

            log_info(f"记录错误日志: {error_type} - {message}")

        except Exception as e:
            log_error(f"记录错误日志失败: {e}")

    def get_publish_history(self, days: int = 30, status_filter: Optional[str] = None) -> List[PublishOperationRecord]:
        """获取发布历史

        Args:
            days: 获取最近多少天的历史
            status_filter: 状态过滤 ('success', 'failed', 'started', 'cancelled')

        Returns:
            过滤后的发布历史列表，按时间倒序
        """
        try:
            cutoff_time = time.time() - (days * 24 * 3600)

            filtered_history = [
                record for record in self.publish_history
                if record.timestamp >= cutoff_time
            ]

            if status_filter:
                filtered_history = [
                    record for record in filtered_history
                    if record.status == status_filter
                ]

            # 按时间倒序排列（最新的在前）
            return sorted(filtered_history, key=lambda x: x.timestamp, reverse=True)

        except Exception as e:
            log_error(f"获取发布历史失败: {e}")
            return []

    def get_error_logs(self, days: int = 30, error_type: Optional[str] = None,
                      severity_min: str = "info") -> List[ErrorLogRecord]:
        """获取错误日志

        Args:
            days: 获取最近多少天的日志
            error_type: 错误类型过滤
            severity_min: 最低严重程度级别

        Returns:
            过滤后的错误日志列表，按时间倒序
        """
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            severity_levels = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}
            min_level = severity_levels.get(severity_min, 1)

            filtered_logs = [
                record for record in self.error_logs
                if (record.timestamp >= cutoff_time and
                    severity_levels.get(record.severity, 1) >= min_level)
            ]

            if error_type:
                filtered_logs = [
                    record for record in filtered_logs
                    if record.error_type == error_type
                ]

            # 按时间倒序排列
            return sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)

        except Exception as e:
            log_error(f"获取错误日志失败: {e}")
            return []

    def get_operation_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取操作统计数据

        Args:
            days: 统计最近多少天的数据

        Returns:
            统计数据字典
        """
        try:
            cutoff_time = time.time() - (days * 24 * 3600)

            # 过滤指定时间范围内的发布记录
            recent_publishes = [
                record for record in self.publish_history
                if record.timestamp >= cutoff_time
            ]

            # 计算基本统计
            total_publishes = len(recent_publishes)
            successful_publishes = len([r for r in recent_publishes if r.status == "success"])
            failed_publishes = len([r for r in recent_publishes if r.status == "failed"])

            success_rate = (successful_publishes / total_publishes * 100) if total_publishes > 0 else 100.0

            # 计算文件处理统计
            total_files_processed = sum(r.files_count for r in recent_publishes)
            avg_files_per_publish = (total_files_processed / total_publishes) if total_publishes > 0 else 0

            # 计算平均处理时间
            completed_publishes = [r for r in recent_publishes if r.duration > 0]
            avg_duration = sum(r.duration for r in completed_publishes) / len(completed_publishes) if completed_publishes else 0

            # 错误统计
            recent_errors = [
                record for record in self.error_logs
                if record.timestamp >= cutoff_time
            ]
            total_errors = len(recent_errors)

            # 按类型分类错误
            error_by_type = Counter(record.error_type for record in recent_errors)

            return {
                "period_days": days,
                "total_publishes": total_publishes,
                "successful_publishes": successful_publishes,
                "failed_publishes": failed_publishes,
                "success_rate": round(success_rate, 1),
                "total_files_processed": total_files_processed,
                "avg_files_per_publish": round(avg_files_per_publish, 1),
                "avg_processing_time": round(avg_duration, 2),
                "total_errors": total_errors,
                "error_by_type": dict(error_by_type),
                "last_activity": self.operation_stats.get("last_activity")
            }

        except Exception as e:
            log_error(f"获取操作统计失败: {e}")
            return {}

    def clear_history(self, history_type: str = "all", days: int = None) -> None:
        """清除历史数据

        Args:
            history_type: 清除类型 ('all', 'file_selection', 'publish', 'errors')
            days: 清除最近多少天的数据，None表示清除所有
        """
        try:
            if days is None:
                # 清除所有数据
                if history_type in ["all", "file_selection"]:
                    self.file_selection_history.clear()
                if history_type in ["all", "publish"]:
                    self.publish_history.clear()
                if history_type in ["all", "errors"]:
                    self.error_logs.clear()
            else:
                # 清除指定天数之前的数据
                cutoff_time = time.time() - (days * 24 * 3600)

                if history_type in ["all", "file_selection"]:
                    self.file_selection_history = [
                        record for record in self.file_selection_history
                        if record.timestamp >= cutoff_time
                    ]

                if history_type in ["all", "publish"]:
                    self.publish_history = [
                        record for record in self.publish_history
                        if record.timestamp >= cutoff_time
                    ]

                if history_type in ["all", "errors"]:
                    self.error_logs = [
                        record for record in self.error_logs
                        if record.timestamp >= cutoff_time
                    ]

            self.save_history()
            log_info(f"清除历史数据完成: type={history_type}, days={days}")

        except Exception as e:
            log_error(f"清除历史数据失败: {e}")
            raise HistoryManagerError(f"无法清除历史数据: {e}")

    def export_history(self, export_path: Path, format_type: str = "json") -> bool:
        """导出历史数据

        Args:
            export_path: 导出文件路径
            format_type: 导出格式 ('json', 'csv')

        Returns:
            是否导出成功
        """
        try:
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            if format_type.lower() == "json":
                data = {
                    "export_time": time.time(),
                    "file_selection_history": [record.to_dict() for record in self.file_selection_history],
                    "publish_history": [record.to_dict() for record in self.publish_history],
                    "error_logs": [record.to_dict() for record in self.error_logs],
                    "operation_stats": self.operation_stats
                }

                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            elif format_type.lower() == "csv":
                import csv

                # 导出发布历史为CSV
                with open(export_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["时间", "文件数", "状态", "消息", "持续时间"])

                    for record in self.publish_history:
                        timestamp = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                        writer.writerow([
                            timestamp,
                            record.files_count,
                            record.status,
                            record.message,
                            record.duration
                        ])

            else:
                raise ValueError(f"不支持的导出格式: {format_type}")

            log_info(f"历史数据导出成功: {export_path}")
            return True

        except Exception as e:
            log_error(f"导出历史数据失败: {e}")
            return False


class FileSelectionHistory(Static):
    """文件选择历史组件"""

    def __init__(self, history_manager: HistoryManager, **kwargs):
        super().__init__(**kwargs)
        self.history_manager = history_manager
        self.selected_history: List[FileSelectionRecord] = []

    def compose(self) -> ComposeResult:
        yield Container(
            Label("📋 文件选择历史", classes="metric-label"),
            DataTable(id="file-selection-history-table", cursor_type="row"),
            Horizontal(
                Button("重选", id="reselect-btn", variant="primary"),
                Button("清除历史", id="clear-history-btn", variant="error"),
                Button("刷新", id="refresh-btn", variant="default")
            )
        )

    def on_mount(self) -> None:
        """组件挂载时初始化表格"""
        self._setup_table()
        self._refresh_display()

    def _setup_table(self) -> None:
        """设置表格结构"""
        try:
            table = self.query_one("#file-selection-history-table", DataTable)
            table.add_columns("时间", "文件数", "文件列表")
        except Exception:
            pass

    def _refresh_display(self) -> None:
        """刷新显示内容"""
        try:
            table = self.query_one("#file-selection-history-table", DataTable)
            table.clear()

            history = self.get_recent_selections(limit=10)

            for record in history:
                timestamp = datetime.fromtimestamp(record.timestamp).strftime("%m-%d %H:%M")
                file_list = ", ".join([Path(f).name for f in record.files[:3]])
                if len(record.files) > 3:
                    file_list += f" ... (+{len(record.files) - 3})"

                table.add_row(timestamp, str(record.count), file_list)

        except Exception as e:
            log_error(f"刷新文件选择历史显示失败: {e}")

    def get_recent_selections(self, limit: int = 10) -> List[FileSelectionRecord]:
        """获取最近的选择历史"""
        return self.history_manager.file_selection_history[-limit:] if limit > 0 else self.history_manager.file_selection_history

    def get_most_common_files(self, limit: int = 20) -> List[Tuple[str, int]]:
        """获取最常选择的文件"""
        file_counter = Counter()
        for record in self.history_manager.file_selection_history:
            file_counter.update(record.files)

        return file_counter.most_common(limit)

    def quick_reselect(self, index: int) -> List[str]:
        """快速重选历史记录中的文件"""
        try:
            history = self.get_recent_selections()
            if 0 <= index < len(history):
                return history[index].files.copy()
            return []
        except Exception:
            return []

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        button_id = event.button.id

        if button_id == "refresh-btn":
            self._refresh_display()
        elif button_id == "clear-history-btn":
            self._clear_history()
        elif button_id == "reselect-btn":
            self._reselect_files()

    def _clear_history(self) -> None:
        """清除选择历史"""
        try:
            self.history_manager.file_selection_history.clear()
            self.history_manager.save_history()
            self._refresh_display()
            log_info("文件选择历史已清除")
        except Exception as e:
            log_error(f"清除文件选择历史失败: {e}")

    def _reselect_files(self) -> None:
        """重选文件（由父组件处理）"""
        # 这里应该发送消息给父组件处理重选逻辑
        pass


class PublishHistoryTimeline(Static):
    """发布历史时间线组件"""

    def __init__(self, history_manager: HistoryManager, **kwargs):
        super().__init__(**kwargs)
        self.history_manager = history_manager
        self.current_filter = "all"

    def compose(self) -> ComposeResult:
        yield Container(
            Label("📈 发布历史时间线", classes="metric-label"),
            Horizontal(
                Label("状态过滤:"),
                Button("全部", id="filter-all-btn", variant="default"),
                Button("成功", id="filter-success-btn", variant="success"),
                Button("失败", id="filter-failed-btn", variant="error"),
            ),
            DataTable(id="publish-history-table", cursor_type="row"),
            Horizontal(
                Button("撤销上次", id="undo-last-btn", variant="warning"),
                Button("导出", id="export-btn", variant="default"),
                Button("刷新", id="refresh-btn", variant="default")
            )
        )

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._setup_table()
        self._refresh_display()

    def _setup_table(self) -> None:
        """设置表格结构"""
        try:
            table = self.query_one("#publish-history-table", DataTable)
            table.add_columns("时间", "状态", "文件数", "消息", "持续时间")
        except Exception:
            pass

    def _refresh_display(self) -> None:
        """刷新显示内容"""
        try:
            table = self.query_one("#publish-history-table", DataTable)
            table.clear()

            timeline_data = self.get_timeline_data(status_filter=self.current_filter if self.current_filter != "all" else None)

            for record in timeline_data:
                timestamp = datetime.fromtimestamp(record.timestamp).strftime("%m-%d %H:%M:%S")
                status_text = {
                    "success": "✅ 成功",
                    "failed": "❌ 失败",
                    "started": "🔄 开始",
                    "cancelled": "⏹️ 取消"
                }.get(record.status, record.status)

                duration_text = f"{record.duration:.1f}s" if record.duration > 0 else "-"

                table.add_row(
                    timestamp,
                    status_text,
                    str(record.files_count),
                    record.message,
                    duration_text
                )

        except Exception as e:
            log_error(f"刷新发布历史时间线失败: {e}")

    def get_timeline_data(self, days: int = 30, status_filter: Optional[str] = None) -> List[PublishOperationRecord]:
        """获取时间线数据"""
        return self.history_manager.get_publish_history(days=days, status_filter=status_filter)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        button_id = event.button.id

        if button_id == "refresh-btn":
            self._refresh_display()
        elif button_id == "export-btn":
            self._export_timeline()
        elif button_id == "undo-last-btn":
            self._undo_last_publish()
        elif button_id.startswith("filter-"):
            filter_type = button_id.replace("filter-", "").replace("-btn", "")
            self.current_filter = filter_type
            self._refresh_display()

    def _export_timeline(self) -> None:
        """导出时间线数据"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = Path.home() / f"publish_timeline_{timestamp}.json"

            if self.history_manager.export_history(export_path, "json"):
                log_info(f"发布历史已导出到: {export_path}")
            else:
                log_error("导出发布历史失败")
        except Exception as e:
            log_error(f"导出时间线失败: {e}")

    def _undo_last_publish(self) -> None:
        """撤销上次发布操作（由父组件处理）"""
        # 这里应该发送消息给父组件处理撤销逻辑
        pass


class ErrorLogViewer(Static):
    """错误日志查看器组件"""

    def __init__(self, history_manager: HistoryManager, **kwargs):
        super().__init__(**kwargs)
        self.history_manager = history_manager
        self.current_filter = "all"
        self.search_term = ""

    def compose(self) -> ComposeResult:
        yield Container(
            Label("🚨 错误日志查看器", classes="metric-label"),
            Horizontal(
                Input(placeholder="搜索错误日志...", id="error-search-input"),
                Button("搜索", id="search-btn", variant="primary"),
            ),
            Horizontal(
                Label("类型过滤:"),
                Button("全部", id="filter-all-btn", variant="default"),
                Button("处理错误", id="filter-processing-btn", variant="default"),
                Button("网络错误", id="filter-network-btn", variant="default"),
                Button("验证错误", id="filter-validation-btn", variant="default"),
            ),
            DataTable(id="error-log-table", cursor_type="row"),
            Horizontal(
                Button("清除日志", id="clear-logs-btn", variant="error"),
                Button("导出日志", id="export-logs-btn", variant="default"),
                Button("刷新", id="refresh-btn", variant="default")
            )
        )

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._setup_table()
        self._refresh_display()

    def _setup_table(self) -> None:
        """设置表格结构"""
        try:
            table = self.query_one("#error-log-table", DataTable)
            table.add_columns("时间", "类型", "级别", "消息")
        except Exception:
            pass

    def _refresh_display(self) -> None:
        """刷新显示内容"""
        try:
            table = self.query_one("#error-log-table", DataTable)
            table.clear()

            error_logs = self.get_filtered_errors()

            for record in error_logs:
                timestamp = datetime.fromtimestamp(record.timestamp).strftime("%m-%d %H:%M:%S")
                severity_icon = {
                    "debug": "🔍",
                    "info": "ℹ️",
                    "warning": "⚠️",
                    "error": "❌",
                    "critical": "🔥"
                }.get(record.severity, "❓")

                # 高亮搜索词
                message = record.message
                if self.search_term and self.search_term.lower() in message.lower():
                    message = message.replace(self.search_term, f"[bold]{self.search_term}[/bold]")

                table.add_row(
                    timestamp,
                    record.error_type,
                    f"{severity_icon} {record.severity}",
                    message
                )

        except Exception as e:
            log_error(f"刷新错误日志显示失败: {e}")

    def get_all_errors(self, days: int = 30) -> List[ErrorLogRecord]:
        """获取所有错误日志"""
        return self.history_manager.get_error_logs(days=days)

    def get_errors_by_type(self, error_type: str, days: int = 30) -> List[ErrorLogRecord]:
        """按类型获取错误日志"""
        return self.history_manager.get_error_logs(days=days, error_type=error_type)

    def search_errors(self, search_term: str, days: int = 30) -> List[ErrorLogRecord]:
        """搜索错误日志"""
        all_errors = self.get_all_errors(days=days)
        if not search_term:
            return all_errors

        search_lower = search_term.lower()
        return [
            record for record in all_errors
            if (search_lower in record.message.lower() or
                search_lower in record.error_type.lower())
        ]

    def get_filtered_errors(self) -> List[ErrorLogRecord]:
        """获取过滤后的错误日志"""
        if self.search_term:
            return self.search_errors(self.search_term)
        elif self.current_filter != "all":
            return self.get_errors_by_type(self.current_filter)
        else:
            return self.get_all_errors()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        button_id = event.button.id

        if button_id == "refresh-btn":
            self._refresh_display()
        elif button_id == "clear-logs-btn":
            self._clear_logs()
        elif button_id == "export-logs-btn":
            self._export_logs()
        elif button_id == "search-btn":
            self._perform_search()
        elif button_id.startswith("filter-"):
            filter_type = button_id.replace("filter-", "").replace("-btn", "")
            self.current_filter = "all" if filter_type == "all" else filter_type
            self._refresh_display()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理搜索输入提交"""
        if event.input.id == "error-search-input":
            self._perform_search()

    def _perform_search(self) -> None:
        """执行搜索"""
        try:
            search_input = self.query_one("#error-search-input", Input)
            self.search_term = search_input.value.strip()
            self._refresh_display()
        except Exception:
            pass

    def _clear_logs(self) -> None:
        """清除错误日志"""
        try:
            self.history_manager.error_logs.clear()
            self.history_manager.save_history()
            self._refresh_display()
            log_info("错误日志已清除")
        except Exception as e:
            log_error(f"清除错误日志失败: {e}")

    def _export_logs(self) -> None:
        """导出错误日志"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = Path.home() / f"error_logs_{timestamp}.json"

            # 只导出错误相关的数据
            temp_manager = HistoryManager()
            temp_manager.error_logs = self.history_manager.error_logs.copy()

            if temp_manager.export_history(export_path, "json"):
                log_info(f"错误日志已导出到: {export_path}")
            else:
                log_error("导出错误日志失败")
        except Exception as e:
            log_error(f"导出错误日志失败: {e}")


class OperationStatistics(Static):
    """操作统计面板组件"""

    def __init__(self, history_manager: HistoryManager, **kwargs):
        super().__init__(**kwargs)
        self.history_manager = history_manager
        self.stats_period = 30  # 默认统计最近30天

    def compose(self) -> ComposeResult:
        yield Container(
            Label("📊 操作统计面板", classes="metric-label"),
            Horizontal(
                Label("统计周期:"),
                Button("7天", id="period-7-btn", variant="default"),
                Button("30天", id="period-30-btn", variant="primary"),
                Button("90天", id="period-90-btn", variant="default"),
            ),
            Vertical(
                Horizontal(
                    Vertical(
                        Label("总发布次数", classes="metric-label"),
                        Label("0", id="total-publishes", classes="progress-text"),
                    ),
                    Vertical(
                        Label("成功率", classes="metric-label"),
                        Label("0%", id="success-rate", classes="progress-text"),
                    ),
                    Vertical(
                        Label("总处理文件", classes="metric-label"),
                        Label("0", id="total-files", classes="progress-text"),
                    ),
                ),
                Horizontal(
                    Vertical(
                        Label("平均文件数", classes="metric-label"),
                        Label("0", id="avg-files", classes="progress-text"),
                    ),
                    Vertical(
                        Label("平均处理时间", classes="metric-label"),
                        Label("0s", id="avg-duration", classes="progress-text"),
                    ),
                    Vertical(
                        Label("总错误数", classes="metric-label"),
                        Label("0", id="total-errors", classes="progress-text"),
                    ),
                ),
                id="stats-grid"
            ),
            Horizontal(
                Button("刷新统计", id="refresh-stats-btn", variant="primary"),
                Button("导出报告", id="export-report-btn", variant="default"),
                Button("重置统计", id="reset-stats-btn", variant="error")
            )
        )

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._refresh_statistics()

    def get_statistics(self, days: int = None) -> Dict[str, Any]:
        """获取统计数据"""
        period = days or self.stats_period
        return self.history_manager.get_operation_statistics(days=period)

    def _refresh_statistics(self) -> None:
        """刷新统计显示"""
        try:
            stats = self.get_statistics()

            # 更新统计数值
            self._update_label("total-publishes", str(stats.get("total_publishes", 0)))
            self._update_label("success-rate", f"{stats.get('success_rate', 0):.1f}%")
            self._update_label("total-files", str(stats.get("total_files_processed", 0)))
            self._update_label("avg-files", f"{stats.get('avg_files_per_publish', 0):.1f}")
            self._update_label("avg-duration", f"{stats.get('avg_processing_time', 0):.1f}s")
            self._update_label("total-errors", str(stats.get("total_errors", 0)))

        except Exception as e:
            log_error(f"刷新统计数据失败: {e}")

    def _update_label(self, label_id: str, text: str) -> None:
        """更新标签文本"""
        try:
            label = self.query_one(f"#{label_id}", Label)
            label.update(text)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        button_id = event.button.id

        if button_id == "refresh-stats-btn":
            self._refresh_statistics()
        elif button_id == "export-report-btn":
            self._export_report()
        elif button_id == "reset-stats-btn":
            self._reset_statistics()
        elif button_id.startswith("period-"):
            # 提取天数
            period_str = button_id.replace("period-", "").replace("-btn", "")
            self.stats_period = int(period_str)
            self._refresh_statistics()

            # 更新按钮样式
            for btn_id in ["period-7-btn", "period-30-btn", "period-90-btn"]:
                try:
                    btn = self.query_one(f"#{btn_id}", Button)
                    btn.variant = "primary" if btn_id == button_id else "default"
                except:
                    pass

    def _export_report(self) -> None:
        """导出统计报告"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = Path.home() / f"statistics_report_{timestamp}.json"

            # 生成报告数据
            stats = self.get_statistics()
            report_data = {
                "report_time": time.time(),
                "period_days": self.stats_period,
                "statistics": stats,
                "detailed_publish_history": [record.to_dict() for record in self.history_manager.get_publish_history(days=self.stats_period)],
                "detailed_error_logs": [record.to_dict() for record in self.history_manager.get_error_logs(days=self.stats_period)]
            }

            # 保存报告
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            log_info(f"统计报告已导出到: {report_path}")

        except Exception as e:
            log_error(f"导出统计报告失败: {e}")

    def _reset_statistics(self) -> None:
        """重置统计数据"""
        try:
            # 这里提供重置选项，让用户选择要清除的数据
            # 实际实现中可能需要确认对话框
            self.history_manager.clear_history(history_type="all")
            self._refresh_statistics()
            log_info("统计数据已重置")
        except Exception as e:
            log_error(f"重置统计数据失败: {e}")


class HistoryDashboard(Container):
    """历史管理仪表板 - 整合所有历史管理组件"""

    def __init__(self, history_manager: Optional[HistoryManager] = None, **kwargs):
        super().__init__(**kwargs)
        self.history_manager = history_manager or HistoryManager()

    def compose(self) -> ComposeResult:
        """组合所有历史管理组件"""
        yield Container(
            Label("📚 操作历史管理中心", classes="metric-label"),
            id="history-container"
        )

    def get_history_manager(self) -> HistoryManager:
        """获取历史管理器实例"""
        return self.history_manager

    def record_current_operation(self, operation_type: str, data: Dict[str, Any]) -> None:
        """记录当前操作的便捷方法

        Args:
            operation_type: 操作类型 ('file_selection', 'publish', 'error')
            data: 操作数据
        """
        try:
            if operation_type == "file_selection":
                files = data.get("files", [])
                self.history_manager.record_file_selection(files)
            elif operation_type == "publish":
                files = data.get("files", [])
                status = data.get("status", "started")
                message = data.get("message", "")
                duration = data.get("duration", 0.0)
                self.history_manager.record_publish_operation(files, status, message, duration)
            elif operation_type == "error":
                message = data.get("message", "")
                error_type = data.get("error_type", "general")
                severity = data.get("severity", "error")
                context = data.get("context", {})
                self.history_manager.record_error_log(message, error_type, severity, context)
        except Exception as e:
            log_error(f"记录操作失败: {e}")

    def refresh_all_components(self) -> None:
        """刷新所有组件显示"""
        try:
            # 刷新各个标签页的组件
            file_selection = self.query_one("#file-selection-history", FileSelectionHistory)
            file_selection._refresh_display()

            publish_history = self.query_one("#publish-history-timeline", PublishHistoryTimeline)
            publish_history._refresh_display()

            error_viewer = self.query_one("#error-log-viewer", ErrorLogViewer)
            error_viewer._refresh_display()

            statistics = self.query_one("#operation-statistics", OperationStatistics)
            statistics._refresh_statistics()
        except Exception as e:
            log_error(f"刷新历史管理组件失败: {e}")