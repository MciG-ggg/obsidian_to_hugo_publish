import subprocess
from pathlib import Path
import shutil
import yaml
import re
from datetime import datetime
from src.core.front_matter import (
    FrontMatter,
    extract_yaml_and_content,
    load_tag_category_mapping,
    get_categories_from_tags,
    update_tag_category_mapping
)
from src.utils.cli_utils import CLIColors
from src.utils.utils import print_step, print_success, print_error, print_warning, print_info, print_header
from src.utils.logger import debug, info, warning, error
from src.i18n.i18n import t

class BlogProcessor:
    """博客处理类，负责处理博客相关的具体操作"""
    
    def __init__(self, source_dir, hugo_dir, config_path = 'config.yaml'):
        self.source_dir = Path(source_dir)
        self.hugo_dir = Path(hugo_dir)
        info(f"BlogProcessor initialized with source_dir: {source_dir}, hugo_dir: {hugo_dir}")
    
    def process_mermaid_blocks(self, content):
        """将```mermaid代码块转换为Hugo短代码格式"""
        # 使用更灵活的模式，允许空白字符变化
        pattern = r'```mermaid\s*\n(.*?)\s*\n\s*```'
        replacement = r'{{< mermaid >}}\n\1\n{{< /mermaid >}}'
        return re.sub(pattern, replacement, content, flags=re.DOTALL)

    def process_note_blocks(self, content):
        """将 [!NOTE] 块转换为 Hugo shortcode 格式"""
        # 匹配 > [!NOTE] Title\n> 内容... 形式
        pattern = r'> \[!NOTE\](?: (.*))?\n((?:> .*(?:\n|$))+)'  # 支持可选标题和多行内容
        def replace_note(match):
            title = match.group(1) or "Note"
            note_content = match.group(2)
            # 清理内容：移除每行开头的 '> '
            lines = note_content.strip().split('\n')
            cleaned_lines = [line[2:] if line.startswith('> ') else line for line in lines]
            cleaned_content = '\n'.join(cleaned_lines)
            return f'{{{{< admonition type="note" title="{title}" >}}}}\n{cleaned_content}\n{{{{< /admonition >}}}}'
        return re.sub(pattern, replace_note, content, flags=re.MULTILINE)

    def create_new_post(self, title, content, source_file=None, categories=None, tags=None, draft=False, description=None):
        """创建新的Hugo博客文章"""
        try:
            post_dir = self.hugo_dir / 'content' / 'post' / title.lower().replace(' ', '-')
            post_dir.mkdir(parents=True, exist_ok=True)
            post_file = post_dir / 'index.md'
            
            # 处理图片
            if source_file:
                from src.handlers.obsidian_image_handler import process_obsidian_images
                try:
                    content = process_obsidian_images(content, source_file, post_dir, Path(source_file).parent)
                except Exception as e:
                    print_warning(t("image_processing_error", error=str(e)))
                    # 即使图片处理出错，也要继续处理文章
            
            # 处理Mermaid代码块
            content = self.process_mermaid_blocks(content)
            # 处理NOTE块
            content = self.process_note_blocks(content)
            
            # 准备YAML前置数据，带入 description
            front_matter = FrontMatter({
                'title': title,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'draft': draft,
                'description': description or '',
            })

            # 检查是否已有description
            if front_matter.description:
                print_info(t("using_existing_desc", description=front_matter.description))
          
            first_image = None
            # 匹配两种格式的图片（排除完整URL）
            img_patterns = [
                r'!\[([^\]]*)\]\(([^)]+)\)',  # ![alt](image.jpg)
                r'!\[\[([^]]+)\]\]'  # ![[image.jpg]]
            ]
            for pattern in img_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    if pattern == r'!\[\[([^]]+)\]\]':
                        img_name = match.group(1)
                    else:
                        img_name = match.group(2)
                    
                    # 确保不选择完整URL（如 http:// 或 https:// 开头的）
                    if not (img_name.startswith('http://') or img_name.startswith('https://')):
                        # 如果是绝对路径(/images/...)，将其转换为相对路径
                        if img_name.startswith('/images/'):
                            img_name = img_name[8:]  # 去掉 '/images/' 前缀
                        first_image = img_name
                        break
                if first_image:
                    break
            front_matter.update({'image': first_image if first_image else ''})
            
            # 处理标签和分类
            try:
                tag_mapping = load_tag_category_mapping()
                if tags:
                    front_matter.update({'tags': tags})
                    if not categories:
                        categories = get_categories_from_tags(tags, tag_mapping)
                if categories:
                    front_matter.update({'categories': categories})
            except Exception as e:
                print_warning(t("tag_category_error", error=str(e)))
            
            # 写入文件
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write('---\n')
                yaml.dump(front_matter.to_dict(), f, allow_unicode=True)
                f.write('---\n\n')
                f.write(content)
            
            return post_file
        except Exception as e:
            print_error(t("process_file_error", md_file_name=title, error=str(e)))
            raise
    
    def process_markdown_files(self, selected_files=None, as_draft=False):
        """处理Markdown文件并创建Hugo博客文章"""
        processed_files = []
        
        try:
            # 更新标签到分类的映射关系
            update_tag_category_mapping(self.hugo_dir)
            
            # 收集所有需要处理的Markdown文件
            files_to_process = []
            for md_file in self.source_dir.rglob('*.md'):
                if selected_files and md_file.name not in selected_files:
                    continue
                    
                front_matter, content = extract_yaml_and_content(md_file)
                if front_matter and front_matter.publish:
                    files_to_process.append((md_file, front_matter, content))
            
            # 使用并行处理创建文章
            from src.utils.parallel import parallel_process
            
            def process_single_file(args):
                md_file, front_matter, content = args
                try:
                    # 使用FrontMatter中的标题，如果没有则使用文件名
                    title = front_matter.title if front_matter.title else md_file.stem
                    new_post = self.create_new_post(
                        title,
                        content,
                        source_file=md_file,
                        categories=front_matter.categories,
                        tags=front_matter.tags,
                        draft=as_draft,
                        description=front_matter.description
                    )
                    print_success(t("create_new_article", post_file=str(new_post)))
                    return new_post
                except Exception as e:
                    print_error(t("process_file_error", md_file_name=md_file.name, error=str(e)))
                    return None
            
            if files_to_process:
                results = parallel_process(files_to_process, process_single_file, max_workers=4)
                
                # 收集成功处理的文件
                for result in results:
                    if result is not None:
                        processed_files.append(result)
                    
        except Exception as e:
            print_error(t("processing_markdown_error", error=str(e)))
            raise
        
        return processed_files
    
    def list_published_markdowns(self):
        """列出所有publish: true的markdown文件"""
        published = []
        try:
            for md_file in self.source_dir.rglob('*.md'):
                try:
                    front_matter, _ = extract_yaml_and_content(md_file)
                    if front_matter and front_matter.publish:
                        published.append((md_file, front_matter))
                except Exception as e:
                    print_warning(t("read_file_error", md_file=str(md_file), error=str(e)))
                    continue
        except Exception as e:
            print_error(t("find_markdown_error", error=str(e)))
            raise
        
        return published
    
    def set_publish_false(self, md_file):
        """将markdown文件的publish字段设为false"""
        try:
            front_matter, content = extract_yaml_and_content(md_file)
            if not front_matter or not front_matter.publish:
                return False
            
            front_matter.update({'publish': False})
            
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write('---\n')
                yaml.dump(front_matter.to_dict(), f, allow_unicode=True)
                f.write('---\n\n')
                f.write(content)
            return True
        except Exception as e:
            print_error(t("update_publish_error", md_file=str(md_file), error=str(e)))
            return False
    
    def unpublish_article(self, article_name):
        """删除hugo下对应文章文件夹"""
        try:
            post_dir = self.hugo_dir / 'content' / 'post' / article_name.lower().replace(' ', '-')
            if post_dir.exists():
                shutil.rmtree(post_dir)
                print_warning(t("unpublished_success", article_name=article_name))
                return True
            return False
        except Exception as e:
            print_error(t("unpublish_error", article_name=article_name, error=str(e)))
            return False
    
    def preview_site(self):
        """启动Hugo服务器预览站点"""
        try:
            print_info(t("start_preview"))
            
            # 检查Hugo是否已安装
            try:
                subprocess.run(['hugo', 'version'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL, 
                             check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print_error(t("hugo_not_installed"))
                return
            
            preview_process = subprocess.Popen(
                ['hugo', 'server', '--buildDrafts', '--buildFuture'],
                cwd=self.hugo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            import time
            time.sleep(2)
            
            if preview_process.poll() is None:
                print_success(t("preview_started"))
                print_info(t("preview_url"))
                print_info(t("stop_preview"))
                try:
                    preview_process.wait()
                except KeyboardInterrupt:
                    preview_process.terminate()
                    print_info(t("preview_stopped"))
            else:
                stdout, stderr = preview_process.communicate()
                print_error(t("preview_failed", error=stderr))
        except Exception as e:
            print_error(t("preview_error", error=str(e)))
    
    def deploy_to_repos(self, repo_source, repo_pages, commit_msg=None):
        """使用SSH部署更改到源码仓库和页面仓库"""
        try:
            # 1. Setup .gitignore
            gitignore_path = self.hugo_dir / '.gitignore'
            if not gitignore_path.exists():
                with open(gitignore_path, 'w') as f:
                    f.write("public/\n.DS_Store\nresources/\n")
            
            # 2. Deploy to source repository
            print(f"\n{CLIColors.YELLOW}执行部署流程...{CLIColors.RESET}")
            
            # 检查Git是否已安装
            try:
                subprocess.run(['git', '--version'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL, 
                             check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print_error("Git未安装或未在PATH中找到，请先安装Git")
                return False
            
            # 检查是否在git仓库中
            if not (self.hugo_dir / '.git').exists():
                print_error(f"{self.hugo_dir} 不是一个Git仓库")
                return False
                
            subprocess.run(['git', 'checkout', 'main'], cwd=self.hugo_dir, check=True)
            subprocess.run(['git', 'pull', 'origin', 'main'], cwd=self.hugo_dir, check=True)
            
            subprocess.run(['git', 'rm', '-r', '--cached', 'public'], 
                         cwd=self.hugo_dir, stderr=subprocess.DEVNULL, check=False)
            subprocess.run(['git', 'add', '-A'], cwd=self.hugo_dir, check=True)
            
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  cwd=self.hugo_dir, capture_output=True, text=True)
            if result.stdout.strip():
                commit_msg = commit_msg or "Update blog content"
                subprocess.run(['git', 'commit', '-m', commit_msg, '--allow-empty'], 
                             cwd=self.hugo_dir, check=True)
            
            subprocess.run(['git', 'remote', 'set-url', 'origin', repo_source], 
                         cwd=self.hugo_dir, check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], cwd=self.hugo_dir, check=True)
            print_success(t("deploy_success"))
            
            # 3. Build Hugo site
            print_step(2, t("build_site_step"))
            try:
                subprocess.run(['hugo', '--minify'], cwd=self.hugo_dir, check=True)
            except subprocess.CalledProcessError as e:
                print_error(f"构建Hugo站点失败: {str(e)}")
                return False
            
            # 4. Deploy to pages repository
            public_dir = self.hugo_dir / 'public'
            print_step(3, "部署到GitHub Pages仓库...")
            
            if not (public_dir / '.git').exists():
                subprocess.run(['git', 'init'], cwd=public_dir, check=True)
                subprocess.run(['git', 'remote', 'add', 'origin', repo_pages], 
                             cwd=public_dir, check=True)
            else:
                subprocess.run(['git', 'remote', 'set-url', 'origin', repo_pages], 
                             cwd=public_dir, check=True)
            
            subprocess.run(['git', 'add', '.'], cwd=public_dir, check=True)
            pages_msg = f"Deploy website: {commit_msg}" if commit_msg else "Update website"
            subprocess.run(['git', 'commit', '-m', pages_msg, '--allow-empty'], 
                         cwd=public_dir, check=True)
            subprocess.run(['git', 'push', 'origin', 'main', '--force'], 
                         cwd=public_dir, check=True)
            print_success(t("pages_deploy_success"))
            print(f"\n{CLIColors.GREEN}{t('deployment_complete')}{CLIColors.RESET}")
            
            return True
        except subprocess.CalledProcessError as e:
            print_error(t("git_command_failed", error=str(e)))
            return False
        except Exception as e:
            print_error(t("general_error", error=str(e)))
            return False 