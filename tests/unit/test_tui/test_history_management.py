"""
历史管理功能单元测试
测试历史记录存储、检索、过滤功能
"""

import pytest
import time
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 导入要测试的历史管理组件
try:
    from src.tui.history_components import (
        HistoryManager,
        FileSelectionHistory,
        PublishHistoryTimeline,
        ErrorLogViewer,
        OperationStatistics,
        HistoryManagerError
    )
except ImportError:
    pytest.skip("历史管理组件尚未实现", allow_module_level=True)


class TestHistoryManager:
    """历史管理器核心功能测试"""

    def test_history_manager_initialization(self):
        """测试历史管理器初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"

            manager = HistoryManager(history_file)

            assert manager.history_file == history_file
            assert isinstance(manager.file_selection_history, list)
            assert isinstance(manager.publish_history, list)
            assert isinstance(manager.error_logs, list)
            assert isinstance(manager.operation_stats, dict)

    def test_save_and_load_history(self):
        """测试历史记录保存和加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"

            # 创建管理器并添加测试数据
            manager = HistoryManager(history_file)
            manager.record_file_selection(["test1.md", "test2.md"])
            manager.record_publish_operation(["test1.md"], "success", "发布完成")

            # 保存历史
            manager.save_history()
            assert history_file.exists()

            # 创建新管理器并加载历史
            new_manager = HistoryManager(history_file)
            new_manager.load_history()

            assert len(new_manager.file_selection_history) == 1
            assert len(new_manager.publish_history) == 1
            assert new_manager.file_selection_history[0]["files"] == ["test1.md", "test2.md"]

    def test_record_file_selection(self):
        """测试文件选择记录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            selected_files = ["article1.md", "article2.md"]
            manager.record_file_selection(selected_files)

            assert len(manager.file_selection_history) == 1
            record = manager.file_selection_history[0]
            assert record["files"] == selected_files
            assert "timestamp" in record
            assert record["count"] == 2

    def test_record_publish_operation(self):
        """测试发布操作记录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            files = ["post1.md"]
            status = "success"
            message = "发布成功"
            manager.record_publish_operation(files, status, message)

            assert len(manager.publish_history) == 1
            record = manager.publish_history[0]
            assert record["files"] == files
            assert record["status"] == status
            assert record["message"] == message
            assert "timestamp" in record
            assert "duration" in record

    def test_record_error_log(self):
        """测试错误日志记录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            error_message = "文件处理失败"
            error_type = "processing_error"
            manager.record_error_log(error_message, error_type)

            assert len(manager.error_logs) == 1
            record = manager.error_logs[0]
            assert record["message"] == error_message
            assert record["type"] == error_type
            assert "timestamp" in record

    def test_filter_publish_history_by_date(self):
        """测试按日期过滤发布历史"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            # 添加不同时间的发布记录
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            last_week = now - timedelta(days=7)

            # 模拟不同时间的历史记录
            with patch('time.time') as mock_time:
                mock_time.return_value = now.timestamp()
                manager.record_publish_operation(["new.md"], "success", "最新发布")

                mock_time.return_value = yesterday.timestamp()
                manager.record_publish_operation(["yesterday.md"], "success", "昨天发布")

                mock_time.return_value = last_week.timestamp()
                manager.record_publish_operation(["old.md"], "failed", "上周发布")

            # 测试日期过滤
            recent_history = manager.get_publish_history(days=2)
            assert len(recent_history) == 2  # 今天和昨天的

            week_history = manager.get_publish_history(days=7)
            assert len(week_history) == 3  # 所有记录

    def test_get_operation_statistics(self):
        """测试操作统计功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            # 添加一些操作记录
            manager.record_publish_operation(["file1.md"], "success", "成功")
            manager.record_publish_operation(["file2.md"], "success", "成功")
            manager.record_publish_operation(["file3.md"], "failed", "失败")
            manager.record_error_log("测试错误", "test")

            stats = manager.get_operation_statistics()

            assert stats["total_publishes"] == 3
            assert stats["successful_publishes"] == 2
            assert stats["failed_publishes"] == 1
            assert stats["success_rate"] == 2/3 * 100
            assert stats["total_errors"] == 1


class TestFileSelectionHistory:
    """文件选择历史测试"""

    def test_file_selection_history_component(self):
        """测试文件选择历史组件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            # 添加一些选择历史
            manager.record_file_selection(["file1.md", "file2.md"])
            manager.record_file_selection(["file3.md"])

            component = FileSelectionHistory(manager)

            # 测试获取最近选择
            recent = component.get_recent_selections(limit=5)
            assert len(recent) == 2
            assert recent[0]["files"] == ["file3.md"]  # 最新的在前

            # 测试获取最常选择的文件
            common_files = component.get_most_common_files(limit=3)
            # file1.md和file2.md各出现一次，file3.md出现一次
            assert len(common_files) <= 3

    def test_quick_reslection_functionality(self):
        """测试快速重选功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            component = FileSelectionHistory(manager)

            # 记录一个选择历史
            selected_files = ["article1.md", "article2.md"]
            manager.record_file_selection(selected_files)

            # 测试快速重选
            reselected_files = component.quick_reselect(index=0)
            assert reselected_files == selected_files


class TestPublishHistoryTimeline:
    """发布历史时间线测试"""

    def test_publish_timeline_component(self):
        """测试发布历史时间线组件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            component = PublishHistoryTimeline(manager)

            # 添加发布历史
            manager.record_publish_operation(["file1.md"], "success", "发布成功")
            manager.record_publish_operation(["file2.md"], "failed", "发布失败")

            # 测试获取时间线数据
            timeline_data = component.get_timeline_data()
            assert len(timeline_data) == 2
            assert timeline_data[0]["status"] == "failed"  # 最新的在前
            assert timeline_data[1]["status"] == "success"

    def test_timeline_filtering(self):
        """测试时间线过滤功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            component = PublishHistoryTimeline(manager)

            # 添加不同状态的发布记录
            manager.record_publish_operation(["file1.md"], "success", "成功")
            manager.record_publish_operation(["file2.md"], "failed", "失败")
            manager.record_publish_operation(["file3.md"], "success", "成功")

            # 测试按状态过滤
            success_only = component.get_timeline_data(status_filter="success")
            assert len(success_only) == 2
            assert all(record["status"] == "success" for record in success_only)

            failed_only = component.get_timeline_data(status_filter="failed")
            assert len(failed_only) == 1
            assert failed_only[0]["status"] == "failed"


class TestErrorLogViewer:
    """错误日志查看器测试"""

    def test_error_log_viewer_component(self):
        """测试错误日志查看器组件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            component = ErrorLogViewer(manager)

            # 添加不同类型的错误
            manager.record_error_log("处理错误", "processing")
            manager.record_error_log("网络错误", "network")
            manager.record_error_log("处理错误2", "processing")

            # 测试获取所有错误
            all_errors = component.get_all_errors()
            assert len(all_errors) == 3

            # 测试按类型过滤
            processing_errors = component.get_errors_by_type("processing")
            assert len(processing_errors) == 2

            network_errors = component.get_errors_by_type("network")
            assert len(network_errors) == 1

    def test_error_log_searching(self):
        """测试错误日志搜索功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            component = ErrorLogViewer(manager)

            # 添加可搜索的错误
            manager.record_error_log("文件 file1.md 处理失败", "processing")
            manager.record_error_log("网络连接超时", "network")
            manager.record_error_log("文件 file2.md 格式错误", "validation")

            # 测试搜索
            search_results = component.search_errors("file1")
            assert len(search_results) == 1
            assert "file1.md" in search_results[0]["message"]

            search_results = component.search_errors("文件")
            assert len(search_results) == 2  # 包含"文件"的错误


class TestOperationStatistics:
    """操作统计面板测试"""

    def test_operation_statistics_component(self):
        """测试操作统计面板组件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            component = OperationStatistics(manager)

            # 添加操作数据
            manager.record_publish_operation(["file1.md"], "success", "成功")
            manager.record_publish_operation(["file2.md"], "success", "成功")
            manager.record_publish_operation(["file3.md"], "failed", "失败")

            # 测试获取统计数据
            stats = component.get_statistics()
            assert stats["total_publishes"] == 3
            assert stats["success_rate"] == 66.7  # 2/3 * 100，保留一位小数

    def test_time_period_statistics(self):
        """测试时间段统计功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            component = OperationStatistics(manager)

            # 模拟不同时期的操作
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            with patch('time.time') as mock_time:
                mock_time.return_value = now.timestamp()
                manager.record_publish_operation(["new.md"], "success", "最新")

                mock_time.return_value = week_ago.timestamp()
                manager.record_publish_operation(["week_old.md"], "success", "一周前")

                mock_time.return_value = month_ago.timestamp()
                manager.record_publish_operation(["month_old.md"], "failed", "一月前")

            # 测试本周统计
            week_stats = component.get_statistics(days=7)
            assert week_stats["total_publishes"] == 2  # 本周的发布

            # 测试本月统计
            month_stats = component.get_statistics(days=30)
            assert month_stats["total_publishes"] == 3  # 本月的发布


class TestHistoryPersistence:
    """历史持久化测试"""

    def test_history_file_creation_and_permissions(self):
        """测试历史文件创建和权限"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"

            manager = HistoryManager(history_file)
            manager.record_file_selection(["test.md"])
            manager.save_history()

            assert history_file.exists()
            assert os.access(history_file, os.R_OK)
            assert os.access(history_file, os.W_OK)

    def test_corrupted_history_handling(self):
        """测试损坏历史文件的处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"

            # 创建损坏的历史文件
            with open(history_file, 'w') as f:
                f.write("invalid json content")

            # 管理器应该能处理损坏的文件
            manager = HistoryManager(history_file)

            # 应该能正常加载，不会崩溃
            try:
                manager.load_history()
                # 加载后应该有默认的空数据结构
                assert isinstance(manager.file_selection_history, list)
                assert isinstance(manager.publish_history, list)
            except Exception as e:
                pytest.fail(f"处理损坏历史文件时抛出异常: {e}")

    def test_large_history_performance(self):
        """测试大量历史数据的性能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            # 添加大量历史记录
            start_time = time.time()
            for i in range(1000):
                manager.record_error_log(f"错误消息 {i}", "test")

            add_time = time.time() - start_time

            # 测试保存性能
            start_time = time.time()
            manager.save_history()
            save_time = time.time() - start_time

            # 测试加载性能
            new_manager = HistoryManager(history_file)
            start_time = time.time()
            new_manager.load_history()
            load_time = time.time() - start_time

            # 验证性能在合理范围内（这些时间限制可能需要根据实际情况调整）
            assert add_time < 5.0  # 添加1000条记录应在5秒内
            assert save_time < 2.0  # 保存应在2秒内
            assert load_time < 2.0  # 加载应在2秒内
            assert len(new_manager.error_logs) == 1000


