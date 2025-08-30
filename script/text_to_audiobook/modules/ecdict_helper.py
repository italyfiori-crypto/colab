#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECDICT词典查询工具
基于官方stardict.py提供本地词典查询功能
"""

import os
import sys
from typing import Dict, List, Optional
from pathlib import Path

# 导入ECDICT官方脚本
current_dir = os.path.dirname(os.path.abspath(__file__))
ecdict_dir =  os.path.join(os.path.dirname( os.path.dirname(os.path.dirname(current_dir))), "ECDICT")
sys.path.append(ecdict_dir)

try:
    from stardict import DictCsv
except ImportError as e:
    print(f"❌ 无法导入ECDICT模块: {e}")
    print(f"请确保ECDICT目录存在: {ecdict_dir}")
    raise


class ECDictHelper:
    """ECDICT词典查询助手"""
    
    def __init__(self, ecdict_path: str = None):
        """
        初始化ECDICT查询助手
        
        Args:
            ecdict_path: ECDICT CSV文件路径，默认使用mini版本
        """
        if not ecdict_path:
            # 默认使用完整版本
            ecdict_path = os.path.join(ecdict_dir, "ecdict.csv")
        
        if not os.path.exists(ecdict_path):
            raise FileNotFoundError(f"ECDICT文件不存在: {ecdict_path}")
        
        self.ecdict_path = ecdict_path
        self.dict_csv = DictCsv(ecdict_path)
        
        print(f"📚 ECDICT词典加载完成: {ecdict_path}")
        print(f"📊 词典词汇总数: {self.dict_csv.count()}")
    
    def query_word(self, word: str) -> Optional[Dict]:
        """
        查询单词信息
        
        Args:
            word: 要查询的单词
            
        Returns:
            单词信息字典，如果未找到返回None
        """
        result = self.dict_csv.query(word.lower())
        if result:
            return self._format_word_data(result)
        return None
    
    def query_words_batch(self, words: List[str]) -> Dict[str, Optional[Dict]]:
        """
        批量查询单词信息
        
        Args:
            words: 要查询的单词列表
            
        Returns:
            {word: word_info} 映射字典
        """
        # 转换为小写
        lower_words = [word.lower() for word in words]
        
        # 批量查询
        results = self.dict_csv.query_batch(lower_words)
        
        # 格式化结果
        word_data = {}
        for i, word in enumerate(words):
            result = results[i] if i < len(results) else None
            if result:
                word_data[word] = self._format_word_data(result)
            else:
                word_data[word] = None
        
        return word_data
    
    def _format_word_data(self, ecdict_data: Dict) -> Dict:
        """
        格式化ECDICT数据为标准格式
        
        Args:
            ecdict_data: ECDICT原始数据
            
        Returns:
            标准格式的单词数据
        """
        return {
            "word": ecdict_data.get("word", ""),
            "phonetic": ecdict_data.get("phonetic", ""),
            "translation": ecdict_data.get("translation", ""),
            "pos": ecdict_data.get("pos", ""),
            "collins": ecdict_data.get("collins", 0),
            "oxford": ecdict_data.get("oxford", 0),
            "bnc": ecdict_data.get("bnc", 0),
            "frq": ecdict_data.get("frq", 0),
            "exchange": ecdict_data.get("exchange", ""),
            "definition": ecdict_data.get("definition", ""),  # 英文释义
            "tag": ecdict_data.get("tag", ""),  # 考试标签
            "level": ecdict_data.get("tag", "")  # 等级就是标签
        }
    
    def get_word_level_from_tags(self, tag_str: str) -> str:
        """
        获取ECDICT原生标签作为等级
        
        Args:
            tag_str: ECDICT的tag字段
            
        Returns:
            原生标签字符串
        """
        if not tag_str or not tag_str.strip():
            return ""
        
        # 直接返回ECDICT的原生标签
        return tag_str.strip()
    
    def is_word_normalized_form(self, word: str, original_word: str) -> bool:
        """
        检查单词是否为原始单词的归一化形式
        
        Args:
            word: 当前单词（可能是归一化后的）
            original_word: 原始单词
            
        Returns:
            是否为归一化形式
        """
        if word == original_word:
            return False
        
        # 查询原始单词的exchange信息
        word_data = self.query_word(word)
        if not word_data or not word_data.get("exchange"):
            return False
        
        exchange = word_data["exchange"]
        
        # 检查是否为复数或第三人称单数形式
        # 格式: s:复数形式/3:第三人称单数形式
        for item in exchange.split("/"):
            if ":" in item:
                change_type, change_form = item.split(":", 1)
                if change_type in ["s", "3"] and change_form == original_word:
                    return True
        
        return False