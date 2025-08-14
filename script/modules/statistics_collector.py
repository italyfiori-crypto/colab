#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计信息收集模块
收集和计算有声书生成过程中的各类统计信息
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class StatisticsCollector:
    """统计信息收集器"""
    
    def __init__(self, book_title_en: str = "", book_title_zh: str = "", author: str = ""):
        """
        初始化统计收集器
        
        Args:
            book_title_en: 英文书籍标题
            book_title_zh: 中文书籍标题
            author: 作者
        """
        self.book_title_en = book_title_en
        self.book_title_zh = book_title_zh
        self.book_title = book_title_en  # 保持向后兼容
        self.author = author
        self.chapters_stats = []
        self.start_time = datetime.now()
        
        # 阅读速度常量（词/分钟）
        self.reading_speed_wpm = 250
    
    def add_chapter_stats(self, chapter_number: int, chapter_title_en: str, 
                         chapter_title_zh: str, text: str, subtitle_count: int, 
                         segments_count: int, audio_duration: float) -> Dict[str, Any]:
        """
        添加章节统计信息
        
        Args:
            chapter_number: 章节编号
            chapter_title_en: 英文章节标题
            chapter_title_zh: 中文章节标题
            text: 章节文本内容
            subtitle_count: 字幕条目数
            segments_count: 音频段数
            audio_duration: 音频时长（秒）
            
        Returns:
            章节统计信息字典
        """
        # 计算文本统计
        character_count = len(text)
        word_count = len(text.split())
        
        # 计算预计阅读时间
        reading_time_minutes = word_count / self.reading_speed_wpm
        
        # 格式化音频时长
        audio_duration_formatted = self._format_duration(audio_duration)
        
        # 创建章节统计
        chapter_stats = {
            "chapter_number": chapter_number,
            "chapter_title_en": chapter_title_en,
            "chapter_title_zh": chapter_title_zh,
            "chapter_title": chapter_title_en,  # 保持向后兼容
            "subtitle_count": subtitle_count,
            "character_count": character_count,
            "word_count": word_count,
            "audio_duration_seconds": round(audio_duration, 2),
            "audio_duration_formatted": audio_duration_formatted,
            "estimated_reading_time_minutes": round(reading_time_minutes, 1),
            "segments_count": segments_count
        }
        
        self.chapters_stats.append(chapter_stats)
        return chapter_stats
    
    def get_book_stats(self) -> Dict[str, Any]:
        """
        获取整本书的统计信息
        
        Returns:
            整本书统计信息字典
        """
        if not self.chapters_stats:
            return {}
        
        # 汇总统计
        total_chapters = len(self.chapters_stats)
        total_subtitle_count = sum(ch["subtitle_count"] for ch in self.chapters_stats)
        total_character_count = sum(ch["character_count"] for ch in self.chapters_stats)
        total_word_count = sum(ch["word_count"] for ch in self.chapters_stats)
        total_audio_duration = sum(ch["audio_duration_seconds"] for ch in self.chapters_stats)
        total_reading_time = sum(ch["estimated_reading_time_minutes"] for ch in self.chapters_stats)
        total_segments = sum(ch["segments_count"] for ch in self.chapters_stats)
        
        # 计算平均值
        avg_chapter_duration = total_audio_duration / total_chapters
        avg_chapter_word_count = total_word_count / total_chapters
        avg_subtitle_per_chapter = total_subtitle_count / total_chapters
        
        return {
            "book_title_en": self.book_title_en,
            "book_title_zh": self.book_title_zh,
            "book_title": self.book_title,  # 保持向后兼容
            "author": self.author,
            "total_chapters": total_chapters,
            "total_subtitle_count": total_subtitle_count,
            "total_character_count": total_character_count,
            "total_word_count": total_word_count,
            "total_audio_duration_seconds": round(total_audio_duration, 2),
            "total_audio_duration_formatted": self._format_duration(total_audio_duration),
            "total_estimated_reading_time_minutes": round(total_reading_time, 1),
            "total_segments_count": total_segments,
            "average_chapter_duration_seconds": round(avg_chapter_duration, 2),
            "average_chapter_word_count": round(avg_chapter_word_count),
            "average_subtitle_per_chapter": round(avg_subtitle_per_chapter, 1),
            "processing_date": self.start_time.isoformat(),
            "processing_duration_seconds": round((datetime.now() - self.start_time).total_seconds(), 2)
        }
    
    def _format_duration(self, seconds: float) -> str:
        """
        格式化时长为 MM:SS 或 HH:MM:SS 格式
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时长字符串
        """
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def export_json(self, output_path: Path):
        """
        导出JSON格式的统计信息
        
        Args:
            output_path: 输出文件路径
        """
        metadata = {
            "book_statistics": self.get_book_stats(),
            "chapter_statistics": self.chapters_stats
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"统计信息已导出到: {output_path}")
    
    def export_markdown(self, output_path: Path):
        """
        导出Markdown格式的统计报告
        
        Args:
            output_path: 输出文件路径
        """
        book_stats = self.get_book_stats()
        
        if not book_stats:
            return
        
        content = []
        
        # 书籍标题
        if book_stats.get('book_title_zh') and book_stats.get('book_title_en'):
            content.append(f"# {book_stats['book_title_zh']} ({book_stats['book_title_en']})")
        elif book_stats.get('book_title_en'):
            content.append(f"# {book_stats['book_title_en']}")
        else:
            content.append("# 有声书统计报告")
        content.append("")
        
        # 作者信息
        if book_stats.get('author'):
            content.append(f"**作者**: {book_stats['author']}")
            content.append("")
        
        # 生成信息
        content.append("## 生成信息")
        content.append(f"- **生成时间**: {book_stats['processing_date']}")
        content.append(f"- **处理耗时**: {book_stats['processing_duration_seconds']} 秒")
        content.append("")
        
        # 整体统计
        content.append("## 整体统计")
        content.append(f"- **总章节数**: {book_stats['total_chapters']}")
        content.append(f"- **总字符数**: {book_stats['total_character_count']:,}")
        content.append(f"- **总单词数**: {book_stats['total_word_count']:,}")
        content.append(f"- **总字幕条目**: {book_stats['total_subtitle_count']}")
        content.append(f"- **总音频时长**: {book_stats['total_audio_duration_formatted']} ({book_stats['total_audio_duration_seconds']} 秒)")
        content.append(f"- **预计阅读时间**: {book_stats['total_estimated_reading_time_minutes']} 分钟")
        content.append(f"- **总音频段数**: {book_stats['total_segments_count']}")
        content.append("")
        
        # 平均统计
        content.append("## 平均统计")
        content.append(f"- **平均章节时长**: {self._format_duration(book_stats['average_chapter_duration_seconds'])}")
        content.append(f"- **平均章节字数**: {book_stats['average_chapter_word_count']}")
        content.append(f"- **平均章节字幕数**: {book_stats['average_subtitle_per_chapter']}")
        content.append("")
        
        # 章节详情
        content.append("## 章节详情")
        content.append("")
        content.append("| 章节 | 英文标题 | 中文标题 | 字数 | 字幕数 | 音频时长 | 预计阅读时间 |")
        content.append("|------|----------|----------|------|--------|----------|--------------|")
        
        for chapter in self.chapters_stats:
            en_title = chapter.get('chapter_title_en', chapter.get('chapter_title', ''))
            zh_title = chapter.get('chapter_title_zh', '')
            
            content.append(
                f"| {chapter['chapter_number']} | "
                f"{en_title} | "
                f"{zh_title} | "
                f"{chapter['word_count']} | "
                f"{chapter['subtitle_count']} | "
                f"{chapter['audio_duration_formatted']} | "
                f"{chapter['estimated_reading_time_minutes']} 分钟 |"
            )
        
        content.append("")
        
        # 技术信息
        content.append("## 技术信息")
        content.append("- **文本分割**: 使用 spaCy 智能分割")
        content.append("- **语音合成**: Kokoro TTS")
        content.append("- **字幕格式**: SRT")
        content.append(f"- **阅读速度基准**: {self.reading_speed_wpm} 词/分钟")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        print(f"统计报告已导出到: {output_path}")
    
    def print_summary(self):
        """打印统计摘要"""
        book_stats = self.get_book_stats()
        
        if not book_stats:
            print("暂无统计信息")
            return
        
        print("\n📊 有声书生成统计摘要")
        print("=" * 50)
        
        # 显示书名（优先显示双语）
        if book_stats.get('book_title_zh') and book_stats.get('book_title_en'):
            print(f"📖 书籍: {book_stats['book_title_zh']} ({book_stats['book_title_en']})")
        elif book_stats.get('book_title_en'):
            print(f"📖 书籍: {book_stats['book_title_en']}")
        else:
            print(f"📖 书籍: {book_stats.get('book_title', '未知')}")
            
        if book_stats.get('author'):
            print(f"✍️  作者: {book_stats['author']}")
            
        print(f"📚 章节数: {book_stats['total_chapters']}")
        print(f"📝 总字数: {book_stats['total_word_count']:,}")
        print(f"🎵 总时长: {book_stats['total_audio_duration_formatted']}")
        print(f"📋 字幕条目: {book_stats['total_subtitle_count']}")
        print(f"⏱️  预计阅读: {book_stats['total_estimated_reading_time_minutes']} 分钟")
        print(f"⚡ 处理耗时: {book_stats['processing_duration_seconds']} 秒")
        print("=" * 50)