"""
历史管理核心功能
提供文件选择历史、发布历史时间线、错误日志查看、操作统计等功能
不包含复杂的Textual UI组件，专注核心功能
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

    def get_recent_file_selections(self, limit: int = 10) -> List[FileSelectionRecord]:
        """获取最近的文件选择记录"""
        return self.file_selection_history[-limit:] if limit > 0 else self.file_selection_history

    def get_most_common_files(self, limit: int = 20) -> List[Tuple[str, int]]:
        """获取最常选择的文件"""
        file_counter = Counter()
        for record in self.file_selection_history:
            file_counter.update(record.files)

        return file_counter.most_common(limit)

    def get_last_successful_publish(self) -> Optional[PublishOperationRecord]:
        """获取最近一次成功的发布操作"""
        successful_publishes = self.get_publish_history(days=30, status_filter="success")
        return successful_publishes[0] if successful_publishes else None

    def search_error_logs(self, search_term: str, days: int = 30) -> List[ErrorLogRecord]:
        """搜索错误日志"""
        all_errors = self.get_error_logs(days=days)
        if not search_term:
            return all_errors

        search_lower = search_term.lower()
        return [
            record for record in all_errors
            if (search_lower in record.message.lower() or
                search_lower in record.error_type.lower())
        ]

    def undo_last_publish_operation(self) -> Optional[PublishOperationRecord]:
        """获取最近一次发布操作用于撤销"""
        recent_publishes = self.get_publish_history(days=30)
        return recent_publishes[0] if recent_publishes else None