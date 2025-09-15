#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理服务 - 统一的文本拆分功能
合并章节拆分、子章节拆分、句子拆分
"""

import os
import re
import math
from typing import List, Tuple
from infra import AIClient, FileManager
from infra.config_loader import AppConfig, ChapterPattern
from util import OUTPUT_DIRECTORIES, generate_chapter_filename, generate_sub_filename, clean_title_for_filename, get_basename_without_extension


class TextProcessor:
    """统一的文本处理器"""
    
    def __init__(self, config: AppConfig):
        """
        初始化文本处理器
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.ai_client = AIClient(config.api)
        self.file_manager = FileManager()
    
    def split_book_to_sentences(self, input_file: str, output_dir: str) -> Tuple[List[str], List[str], List[str]]:
        """
        完整的书籍拆分流程：章节 → 子章节 → 句子
        
        Args:
            input_file: 输入书籍文件
            output_dir: 输出目录
            
        Returns:
            (章节文件列表, 子章节文件列表, 句子文件列表)
        """
        # 1. 章节拆分
        chapter_files = self._split_chapters(input_file, output_dir)
        
        # 2. 子章节拆分
        sub_chapter_files = self._split_sub_chapters(chapter_files, output_dir)
        
        # 3. 句子拆分
        sentence_files = self._split_sentences(sub_chapter_files, output_dir)
        
        return chapter_files, sub_chapter_files, sentence_files
    
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
            print(f"⚠️ 未找到章节分隔符，将整个文件作为单个章节")
        
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
            
            print(f"📝 已保存章节: {filename}")
        
        print(f"✅ 章节拆分完成! 共生成 {len(chapter_files)} 个章节文件")
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
            
            chapter_content = content[content_start:content_end].strip()
            if chapter_content:
                chapters.append((title, chapter_content))
        
        return chapters
    
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
        config = self.config.text_processing
        
        for chapter_file in chapter_files:
            content = self.file_manager.read_text_file(chapter_file)
            title, body = self.file_manager.extract_title_and_body(content)
            
            # 按段落分割
            paragraphs = [p.strip() for p in re.split(r'\n\n+', body) if p.strip()]
            
            if not paragraphs:
                continue
            
            # 计算每个子章节的目标词数
            total_words = sum(len(p.split()) for p in paragraphs)
            max_words = config.sub_chapter_max_minutes * config.words_per_minute
            
            if total_words <= max_words:
                # 整个章节作为一个子章节
                sub_chapter_content = f"{title}\n\n{body}"
                chapter_basename = os.path.basename(chapter_file)
                sub_filename = generate_sub_filename(chapter_basename, 1)
                sub_file = os.path.join(sub_chapters_dir, sub_filename)
                self.file_manager.write_text_file(sub_file, sub_chapter_content)
                sub_chapter_files.append(sub_file)
            else:
                # 拆分为多个子章节
                current_words = 0
                current_paragraphs = []
                sub_index = 1
                
                for paragraph in paragraphs:
                    paragraph_words = len(paragraph.split())
                    
                    if current_words + paragraph_words > max_words and current_paragraphs:
                        # 保存当前子章节
                        sub_content = f"{title} (Part {sub_index})\n\n" + '\n\n'.join(current_paragraphs)
                        chapter_basename = os.path.basename(chapter_file)
                        sub_filename = generate_sub_filename(chapter_basename, sub_index)
                        sub_file = os.path.join(sub_chapters_dir, sub_filename)
                        self.file_manager.write_text_file(sub_file, sub_content)
                        sub_chapter_files.append(sub_file)
                        
                        # 重置
                        current_paragraphs = [paragraph]
                        current_words = paragraph_words
                        sub_index += 1
                    else:
                        current_paragraphs.append(paragraph)
                        current_words += paragraph_words
                
                # 保存最后一个子章节
                if current_paragraphs:
                    sub_content = f"{title} (Part {sub_index})\n\n" + '\n\n'.join(current_paragraphs)
                    chapter_basename = os.path.basename(chapter_file)
                    sub_filename = generate_sub_filename(chapter_basename, sub_index)
                    sub_file = os.path.join(sub_chapters_dir, sub_filename)
                    self.file_manager.write_text_file(sub_file, sub_content)
                    sub_chapter_files.append(sub_file)
        
        print(f"✅ 子章节拆分完成! 生成 {len(sub_chapter_files)} 个子章节文件")
        return sub_chapter_files
    
    def _split_sentences(self, sub_chapter_files: List[str], output_dir: str) -> List[str]:
        """
        句子拆分
        
        Args:
            sub_chapter_files: 子章节文件列表
            output_dir: 输出目录
            
        Returns:
            句子文件列表
        """
        print(f"🔄 开始AI句子拆分...")
        
        # 创建句子目录
        sentences_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['sentences'])
        self.file_manager.create_directory(sentences_dir)
        
        sentence_files = []
        
        for sub_chapter_file in sub_chapter_files:
            content = self.file_manager.read_text_file(sub_chapter_file)
            title, body = self.file_manager.extract_title_and_body(content)
            
            # 处理段落句子拆分
            processed_content = self._split_paragraphs_to_sentences(body)
            
            # 构建最终内容
            final_content = f"{title}\n\n{processed_content}"
            
            # 保存句子文件
            filename = os.path.basename(sub_chapter_file)
            sentence_file = os.path.join(sentences_dir, filename)
            self.file_manager.write_text_file(sentence_file, final_content)
            sentence_files.append(sentence_file)
            
            print(f"📝 已处理句子拆分: {filename}")
        
        print(f"✅ 句子拆分完成! 最终生成 {len(sentence_files)} 个句子文件")
        return sentence_files
    
    def _split_paragraphs_to_sentences(self, content: str) -> str:
        """
        将段落拆分为句子
        
        Args:
            content: 段落内容
            
        Returns:
            拆分后的内容
        """
        # 按段落分割
        paragraphs = [p.strip() for p in re.split(r'\n\n', content) if p.strip()]
        
        processed_paragraphs = []
        
        for paragraph in paragraphs:
            # 对段落进行句子拆分
            sentences = self._split_paragraph_sentences(paragraph)
            
            if sentences:
                paragraph_content = '\n'.join(sentences)
                processed_paragraphs.append(paragraph_content)
        
        return '\n\n'.join(processed_paragraphs)
    
    def _split_paragraph_sentences(self, paragraph: str) -> List[str]:
        """
        使用AI拆分段落中的句子
        
        Args:
            paragraph: 段落文本
            
        Returns:
            句子列表
        """
        # 清理文本
        text = re.sub(r'\s+', ' ', paragraph.strip())
        if not text:
            return []
        
        # 简单的基础句子分割
        sentences = re.split(r'[.!?]+\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 使用AI智能拆分长句
        result = []
        config = self.config.text_processing
        
        for i, sentence in enumerate(sentences):
            if len(sentence) < config.ai_split_threshold:
                result.append(sentence)
            else:
                # 获取上下文
                context_sentences = self._get_context_sentences(sentences, i, config.context_window)
                split_result = self._ai_split_sentence(sentence, context_sentences, paragraph)
                result.extend(split_result)
        
        return result
    
    def _get_context_sentences(self, sentences: List[str], current_index: int, window_size: int) -> List[str]:
        """获取当前句子的上下文"""
        start = max(0, current_index - window_size)
        end = min(len(sentences), current_index + window_size + 1)
        return sentences[start:end]
    
    def _ai_split_sentence(self, sentence: str, context_sentences: List[str], paragraph_context: str) -> List[str]:
        """
        使用AI拆分单个句子
        
        Args:
            sentence: 要拆分的句子
            context_sentences: 上下文句子
            paragraph_context: 段落上下文
            
        Returns:
            拆分后的句子列表
        """
        # 构建上下文信息
        context_info = ""
        if context_sentences:
            context_info = f"上下文句子：\n{chr(10).join(context_sentences)}\n\n"
        
        if paragraph_context:
            context_info += f"段落背景：{paragraph_context[:200]}...\n\n"
        
        prompt = f"""请将以下英文长句拆分为多个语义完整的子句。拆分时需要考虑：
1. 保持每个子句的语义完整性
2. 考虑语法结构和逻辑关系
3. 子句长度适中（建议20-60字符）
4. 保持原意不变

{context_info}需要拆分的句子：
{sentence}

请直接返回拆分后的子句，每行一个，不要添加序号或其他格式："""

        try:
            response = self.ai_client.chat_completion(prompt)
            if not response:
                raise RuntimeError("AI返回空结果")
            
            # 解析拆分结果
            split_sentences = []
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.startswith('*') and not line.startswith('-'):
                    # 清理可能的序号
                    line = re.sub(r'^\d+\.\s*', '', line)
                    line = re.sub(r'^[•·]\s*', '', line)
                    if line:
                        split_sentences.append(line)
            
            if not split_sentences:
                raise RuntimeError("AI拆分返回空结果")
            
            return split_sentences
            
        except Exception as e:
            print(f"❌ AI拆分失败: {e}")
            raise