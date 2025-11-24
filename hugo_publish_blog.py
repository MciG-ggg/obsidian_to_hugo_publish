# 博客发布脚本
# 用于将Markdown文件发布到Hugo博客并部署到GitHub Pages

import argparse
from pathlib import Path
import subprocess
import sys
import os
from typing import Optional
from src.utils.cli_utils import CLIColors

# 配置常量
DEFAULT_OUTPUT_FORMAT = "default"

# 添加src目录到Python路径
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

from src.core.config_manager import Config
from src.core.blog_processor import BlogProcessor
from src.utils.cli_utils import print_step, print_success, print_error, print_warning, print_info, print_header, print_task_header, print_subtask_status
from src.i18n.i18n import set_locale, t
from src.utils import set_log_file, set_log_level

def select_articles_to_publish(processor):
    """让用户选择要发布的文章"""
    published = processor.list_published_markdowns()
    if not published:
        print_warning(t("no_published_articles"))
        return []
    print_header(t("start_republish_header"))
    for idx, (md_file, yaml_data) in enumerate(published):
        title = yaml_data.title if yaml_data.title else md_file.stem
        description = yaml_data.description if yaml_data.description else t("no_description_fallback")
        print(f"{CLIColors.BOLD}[{idx}]{CLIColors.RESET} {title}")
        print(f"    {CLIColors.DIM}{t('file_label', filename=md_file.name)}{CLIColors.RESET}")  # 需要在翻译文件中添加file_label
        print(f"    {CLIColors.DIM}{t('description_label', description=description)}{CLIColors.RESET}")  # 需要在翻译文件中添加description_label
        if yaml_data.tags:
            print(f"    {CLIColors.DIM}{t('tags_label', tags=', '.join(yaml_data.tags))}{CLIColors.RESET}")  # 需要在翻译文件中添加tags_label
        print()

    while True:
        selection = input(f"{CLIColors.YELLOW}{t('select_article_prompt')}{CLIColors.RESET}").strip()  # 需要在翻译文件中添加select_article_prompt

        if not selection:
            print_warning(t("no_selection_cancel"))
            return []

        if selection.lower() == 'all':
            return [md_file.name for md_file, _ in published]

        try:
            # 解析用户输入的数字
            selected_indices = []
            for part in selection.split(','):
                part = part.strip()
                if part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(published):
                        selected_indices.append(idx)
                    else:
                        print_error(t("invalid_selection", idx=idx))
                        continue
                else:
                    print_error(t("invalid_input", part=part))
                    continue

            if not selected_indices:
                print_error(t("no_valid_indices"))
                continue

            selected_files = [published[idx][0].name for idx in selected_indices]
            print_success(t("selected_count", count=len(selected_files)))  # 需要在翻译文件中添加selected_count
            return selected_files

        except ValueError:
            print_error(t("input_format_error"))

def run_tui():
    """启动TUI界面 - 使用改进的架构"""
    try:
        from src.tui.tui_app import BlogPublishApp
        from src.core.config_manager import Config
        
        # 使用配置文件中的配置
        config = Config()
        
        # 通过新的main方法启动TUI
        exit_code = BlogPublishApp.main(
            config=config,
            validate_config=True,
            skip_checks=False
        )
        
        return exit_code == 0
        
    except ImportError as e:
        print_error(t("tui_dependencies_missing", error=str(e)))
        return False
    except Exception as e:
        print_error(t("tui_start_error", error=str(e)))
        return False

class CLIConfig:
    """CLI配置管理类"""
    
    def __init__(self, config: Config, args: argparse.Namespace):
        self.config = config
        self.args = args
        self.source_dir = Path(args.source).expanduser() if hasattr(args, 'source') else None
        self.hugo_dir = Path(args.hugo_dir).expanduser() if hasattr(args, 'hugo_dir') else None
        self.output_format = getattr(args, 'output_format', 'default')
        
    def validate_paths(self) -> tuple[bool, list[str]]:
        """验证路径配置"""
        errors = []
        
        if not self.source_dir:
            errors.append("未指定源目录")
        elif not self.source_dir.exists():
            errors.append(f"源目录不存在: {self.source_dir}")
            
        if not self.hugo_dir:
            errors.append("未指定Hugo目录")
        elif not self.hugo_dir.exists():
            errors.append(f"Hugo目录不存在: {self.hugo_dir}")
            
        return len(errors) == 0, errors
    
    def create_processor(self) -> Optional[BlogProcessor]:
        """创建博客处理器"""
        if not self.source_dir or not self.hugo_dir:
            return None
        return BlogProcessor(self.source_dir, self.hugo_dir)


