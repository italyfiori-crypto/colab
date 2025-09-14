#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕解析模块
使用 SiliconFlow API 对英文字幕进行语言学解析，生成中英文字幕和详细的解析JSON文件
"""

import os
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


@dataclass
class SubtitleParserConfig:
    """字幕解析配置"""
    
    # API 配置
    api_key: str = ""
    model: str = ""
    timeout: int = 0
    max_retries: int = 0
    max_concurrent_workers: int = 0


    # 请求配置
    base_url: str = "https://api.siliconflow.cn/v1"
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 30.0


class SubtitleParser:
    """字幕解析器 - 生成中英文字幕并创建详细的语言学解析JSON文件"""
    
    def __init__(self, config: SubtitleParserConfig):
        """
        初始化字幕解析器
        
        Args:
            config: 解析配置
        """
        self.config = config
        
        if not self.config.api_key:
            raise RuntimeError("字幕解析器初始化失败: 缺少 SiliconFlow API 密钥")
    
    def parse_subtitle_files(self, subtitle_files: List[str], output_dir: str) -> List[str]:
        """
        批量解析字幕文件，生成中英文字幕和语言学解析JSON文件
        
        Args:
            subtitle_files: 字幕文件路径列表
            output_dir: 输出根目录
            
        Returns:
            成功解析的文件列表
        """        
        parsed_files = []
        total_files = len(subtitle_files)
        
        # 创建解析结果目录
        analysis_dir = os.path.join(output_dir, "parsed_analysis")
        os.makedirs(analysis_dir, exist_ok=True)
        
        print(f"🔄 开始解析 {total_files} 个字幕文件...")
        
        for i, subtitle_file in enumerate(subtitle_files, 1):
            try:
                filename = os.path.basename(subtitle_file)
                print(f"🔍 解析字幕文件 ({i}/{total_files}): {filename}")
                
                if self._parse_single_file(subtitle_file, analysis_dir):
                    parsed_files.append(subtitle_file)
                    print(f"✅ 解析完成: {filename}")
                else:
                    print(f"❌ 解析失败: {filename}")
                
                # 添加延迟避免API限流
                if i < total_files:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"❌ 解析文件时出错 {os.path.basename(subtitle_file)}: {e}")
                continue
        
        return parsed_files
    
    def _parse_single_file(self, subtitle_file: str, analysis_dir: str) -> bool:
        """
        解析单个字幕文件，生成中英文字幕和JSON解析文件
        
        Args:
            subtitle_file: 字幕文件路径
            analysis_dir: 解析结果输出目录
            
        Returns:
            是否解析成功
        """
        try:
            # 解析SRT文件
            subtitle_entries = self._parse_srt_file(subtitle_file)
            if not subtitle_entries:
                print(f"⚠️ 文件无有效字幕: {os.path.basename(subtitle_file)}")
                return False
            
            # 批量解析字幕条目
            parsed_entries = self._parse_subtitle_entries(subtitle_entries)
            if not parsed_entries:
                return False
            
            # 写回原文件，包含中英文
            self._write_bilingual_srt(parsed_entries, subtitle_file)
            
            # 写入JSON解析结果
            self._write_analysis_json(parsed_entries, subtitle_file, analysis_dir)
            return True
            
        except Exception as e:
            print(f"❌ 解析单个文件失败: {e}")
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
    
    def _parse_subtitle_entries(self, subtitle_entries: List[Dict]) -> List[Dict]:
        """批量解析字幕条目"""
        parsed_entries = []
        total_entries = len(subtitle_entries)
        
        # 分批处理（按并发数分批）
        batch_size = self.config.max_concurrent_workers
        for i in range(0, total_entries, batch_size):
            batch = subtitle_entries[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_entries + batch_size - 1) // batch_size
            
            print(f"  解析批次 {batch_num}/{total_batches} ({len(batch)} 条字幕)")
            
            # 解析当前批次
            parsed_batch = self._parse_batch(batch)
            if parsed_batch:
                parsed_entries.extend(parsed_batch)
            else:
                # 解析失败，保留原英文
                for entry in batch:
                    entry['chinese_text'] = f"[解析失败] {entry['english_text']}"
                    entry['analysis'] = {}
                parsed_entries.extend(batch)
            
            # 添加延迟避免API限流
            if i + batch_size < total_entries:
                time.sleep(0.5)
        
        return parsed_entries
    
    def _parse_batch(self, batch: List[Dict]) -> Optional[List[Dict]]:
        """解析一批字幕条目（并发版本）"""
        print(f"    🚀 开始并发解析 {len(batch)} 条字幕...")
        
        # 使用线程池进行并发处理
        max_workers = min(len(batch), self.config.max_concurrent_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_entry = {
                executor.submit(self._analyze_single_sentence_safe, entry): entry 
                for entry in batch
            }
            
            parsed_batch = []
            completed_count = 0
            for future in as_completed(future_to_entry):
                entry = future_to_entry[future]
                try:
                    analysis_result = future.result()
                    if analysis_result:
                        entry['chinese_text'] = analysis_result.get('translation', f"[翻译失败] {entry['english_text']}")
                        entry['analysis'] = analysis_result
                    else:
                        entry['chinese_text'] = f"[解析失败] {entry['english_text']}"
                        entry['analysis'] = {}
                    
                    parsed_batch.append(entry)
                    completed_count += 1
                    print(f"    ✅ 解析完成字幕 {entry['index']} ({completed_count}/{len(batch)})")
                    
                except Exception as e:
                    print(f"    ❌ 解析字幕 {entry['index']} 失败: {e}")
                    entry['chinese_text'] = f"[解析失败] {entry['english_text']}"
                    entry['analysis'] = {}
                    parsed_batch.append(entry)
        
        # 按原始顺序排序
        parsed_batch.sort(key=lambda x: int(x['index']))
        return parsed_batch
    
    def _analyze_single_sentence_safe(self, entry: Dict) -> Optional[Dict]:
        """
        线程安全的单个句子分析方法
        
        Args:
            entry: 字幕条目字典
            
        Returns:
            解析结果或None
        """
        try:
            english_text = entry['english_text']
            print(f"    📝 解析字幕 {entry['index']}: {english_text}")
            
            # 调用现有的分析方法
            return self._analyze_single_sentence(english_text)
            
        except Exception as e:
            print(f"    ❌ 线程解析失败: {e}")
            return None
    
    def _analyze_single_sentence(self, english_text: str) -> Optional[Dict]:
        """
        分析单个英文句子，返回详细的语言学解析结果
        
        Args:
            english_text: 英文句子
            
        Returns:
            包含翻译和语言学分析的字典，或None表示失败
        """
        # 构建语言学分析提示词
        system_prompt = """IMPORTANT: 只返回JSON格式，不要任何额外文字或解释。

