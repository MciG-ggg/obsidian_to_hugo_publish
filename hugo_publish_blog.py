# 博客发布脚本
# 用于将Markdown文件发布到Hugo博客并部署到GitHub Pages

import argparse
from pathlib import Path
import subprocess
import sys
import os
from src.utils.utils import ( COLOR_BOLD, COLOR_RESET, COLOR_DIM, COLOR_YELLOW)

# 添加src目录到Python路径
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

from src.core.config_manager import Config
from src.core.blog_processor import BlogProcessor
from src.utils.utils import print_step, print_success, print_error, print_warning, print_info, print_header
from src.i18n.i18n import set_locale, t
from src.utils.logger import set_log_file, set_log_level

def select_articles_to_publish(processor):
    """让用户选择要发布的文章"""
    published = processor.list_published_markdowns()
    if not published:
        print_warning(t("no_published_articles"))
        return []
    print_header(t("start_republish_header"))
    for idx, (md_file, yaml_data) in enumerate(published):
        title = yaml_data.title if yaml_data.title else md_file.stem
        description = yaml_data.description if yaml_data.description else t("no_description", description="无描述")  # 如果翻译文件中没有这个键，就使用中文
        print(f"{COLOR_BOLD}[{idx}]{COLOR_RESET} {title}")
        print(f"    {COLOR_DIM}{t('file_label', filename=md_file.name)}{COLOR_RESET}")  # 需要在翻译文件中添加file_label
        print(f"    {COLOR_DIM}{t('description_label', description=description)}{COLOR_RESET}")  # 需要在翻译文件中添加description_label
        if yaml_data.tags:
            print(f"    {COLOR_DIM}{t('tags_label', tags=', '.join(yaml_data.tags))}{COLOR_RESET}")  # 需要在翻译文件中添加tags_label
        print()

    while True:
        selection = input(f"{COLOR_YELLOW}{t('select_article_prompt')}{COLOR_RESET}").strip()  # 需要在翻译文件中添加select_article_prompt

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

            selected_files = [published[idx][0] for idx in selected_indices]
            print_success(t("selected_count", count=len(selected_files)))  # 需要在翻译文件中添加selected_count
            return selected_files

        except ValueError:
            print_error(t("input_format_error"))

