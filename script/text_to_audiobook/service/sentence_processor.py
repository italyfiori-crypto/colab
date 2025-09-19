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
    (""", """),
    ('"', '"'),  # 恢复标准双引号用于调试
    ("'", "'"),  # 添加单引号支持
]

# 配置：句中分隔符（可以再扩展）
SPLIT_PUNCT = [",", "，", ":", "：", ";", "；", "!", "?", "."]

# 常见英文缩写词（避免在缩写词后的句号处错误拆分）
COMMON_ABBREVIATIONS = {
    # 敬语和称谓
    "mr", "mrs", "ms", "dr", "prof", "rev", "fr", "sr", "jr",
    # 学位和职位
    "phd", "md", "ba", "ma", "bs", "ms", "llb", "jd", "ceo", "cfo", "cto",
    # 公司和组织
    "inc", "ltd", "corp", "co", "llc", "plc", "ltd", "corp",
    # 地址和地理
    "st", "ave", "rd", "blvd", "dr", "ln", "ct", "pl", "sq", "ter",
    # 时间
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    "am", "pm",
    # 其他常见缩写
    "vs", "etc", "vol", "ch", "fig", "sec", "no", "pg", "pp", "ed", "eds",
    "ie", "eg", "cf", "ibid", "op", "ca", "al", "aka",
    # 国家和地区
    "usa", "uk", "eu", "ussr", "nato", "un", "fbi", "cia", "nasa",
}

