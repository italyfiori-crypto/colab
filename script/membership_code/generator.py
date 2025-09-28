#!/usr/bin/env python3
"""
会员码生成器
生成包含类型和校验码的12位会员码，并导出为CSV文件

使用方式:
python membership_code_generator.py --type 1 --count 100
python membership_code_generator.py --type 99 --count 50

支持的类型:
1: 1年会员 (1Y前缀)
2: 2年会员 (2Y前缀) 
5: 5年会员 (5Y前缀)
99: 终身会员 (LT前缀)
"""

import argparse
import csv
import random
import string
import time
import os
import glob
from datetime import datetime
from typing import List, Set


class MembershipCodeGenerator:
    """会员码生成器"""
    
    # 类型前缀映射
    TYPE_PREFIXES = {
        1: "1Y",    # 1年
        2: "2Y",    # 2年  
        5: "5Y",    # 5年
        99: "LT"    # 终身(LifeTime)
    }
    
    # 可用字符集(排除易混淆字符: 0,1,O,I)
    CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    
    def __init__(self):
        self.generated_codes: Set[str] = set()
        # 初始化随机种子，提升随机性
        random.seed(int(time.time() * 1000) + os.getpid())
        # 加载已有的会员码进行去重
        self._load_existing_codes()
    
    def _generate_checksum(self, code: str) -> str:
        """生成2位校验码"""
        # 简单校验算法: 对字符ASCII值求和取模
        checksum = sum(ord(c) for c in code) % len(self.CHARSET)
        return self.CHARSET[checksum] + self.CHARSET[(checksum * 7) % len(self.CHARSET)]
    
    def _generate_single_code(self, code_type: int) -> str:
        """生成单个会员码"""
        if code_type not in self.TYPE_PREFIXES:
            raise ValueError(f"不支持的会员码类型: {code_type}")
        
        max_attempts = 1000
        attempts = 0
        
        while attempts < max_attempts:
            # 生成类型前缀 (2位)
            prefix = self.TYPE_PREFIXES[code_type]
            
            # 生成随机字符 (8位) - 优化随机性
            # 使用更好的随机分布，避免连续重复字符
            random_chars = ''
            for _ in range(8):
                # 确保不与前一个字符相同
                available_chars = self.CHARSET
                if random_chars:
                    available_chars = [c for c in self.CHARSET if c != random_chars[-1]]
                random_chars += random.choice(available_chars)
            
            # 计算校验码 (2位)
            base_code = prefix + random_chars
            checksum = self._generate_checksum(base_code)
            
            # 组合完整会员码
            full_code = base_code + checksum
            
            # 检查重复
            if full_code not in self.generated_codes:
                self.generated_codes.add(full_code)
                return full_code
            
            attempts += 1
        
        raise RuntimeError(f"生成会员码失败，尝试了{max_attempts}次仍有重复")
    
    def generate_codes(self, code_type: int, count: int) -> List[dict]:
        """批量生成会员码"""
        if count <= 0:
            raise ValueError("生成数量必须大于0")
        
        codes = []
        current_time = int(time.time() * 1000)
        
        print(f"开始生成 {count} 个 {self.TYPE_PREFIXES[code_type]} 类型会员码...")
        
        for i in range(count):
            code = self._generate_single_code(code_type)
            codes.append({
                '_id': code,
                'code_type': str(code_type),
                'use_status': 'unused',
                'active': True,
                'used_at': None,
                'used_by': None,
                'created_at': current_time,
                'updated_at': current_time
            })
            
            # 显示进度
            if (i + 1) % 50 == 0 or i == count - 1:
                print(f"已生成 {i + 1}/{count} 个会员码")
        
        return codes
    
    def save_to_csv(self, codes: List[dict], code_type: int) -> str:
        """保存会员码到CSV文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        type_name = self.TYPE_PREFIXES[code_type]
        
        # 确保data目录存在
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        filename = f"membership_codes_{type_name}_{timestamp}.csv"
        filepath = os.path.join(data_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['_id', 'code_type', 'use_status', 'active', 'created_at']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for code in codes:
                # 只保存需要的字段到CSV
                csv_row = {
                    '_id': code['_id'],
                    'code_type': code['code_type'], 
                    'use_status': code['use_status'],
                    'active': code['active'],
                    'created_at': code['created_at']
                }
                writer.writerow(csv_row)
        
        return filepath
    
    def validate_code(self, code: str) -> dict:
        """验证会员码格式和校验码"""
        result = {
            'valid': False,
            'code_type': None,
            'error': None
        }
        
        # 检查长度
        if len(code) != 12:
            result['error'] = f"会员码长度错误，应为12位，实际为{len(code)}位"
            return result
        
        # 检查字符集
        if not all(c in self.CHARSET for c in code[2:]):
            result['error'] = "会员码包含无效字符"
            return result
        
        # 提取前缀和类型
        prefix = code[:2]
        code_type = None
        for type_num, type_prefix in self.TYPE_PREFIXES.items():
            if prefix == type_prefix:
                code_type = type_num
                break
        
        if code_type is None:
            result['error'] = f"无效的类型前缀: {prefix}"
            return result
        
        # 验证校验码
        base_code = code[:10]
        expected_checksum = self._generate_checksum(base_code)
        actual_checksum = code[10:]
        
        if expected_checksum != actual_checksum:
            result['error'] = f"校验码错误，期望: {expected_checksum}，实际: {actual_checksum}"
            return result
        
        result['valid'] = True
        result['code_type'] = code_type
        return result
    
    def _load_existing_codes(self):
        """加载data目录下所有CSV文件中的已有会员码"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        if not os.path.exists(data_dir):
            return
        
        csv_files = glob.glob(os.path.join(data_dir, '*.csv'))
        loaded_count = 0
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if '_id' in row and row['_id']:
                            self.generated_codes.add(row['_id'].strip())
                            loaded_count += 1
            except Exception as e:
                print(f"警告: 无法读取文件 {csv_file}: {e}")
        
        if loaded_count > 0:
            print(f"已加载 {loaded_count} 个已有会员码用于去重检查")


