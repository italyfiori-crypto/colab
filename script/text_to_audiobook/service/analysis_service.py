#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析服务 - 专门处理字幕语言学分析
统计功能已独立到StatisticsService
"""

import os
import json
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from infra import AIClient, FileManager
from infra.config_loader import AppConfig
from util import OUTPUT_DIRECTORIES, parse_srt_file


class AnalysisService:
    """字幕语言学分析服务"""
    
    def __init__(self, config: AppConfig):
        """
        初始化分析服务
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.ai_client = AIClient(config.api)
        self.file_manager = FileManager()
    
    def analyze_subtitle_files(self, subtitle_files: List[str], output_dir: str) -> List[str]:
        """
        批量分析字幕文件，逐文件增量处理
        
        Args:
            subtitle_files: 字幕文件路径列表
            output_dir: 输出根目录
            
        Returns:
            成功分析的文件列表
        """
        if not subtitle_files:
            print("⚠️ 未找到字幕文件，跳过分析")
            return []
        
        # 创建分析结果目录
        analysis_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['parsed_analysis'])
        self.file_manager.create_directory(analysis_dir)
        
        print(f"🔍 开始逐文件分析 {len(subtitle_files)} 个字幕文件...")
        
        # 总体统计
        analyzed_files = []
        total_stats = {
            'entries_processed': 0,
            'entries_failed': 0,
            'files_completed': 0,
            'files_failed': 0,
            'files_skipped': 0
        }
        
        # 逐个文件处理
        for file_idx, subtitle_file in enumerate(subtitle_files, 1):
            print(f"\n📄 [{file_idx}/{len(subtitle_files)}] 处理文件: {os.path.basename(subtitle_file)}")
            
            try:
                file_stats = self._process_single_file(subtitle_file, analysis_dir)
                
                if file_stats['success']:
                    analyzed_files.append(subtitle_file)
                    total_stats['files_completed'] += 1
                else:
                    total_stats['files_failed'] += 1
                    
                # 累计条目统计
                total_stats['entries_processed'] += file_stats['entries_processed']
                total_stats['entries_failed'] += file_stats['entries_failed']
                total_stats['files_skipped'] += file_stats.get('skipped', 0)
                
            except Exception as e:
                print(f"    ❌ 处理文件异常: {e}")
                total_stats['files_failed'] += 1
        
        # 输出最终统计
        print(f"\n📊 分析完成统计:")
        print(f"   📁 成功文件: {total_stats['files_completed']}/{len(subtitle_files)}")
        print(f"   📄 处理字幕条目: {total_stats['entries_processed']}")
        print(f"   ❌ 失败字幕条目: {total_stats['entries_failed']}")
        if total_stats['files_skipped'] > 0:
            print(f"   ⏭️  跳过已处理: {total_stats['files_skipped']} 个文件")
        
        return analyzed_files
    
    def _process_single_file(self, subtitle_file: str, analysis_dir: str) -> Dict:
        """
        处理单个字幕文件
        
        Args:
            subtitle_file: 字幕文件路径
            analysis_dir: 分析结果目录
            
        Returns:
            处理结果统计字典
        """
        file_stats = {
            'success': False,
            'entries_processed': 0,
            'entries_failed': 0,
            'skipped': 0
        }
        
        try:
            # 1. 解析字幕文件
            subtitle_entries = self._parse_srt_file(subtitle_file)
            if not subtitle_entries:
                print(f"    ⚠️ 文件无有效字幕，跳过")
                return file_stats
            
            # 2. 加载已有分析结果
            subtitle_name = self.file_manager.get_basename_without_extension(subtitle_file)
            json_file = os.path.join(analysis_dir, f"{subtitle_name}.json")
            existing_results = self._load_existing_results(json_file)
            
            # 3. 识别需要处理的字幕条目
            missing_subtitles = self._get_missing_subtitles(subtitle_entries, existing_results)
            
            if not missing_subtitles:
                print(f"    ✅ 所有字幕已处理完毕，跳过 ({len(subtitle_entries)} 条)")
                file_stats['skipped'] = 1
                file_stats['success'] = True
                return file_stats
            
            print(f"    🔍 需要处理 {len(missing_subtitles)}/{len(subtitle_entries)} 条字幕")
            
            # 4. 并发分析缺失的字幕条目
            new_results = []
            max_workers = min(len(missing_subtitles), self.config.api.max_concurrent_workers)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交分析任务
                future_to_entry = {
                    executor.submit(self._analyze_subtitle_entry, entry): entry
                    for entry in missing_subtitles
                }
                
                # 收集结果
                for future in as_completed(future_to_entry):
                    entry = future_to_entry[future]
                    try:
                        result = future.result()
                        if result:
                            new_results.append(result)
                            file_stats['entries_processed'] += 1
                        else:
                            file_stats['entries_failed'] += 1
                            
                        # 显示进度
                        completed = file_stats['entries_processed'] + file_stats['entries_failed']
                        if completed % 5 == 0 or completed == len(missing_subtitles):
                            print(f"      📊 进度: {completed}/{len(missing_subtitles)} 条")
                            
                    except Exception as e:
                        print(f"      ❌ 分析字幕 {entry.get('index', '?')} 出错: {e}")
                        file_stats['entries_failed'] += 1
            
            # 5. 保存合并结果
            if new_results or existing_results:
                success = self._save_analysis_results(new_results, existing_results, subtitle_file, analysis_dir)
                if success:
                    file_stats['success'] = True
                    print(f"    ✅ 文件处理完成")
                else:
                    print(f"    ❌ 保存失败")
            else:
                print(f"    ⚠️ 无有效分析结果")
                
        except Exception as e:
            print(f"    ❌ 文件处理失败: {e}")
            
        return file_stats
    
    
    def _analyze_subtitle_entry(self, entry: Dict) -> Optional[Dict]:
        """
        分析单个字幕条目的语言学特征
        
        Args:
            entry: 字幕条目
            
        Returns:
            分析结果或None
        """
        try:
            english_text = entry['english_text']
            chinese_text = entry.get('chinese_text', '')
            
            system_prompt = """IMPORTANT: 只返回JSON格式，不要任何额外文字或解释。

作为英语语言学家，请分析用户输入的英语句子，并严格按以下JSON格式输出语言学分析。

字段要求:
- sentence_structure: 句法成分分析（主语+谓语+宾语+状语等）
- key_words: 句子中有意义的核心词汇，排除the、a、is、Mrs.等常见词
- fixed_phrases: 有固定含义的短语搭配，排除过于简单的组合
- core_grammar: 重要语法现象（时态、语态、句式等）
- colloquial_expression: 正式与口语表达对比

输出格式:
{
  "sentence_structure": "句子结构分析",
  "key_words": [{"word": "单词", "pos": "词性", "meaning": "含义", "pronunciation": "音标"}],
  "fixed_phrases": [{"phrase": "短语", "meaning": "含义"}],
  "core_grammar": [{"point": "语法点", "explanation": "解释"}],
  "colloquial_expression": [{"formal": "正式表达", "informal": "口语表达", "explanation": "用法说明"}]
}

示例1:
输入: "The project that we've been working on for months, which involves multiple stakeholders, will be completed once we receive the final approval."
输出:
{
  "sentence_structure": "主语(The project) + 定语从句1(that we've been working on for months) + 定语从句2(which involves multiple stakeholders) + 谓语(will be completed) + 时间状语从句(once we receive the final approval)",
  "key_words": [{"word": "stakeholders", "pos": "n.", "meaning": "利益相关者", "pronunciation": "/ˈsteɪkhoʊldərz/"}, {"word": "approval", "pos": "n.", "meaning": "批准，同意", "pronunciation": "/əˈpruːvəl/"}],
  "fixed_phrases": [{"phrase": "work on", "meaning": "从事，致力于"}],
  "core_grammar": [{"point": "定语从句嵌套", "explanation": "两个定语从句修饰同一主语，'that'引导限制性定语从句，'which'引导非限制性定语从句"}],
  "colloquial_expression": [{"formal": "receive the final approval", "informal": "get the green light", "explanation": "'get the green light'表示获得许可，比'receive approval'更生动"}]
}

示例2:
输入: "I visited the museum yesterday."
输出:
{
  "sentence_structure": "主语(I) + 谓语(visited) + 宾语(the museum) + 时间状语(yesterday)",
  "key_words": [{"word": "museum", "pos": "n.", "meaning": "博物馆", "pronunciation": "/mjuˈziːəm/"}, {"word": "visited", "pos": "v.", "meaning": "参观，拜访", "pronunciation": "/ˈvɪzɪtɪd/"}],
  "fixed_phrases": [],
  "core_grammar": [{"point": "一般过去时", "explanation": "动词visit的过去式visited，表示过去发生的动作"}],
  "colloquial_expression": [{"formal": "I went to see the museum yesterday.", "informal": "I checked out the museum yesterday.", "explanation": "口语中常用check out代替visit，语气更随意"}]
}

注意: 无相关内容时字段留空(空数组[]或空字符串"")，但不可省略字段。记住：仅输出JSON格式。"""
            
            user_prompt = f"请分析以下英语句子: \"{english_text}\""""
            
            # 使用AIClient的chat_completion方法
            response = self.ai_client.chat_completion(user_prompt, system_prompt, temperature=0.2, max_tokens=1500)
            if not response:
                return None
            
            # 解析JSON响应
            try:
                # 智能提取JSON内容
                json_str = self._extract_json_from_response(response)
                if not json_str:
                    print(f"⚠️ 无法从响应中提取JSON: {response[:100]}...")
                    return None
                
                analysis_data = json.loads(json_str)
                
                result = {
                    "subtitle_index": entry['index'],
                    "timestamp": entry['timestamp'],
                    "english_text": english_text,
                    "chinese_text": chinese_text,
                    "sentence_structure": analysis_data.get("sentence_structure", ""),
                    "key_words": analysis_data.get("key_words", []),
                    "fixed_phrases": analysis_data.get("fixed_phrases", []),
                    "core_grammar": analysis_data.get("core_grammar", []),
                    "colloquial_expression": analysis_data.get("colloquial_expression", [])
                }
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON解析失败: {e}")
                print(f"⚠️ 原始响应: {response[:200]}...")
                return None
                
        except Exception as e:
            print(f"❌ 分析字幕条目失败: {e}")
            return None
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        从AI响应中智能提取JSON内容
        
        Args:
            response: AI返回的原始响应
            
        Returns:
            提取的JSON字符串，失败返回空字符串
        """
        if not response:
            return ""
        
        # 清理响应内容
        response = response.strip()
        
        # 1. 尝试移除代码块标记
        if response.startswith('```json'):
            response = response[7:]  # 移除 ```json
        if response.startswith('```'):
            response = response[3:]  # 移除 ```
        if response.endswith('```'):
            response = response[:-3]  # 移除结尾的 ```
        
        response = response.strip()
        
        # 2. 寻找第一个{和最后一个}
        first_brace = response.find('{')
        last_brace = response.rfind('}')
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_str = response[first_brace:last_brace + 1]
            return json_str
        
        # 3. 如果已经是完整JSON格式，直接返回
        if response.startswith('{') and response.endswith('}'):
            return response
        
        return ""
    
    def _save_analysis_results(self, new_results: List[Dict], existing_results: Dict[str, Dict], 
                               subtitle_file: str, analysis_dir: str) -> bool:
        """
        合并新旧分析结果并保存到JSONL文件
        
        Args:
            new_results: 新分析的结果列表
            existing_results: 已存在的结果字典
            subtitle_file: 字幕文件路径
            analysis_dir: 分析结果目录
            
        Returns:
            保存是否成功
        """
        try:
            subtitle_name = self.file_manager.get_basename_without_extension(subtitle_file)
            json_file = os.path.join(analysis_dir, f"{subtitle_name}.json")
            
            # 合并新旧结果
            all_results = dict(existing_results)  # 复制已有结果
            
            # 添加新结果，覆盖已有的相同序号
            for result in new_results:
                subtitle_index = str(result.get('subtitle_index', ''))
                if subtitle_index:
                    # 为每个字幕条目添加源文件信息
                    result_with_source = {
                        "source_file": os.path.basename(subtitle_file),
                        **result
                    }
                    all_results[subtitle_index] = result_with_source
            
            # 按字幕序号排序（数值排序）
            sorted_results = sorted(all_results.values(), 
                                  key=lambda x: int(x.get('subtitle_index', '0')) if str(x.get('subtitle_index', '0')).isdigit() else 0)
            
            # 保存为JSONL格式：每行一个字幕条目的解析JSON
            with open(json_file, 'w', encoding='utf-8') as f:
                for result in sorted_results:
                    f.write(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
            
            total_count = len(sorted_results)
            new_count = len(new_results)
            print(f"    ✅ 分析结果已保存: {json_file} (新增{new_count}条，总计{total_count}条)")
            return True
            
        except Exception as e:
            print(f"    ❌ 保存分析结果失败: {e}")
            return False
    
    
    def _load_existing_results(self, json_file: str) -> Dict[str, Dict]:
        """
        加载已存在的分析结果
        
        Args:
            json_file: JSON文件路径
            
        Returns:
            已存在的分析结果字典，键为subtitle_index，值为分析结果
        """
        existing_results = {}
        
        if not os.path.exists(json_file):
            return existing_results
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        result = json.loads(line)
                        subtitle_index = str(result.get('subtitle_index', ''))
                        if subtitle_index:
                            existing_results[subtitle_index] = result
                    except json.JSONDecodeError as e:
                        print(f"⚠️ 解析JSON行 {line_num} 失败: {e}")
                        continue
                        
        except Exception as e:
            print(f"⚠️ 读取已有结果文件失败 {json_file}: {e}")
            
        return existing_results
    
    def _get_missing_subtitles(self, all_subtitles: List[Dict], existing_results: Dict[str, Dict]) -> List[Dict]:
        """
        识别需要处理的字幕条目
        
        Args:
            all_subtitles: 所有字幕条目列表
            existing_results: 已存在的分析结果字典
            
        Returns:
            需要处理的字幕条目列表
        """
        missing_subtitles = []
        
        for subtitle in all_subtitles:
            subtitle_index = str(subtitle.get('index', ''))
            if subtitle_index not in existing_results:
                missing_subtitles.append(subtitle)
                
        return missing_subtitles
    
    def _parse_srt_file(self, subtitle_file: str) -> List[Dict]:
        """解析SRT字幕文件 - 使用统一的解析工具"""
        return parse_srt_file(subtitle_file)