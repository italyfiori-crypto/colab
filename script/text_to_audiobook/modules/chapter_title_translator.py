#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节标题翻译模块
专门处理章节标题的批量翻译，支持智能去重和上下文翻译
"""

import os
import time
import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import requests


@dataclass
class ChapterTitleTranslatorConfig:
    """章节标题翻译器配置"""
    
    # API 配置
    api_key: str = ""
    model: str = ""
    timeout: int = 30
    max_retries: int = 3
    
    # 批量翻译配置
    batch_size: int = 5
    
    # 请求配置
    base_url: str = "https://api.siliconflow.cn/v1"
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 30.0


class ChapterTitleTranslator:
    """章节标题翻译器 - 批量翻译章节标题，支持智能去重和上下文翻译"""
    
    def __init__(self, config: ChapterTitleTranslatorConfig):
        """
        初始化章节标题翻译器
        
        Args:
            config: 翻译器配置
        """
        self.config = config
        
        if not self.config.api_key:
            raise RuntimeError("章节标题翻译器初始化失败: 缺少 API 密钥")
    
    def translate_chapter_titles(self, chapter_titles: List[str], book_name: str = "") -> List[str]:
        """
        翻译章节标题列表（智能去重 + 批量处理）
        
        Args:
            chapter_titles: 英文章节标题列表
            book_name: 书籍名称，用于提供翻译上下文
            
        Returns:
            中文章节标题列表
        """
        if not chapter_titles:
            return []
        
        print(f"🌏 正在智能翻译 {len(chapter_titles)} 个章节标题...")
        if book_name:
            print(f"📖 书籍上下文: {book_name}")
        
        # 步骤1: 分析标题模式并去重
        unique_patterns, pattern_mapping = self._analyze_title_patterns(chapter_titles)
        
        print(f"🔍 识别到 {len(unique_patterns)} 个独特标题模式")
        
        # 步骤2: 批量翻译独特的模式
        pattern_translations = self._translate_unique_patterns_batch(unique_patterns, book_name)
        
        # 步骤3: 根据模式映射生成完整的翻译结果
        translated_titles = self._apply_pattern_translations(chapter_titles, pattern_mapping, pattern_translations)
        
        print(f"✅ 章节标题翻译完成")
        return translated_titles
    
    def _analyze_title_patterns(self, chapter_titles: List[str]) -> Tuple[List[str], List[int]]:
        """
        分析章节标题模式，识别相同的标题结构（除数字外）
        
        Args:
            chapter_titles: 章节标题列表
            
        Returns:
            tuple: (独特模式列表, 模式映射索引列表)
        """
        patterns = []
        pattern_mapping = []
        unique_patterns = []
        
        for title in chapter_titles:
            # 将数字替换为占位符，识别标题模式
            pattern = re.sub(r'\d+', '{num}', title)
            pattern = re.sub(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b', '{num}', pattern, flags=re.IGNORECASE)
            
            if pattern not in patterns:
                patterns.append(pattern)
                unique_patterns.append(title)  # 使用第一个遇到的标题作为模式代表
                pattern_mapping.append(len(patterns) - 1)
            else:
                pattern_mapping.append(patterns.index(pattern))
        
        return unique_patterns, pattern_mapping
    
    def _translate_unique_patterns_batch(self, unique_patterns: List[str], book_name: str) -> List[str]:
        """
        批量翻译独特的标题模式
        
        Args:
            unique_patterns: 独特标题模式列表
            book_name: 书籍名称
            
        Returns:
            翻译结果列表
        """
        if not unique_patterns:
            return []
        
        translated_patterns = []
        total_patterns = len(unique_patterns)
        
        # 分批处理
        for i in range(0, total_patterns, self.config.batch_size):
            batch = unique_patterns[i:i + self.config.batch_size]
            batch_num = i // self.config.batch_size + 1
            total_batches = (total_patterns + self.config.batch_size - 1) // self.config.batch_size
            
            print(f"  翻译批次 {batch_num}/{total_batches} ({len(batch)} 个模式)")
            
            try:
                # 翻译当前批次
                batch_translated = self._translate_batch_with_fallback(batch, book_name, i + 1)
                translated_patterns.extend(batch_translated)
                
            except Exception as e:
                print(f"⚠️ 批次 {batch_num} 翻译失败: {e}")
                # 翻译失败时，保留原标题
                translated_patterns.extend(batch)
            
            # 添加延迟避免API限流
            if i + self.config.batch_size < total_patterns:
                time.sleep(0.5)
        
        return translated_patterns
    
    def _translate_batch_with_fallback(self, batch_titles: List[str], book_name: str, start_number: int) -> List[str]:
        """
        带降级机制的批量翻译
        
        Args:
            batch_titles: 当前批次的标题列表
            book_name: 书籍名称
            start_number: 编号起始值
            
        Returns:
            翻译后的标题列表
        """
        try:
            # 尝试批量翻译
            return self._translate_chapter_titles_batch(batch_titles, book_name, start_number)
        except Exception as e:
            print(f"    ⚠️ 批量翻译失败，回退到单个翻译: {e}")
            # 回退到单个翻译
            return self._translate_titles_individually(batch_titles, book_name)
    
    def _translate_chapter_titles_batch(self, batch_titles: List[str], book_name: str, start_number: int) -> List[str]:
        """
        翻译一批章节标题
        
        Args:
            batch_titles: 当前批次的标题列表
            book_name: 书籍名称
            start_number: 编号起始值
            
        Returns:
            翻译后的标题列表
        """
        # 构建翻译提示词，使用连续编号
        titles_text = '\n'.join([f"{start_number + i}. {title}" 
                                for i, title in enumerate(batch_titles)])
        
        # 构建包含书籍上下文的prompt
        if book_name:
            context_info = f"""你正在翻译书籍《{book_name}》的章节标题。请根据书籍主题和风格进行翻译。

