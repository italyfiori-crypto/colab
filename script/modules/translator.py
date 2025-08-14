#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译模块
使用硅基流动API进行英文字幕的中文翻译
"""

import os
import time
import json
from pathlib import Path
from typing import List, Dict, Optional

try:
    import requests
except ImportError:
    requests = None


class ChineseTranslator:
    """中文翻译器，使用硅基流动API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化翻译器
        
        Args:
            api_key: 硅基流动API密钥，如果为None则从环境变量SILICONFLOW_API_KEY获取
        """
        self.api_key = 'sk-umedlfcxxcbzvyiobzxnigiyjrwgpeocgbffhhmwqmnlnein'
        self.base_url = "https://api.siliconflow.cn/v1"
        self.model = "deepseek-ai/DeepSeek-V2.5"  # 使用DeepSeek模型，翻译效果较好
        
        # 请求配置
        self.timeout = 30
        self.max_retries = 5
        self.initial_retry_delay = 1  # 初始重试间隔（秒）
        self.max_retry_delay = 30     # 最大重试间隔（秒）
        
        # 批处理配置
        self.batch_size = 5  # 每次翻译的字幕条目数量
        
        if not self.api_key:
            print("⚠️  未找到硅基流动API密钥")
            print("请设置环境变量 SILICONFLOW_API_KEY 或在初始化时传入api_key参数")
            print("获取API密钥: https://cloud.siliconflow.cn/")
        
        if not requests:
            print("⚠️  未安装requests库，请运行: pip install requests")
    
    def generate_bilingual_subtitle(self, english_srt_path: Path, output_path: Path) -> bool:
        """
        生成中英文合并字幕文件
        
        Args:
            english_srt_path: 英文SRT文件路径
            output_path: 中英文合并输出SRT文件路径
            
        Returns:
            翻译是否成功
        """
        if not self.api_key or not requests:
            print("翻译功能不可用，生成纯英文字幕")
            # 复制英文字幕到输出路径
            self._copy_english_subtitle(english_srt_path, output_path)
            return False
        
        print(f"正在生成中英文合并字幕: {english_srt_path.name} -> {output_path.name}")
        
        try:
            # 解析英文SRT文件
            subtitle_entries = self._parse_srt_file(english_srt_path)
            if not subtitle_entries:
                print("未找到有效的字幕条目")
                return False
            
            print(f"找到 {len(subtitle_entries)} 条字幕，开始翻译...")
            
            # 批量翻译字幕文本
            translated_entries = self._translate_subtitle_entries(subtitle_entries)
            
            if not translated_entries:
                print("翻译失败，生成纯英文字幕")
                self._copy_english_subtitle(english_srt_path, output_path)
                return False
            
            # 写入中英文合并SRT文件
            self._write_bilingual_srt(translated_entries, output_path)
            print(f"中英文合并字幕已保存到: {output_path}")
            return True
            
        except Exception as e:
            print(f"翻译过程中出错: {e}")
            print("生成纯英文字幕作为备选")
            self._copy_english_subtitle(english_srt_path, output_path)
            return False
    
    def _parse_srt_file(self, srt_path: Path) -> List[Dict]:
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
        for i in range(0, total_entries, self.batch_size):
            batch = subtitle_entries[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_entries + self.batch_size - 1) // self.batch_size
            
            print(f"  翻译批次 {batch_num}/{total_batches} ({len(batch)} 条字幕)")
            
            # 翻译当前批次
            translated_batch = self._translate_batch(batch)
            
            if translated_batch:
                translated_entries.extend(translated_batch)
            else:
                print(f"  批次 {batch_num} 翻译失败，使用原文")
                # 翻译失败时使用原文
                for entry in batch:
                    entry['chinese_text'] = entry['english_text']
                translated_entries.extend(batch)
            
            # 添加延迟避免API限流
            if i + self.batch_size < total_entries:
                time.sleep(0.5)
        
        return translated_entries
    
    def _translate_batch(self, batch: List[Dict]) -> Optional[List[Dict]]:
        """翻译一批字幕条目"""
        # 构建翻译提示词
        texts_to_translate = []
        for entry in batch:
            texts_to_translate.append(f"{entry['index']}. {entry['english_text']}")
        
        combined_text = '\n'.join(texts_to_translate)
        
        prompt = f"""请将以下英文字幕翻译成中文，保持原有的编号和格式。翻译要求：
1. 准确传达原意
2. 语言自然流畅
3. 保持字幕的简洁性
4. 保留原有的编号格式