作为英语语言学家，请分析用户输入的英语句子，并严格按以下JSON格式输出。

字段要求:
- translation: 中文翻译，要求信达雅（准确传达原意，语言自然流畅，表达优美）
- sentence_structure: 句法成分分析（主语+谓语+宾语+状语等）
- key_words: 句子中有意义的词汇，排除the、a、is、Mrs.等常见词
- fixed_phrases: 有固定含义的短语搭配，排除过于简单的组合
- core_grammar: 重要语法现象（时态、语态、句式等）
- colloquial_expression: 正式与口语表达对比

输出格式:
{
  "translation": "中文翻译",
  "sentence_structure": "句子结构分析",
  "key_words": [{"word": "单词", "pos": "词性", "meaning": "含义", "pronunciation": "音标"}],
  "fixed_phrases": [{"phrase": "短语", "meaning": "含义"}],
  "core_grammar": [{"point": "语法点", "explanation": "解释"}],
  "colloquial_expression": [{"formal": "正式表达", "informal": "口语表达", "explanation": "用法说明"}]
}

示例1 (复合句):
输入: "The project that we've been working on for months, which involves multiple stakeholders, will be completed once we receive the final approval."
输出:
{
  "translation": "我们已经工作了几个月的这个项目，涉及多个利益相关者，一旦我们收到最终批准就会完成。",
  "sentence_structure": "主语(The project) + 定语从句1(that we've been working on for months) + 定语从句2(which involves multiple stakeholders) + 谓语(will be completed) + 时间状语从句(once we receive the final approval)",
  "key_words": [{"word": "stakeholders", "pos": "n.", "meaning": "利益相关者", "pronunciation": "/ˈsteɪkhoʊldərz/"}, {"word": "approval", "pos": "n.", "meaning": "批准，同意", "pronunciation": "/əˈpruːvəl/"}],
  "fixed_phrases": [{"phrase": "work on", "meaning": "从事，致力于"}],
  "core_grammar": [{"point": "定语从句嵌套", "explanation": "两个定语从句修饰同一主语，'that'引导限制性定语从句，'which'引导非限制性定语从句"}],
  "colloquial_expression": [{"formal": "receive the final approval", "informal": "get the green light", "explanation": "'get the green light'表示获得许可，比'receive approval'更生动"}]
}