class CommandHandler:
    """命令处理器基类"""
    
    def __init__(self, cli_config: CLIConfig):
        self.cli_config = cli_config
        self.config = cli_config.config
        self.args = cli_config.args
        
    def handle(self) -> int:
        """处理命令，返回退出码"""
        raise NotImplementedError
    
    def validate_repos(self) -> tuple[bool, list[str]]:
        """验证仓库配置"""
        errors = []
        repo_source = self.config.get('repositories.source.url')
        repo_pages = self.config.get('repositories.pages.url')
        
        if not repo_source:
            errors.append("缺少源仓库配置")
        if not repo_pages:
            errors.append("缺少Pages仓库配置")
            
        return len(errors) == 0, errors


class PublishHandler(CommandHandler):
    """发布命令处理器"""
    
    def handle(self) -> int:
        """处理发布命令"""
        # 验证路径
        paths_valid, path_errors = self.cli_config.validate_paths()
        if not paths_valid:
            for error in path_errors:
                print_error(error)
            return 1
        
        processor = self.cli_config.create_processor()
        if not processor:
            print_error("无法创建博客处理器")
            return 1
        
        # 获取要发布的文件
        selected_files = self._get_selected_files(processor)
        if selected_files is None:  # 用户取消
            return 0
        
        # 处理文件
        processed_files = self._process_files(processor, selected_files)
        if not processed_files:
            return 1
        
        # 部署
        return self._deploy(processor, processed_files)
    
    def _get_selected_files(self, processor: BlogProcessor) -> Optional[list]:
        """获取要发布的文件列表"""
        selected_files = getattr(self.args, 'files', [])
        
        # 如果使用选择参数，让用户选择文章
        if getattr(self.args, 'select', False):
            try:
                selected_files = select_articles_to_publish(processor)
            except KeyboardInterrupt:
                print_error(t("cancel_by_user"))
                return None
            except Exception as e:
                print_error(t("process_file_error", md_file_name="selecting articles", error=str(e)))
                return None
        
        return selected_files
    
    def _process_files(self, processor: BlogProcessor, selected_files: list) -> list:
        """处理文件"""
        print_task_header(t("start_publish_header"), t("publish_process_description"))
        
        try:
            print_info(t("processing_articles_info", count=len(selected_files) if selected_files else "all"))
            processed_files = processor.process_markdown_files(selected_files, as_draft=getattr(self.args, 'draft', False))
        except Exception as e:
            print_error(t("process_file_error", md_file_name="files", error=str(e)))
            return []
        
        if not processed_files:
            if self.cli_config.output_format == "json":
                from src.utils import print_formatted_output
                result = {"status": "warning", "message": t("no_files_processed")}
                print_formatted_output(result, "json")
            else:
                print_warning(t("no_files_processed"))
            return []
        
        if self.cli_config.output_format == "json":
            from src.utils import print_formatted_output
            result = {
                "status": "success",
                "message": t("process_files_success", count=len(processed_files)),
                "processed_count": len(processed_files),
                "files": processed_files
            }
            print_formatted_output(result, "json")
        else:
            print_success(t("process_files_success", count=len(processed_files)))
            print_subtask_status(
                t("publish_articles_task"),
                "success",
                t("published_count_info", count=len(processed_files))
            )
        
        return processed_files
    
    def _deploy(self, processor: BlogProcessor, processed_files: list) -> int:
        """部署到仓库"""
        # 确认部署
        should_deploy = self._confirm_deployment()
        if not should_deploy:
            return 0
        
        # SSH连接测试
        if not self._test_ssh_connection():
            return 1
        
        # 获取提交信息
        commit_msg = self._get_commit_message()
        if not commit_msg:
            return 1
        
        # 显示部署计划
        if not self._show_deployment_plan(commit_msg):
            return 0
        
        # 执行部署
        return self._execute_deployment(processor, commit_msg)
    
    def _confirm_deployment(self) -> bool:
        """确认是否部署"""
        if getattr(self.args, 'no_interactive', False):
            print_info(t('cli_no_interactive_assuming_yes'))
            return True
        
        try:
            response = input(f"\n{CLIColors.YELLOW}{t('confirm_deployment')}{CLIColors.RESET}").lower().strip()
            return response in ('y', 'yes')
        except KeyboardInterrupt:
            print_error(t("cancel_by_user"))
            return False
    
    def _test_ssh_connection(self) -> bool:
        """测试SSH连接"""
        try:
            result = subprocess.run(['ssh', '-T', 'git@github.com'],
                                 stderr=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 check=False,
                                 timeout=10)
            if result.returncode not in [0, 1]:
                print_warning(t("ssh_test_failed", error="SSH connection to GitHub failed. Please check your SSH keys."))
        except subprocess.TimeoutExpired:
            print_error(t("ssh_test_timeout"))
            return False
        except Exception as e:
            print_error(t("ssh_test_failed", error=str(e)))
            return False
        return True
    
    def _get_commit_message(self) -> Optional[str]:
        """获取提交信息"""
        try:
            commit_msg = input(f"\n{CLIColors.YELLOW}{t('enter_commit_msg')}{CLIColors.RESET}").strip()
            if not commit_msg:
                print_error(t("commit_msg_required"))
                return None
            return commit_msg
        except KeyboardInterrupt:
            print_error(t("cancel_by_user"))
            return None
    
    def _show_deployment_plan(self, commit_msg: str) -> bool:
        """显示部署计划"""
        print(f"\n{CLIColors.YELLOW}{t('deployment_plan')}{CLIColors.RESET}")
        print(t("deploy_step_checkout"))
        print(t("deploy_step_add"))
        print(t('deploy_step_commit', commit_msg=commit_msg))
        print(t("deploy_step_push_source"))
        print(t("deploy_step_build"))
        print(t("deploy_step_push_pages"))
        
        try:
            response = input(f"\n{CLIColors.YELLOW}{t('confirm_action_prompt')}{CLIColors.RESET}").lower().strip()
            return response in ('y', 'yes')
        except KeyboardInterrupt:
            print_error(t("cancel_by_user"))
            return False
    
    def _execute_deployment(self, processor: BlogProcessor, commit_msg: str) -> int:
        """执行部署"""
        # 验证仓库配置
        repos_valid, repo_errors = self.validate_repos()
        if not repos_valid:
            for error in repo_errors:
                print_error(error)
            return 1
        
        try:
            print_info(t("starting_deployment_info"))
            success = processor.deploy_to_repos(
                self.config.get('repositories.source.url'),
                self.config.get('repositories.pages.url'),
                commit_msg
            )
            if success:
                print_subtask_status(
                    t("deployment_task"),
                    "success",
                    t("deployment_completed_info")
                )
            return 0 if success else 1
        except Exception as e:
            print_error(t("deployment_failed", error=str(e)))
            return 1


