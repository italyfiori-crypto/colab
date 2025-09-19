#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI客户端 - 统一所有AI API调用
"""

import requests
import time
from typing import List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class AIConfig:
    """AI配置"""
    api_key: str
    model: str = "deepseek-ai/DeepSeek-V2.5"
    base_url: str = "https://api.siliconflow.cn/v1"
    timeout: int = 30
    max_retries: int = 3
    max_concurrent_workers: int = 20


class AIClient:
    """统一的AI客户端"""
    
    def __init__(self, config: AIConfig):
        """
        初始化AI客户端
        
        Args:
            config: AI配置
        """
        self.config = config
        
        if not config.api_key:
            raise RuntimeError("AI客户端初始化失败: 缺少API密钥")
    
    def chat_completion(self, prompt: str, system_prompt: str = "", temperature: float = 0.1, max_tokens: int = 1000) -> str:
        """
        单次对话完成
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            AI响应内容
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self._call_api(messages, temperature, max_tokens)
    
    def batch_completion(self, prompts: List[str], system_prompt: str = "") -> List[str]:
        """
        批量对话完成（支持并发处理）
        
        Args:
            prompts: 用户提示词列表
            system_prompt: 系统提示词
            
        Returns:
            AI响应内容列表
        """
        if not prompts:
            return []
        
        results = [None] * len(prompts)  # 预分配结果列表，保持顺序
        
        def process_single_prompt(index_prompt_pair):
            index, prompt = index_prompt_pair
            try:
                result = self.chat_completion(prompt, system_prompt)
                return index, result
            except Exception as e:
                print(f"⚠️ 处理第{index+1}个请求时出错: {e}")
                return index, ""
        
        # 使用线程池进行并发处理
        with ThreadPoolExecutor(max_workers=self.config.max_concurrent_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(process_single_prompt, (i, prompt)): i 
                for i, prompt in enumerate(prompts)
            }
            
            # 收集结果
            for future in as_completed(future_to_index):
                try:
                    index, result = future.result()
                    results[index] = result
                except Exception as e:
                    index = future_to_index[future]
                    print(f"⚠️ 任务{index+1}执行失败: {e}")
                    results[index] = ""
        
        return results
    
    def _call_api(self, messages: List[dict], temperature: float, max_tokens: int) -> str:
        """
        调用API
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            API响应内容
        """
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.config.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                else:
                    error_msg = f"API调用失败: {response.status_code} - {response.text}"
                    if attempt == self.config.max_retries - 1:
                        raise RuntimeError(error_msg)
                    else:
                        print(f"⚠️ {error_msg}，重试中... ({attempt + 1}/{self.config.max_retries})")
                        time.sleep(2 ** attempt)  # 指数退避
                        
            except requests.RequestException as e:
                error_msg = f"API请求异常: {e}"
                if attempt == self.config.max_retries - 1:
                    raise RuntimeError(error_msg)
                else:
                    print(f"⚠️ {error_msg}，重试中... ({attempt + 1}/{self.config.max_retries})")
                    time.sleep(2 ** attempt)
        
        raise RuntimeError("API调用失败: 超过最大重试次数")