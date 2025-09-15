#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计服务 - 专门处理书籍和章节统计信息
从AnalysisService中独立出来
"""

import os
import json
import wave
from typing import List, Dict, Optional, Any
from infra import FileManager
from infra.config_loader import AppConfig
from util import OUTPUT_DIRECTORIES, OUTPUT_FILES


class StatisticsService:
    """统一的统计服务"""
    
    def __init__(self, config: AppConfig):
        """
        初始化统计服务
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.file_manager = FileManager()
    
    def collect_statistics(self, sub_chapter_files: List[str], audio_files: List[str], output_dir: str) -> Optional[Dict[str, Any]]:
        """
        收集书籍和章节统计信息
        
        Args:
            sub_chapter_files: 子章节文件路径列表
            audio_files: 音频文件路径列表
            output_dir: 输出目录
            
        Returns:
            统计信息字典
        """
        if not sub_chapter_files:
            print("⚠️ 未找到子章节文件，跳过统计收集")
            return None
        
        print(f"📊 开始收集统计信息...")
        
        try:
            # 收集章节信息
            chapters_info = self._collect_chapters_info(sub_chapter_files, output_dir)
            
            # 翻译章节标题（如果需要）
            if chapters_info:
                chapters_info = self._translate_chapter_titles(chapters_info, output_dir)
            
            # 生成书籍信息
            book_info = self._generate_book_info(chapters_info, output_dir)
            
            # 组装最终统计信息
            statistics = {
                "book": book_info,
                "chapters": chapters_info
            }
            
            # 保存到文件
            self._save_statistics(statistics, output_dir)
            
            print(f"✅ 统计信息收集完成！")
            return statistics
            
        except Exception as e:
            print(f"❌ 统计信息收集失败: {e}")
            return None
    
    def _collect_chapters_info(self, sub_chapter_files: List[str], output_dir: str) -> List[Dict]:
        """收集章节信息"""
        chapters_info = []
        
        for i, sub_chapter_file in enumerate(sorted(sub_chapter_files)):
            try:
                # 提取章节标题（读取文件第一行）
                content = self.file_manager.read_text_file(sub_chapter_file)
                title, _ = self.file_manager.extract_title_and_body(content)
                
                # 查找对应的音频文件
                filename = os.path.basename(sub_chapter_file)
                filekey = self.file_manager.get_basename_without_extension(filename)
                
                # 计算音频时长
                duration = 0.0
                audio_file = os.path.join(output_dir, OUTPUT_DIRECTORIES['audio'], f'{filekey}.wav')
                if self.file_manager.file_exists(audio_file):
                    duration = self._get_audio_duration(audio_file)
                else:
                    print(f"⚠️ 未找到对应音频文件: {audio_file}")
                
                chapter_info = {
                    "local_subtitle_file": os.path.join(OUTPUT_DIRECTORIES['subtitles'], f'{filekey}.srt'),
                    "local_audio_file": os.path.join(OUTPUT_DIRECTORIES['compressed_audio'], f'{filekey}.mp3'),
                    "chapter_number": i + 1,
                    "title": title,
                    "subtitle_url": "",
                    "audio_url": "",
                    "duration": duration,
                    "is_active": True,
                }
                
                chapters_info.append(chapter_info)
                
            except Exception as e:
                filename = os.path.basename(sub_chapter_file) if sub_chapter_file else "unknown"
                print(f"⚠️ 处理子章节文件失败 {filename}: {e}")
                continue
        
        return chapters_info
    
    def _translate_chapter_titles(self, chapters_info: List[Dict], output_dir: str) -> List[Dict]:
        """翻译章节标题"""
        try:
            from .translation_service import TranslationService
            translation_service = TranslationService(self.config)
            
            book_name = os.path.basename(output_dir.rstrip('/\\'))
            chapter_titles = [ch['title'] for ch in chapters_info]
            translated_titles = translation_service.translate_chapter_titles(chapter_titles, book_name)
            
            # 更新章节信息中的中文标题
            for i, chapter in enumerate(chapters_info):
                if i < len(translated_titles):
                    chapter['title_cn'] = translated_titles[i]
                else:
                    chapter['title_cn'] = chapter['title']
                    
            return chapters_info
            
        except Exception as e:
            print(f"⚠️ 章节标题翻译失败: {e}")
            # 如果翻译失败，使用原标题作为中文标题
            for chapter in chapters_info:
                chapter['title_cn'] = chapter['title']
            return chapters_info
    
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
    
    def _save_statistics(self, statistics: Dict, output_dir: str) -> None:
        """保存统计信息到文件"""
        output_file = os.path.join(output_dir, OUTPUT_FILES['statistics'])
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(statistics, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 统计信息已保存到: {output_file}")
            
        except Exception as e:
            print(f"❌ 保存统计信息失败: {e}")
            raise