class PreviewHandler(CommandHandler):
    """预览命令处理器"""
    
    def handle(self) -> int:
        """处理预览命令"""
        paths_valid, path_errors = self.cli_config.validate_paths()
        if not paths_valid:
            for error in path_errors:
                print_error(error)
            return 1
        
        processor = self.cli_config.create_processor()
        if not processor:
            print_error("无法创建博客处理器")
            return 1
        
        print_task_header(t("start_preview_header"), t("preview_process_description"))
        
        try:
            print_info(t("starting_preview_info"))
            processor.preview_site()
            return 0
        except Exception as e:
            print_error(t("preview_error", error=str(e)))
            return 1


class TUIHandler(CommandHandler):
    """TUI命令处理器"""
    
    def handle(self) -> int:
        """处理TUI命令"""
        print_info(t("starting_tui"))
        success = run_tui()
        return 0 if success else 1


class UnpublishHandler(CommandHandler):
    """取消发布命令处理器"""
    
    def handle(self) -> int:
        """处理取消发布命令"""
        paths_valid, path_errors = self.cli_config.validate_paths()
        if not paths_valid:
            for error in path_errors:
                print_error(error)
            return 1
        
        processor = self.cli_config.create_processor()
        if not processor:
            print_error("无法创建博客处理器")
            return 1
        
        # 获取已发布文章
        try:
            published = processor.list_published_markdowns()
        except Exception as e:
            print_error(t("list_published_error", error=str(e)))
            return 1
        
        if not published:
            print_warning(t("no_articles_to_unpublish"))
            return 0
        
        # 选择要取消发布的文章
        selected_indices = self._select_articles(published)
        if not selected_indices:
            return 0
        
        # 执行取消发布
        self._unpublish_articles(processor, published, selected_indices)
        
        # 部署更改
        return self._deploy_changes(processor)
    
    def _select_articles(self, published: list) -> list:
        """选择要取消发布的文章"""
        print_task_header(t("start_unpublish_header"), t("unpublish_process_description"))
        
        print_subtask_status(t("list_published_articles_task"), "info", t("found_count_info", count=len(published)))
        for idx, (md_file, yaml_data) in enumerate(published):
            print(f"[{idx}] {md_file}")
        
        try:
            idxs_input = input(t("unpublish_selection_prompt")).strip()
            if not idxs_input:
                print_warning(t("no_selection_cancel"))
                return []
            
            idxs = [int(i) for i in idxs_input.split(',') if i.strip().isdigit() and int(i) < len(published)]
            if not idxs:
                print_error(t("no_valid_indices"))
                return []
            
            return idxs
        except (ValueError, KeyboardInterrupt):
            print_error(t("cancel_by_user"))
            return []
    
    def _unpublish_articles(self, processor: BlogProcessor, published: list, selected_indices: list):
        """执行取消发布操作"""
        for i in selected_indices:
            md_file, yaml_data = published[i]
            try:
                processor.set_publish_false(md_file)
                article_name = Path(md_file).stem
                success = processor.unpublish_article(article_name)
                if success:
                    print_subtask_status(
                        t("unpublish_article_task", article=article_name),
                        "success",
                        t("completed_status")
                    )
            except Exception as e:
                print_subtask_status(
                    t("unpublish_article_task", article=Path(md_file).stem),
                    "error",
                    str(e)
                )
    
    def _deploy_changes(self, processor: BlogProcessor) -> int:
        """部署更改"""
        print(f"{CLIColors.YELLOW}{t('push_to_remote')}{CLIColors.RESET}")
        
        try:
            commit_msg = input(f"{t('unpublish_commit_prompt')}").strip() or t("default_unpublish_msg")
        except KeyboardInterrupt:
            print_error(t("cancel_by_user"))
            return 1
        
        repos_valid, repo_errors = self.validate_repos()
        if not repos_valid:
            for error in repo_errors:
                print_error(error)
            return 1
        
        try:
            print_info(t("starting_deployment_info"))
            success = processor.deploy_to_repos(
                self.config.get('repositories.source.url'),
                self.config.get('repositories.pages.url'),
                commit_msg
            )
            if success:
                print_subtask_status(
                    t("deployment_task"),
                    "success",
                    t("deployment_completed_info")
                )
            return 0 if success else 1
        except Exception as e:
            print_error(t("deployment_failed", error=str(e)))
            return 1


