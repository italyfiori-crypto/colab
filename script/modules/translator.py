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

import requests


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
            print("❌ 未找到硅基流动API密钥")
            print("请设置环境变量 SILICONFLOW_API_KEY 或在初始化时传入api_key参数")
            print("获取API密钥: https://cloud.siliconflow.cn/")
            raise RuntimeError("翻译器初始化失败: 缺少API密钥")
    
    def generate_bilingual_subtitle(self, english_srt_path: Path, output_path: Path) -> bool:
        """
        生成中英文合并字幕文件
        
        Args:
            english_srt_path: 英文SRT文件路径
            output_path: 中英文合并输出SRT文件路径
            
        Returns:
            翻译是否成功
        """
        
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
                raise RuntimeError("字幕翻译失败")
            
            # 写入中英文合并SRT文件
            self._write_bilingual_srt(translated_entries, output_path)
            print(f"中英文合并字幕已保存到: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 翻译过程中出错: {e}")
            raise
    
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
            
            # 翻译当前批次 - 必须成功
            translated_batch = self._translate_batch(batch)
            translated_entries.extend(translated_batch)
            
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
        
        # 调用API进行翻译 - 不重试，必须成功
        response = self._call_api(prompt)
        if not response:
            raise RuntimeError("翻译API调用失败")
        
        # 解析翻译结果
        return self._parse_translation_response(response, batch)
    
    def _call_api(self, prompt: str) -> Optional[str]:
        """调用API - 带重试机制"""
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
            "temperature": 0.3
        }
        
        # 带指数退避的重试机制
        retry_delay = self.initial_retry_delay
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
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
                last_exception = e
                
                if attempt == self.max_retries:
                    print(f"❌ API调用失败，已达到最大重试次数({self.max_retries + 1}次)")
                    print(f"最后错误: {e}")
                    raise RuntimeError(f"硅基流动API调用失败，重试{self.max_retries + 1}次后仍然失败: {e}")
                
                print(f"⚠️ API调用失败(第{attempt + 1}次尝试): {e}")
                print(f"将在{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                
                # 指数退避，但不超过最大延迟
                retry_delay = min(retry_delay * 2, self.max_retry_delay)
        
        # 理论上不会执行到这里
        raise RuntimeError("API调用出现未知错误")
    
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
        
        # 如果解析失败，直接报错
        if len(translated_batch) != len(batch):
            raise RuntimeError(f"翻译结果解析失败，期望{len(batch)}条，实际解析{len(translated_batch)}条")
        
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
    
    
    def translate_book_title(self, title: str) -> str:
        """
        翻译书名
        
        Args:
            title: 英文书名
            
        Returns:
            中文书名
        """
        if not title.strip():
            return ""
        
        prompt = f"""请将以下英文书名翻译成中文，要求：
1. 准确传达原书名的含义
2. 符合中文图书命名习惯
3. 保持书名的文学性和吸引力
4. 只返回翻译结果，不要其他解释

英文书名：{title}

中文书名："""
        
        response = self._call_api(prompt)
        if response:
            # 清理响应，只保留书名
            chinese_title = response.strip().replace("中文书名：", "").strip()
            return chinese_title
        else:
            raise RuntimeError("书名翻译失败")
    
    def translate_chapter_title(self, title: str) -> str:
        """
        翻译章节标题
        
        Args:
            title: 英文章节标题
            
        Returns:
            中文章节标题
        """
        if not title.strip():
            return ""
        
        prompt = f"""请将以下英文章节标题翻译成中文，要求：
1. 准确传达章节内容主题
2. 保持标题的简洁性
3. 符合中文表达习惯
4. 如果是"CHAPTER X"格式，保持章节编号
5. 只返回翻译结果，不要其他解释

英文章节标题：{title}

中文章节标题："""
        
        response = self._call_api(prompt)
        if response:
            # 清理响应，只保留标题
            chinese_title = response.strip().replace("中文章节标题：", "").strip()
            return chinese_title
        else:
            raise RuntimeError("章节标题翻译失败")
    
    def test_connection(self) -> bool:
        """测试API连接 - 必须成功"""
        print("正在测试硅基流动API连接...")
        response = self._call_api("请回答：你好")
        
        if response:
            print(f"✅ API连接成功，响应: {response[:50]}...")
            return True
        else:
            raise RuntimeError("API连接失败")