#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句子拆分模块
将子章节的段落拆分为句子每个句子占一行保留段落间隔
使用引号优先的语义感知分割方法
"""

import os
import re
import nltk
import pysbd
from typing import List
from infra.config_loader import AppConfig

# 调试开关
DEBUG_SENTENCE_PROCESSING = False

def debug_print(stage, content):
    """调试输出函数"""
    if DEBUG_SENTENCE_PROCESSING:
        if isinstance(content, list):
            print(f"[DEBUG] {stage}: {len(content)} items")
            for i, item in enumerate(content):
                print(f"  [{i}]: {repr(item)}")
        else:
            print(f"[DEBUG] {stage}: {repr(content)}")
        print()  # 空行分隔

# 配置：括号类符号（整体保留）
PAIR_SYMBOLS_PARENS = [
    ("(", ")"),
    ("[", "]"),
    ("{", "}"),
    ("（", "）"),
    ("【", "】"),
    ("《", "》"),
]

# 配置：引号类符号（允许内部继续拆分）
PAIR_SYMBOLS_QUOTES = [
    ("‘", "’"),
    ("“", "”"),
    ('"', '"'),  # 恢复标准双引号用于调试
]

# 配置：句中分隔符（可以再扩展）
SPLIT_PUNCT = [",", "，", ":", "：", ";", "；", "!", "?", "."]

# 配置：英语常见缩写词（不应在句号处拆分）
ENGLISH_ABBREVIATIONS = ["Dr", "Mrs", "Ms", "Mr", "Prof", "St", "Ave", "etc", "vs", "Jr", "Sr", "Co", "Inc", "Ltd", "Corp"]

# 配置：英语缩写词模式（单引号在这些情况下不应作为引号分隔符）
CONTRACTION_PATTERNS = [
    "'t",   # don't, can't, won't, isn't, aren't, haven't, hasn't
    "'m",    # I'm, we'm  
    "'am",
    "'re",   # you're, we're, they're
    "'ve",   # I've, you've, we've, they've
    "'d",    # I'd, you'd, he'd, she'd, we'd, they'd
    "'ll",   # I'll, you'll, he'll, she'll, we'll, they'll
    "'s",    # possessive: John's, Mary's, 或 is/has: he's, she's
]

# 句末分隔符（不应在此处合并子句）
SENTENCE_TERMINATORS = [".", "?", ";"]

# 可合并的分隔符 + 成对符号的结束部分
PREV_MERGEABLE_SEPARATORS = [".", "!", "?", ";"]
NEXT_SYMBOL_ENDINGS = ["”", "’", ")", "]", "}", "）", "】", "》"]

PREV_SYMBOL_ENDINGS = ["”", "’", ")", "]", "}", "）", "】", "》"]
NEXT_MERGEABLE_SEPARATORS = [".", "!", "?", ";",  ",", "，"]


# 长度控制常量 - 针对语音合成优化
MAX_SENTENCE_LENGTH = 80      # 目标最大长度（适合语音合成）
MIN_MERGE_LENGTH = 30      # 最小合并长度
MAX_MERGE_LENGTH = 100      # 最大合并长度


class SentenceProcessor:
    """句子拆分器"""
    
    def __init__(self, config: AppConfig):
        """
        初始化句子拆分器
        """
        self._ensure_nltk_data()
        self._init_pysbd()
    
    def _ensure_nltk_data(self):
        """
        确保NLTK数据包可用
        """
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            print("下载NLTK punkt数据包...")
            nltk.download('punkt')
    
    def _init_pysbd(self):
        """
        初始化pySBD分段器
        """
        self.segmenter = pysbd.Segmenter(language="en", clean=False)
        print("✅ pySBD分段器初始化完成")
    
    def split_sub_chapters_to_sentences(self, input_files: List[str], output_dir: str) -> List[str]:
        """
        拆分文件列表为句子级文件
        
        Args:
            input_files: 输入文件路径列表
            output_dir: 输出目录
            
        Returns:
            生成的句子文件路径列表
        """
        # 创建输出目录
        sentences_dir = os.path.join(output_dir, "sentences")
        os.makedirs(sentences_dir, exist_ok=True)
        
        output_files = []
        
        for input_file in input_files:
            try:
                # 生成输出文件路径
                filename = os.path.basename(input_file)
                output_file = os.path.join(sentences_dir, filename)
                
                # 处理单个文件
                self._process_file(input_file, output_file)
                output_files.append(output_file)
                
                print(f"📝 已处理句子拆分: {filename}")
            except Exception as e:
                print(f"❌ 拆分失败: {e}")
                continue
        
        print(f"\n📁 句子拆分完成，输出到: {sentences_dir}")
        return output_files
    
    def _process_file(self, input_file: str, output_file: str):
        """
        处理单个文件的句子拆分
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
        """
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标题和正文
        title, body = self._extract_title_and_body(content)
        
        # 处理段落句子拆分，同时保存中间结果
        processed_content, pysbd_content = self._split_paragraphs_to_sentences(body)
        
        # 构建最终内容
        final_content = f"{title}\n\n{processed_content}"
        
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_content)        
        
        # pySBD原始结果
        # base_name = os.path.splitext(output_file)[0]
        # pysbd_file = f"{base_name}_pysbd.txt"
        # pysbd_final_content = f"{title}\n\n{pysbd_content}"
        # with open(pysbd_file, 'w', encoding='utf-8') as f:
        #     f.write(pysbd_final_content)
    
    def _extract_title_and_body(self, content: str) -> tuple[str, str]:
        """
        提取标题和正文内容
        
        Args:
            content: 文件内容
            
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

    def _split_paragraphs_to_sentences(self, content: str) -> tuple[str, str]:
        """
        将内容按段落拆分再将每个段落拆分为句子同时返回中间处理结果
        
        Args:
            content: 正文内容
            
        Returns:
            (最终处理内容, pySBD原始内容)
        """
        # 按段落分割（双换行分割）
        paragraphs = re.split(r'\n\n', content)
        
        # 过滤空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        final_paragraphs = []
        pysbd_paragraphs = []
        
        for paragraph in paragraphs:
            # 对段落进行句子拆分
            final_sentences, pysbd_sentences = self._split_sentences(paragraph)
            
            # 将句子列表转换为字符串（每句一行）
            if final_sentences:
                final_paragraphs.append('\n'.join(final_sentences))
            if pysbd_sentences:
                pysbd_paragraphs.append('\n'.join(pysbd_sentences))
        
        # 段落间用空行分隔
        return (
            '\n\n'.join(final_paragraphs),
            '\n\n'.join(pysbd_paragraphs),
        )

    def _split_sentences(self, text: str) -> tuple[List[str], List[str]]:
        """
        将文本拆分为句子返回
        
        Args:
            text: 输入文本
            
        Returns:
            (最终句子列表, pySBD原始句子列表)
        """
        # 清理文本（移除多余空白）
        text = re.sub(r'\s+', ' ', text.strip())
        
        if not text:
            return [], []
        
        # 第一阶段：使用pySBD进行基础句子分割
        if len(text) <= MAX_SENTENCE_LENGTH:
            return [text], [text] 

        pysbd_sentences = self._split_with_pysbd(text)
        pysbd_sentences = [s.strip() for s in pysbd_sentences if s.strip()]
        
        # 第二阶段：长句拆分逻辑
        final_sentences = self._split_long_sentences(pysbd_sentences)
        final_sentences = [s.strip() for s in final_sentences if s.strip()]
        
        return final_sentences, pysbd_sentences
    
    def _split_with_nltk(self, text: str) -> List[str]:
        """
        使用NLTK进行句子分割
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        return nltk.sent_tokenize(text)

    def _split_with_pysbd(self, text: str) -> List[str]:
        """
        使用pySBD进行句子分割
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        debug_print("pySBD输入", text)
        result = self.segmenter.segment(text)
        result = [sent.strip() for sent in result if sent.strip()]
        debug_print("pySBD输出", result)
        return result
    
    
    def _split_long_sentences(self, sentences: List[str]) -> List[str]:
        """
        新的长句拆分策略: 成对符号保护 + 分隔符拆分 + 智能合并
        
        Args:
            sentences: 原始句子列表
            
        Returns:
            处理后的句子列表
        """
        result = []
        
        for sentence in sentences:
            if len(sentence) <= MAX_SENTENCE_LENGTH:
                result.append(sentence)
                continue
            
            # 对长句进行拆分-合并处理
            split_result = self.split_into_clauses(sentence)
            result.extend(split_result)
        
        return result
    
    def _is_abbreviation(self, position: int, text: str) -> bool:
        """检测指定位置的句号前是否为英语缩写词"""
        if position == 0:
            return False
        
        # 向前查找单词边界
        word_start = position - 1
        while word_start > 0 and text[word_start - 1].isalpha():
            word_start -= 1
        
        if word_start == position:
            return False
        
        # 提取可能的缩写词
        word = text[word_start:position]
        return word in ENGLISH_ABBREVIATIONS
    
    def _get_quote_type(self, ch: str) -> tuple[str, str] | None:
        """获取引号字符的开始和结束符号，如果不是引号返回None"""
        for open_quote, close_quote in PAIR_SYMBOLS_QUOTES:
            if ch == open_quote or ch == close_quote:
                return open_quote, close_quote
        return None
    
    def _get_paren_type(self, ch: str) -> tuple[str, str] | None:
        """获取括号字符的开始和结束符号，如果不是括号返回None"""
        for open_paren, close_paren in PAIR_SYMBOLS_PARENS:
            if ch == open_paren or ch == close_paren:
                return open_paren, close_paren
        return None
    
    def _split_by_quotes_and_parens(self, text: str) -> List[tuple[str, int]]:
        """
        第1步：按引号和括号拆分文本，为每个片段分配序号
        
        Args:
            text: 输入文本
            
        Returns:
            List of (文本片段, 源序号) 元组
        """
        segments = []
        buf = []
        current_segment_index = 0
        
        # 统一的符号状态跟踪
        quote_stack = []  # 引号栈，记录当前打开的引号类型
        paren_count = 0   # 括号嵌套层级
        
        def add_segment_if_not_empty():
            """添加当前缓冲区内容为新片段"""
            nonlocal current_segment_index
            if buf:
                clause = ''.join(buf).strip()
                if clause:
                    segments.append((clause, current_segment_index))
                    current_segment_index += 1
                buf.clear()
        
        i = 0
        while i < len(text):
            ch = text[i]
            
            # 检查是否为引号字符
            quote_info = self._get_quote_type(ch)
            if quote_info:
                open_quote, close_quote = quote_info
                
                # 检查是否为缩写词中的撇号，如果是则不作为引号处理
                if ch in ["'", "'"] and self._is_contraction_apostrophe(i, text):
                    buf.append(ch)
                else:
                    # 只在没有括号嵌套时处理引号
                    if paren_count == 0:
                        if ch == open_quote:
                            # 检查是否为开始引号
                            if not quote_stack or quote_stack[-1] != (open_quote, close_quote):
                                # 开始新的引号区域 - 先保存当前缓冲区
                                add_segment_if_not_empty()
                                buf.append(ch)
                                quote_stack.append((open_quote, close_quote))
                            else:
                                buf.append(ch)
                        elif ch == close_quote:
                            # 检查是否为结束引号
                            if quote_stack and quote_stack[-1] == (open_quote, close_quote):
                                buf.append(ch)
                                # 结束当前引号区域
                                quote_stack.pop()
                                add_segment_if_not_empty()
                            else:
                                buf.append(ch)
                        else:
                            buf.append(ch)
                    else:
                        buf.append(ch)
            
            # 检查是否为括号字符
            elif self._get_paren_type(ch):
                open_paren, close_paren = self._get_paren_type(ch)
                
                # 只在没有引号嵌套时计算括号层级
                if not quote_stack:
                    if ch == open_paren:
                        # 开始新的括号区域 - 先保存当前缓冲区
                        add_segment_if_not_empty()
                        buf.append(ch)
                        paren_count += 1
                    elif ch == close_paren and paren_count > 0:
                        buf.append(ch)
                        paren_count -= 1
                        # 如果括号完全闭合，结束当前片段
                        if paren_count == 0:
                            add_segment_if_not_empty()
                    else:
                        buf.append(ch)
                else:
                    buf.append(ch)
            
            # 普通字符
            else:
                buf.append(ch)
            
            i += 1
        
        # 收尾处理
        add_segment_if_not_empty()
        
        debug_print("第1步-引号括号拆分", [(seg[0], seg[1]) for seg in segments])
        return segments

    def _is_contraction_apostrophe(self, position: int, text: str) -> bool:
        """检测指定位置的单引号是否为英语缩写词中的撇号"""
        if position == 0 or position >= len(text) - 1:
            return False
        
        # 检查是否符合缩写词模式
        for pattern in CONTRACTION_PATTERNS:
            pattern_start = position
            pattern_end = position + len(pattern)
            
            if pattern_end <= len(text):
                if text[pattern_start:pattern_end] == pattern:
                    # 检查前面是否有字母（确保是单词的一部分）
                    if position > 0 and text[position-1].isalpha():
                        # 检查后面是否是单词边界（空格、标点、文本结尾）
                        if (pattern_end >= len(text) or 
                            text[pattern_end].isspace() or 
                            text[pattern_end] in SPLIT_PUNCT or
                            text[pattern_end] in '"",，"'):
                            return True
        
        return False
    
    def _split_by_punctuation(self, segments: List[tuple[str, int]]) -> List[tuple[str, int]]:
        """
        第2步：按分隔符拆分长度超过阈值的片段
        
        Args:
            segments: 第1步的输出 - (文本, 源序号) 元组列表
            
        Returns:
            进一步拆分的 (文本, 源序号) 元组列表
        """
        result = []
        
        for text, source_idx in segments:
            if len(text) <= MAX_SENTENCE_LENGTH:
                # 短片段直接保留
                result.append((text, source_idx))
            else:
                # 长片段按分隔符拆分
                sub_parts = self._split_text_by_punct(text)
                # 保持相同的源序号
                result.extend([(part, source_idx) for part in sub_parts])
        
        debug_print("第2步-分隔符拆分", [(seg[0], seg[1]) for seg in result])
        return result
    
    def _split_text_by_punct(self, text: str) -> List[str]:
        """
        按分隔符拆分文本（不处理引号括号逻辑）
        
        Args:
            text: 输入文本
            
        Returns:
            拆分后的文本片段列表
        """
        clauses = []
        buf = []
        
        i = 0
        while i < len(text):
            ch = text[i]
            buf.append(ch)
            
            # 处理分隔符
            if ch in SPLIT_PUNCT:
                # 特殊处理句号：检查是否为缩写词
                if ch == '.' and self._is_abbreviation(i, text):
                    pass  # 不拆分缩写词
                else:
                    clause = ''.join(buf).strip()
                    if clause and len(clause) > 1:  # 避免单个分隔符成为独立子句
                        clauses.append(clause)
                        buf = []
            
            i += 1
        
        # 收尾处理
        if buf:
            clause = ''.join(buf).strip()
            if clause:
                clauses.append(clause)
        
        # 清理并过滤空子句
        clauses = [clause.strip() for clause in clauses if clause.strip()]
        return clauses
    
    def _has_adjacent_same_source(self, segments: List[tuple[str, int]], current_index: int, source_idx: int) -> bool:
        """
        检查当前位置是否有相邻的相同源序号片段
        
        Args:
            segments: 完整的片段列表
            current_index: 当前片段在列表中的位置
            source_idx: 要检查的源序号
            
        Returns:
            是否存在相邻的相同源序号片段
        """
        # 检查下一个片段是否为相同序号
        if (current_index + 1 < len(segments) and 
            segments[current_index + 1][1] == source_idx):
            debug_print("邻近检查", f"序号{source_idx}在位置{current_index}有后续相同序号片段")
            return True
        
        # 检查前一个片段是否为相同序号
        # 注意：这里不需要检查前一个，因为如果前一个是相同序号，在处理前一个片段时就会合并
        # 这里主要关心是否有后续的相同序号片段需要等待
        
        return False
    
    def _merge_short_segments(self, segments: List[tuple[str, int]]) -> List[str]:
        """
        第3步：智能合并短片段，优先与相同源序号的片段合并
        
        Args:
            segments: 第2步的输出 - (文本, 源序号) 元组列表
            
        Returns:
            最终的子句列表
        """
        merged = []
        merged_indices = []  # 追踪已合并文本的源序号
        
        for i, (text, source_idx) in enumerate(segments):
            # 优先级1：与相同源序号的前一片段合并
            if (merged and merged_indices and merged_indices[-1] == source_idx and 
                self._can_merge_segments(merged[-1], text)):
                merged[-1] += " " + text
                debug_print("相同序号合并", f"序号{source_idx}: {merged[-1]}")
            
            # 优先级2：与不同序号的前一片段合并
            # 新增条件：只有当前片段没有相邻的相同序号片段时才允许
            elif (merged and self._can_merge_segments(merged[-1], text) and
                  not self._has_adjacent_same_source(segments, i, source_idx)):
                merged[-1] += " " + text
                merged_indices[-1] = source_idx  # 更新序号为新片段的序号
                debug_print("跨序号合并", f"序号{merged_indices[-1]}: {merged[-1]}")
            
            else:
                # 无法合并，添加为新片段
                merged.append(text)
                merged_indices.append(source_idx)
                debug_print("独立片段", f"序号{source_idx}: {text}")
        
        debug_print("第3步-智能合并", merged)
        return merged
    
    def _can_merge_segments(self, prev_text: str, current_text: str) -> bool:
        """
        检查两个片段是否可以合并
        
        Args:
            prev_text: 前一个片段文本
            current_text: 当前片段文本
            
        Returns:
            是否可以合并
        """
        # 合并条件：
        # 1. 前一个片段或当前片段过短
        # 2. 合并后不超过最大长度
        # 3. 前一个片段不以句末分隔符结尾
        return (
            (len(prev_text) < MIN_MERGE_LENGTH or len(current_text) < MIN_MERGE_LENGTH) and 
            len(prev_text) + len(current_text) < MAX_MERGE_LENGTH and
            not self._ends_with_sentence_terminator(prev_text)
        )
    
    def _parse_text_into_clauses(self, text: str):
        """
        将文本拆分成子句的核心逻辑:
        使用统一的符号处理和状态跟踪
        """
        clauses = []
        buf = []
        
        # 统一的符号状态跟踪
        quote_stack = []  # 引号栈，记录当前打开的引号类型
        paren_count = 0   # 括号嵌套层级
        
        i = 0
        while i < len(text):
            ch = text[i]
            
            # 检查是否为引号字符
            quote_info = self._get_quote_type(ch)
            if quote_info:
                open_quote, close_quote = quote_info
                buf.append(ch)
                
                # 只在没有括号嵌套时处理引号
                if paren_count == 0:
                    if ch == open_quote:
                        # 检查是否为开始引号
                        if not quote_stack or quote_stack[-1] != (open_quote, close_quote):
                            # 开始新的引号区域
                            if buf[:-1]:  # 如果缓冲区有内容（除了刚加入的引号）
                                clause = ''.join(buf[:-1]).strip()
                                if clause:
                                    clauses.append(clause)
                                buf = [ch]  # 重新开始，只保留引号
                            quote_stack.append((open_quote, close_quote))
                    elif ch == close_quote:
                        # 检查是否为结束引号
                        if quote_stack and quote_stack[-1] == (open_quote, close_quote):
                            # 结束当前引号区域
                            quote_stack.pop()
                            clause = ''.join(buf).strip()
                            if clause:
                                clauses.append(clause)
                            buf = []
            
            # 检查是否为括号字符
            elif self._get_paren_type(ch):
                open_paren, close_paren = self._get_paren_type(ch)
                buf.append(ch)
                
                # 只在没有引号嵌套时计算括号层级
                if not quote_stack:
                    if ch == open_paren:
                        paren_count += 1
                    elif ch == close_paren and paren_count > 0:
                        paren_count -= 1
            
            # 处理分隔符
            elif ch in SPLIT_PUNCT:
                buf.append(ch)
                
                # 只在没有引号或括号嵌套时进行拆分
                if not quote_stack and paren_count == 0:
                    # 特殊处理句号：检查是否为缩写词
                    if ch == '.' and self._is_abbreviation(i, text):
                        pass  # 不拆分缩写词
                    else:
                        clause = ''.join(buf).strip()
                        if clause and len(clause) > 1:  # 避免单个分隔符成为独立子句
                            clauses.append(clause)
                            buf = []
            
            # 普通字符
            else:
                buf.append(ch)
            
            i += 1
        
        # 收尾处理
        if buf:
            clause = ''.join(buf).strip()
            if clause:
                clauses.append(clause)
        
        # 清理并过滤空子句
        clauses = [clause.strip() for clause in clauses if clause.strip()]
        debug_print("_parse_text_into_clauses输出", clauses)
        
        return clauses

    def split_into_clauses(self, text: str):
        """
        三步优化的子句拆分:
        1. 按括号和引号拆分，记录序号
        2. 按分隔符拆分长片段，保持序号
        3. 智能合并，优先相同序号片段
        """
        debug_print("split_into_clauses输入", text)
        
        # 第1步：按引号和括号拆分，分配序号
        segments = self._split_by_quotes_and_parens(text)
        
        # 第2步：按分隔符拆分长片段  
        segments = self._split_by_punctuation(segments)
        
        # 第3步：智能合并
        result = self._merge_short_segments(segments)
        
        # 后置处理: 合并被分离的标点符号
        result = self._merge_split_punctuation(result)
        debug_print("split_into_clauses最终输出", result)
        
        return result

    def _ends_with_sentence_terminator(self, text: str) -> bool:
        """
        检查文本是否以句末分隔符结尾(去除空格后)
        
        Args:
            text: 输入文本
            
        Returns:
            True if 文本以句末分隔符结尾
        """
        if not text:
            return False
            
        # 去除尾部空格后检查最后一个字符
        trimmed = text.rstrip()
        if not trimmed:
            return False
            
        return trimmed[-1] in SENTENCE_TERMINATORS

    def _merge_split_punctuation(self, clauses: List[str]) -> List[str]:
        """
        后置处理: 合并被分离的分隔符和成对符号
        两种情况:
        1. 分隔符(非冒号) + 成对符号结束部分
        2. 成对符号结束部分 + 分隔符(非冒号)
        
        Args:
            clauses: 原始子句列表
            
        Returns:
            合并后的子句列表
        """
        if not clauses:
            return clauses
            
        merged = []
        
        for clause in clauses:
            if merged and self._should_merge_with_previous(merged[-1], clause):
                # 合并符号
                clause = clause.lstrip()
                merged[-1] += clause[0]
                if len(clause) > 1:
                    merged.append(clause[1:].lstrip())
            else:
                merged.append(clause)
        
        return merged
    
    def _should_merge_with_previous(self, prev_clause: str, current_clause: str) -> bool:
        """
        检查当前子句是否应该与前一个子句合并
        两种情况:
        1. 分隔符(非冒号) + 成对符号结束部分
        2. 成对符号结束部分 + 分隔符(非冒号)
        
        Args:
            prev_clause: 前一个子句
            current_clause: 当前子句
            
        Returns:
            True if 应该合并
        """
        if not prev_clause or not current_clause:
            return False
            
        # 检查前一句的结尾字符
        prev_trimmed = prev_clause.rstrip()
        if not prev_trimmed:
            return False
        prev_end_char = prev_trimmed[-1]
        
        # 检查当前句的开头字符
        current_trimmed = current_clause.lstrip()
        if not current_trimmed:
            return False
        current_start_char = current_trimmed[0]
        
        # 情况1: 分隔符(非冒号) + 成对符号结束部分
        case1 = (prev_end_char in PREV_MERGEABLE_SEPARATORS and 
                current_start_char in NEXT_SYMBOL_ENDINGS)
        
        # 情况2: 成对符号结束部分 + 分隔符(非冒号)
        case2 = (prev_end_char in PREV_SYMBOL_ENDINGS and 
                current_start_char in NEXT_MERGEABLE_SEPARATORS)
        
        return case1 or case2

    def _is_quoted_or_parenthesized(self, text: str) -> bool:
        """
        检查文本是否被括号或引号包围
        """
        if len(text) < 2:
            return False
        
        # 检查是否被括号包围
        for open_sym, close_sym in PAIR_SYMBOLS_PARENS:
            if text.startswith(open_sym) and text.endswith(close_sym):
                return True
        
        # 检查是否被引号包围
        for open_sym, close_sym in PAIR_SYMBOLS_QUOTES:
            if text.startswith(open_sym) and text.endswith(close_sym):
                return True
        
        return False

    def _extract_inner_content_and_wrapper(self, text: str) -> tuple[str, tuple[str, str]]:
        """
        从被包围的文本中提取内部内容和包围符号
        
        Returns:
            (内部内容, (开始符号, 结束符号))
        """
        if len(text) < 2:
            return text, ("", "")
        
        # 检查括号
        for open_sym, close_sym in PAIR_SYMBOLS_PARENS:
            if text.startswith(open_sym) and text.endswith(close_sym):
                inner = text[len(open_sym):-len(close_sym)]
                return inner, (open_sym, close_sym)
        
        # 检查引号
        for open_sym, close_sym in PAIR_SYMBOLS_QUOTES:
            if text.startswith(open_sym) and text.endswith(close_sym):
                inner = text[len(open_sym):-len(close_sym)]
                return inner, (open_sym, close_sym)
        
        return text, ("", "")

