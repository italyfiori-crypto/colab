#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节处理服务 - 负责章节和子章节拆分
拆分到子章节粒度，不包含句子拆分
"""

import os
import re
import math
from typing import List, Tuple
from infra import FileManager
from infra.config_loader import AppConfig, ChapterPattern
from util import OUTPUT_DIRECTORIES, generate_chapter_filename, generate_sub_filename, get_basename_without_extension


class ChapterProcessor:
    """章节处理器 - 负责章节拆分到子章节粒度"""
    
    def __init__(self, config: AppConfig):
        """
        初始化章节处理器
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.file_manager = FileManager()
    
    def split_book_to_sub_chapters(self, input_file: str, output_dir: str) -> Tuple[List[str], List[str]]:
        """
        完整的章节拆分流程：书籍 → 章节 → 子章节
        
        Args:
            input_file: 输入书籍文件
            output_dir: 输出目录
            
        Returns:
            (章节文件列表, 子章节文件列表)
        """
        # 1. 章节拆分
        chapter_files = self._split_chapters(input_file, output_dir)
        
        # 2. 子章节拆分
        sub_chapter_files = self._split_sub_chapters(chapter_files, output_dir)
        
        return chapter_files, sub_chapter_files
    
    def _split_chapters(self, input_file: str, output_dir: str) -> List[str]:
        """
        章节拆分
        
        Args:
            input_file: 输入文件
            output_dir: 输出目录
            
        Returns:
            章节文件列表
        """
        print(f"🔄 开始章节拆分...")
        
        # 读取输入文件
        content = self.file_manager.read_text_file(input_file)
        
        # 创建章节目录
        chapters_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['chapters'])
        self.file_manager.create_directory(chapters_dir)
        
        # 尝试各种章节模式
        for pattern in self.config.chapter_patterns:
            chapters = self._extract_chapters_with_pattern(content, pattern)
            if chapters:
                print(f"✅ 使用模式 '{pattern.name}' 找到 {len(chapters)} 个章节")
                break
        else:
            # 如果没有找到章节，将整个文件作为一个章节
            book_name = self.file_manager.get_basename_without_extension(input_file)
            chapters = [(f"Chapter 1: {book_name}", content)]
            print(f"⚠️  未找到章节分隔符，将整个文件作为单个章节")
        
        # 保存章节文件
        chapter_files = []
        for i, (title, chapter_content) in enumerate(chapters, 1):
            # 使用新的命名格式：001_Down_the_Rabbit-Hole.txt
            filename = generate_chapter_filename(i, title)
            chapter_file = os.path.join(chapters_dir, filename)
            
            # 构建章节内容
            full_content = f"{title}\n\n{chapter_content.strip()}"
            self.file_manager.write_text_file(chapter_file, full_content)
            chapter_files.append(chapter_file)
            
            print(f"📝 已生成章节文件: {chapter_file}")
        
        print(f"✅ 成功拆分 {len(chapter_files)} 个章节到目录: {chapters_dir}")
        return chapter_files
    
    def _extract_chapters_with_pattern(self, content: str, pattern: ChapterPattern) -> List[Tuple[str, str]]:
        """
        使用指定模式提取章节
        
        Args:
            content: 文本内容
            pattern: 章节模式
            
        Returns:
            章节列表 [(标题, 内容), ...]
        """
        flags = re.MULTILINE | re.DOTALL
        if self.config.ignore_case:
            flags |= re.IGNORECASE
        
        matches = list(re.finditer(pattern.multiline_regex, content, flags))
        if not matches:
            return []
        
        chapters = []
        for i, match in enumerate(matches):
            # 提取标题
            match_lines = match.group(0).split('\n')
            if pattern.title_line_index < len(match_lines):
                title = match_lines[pattern.title_line_index].strip()
            else:
                title = f"Chapter {i + 1}"
            
            # 确定内容范围
            content_start = match.end()
            if i + 1 < len(matches):
                content_end = matches[i + 1].start()
            else:
                content_end = len(content)
            
            # 提取原始内容
            raw_content = content[content_start:content_end].strip()
            
            # 处理段落合并
            content_lines = raw_content.split('\n')
            
            # 清理内容（去除开头和结尾的空行）
            while content_lines and not content_lines[0].strip():
                content_lines.pop(0)
            while content_lines and not content_lines[-1].strip():
                content_lines.pop()
            
            # 合并段落（将多行合并为单行）
            processed_lines = self._merge_paragraph_lines(content_lines)
            chapter_content = ''.join(processed_lines).strip()
            
            if chapter_content:
                chapters.append((title, chapter_content))
        
        return chapters
    
    def _merge_paragraph_lines(self, lines: List[str]) -> List[str]:
        """
        合并段落内的多行为单行
        
        Args:
            lines: 原始行列表
            
        Returns:
            处理后的行列表
        """
        if not lines:
            return []
        
        result = []
        current_paragraph = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                # 空行，表示段落结束
                if current_paragraph:
                    # 合并当前段落
                    merged_line = self._merge_lines(current_paragraph)
                    result.append(merged_line + '\n')
                    current_paragraph = []
                result.append('\n')  # 保留段落间的空行
            else:
                # 非空行，加入当前段落
                current_paragraph.append(line_stripped)
        
        # 处理最后一个段落
        if current_paragraph:
            merged_line = self._merge_lines(current_paragraph)
            result.append(merged_line + '\n')
        
        return result
    
    def _merge_lines(self, lines: List[str]) -> str:
        """
        将多行文本合并为一行
        
        Args:
            lines: 行列表
            
        Returns:
            合并后的单行文本
        """
        if not lines:
            return ""
        
        if len(lines) == 1:
            return lines[0]
        
        result = lines[0]
        
        for i in range(1, len(lines)):
            prev_line = result
            current_line = lines[i].strip()
            
            # 检查前一行是否以标点符号结尾
            if prev_line and prev_line[-1] in '.,;:!?"\'':
                # 有标点符号，直接连接不加空格
                result += current_line
            else:
                # 没有标点符号，加一个空格连接
                result += ' ' + current_line
        
        return result
    
    def _split_sub_chapters(self, chapter_files: List[str], output_dir: str) -> List[str]:
        """
        子章节拆分
        
        Args:
            chapter_files: 章节文件列表
            output_dir: 输出目录
            
        Returns:
            子章节文件列表
        """
        print(f"🔄 开始子章节拆分...")
        
        # 创建子章节目录
        sub_chapters_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['sub_chapters'])
        self.file_manager.create_directory(sub_chapters_dir)
        
        sub_chapter_files = []
        text_config = self.config.text_processing
        max_words_per_sub = text_config.sub_chapter_max_minutes * text_config.words_per_minute
        
        for chapter_file in chapter_files:
            content = self.file_manager.read_text_file(chapter_file)
            title, body = self.file_manager.extract_title_and_body(content)
            
            # 判断是否需要拆分
            if self._should_split_chapter(body, max_words_per_sub):
                # 拆分为子章节
                sub_files = self._split_into_sub_chapters(
                    title, body, chapter_file, sub_chapters_dir, text_config, max_words_per_sub
                )
                sub_chapter_files.extend(sub_files)
                print(f"📚 章节 '{title}' 拆分为 {len(sub_files)} 个子章节")
            else:
                # 不需要拆分，直接复制到子章节目录
                sub_chapter_content = f"{title}\n\n{body}"
                chapter_basename = os.path.basename(chapter_file)
                sub_filename = generate_sub_filename(chapter_basename, 1)
                sub_file = os.path.join(sub_chapters_dir, sub_filename)
                self.file_manager.write_text_file(sub_file, sub_chapter_content)
                sub_chapter_files.append(sub_file)
                print(f"📄 章节 '{title}' 无需拆分，直接复制")
        
        print(f"\n📁 所有文件已处理完成，输出到: {sub_chapters_dir}")
        print(f"✅ 子章节拆分完成! 生成 {len(sub_chapter_files)} 个子章节文件")
        return sub_chapter_files
    
    def _should_split_chapter(self, content: str, max_words_per_sub: int) -> bool:
        """
        判断章节是否需要拆分
        
        Args:
            content: 章节内容
            max_words_per_sub: 每个子章节最大词数
            
        Returns:
            是否需要拆分
        """
        word_count = self._count_words(content)
        return word_count > max_words_per_sub
    
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
        output_dir: str,
        text_config,
        max_words_per_sub: int
    ) -> List[str]:
        """
        将章节拆分为多个子章节
        
        Args:
            title: 章节标题
            content: 章节内容
            original_file: 原始文件路径
            output_dir: 输出目录
            text_config: 文本处理配置
            max_words_per_sub: 每个子章节最大词数
            
        Returns:
            生成的子章节文件路径列表
        """
        # 按段落分割内容
        paragraphs = self._split_into_paragraphs(content)
        
        # 从配置JSON获取最小段落数，如果没有配置则使用默认值2
        min_paragraphs_per_sub = 2
        if len(paragraphs) < min_paragraphs_per_sub * 2:
            # 段落太少，不拆分
            return [self._copy_to_output(title, content, original_file, output_dir)]
        
        # 计算每个段落的字数
        paragraph_words = [self._count_words(p) for p in paragraphs]
        
        # 将段落分组为子章节
        sub_groups = self._group_paragraphs(paragraphs, paragraph_words, min_paragraphs_per_sub, max_words_per_sub)
        
        # 生成子章节文件
        sub_files = []
        base_filename = get_basename_without_extension(original_file)
        
        for i, group in enumerate(sub_groups, 1):
            sub_title = f"{title}({i})"
            sub_content = self._format_sub_chapter(sub_title, group)
            sub_filename = f"{base_filename}({i}).txt"
            sub_file_path = os.path.join(output_dir, sub_filename)
            
            self.file_manager.write_text_file(sub_file_path, sub_content)
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
        paragraph_words: List[int],
        min_paragraphs_per_sub: int,
        max_words_per_sub: int
    ) -> List[List[str]]:
        """
        将段落分组为子章节
        
        Args:
            paragraphs: 段落列表
            paragraph_words: 每个段落的字数列表
            min_paragraphs_per_sub: 每个子章节最小段落数
            max_words_per_sub: 每个子章节最大词数
            
        Returns:
            段落分组列表
        """
        total_words = sum(paragraph_words)
        target_sub_count = max(2, (total_words + max_words_per_sub - 1) // max_words_per_sub)
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
                len(current_group) >= min_paragraphs_per_sub and
                # 不是最后一个段落（避免最后一组太小）
                i < len(paragraphs) - min_paragraphs_per_sub
            )
            
            if should_end_group:
                groups.append(current_group)
                current_group = []
                current_words = 0
        
        # 添加剩余段落
        if current_group:
            if groups and len(current_group) < min_paragraphs_per_sub:
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
        chapter_basename = os.path.basename(original_file)
        sub_filename = generate_sub_filename(chapter_basename, 1)
        target_file = os.path.join(output_dir, sub_filename)
        
        # 重新构建完整内容
        full_content = f"{title}\n\n{content}"
        
        self.file_manager.write_text_file(target_file, full_content)
        return target_file