示例2 (简单句):
输入: "She is very happy."
输出:
{
  "translation": "她很开心。",
  "sentence_structure": "主语(She) + 系动词(is) + 表语(very happy)",
  "key_words": [],
  "fixed_phrases": [],
  "core_grammar": [],
  "colloquial_expression": []
}

注意: 无相关内容时字段留空(空数组[]或空字符串"")，但不可省略字段。记住：仅输出JSON格式。"""

        user_prompt = f"请分析以下英语句子: \"{english_text}\""
        
        try:
            # 调用API进行分析
            response = self._call_analysis_api(system_prompt, user_prompt)
            if not response:
                return None
            
            # 解析JSON响应
            return self._parse_analysis_response(response)
            
        except Exception as e:
            print(f"    ❌ 句子分析API调用失败: {e}")
            return None
    
    def _call_analysis_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """调用API进行语言学分析"""
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
            "max_tokens": 1500,
            "temperature": 0.2  # 较低温度确保结果稳定
        }
        
        # 带重试的API调用
        retry_delay = self.config.initial_retry_delay
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout)
                response.raise_for_status()
                
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    return content.strip()
                else:
                    raise RuntimeError(f"API响应格式异常: {result}")
                    
            except Exception as e:
                if attempt == self.config.max_retries:
                    print(f"    ❌ 分析API调用失败，已达到最大重试次数({self.config.max_retries + 1}次): {e}")
                    return None
                
                print(f"    ⚠️ 分析API调用失败(第{attempt + 1}次尝试): {e}")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, self.config.max_retry_delay)
        
        return None
    
    def _parse_analysis_response(self, response: str) -> Optional[Dict]:
        """解析API返回的语言学分析结果"""
        try:
            # 尝试直接解析JSON
            analysis = json.loads(response)
            
            # 验证必要字段
            required_fields = ['translation', 'sentence_structure', 'key_words', 'fixed_phrases', 'core_grammar', 'colloquial_expression']
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = [] if field != 'translation' and field != 'sentence_structure' else ""
            
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"    ❌ JSON解析失败: {e}")
            # 尝试提取可能的JSON片段
            try:
                # 查找JSON开始和结束标记
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_text = response[start_idx:end_idx+1]
                    analysis = json.loads(json_text)
                    
                    # 验证字段
                    required_fields = ['translation', 'sentence_structure', 'key_words', 'fixed_phrases', 'core_grammar', 'colloquial_expression']
                    for field in required_fields:
                        if field not in analysis:
                            analysis[field] = [] if field != 'translation' and field != 'sentence_structure' else ""
                    
                    return analysis
            except:
                pass
            
            return None
        except Exception as e:
            print(f"    ❌ 解析响应失败: {e}")
            return None
    
    def _write_analysis_json(self, parsed_entries: List[Dict], subtitle_file: str, analysis_dir: str):
        """将解析结果写入JSON文件"""
        try:
            # 获取字幕文件名（不包含扩展名）
            subtitle_name = os.path.splitext(os.path.basename(subtitle_file))[0]
            json_file = os.path.join(analysis_dir, f"{subtitle_name}.json")
            
            with open(json_file, 'w', encoding='utf-8') as f:
                for entry in parsed_entries:
                    # 构建输出JSON对象
                    output_json = {
                        "subtitle_index": int(entry['index']),
                        "english_text": entry['english_text']
                    }
                    
                    # 添加分析结果
                    if 'analysis' in entry and entry['analysis']:
                        output_json.update(entry['analysis'])
                    else:
                        # 如果没有分析结果，设置默认值
                        output_json.update({
                            "translation": entry.get('chinese_text', ''),
                            "sentence_structure": "",
                            "key_words": [],
                            "fixed_phrases": [],
                            "core_grammar": [],
                            "colloquial_expression": []
                        })
                    
                    # 写入一行JSON
                    f.write(json.dumps(output_json, ensure_ascii=False, separators=(',', ':')) + '\n')
            
            print(f"    ✅ 解析结果已保存到: {json_file}")
            
        except Exception as e:
            print(f"    ❌ 保存解析结果失败: {e}")
    
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
        翻译章节标题列表（并发处理）
        
        Args:
            chapter_titles: 英文章节标题列表
            
        Returns:
            中文章节标题列表
        """
        if not chapter_titles:
            return []
        
        print(f"🌏 正在并发翻译 {len(chapter_titles)} 个章节标题...")
        
        # 使用线程池进行并发处理
        max_workers = min(len(chapter_titles), self.config.max_concurrent_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有翻译任务
            future_to_index = {
                executor.submit(self._translate_single_title, title, i): i
                for i, title in enumerate(chapter_titles)
            }
            
            # 存储结果（按原始顺序）
            translated_titles = [''] * len(chapter_titles)
            completed_count = 0
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    translated_title = future.result()
                    translated_titles[index] = translated_title if translated_title else chapter_titles[index]
                    completed_count += 1
                    print(f"  ✅ 翻译完成标题 {index + 1}/{len(chapter_titles)}: {chapter_titles[index]} -> {translated_titles[index]}")
                    
                except Exception as e:
                    print(f"  ❌ 翻译标题 {index + 1} 失败: {e}")
                    translated_titles[index] = chapter_titles[index]  # 保留原标题
        
        print(f"✅ 章节标题翻译完成")
        return translated_titles
    
    def _translate_single_title(self, title: str, index: int) -> Optional[str]:
        """
        翻译单个章节标题（线程安全）
        
        Args:
            title: 英文章节标题
            index: 标题索引（用于日志）
            
        Returns:
            中文翻译或None（表示失败）
        """
        try:
            print(f"  📝 翻译标题 {index + 1}: {title}")
            
            # 使用简化的翻译prompt
            system_prompt = "你是专业的英中翻译专家。请将用户输入的英文章节标题翻译成中文，保持简洁优雅。只返回翻译结果，无需其他内容。"
            user_prompt = f"请翻译以下章节标题: \"{title}\""
            
            response = self._call_analysis_api(system_prompt, user_prompt)
            if response and response.strip():
                return response.strip()
            else:
                print(f"  ⚠️ 标题 {index + 1} API返回空结果")
                return None
                
        except Exception as e:
            print(f"  ❌ 翻译标题 {index + 1} 异常: {e}")
            return None

    def test_connection(self) -> bool:
        """测试API连接"""
        print("正在测试 SiliconFlow API 连接...")
        try:
            response = self._call_analysis_api("你是一个AI助手", "请回答：你好")
            if response:
                print(f"✅ API连接成功，响应: {response[:50]}...")
                return True
            else:
                print("❌ API连接失败")
                return False
        except Exception as e:
            print(f"❌ API连接测试失败: {e}")
            return False