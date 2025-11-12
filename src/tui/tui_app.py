"""
TUI应用主类
基于Textual框架实现简洁的博客发布界面
专注于文件选择、预览和发布功能
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import (
    Header, Footer, Static, Log,
    DataTable, Tree, Label, Input
)
from textual.reactive import reactive
from textual.binding import Binding
from textual.screen import Screen

# 修改为绝对导入
from src.core.config_manager import Config
from src.core.blog_processor import BlogProcessor
from src.i18n.i18n import t
from src.utils.logger import info as log_info, error as log_error, warning as print_warning


class BTopStyle:
    """btop风格的颜色主题和样式"""

    # 基于现有CLIColors的颜色定义，适配Textual格式
    COLORS = {
        "background": "#0d1117",      # 深蓝色背景
        "surface": "#161b22",         # 表面颜色
        "primary": "#58a6ff",         # 亮青色主色调
        "secondary": "#f85149",       # 橙色强调色
        "success": "#3fb950",         # 成功绿色
        "warning": "#d29922",         # 警告黄色
        "error": "#f85149",           # 错误红色
        "text": "#c9d1d9",           # 主要文本颜色
        "text_dim": "#8b949e",       # 暗色文本
        "border": "#30363d",         # 边框颜色
    }

    CSS = f"""
    Screen {{
        background: {COLORS["background"]};
        color: {COLORS["text"]};
    }}

    .btop-panel {{
        background: {COLORS["surface"]};
        border: solid {COLORS["border"]};
        padding: 1;
        margin: 1;
        height: 100%;
    }}

    .status-bar {{
        background: {COLORS["surface"]};
        color: {COLORS["text"]};
        text-align: center;
        padding: 0 1;
        height: 3;
        dock: top;
    }}

    .metric-label {{
        color: {COLORS["text_dim"]};
        text-style: bold;
        margin: 1 0;
    }}

    .preview-content {{
        background: {COLORS["background"]};
        border: solid {COLORS["border"]};
        padding: 1;
        margin: 1 0;
        height: 50%;
        overflow-y: auto;
    }}

    #main-container {{
        height: 100%;
    }}

    #files-panel {{
        width: 40%;
    }}

    #preview-panel {{
        width: 60%;
    }}

    Header {{
        background: {COLORS["surface"]};
        color: {COLORS["text"]};
        text-align: center;
    }}

    Footer {{
        background: {COLORS["surface"]};
        color: {COLORS["text"]};
    }}

    DataTable {{
        background: {COLORS["surface"]};
        border: solid {COLORS["border"]};
    }}

    Tree {{
        background: {COLORS["surface"]};
        border: solid {COLORS["border"]};
    }}

    Log {{
        background: {COLORS["surface"]};
        border: solid {COLORS["border"]};
    }}

    
    Input {{
        background: {COLORS["surface"]};
        border: solid {COLORS["border"]};
        color: {COLORS["text"]};
    }}

    .progress-text {{
        text-align: center;
        color: {COLORS["primary"]};
        text-style: bold;
    }}
    """




class StatusBar(Static):
    """顶部状态栏 - 模仿btop的布局"""

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label("博客发布工具 TUI", id="app-title"),
            Label("", id="current-time"),
            Label("状态: 就绪", id="status-indicator"),
            id="status-content"
        )

    def on_mount(self) -> None:
        """组件挂载时启动时间更新"""
        self.update_time()
        self.set_interval(1.0, self.update_time)

    def update_time(self) -> None:
        """更新当前时间显示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_label = self.query_one("#current-time", Label)
        time_label.update(current_time)

    def update_status(self, status: str, status_type: str = "info") -> None:
        """更新状态指示器"""
        status_label = self.query_one("#status-indicator", Label)
        status_map = {
            "info": f"状态: {status}",
            "success": f"✓ 状态: {status}",
            "warning": f"⚠ 状态: {status}",
            "error": f"✗ 状态: {status}"
        }
        status_label.update(status_map.get(status_type, status_map["info"]))