# 句末分隔符（不应在此处合并子句）
SENTENCE_TERMINATORS = [".", "!", "?", ";"]

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
    
    def __init__(self):
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
    
    def _parse_text_into_clauses(self, text: str,
                                paren_symbols=PAIR_SYMBOLS_PARENS,
                                quote_symbols=PAIR_SYMBOLS_QUOTES,
                                split_punct=SPLIT_PUNCT):
        """
        将文本拆分成子句的核心逻辑:
        使用简化的状态跟踪，避免复杂的栈管理
        """
        clauses = []
        buf = []
        
        # 简化的引号状态跟踪
        in_double_quote = False  # 标准双引号状态
        in_curved_quote = False  # 弯引号状态
        in_single_quote = False  # 单引号状态
        in_paren = 0  # 括号嵌套层级
        
        i = 0
        while i < len(text):
            ch = text[i]
            
            # 处理标准双引号 "
            if ch == '"':
                if not in_curved_quote and not in_single_quote and in_paren == 0:  # 只在不在其他引号/括号内时处理
                    if not in_double_quote:
                        # 开始双引号 - 保存当前缓冲区，开始引号内容
                        if buf:
                            clause = ''.join(buf).strip()
                            if clause:
                                clauses.append(clause)
                            buf = []
                        in_double_quote = True
                        buf.append(ch)
                    else:
                        # 结束双引号 - 完成引号内容
                        buf.append(ch)
                        clause = ''.join(buf).strip()
                        if clause:
                            clauses.append(clause)
                        buf = []
                        in_double_quote = False
                else:
                    buf.append(ch)
            
            # 处理弯引号 ""
            elif ch == '"':
                if not in_double_quote and not in_single_quote and in_paren == 0:
                    if not in_curved_quote:
                        # 开始弯引号
                        if buf:
                            clause = ''.join(buf).strip()
                            if clause:
                                clauses.append(clause)
                            buf = []
                        in_curved_quote = True
                        buf.append(ch)
                    else:
                        # 这应该是结束，但我们检查下一个字符是否是结束弯引号
                        buf.append(ch)
                else:
                    buf.append(ch)
            
            elif ch == '"':
                if in_curved_quote and not in_double_quote and not in_single_quote and in_paren == 0:
                    # 结束弯引号
                    buf.append(ch)
                    clause = ''.join(buf).strip()
                    if clause:
                        clauses.append(clause)
                    buf = []
                    in_curved_quote = False
                else:
                    buf.append(ch)
            
            # 处理单引号 '
            elif ch == "'":
                # 首先检查是否是缩写词
                if self._is_contraction(text, i):
                    # 是缩写词，直接添加到缓冲区，不进行拆分
                    buf.append(ch)
                elif not in_double_quote and not in_curved_quote and in_paren == 0:
                    if not in_single_quote:
                        # 开始单引号
                        if buf:
                            clause = ''.join(buf).strip()
                            if clause:
                                clauses.append(clause)
                            buf = []
                        in_single_quote = True
                        buf.append(ch)
                    else:
                        # 结束单引号
                        buf.append(ch)
                        clause = ''.join(buf).strip()
                        if clause:
                            clauses.append(clause)
                        buf = []
                        in_single_quote = False
                else:
                    buf.append(ch)
            
            # 处理括号类符号
            elif ch in '([{（【《':
                buf.append(ch)
                if not in_double_quote and not in_curved_quote and not in_single_quote:
                    in_paren += 1
            
            elif ch in ')]}）】》':
                buf.append(ch)
                if not in_double_quote and not in_curved_quote and not in_single_quote and in_paren > 0:
                    in_paren -= 1
            
            # 处理分隔符
            elif ch in split_punct:
                buf.append(ch)
                # 只在不在引号或括号内时进行拆分
                if not in_double_quote and not in_curved_quote and not in_single_quote and in_paren == 0:
                    # 对句号进行特殊检查：如果是缩写词后的句号，则不拆分
                    should_split = True
                    if ch == '.':
                        # 检查是否是缩写词的句号
                        full_text = ''.join(buf)
                        period_pos = len(full_text) - 1
                        if self._is_abbreviation_period(full_text, period_pos):
                            should_split = False
                    
                    if should_split:
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
    
    def _is_contraction(self, text: str, position: int) -> bool:
        """
        检查指定位置的单引号是否是英语缩写词的一部分
        
        Args:
            text: 完整文本
            position: 单引号的位置
            
        Returns:
            True if 是缩写词的单引号，不应拆分
        """
        if position < 0 or position >= len(text) or text[position] != "'":
            return False
        
        def _is_word_boundary_after(pos):
            """检查指定位置后是否是单词边界"""
            return pos >= len(text) or not text[pos].isalnum()
        
        def _is_word_boundary_before(pos):
            """检查指定位置前是否是单词边界"""
            return pos <= 0 or not text[pos-1].isalnum()
        
        # 1. 否定缩写 (n't)
        if position >= 1 and position + 2 < len(text):
            if text[position-1:position+3] == 'n\'t':
                # 检查前面有字母，后面是单词边界
                if position >= 2 and text[position-2].isalpha() and _is_word_boundary_after(position+2):
                    return True
        
        # 2. 动词缩写 ('m, 's, 're, 've, 'd, 'll)
        contraction_suffixes = ['\'m', '\'s', '\'re', '\'ve', '\'d', '\'ll']
        for suffix in contraction_suffixes:
            suffix_end = position + len(suffix)
            if suffix_end <= len(text):
                if text[position:suffix_end] == suffix:
                    # 检查前面有字母，后面是单词边界
                    if position > 0 and text[position-1].isalpha() and _is_word_boundary_after(suffix_end-1):
                        return True
        
        # 3. 以撇号开头的缩写 (只保留最常见、最安全的)
        # 只在前面是真正的单词边界时才检查
        if _is_word_boundary_before(position):
            apostrophe_prefixes = ['\'em', '\'til', '\'till', '\'cause', 
                                 '\'twas', '\'tis', '\'twould', '\'twill']
            for prefix in apostrophe_prefixes:
                prefix_end = position + len(prefix)
                if prefix_end <= len(text):
                    if text[position:prefix_end] == prefix:
                        # 检查后面是单词边界
                        if _is_word_boundary_after(prefix_end-1):
                            return True
        
        # 4. 年代缩写 ('90s, '80s等)
        if _is_word_boundary_before(position):
            if position + 3 <= len(text):
                year_pattern = text[position:position+3]
                if len(year_pattern) == 3 and year_pattern[1:3].isdigit():
                    # 检查是否是年代格式 ('90s)
                    if position + 4 <= len(text) and text[position+3] == 's':
                        if _is_word_boundary_after(position+3):
                            return True
                    # 或者只是两位数年份 ('90)
                    elif _is_word_boundary_after(position+2):
                        return True
        
        # 5. O'姓氏模式 (O'Connor, O'Brien等)
        if position >= 1 and text[position-1] == 'O':
            if position + 1 < len(text) and text[position+1].isupper():
                # 这通常是姓氏，应该保持完整
                return True
        
        # 6. 所有格模式 (word's, words')
        if position > 0 and text[position-1].isalpha():
            # 情况1: word's (单数所有格)
            if position + 1 < len(text) and text[position+1] == 's':
                if _is_word_boundary_after(position+1):
                    return True
            # 情况2: words' (复数所有格)
            elif _is_word_boundary_after(position):
                return True
        
        return False

    def _is_abbreviation_period(self, text: str, position: int) -> bool:
        """
        检查指定位置的句号是否是缩写词的一部分
        
        Args:
            text: 完整文本
            position: 句号的位置
            
        Returns:
            True if 是缩写词的句号，不应拆分
        """
        if position == 0 or text[position] != '.':
            return False
        
        # 向前查找单词边界
        start = position - 1
        while start >= 0 and text[start].isalnum():
            start -= 1
        start += 1
        
        # 提取句号前的单词
        word_before = text[start:position].lower()
        
        # 检查是否是已知缩写词
        return word_before in COMMON_ABBREVIATIONS

    def split_into_clauses(self, text: str,
                        paren_symbols=PAIR_SYMBOLS_PARENS,
                        quote_symbols=PAIR_SYMBOLS_QUOTES,
                        split_punct=SPLIT_PUNCT):
        """
        将文本拆分成子句:
        1. 括号类符号内的文本作为独立子句
        2. 引号类符号内的文本作为独立子句
        3. 分隔符触发拆分分隔符保留在子句末尾
        4. 短子句自动与前一个子句合并
        5. 对长度超过阈值的括号或引号子句再次拆分
        """
        debug_print("split_into_clauses输入", text)
        
        # 第一次调用内部逻辑进行基础拆分
        clauses = self._parse_text_into_clauses(text, paren_symbols, quote_symbols, split_punct)
        debug_print("基础拆分结果", clauses)

        # 第二次调用内部逻辑对长度超过阈值的括号或引号包围的子句进行再拆分
        final_result = []
        for clause in clauses:
            if len(clause) > MAX_SENTENCE_LENGTH and self._is_quoted_or_parenthesized(clause):
                # 去掉外层括号或引号拆分内部内容然后重新包围
                inner_content, wrapper = self._extract_inner_content_and_wrapper(clause)
                if inner_content:
                    inner_clauses = self._parse_text_into_clauses(inner_content, paren_symbols, quote_symbols, split_punct)
                    # 重新添加包围符号
                    for i, inner_clause in enumerate(inner_clauses):
                        if i == 0 and i == len(inner_clauses) - 1:
                            # 只有一个子句，完整包围
                            final_result.append(f"{wrapper[0]}{inner_clause}{wrapper[1]}")
                        elif i == 0:
                            # 第一个子句，只加开始符号
                            final_result.append(f"{wrapper[0]}{inner_clause}")
                        elif i == len(inner_clauses) - 1:
                            # 最后一个子句，只加结束符号
                            final_result.append(f"{inner_clause}{wrapper[1]}")
                        else:
                            # 中间子句，不加符号
                            final_result.append(inner_clause)
                else:
                    final_result.append(clause)
            else:
                final_result.append(clause)

        # 合并过短的子句
        merged = []
        for c in final_result:
            # 检查是否应该合并：
            # 1. 存在前一个子句
            # 2. 前一个子句或当前子句过短
            # 3. 合并后不超过最大长度
            # 4. 前一个子句不以句末分隔符结尾（新增条件）
            should_merge = (
                merged and 
                (len(merged[-1]) < MIN_MERGE_LENGTH or len(c) < MIN_MERGE_LENGTH) and 
                len(merged[-1]) + len(c) < MAX_MERGE_LENGTH and
                not self._ends_with_sentence_terminator(merged[-1])
            )
            
            if should_merge:
                merged[-1] += " " + c
            else:
                merged.append(c)

        # 后置处理: 合并被分离的标点符号
        merged = self._merge_split_punctuation(merged)

        debug_print("split_into_clauses最终输出", merged)
        return merged

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

