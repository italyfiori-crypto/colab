#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理过长句子文件脚本
删除拆分得过长的句子文件以及对应的音频、解析和字幕文件
"""

import os
import argparse
import glob
from typing import List, Tuple, Dict


class LongSentenceCleaner:
    """过长句子文件清理器"""
    
    def __init__(self, max_char_length: int = 200):
        """
        初始化清理器
        
        Args:
            max_char_length: 最大字符长度阈值
        """
        self.max_char_length = max_char_length
        self.related_dirs = ['audio', 'analysis', 'subtitles']
    
    def validate_book_dir(self, book_dir: str) -> bool:
        """
        验证书籍目录是否有效
        
        Args:
            book_dir: 书籍目录路径
            
        Returns:
            是否是有效的书籍目录
        """
        if not os.path.exists(book_dir):
            print(f"❌ 书籍目录不存在: {book_dir}")
            return False
        
        if not os.path.isdir(book_dir):
            print(f"❌ 路径不是目录: {book_dir}")
            return False
        
        sentences_dir = os.path.join(book_dir, 'sentences')
        if not os.path.exists(sentences_dir):
            print(f"❌ 句子目录不存在: {sentences_dir}")
            return False
        
        return True
    
    def check_sentence_file(self, file_path: str) -> Tuple[bool, int]:
        """
        检查句子文件是否超过长度阈值
        
        Args:
            file_path: 句子文件路径
            
        Returns:
            (是否过长, 最大行字符长度)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            max_line_length = 0
            for line_num, line in enumerate(lines, 1):
                # 跳过标题行、空行、注释行
                line = line.strip()
                if not line or line_num == 1 or line.startswith('<!--'):
                    continue
                
                line_length = len(line)
                if line_length > max_line_length:
                    max_line_length = line_length
            
            return max_line_length > self.max_char_length, max_line_length
            
        except Exception as e:
            print(f"❌ 读取文件失败 {file_path}: {e}")
            return False, 0
    
    def find_long_sentence_files(self, book_dir: str) -> List[Tuple[str, int]]:
        """
        查找书籍目录下过长的句子文件
        
        Args:
            book_dir: 书籍目录路径
            
        Returns:
            过长文件列表: [(文件路径, 最大字符长度), ...]
        """
        sentences_dir = os.path.join(book_dir, 'sentences')
        if not os.path.exists(sentences_dir):
            return []
        
        long_files = []
        sentence_files = glob.glob(os.path.join(sentences_dir, '*.txt'))
        
        for file_path in sentence_files:
            is_long, max_length = self.check_sentence_file(file_path)
            if is_long:
                long_files.append((file_path, max_length))
        
        return sorted(long_files, key=lambda x: x[1], reverse=True)
    
    def find_related_files(self, sentence_file: str, book_dir: str) -> List[str]:
        """
        查找与句子文件相关的其他文件
        
        Args:
            sentence_file: 句子文件路径
            book_dir: 书籍目录路径
            
        Returns:
            相关文件路径列表
        """
        filename = os.path.basename(sentence_file)
        related_files = []
        
        for dir_name in self.related_dirs:
            dir_path = os.path.join(book_dir, dir_name)
            if os.path.exists(dir_path):
                # 查找同名文件（可能有不同扩展名）
                base_name = os.path.splitext(filename)[0]
                pattern = os.path.join(dir_path, f"{base_name}.*")
                matched_files = glob.glob(pattern)
                related_files.extend(matched_files)
        
        return related_files
    
    def delete_files(self, files_to_delete: List[str]) -> Dict[str, int]:
        """
        删除文件列表
        
        Args:
            files_to_delete: 要删除的文件列表
            
        Returns:
            删除统计信息
        """
        stats = {'success': 0, 'failed': 0}
        
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                stats['success'] += 1
                print(f"🗑️  已删除: {file_path}")
            except Exception as e:
                stats['failed'] += 1
                print(f"❌ 删除失败 {file_path}: {e}")
        
        return stats
    
    def preview_cleanup(self, book_dir: str) -> None:
        """
        预览清理操作（不实际删除）
        
        Args:
            book_dir: 书籍目录路径
        """
        print(f"🔍 扫描过长句子文件 (最大字符长度: {self.max_char_length})")
        print(f"📂 书籍目录: {book_dir}")
        print("-" * 80)
        
        if not self.validate_book_dir(book_dir):
            return
        
        book_name = os.path.basename(book_dir)
        long_files = self.find_long_sentence_files(book_dir)
        
        if not long_files:
            print(f"📭 {book_name}: 未发现过长句子文件")
            return
        
        print(f"\n📚 书籍: {book_name}")
        print(f"🔴 发现 {len(long_files)} 个过长句子文件:")
        
        total_related = 0
        for sentence_file, max_length in long_files:
            filename = os.path.basename(sentence_file)
            print(f"  • {filename} (最大行长度: {max_length} 字符)")
            
            # 查找相关文件
            related_files = self.find_related_files(sentence_file, book_dir)
            if related_files:
                print(f"    关联文件:")
                for related_file in related_files:
                    rel_path = os.path.relpath(related_file, book_dir)
                    print(f"      - {rel_path}")
                total_related += len(related_files)
        
        print(f"\n📊 预览统计:")
        print(f"  🔴 过长句子文件: {len(long_files)} 个")
        print(f"  🔗 关联文件: {total_related} 个")
        print(f"  📝 总计将删除: {len(long_files) + total_related} 个文件")
    
    def execute_cleanup(self, book_dir: str) -> None:
        """
        执行清理操作（实际删除文件）
        
        Args:
            book_dir: 书籍目录路径
        """
        print(f"🗑️  执行清理过长句子文件 (最大字符长度: {self.max_char_length})")
        print(f"📂 书籍目录: {book_dir}")
        print("-" * 80)
        
        if not self.validate_book_dir(book_dir):
            return
        
        book_name = os.path.basename(book_dir)
        long_files = self.find_long_sentence_files(book_dir)
        
        if not long_files:
            print(f"📭 {book_name}: 未发现过长句子文件")
            return
        
        print(f"\n📚 处理书籍: {book_name}")
        
        total_stats = {'success': 0, 'failed': 0}
        for sentence_file, max_length in long_files:
            filename = os.path.basename(sentence_file)
            print(f"\n🔴 处理过长文件: {filename} (最大行长度: {max_length} 字符)")
            
            # 收集所有要删除的文件
            files_to_delete = [sentence_file]
            related_files = self.find_related_files(sentence_file, book_dir)
            files_to_delete.extend(related_files)
            
            # 删除文件
            stats = self.delete_files(files_to_delete)
            total_stats['success'] += stats['success']
            total_stats['failed'] += stats['failed']
        
        print(f"\n📊 清理统计:")
        print(f"  ✅ 成功删除: {total_stats['success']} 个文件")
        print(f"  ❌ 删除失败: {total_stats['failed']} 个文件")
        print(f"🎉 清理完成!")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='清理过长句子文件及其关联文件')
    parser.add_argument('book_dir', help='书籍目录路径（如: output/1812_格林童话_Grimm\'s Fairy Tales）')
    parser.add_argument('--max-length', type=int, default=200, 
                      help='最大字符长度阈值 (默认: 200)')
    parser.add_argument('--delete', action='store_true', 
                      help='实际删除文件（默认只预览）')
    
    args = parser.parse_args()
    
    # 创建清理器
    cleaner = LongSentenceCleaner(max_char_length=args.max_length)
    
    if args.delete:
        # 执行删除
        print("⚠️  警告：将要实际删除文件！")
        confirm = input("确认继续？(y/N): ")
        if confirm.lower() in ['y', 'yes']:
            cleaner.execute_cleanup(args.book_dir)
        else:
            print("🚫 操作已取消")
    else:
        # 预览模式
        cleaner.preview_cleanup(args.book_dir)
        print(f"\n💡 使用 --delete 参数来实际删除文件")


if __name__ == '__main__':
    main()