class FileSelector(Static):
    """文件选择器组件"""

    selected_files: reactive[List[str]] = reactive([])

    def compose(self) -> ComposeResult:
        yield Container(
            Label("文件选择", classes="metric-label"),
            Input(placeholder="搜索文件...", id="file-search"),
            Tree("Obsidian文件", id="file-tree"),
            DataTable(id="selected-files-table"),
            id="file-selector-content"
        )

    def on_mount(self) -> None:
        """组件挂载时初始化文件树"""
        self.load_files()
        self.setup_selected_table()

    def load_files(self) -> None:
        """加载可发布的文件树"""
        try:
            config = Config()
            obsidian_path = Path(config.get('paths.obsidian.vault', '')).expanduser()

            if not obsidian_path.exists():
                log_error(f"Obsidian路径不存在: {obsidian_path}")
                return

            # 使用与CLI相同的逻辑获取可发布文件
            from src.core.blog_processor import BlogProcessor
            processor = BlogProcessor(obsidian_path, "")
            published_files = processor.list_published_markdowns()

            if not published_files:
                log_error("没有找到可发布的文章")
                return

            tree = self.query_one("#file-tree", Tree)
            tree.root.expand()

            # 清空现有树内容
            tree.clear()
            tree.root.expand()

            # 使用字典来构建树形结构
            folder_nodes = {}

            # 查找所有可发布的Markdown文件
            for md_file, front_matter in published_files:
                relative_path = md_file.relative_to(obsidian_path)
                folder_path = str(relative_path.parent)

                # 获取或创建文件夹节点
                if folder_path not in folder_nodes:
                    if folder_path == ".":
                        # 根目录文件
                        folder_node = tree.root
                    else:
                        # 创建文件夹节点
                        folder_parts = folder_path.split("/")
                        parent = tree.root
                        current_path = ""

                        for part in folder_parts:
                            current_path += f"/{part}" if current_path else part
                            if current_path not in folder_nodes:
                                folder_nodes[current_path] = parent.add(
                                    part,
                                    expand=True,
                                    data={"type": "folder", "path": current_path}
                                )
                            parent = folder_nodes[current_path]
                        folder_node = folder_nodes[current_path]
                else:
                    folder_node = folder_nodes[folder_path]

                # 使用文章标题作为显示名，如果没有则使用文件名
                title = None
                if front_matter and hasattr(front_matter, 'title') and front_matter.title:
                    title = str(front_matter.title) if not isinstance(front_matter.title, str) else front_matter.title

                if not title:
                    title = md_file.stem

                # 添加文件节点
                folder_node.add_leaf(
                    title,
                    data={
                        "type": "file",
                        "path": str(md_file),
                        "front_matter": front_matter
                    }
                )

            # 更新状态栏显示文件数量
            total_files = len(published_files)

            if hasattr(self.app, 'update_status'):
                self.app.update_status(f"找到 {total_files} 个可发布文章")

        except Exception as e:
            log_error(f"加载文件树失败: {e}")

    def count_files_in_tree(self, node) -> int:
        """递归计算树中的文件数量"""
        count = 0
        if hasattr(node, 'data') and node.data and node.data.get("type") == "file":
            count += 1
        for child in node.children:
            count += self.count_files_in_tree(child)
        return count

    
    def setup_selected_table(self) -> None:
        """设置已选择文件表格"""
        table = self.query_one("#selected-files-table", DataTable)
        table.add_column("文件名", key="filename")
        table.add_column("路径", key="path")

    def on_input_changed(self, event: Input.Changed) -> None:
        """搜索输入变化时过滤文件"""
        if event.input.id == "file-search":
            self.filter_files(event.value)

    def filter_files(self, search_term: str) -> None:
        """过滤文件列表"""
        # TODO: 实现文件搜索过滤逻辑
        pass

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """文件树节点选择事件"""
        if event.node.data and event.node.data.get("type") == "file":
            file_data = event.node.data
            filename = file_data["path"]
            title = event.node.label  # 文章标题
            self.add_selected_file(title, filename)

    def add_selected_file(self, title: str, filepath: str) -> None:
        """添加选中文件到表格"""
        table = self.query_one("#selected-files-table", DataTable)
        table.add_row(title, filepath)


