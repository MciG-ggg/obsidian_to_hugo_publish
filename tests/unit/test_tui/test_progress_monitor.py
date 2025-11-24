"""
进度监控仪表板测试
测试进度条更新、状态显示、错误统计等功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# 模拟导入进度监控组件（我们即将创建的）
from src.tui.progress_components import (
    ProgressMonitor,
    ProcessingProgress,
    CurrentOperationStatus,
    PerformanceMetrics,
    OperationControls,
    ErrorStatistics
)


class TestProgressMonitor:
    """测试进度监控主组件"""

    def test_progress_monitor_creation(self):
        """测试进度监控组件创建"""
        monitor = ProgressMonitor()
        assert monitor.total_tasks == 0
        assert monitor.completed_tasks == 0
        assert monitor.failed_tasks == 0
        assert monitor.progress_percentage == 0.0

    def test_progress_monitor_initial_values(self):
        """测试进度监控初始值设置"""
        monitor = ProgressMonitor(total_tasks=10)
        assert monitor.total_tasks == 10
        assert monitor.completed_tasks == 0
        assert monitor.failed_tasks == 0

    def test_progress_update(self):
        """测试进度更新"""
        monitor = ProgressMonitor(total_tasks=5)

        # 完成第一个任务
        monitor.complete_task()
        assert monitor.completed_tasks == 1
        assert monitor.progress_percentage == 20.0

        # 失败一个任务
        monitor.fail_task("Test error")
        assert monitor.failed_tasks == 1
        assert monitor.completed_tasks == 1  # 完成任务数不变

        # 完成第二个任务
        monitor.complete_task()
        assert monitor.completed_tasks == 2
        assert monitor.progress_percentage == 40.0

    def test_progress_calculation(self):
        """测试进度计算准确性"""
        monitor = ProgressMonitor(total_tasks=4)

        # 完成所有任务
        for i in range(4):
            monitor.complete_task()

        assert monitor.progress_percentage == 100.0
        assert monitor.is_completed() == True

    def test_progress_time_estimation(self):
        """测试时间估算功能"""
        import time

        monitor = ProgressMonitor(total_tasks=10)
        start_time = time.time()

        # 模拟处理一些任务
        time.sleep(0.1)  # 短暂延迟
        monitor.complete_task()
        monitor.complete_task()

        elapsed = time.time() - start_time
        estimated_total = monitor.get_estimated_total_time()

        # 验证估算时间合理（应该大于已用时间）
        assert estimated_total >= elapsed

    def test_error_statistics(self):
        """测试错误统计"""
        monitor = ProgressMonitor()

        # 添加一些错误
        monitor.fail_task("File not found")
        monitor.fail_task("Permission denied")
        monitor.fail_task("Network timeout")

        errors = monitor.get_errors()
        assert len(errors) == 3
        assert errors[0]["message"] == "File not found"
        assert errors[1]["message"] == "Permission denied"
        assert errors[2]["message"] == "Network timeout"

    def test_reset_progress(self):
        """测试重置进度"""
        monitor = ProgressMonitor(total_tasks=5)
        monitor.complete_task()
        monitor.fail_task("Test error")

        monitor.reset()
        assert monitor.total_tasks == 0
        assert monitor.completed_tasks == 0
        assert monitor.failed_tasks == 0
        assert monitor.progress_percentage == 0.0


class TestProcessingProgress:
    """测试处理进度显示组件"""

    def test_progress_bar_update(self):
        """测试进度条更新"""
        progress = ProcessingProgress()

        # 初始状态
        assert progress.current_progress == 0
        assert progress.progress_percentage == 0.0

        # 更新进度
        progress.update_progress(50, 100)
        assert progress.progress_percentage == 50.0

        # 完成状态
        progress.update_progress(100, 100)
        assert progress.progress_percentage == 100.0

    def test_processing_speed_calculation(self):
        """测试处理速度计算"""
        import time

        progress = ProcessingProgress()
        start_time = time.time()

        # 模拟处理
        time.sleep(0.1)
        progress.update_progress(10, 100)  # 处理了10个文件
        progress.update_speed(start_time)

        speed = progress.get_processing_speed()  # 文件/分钟
        assert speed > 0  # 应该有正的处理速度

    def test_remaining_time_estimation(self):
        """测试剩余时间估算"""
        import time

        progress = ProcessingProgress()
        start_time = time.time()

        # 模拟处理一些任务
        time.sleep(0.1)
        progress.update_progress(20, 100)
        progress.update_speed(start_time)

        remaining = progress.get_remaining_time()
        assert remaining > 0  # 应该估算出剩余时间


class TestCurrentOperationStatus:
    """测试当前操作状态组件"""

    def test_status_update(self):
        """测试状态更新"""
        status = CurrentOperationStatus()

        # 初始状态
        assert status.current_operation == "待机"
        assert status.is_active == False

        # 更新操作状态
        status.set_operation("文件转换")
        assert status.current_operation == "文件转换"
        assert status.is_active == True

        # 完成操作
        status.set_operation("待机")
        assert status.current_operation == "待机"
        assert status.is_active == False

    def test_operation_logging(self):
        """测试操作日志记录"""
        status = CurrentOperationStatus()

        # 添加操作日志
        status.add_log("开始处理文章", "info")
        status.add_log("转换Markdown", "info")
        status.add_log("处理图片", "warning")
        status.add_log("上传失败", "error")

        logs = status.get_logs()
        assert len(logs) == 4
        assert logs[0]["message"] == "开始处理文章"
        assert logs[0]["level"] == "info"
        assert logs[3]["level"] == "error"

    def test_log_filtering(self):
        """测试日志过滤"""
        status = CurrentOperationStatus()

        # 添加不同级别的日志
        status.add_log("信息1", "info")
        status.add_log("警告1", "warning")
        status.add_log("错误1", "error")
        status.add_log("信息2", "info")

        # 过滤错误日志
        error_logs = status.get_logs(level="error")
        assert len(error_logs) == 1
        assert error_logs[0]["message"] == "错误1"

        # 过滤警告及以上级别
        warning_logs = status.get_logs(min_level="warning")
        assert len(warning_logs) == 2


class TestPerformanceMetrics:
    """测试性能指标监控组件"""

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_system_metrics_collection(self, mock_memory, mock_cpu):
        """测试系统指标收集"""
        # 模拟psutil返回值
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(percent=60.2)

        metrics = PerformanceMetrics()
        metrics.update_system_metrics()

        assert metrics.cpu_usage == 45.5
        assert metrics.memory_usage == 60.2

    def test_processing_metrics(self):
        """测试处理指标"""
        metrics = PerformanceMetrics()

        # 记录处理时间
        metrics.record_processing_time(1.5)  # 1.5秒
        metrics.record_processing_time(2.0)  # 2.0秒
        metrics.record_processing_time(1.2)  # 1.2秒

        assert metrics.total_processed == 3
        assert metrics.average_processing_time == pytest.approx(1.57, rel=1e-2)

    def test_performance_history(self):
        """测试性能历史记录"""
        metrics = PerformanceMetrics()

        # 添加历史数据点
        metrics.add_history_point(50, 60, 100)  # CPU, Memory, Speed
        metrics.add_history_point(60, 65, 95)
        metrics.add_history_point(45, 58, 110)

        history = metrics.get_performance_history()
        assert len(history) == 3
        assert history[0]["cpu"] == 50
        assert history[0]["memory"] == 60
        assert history[0]["speed"] == 100

    def test_metrics_reset(self):
        """测试指标重置"""
        metrics = PerformanceMetrics()

        # 添加一些数据
        metrics.record_processing_time(1.5)
        metrics.add_history_point(50, 60, 100)

        metrics.reset()
        assert metrics.total_processed == 0
        assert metrics.average_processing_time == 0
        assert len(metrics.get_performance_history()) == 0


class TestOperationControls:
    """测试操作控制组件"""

    def test_initial_controls_state(self):
        """测试初始控制状态"""
        controls = OperationControls()

        assert controls.can_pause == False
        assert controls.can_resume == False
        assert controls.can_cancel == False
        assert controls.is_running == False

    def test_start_operation(self):
        """测试开始操作"""
        controls = OperationControls()

        controls.start_operation()
        assert controls.is_running == True
        assert controls.can_pause == True
        assert controls.can_cancel == True
        assert controls.can_resume == False

    def test_pause_resume_operation(self):
        """测试暂停恢复操作"""
        controls = OperationControls()

        # 开始操作
        controls.start_operation()

        # 暂停操作
        controls.pause_operation()
        assert controls.is_running == False
        assert controls.is_paused == True
        assert controls.can_resume == True
        assert controls.can_pause == False

        # 恢复操作
        controls.resume_operation()
        assert controls.is_running == True
        assert controls.is_paused == False
        assert controls.can_pause == True
        assert controls.can_resume == False

    def test_cancel_operation(self):
        """测试取消操作"""
        controls = OperationControls()

        controls.start_operation()
        controls.cancel_operation()

        assert controls.is_running == False
        assert controls.is_cancelled == True
        assert controls.can_pause == False
        assert controls.can_resume == False
        assert controls.can_cancel == False

    def test_operation_completion(self):
        """测试操作完成"""
        controls = OperationControls()

        controls.start_operation()
        controls.complete_operation()

        assert controls.is_running == False
        assert controls.is_completed == True
        assert controls.can_pause == False
        assert controls.can_resume == False
        assert controls.can_cancel == False


class TestErrorStatistics:
    """测试错误统计组件"""

    def test_error_counting(self):
        """测试错误计数"""
        error_stats = ErrorStatistics()

        # 初始状态
        assert error_stats.total_errors == 0
        assert error_stats.get_error_rate() == 0.0

        # 添加错误
        error_stats.add_error("File not found", "critical")
        error_stats.add_error("Permission denied", "warning")

        assert error_stats.total_errors == 2

        # 设置成功计数并计算错误率
        error_stats.success_count = 8
        assert error_stats.get_error_rate() == 0.2  # 2 errors / 10 total

    def test_error_categories(self):
        """测试错误分类"""
        error_stats = ErrorStatistics()

        # 添加不同类型的错误
        error_stats.add_error("File not found", "critical")
        error_stats.add_error("Network timeout", "network")
        error_stats.add_error("Parse error", "content")
        error_stats.add_error("Invalid config", "config")
        error_stats.add_error("Another timeout", "network")

        categories = error_stats.get_error_categories()
        assert categories["critical"] == 1
        assert categories["network"] == 2
        assert categories["content"] == 1
        assert categories["config"] == 1

    def test_error_details(self):
        """测试错误详情"""
        error_stats = ErrorStatistics()

        # 添加带时间戳的错误
        import time
        timestamp1 = time.time()
        error_stats.add_error("First error", "critical", timestamp1)

        time.sleep(0.1)
        timestamp2 = time.time()
        error_stats.add_error("Second error", "warning", timestamp2)

        errors = error_stats.get_error_details()
        assert len(errors) == 2
        assert errors[0]["message"] == "First error"
        assert errors[1]["message"] == "Second error"
        assert errors[1]["timestamp"] > errors[0]["timestamp"]

    def test_error_recovery_stats(self):
        """测试错误恢复统计"""
        error_stats = ErrorStatistics()

        # 添加一些错误和恢复
        error_stats.add_error("First error", "critical")
        error_stats.record_recovery_attempt("First error", True)

        error_stats.add_error("Second error", "warning")
        error_stats.record_recovery_attempt("Second error", False)
        error_stats.record_recovery_attempt("Second error", True)

        recovery_stats = error_stats.get_recovery_stats()
        assert recovery_stats["total_attempts"] == 3
        assert recovery_stats["successful_recoveries"] == 2
        assert recovery_stats["recovery_rate"] == pytest.approx(0.67, rel=1e-2)


# 集成测试
class TestProgressMonitorIntegration:
    """测试进度监控组件集成"""

    def test_full_workflow_simulation(self):
        """测试完整工作流程模拟"""
        # 创建所有组件
        monitor = ProgressMonitor(total_tasks=5)
        progress = ProcessingProgress()
        status = CurrentOperationStatus()
        metrics = PerformanceMetrics()
        controls = OperationControls()
        error_stats = ErrorStatistics()

        # 开始操作
        controls.start_operation()
        status.set_operation("文件转换")

        # 模拟处理过程
        for i in range(5):
            status.add_log(f"处理文件 {i+1}", "info")
            progress.update_progress(i+1, 5)
            monitor.complete_task()
            metrics.record_processing_time(1.0 + i * 0.1)

            # 模拟一个错误
            if i == 2:
                error_stats.add_error(f"文件 {i+1} 处理失败", "warning")
                monitor.fail_task(f"文件 {i+1} 错误")

        # 完成操作
        status.set_operation("待机")
        controls.complete_operation()

        # 验证结果
        assert monitor.completed_tasks == 5
        assert monitor.progress_percentage == 100.0
        assert progress.progress_percentage == 100.0
        assert controls.is_completed == True
        assert error_stats.total_errors == 1
        assert metrics.total_processed == 5

    @pytest.mark.asyncio
    async def test_async_progress_updates(self):
        """测试异步进度更新"""
        monitor = ProgressMonitor(total_tasks=3)
        status = CurrentOperationStatus()

        async def simulate_processing():
            """模拟异步处理"""
            for i in range(3):
                status.add_log(f"异步处理 {i+1}", "info")
                monitor.complete_task()
                await asyncio.sleep(0.01)  # 模拟处理时间

        # 开始异步处理
        status.set_operation("异步处理")
        await simulate_processing()
        status.set_operation("待机")

        # 验证结果
        assert monitor.completed_tasks == 3
        assert monitor.progress_percentage == 100.0
        logs = status.get_logs()
        assert len(logs) == 3


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])