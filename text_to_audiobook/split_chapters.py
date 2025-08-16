#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节拆分主程序 - 精简版
支持配置文件和最少的命令行参数
"""

import argparse
import sys
import os
from pathlib import Path

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.chapter_splitter import ChapterSplitter, ChapterDetectionConfig


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='章节拆分工具 - 将书籍文本拆分为独立的章节文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s data/greens.txt
  %(prog)s data/book.txt --output-dir ./my_output
  %(prog)s data/book.txt --config my_config.json
  
默认配置文件: text_to_audiobook/config.json
默认输出目录: ./output
输出格式: {filename}_chapters/ 目录下的章节文件
        """
    )
    
    # 核心参数
    parser.add_argument('input_file',help='输入文本文件路径')
    parser.add_argument('--output-dir', default='./output', help='输出目录路径 (默认: ./output)')
    parser.add_argument('--config', default='text_to_audiobook/config.json', help='配置文件路径 (默认: text_to_audiobook/config.json)')
    parser.add_argument('--verbose','-v',action='store_true',help='显示详细信息')
    
    args = parser.parse_args()
    
    # 验证输入文件
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}")
        return 1
    
    # 创建输出目录
    output_dir = args.output_dir
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"错误: 无法创建输出目录: {e}")
        return 1
    
    try:
        # 加载配置
        config_path = Path(args.config)
        if not os.path.exists(config_path):
            print(f"错误: 配置文件不存在: {config_path}")
            return 1
        
        config = ChapterDetectionConfig.from_json_file(config_path)
        if args.verbose:
            print(f"已加载配置文件: {config_path}")
        
        
        # 创建拆分器并执行拆分
        splitter = ChapterSplitter(config)
        output_files = splitter.split_book(args.input_file,output_dir)
        
        print(f"\n✅ 拆分完成! 共生成 {len(output_files)} 个章节文件")
        
        if args.verbose:
            # 从第一个输出文件获取实际输出目录
            if output_files:
                actual_output_dir = os.path.dirname(output_files[0])
                print(f"\n输出目录: {actual_output_dir}")
            print("生成的文件:")
            for file_path in output_files:
                print(f"  - {os.path.basename(file_path)}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 拆分失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())