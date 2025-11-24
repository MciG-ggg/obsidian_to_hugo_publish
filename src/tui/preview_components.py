"""
TUI预览功能组件 - 修复版本
提供Markdown渲染、同步滚动、前置数据编辑等功能
"""

import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import (
    Static, Label, Input, Button, TextArea,
    Tabs, TabPane, TabbedContent, ProgressBar
)
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from textual import events

from src.core.front_matter import FrontMatter, extract_yaml_and_content
from src.core.blog_processor import BlogProcessor
from src.utils.logger import info as log_info, error as log_error


class MarkdownViewer(Static):
    """Markdown内容查看器，支持语法高亮"""

    content: reactive[str] = reactive("")
    scroll_position: reactive[float] = reactive(0.0)
    sync_partner: Optional['MarkdownViewer'] = None

    def __init__(self, id: str = None, classes: str = None):
        super().__init__(id=id, classes=classes)
        self.can_focus = True

    def compose(self) -> ComposeResult:
        """构建Markdown查看器界面"""
        with ScrollableContainer(id="markdown-scroll"):
            yield Static(self.content, id="markdown-content")

    def update_content(self, content: str) -> None:
        """更新Markdown内容"""
        self.content = content
        try:
            content_widget = self.query_one("#markdown-content", Static)
            # 基础的Markdown格式化
            formatted_content = self._format_markdown(content)
            content_widget.update(formatted_content)
        except Exception as e:
            log_error(f"更新Markdown内容失败: {e}")

    def _format_markdown(self, content: str) -> str:
        """基础的Markdown格式化"""
        if not content:
            return "空内容"

        lines = content.split('\n')
        formatted_lines = []

        for line in lines:
            # 标题
            if line.startswith('# '):
                formatted_lines.append(f"[bold blue]{line}[/bold blue]")
            elif line.startswith('## '):
                formatted_lines.append(f"[bold cyan]{line}[/bold cyan]")
            elif line.startswith('### '):
                formatted_lines.append(f"[bold green]{line}[/bold green]")
            # 代码块
            elif line.startswith('```'):
                formatted_lines.append(f"[dim yellow]{line}[/dim yellow]")
            # 引用
            elif line.startswith('>'):
                formatted_lines.append(f"[italic dim]{line}[/italic dim]")
            # 列表项
            elif re.match(r'^\s*[-*+]\s+', line):
                formatted_lines.append(f"  {line}")
            # 链接
            else:
                line = re.sub(
                    r'\[([^\]]+)\]\(([^)]+)\)',
                    r'[blue underline]\1[/blue underline] (\2)',
                    line
                )
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    def setup_sync_scroll(self, partner: 'MarkdownViewer') -> None:
        """设置同步滚动"""
        self.sync_partner = partner

    def on_mouse_scroll_up(self, event) -> None:
        """处理鼠标向上滚动事件"""
        self._handle_scroll()

    def on_mouse_scroll_down(self, event) -> None:
        """处理鼠标向下滚动事件"""
        self._handle_scroll()

    def _handle_scroll(self) -> None:
        """处理滚动逻辑"""
        # 更新滚动位置
        try:
            scroll_container = self.query_one("#markdown-scroll", ScrollableContainer)
            self.scroll_position = scroll_container.scroll_y

            # 同步到伙伴组件
            if self.sync_partner:
                try:
                    partner_scroll = self.sync_partner.query_one("#markdown-scroll", ScrollableContainer)
                    partner_scroll.scroll_y = self.scroll_position
                except Exception:
                    pass
        except Exception:
            pass