class RepublishHandler(CommandHandler):
    """重新发布命令处理器"""
    
    def handle(self) -> int:
        """处理重新发布命令"""
        paths_valid, path_errors = self.cli_config.validate_paths()
        if not paths_valid:
            for error in path_errors:
                print_error(error)
            return 1
        
        processor = self.cli_config.create_processor()
        if not processor:
            print_error("无法创建博客处理器")
            return 1
        
        # 获取已发布文章
        try:
            published = processor.list_published_markdowns()
        except Exception as e:
            print_error(t("list_published_error", error=str(e)))
            return 1
        
        if not published:
            print_warning(t("no_published_articles"))
            return 0
        
        # 取消发布所有文章
        print_step(1, t("unpublish_all_step"))
        self._unpublish_all(processor, published)
        
        # 重新发布
        print_step(2, t("republish_all_step"))
        processed_files = self._republish_all(processor)
        if not processed_files:
            return 1
        
        # 部署
        print_step(3, t("deploy_step"))
        return self._deploy_changes(processor)
    
    def _unpublish_all(self, processor: BlogProcessor, published: list):
        """取消发布所有文章"""
        total_tasks = len(published) + 1 + 1
        from src.utils.cli_utils import ProgressTracker
        progress_tracker = ProgressTracker(total_tasks, t("republish_progress_description"))
        
        for idx, (md_file, _) in enumerate(published):
            article_name = Path(md_file).stem
            try:
                if processor.unpublish_article(article_name):
                    print_subtask_status(
                        t("unpublish_article_task", article=article_name),
                        "success",
                        t("completed_status")
                    )
                else:
                    print_subtask_status(
                        t("unpublish_article_task", article=article_name),
                        "warning",
                        t("not_found_status")
                    )
            except Exception as e:
                print_subtask_status(
                    t("unpublish_article_task", article=article_name),
                    "error",
                    str(e)
                )
                continue
            progress_tracker.start_task(t("unpublish_article_task", article=article_name))
    
    def _republish_all(self, processor: BlogProcessor) -> list:
        """重新发布所有文章"""
        try:
            print_info(t("processing_articles_info", count=len(published)))
            
            def progress_callback(current, total):
                # TODO: 实现进度回调
                pass
            
            processed_files = processor.process_markdown_files(
                as_draft=getattr(self.args, 'draft', False),
                progress_callback=progress_callback
            )
            
            if self.cli_config.output_format == "json":
                from src.utils import print_formatted_output
                result = {
                    "status": "success",
                    "message": t("process_files_success", count=len(processed_files)),
                    "processed_count": len(processed_files),
                    "files": processed_files
                }
                print_formatted_output(result, "json")
            else:
                print_success(t("process_files_success", count=len(processed_files)))
                print_subtask_status(
                    t("publish_articles_task"),
                    "success",
                    t("published_count_info", count=len(processed_files))
                )
            
            return processed_files
        except Exception as e:
            print_error(t("process_file_error", md_file_name="files", error=str(e)))
            return []
    
    def _deploy_changes(self, processor: BlogProcessor) -> int:
        """部署更改"""
        commit_msg = t("start_republish_header")
        
        repos_valid, repo_errors = self.validate_repos()
        if not repos_valid:
            for error in repo_errors:
                print_error(error)
            return 1
        
        try:
            print_info(t("starting_deployment_info"))
            success = processor.deploy_to_repos(
                self.config.get('repositories.source.url'),
                self.config.get('repositories.pages.url'),
                commit_msg
            )
            if success:
                print_success(t("republish_success"))
            return 0 if success else 1
        except Exception as e:
            print_error(t("deployment_failed", error=str(e)))
            return 1


