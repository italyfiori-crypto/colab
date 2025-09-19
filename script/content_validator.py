#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容比对脚本
比对 output 目录下书籍的 sentences 和 sub_chapters 内容是否对应，检测内容缺失
"""

import os
import re
import argparse
import glob
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class ComparisonResult:
    """比对结果数据类"""
    file_path: str
    is_match: bool
    original_length: int
    processed_length: int
    missing_content: Optional[str] = None
    extra_content: Optional[str] = None
    similarity_percent: float = 0.0


class TextNormalizer:
    """文本标准化工具"""
    
    
    @staticmethod
    def normalize(text: str) -> str:
        """
        标准化文本：去除所有空格，专注于内容本身
        
        Args:
            text: 原始文本
            
        Returns:
            标准化后的文本（无空格）
        """
        if not text:
            return ""
        
        # 去除首尾空格
        text = text.strip()
        
        # 去除段落间的多余换行，但保留段落结构
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # 关键简化：去除所有空格和制表符
        text = re.sub(r'[ \t]+', '', text)
        
        return text
    
    @staticmethod
    def extract_content_only(text: str) -> str:
        """
        提取纯内容，忽略标题行
        
        Args:
            text: 包含标题的完整文本
            
        Returns:
            去除标题后的内容文本
        """
        lines = text.split('\n')
        if len(lines) <= 2:
            return text
        
        # 跳过第一行标题和第二行空行
        content_lines = lines[2:]
        return '\n'.join(content_lines)


class FilePairMatcher:
    """文件配对工具"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
    
    def get_book_directories(self) -> List[str]:
        """获取所有书籍目录"""
        book_dirs = []
        if not os.path.exists(self.output_dir):
            return book_dirs
        
        for item in os.listdir(self.output_dir):
            book_path = os.path.join(self.output_dir, item)
            if os.path.isdir(book_path) and not item.startswith('.'):
                # 检查是否包含必要的子目录
                sub_chapters_dir = os.path.join(book_path, "sub_chapters")
                sentences_dir = os.path.join(book_path, "sentences")
                if os.path.exists(sub_chapters_dir) and os.path.exists(sentences_dir):
                    book_dirs.append(item)
        
        return sorted(book_dirs)
    
    def get_file_pairs(self, book_name: str) -> List[Tuple[str, str]]:
        """
        获取指定书籍的文件配对
        
        Args:
            book_name: 书籍名称
            
        Returns:
            (sub_chapter_file, sentence_file) 元组列表
        """
        pairs = []
        book_path = os.path.join(self.output_dir, book_name)
        
        sub_chapters_dir = os.path.join(book_path, "sub_chapters")
        sentences_dir = os.path.join(book_path, "sentences")
        
        if not (os.path.exists(sub_chapters_dir) and os.path.exists(sentences_dir)):
            return pairs
        
        # 获取 sub_chapters 中的所有文件
        sub_chapter_files = glob.glob(os.path.join(sub_chapters_dir, "*.txt"))
        
        for sub_chapter_file in sub_chapter_files:
            filename = os.path.basename(sub_chapter_file)
            sentence_file = os.path.join(sentences_dir, filename)
            
            if os.path.exists(sentence_file):
                pairs.append((sub_chapter_file, sentence_file))
        
        return sorted(pairs)


