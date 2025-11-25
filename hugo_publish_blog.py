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
from src.core.front_matter import extract_yaml_and_content
from src.utils.cli_utils import print_step, print_success, print_error, print_warning, print_info, print_header, print_task_header, print_subtask_status
from src.i18n.i18n import set_locale, t
from src.utils import set_log_file, set_log_level
from src.utils.logger import warning

def format_article_time_display(processor, md_file):
    """
    格式化文章时间显示
    :param processor: BlogProcessor实例
    :param md_file: markdown文件路径
    :return: 格式化的时间字符串
    """
    try:
        mtime = processor.get_file_mtime(md_file)
        formatted_time = processor.format_mtime(mtime)
        return t("modified_time_label", mtime=formatted_time)
    except Exception as e:
        # 时间获取失败时显示提示
        warning(f"无法获取文件 {md_file} 的时间信息: {e}")
        return t("modified_time_unavailable")

def select_articles_to_publish(processor, config=None):
    """让用户选择要发布的文章"""
    # 如果没有传入配置，创建默认配置
    if config is None:
        config = Config()

    # 读取排序配置，默认启用排序
    sort_enabled = config.get('display.sort_by_mtime', True)

    # 根据配置决定是否使用排序
    if sort_enabled:
        published = processor.list_published_markdowns(sort_by='mtime')
    else:
        published = processor.list_published_markdowns()

    if not published:
        print_warning(t("no_published_articles"))
        return []

    print_header(t("start_republish_header"))

    for idx, (md_file, yaml_data) in enumerate(published):
        title = yaml_data.title if yaml_data.title else md_file.stem
        description = yaml_data.description if yaml_data.description else t("no_description_fallback")

        # 显示文章基本信息
        print(f"{CLIColors.BOLD}[{idx}]{CLIColors.RESET} {title}")
        print(f"    {CLIColors.DIM}{t('file_label', filename=md_file.name)}{CLIColors.RESET}")
        print(f"    {CLIColors.DIM}{t('description_label', description=description)}{CLIColors.RESET}")

        # 显示标签信息
        if yaml_data.tags:
            print(f"    {CLIColors.DIM}{t('tags_label', tags=', '.join(yaml_data.tags))}{CLIColors.RESET}")

        # 显示修改时间信息
        time_display = format_article_time_display(processor, md_file)
        print(f"    {CLIColors.DIM}{time_display}{CLIColors.RESET}")

        print()

    while True:
        selection = input(f"{CLIColors.YELLOW}{t('select_article_prompt')}{CLIColors.RESET}").strip()

        if not selection:
            print_warning(t("no_selection_cancel"))
            return []

        if selection.lower() == 'all':
            return [str(md_file) for md_file, _ in published]

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

            selected_files = [str(published[idx][0]) for idx in selected_indices]
            print_success(t("selected_count", count=len(selected_files)))
            return selected_files

        except ValueError:
            print_error(t("input_format_error"))

def select_articles_to_unpublish(processor, config=None):
    """让用户选择要取消发布的文章"""
    # 如果没有传入配置，创建默认配置
    if config is None:
        config = Config()

    # 读取排序配置，默认启用排序
    sort_enabled = config.get('display.sort_by_mtime', True)

    # 根据配置决定是否使用排序
    if sort_enabled:
        published = processor.list_published_markdowns(sort_by='mtime')
    else:
        published = processor.list_published_markdowns()

    if not published:
        print_warning(t("no_published_articles"))
        return []

    print_header(t("select_articles_to_unpublish_header"))

    for idx, (md_file, yaml_data) in enumerate(published):
        title = yaml_data.title if yaml_data.title else md_file.stem
        description = yaml_data.description if yaml_data.description else t("no_description_fallback")

        # 显示文章基本信息
        print(f"{CLIColors.BOLD}[{idx}]{CLIColors.RESET} {title}")
        print(f"    {CLIColors.DIM}{t('file_label', filename=md_file.name)}{CLIColors.RESET}")
        print(f"    {CLIColors.DIM}{t('description_label', description=description)}{CLIColors.RESET}")

        # 显示标签信息
        if yaml_data.tags:
            print(f"    {CLIColors.DIM}{t('tags_label', tags=', '.join(yaml_data.tags))}{CLIColors.RESET}")

        # 显示修改时间信息
        time_display = format_article_time_display(processor, md_file)
        print(f"    {CLIColors.DIM}{time_display}{CLIColors.RESET}")

        print()

    while True:
        selection = input(f"{CLIColors.YELLOW}{t('select_unpublish_article_prompt')}{CLIColors.RESET}").strip()

        if not selection:
            print_warning(t("no_selection_cancel"))
            return []

        if selection.lower() == 'all':
            return [str(md_file) for md_file, _ in published]

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

            selected_files = [str(published[idx][0]) for idx in selected_indices]
            print_success(t("selected_count", count=len(selected_files)))
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

        # 创建TUI应用实例
        app = BlogPublishApp(config)

        # 运行应用
        app.run()

    except ImportError as e:
        print_error(f"TUI dependencies missing: {e}")
        print_info("Please install required dependencies: pip install textual textual-dev")
        sys.exit(1)
    except Exception as e:
        print_error(f"TUI startup failed: {e}")
        sys.exit(1)