def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    config = Config()
    
    # 获取默认路径
    source_default = config.get('paths.obsidian.vault', '')
    hugo_default = config.get('paths.hugo.blog', '')
    
    # 创建主解析器
    parser = argparse.ArgumentParser(
        prog='hugo-publish',
        description=t('cli_description'),
        epilog=t('cli_epilog'),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 全局参数
    parser.add_argument('--lang',
                       default=os.getenv('LANG', 'zh-CN').split('.')[0].replace('_', '-'),
                       choices=['zh-CN', 'en'],
                       help=t('cli_lang_help'))
    parser.add_argument('--log-file',
                       help=t('cli_log_file_help'))
    parser.add_argument('--log-level',
                       default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help=t('cli_log_level_help'))
    parser.add_argument('--version', '-v', action='version', version=f'%(prog)s {t("version")}')
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest='command', help=t('subcommands_help'))
    
    # 发布命令
    publish_parser = subparsers.add_parser('publish', help=t('publish_command_help'))
    publish_parser.add_argument('--source', default=source_default, help=t('cli_source_help'))
    publish_parser.add_argument('--hugo-dir', default=hugo_default, help=t('cli_hugo_dir_help'))
    publish_parser.add_argument('--files', nargs='*', help=t('cli_files_help'))
    publish_parser.add_argument('--draft', action='store_true', help=t('cli_draft_help'))
    publish_parser.add_argument('--select', action='store_true', help=t('cli_select_help'))
    publish_parser.add_argument('--output-format', default='default', choices=['default', 'json', 'table'], help=t('cli_output_format_help'))
    publish_parser.add_argument('--no-interactive', action='store_true', help=t('cli_no_interactive_help'))
    
    # 取消发布命令
    unpublish_parser = subparsers.add_parser('unpublish', help=t('unpublish_command_help'))
    unpublish_parser.add_argument('--source', default=source_default, help=t('cli_source_help'))
    unpublish_parser.add_argument('--hugo-dir', default=hugo_default, help=t('cli_hugo_dir_help'))
    unpublish_parser.add_argument('--output-format', default='default', choices=['default', 'json', 'table'], help=t('cli_output_format_help'))
    
    # 预览命令
    preview_parser = subparsers.add_parser('preview', help=t('preview_command_help'))
    preview_parser.add_argument('--source', default=source_default, help=t('cli_source_help'))
    preview_parser.add_argument('--hugo-dir', default=hugo_default, help=t('cli_hugo_dir_help'))
    preview_parser.add_argument('--output-format', default='default', choices=['default', 'json', 'table'], help=t('cli_output_format_help'))
    preview_parser.add_argument('--no-interactive', action='store_true', help=t('cli_no_interactive_help'))
    
    # 重新发布命令
    republish_parser = subparsers.add_parser('republish', help=t('republish_command_help'))
    republish_parser.add_argument('--source', default=source_default, help=t('cli_source_help'))
    republish_parser.add_argument('--hugo-dir', default=hugo_default, help=t('cli_hugo_dir_help'))
    republish_parser.add_argument('--draft', action='store_true', help=t('cli_draft_help'))
    republish_parser.add_argument('--output-format', default='default', choices=['default', 'json', 'table'], help=t('cli_output_format_help'))
    republish_parser.add_argument('--no-interactive', action='store_true', help=t('cli_no_interactive_help'))
    
    # TUI命令
    tui_parser = subparsers.add_parser('tui', help=t('tui_command_help'))
    tui_parser.add_argument('--source', default=source_default, help=t('cli_source_help'))
    tui_parser.add_argument('--hugo-dir', default=hugo_default, help=t('cli_hugo_dir_help'))
    tui_parser.add_argument('--output-format', default='default', choices=['default', 'json', 'table'], help=t('cli_output_format_help'))
    tui_parser.add_argument('--no-interactive', action='store_true', help=t('cli_no_interactive_help'))
    
    return parser


