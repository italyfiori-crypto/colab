#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析服务 - 专门处理字幕语言学分析
统计功能已独立到StatisticsService
"""

import os
import json
import re
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
            json_file = os.path.join(analysis_dir, f"{subtitle_name}.jsonl")
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
            
            system_prompt = """作为英语语言学家，请分析用户输入的英语句子，严格按以下标记格式输出语言学分析。

使用以下标记分隔各个段落，每个标记独占一行，内容紧随其后：

[SENTENCE_STRUCTURE]
句法成分分析（主语+谓语+宾语+状语等）

[STRUCTURE_EXPLANATION]  
句子结构的语法解释（时态、语态、句式等重要语法现象）

[KEY_WORDS]
核心词汇，每行一个，格式：单词|词性|含义|音标
排除the、a、is、Mrs.等常见词

[FIXED_PHRASES]
固定短语，每行一个，格式：短语|含义
排除过于简单的组合

[COLLOQUIAL_EXPRESSION]
正式与口语表达对比，每行一组，格式：正式表达|口语表达|用法说明

示例1:
输入: "The project that we've been working on for months will be completed soon."
输出:
[SENTENCE_STRUCTURE]
主语(The project) + 定语从句(that we've been working on for months) + 谓语(will be completed) + 时间状语(soon)

[STRUCTURE_EXPLANATION]
定语从句修饰主语，'that'引导限制性定语从句；主句使用一般将来时的被动语态

[KEY_WORDS]
project|n.|项目|/ˈprɑːdʒekt/
completed|v.|完成|/kəmˈpliːtɪd/

[FIXED_PHRASES]
work on|从事，致力于

[COLLOQUIAL_EXPRESSION]
will be completed soon|will be done soon|口语中用'done'替代'completed'更简洁

示例2:
输入: "She said hello to me."
输出:
[SENTENCE_STRUCTURE]
主语(She) + 谓语(said) + 宾语(hello) + 介词短语(to me)

[STRUCTURE_EXPLANATION]
一般过去时，动词say的过去式said，表示过去发生的动作

[KEY_WORDS]
said|v.|说，讲|/sed/

[FIXED_PHRASES]

[COLLOQUIAL_EXPRESSION]
She said hello to me|She said hi to me|口语中常用'hi'代替'hello'更简洁

注意事项:
1. 严格按标记格式输出，每个标记必须独占一行
2. 无相关内容时该段落留空，但标记必须保留
3. 数组字段每行一项，用|分隔各个属性
4. 不要添加任何解释性文字，只输出标记格式内容"""
            
            user_prompt = f"请分析以下英语句子: \"{english_text}\""""
            
            # 使用AIClient的chat_completion方法
            response = self.ai_client.chat_completion(user_prompt, system_prompt, temperature=0.2, max_tokens=5000)
            if not response:
                return None
            
            # 解析结构化响应
            try:
                # 使用新的结构化解析方法
                analysis_data = self._parse_structured_response(response)
                if not analysis_data:
                    print(f"⚠️ 无法解析响应内容: {response[:100]}...")
                    return None
                
                result = {
                    "subtitle_index": entry['index'],
                    "timestamp": entry['timestamp'],
                    "english_text": english_text,
                    "chinese_text": chinese_text,
                    "sentence_structure": analysis_data.get("sentence_structure", ""),
                    "key_words": analysis_data.get("key_words", []),
                    "fixed_phrases": analysis_data.get("fixed_phrases", []),
                    "structure_explanation": analysis_data.get("structure_explanation", ""),
                    "colloquial_expression": analysis_data.get("colloquial_expression", [])
                }
                
                return result
                
            except Exception as e:
                print(f"⚠️ 响应解析失败: {e}")
                print(f"⚠️ 原始响应: {response[:200]}...")
                return None
                
        except Exception as e:
            print(f"❌ 分析字幕条目失败: {e}")
            return None
    
    def _parse_structured_response(self, response: str) -> Dict:
        """
        从AI响应中解析结构化标记内容
        
        Args:
            response: AI返回的原始响应
            
        Returns:
            解析的结构化数据字典
        """
        if not response:
            return {}
        
        # 初始化结果
        result = {
            "sentence_structure": "",
            "structure_explanation": "",
            "key_words": [],
            "fixed_phrases": [],
            "colloquial_expression": []
        }
        
        try:
            # 使用正则表达式提取各个段落
            
            # 提取句子结构
            structure_match = re.search(r'\[SENTENCE_STRUCTURE\]\s*(.*?)(?=\[|$)', response, re.DOTALL)
            if structure_match:
                result["sentence_structure"] = structure_match.group(1).strip()
            
            # 提取结构解释
            explanation_match = re.search(r'\[STRUCTURE_EXPLANATION\]\s*(.*?)(?=\[|$)', response, re.DOTALL)
            if explanation_match:
                result["structure_explanation"] = explanation_match.group(1).strip()
            
            # 提取关键词
            keywords_match = re.search(r'\[KEY_WORDS\]\s*(.*?)(?=\[|$)', response, re.DOTALL)
            if keywords_match:
                keywords_text = keywords_match.group(1).strip()
                for line in keywords_text.split('\n'):
                    line = line.strip()
                    if line and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            word_dict = {
                                "word": parts[0].strip(),
                                "pos": parts[1].strip(),
                                "meaning": parts[2].strip()
                            }
                            # 可选的音标
                            if len(parts) >= 4:
                                word_dict["pronunciation"] = parts[3].strip()
                            result["key_words"].append(word_dict)
            
            # 提取固定短语
            phrases_match = re.search(r'\[FIXED_PHRASES\]\s*(.*?)(?=\[|$)', response, re.DOTALL)
            if phrases_match:
                phrases_text = phrases_match.group(1).strip()
                for line in phrases_text.split('\n'):
                    line = line.strip()
                    if line and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            phrase_dict = {
                                "phrase": parts[0].strip(),
                                "meaning": parts[1].strip()
                            }
                            result["fixed_phrases"].append(phrase_dict)
            
            # 提取口语表达
            colloquial_match = re.search(r'\[COLLOQUIAL_EXPRESSION\]\s*(.*?)(?=\[|$)', response, re.DOTALL)
            if colloquial_match:
                colloquial_text = colloquial_match.group(1).strip()
                for line in colloquial_text.split('\n'):
                    line = line.strip()
                    if line and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            expression_dict = {
                                "formal": parts[0].strip(),
                                "informal": parts[1].strip(),
                                "explanation": parts[2].strip()
                            }
                            result["colloquial_expression"].append(expression_dict)
            
            return result
            
        except Exception as e:
            print(f"⚠️ 解析结构化响应失败: {e}")
            return result
    
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
            json_file = os.path.join(analysis_dir, f"{subtitle_name}.jsonl")
            
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