#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子章节拆分模块
将过长的章节拆分为更小的子章节，便于阅读和处理
"""

import os
import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class SubChapterConfig:
    """子章节拆分配置类"""
    
    # 每个子章节最大阅读时长（分钟）
    max_reading_minutes: int
    
    # 每分钟阅读字数
    words_per_minute: int
    
    # 是否启用子章节拆分
    enable_splitting: bool
    
    # 每个子章节最少段落数
    min_paragraphs_per_sub: int


class SubChapterSplitter:
    """子章节拆分器"""
    
    def __init__(self, config: SubChapterConfig):
        """
        初始化子章节拆分器
        
        Args:
            config: 子章节拆分配置
        """
        self.config = config
        self.max_words_per_sub = config.max_reading_minutes * config.words_per_minute
    
    def split_chapters(self, chapter_files: List[str], output_dir: str) -> List[str]:
        """
        拆分章节文件为子章节
        
        Args:
            chapter_files: 章节文件路径列表
            output_dir: 输出目录
            
        Returns:
            最终生成的文件路径列表（包含拆分和未拆分的）
        """
        if not self.config.enable_splitting:
            return chapter_files
        
        # 创建子章节输出目录
        sub_chapters_dir = os.path.join(output_dir, "sub_chapters")
        os.makedirs(sub_chapters_dir, exist_ok=True)
        
        final_files = []
        
        for chapter_file in chapter_files:
            # 读取章节内容
            with open(chapter_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取章节标题和内容
            title, body = self._extract_title_and_body(content)
            
            # 判断是否需要拆分
            if self._should_split_chapter(body):
                # 拆分为子章节
                sub_files = self._split_into_sub_chapters(
                    title, body, chapter_file, sub_chapters_dir
                )
                final_files.extend(sub_files)
                print(f"📚 章节 '{title}' 拆分为 {len(sub_files)} 个子章节")
            else:
                # 不需要拆分，直接复制到子章节目录
                filename = os.path.basename(chapter_file)
                target_file = os.path.join(sub_chapters_dir, filename)
                
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                final_files.append(target_file)
                print(f"📄 章节 '{title}' 无需拆分，直接复制")
        
        print(f"\n📁 所有文件已处理完成，输出到: {sub_chapters_dir}")
        return final_files
    
    def _extract_title_and_body(self, content: str) -> Tuple[str, str]:
        """
        提取章节标题和正文内容
        
        Args:
            content: 章节内容
            
        Returns:
            (标题, 正文内容)
        """
        lines = content.split('\n')
        
        # 第一行是标题
        title = lines[0].strip() if lines else "Unknown Title"
        
        # 其余是正文（去除开头的空行）
        body_lines = lines[1:]
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        
        body = '\n'.join(body_lines)
        return title, body
    
    def _should_split_chapter(self, content: str) -> bool:
        """
        判断章节是否需要拆分
        
        Args:
            content: 章节内容
            
        Returns:
            是否需要拆分
        """
        word_count = self._count_words(content)
        return word_count > self.max_words_per_sub
    
    def _count_words(self, text: str) -> int:
        """
        统计文本字数（中英文混合）
        
        Args:
            text: 文本内容
            
        Returns:
            字数
        """
        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 分离中文和英文
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        
        # 中文字符按字计算，英文按词计算
        return chinese_chars + english_words
    
    def _split_into_sub_chapters(
        self, 
        title: str, 
        content: str, 
        original_file: str, 
        output_dir: str
    ) -> List[str]:
        """
        将章节拆分为多个子章节
        
        Args:
            title: 章节标题
            content: 章节内容
            original_file: 原始文件路径
            output_dir: 输出目录
            
        Returns:
            生成的子章节文件路径列表
        """
        # 按段落分割内容
        paragraphs = self._split_into_paragraphs(content)
        
        if len(paragraphs) < self.config.min_paragraphs_per_sub * 2:
            # 段落太少，不拆分
            return [self._copy_to_output(title, content, original_file, output_dir)]
        
        # 计算每个段落的字数
        paragraph_words = [self._count_words(p) for p in paragraphs]
        
        # 将段落分组为子章节
        sub_groups = self._group_paragraphs(paragraphs, paragraph_words)
        
        # 生成子章节文件
        sub_files = []
        base_filename = os.path.splitext(os.path.basename(original_file))[0]
        
        for i, group in enumerate(sub_groups, 1):
            sub_title = f"{title}({i})"
            sub_content = self._format_sub_chapter(sub_title, group)
            sub_filename = f"{base_filename}({i}).txt"
            sub_file_path = os.path.join(output_dir, sub_filename)
            
            with open(sub_file_path, 'w', encoding='utf-8') as f:
                f.write(sub_content)
            
            sub_files.append(sub_file_path)
        
        return sub_files
    
    def _split_into_paragraphs(self, content: str) -> List[str]:
        """
        将内容按段落分割
        
        Args:
            content: 文本内容
            
        Returns:
            段落列表
        """
        # 按双换行符分割段落
        paragraphs = re.split(r'\n\s*\n', content)
        
        # 过滤空段落并清理
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs
    
    def _group_paragraphs(
        self, 
        paragraphs: List[str], 
        paragraph_words: List[int]
    ) -> List[List[str]]:
        """
        将段落分组为子章节
        
        Args:
            paragraphs: 段落列表
            paragraph_words: 每个段落的字数列表
            
        Returns:
            段落分组列表
        """
        total_words = sum(paragraph_words)
        target_sub_count = max(2, (total_words + self.max_words_per_sub - 1) // self.max_words_per_sub)
        target_words_per_sub = total_words // target_sub_count
        
        groups = []
        current_group = []
        current_words = 0
        
        for i, (paragraph, words) in enumerate(zip(paragraphs, paragraph_words)):
            current_group.append(paragraph)
            current_words += words
            
            # 检查是否应该结束当前组
            should_end_group = (
                # 达到目标字数
                current_words >= target_words_per_sub and 
                # 有足够的段落数
                len(current_group) >= self.config.min_paragraphs_per_sub and
                # 不是最后一个段落（避免最后一组太小）
                i < len(paragraphs) - self.config.min_paragraphs_per_sub
            )
            
            if should_end_group:
                groups.append(current_group)
                current_group = []
                current_words = 0
        
        # 添加剩余段落
        if current_group:
            if groups and len(current_group) < self.config.min_paragraphs_per_sub:
                # 如果最后一组太小，合并到前一组
                groups[-1].extend(current_group)
            else:
                groups.append(current_group)
        
        return groups
    
    def _format_sub_chapter(self, title: str, paragraphs: List[str]) -> str:
        """
        格式化子章节内容
        
        Args:
            title: 子章节标题
            paragraphs: 段落列表
            
        Returns:
            格式化的子章节内容
        """
        content_lines = [title, '']  # 标题 + 空行
        
        for paragraph in paragraphs:
            content_lines.append(paragraph)
            content_lines.append('')  # 段落间空行
        
        # 移除最后的多余空行
        while content_lines and not content_lines[-1]:
            content_lines.pop()
        
        return '\n'.join(content_lines)
    
        """
        合并段落内的多行为单行
        
        Args:
            paragraph: 段落文本
            
        Returns:
            合并后的单行段落
        """
        # 按行分割段落
        lines = [line.strip() for line in paragraph.split('\n') if line.strip()]
        
        if not lines:
            return ""
        
        if len(lines) == 1:
            return lines[0]
        
        result = lines[0]
        
        for i in range(1, len(lines)):
            prev_line = result
            current_line = lines[i]
            
            # 检查前一行是否以标点符号结尾
            if prev_line and prev_line[-1] in '.,;:!?"\'':
                # 有标点符号，直接连接不加空格
                result += current_line
            else:
                # 没有标点符号，加一个空格连接
                result += ' ' + current_line
        
        return result
    
    def _copy_to_output(
        self, 
        title: str, 
        content: str, 
        original_file: str, 
        output_dir: str
    ) -> str:
        """
        复制章节到输出目录（不拆分）
        
        Args:
            title: 章节标题
            content: 章节内容
            original_file: 原始文件路径
            output_dir: 输出目录
            
        Returns:
            复制后的文件路径
        """
        filename = os.path.basename(original_file)
        target_file = os.path.join(output_dir, filename)
        
        # 重新构建完整内容
        full_content = f"{title}\n\n{content}"
        
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        return target_file