def setup_logging(args: argparse.Namespace, config: Config):
    """设置日志配置"""
    # 优先使用命令行参数，否则使用配置文件设置
    if args.log_file:
        set_log_file(args.log_file)
    else:
        log_file = config.get('logging.file')
        if log_file:
            set_log_file(log_file)
    
    if args.log_level != 'INFO':
        set_log_level(args.log_level)
    else:
        log_level = config.get('logging.level', 'INFO')
        set_log_level(log_level)


def validate_command_args(args: argparse.Namespace) -> bool:
    """验证命令行参数"""
    if args.no_interactive and not (hasattr(args, 'files') and args.files or args.command in ['preview', 'republish']):
        print_error(t("cli_no_interactive_requires_option"))
        return False
    return True


def create_command_handler(args: argparse.Namespace, config: Config) -> Optional[CommandHandler]:
    """创建命令处理器"""
    cli_config = CLIConfig(config, args)
    
    handlers = {
        'publish': PublishHandler,
        'preview': PreviewHandler,
        'tui': TUIHandler,
        'unpublish': UnpublishHandler,
        'republish': RepublishHandler,
    }
    
    handler_class = handlers.get(args.command)
    if not handler_class:
        return None
    
    return handler_class(cli_config)


def execute_command(handler: CommandHandler) -> int:
    """执行命令并返回退出码"""
    try:
        return handler.handle()
    except KeyboardInterrupt:
        print_error(t("cancel_by_user"))
        return 1
    except Exception as e:
        from src.utils.cli_utils import handle_exception
        handle_exception(e, handler.__class__.__name__)
        return 1

