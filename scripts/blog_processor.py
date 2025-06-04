import subprocess
from pathlib import Path
import shutil
import yaml
import re
from datetime import datetime
from scripts.front_matter import (
    FrontMatter,
    extract_yaml_and_content,
    load_tag_category_mapping,
    get_categories_from_tags,
    update_tag_category_mapping
)
from scripts.api_handler import APIHandler

# ANSI 颜色代码
COLOR_GREEN = "\033[92m"    # 成功信息
COLOR_RED = "\033[91m"      # 错误信息
COLOR_YELLOW = "\033[93m"   # 警告和提示
COLOR_BLUE = "\033[94m"     # 步骤和进度
COLOR_BOLD = "\033[1m"      # 粗体
COLOR_DIM = "\033[2m"       # 暗色
COLOR_ITALIC = "\033[3m"    # 斜体
COLOR_UNDERLINE = "\033[4m" # 下划线
COLOR_RESET = "\033[0m"     # 重置颜色
COLOR_CYAN = "\033[96m"     # 信息提示
COLOR_MAGENTA = "\033[95m"  # 强调

# 格式化输出函数
def print_step(step_num, message):
    """打印带编号的步骤信息"""
    print(f"\n{COLOR_BLUE}{COLOR_BOLD}[步骤 {step_num}]{COLOR_RESET} {message}")

def print_success(message):
    """打印成功信息"""
    print(f"{COLOR_GREEN}✓ {message}{COLOR_RESET}")

def print_error(message):
    """打印错误信息"""
    print(f"{COLOR_RED}✗ {message}{COLOR_RESET}")

def print_warning(message):
    """打印警告信息"""
    print(f"{COLOR_YELLOW}! {message}{COLOR_RESET}")

def print_info(message):
    """打印普通信息"""
    print(f"{COLOR_CYAN}ℹ {message}{COLOR_RESET}")

def print_header(message):
    """打印标题信息"""
    print(f"\n{COLOR_MAGENTA}{COLOR_BOLD}{message}{COLOR_RESET}")
    print(f"{COLOR_DIM}{'='*len(message)}{COLOR_RESET}\n")

class BlogProcessor:
    """博客处理类，负责处理博客相关的具体操作"""
    
    def __init__(self, source_dir, hugo_dir, config_path):
        self.source_dir = Path(source_dir)
        self.hugo_dir = Path(hugo_dir)
        self.api_handler = APIHandler(config_path)
    
    def process_mermaid_blocks(self, content):
        """将```mermaid代码块转换为Hugo短代码格式"""
        pattern = r'```mermaid\n(.*?)\n```'
        replacement = r'{{< mermaid >}}\n\1\n{{< /mermaid >}}'
        return re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    def create_new_post(self, title, content, source_file=None, categories=None, tags=None, draft=False):
        """创建新的Hugo博客文章"""
        post_dir = self.hugo_dir / 'content' / 'post' / title.lower().replace(' ', '-')
        post_dir.mkdir(parents=True, exist_ok=True)
        post_file = post_dir / 'index.md'
        
        # 处理图片
        if source_file:
            from scripts.obsidian_image_handler import process_obsidian_images
            content = process_obsidian_images(content, source_file, post_dir, Path(source_file).parent)
        
        # 处理Mermaid代码块
        content = self.process_mermaid_blocks(content)
        
        # 生成摘要
        summary = self.api_handler.generate_summary(content)
        
        # 准备YAML前置数据
        front_matter = FrontMatter({
            'title': title,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'description': summary or f'Content from {title}',
            'draft': draft,
        })
        
        # 处理标签和分类
        tag_mapping = load_tag_category_mapping()
        if tags:
            front_matter.update({'tags': tags})
            if not categories:
                categories = get_categories_from_tags(tags, tag_mapping)
        if categories:
            front_matter.update({'categories': categories})
        
        # 写入文件
        with open(post_file, 'w', encoding='utf-8') as f:
            f.write('---\n')
            yaml.dump(front_matter.to_dict(), f, allow_unicode=True)
            f.write('---\n\n')
            f.write(content)
        
        return post_file
    
    def process_markdown_files(self, selected_files=None, as_draft=False):
        """处理Markdown文件并创建Hugo博客文章"""
        processed_files = []
        
        # 更新标签到分类的映射关系
        update_tag_category_mapping(self.hugo_dir)
        
        # 查找所有Markdown文件
        for md_file in self.source_dir.rglob('*.md'):
            if selected_files and md_file.name not in selected_files:
                continue
                
            front_matter, content = extract_yaml_and_content(md_file)
            if not front_matter or not front_matter.publish:
                print_warning(f"跳过 {md_file.name} - 未标记为发布状态")
                continue
            
            try:
                title = md_file.stem
                new_post = self.create_new_post(
                    title,
                    content,
                    source_file=md_file,
                    categories=front_matter.categories,
                    tags=front_matter.tags,
                    draft=as_draft
                )
                print_success(f"已创建新文章: {new_post}")
                processed_files.append(new_post)
                
            except Exception as e:
                print_error(f"处理 {md_file.name} 时出错: {str(e)}")
        
        return processed_files
    
    def list_published_markdowns(self):
        """列出所有publish: true的markdown文件"""
        published = []
        for md_file in self.source_dir.rglob('*.md'):
            front_matter, _ = extract_yaml_and_content(md_file)
            if front_matter and front_matter.publish:
                published.append((md_file, front_matter))
        return published
    
    def set_publish_false(self, md_file):
        """将markdown文件的publish字段设为false"""
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
    
    def unpublish_article(self, article_name):
        """删除hugo下对应文章文件夹"""
        post_dir = self.hugo_dir / 'content' / 'post' / article_name.lower().replace(' ', '-')
        if post_dir.exists():
            shutil.rmtree(post_dir)
            print_warning(f"已删除Hugo文章: {post_dir}")
            return True
        return False
    
    def preview_site(self):
        """启动Hugo服务器预览站点"""
        try:
            print_info("正在启动Hugo服务器进行预览...")
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
                print_success("预览服务器已启动！")
                print_info("请访问 http://localhost:1313 查看预览")
                print_info("按 Ctrl+C 停止预览...")
                try:
                    preview_process.wait()
                except KeyboardInterrupt:
                    preview_process.terminate()
                    print_info("\n预览服务器已停止")
            else:
                stdout, stderr = preview_process.communicate()
                print_error(f"预览服务器启动失败: {stderr}")
        except Exception as e:
            print_error(f"启动预览服务器时出错: {str(e)}")
    
    def deploy_to_repos(self, repo_source, repo_pages, commit_msg=None):
        """使用SSH部署更改到源码仓库和页面仓库"""
        try:
            # 1. Setup .gitignore
            gitignore_path = self.hugo_dir / '.gitignore'
            if not gitignore_path.exists():
                with open(gitignore_path, 'w') as f:
                    f.write("public/\n.DS_Store\nresources/\n")
            
            # 2. Deploy to source repository
            print(f"\n{COLOR_YELLOW}执行部署流程...{COLOR_RESET}")
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
            print_success("源码仓库更新成功！")
            
            # 3. Build Hugo site
            print_step(2, "构建Hugo站点...")
            subprocess.run(['hugo', '--minify'], cwd=self.hugo_dir, check=True)
            
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
            print_success("GitHub Pages 部署成功！")
            print(f"\n{COLOR_GREEN}全部部署流程已完成！{COLOR_RESET}")
            
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Deployment failed: {str(e)}")
            return False 