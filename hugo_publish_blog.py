# 博客发布脚本
# 用于将Markdown文件发布到Hugo博客并部署到GitHub Pages

import argparse
from pathlib import Path
import subprocess
import sys
import os
from src.utils.cli_utils import CLIColors

# 全局变量
output_format = "default"
cli_args = None

# 添加src目录到Python路径
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

from src.core.config_manager import Config
from src.core.blog_processor import BlogProcessor
from src.utils.cli_utils import print_step, print_success, print_error, print_warning, print_info, print_header
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

def main():
    global output_format, cli_args
    
    try:
        config = Config()

        # Validate required config values exist
        try:
            source_default = config.get('paths.obsidian.vault')
            if not source_default:
                print_error(t("config_missing_source_path"))
                return
            hugo_default = config.get('paths.hugo.blog')
            if not hugo_default:
                print_error(t("config_missing_hugo_path"))
                return
        except Exception as e:
            print_error(t("config_load_error", error=str(e)))
            return

        # Create the main parser with subcommands
        parser = argparse.ArgumentParser(
            prog='hugo-publish',
            description=t('cli_description'),
            epilog=t('cli_epilog'),
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
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
        
        # Add subparsers for different commands
        subparsers = parser.add_subparsers(dest='command', help=t('subcommands_help'))
        
        # Publish command
        publish_parser = subparsers.add_parser('publish', help=t('publish_command_help'))
        publish_parser.add_argument('--source',
                                   default=source_default,
                                   help=t('cli_source_help'))
        publish_parser.add_argument('--hugo-dir',
                                   default=hugo_default,
                                   help=t('cli_hugo_dir_help'))
        publish_parser.add_argument('--files',
                                   nargs='*',
                                   help=t('cli_files_help'))
        publish_parser.add_argument('--draft', action='store_true', help=t('cli_draft_help'))
        publish_parser.add_argument('--select', action='store_true', help=t('cli_select_help'))
        publish_parser.add_argument('--output-format',
                                   default='default',
                                   choices=['default', 'json', 'table'],
                                   help=t('cli_output_format_help'))
        publish_parser.add_argument('--no-interactive',
                                   action='store_true',
                                   help=t('cli_no_interactive_help'))
        
        # Unpublish command
        unpublish_parser = subparsers.add_parser('unpublish', help=t('unpublish_command_help'))
        unpublish_parser.add_argument('--source',
                                     default=source_default,
                                     help=t('cli_source_help'))
        unpublish_parser.add_argument('--hugo-dir',
                                     default=hugo_default,
                                     help=t('cli_hugo_dir_help'))
        unpublish_parser.add_argument('--output-format',
                                     default='default',
                                     choices=['default', 'json', 'table'],
                                     help=t('cli_output_format_help'))
        
        # Preview command
        preview_parser = subparsers.add_parser('preview', help=t('preview_command_help'))
        preview_parser.add_argument('--source',
                                   default=source_default,
                                   help=t('cli_source_help'))
        preview_parser.add_argument('--hugo-dir',
                                   default=hugo_default,
                                   help=t('cli_hugo_dir_help'))
        preview_parser.add_argument('--output-format',
                                   default='default',
                                   choices=['default', 'json', 'table'],
                                   help=t('cli_output_format_help'))
        preview_parser.add_argument('--no-interactive',
                                   action='store_true',
                                   help=t('cli_no_interactive_help'))
        
        # Republish command
        republish_parser = subparsers.add_parser('republish', help=t('republish_command_help'))
        republish_parser.add_argument('--source',
                                     default=source_default,
                                     help=t('cli_source_help'))
        republish_parser.add_argument('--hugo-dir',
                                     default=hugo_default,
                                     help=t('cli_hugo_dir_help'))
        republish_parser.add_argument('--draft', action='store_true', help=t('cli_draft_help'))
        republish_parser.add_argument('--output-format',
                                     default='default',
                                     choices=['default', 'json', 'table'],
                                     help=t('cli_output_format_help'))
        republish_parser.add_argument('--no-interactive',
                                     action='store_true',
                                     help=t('cli_no_interactive_help'))

        args = parser.parse_args()
        
        # 设置语言环境
        set_locale(args.lang)
        
        # 检查是否有版本参数，如果有则已经由argparse处理并退出
        # 根据新的命令行参数设置输出格式等
        if args.output_format == 'json':
            # 如果用户选择json格式，我们可以设置一个全局变量或在相关函数中处理
            pass  # 目前暂时留空，可以后续实现具体处理逻辑
        
        # 检查是否使用非交互模式
        if args.no_interactive and not (args.files or args.preview or args.republish):
            print_error(t("cli_no_interactive_requires_option"))
            return

        # 根据输出格式设置全局变量或选项
        output_format = args.output_format
        
        # 保存 args 以便其他函数使用
        cli_args = args
        
        # 设置日志
        # 优先使用命令行参数，如果未指定则使用配置文件中的设置
        if args.log_file:
            set_log_file(args.log_file)
        else:
            log_file = config.get('logging.file')
            if log_file:
                set_log_file(log_file)
                
        if args.log_level != 'INFO':  # 检查是否是默认值
            set_log_level(args.log_level)
        else:
            log_level = config.get('logging.level', 'INFO')
            set_log_level(log_level)

        # Check if command was provided
        if not args.command:
            parser.print_help()
            return

        # 根据命令执行相应操作
        if args.command == 'preview':
            source_dir = Path(args.source).expanduser()
            hugo_dir = Path(args.hugo_dir).expanduser()

            if not source_dir.exists():
                print_error(t("source_dir_not_exist", source_dir=source_dir))
                return

            if not hugo_dir.exists():
                print_error(t("hugo_dir_not_exist", hugo_dir=hugo_dir))
                return

            # 创建博客处理器实例
            processor = BlogProcessor(source_dir, hugo_dir)
            
            try:
                processor.preview_site()
            except Exception as e:
                print_error(t("preview_error", error=str(e)))
                return
        elif args.command == 'republish':
            source_dir = Path(args.source).expanduser()
            hugo_dir = Path(args.hugo_dir).expanduser()

            if not source_dir.exists():
                print_error(t("source_dir_not_exist", source_dir=source_dir))
                return

            if not hugo_dir.exists():
                print_error(t("hugo_dir_not_exist", hugo_dir=hugo_dir))
                return

            # 创建博客处理器实例
            processor = BlogProcessor(source_dir, hugo_dir)
            
            # 根据输出格式设置全局变量或选项
            output_format = args.output_format
            
            # 重新发布流程
            print_header(t("start_republish_header"))
            try:
                published = processor.list_published_markdowns()
            except Exception as e:
                print_error(t("list_published_error", error=str(e)))
                return
                
            if not published:
                print_warning(t("no_published_articles"))
                return

            print_step(1, t("unpublish_all_step"))
            for md_file, _ in published:
                article_name = Path(md_file).stem
                try:
                    if processor.unpublish_article(article_name):
                        print_success(t("unpublished_success", article_name=article_name))
                except Exception as e:
                    print_error(t("process_file_error", md_file_name=article_name, error=str(e)))
                    continue

            print_step(2, t("republish_all_step"))
            try:
                processed_files = processor.process_markdown_files(as_draft=args.draft)
            except Exception as e:
                print_error(t("process_file_error", md_file_name="files", error=str(e)))
                return

            if not processed_files:
                if output_format == "json":
                    from src.utils import print_formatted_output
                    result = {
                        "status": "warning",
                        "message": t("no_files_processed")
                    }
                    print_formatted_output(result, "json")
                else:
                    print_warning(t("no_files_processed"))
                return

            if output_format == "json":
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

            print_step(3, t("deploy_step"))
            commit_msg = t("start_republish_header")
            
            # Validate repository URLs
            repo_source = config.get('repositories.source.url')
            repo_pages = config.get('repositories.pages.url')
            if not repo_source or not repo_pages:
                print_error(t("missing_repo_config"))
                return
                
            try:
                if processor.deploy_to_repos(repo_source, repo_pages, commit_msg):
                    if output_format == "json":
                        from src.utils import print_formatted_output
                        result = {
                            "status": "success",
                            "message": t("republish_success")
                        }
                        print_formatted_output(result, "json")
                    else:
                        print_success(t("republish_success"))
            except Exception as e:
                print_error(t("deployment_failed", error=str(e)))
                return
        elif args.command == 'unpublish':
            source_dir = Path(args.source).expanduser()
            hugo_dir = Path(args.hugo_dir).expanduser()

            if not source_dir.exists():
                print_error(t("source_dir_not_exist", source_dir=source_dir))
                return

            if not hugo_dir.exists():
                print_error(t("hugo_dir_not_exist", hugo_dir=hugo_dir))
                return

            # 创建博客处理器实例
            processor = BlogProcessor(source_dir, hugo_dir)
            
            # 根据输出格式设置全局变量或选项
            output_format = args.output_format
            
            # 取消发布流程
            try:
                published = processor.list_published_markdowns()
            except Exception as e:
                print_error(t("list_published_error", error=str(e)))
                return
                
            if not published:
                print_warning(t("no_articles_to_unpublish"))
                return
                
            print(f"{CLIColors.YELLOW}{t('published_list_header')}{CLIColors.RESET}")
            for idx, (md_file, yaml_data) in enumerate(published):
                print(f"[{idx}] {md_file}")
            
            try:
                idxs_input = input(t("unpublish_selection_prompt")).strip()
            except KeyboardInterrupt:
                print_error(t("cancel_by_user"))
                return
                
            if not idxs_input:
                print_warning(t("no_selection_cancel"))
                return
                
            try:
                idxs = [int(i) for i in idxs_input.split(',') if i.strip().isdigit() and int(i) < len(published)]
                if not idxs:
                    print_error(t("no_valid_indices"))
                    return
            except ValueError:
                print_error(t("input_format_error"))
                return
                
            for i in idxs:
                md_file, yaml_data = published[i]
                try:
                    processor.set_publish_false(md_file)
                    article_name = Path(md_file).stem
                    processor.unpublish_article(article_name)
                except Exception as e:
                    print_error(t("process_file_error", md_file_name=md_file.name, error=str(e)))
                    continue

            print(f"{CLIColors.YELLOW}{t('push_to_remote')}{CLIColors.RESET}")
            try:
                commit_msg = input(f"{t('unpublish_commit_prompt')}").strip() or t("default_unpublish_msg")
            except KeyboardInterrupt:
                print_error(t("cancel_by_user"))
                return
                
            # Validate repository URLs
            repo_source = config.get('repositories.source.url')
            repo_pages = config.get('repositories.pages.url')
            if not repo_source or not repo_pages:
                print_error(t("missing_repo_config"))
                return
                
            try:
                processor.deploy_to_repos(repo_source, repo_pages, commit_msg)
            except Exception as e:
                print_error(t("deployment_failed", error=str(e)))
                return
        elif args.command == 'publish':
            source_dir = Path(args.source).expanduser()
            hugo_dir = Path(args.hugo_dir).expanduser()

            if not source_dir.exists():
                print_error(t("source_dir_not_exist", source_dir=source_dir))
                return

            if not hugo_dir.exists():
                print_error(t("hugo_dir_not_exist", hugo_dir=hugo_dir))
                return

            # 创建博客处理器实例
            processor = BlogProcessor(source_dir, hugo_dir)
            
            # 根据输出格式设置全局变量或选项
            output_format = args.output_format

            # 正常发布流程
            selected_files = args.files

            # 如果使用了 --select 参数，让用户选择文章
            if args.select:
                try:
                    selected_files = select_articles_to_publish(processor)
                except KeyboardInterrupt:
                    print_error(t("cancel_by_user"))
                    return
                except Exception as e:
                    print_error(t("process_file_error", md_file_name="selecting articles", error=str(e)))
                    return
                if not selected_files:
                    return

            # 处理文件
            try:
                processed_files = processor.process_markdown_files(selected_files, as_draft=args.draft)
            except Exception as e:
                print_error(t("process_file_error", md_file_name="files", error=str(e)))
                return

            if not processed_files:
                if output_format == "json":
                    from src.utils import print_formatted_output
                    result = {
                        "status": "warning",
                        "message": t("no_files_processed")
                    }
                    print_formatted_output(result, "json")
                else:
                    print_warning(t("no_files_processed"))
                return

            if output_format == "json":
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

            # Deploy to repositories
            should_deploy = True
            if not args.no_interactive:
                try:
                    should_deploy = input(f"\n{CLIColors.YELLOW}{t('confirm_deployment')}{CLIColors.RESET}").lower().strip() in ('y', 'yes')
                except KeyboardInterrupt:
                    print_error(t("cancel_by_user"))
                    return
            elif args.no_interactive:
                print_info(t('cli_no_interactive_assuming_yes'))
                should_deploy = True
                
            if should_deploy:
                # Check if SSH key is configured
                try:
                    result = subprocess.run(['ssh', '-T', 'git@github.com'],
                                         stderr=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         check=False,
                                         timeout=10)  # Add timeout to avoid hanging
                    if result.returncode != 0:
                        print_warning(t("ssh_test_failed", error="SSH connection to GitHub failed. Please check your SSH keys."))
                except subprocess.TimeoutExpired:
                    print_error(t("ssh_test_timeout"))
                    return
                except Exception as e:
                    print_error(t("ssh_test_failed", error=str(e)))
                    return

                # Get commit message
                try:
                    commit_msg = input(f"\n{CLIColors.YELLOW}{t('enter_commit_msg')}{CLIColors.RESET}").strip()
                except KeyboardInterrupt:
                    print_error(t("cancel_by_user"))
                    return
                    
                if not commit_msg:
                    print_error(t("commit_msg_required"))
                    return

                # Show deployment plan
                print(f"\n{CLIColors.YELLOW}{t('deployment_plan')}{CLIColors.RESET}")
                print(t("deploy_step_checkout"))
                print(t("deploy_step_add"))
                print(t('deploy_step_commit', commit_msg=commit_msg))
                print(t("deploy_step_push_source"))
                print(t("deploy_step_build"))
                print(t("deploy_step_push_pages"))

                try:
                    if input(f"\n{CLIColors.YELLOW}{t('confirm_action_prompt')}{CLIColors.RESET}").lower().strip() not in ('y', 'yes'):
                        print_error(t("deploy_cancelled"))
                        return
                except KeyboardInterrupt:
                    print_error(t("cancel_by_user"))
                    return

                repo_source = config.get('repositories.source.url')
                repo_pages = config.get('repositories.pages.url')
                
                # Validate repository URLs
                if not repo_source or not repo_pages:
                    print_error(t("missing_repo_config"))
                    return
                    
                try:
                    processor.deploy_to_repos(repo_source, repo_pages, commit_msg)
                except Exception as e:
                    print_error(t("deployment_failed", error=str(e)))
                    return
    except KeyboardInterrupt:
        print_error(t("cancel_by_user"))
    except Exception as e:
        from src.utils.cli_utils import handle_exception
        handle_exception(e, "main")

if __name__ == '__main__':
    main()