class FrontMatterEditor(Static):
    """前置数据编辑器"""

    front_matter: reactive[Optional[FrontMatter]] = reactive(None)
    edit_mode: reactive[bool] = reactive(False)

    class DataChanged(Message):
        """前置数据变更消息"""
        def __init__(self, field: str, value: Any) -> None:
            super().__init__()
            self.field = field
            self.value = value

    def compose(self) -> ComposeResult:
        """构建前置数据编辑器界面"""
        with Vertical(id="front-matter-container"):
            yield Label("📝 文章元数据", classes="metric-label")

            # 显示模式
            with Vertical(id="display-mode"):
                yield Static("", id="fm-display")

            # 编辑模式
            with Vertical(id="edit-mode"):
                yield Input(placeholder="标题", id="fm-title")
                yield Input(placeholder="描述", id="fm-description")
                yield Input(placeholder="标签 (逗号分隔)", id="fm-tags")
                yield Input(placeholder="分类 (逗号分隔)", id="fm-categories")
                yield Input(placeholder="发布日期 (YYYY-MM-DD)", id="fm-date")

                with Horizontal(id="fm-buttons"):
                    yield Button("保存", id="fm-save", variant="success")
                    yield Button("取消", id="fm-cancel", variant="error")

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        # 默认隐藏编辑模式
        try:
            edit_mode = self.query_one("#edit-mode", Vertical)
            edit_mode.display = False
            edit_mode.visible = False
        except:
            pass  # 在测试环境中忽略错误

    def load_front_matter(self, front_matter: FrontMatter) -> None:
        """加载前置数据"""
        self.front_matter = front_matter
        self._update_display()

    def _update_display(self) -> None:
        """更新显示"""
        if not self.front_matter:
            self.query_one("#fm-display", Static).update("无前置数据")
            return

        # 构建显示文本
        lines = []
        fm = self.front_matter

        if fm.title:
            lines.append(f"[bold]标题:[/bold] {fm.title}")

        if fm.description:
            lines.append(f"[bold]描述:[/bold] {fm.description}")

        if fm.tags:
            tags_str = ', '.join(fm.tags) if isinstance(fm.tags, list) else str(fm.tags)
            lines.append(f"[bold]标签:[/bold] {tags_str}")

        if fm.categories:
            cats_str = ', '.join(fm.categories) if isinstance(fm.categories, list) else str(fm.categories)
            lines.append(f"[bold]分类:[/bold] {cats_str}")

        if fm.date:
            lines.append(f"[bold]日期:[/bold] {fm.date}")

        lines.append(f"[bold]草稿:[/bold] {'是' if fm.draft else '否'}")
        lines.append(f"[bold]发布:[/bold] {'是' if fm.publish else '否'}")

        display_text = '\n'.join(lines)
        self.query_one("#fm-display", Static).update(display_text)

    def enable_edit_mode(self) -> None:
        """启用编辑模式"""
        if not self.front_matter:
            return

        self.edit_mode = True

        # 填充当前值
        fm = self.front_matter
        self.query_one("#fm-title", Input).value = fm.title or ""
        self.query_one("#fm-description", Input).value = fm.description or ""

        if fm.tags:
            tags_str = ', '.join(fm.tags) if isinstance(fm.tags, list) else str(fm.tags)
            self.query_one("#fm-tags", Input).value = tags_str

        if fm.categories:
            cats_str = ', '.join(fm.categories) if isinstance(fm.categories, list) else str(fm.categories)
            self.query_one("#fm-categories", Input).value = cats_str

        if fm.date:
            self.query_one("#fm-date", Input).value = str(fm.date)

        # 切换显示
        try:
            self.query_one("#display-mode", Vertical).display = False
            self.query_one("#display-mode", Vertical).visible = False
            self.query_one("#edit-mode", Vertical).display = True
            self.query_one("#edit-mode", Vertical).visible = True
        except:
            pass  # 在测试环境中忽略错误

    def disable_edit_mode(self) -> None:
        """禁用编辑模式"""
        self.edit_mode = False
        try:
            self.query_one("#display-mode", Vertical).display = True
            self.query_one("#display-mode", Vertical).visible = True
            self.query_one("#edit-mode", Vertical).display = False
            self.query_one("#edit-mode", Vertical).visible = False
        except:
            pass  # 在测试环境中忽略错误

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮事件"""
        if event.button.id == "fm-save":
            self._save_changes()
        elif event.button.id == "fm-cancel":
            self.disable_edit_mode()

    def _save_changes(self) -> None:
        """保存更改"""
        if not self.front_matter:
            return

        try:
            # 获取表单数据
            updates = {}

            title = self.query_one("#fm-title", Input).value.strip()
            if title:
                updates['title'] = title

            description = self.query_one("#fm-description", Input).value.strip()
            if description:
                updates['description'] = description

            tags = self.query_one("#fm-tags", Input).value.strip()
            if tags:
                updates['tags'] = [tag.strip() for tag in tags.split(',') if tag.strip()]

            categories = self.query_one("#fm-categories", Input).value.strip()
            if categories:
                updates['categories'] = [cat.strip() for cat in categories.split(',') if cat.strip()]

            date = self.query_one("#fm-date", Input).value.strip()
            if date:
                updates['date'] = date

            # 更新前置数据
            self.front_matter.update(updates)

            # 更新显示
            self._update_display()
            self.disable_edit_mode()

            # 发送变更消息
            for field, value in updates.items():
                self.post_message(self.DataChanged(field, value))

        except Exception as e:
            log_error(f"保存前置数据失败: {e}")

    def get_updated_data(self) -> Dict[str, Any]:
        """获取更新后的数据"""
        if self.front_matter:
            return self.front_matter.to_dict()
        return {}


class PreviewPane(Static):
    """主预览面板，包含分屏预览和编辑功能"""

    current_file_info: reactive[Dict[str, Any]] = reactive({})
    processed_content: reactive[str] = reactive("")

    BINDINGS = [
        Binding("f3", "toggle_preview_mode", "切换预览模式"),
        Binding("ctrl+e", "edit_metadata", "编辑元数据"),
        Binding("ctrl+r", "refresh_preview", "刷新预览"),
    ]

    def compose(self) -> ComposeResult:
        """构建预览面板界面"""
        with Vertical(id="preview-container"):
            # 预览标签页
            yield Label("📄 文件预览", classes="metric-label")

            with TabbedContent(id="preview-tabs"):
                with TabPane("原始内容", id="original-tab"):
                    yield MarkdownViewer(id="original-viewer", classes="preview-content")

                with TabPane("渲染效果", id="rendered-tab"):
                    yield MarkdownViewer(id="rendered-viewer", classes="preview-content")

                with TabPane("文章元数据", id="metadata-tab"):
                    yield FrontMatterEditor(id="front-matter-editor")

    def update_file_content(self, file_info: Dict[str, Any]) -> None:
        """更新文件内容"""
        self.current_file_info = file_info

        if not file_info or not file_info.get('path'):
            self._clear_content()
            return

        try:
            file_path = Path(file_info['path'])

            if not file_path.exists():
                log_error(f"文件不存在: {file_path}")
                self._clear_content()
                return

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析前置数据和内容
            front_matter_data, markdown_content = extract_yaml_and_content(file_path)

            # 更新原始内容
            original_viewer = self.query_one("#original-viewer", MarkdownViewer)
            original_viewer.update_content(markdown_content)

            # 处理内容（模拟Hugo渲染效果）
            processed_content = self._process_content(markdown_content, front_matter_data)
            self.processed_content = processed_content

            # 更新渲染内容
            rendered_viewer = self.query_one("#rendered-viewer", MarkdownViewer)
            rendered_viewer.update_content(processed_content)

            # 更新前置数据编辑器
            if front_matter_data:
                fm_editor = self.query_one("#front-matter-editor", FrontMatterEditor)
                fm_editor.load_front_matter(front_matter_data)

            # 设置同步滚动
            original_viewer.setup_sync_scroll(rendered_viewer)
            rendered_viewer.setup_sync_scroll(original_viewer)

        except Exception as e:
            log_error(f"更新预览内容失败: {e}")
            self._show_error(f"预览加载失败: {e}")

    def _process_content(self, content: str, front_matter: Optional[FrontMatter] = None) -> str:
        """处理内容，模拟Hugo渲染效果"""
        try:
            # 如果有博客处理器，使用它来处理内容
            if hasattr(self, 'app') and hasattr(self.app, 'get_processor'):
                processor = self.app.get_processor()
                if processor:
                    content = processor.process_obsidian_wiki_links(content)
                    content = processor.process_mermaid_blocks(content)
                    content = processor.process_note_blocks(content)

            # 添加一些基础的格式化指示
            processed_lines = []
            lines = content.split('\n')

            for line in lines:
                # 模拟Hugo短代码处理
                if '{{<' in line and '>}}' in line:
                    processed_lines.append(f"[green]{line}[/green] (Hugo Shortcode)")
                else:
                    processed_lines.append(line)

            return '\n'.join(processed_lines)

        except Exception as e:
            log_error(f"内容处理失败: {e}")
            return content

    def _clear_content(self) -> None:
        """清空内容"""
        original_viewer = self.query_one("#original-viewer", MarkdownViewer)
        rendered_viewer = self.query_one("#rendered-viewer", MarkdownViewer)
        fm_editor = self.query_one("#front-matter-editor", FrontMatterEditor)

        original_viewer.update_content("选择文件查看预览")
        rendered_viewer.update_content("选择文件查看预览")
        fm_editor.load_front_matter(None)

    def _show_error(self, error_message: str) -> None:
        """显示错误信息"""
        original_viewer = self.query_one("#original-viewer", MarkdownViewer)
        rendered_viewer = self.query_one("#rendered-viewer", MarkdownViewer)

        error_content = f"[red]错误:[/red] {error_message}"
        original_viewer.update_content(error_content)
        rendered_viewer.update_content(error_content)

    def action_toggle_preview_mode(self) -> None:
        """切换预览模式"""
        tabs = self.query_one(TabbedContent)
        current_tab = tabs.active
        tab_count = len(tabs.panes)

        # 切换到下一个标签
        next_tab = (current_tab + 1) % tab_count
        tabs.active = next_tab

    def action_edit_metadata(self) -> None:
        """编辑元数据"""
        if self.current_file_info:
            fm_editor = self.query_one("#front-matter-editor", FrontMatterEditor)
            if not fm_editor.edit_mode:
                fm_editor.enable_edit_mode()

                # 切换到元数据标签页
                tabs = self.query_one(TabbedContent)
                tabs.active = 2  # 元数据标签页索引

    def action_refresh_preview(self) -> None:
        """刷新预览"""
        if self.current_file_info:
            self.update_file_content(self.current_file_info)

    def on_front_matter_editor_data_changed(self, message: FrontMatterEditor.DataChanged) -> None:
        """处理前置数据变更"""
        # 刷新预览以反映更改
        self.action_refresh_preview()