待翻译内容：
{combined_text}

请严格按照 "编号. 中文翻译" 的格式输出，每行一条字幕："""
        
        # 调用API进行翻译，使用指数退避重试
        for attempt in range(self.max_retries):
            try:
                response = self._call_api_with_retry(prompt, attempt)
                if response:
                    # 解析翻译结果
                    return self._parse_translation_response(response, batch)
                
            except Exception as e:
                print(f"  翻译尝试 {attempt + 1} 失败: {e}")
                if attempt < self.max_retries - 1:
                    # 指数退避延迟
                    delay = min(self.initial_retry_delay * (2 ** attempt), self.max_retry_delay)
                    print(f"  等待 {delay} 秒后重试...")
                    time.sleep(delay)
        
        return None
    
    def _call_api_with_retry(self, prompt: str, attempt: int) -> Optional[str]:
        """带重试逻辑的API调用"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
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
            "temperature": 0.3  # 较低的温度以确保翻译一致性
        }
        
        try:
            # 动态调整超时时间
            timeout = self.timeout + (attempt * 5)  # 每次重试增加5秒超时
            
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            
            # 检查HTTP状态码
            if response.status_code == 429:  # 速率限制
                print(f"  遇到速率限制，等待更长时间...")
                raise requests.exceptions.RequestException("Rate limit exceeded")
            elif response.status_code >= 500:  # 服务器错误，可重试
                print(f"  服务器错误 {response.status_code}，可重试")
                raise requests.exceptions.RequestException(f"Server error: {response.status_code}")
            elif response.status_code >= 400:  # 客户端错误，不重试
                print(f"  客户端错误 {response.status_code}，不重试")
                return None
            
            response.raise_for_status()
            
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                return content.strip()
            else:
                print(f"API响应格式异常: {result}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"  请求超时 (超时时间: {timeout}秒)")
            raise
        except requests.exceptions.ConnectionError:
            print(f"  连接错误")
            raise
        except requests.exceptions.RequestException as e:
            print(f"  API请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            print(f"  API响应解析失败: {e}")
            return None
    
    def _call_api(self, prompt: str) -> Optional[str]:
        """简单API调用（向后兼容）"""
        return self._call_api_with_retry(prompt, 0)
    
    def _parse_translation_response(self, response: str, batch: List[Dict]) -> List[Dict]:
        """解析翻译响应"""
        lines = response.strip().split('\n')
        translated_batch = []
        
        # 创建索引映射
        index_map = {entry['index']: entry for entry in batch}
        
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
                    
                    if index in index_map:
                        entry = index_map[index].copy()
                        entry['chinese_text'] = chinese_text
                        translated_batch.append(entry)
        
        # 如果解析失败，回退到按顺序匹配
        if len(translated_batch) != len(batch):
            print(f"  解析翻译结果异常，尝试按顺序匹配")
            translated_batch = []
            for i, entry in enumerate(batch):
                if i < len(lines):
                    # 移除可能的编号前缀
                    chinese_text = lines[i].strip()
                    if '. ' in chinese_text:
                        chinese_text = chinese_text.split('. ', 1)[1]
                    
                    entry_copy = entry.copy()
                    entry_copy['chinese_text'] = chinese_text or entry['english_text']
                    translated_batch.append(entry_copy)
                else:
                    entry_copy = entry.copy()
                    entry_copy['chinese_text'] = entry['english_text']
                    translated_batch.append(entry_copy)
        
        return translated_batch
    
    def _write_bilingual_srt(self, translated_entries: List[Dict], output_path: Path):
        """写入中英文合并SRT文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in translated_entries:
                f.write(f"{entry['index']}\n")
                f.write(f"{entry['timestamp']}\n")
                f.write(f"{entry['english_text']}\n")
                f.write(f"{entry['chinese_text']}\n\n")
    
    def _copy_english_subtitle(self, english_srt_path: Path, output_path: Path):
        """复制英文字幕作为备选"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(english_srt_path, 'r', encoding='utf-8') as src:
                content = src.read()
            
            with open(output_path, 'w', encoding='utf-8') as dst:
                dst.write(content)
            
            print(f"已复制英文字幕到: {output_path}")
        except Exception as e:
            print(f"复制英文字幕失败: {e}")
    
    def test_connection(self) -> bool:
        """测试API连接"""
        if not self.api_key or not requests:
            return False
        
        try:
            print("正在测试硅基流动API连接...")
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