def main():
    try:
        config = Config()

        parser = argparse.ArgumentParser(description='将Markdown文件发布到Hugo博客')  # 这个可以本地化，但argparse的description通常不国际化
        parser.add_argument('--source',
                           default=config.get('paths.obsidian.vault'),
                           help='包含markdown文件的源目录')
        parser.add_argument('--hugo-dir',
                           default=config.get('paths.hugo.blog'),
                           help='Hugo博客目录')
        parser.add_argument('--files',
                           nargs='*',
                           help='要处理的特定markdown文件（可选）')
        parser.add_argument('--unpublish', action='store_true', help='取消发布模式')
        parser.add_argument('--preview', action='store_true', help='预览模式，启动Hugo服务器')
        parser.add_argument('--draft', action='store_true', help='以草稿模式发布文章')
        parser.add_argument('--republish', action='store_true', help='取消所有发布的文章并重新发布')
        parser.add_argument('--select', action='store_true', help='交互式选择要发布的文章')
        parser.add_argument('--lang', 
                           default=os.getenv('LANG', 'zh-CN').split('.')[0].replace('_', '-'), 
                           choices=['zh-CN', 'en'], 
                           help='设置语言 (默认: 从环境变量LANG获取)')
        parser.add_argument('--log-file',
                           help='指定日志文件路径')
        parser.add_argument('--log-level',
                           default='INFO',
                           choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                           help='设置日志级别 (默认: INFO)')

        args = parser.parse_args()
        
        # 设置语言环境
        set_locale(args.lang)
        
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

        # 根据参数执行相应操作
        if args.preview:
            processor.preview_site()
        elif args.republish:
            # 重新发布流程
            print_header(t("start_republish_header"))
            published = processor.list_published_markdowns()
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
                print_warning(t("no_files_processed"))
                return

            print_success(t("process_files_success", count=len(processed_files)))

            print_step(3, t("deploy_step"))
            commit_msg = t("start_republish_header")
            repo_source = config.get('repositories.source.url')
            repo_pages = config.get('repositories.pages.url')
            if processor.deploy_to_repos(repo_source, repo_pages, commit_msg):
                print_success(t("republish_success"))
            return
        elif args.unpublish:
            # 取消发布流程
            try:
                published = processor.list_published_markdowns()
            except Exception as e:
                print_error(t("find_markdown_error", error=str(e)))
                return
                
            if not published:
                print_warning(t("no_articles_to_unpublish"))
                return
            print(f"{COLOR_YELLOW}{t('published_list_header')}{COLOR_RESET}")
            for idx, (md_file, yaml_data) in enumerate(published):
                print(f"[{idx}] {md_file}")
            idxs = input(t("unpublish_selection_prompt")).strip()
            if not idxs:
                print_warning(t("no_selection_cancel"))
                return
            try:
                idxs = [int(i) for i in idxs.split(',') if i.strip().isdigit() and int(i) < len(published)]
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

            print(f"{COLOR_YELLOW}{t('push_to_remote')}{COLOR_RESET}")
            commit_msg = input(f"{t('unpublish_commit_prompt')}").strip() or t("default_unpublish_msg")
            repo_source = config.get('repositories.source.url')
            repo_pages = config.get('repositories.pages.url')
            try:
                processor.deploy_to_repos(repo_source, repo_pages, commit_msg)
            except Exception as e:
                print_error(t("deployment_failed", error=str(e)))
                return
            return
        else:
            # 正常发布流程
            selected_files = args.files

            # 如果使用了 --select 参数，让用户选择文章
            if args.select:
                try:
                    selected_files = select_articles_to_publish(processor)
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
                print_warning(t("no_files_processed"))
                return

            print_success(t("process_files_success", count=len(processed_files)))

            # Deploy to repositories
            if input(f"\n{COLOR_YELLOW}{t('confirm_deployment')}{COLOR_RESET}").lower().strip() in ('y', 'yes'):  # 需要在翻译文件中添加confirm_deployment
                # Check if SSH key is configured
                try:
                    subprocess.run(['ssh', '-T', 'git@github.com'],
                                 stderr=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 check=False)
                except Exception as e:
                    print_error(t("ssh_test_failed", error=str(e)))
                    return

                # Get commit message
                commit_msg = input(f"\n{COLOR_YELLOW}{t('enter_commit_msg')}{COLOR_RESET}").strip()  # 需要在翻译文件中添加enter_commit_msg
                if not commit_msg:
                    print_error(t("commit_msg_required"))
                    return

                # Show deployment plan
                print(f"\n{COLOR_YELLOW}{t('deployment_plan')}{COLOR_RESET}")
                print(t("deploy_step_checkout"))
                print(t("deploy_step_add"))
                print(t('deploy_step_commit', commit_msg=commit_msg))
                print(t("deploy_step_push_source"))
                print(t("deploy_step_build"))
                print(t("deploy_step_push_pages"))

                if input(f"\n{COLOR_YELLOW}{t('confirm_action_prompt')}{COLOR_RESET}").lower().strip() not in ('y', 'yes'):  # 需要在翻译文件中添加confirm_action_prompt
                    print_error(t("deploy_cancelled"))
                    return

                repo_source = config.get('repositories.source.url')
                repo_pages = config.get('repositories.pages.url')
                try:
                    processor.deploy_to_repos(repo_source, repo_pages, commit_msg)
                except Exception as e:
                    print_error(t("deployment_failed", error=str(e)))
                    return
    except KeyboardInterrupt:
        print_error(t("cancel_by_user"))
    except Exception as e:
        print_error(t("unexpected_error", error=str(e)))
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