def main() -> int:
    """主入口函数 - 使用重构后的模块化架构
    
    Returns:
        int: 程序退出码 (0=成功, 1=失败)
    """
    try:
        # 加载配置
        config = Config()
        
        # 验证基本配置
        try:
            source_default = config.get('paths.obsidian.vault')
            if not source_default:
                print_error(t("config_missing_source_path"))
                return 1
            hugo_default = config.get('paths.hugo.blog')
            if not hugo_default:
                print_error(t("config_missing_hugo_path"))
                return 1
        except Exception as e:
            print_error(t("config_load_error", error=str(e)))
            return 1
        
        # 创建参数解析器并解析参数
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # 检查是否提供了命令
        if not args.command:
            parser.print_help()
            return 0
        
        # 设置语言环境
        set_locale(args.lang)
        
        # 设置日志
        setup_logging(args, config)
        
        # 验证命令参数
        if not validate_command_args(args):
            return 1
        
        # 创建命令处理器
        handler = create_command_handler(args, config)
        if not handler:
            print_error(f"未知命令: {args.command}")
            parser.print_help()
            return 1
        
        # 执行命令
        return execute_command(handler)
        
    except KeyboardInterrupt:
        print_error(t("cancel_by_user"))
        return 1
    except Exception as e:
        from src.utils.cli_utils import handle_exception
        handle_exception(e, "main")
        return 1

def cli_main(args=None) -> int:
    """CLI程序的入口点，支持参数注入以便测试

    Args:
        args: 可选的命令行参数列表，如果为None则使用sys.argv

    Returns:
        int: 程序退出码
    """
    if args is not None:
        # 临时替换sys.argv以便测试
        original_argv = sys.argv
        sys.argv = ['hugo-publish'] + args
        try:
            exit_code = main()
        finally:
            sys.argv = original_argv
        return exit_code
    else:
        return main()


def run_with_config(config_file: Optional[str] = None, command: str = 'publish', **kwargs) -> int:
    """使用自定义配置运行程序

    Args:
        config_file: 配置文件路径
        command: 要执行的命令
        **kwargs: 其他参数

    Returns:
        int: 程序退出码
    """
    # TODO: 实现自定义配置文件支持
    args = [command]

    # 添加其他参数
    for key, value in kwargs.items():
        if value is not None:
            args.extend([f'--{key.replace("_", "-")}', str(value)])

    return cli_main(args)


# 提供便捷的函数接口
def publish_blog(source_dir: Optional[str] = None, hugo_dir: Optional[str] = None,
                 files: Optional[list] = None, draft: bool = False,
                 select_mode: bool = False, **kwargs) -> int:
    """发布博客的便捷函数

    Args:
        source_dir: 源目录路径
        hugo_dir: Hugo目录路径
        files: 要发布的文件列表
        draft: 是否以草稿模式发布
        select_mode: 是否启用选择模式
        **kwargs: 其他参数

    Returns:
        int: 程序退出码
    """
    args = ['publish']

    if source_dir:
        args.extend(['--source', source_dir])
    if hugo_dir:
        args.extend(['--hugo-dir', hugo_dir])
    if files:
        args.extend(['--files'] + files)
    if draft:
        args.append('--draft')
    if select_mode:
        args.append('--select')

    # 添加其他参数
    for key, value in kwargs.items():
        if value is not None and key not in ['source', 'hugo_dir', 'files', 'draft', 'select']:
            args.extend([f'--{key.replace("_", "-")}', str(value)])

    return cli_main(args)


def preview_blog(source_dir: Optional[str] = None, hugo_dir: Optional[str] = None, **kwargs) -> int:
    """预览博客的便捷函数

    Args:
        source_dir: 源目录路径
        hugo_dir: Hugo目录路径
        **kwargs: 其他参数

    Returns:
        int: 程序退出码
    """
    return run_with_config(command='preview', source=source_dir, hugo_dir=hugo_dir, **kwargs)


def unpublish_blog(source_dir: Optional[str] = None, hugo_dir: Optional[str] = None, **kwargs) -> int:
    """取消发布博客的便捷函数

    Args:
        source_dir: 源目录路径
        hugo_dir: Hugo目录路径
        **kwargs: 其他参数

    Returns:
        int: 程序退出码
    """
    return run_with_config(command='unpublish', source=source_dir, hugo_dir=hugo_dir, **kwargs)


def start_tui(**kwargs) -> int:
    """启动TUI界面的便捷函数

    Args:
        **kwargs: 其他参数

    Returns:
        int: 程序退出码
    """
    return run_with_config(command='tui', **kwargs)


if __name__ == '__main__':
    main()