class TestHistoryIntegration:
    """历史管理集成测试"""

    def test_end_to_end_history_workflow(self):
        """端到端历史管理工作流测试"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"
            manager = HistoryManager(history_file)

            # 模拟完整的工作流程
            # 1. 用户选择文件
            selected_files = ["article1.md", "article2.md"]
            manager.record_file_selection(selected_files)

            # 2. 开始发布操作
            manager.record_publish_operation(selected_files, "started", "开始发布")

            # 3. 记录处理过程中的错误
            manager.record_error_log("处理article2.md时出错", "processing")

            # 4. 部分成功
            manager.record_publish_operation(["article1.md"], "success", "article1发布成功")

            # 5. 验证历史数据完整性
            stats = manager.get_operation_statistics()
            assert stats["total_publishes"] == 2  # started + success
            assert stats["total_errors"] == 1
            assert len(manager.file_selection_history) == 1

            # 6. 测试历史查询功能
            recent_publishes = manager.get_publish_history(days=1)
            assert len(recent_publishes) == 2

    def test_concurrent_history_access(self):
        """测试并发历史访问"""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.json"

            # 创建多个管理器实例模拟并发访问
            manager1 = HistoryManager(history_file)
            manager2 = HistoryManager(history_file)

            # 模拟并发操作
            manager1.record_file_selection(["file1.md"])
            manager2.record_error_log("并发错误", "concurrent")

            manager1.save_history()
            manager2.load_history()

            # 验证数据一致性
            assert len(manager2.file_selection_history) == 1
            assert len(manager2.error_logs) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])