def main():
    parser = argparse.ArgumentParser(description='会员码生成器')
    parser.add_argument('--type', type=int, required=True,
                        choices=[1, 2, 5, 99],
                        help='会员码类型: 1(1年) 2(2年) 5(5年) 99(终身)')
    parser.add_argument('--count', type=int, required=True,
                        help='生成数量')
    parser.add_argument('--validate', type=str,
                        help='验证指定的会员码格式')
    
    args = parser.parse_args()
    
    generator = MembershipCodeGenerator()
    
    # 如果是验证模式
    if args.validate:
        result = generator.validate_code(args.validate)
        if result['valid']:
            type_name = generator.TYPE_PREFIXES[result['code_type']]
            print(f"✅ 会员码有效: {args.validate}")
            print(f"   类型: {type_name} ({result['code_type']})")
        else:
            print(f"❌ 会员码无效: {result['error']}")
        return
    
    # 生成模式
    try:
        # 生成会员码
        codes = generator.generate_codes(args.type, args.count)
        
        # 保存到CSV
        filename = generator.save_to_csv(codes, args.type)
        
        type_name = generator.TYPE_PREFIXES[args.type]
        print(f"\n✅ 成功生成 {args.count} 个 {type_name} 类型会员码")
        print(f"📄 已保存到文件: {filename}")
        print(f"🔍 示例会员码: {codes[0]['_id']}")
        
        # 验证生成的第一个码
        validation = generator.validate_code(codes[0]['_id'])
        if validation['valid']:
            print("✅ 格式验证通过")
        else:
            print(f"❌ 格式验证失败: {validation['error']}")
            
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())