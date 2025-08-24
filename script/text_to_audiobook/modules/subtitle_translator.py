#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕翻译模块
使用 SiliconFlow API 将英文字幕翻译为中文，直接修改原字幕文件
"""

import os
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import requests


@dataclass
class SubtitleTranslatorConfig:
    """字幕翻译配置"""
    
    # API 配置
    api_key: str = ""
    model: str = "deepseek-ai/DeepSeek-V2.5"
    base_url: str = "https://api.siliconflow.cn/v1"
    
    # 翻译配置
    enabled: bool = False
    batch_size: int = 5
    
    # 请求配置
    timeout: int = 30
    max_retries: int = 5
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 30.0


class SubtitleTranslator:
    """字幕翻译器 - 直接修改原字幕文件添加中文翻译"""
    
    def __init__(self, config: SubtitleTranslatorConfig):
        """
        初始化字幕翻译器
        
        Args:
            config: 翻译配置
        """
        self.config = config
        
        if not self.config.api_key:
            raise RuntimeError("字幕翻译器初始化失败: 缺少 SiliconFlow API 密钥")
    
    def translate_subtitle_files(self, subtitle_files: List[str]) -> List[str]:
        """
        批量翻译字幕文件，直接修改原文件
        
        Args:
            subtitle_files: 字幕文件路径列表
            
        Returns:
            成功翻译的文件列表
        """        
        translated_files = []
        total_files = len(subtitle_files)
        
        print(f"🔄 开始翻译 {total_files} 个字幕文件...")
        
        for i, subtitle_file in enumerate(subtitle_files, 1):
            try:
                filename = os.path.basename(subtitle_file)
                print(f"🌏 翻译字幕文件 ({i}/{total_files}): {filename}")
                
                if self._translate_single_file(subtitle_file):
                    translated_files.append(subtitle_file)
                    print(f"✅ 翻译完成: {filename}")
                else:
                    print(f"❌ 翻译失败: {filename}")
                
                # 添加延迟避免API限流
                if i < total_files:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"❌ 翻译文件时出错 {os.path.basename(subtitle_file)}: {e}")
                continue
        
        return translated_files
    
    def _translate_single_file(self, subtitle_file: str) -> bool:
        """
        翻译单个字幕文件，直接修改原文件
        
        Args:
            subtitle_file: 字幕文件路径
            
        Returns:
            是否翻译成功
        """
        try:
            # 解析SRT文件
            subtitle_entries = self._parse_srt_file(subtitle_file)
            if not subtitle_entries:
                print(f"⚠️ 文件无有效字幕: {os.path.basename(subtitle_file)}")
                return False
            
            # 批量翻译字幕条目
            translated_entries = self._translate_subtitle_entries(subtitle_entries)
            if not translated_entries:
                return False
            
            # 写回原文件，包含中英文
            self._write_bilingual_srt(translated_entries, subtitle_file)
            return True
            
        except Exception as e:
            print(f"❌ 翻译单个文件失败: {e}")
            return False
    
    def _parse_srt_file(self, srt_path: str) -> List[Dict]:
        """解析SRT文件"""
        subtitle_entries = []
        
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 按空行分割字幕条目
            blocks = content.split('\n\n')
            
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    # 解析字幕条目
                    index = lines[0].strip()
                    timestamp = lines[1].strip()
                    text = '\n'.join(lines[2:]).strip()
                    
                    subtitle_entries.append({
                        'index': index,
                        'timestamp': timestamp,
                        'english_text': text,
                        'chinese_text': ''
                    })
            
            return subtitle_entries
            
        except Exception as e:
            print(f"解析SRT文件失败: {e}")
            return []
    
    def _translate_subtitle_entries(self, subtitle_entries: List[Dict]) -> List[Dict]:
        """批量翻译字幕条目"""
        translated_entries = []
        total_entries = len(subtitle_entries)
        
        # 分批处理
        for i in range(0, total_entries, self.config.batch_size):
            batch = subtitle_entries[i:i + self.config.batch_size]
            batch_num = i // self.config.batch_size + 1
            total_batches = (total_entries + self.config.batch_size - 1) // self.config.batch_size
            
            print(f"  翻译批次 {batch_num}/{total_batches} ({len(batch)} 条字幕)")
            
            # 翻译当前批次
            translated_batch = self._translate_batch(batch)
            if translated_batch:
                translated_entries.extend(translated_batch)
            else:
                # 翻译失败，保留原英文
                for entry in batch:
                    entry['chinese_text'] = f"[翻译失败] {entry['english_text']}"
                translated_entries.extend(batch)
            
            # 添加延迟避免API限流
            if i + self.config.batch_size < total_entries:
                time.sleep(0.5)
        
        return translated_entries
    
    def _translate_batch(self, batch: List[Dict]) -> Optional[List[Dict]]:
        """翻译一批字幕条目"""
        # 构建翻译提示词
        texts_to_translate = []
        for entry in batch:
            texts_to_translate.append(f"{entry['index']}. {entry['english_text']}")
        
        combined_text = '\n'.join(texts_to_translate)
        
        prompt = f"""将英文字幕翻译成中文，必须严格遵守格式要求。

