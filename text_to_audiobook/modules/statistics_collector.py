#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计收集模块
收集书籍和章节的统计信息，生成meta.json
基于子章节文件和对应的音频文件
"""

import os
import json
import re
from typing import List, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .subtitle_translator import SubtitleTranslator

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    import wave
    LIBROSA_AVAILABLE = False
    print("⚠️ librosa未安装，使用wave库计算音频时长")


@dataclass
class StatisticsCollectorConfig:
    """统计收集器配置"""
    
    # 输出配置
    output_filename: str = "meta.json"
    enabled: bool = True
    
    # 书籍信息配置
    book_title: str = ""  # 如果为空，从输入文件名推导
    book_description: str = ""


class StatisticsCollector:
    """统计收集器 - 收集书籍和章节统计信息"""
    
    def __init__(self, config: StatisticsCollectorConfig):
        """
        初始化统计收集器
        
        Args:
            config: 统计收集器配置
        """
        self.config = config
    
    def collect_statistics(self, 
                         sub_chapter_files: List[str], 
                         audio_files: List[str], 
                         output_dir: str,
                         translator: Optional['SubtitleTranslator'] = None) -> Dict:
        """
        收集书籍和章节统计信息
        
        Args:
            sub_chapter_files: 子章节文件路径列表
            audio_files: 音频文件路径列表  
            output_dir: 输出目录
            translator: 字幕翻译器实例(用于翻译章节标题)
            
        Returns:
            统计信息字典
        """
        print(f"\n📊 开始收集统计信息...")
        
        # 收集章节信息
        chapters_info = self._collect_chapters_info(sub_chapter_files, audio_files)
        
        # 翻译章节标题
        if translator and chapters_info:
            chapter_titles = [ch['title'] for ch in chapters_info]
            print(f"🌏 正在翻译 {len(chapter_titles)} 个章节标题...")
            translated_titles = translator.translate_chapter_titles(chapter_titles)
            
            # 更新章节信息中的中文标题
            for i, chapter in enumerate(chapters_info):
                if i < len(translated_titles):
                    chapter['title_cn'] = translated_titles[i]
                else:
                    chapter['title_cn'] = chapter['title']  # 翻译失败时保持原标题
        
        # 生成书籍信息
        book_info = self._generate_book_info(chapters_info, output_dir)
        
        # 组装最终统计信息
        statistics = {
            "book": book_info,
            "chapters": chapters_info
        }
        
        # 保存到文件
        self._save_statistics(statistics, output_dir)
        
        print(f"✅ 统计信息收集完成！保存到: {os.path.join(output_dir, self.config.output_filename)}")
        return statistics
    
    def _collect_chapters_info(self, sub_chapter_files: List[str], audio_files: List[str]) -> List[Dict]:
        """收集章节信息，从子章节文件提取章节名称"""
        chapters_info = []
        
        # 创建音频文件映射，便于快速查找
        audio_map = {}
        for audio_file in audio_files:
            filename = os.path.basename(audio_file)
            # 移除扩展名，用作键
            key = os.path.splitext(filename)[0]
            audio_map[key] = audio_file
        
        # 处理每个子章节文件
        for sub_chapter_file in sorted(sub_chapter_files):
            try:
                filename = os.path.basename(sub_chapter_file)
                # 子章节文件格式：01_Down_the_Rabbit-Hole(1).txt
                sub_chapter_pattern = re.compile(r'^(\d+)_(.+?)\((\d+)\)\.txt$')
                match = sub_chapter_pattern.match(filename)
                
                if match:
                    chapter_index = int(match.group(1))
                    sub_chapter_index = int(match.group(3))
                    
                    # 提取章节标题（读取文件第一行）
                    chapter_title = self._extract_chapter_title(sub_chapter_file)
                    
                    # 查找对应的音频文件
                    audio_key = os.path.splitext(filename)[0]  # 移除.txt扩展名
                    audio_file = audio_map.get(audio_key)
                    
                    # 计算音频时长
                    duration = 0.0
                    if audio_file and os.path.exists(audio_file):
                        duration = self._get_audio_duration(audio_file)
                    else:
                        print(f"⚠️ 未找到对应音频文件: {audio_key}.wav")
                    
                    chapter_info = {
                        "index": chapter_index,
                        "sub_index": sub_chapter_index,
                        "title": chapter_title,
                        "title_cn": "",  # 待翻译
                        "duration": duration
                    }
                    
                    chapters_info.append(chapter_info)
                else:
                    print(f"⚠️ 子章节文件名格式不匹配: {filename}")
                    
            except Exception as e:
                print(f"⚠️ 处理子章节文件失败 {filename}: {e}")
                continue
        
        # 按章节索引和子章节索引排序
        chapters_info.sort(key=lambda x: (x['index'], x['sub_index']))
        
        return chapters_info
    
    def _extract_chapter_title(self, sub_chapter_file: str) -> str:
        """
        从子章节文件提取章节标题（第一行）
        
        Args:
            sub_chapter_file: 子章节文件路径
            
        Returns:
            章节标题
        """
        try:
            with open(sub_chapter_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                # 如果第一行为空，尝试读取第二行
                if not first_line:
                    first_line = f.readline().strip()
                return first_line if first_line else "Unknown Chapter"
        except Exception as e:
            print(f"⚠️ 无法读取章节标题 {os.path.basename(sub_chapter_file)}: {e}")
            return "Unknown Chapter"
    
    def _get_audio_duration(self, audio_file: str) -> float:
        """获取音频文件时长（秒）"""
        try:
            if LIBROSA_AVAILABLE:
                # 使用librosa
                duration = librosa.get_duration(path=audio_file)
                return round(duration, 2)
            else:
                # 使用wave库
                with wave.open(audio_file, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    sample_rate = wav_file.getframerate()
                    duration = frames / float(sample_rate)
                    return round(duration, 2)
        except Exception as e:
            print(f"⚠️ 无法获取音频时长 {os.path.basename(audio_file)}: {e}")
            return 0.0
    
    def _generate_book_info(self, chapters_info: List[Dict], output_dir: str) -> Dict:
        """生成书籍信息"""
        # 推导书籍标题
        book_title = self.config.book_title
        if not book_title:
            # 从输出目录名推导
            output_dir_name = os.path.basename(output_dir.rstrip('/'))
            if output_dir_name and output_dir_name != 'output':
                book_title = output_dir_name.replace('_', ' ').title()
            else:
                book_title = "Unknown Book"
        
        # 统计总章节数（去重）
        unique_chapters = set()
        total_duration = 0.0
        
        for ch in chapters_info:
            unique_chapters.add(ch['index'])
            total_duration += ch['duration']
        
        return {
            "title": book_title,
            "title_cn": "",  # 待翻译
            "description": self.config.book_description,
            "total_chapters": len(unique_chapters),
            "total_duration": round(total_duration, 2)
        }
    
    def _save_statistics(self, statistics: Dict, output_dir: str):
        """保存统计信息到文件"""
        output_file = os.path.join(output_dir, self.config.output_filename)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(statistics, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存统计信息失败: {e}")
            raise