"""
        else:
            context_info = ""
        
        prompt = f"""{context_info}将英文章节标题翻译成中文，必须严格遵守格式要求。

**格式要求（必须严格遵守）**：
- 输出格式：编号. 中文翻译
- 保持原有编号不变
- 每行一个标题
- 不要添加任何解释或其他文字
- 不要改变编号顺序

**翻译要求**：
1. 准确传达章节主题
2. 语言简洁优雅
3. 符合中文表达习惯
4. 保持文学性
5. 标题中如果包含符号和数字，翻译要保持不变

**示例**：
输入：
1. Down the Rabbit-Hole(1)
2. The Pool of Tears
3. Down the Rabbit-Hole(2)

输出：
1. 掉进兔子洞(1)
2. 眼泪池
3. 掉进兔子洞(2)

**待翻译章节标题**：
{titles_text}

**严格按照格式输出**："""
        
        # 调用API进行翻译
        response = self._call_translation_api(prompt)
        if not response:
            raise RuntimeError("API返回空结果")
        
        # 解析翻译结果
        translated_titles = self._parse_batch_response(response, batch_titles, start_number)
        
        return translated_titles
    
    def _translate_titles_individually(self, batch_titles: List[str], book_name: str) -> List[str]:
        """
        单个翻译标题（降级方案）
        
        Args:
            batch_titles: 标题列表
            book_name: 书籍名称
            
        Returns:
            翻译结果列表
        """
        translated_titles = []
        
        for i, title in enumerate(batch_titles):
            try:
                print(f"    📝 单独翻译标题 {i+1}: {title}")
                translated = self._translate_single_title(title, book_name)
                translated_titles.append(translated if translated else title)
            except Exception as e:
                print(f"    ❌ 单独翻译失败: {e}")
                translated_titles.append(title)
        
        return translated_titles
    
    def _translate_single_title(self, title: str, book_name: str) -> Optional[str]:
        """
        翻译单个章节标题
        
        Args:
            title: 英文章节标题
            book_name: 书籍名称
            
        Returns:
            中文翻译或None（表示失败）
        """
        # 使用包含书籍上下文的翻译prompt
        if book_name:
            system_prompt = f"""你是专业的英中翻译专家。你正在翻译书籍《{book_name}》的章节标题。

