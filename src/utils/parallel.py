"""
并行处理模块
提供对耗时操作的并行处理支持
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import shutil
from typing import List, Callable, Any, Optional


def parallel_process(items: List[Any], 
                    func: Callable, 
                    max_workers: Optional[int] = None, 
                    *args, **kwargs) -> List[Any]:
    """
    并行处理项目列表
    :param items: 要处理的项目列表
    :param func: 处理函数
    :param max_workers: 最大工作线程数，默认为系统CPU核心数
    :param args: 传递给处理函数的额外位置参数
    :param kwargs: 传递给处理函数的额外关键字参数
    :return: 处理结果列表
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_item = {executor.submit(func, item, *args, **kwargs): item for item in items}
        
        # 获取结果
        for future in as_completed(future_to_item):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                item = future_to_item[future]
                print(f"处理项目 {item} 时出错: {e}")
                
    return results


def parallel_copy_files(file_mapping: List[tuple], 
                       max_workers: Optional[int] = None) -> bool:
    """
    并行复制文件
    :param file_mapping: 包含(源路径, 目标路径)元组的列表
    :param max_workers: 最大工作线程数
    :return: 如果所有复制操作都成功则返回True，否则返回False
    """
    def copy_single_file(src_dst_pair):
        src, dst = src_dst_pair
        dst_path = Path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return f"已复制 {src} 到 {dst}"
    
    try:
        results = parallel_process(file_mapping, copy_single_file, max_workers)
        print(f"完成 {len(results)} 个文件的复制")
        return True
    except Exception as e:
        print(f"并行复制文件时出错: {e}")
        return False