def publish_command(args, config):
    """处理发布命令"""
    try:
        from src.core.blog_processor import BlogProcessor

        source_dir = config.get('paths.obsidian.vault')
        hugo_dir = config.get('paths.hugo.blog')

        if not source_dir or not hugo_dir:
            print_error("Configuration error: source_dir or hugo_dir not set in config file")
            return False

        processor = BlogProcessor(source_dir, hugo_dir, config_path=config.config_file)

        if args.select:
            selected_files = select_articles_to_publish(processor, config)
            if not selected_files:
                print_info("No files selected for publishing")
                return True
            processor.process_markdown_files(selected_files, as_draft=args.draft)
        elif args.files:
            processor.process_markdown_files(args.files, as_draft=args.draft)
        else:
            # 处理所有markdown文件
            processor.process_markdown_files(as_draft=args.draft)

        # 询问是否部署
        if args.no_interactive:
            deploy = True
        else:
            deploy_choice = input(f"{CLIColors.YELLOW}{t('confirm_deployment')}{CLIColors.RESET}").strip().lower()
            deploy = deploy_choice in ['y', 'yes']

        if deploy:
            success = processor.deploy()
            if success:
                print_success(t("deployment_complete"))
                return True
            else:
                print_error(t("deployment_failed", error="Deployment process failed"))
                return False

        return True

    except Exception as e:
        print_error(t("processing_markdown_error", error=str(e)))
        return False

def unpublish_command(args, config):
    """处理取消发布命令"""
    try:
        from src.core.blog_processor import BlogProcessor

        source_dir = config.get('paths.obsidian.vault')
        hugo_dir = config.get('paths.hugo.blog')

        if not source_dir or not hugo_dir:
            print_error("Configuration error: source_dir or hugo_dir not set in config file")
            return False

        processor = BlogProcessor(source_dir, hugo_dir, config_path=config.config_file)

        if args.select:
            selected_files = select_articles_to_unpublish(processor, config)
            if not selected_files:
                print_info("No files selected for unpublishing")
                return True
            # 取消发布选中的文件
            for file_path in selected_files:
                processor.unpublish_article(file_path)
        else:
            # 取消发布所有文章
            processor.unpublish_all_articles()

        # 询问是否部署
        if args.no_interactive:
            deploy = True
        else:
            deploy_choice = input(f"{CLIColors.YELLOW}{t('confirm_deployment')}{CLIColors.RESET}").strip().lower()
            deploy = deploy_choice in ['y', 'yes']

        if deploy:
            success = processor.deploy()
            if success:
                print_success(t("deployment_complete"))
                return True
            else:
                print_error(t("deployment_failed", error="Deployment process failed"))
                return False

        return True

    except Exception as e:
        print_error(t("processing_markdown_error", error=str(e)))
        return False

def preview_command(args, config):
    """处理预览命令"""
    try:
        from src.core.blog_processor import BlogProcessor

        hugo_dir = config.get('paths.hugo.blog')

        if not hugo_dir:
            print_error("Configuration error: hugo_dir not set in config file")
            return False

        processor = BlogProcessor("", hugo_dir)
        processor.start_preview_server()
        return True

    except Exception as e:
        print_error(t("preview_failed", error=str(e)))
        return False

