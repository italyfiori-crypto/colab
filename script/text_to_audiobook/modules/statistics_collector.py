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
import wave
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .chapter_title_translator import ChapterTitleTranslator
from dataclasses import dataclass

if TYPE_CHECKING:
    from .subtitle_parser import SubtitleParser


@dataclass
class StatisticsCollectorConfig:
    """统计收集器配置"""
    
    # 输出配置
    output_filename: str = "meta.json"
    enabled: bool = True

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
                         title_translator: Optional['ChapterTitleTranslator'] = None) -> Dict:
        """
        收集书籍和章节统计信息
        
        Args:
            sub_chapter_files: 子章节文件路径列表
            audio_files: 音频文件路径列表  
            output_dir: 输出目录
            title_translator: 章节标题翻译器实例(用于翻译章节标题)
            
        Returns:
            统计信息字典
        """
        print(f"\n📊 开始收集统计信息...")
        
        # 收集章节信息
        chapters_info = self._collect_chapters_info(sub_chapter_files, audio_files, output_dir)
        
        # 翻译章节标题
        if title_translator and chapters_info:
            # 从输出目录路径中提取书籍名称
            book_name = os.path.basename(output_dir.rstrip('/\\'))
            chapter_titles = [ch['title'] for ch in chapters_info]
            translated_titles = title_translator.translate_chapter_titles(chapter_titles, book_name)
            
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
    
    def _collect_chapters_info(self, sub_chapter_files: List[str], audio_files: List[str], output_dir: str) -> List[Dict]:
        """收集章节信息，从子章节文件提取章节名称"""
        chapters_info = []
        
        # 处理每个子章节文件
        for i, sub_chapter_file in enumerate(sorted(sub_chapter_files)):
            try:
                # 提取章节标题（读取文件第一行）
                chapter_title = self._extract_chapter_title(sub_chapter_file)
                
                # 查找对应的音频文件
                filename = os.path.basename(sub_chapter_file)
                filekey = os.path.splitext(filename)[0]
                
                # 计算音频时长
                duration = 0.0
                audio_file = os.path.join(output_dir, "audio", f'{filekey}.wav')
                if audio_file and os.path.exists(audio_file):
                    duration = self._get_audio_duration(audio_file)
                else:
                    print(f"⚠️ 未找到对应音频文件: {audio_file}")
                
                chapter_info = {
                    "local_subtitle_file": os.path.join("subtitles", f'{filekey}.srt'),
                    "local_audio_file": os.path.join("compressed_audio", f'{filekey}.mp3'),
                    "chapter_number": i + 1,
                    "title": chapter_title,
                    "subtitle_url": "",
                    "audio_url": "",
                    "duration": duration,
                    "is_active": True,
                }
                
                chapters_info.append(chapter_info)                    
            except Exception as e:
                print(f"⚠️ 处理子章节文件失败 {filename}: {e}")
                continue
        
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
        
        # 统计总章节时长
        total_duration = sum(ch['duration'] for ch in chapters_info)
        
        return {
            "title": "",
            "author": "",
            "local_cover_file": 'cover.jpg',
            "category": "",
            "description": "",
            "difficulty": "medium",
            "total_chapters": len(chapters_info),
            "total_duration": round(total_duration, 2),
            "is_active": True,
            "tags": [],
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