**格式要求（必须严格遵守）**：
- 输出格式：编号. 中文翻译
- 保持原有编号不变
- 每行一条字幕
- 不要添加任何解释或其他文字
- 不要改变编号顺序

**翻译要求**：
1. 准确传达原意
2. 语言自然流畅  
3. 保持字幕简洁性

**示例**：
输入：
1. Alice was beginning to get very tired.
2. She looked at her sister's book.

输出：
1. 爱丽丝开始感到非常疲倦。
2. 她看了看姐姐的书。

**待翻译内容**：
{combined_text}

**严格按照格式输出**："""
        
        try:
            # 调用API进行翻译
            response = self._call_api(prompt)
            if not response:
                return None
            
            # 解析翻译结果
            return self._parse_translation_response(response, batch)
            
        except Exception as e:
            print(f"❌ 批量翻译失败: {e}")
            return None
    
    def _call_api(self, prompt: str) -> Optional[str]:
        """调用 SiliconFlow API"""
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
                    "content": "你是一个专业的英中翻译专家，专门翻译英文字幕。你的翻译准确、自然、符合中文表达习惯。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "stream": False,
            "max_tokens": 2000,
            "temperature": 0.3
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
    
    def _parse_translation_response(self, response: str, batch: List[Dict]) -> List[Dict]:
        """解析翻译响应"""
        lines = response.strip().split('\n')
        translated_batch = []
        matched_indices = set()
        
        # 创建索引映射
        index_map = {entry['index']: entry for entry in batch}
        
        # 第一轮：精确匹配标准格式 "编号. 翻译内容"
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 尝试解析 "编号. 翻译内容" 格式
            if '. ' in line:
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    index = parts[0].strip()
                    chinese_text = parts[1].strip()
                    
                    if index in index_map and index not in matched_indices:
                        entry = index_map[index].copy()
                        entry['chinese_text'] = chinese_text
                        translated_batch.append(entry)
                        matched_indices.add(index)
        
        # 第二轮：模糊匹配未匹配的条目
        unmatched_entries = [entry for entry in batch if entry['index'] not in matched_indices]
        if unmatched_entries:
            # 收集可能的翻译内容
            potential_translations = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 跳过已经精确匹配的行
                skip_line = False
                for matched_index in matched_indices:
                    if line.startswith(f"{matched_index}. "):
                        skip_line = True
                        break
                
                if not skip_line:
                    # 清理可能的编号前缀
                    import re
                    cleaned_line = re.sub(r'^\d+[.。]\s*', '', line)
                    cleaned_line = re.sub(r'^[•·-]\s*', '', cleaned_line)
                    
                    if cleaned_line and len(cleaned_line) > 5:
                        potential_translations.append(cleaned_line)
            
            # 按顺序匹配剩余条目
            for i, unmatched_entry in enumerate(unmatched_entries):
                if i < len(potential_translations):
                    entry = unmatched_entry.copy()
                    entry['chinese_text'] = potential_translations[i]
                    translated_batch.append(entry)
                else:
                    # 没有足够的翻译内容，保留英文原文
                    entry = unmatched_entry.copy()
                    entry['chinese_text'] = f"[翻译失败] {unmatched_entry['english_text']}"
                    translated_batch.append(entry)
        
        # 按原始顺序排序
        original_order = {entry['index']: i for i, entry in enumerate(batch)}
        translated_batch.sort(key=lambda x: original_order.get(x['index'], 999))
        
        return translated_batch
    
    def _write_bilingual_srt(self, translated_entries: List[Dict], output_path: str):
        """写入中英文双语SRT文件，直接覆盖原文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in translated_entries:
                f.write(f"{entry['index']}\n")
                f.write(f"{entry['timestamp']}\n")
                f.write(f"{entry['english_text']}\n")
                f.write(f"{entry['chinese_text']}\n\n")
    
    def translate_chapter_titles(self, chapter_titles: List[str]) -> List[str]:
        """
        翻译章节标题列表（分批处理）
        
        Args:
            chapter_titles: 英文章节标题列表
            
        Returns:
            中文章节标题列表
        """
        if not chapter_titles:
            return []
        
        print(f"🌏 正在翻译 {len(chapter_titles)} 个章节标题...")
        
        # 分批处理
        translated_titles = [None] * len(chapter_titles)  # 预分配结果列表
        total_batches = (len(chapter_titles) + self.config.batch_size - 1) // self.config.batch_size
        
        for i in range(0, len(chapter_titles), self.config.batch_size):
            batch = chapter_titles[i:i + self.config.batch_size]
            batch_num = i // self.config.batch_size + 1
            
            print(f"  翻译批次 {batch_num}/{total_batches} ({len(batch)} 个标题)")
            
            try:
                # 翻译当前批次
                batch_translated = self._translate_chapter_titles_batch(batch, i)
                
                # 将结果放入对应位置
                for j, translated in enumerate(batch_translated):
                    translated_titles[i + j] = translated
                    
            except Exception as e:
                print(f"⚠️ 批次 {batch_num} 翻译失败: {e}")
                # 翻译失败时，保留原标题
                for j, original in enumerate(batch):
                    translated_titles[i + j] = original
            
            # 添加延迟避免API限流
            if i + self.config.batch_size < len(chapter_titles):
                time.sleep(0.5)
        
        # 过滤掉None值（如果有的话）
        result = [title if title is not None else original 
                 for title, original in zip(translated_titles, chapter_titles)]
        
        print(f"✅ 章节标题翻译完成")
        return result
    
    def _translate_chapter_titles_batch(self, batch_titles: List[str], start_index: int) -> List[str]:
        """
        翻译一批章节标题
        
        Args:
            batch_titles: 当前批次的标题列表
            start_index: 在原始列表中的起始索引
            
        Returns:
            翻译后的标题列表
        """
        # 构建翻译提示词，使用全局编号
        titles_text = '\n'.join([f"{start_index + i + 1}. {title}" 
                                for i, title in enumerate(batch_titles)])
        
        prompt = f"""将英文章节标题翻译成中文，必须严格遵守格式要求。

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
5. 标题中如果包含符号和数字， 翻译要保持不变

**示例**：
输入：
1. Down the Rabbit-Hole(1)
3. Down the Rabbit-Hole(2)
2. The Pool of Tears

输出：
1. 掉进兔子洞(1)
2. 掉进兔子洞(2)
3. 眼泪池

**待翻译章节标题**：
{titles_text}

**严格按照格式输出**："""
        
        try:
            # 调用API进行翻译
            response = self._call_api(prompt)
            if not response:
                print("❌ 批次翻译失败，返回原标题")
                return batch_titles
            
            # 解析翻译结果，传入批次的起始编号
            translated_titles = self._parse_chapter_titles_batch_response(
                response, batch_titles, start_index)
            
            return translated_titles
            
        except Exception as e:
            print(f"❌ 批次翻译失败: {e}")
            return batch_titles
    
    def _parse_chapter_titles_batch_response(self, response: str, original_titles: List[str], start_index: int) -> List[str]:
        """解析批次章节标题翻译响应"""
        lines = response.strip().split('\n')
        translated_titles = [None] * len(original_titles)
        matched_indices = set()
        
        # 第一轮：精确匹配标准格式 "编号. 翻译内容"
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 尝试解析 "编号. 翻译内容" 格式
            if '. ' in line:
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    try:
                        global_index = int(parts[0].strip()) - 1  # 全局索引（0基）
                        chinese_title = parts[1].strip()
                        
                        # 转换为批次内的相对索引
                        relative_index = global_index - start_index
                        
                        if (0 <= relative_index < len(original_titles) and 
                            relative_index not in matched_indices):
                            translated_titles[relative_index] = chinese_title
                            matched_indices.add(relative_index)
                    except ValueError:
                        continue
        
        # 第二轮：处理未匹配的标题，使用原标题
        for i in range(len(original_titles)):
            if i not in matched_indices:
                translated_titles[i] = original_titles[i]  # 保持原标题
        
        # 过滤掉None值
        result = [title if title is not None else original_titles[i] 
                 for i, title in enumerate(translated_titles)]
        
        return result
    
    def _parse_chapter_titles_response(self, response: str, original_titles: List[str]) -> List[str]:
        """解析章节标题翻译响应"""
        lines = response.strip().split('\n')
        translated_titles = []
        matched_indices = set()
        
        # 第一轮：精确匹配标准格式 "编号. 翻译内容"
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 尝试解析 "编号. 翻译内容" 格式
            if '. ' in line:
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    try:
                        index = int(parts[0].strip()) - 1  # 转换为0基索引
                        chinese_title = parts[1].strip()
                        
                        if 0 <= index < len(original_titles) and index not in matched_indices:
                            # 确保translated_titles有足够长度
                            while len(translated_titles) <= index:
                                translated_titles.append("")
                            
                            translated_titles[index] = chinese_title
                            matched_indices.add(index)
                    except ValueError:
                        continue
        
        # 第二轮：处理未匹配的标题，使用原标题
        for i in range(len(original_titles)):
            if i not in matched_indices:
                # 确保translated_titles有足够长度
                while len(translated_titles) <= i:
                    translated_titles.append("")
                
                translated_titles[i] = original_titles[i]  # 保持原标题
        
        # 只返回有效长度的列表
        return translated_titles[:len(original_titles)]
    
    def test_connection(self) -> bool:
        """测试API连接"""
        print("正在测试 SiliconFlow API 连接...")
        try:
            response = self._call_api("请回答：你好")
            if response:
                print(f"✅ API连接成功，响应: {response[:50]}...")
                return True
            else:
                print("❌ API连接失败")
                return False
        except Exception as e:
            print(f"❌ API连接测试失败: {e}")
            return False