def republish_command(args, config):
    """处理重新发布命令"""
    try:
        from src.core.blog_processor import BlogProcessor

        source_dir = config.get('paths.obsidian.vault')
        hugo_dir = config.get('paths.hugo.blog')

        if not source_dir or not hugo_dir:
            print_error("Configuration error: source_dir or hugo_dir not set in config file")
            return False

        processor = BlogProcessor(source_dir, hugo_dir, config_path=config.config_file)

        # 先取消发布所有文章
        processor.unpublish_all_articles()

        # 然后重新发布所有文章
        processor.process_markdown_files(as_draft=args.draft)

        # 询问是否部署
        if args.no_interactive:
            deploy = True
        else:
            deploy_choice = input(f"{CLIColors.YELLOW}{t('confirm_deployment')}{CLIColors.RESET}").strip().lower()
            deploy = deploy_choice in ['y', 'yes']

        if deploy:
            success = processor.deploy()
            if success:
                print_success(t("deployment_complete"))
                return True
            else:
                print_error(t("deployment_failed", error="Deployment process failed"))
                return False

        return True

    except Exception as e:
        print_error(t("processing_markdown_error", error=str(e)))
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description=t("cli_description"),
        epilog=t("cli_epilog"),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--source', help=t("cli_source_help"))
    parser.add_argument('--hugo-dir', help=t("cli_hugo_dir_help"))
    parser.add_argument('--files', nargs='+', help=t("cli_files_help"))
    parser.add_argument('--lang', default=os.getenv('LANG', 'zh-CN').split('.')[0], help=t("cli_lang_help"))
    parser.add_argument('--log-file', help=t("cli_log_file_help"))
    parser.add_argument('--log-level', help=t("cli_log_level_help"))

    subparsers = parser.add_subparsers(dest='command', help=t("subcommands_help"))

    # 发布命令
    publish_parser = subparsers.add_parser('publish', help=t("publish_command_help"))
    publish_parser.add_argument('--select', action='store_true', help=t("cli_select_help"))
    publish_parser.add_argument('--draft', action='store_true', help=t("cli_draft_help"))
    publish_parser.add_argument('--no-interactive', action='store_true', help=t("cli_no_interactive_help"))
    publish_parser.add_argument('--files', nargs='+', help=t("cli_files_help"))

    # 取消发布命令
    unpublish_parser = subparsers.add_parser('unpublish', help=t("unpublish_command_help"))
    unpublish_parser.add_argument('--select', action='store_true', help=t("cli_select_help"))
    unpublish_parser.add_argument('--no-interactive', action='store_true', help=t("cli_no_interactive_help"))
    unpublish_parser.add_argument('--files', nargs='+', help=t("cli_files_help"))

    # 预览命令
    preview_parser = subparsers.add_parser('preview', help=t("preview_command_help"))

    # 重新发布命令
    republish_parser = subparsers.add_parser('republish', help=t("republish_command_help"))
    republish_parser.add_argument('--draft', action='store_true', help=t("cli_draft_help"))
    republish_parser.add_argument('--no-interactive', action='store_true', help=t("cli_no_interactive_help"))

    # TUI命令
    tui_parser = subparsers.add_parser('tui', help=t("tui_command_help"))

    args = parser.parse_args()

    # 设置国际化
    set_locale(args.lang)

    # 设置日志
    if args.log_file:
        set_log_file(args.log_file)
    if args.log_level:
        set_log_level(args.log_level)

    try:
        # 加载配置
        config = Config()

        # 如果没有提供命令，显示帮助
        if not args.command:
            parser.print_help()
            return

        # 根据命令执行相应操作
        success = False
        if args.command == 'publish':
            success = publish_command(args, config)
        elif args.command == 'unpublish':
            success = unpublish_command(args, config)
        elif args.command == 'preview':
            success = preview_command(args, config)
        elif args.command == 'republish':
            success = republish_command(args, config)
        elif args.command == 'tui':
            run_tui()

        if not success:
            sys.exit(1)

    except Exception as e:
        print_error(t("unexpected_error", error=str(e)))
        sys.exit(1)

if __name__ == "__main__":
    main()