要求：
1. 根据书籍《{book_name}》的主题和风格进行翻译
2. 保持章节标题的简洁优雅
3. 如果包含章节序号，保持序号的格式
4. 只返回翻译结果，无需其他内容"""
        else:
            system_prompt = "你是专业的英中翻译专家。请将用户输入的英文章节标题翻译成中文，保持简洁优雅。只返回翻译结果，无需其他内容。"
        
        user_prompt = f"请翻译以下章节标题: \"{title}\""
        
        response = self._call_unified_api(system_prompt, user_prompt, max_tokens=500, temperature=0.2)
        if response and response.strip():
            return response.strip()
        
        return None
    
    def _parse_batch_response(self, response: str, original_titles: List[str], start_number: int) -> List[str]:
        """
        解析批次翻译响应
        
        Args:
            response: API响应文本
            original_titles: 原始标题列表
            start_number: 编号起始值
            
        Returns:
            解析后的翻译列表
        """
        lines = response.strip().split('\n')
        translated_titles = [None] * len(original_titles)
        matched_indices = set()
        
        # 精确匹配标准格式 "编号. 翻译内容"
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 尝试解析 "编号. 翻译内容" 格式
            if '. ' in line:
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    try:
                        number = int(parts[0].strip())
                        chinese_title = parts[1].strip()
                        
                        # 转换为批次内的相对索引
                        relative_index = number - start_number
                        
                        if (0 <= relative_index < len(original_titles) and 
                            relative_index not in matched_indices):
                            translated_titles[relative_index] = chinese_title
                            matched_indices.add(relative_index)
                            print(f"    ✅ 解析翻译 {number}: {original_titles[relative_index]} -> {chinese_title}")
                    except ValueError:
                        continue
        
        # 处理未匹配的标题，使用原标题
        for i in range(len(original_titles)):
            if i not in matched_indices:
                translated_titles[i] = original_titles[i]
                print(f"    ⚠️ 保留原标题 {start_number + i}: {original_titles[i]}")
        
        # 过滤掉None值
        result = [title if title is not None else original_titles[i] 
                 for i, title in enumerate(translated_titles)]
        
        return result
    
    def _apply_pattern_translations(self, original_titles: List[str], pattern_mapping: List[int], pattern_translations: List[str]) -> List[str]:
        """
        根据模式映射将翻译结果应用到所有标题
        
        Args:
            original_titles: 原始标题列表
            pattern_mapping: 模式映射索引列表
            pattern_translations: 模式翻译结果列表
            
        Returns:
            完整的翻译结果列表
        """
        translated_titles = []
        
        for i, (original_title, pattern_index) in enumerate(zip(original_titles, pattern_mapping)):
            if pattern_index < len(pattern_translations):
                pattern_translation = pattern_translations[pattern_index]
                
                # 提取原标题中的数字
                numbers_in_original = re.findall(r'\d+', original_title)
                # 查找英文数字
                number_words = re.findall(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b', original_title, flags=re.IGNORECASE)
                
                # 如果模式翻译中包含数字占位符，用实际数字替换
                final_translation = pattern_translation
                if numbers_in_original:
                    # 按顺序替换翻译中的数字占位符或保持数字
                    for num in numbers_in_original:
                        if '{num}' in final_translation:
                            # 优先替换占位符
                            final_translation = final_translation.replace('{num}', num, 1)
                        elif '第' in final_translation and '章' in final_translation:
                            # 中文章节格式，替换数字
                            final_translation = re.sub(r'第\s*\d+\s*章', f'第{num}章', final_translation, count=1)
                        elif re.search(r'\d+', final_translation):
                            # 直接替换数字
                            final_translation = re.sub(r'\d+', num, final_translation, count=1)
                        else:
                            # 如果翻译中没有数字和占位符，在适当位置插入
                            if '章' in final_translation:
                                final_translation = re.sub(r'章', f'第{num}章', final_translation, count=1)
                
                translated_titles.append(final_translation)
                print(f"    📝 应用翻译 {i+1}: {original_title} -> {final_translation}")
            else:
                translated_titles.append(original_title)
                print(f"    ⚠️ 保留原标题 {i+1}: {original_title}")
        
        return translated_titles
    
    def _call_translation_api(self, prompt: str) -> Optional[str]:
        """
        调用翻译API
        
        Args:
            prompt: 翻译提示词
            
        Returns:
            API响应或None
        """
        return self._call_unified_api("你是专业的英中翻译专家。", prompt, max_tokens=1500, temperature=0.2)
    
    def _call_unified_api(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500, temperature: float = 0.2) -> Optional[str]:
        """统一的API调用方法"""
        url = f"{self.config.base_url}/chat/completions"
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.config.api_key}"
        }
        
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": user_prompt
                }
            ],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # 带指数退避的重试机制
        retry_delay = self.config.initial_retry_delay
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout)
                response.raise_for_status()
                
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    if attempt > 0:
                        print(f"✅ API调用在第{attempt + 1}次尝试后成功")
                    return content.strip()
                else:
                    raise RuntimeError(f"API响应格式异常: {result}")
                    
            except Exception as e:
                if attempt == self.config.max_retries:
                    print(f"❌ API调用失败，已达到最大重试次数({self.config.max_retries + 1}次)")
                    print(f"最后错误: {e}")
                    return None
                
                print(f"⚠️ API调用失败(第{attempt + 1}次尝试): {e}")
                print(f"将在{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                
                # 指数退避，但不超过最大延迟
                retry_delay = min(retry_delay * 2, self.config.max_retry_delay)
        
        return None
    
    def test_connection(self) -> bool:
        """测试API连接"""
        print("正在测试章节标题翻译 API 连接...")
        try:
            response = self._call_unified_api("你是一个AI助手", "请回答：你好", max_tokens=50, temperature=0.3)
            if response:
                print(f"✅ API连接成功，响应: {response[:50]}...")
                return True
            else:
                print("❌ API连接失败")
                return False
        except Exception as e:
            print(f"❌ API连接测试失败: {e}")
            return False