class ContentComparator:
    """内容比对工具"""
    
    def __init__(self):
        self.normalizer = TextNormalizer()
    
    def compare_files(self, sub_chapter_file: str, sentence_file: str) -> ComparisonResult:
        """
        比对两个文件的内容
        
        Args:
            sub_chapter_file: 子章节文件路径
            sentence_file: 句子文件路径
            
        Returns:
            比对结果
        """
        try:
            # 读取文件内容
            with open(sub_chapter_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            with open(sentence_file, 'r', encoding='utf-8') as f:
                processed_content = f.read()
            
            # 提取实际内容（去除标题）
            original_text = self.normalizer.extract_content_only(original_content)
            processed_text = self.normalizer.extract_content_only(processed_content)
            
            # 标准化文本
            original_normalized = self.normalizer.normalize(original_text)
            processed_normalized = self.normalizer.normalize(processed_text)
            
            # 计算相似度
            similarity = self._calculate_similarity(original_normalized, processed_normalized)
            
            # 检查是否匹配
            is_match = original_normalized == processed_normalized
            
            # 查找缺失或多余的内容
            missing_content = None
            extra_content = None
            
            if not is_match:
                missing_content = self._find_missing_content(original_normalized, processed_normalized)
                extra_content = self._find_extra_content(original_normalized, processed_normalized)
            
            return ComparisonResult(
                file_path=os.path.basename(sentence_file),
                is_match=is_match,
                original_length=len(original_normalized),
                processed_length=len(processed_normalized),
                missing_content=missing_content,
                extra_content=extra_content,
                similarity_percent=similarity
            )
            
        except Exception as e:
            return ComparisonResult(
                file_path=os.path.basename(sentence_file),
                is_match=False,
                original_length=0,
                processed_length=0,
                missing_content=f"读取文件错误: {str(e)}",
                similarity_percent=0.0
            )
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度百分比"""
        if not text1 and not text2:
            return 100.0
        if not text1 or not text2:
            return 0.0
        
        # 如果完全相同，返回100%
        if text1 == text2:
            return 100.0
        
        # 使用简单的字符级相似度计算
        max_len = max(len(text1), len(text2))
        
        # 计算匹配的字符数（允许位置差异）
        matching_chars = 0
        text1_chars = list(text1)
        text2_chars = list(text2)
        
        # 简单的字符匹配统计
        for char in text1_chars:
            if char in text2_chars:
                text2_chars.remove(char)  # 避免重复计算
                matching_chars += 1
        
        # 计算相似度百分比
        similarity = (matching_chars / max_len) * 100
        return min(100.0, max(0.0, similarity))
    
    def _find_missing_content(self, original: str, processed: str) -> Optional[str]:
        """查找缺失的内容"""
        if len(original) <= len(processed):
            return None
        
        # 简单的差异检测
        for i in range(min(len(original), len(processed))):
            if original[i] != processed[i]:
                # 找到第一个差异点，返回可能缺失的内容片段
                end_pos = min(i + 100, len(original))  # 显示前100个字符
                return original[i:end_pos] + "..." if end_pos < len(original) else original[i:end_pos]
        
        # 如果前面都相同，那么缺失的是后面的部分
        return original[len(processed):len(processed)+100] + "..."
    
    def _find_extra_content(self, original: str, processed: str) -> Optional[str]:
        """查找多余的内容"""
        if len(processed) <= len(original):
            return None
        
        # 简单的多余内容检测
        for i in range(min(len(original), len(processed))):
            if original[i] != processed[i]:
                # 找到第一个差异点
                end_pos = min(i + 100, len(processed))
                return processed[i:end_pos] + "..." if end_pos < len(processed) else processed[i:end_pos]
        
        # 多余的是后面的部分
        return processed[len(original):len(original)+100] + "..."


class ReportGenerator:
    """报告生成工具"""
    
    def __init__(self):
        self.colors = {
            'green': '\033[92m',
            'red': '\033[91m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'reset': '\033[0m',
            'bold': '\033[1m'
        }
    
    def _colorize(self, text: str, color: str) -> str:
        """为文本添加颜色"""
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def print_summary(self, total_files: int, passed_files: int, failed_files: int):
        """打印总结信息"""
        print(f"\n{self._colorize('=' * 60, 'blue')}")
        print(f"{self._colorize('内容比对总结', 'bold')}")
        print(f"{self._colorize('=' * 60, 'blue')}")
        print(f"总文件数: {self._colorize(str(total_files), 'blue')}")
        print(f"通过文件数: {self._colorize(str(passed_files), 'green')}")
        print(f"失败文件数: {self._colorize(str(failed_files), 'red')}")
        
        if total_files > 0:
            success_rate = (passed_files / total_files) * 100
            color = 'green' if success_rate >= 95 else 'yellow' if success_rate >= 80 else 'red'
            print(f"成功率: {self._colorize(f'{success_rate:.1f}%', color)}")
    
    def print_book_results(self, book_name: str, results: List[ComparisonResult], detailed: bool = False):
        """打印单本书的结果"""
        passed = sum(1 for r in results if r.is_match)
        failed = len(results) - passed
        
        print(f"\n{self._colorize(f'📚 {book_name}', 'bold')}")
        print(f"  文件数: {len(results)}, 通过: {self._colorize(str(passed), 'green')}, 失败: {self._colorize(str(failed), 'red')}")
        
        # 显示失败的文件
        for result in results:
            if not result.is_match:
                self._print_error_details(result, detailed)
    
    def _print_error_details(self, result: ComparisonResult, detailed: bool):
        """打印错误详情"""
        print(f"    {self._colorize(result.file_path, 'red')}")
        print(f"     相似度: {result.similarity_percent:.1f}%")
        print(f"     原始长度: {result.original_length}, 处理后长度: {result.processed_length}")
        
        if result.missing_content:
            print(f"     {self._colorize('缺失内容:', 'yellow')} {result.missing_content[:100]}...")
        
        if result.extra_content:
            print(f"     {self._colorize('多余内容:', 'yellow')} {result.extra_content[:100]}...")
        
        if detailed:
            print()


class ContentValidator:
    """主要的内容验证类"""
    
    def __init__(self, output_dir: str = "output"):
        self.file_matcher = FilePairMatcher(output_dir)
        self.comparator = ContentComparator()
        self.reporter = ReportGenerator()
    
    def validate_book(self, book_name: str, errors_only: bool = False, detailed: bool = False) -> Dict[str, List[ComparisonResult]]:
        """验证单本书籍"""
        print(f"🔍 正在检查书籍: {book_name}")
        
        file_pairs = self.file_matcher.get_file_pairs(book_name)
        if not file_pairs:
            print(f"  ⚠️  未找到匹配的文件对")
            return {book_name: []}
        
        results = []
        for sub_chapter_file, sentence_file in file_pairs:
            result = self.comparator.compare_files(sub_chapter_file, sentence_file)
            results.append(result)
        
        # 只在有错误或不是只显示错误模式时显示结果
        if not errors_only or any(not r.is_match for r in results):
            self.reporter.print_book_results(book_name, results, detailed)
        
        return {book_name: results}
    
    def validate_all(self, book_filter: Optional[str] = None, errors_only: bool = False, detailed: bool = False) -> Dict[str, List[ComparisonResult]]:
        """验证所有书籍或指定书籍"""
        books = self.file_matcher.get_book_directories()
        
        if book_filter:
            books = [book for book in books if book_filter.lower() in book.lower()]
        
        if not books:
            print("❌ 未找到任何书籍目录")
            return {}
        
        print(f"📖 找到 {len(books)} 本书籍")
        
        all_results = {}
        total_files = 0
        passed_files = 0
        
        for book_name in books:
            book_results = self.validate_book(book_name, errors_only, detailed)
            all_results.update(book_results)
            
            for results in book_results.values():
                total_files += len(results)
                passed_files += sum(1 for r in results if r.is_match)
        
        failed_files = total_files - passed_files
        self.reporter.print_summary(total_files, passed_files, failed_files)
        
        return all_results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="比对 sentences 和 sub_chapters 内容的完整性")
    parser.add_argument("--book", "-b", help="指定要检查的书籍名称（支持部分匹配）")
    parser.add_argument("--errors-only", "-e", action="store_true", help="只显示有错误的文件")
    parser.add_argument("--detailed", "-d", action="store_true", help="显示详细的错误信息")
    parser.add_argument("--output-dir", "-o", default="output", help="输出目录路径（默认: output）")
    
    args = parser.parse_args()
    
    validator = ContentValidator(args.output_dir)
    validator.validate_all(
        book_filter=args.book,
        errors_only=args.errors_only,
        detailed=args.detailed
    )


if __name__ == "__main__":
    main()