class MainScreen(Screen):
    """主界面屏幕"""

    BINDINGS = [
        Binding("q", "quit", "退出", priority=True),
        Binding("f1", "help", "帮助"),
        Binding("f2", "files", "文件选择"),
        Binding("f3", "preview", "预览"),
        Binding("f5", "refresh", "刷新"),
        Binding("ctrl+c", "quit", "退出"),
    ]

    def compose(self) -> ComposeResult:
        """构建主界面布局"""
        yield StatusBar(classes="status-bar")

        with Horizontal(id="main-container"):
            # 左侧面板 - 文件选择器
            with Container(classes="btop-panel", id="files-panel"):
                yield FileSelector()

            # 右侧面板 - 预览和日志
            with Container(classes="btop-panel", id="preview-panel"):
                yield Label("文件预览", classes="metric-label", id="preview-title")
                yield Static("选择文件查看预览", id="preview-content", classes="preview-content")
                yield Label("操作日志", classes="metric-label", id="log-title")
                yield Log(id="operation-log")

        yield Footer()

    def on_mount(self) -> None:
        """屏幕挂载时的初始化"""
        self.update_log("TUI界面启动完成", "success")
        log_info("TUI界面启动")

    def update_log(self, message: str, log_type: str = "info") -> None:
        """更新操作日志"""
        log_widget = self.query_one("#operation-log", Log)
        timestamp = datetime.now().strftime("%H:%M:%S")

        type_icons = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗"
        }

        icon = type_icons.get(log_type, "ℹ")
        log_widget.write(f"[{timestamp}] {icon} {message}")

    def action_quit(self) -> None:
        """退出应用"""
        self.app.exit()

    def action_help(self) -> None:
        """显示帮助"""
        self.update_log("F1: 帮助 F2: 文件选择 F3: 预览 F4: 监控 F5: 刷新 Ctrl+C: 退出", "info")

    def action_files(self) -> None:
        """切换到文件选择"""
        self.update_log("切换到文件选择模式", "info")

    def action_preview(self) -> None:
        """切换到预览模式"""
        self.update_log("切换到预览模式", "info")

    def action_monitor(self) -> None:
        """切换到监控模式"""
        self.update_log("切换到监控模式", "info")

    def action_refresh(self) -> None:
        """刷新数据"""
        self.update_log("刷新数据", "info")
        # TODO: 实现具体刷新逻辑

    
    def start_publish(self) -> None:
        """开始发布流程"""
        try:
            # 获取配置
            config = Config()
            source_dir = Path(config.get('paths.obsidian.vault')).expanduser()
            hugo_dir = Path(config.get('paths.hugo.blog')).expanduser()

            # 验证路径
            if not source_dir.exists():
                self.update_log(f"Obsidian路径不存在: {source_dir}", "error")
                return

            if not hugo_dir.exists():
                self.update_log(f"Hugo路径不存在: {hugo_dir}", "error")
                return

            # 创建博客处理器
            processor = BlogProcessor(source_dir, hugo_dir)

            # 这里应该获取选中的文件列表
            selected_files = []  # TODO: 从FileSelector获取选中文件

            self.update_log(f"开始处理 {len(selected_files) if selected_files else '所有'} 文件", "info")

            # TODO: 在后台线程中处理文件
            # 由于这是同步操作，会阻塞UI，后续需要实现异步处理

        except Exception as e:
            self.update_log(f"发布失败: {str(e)}", "error")
            log_error(f"TUI发布失败: {e}")

    def preview_selected(self) -> None:
        """预览选中的文件"""
        # TODO: 实现文件预览功能
        self.update_log("预览功能开发中...", "warning")


class BlogPublishApp(App):
    """博客发布TUI应用主类"""

    CSS = BTopStyle.CSS
    TITLE = "博客发布工具 - TUI"

    def __init__(self):
        super().__init__()
        self.config: Optional[Config] = None
        self.processor: Optional[BlogProcessor] = None

    def on_mount(self) -> None:
        """应用启动时的初始化"""
        try:
            # 加载配置
            self.config = Config()

            # 创建博客处理器
            obsidian_path = Path(self.config.get('paths.obsidian.vault')).expanduser()
            hugo_path = Path(self.config.get('paths.hugo.blog')).expanduser()

            if obsidian_path.exists() and hugo_path.exists():
                self.processor = BlogProcessor(obsidian_path, hugo_path)
                log_info("博客处理器初始化成功")
            else:
                log_error("路径配置错误，无法初始化博客处理器")

            # 推入主屏幕
            self.push_screen(MainScreen())

        except Exception as e:
            log_error(f"TUI应用初始化失败: {e}")
            self.exit()

    
    def get_config(self) -> Config:
        """获取配置实例"""
        if not self.config:
            self.config = Config()
        return self.config

    def get_processor(self) -> Optional[BlogProcessor]:
        """获取博客处理器实例"""
        return self.processor