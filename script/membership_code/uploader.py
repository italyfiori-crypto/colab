#!/usr/bin/env python3
"""
会员码上传器
批量上传生成的会员码到微信云数据库

使用方式:
python membership_code_uploader.py --file membership_codes_1Y_20231201.csv
python membership_code_uploader.py --file membership_codes_LT_20231201.csv --batch-size 50
"""

import argparse
import csv
import os
import sys
import logging
import time
from typing import List, Dict
from datetime import datetime

# 导入微信云API
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(current_dir), 'upload'))

from wechat_api import WeChatCloudAPI


class MembershipCodeUploader:
    """会员码上传器"""
    
    def __init__(self, app_id: str, app_secret: str, env_id: str):
        self.api = WeChatCloudAPI(app_id, app_secret, env_id)
        self.collection_name = "membership_codes"
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
    
    def read_csv_file(self, file_path: str) -> List[Dict]:
        """读取CSV文件中的会员码数据"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV文件不存在: {file_path}")
        
        codes = []
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                required_fields = ['_id', 'code_type', 'use_status', 'active', 'created_at']
                if not all(field in reader.fieldnames for field in required_fields):
                    raise ValueError(f"CSV文件缺少必要字段，需要: {required_fields}")
                
                for row_num, row in enumerate(reader, 1):
                    # 验证必要字段
                    if not row['_id'] or not row['code_type']:
                        self.logger.warning(f"第{row_num}行数据不完整，跳过: {row}")
                        continue
                    
                    # 转换数据类型
                    code_data = {
                        '_id': row['_id'].strip(),
                        'code_type': row['code_type'].strip(),
                        'use_status': row['use_status'].strip() or 'unused',
                        'active': row['active'].lower().strip() in ('true', '1', 'yes'),
                        'used_at': None,
                        'used_by': None,
                        'created_at': int(row['created_at']) if row['created_at'] else int(time.time() * 1000),
                        'updated_at': int(time.time() * 1000)
                    }
                    
                    codes.append(code_data)
            
            self.logger.info(f"从CSV文件读取到 {len(codes)} 个会员码")
            return codes
            
        except Exception as e:
            raise RuntimeError(f"读取CSV文件失败: {e}")
    
    def check_existing_codes(self, codes: List[Dict]) -> tuple[List[Dict], List[str]]:
        """检查数据库中已存在的会员码"""
        code_ids = [code['_id'] for code in codes]
        existing_codes = []
        
        self.logger.info("检查数据库中已存在的会员码...")
        
        # 使用IN语法进行批量查询，避免单个查询循环
        batch_size = 50  # 微信云数据库IN查询建议不超过50个
        for i in range(0, len(code_ids), batch_size):
            batch_ids = code_ids[i:i + batch_size]
            
            # 使用$in操作符进行批量查询
            query_filter = {'_id': {'$in': batch_ids}}
            existing_records = self.api.query_database(
                self.collection_name,
                query_filter,
                limit=batch_size
            )
            
            # 提取已存在的会员码ID
            for record in existing_records:
                if '_id' in record:
                    existing_codes.append(record['_id'])
        
        # 过滤出需要插入的新会员码
        new_codes = [code for code in codes if code['_id'] not in existing_codes]
        
        self.logger.info(f"数据库中已存在 {len(existing_codes)} 个会员码")
        self.logger.info(f"需要插入 {len(new_codes)} 个新会员码")
        
        return new_codes, existing_codes
    
    def upload_codes_batch(self, codes: List[Dict], batch_size: int = 20) -> Dict:
        """批量上传会员码到数据库"""
        stats = {
            'total': len(codes),
            'uploaded': 0,
            'failed': 0,
            'batches': 0
        }
        
        if not codes:
            self.logger.info("没有需要上传的会员码")
            return stats
        
        # 分批上传
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            stats['batches'] += 1
            
            self.logger.info(f"上传第 {stats['batches']} 批，包含 {len(batch)} 个会员码...")
            
            try:
                success = self.api.add_database_records(self.collection_name, batch)
                if success:
                    stats['uploaded'] += len(batch)
                    self.logger.info(f"✅ 第 {stats['batches']} 批上传成功")
                else:
                    stats['failed'] += len(batch)
                    self.logger.error(f"❌ 第 {stats['batches']} 批上传失败")
                
                # 上传间隔，避免频率过高
                if i + batch_size < len(codes):
                    time.sleep(1)
                    
            except Exception as e:
                stats['failed'] += len(batch)
                self.logger.error(f"❌ 第 {stats['batches']} 批上传异常: {e}")
        
        return stats
    
    def upload_from_csv(self, file_path: str, batch_size: int = 20, skip_existing: bool = True) -> Dict:
        """从CSV文件上传会员码"""
        try:
            # 读取CSV文件
            codes = self.read_csv_file(file_path)
            
            if skip_existing:
                # 检查已存在的会员码
                codes, existing_codes = self.check_existing_codes(codes)
            else:
                existing_codes = []
            
            # 批量上传
            stats = self.upload_codes_batch(codes, batch_size)
            stats['existing'] = len(existing_codes)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"上传失败: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='会员码上传器')
    parser.add_argument('file', type=str, help='CSV文件路径')
    parser.add_argument('--batch-size', type=int, default=100, help='批次大小 (默认: 100)')
    parser.add_argument('--force', action='store_true', help='强制上传，不跳过已存在的记录')
    
    args = parser.parse_args()
    
    # 检查环境变量
    app_id = input("请输入AppID (默认: wx7040936883aa6dad): ").strip() or "wx7040936883aa6dad"
    app_secret = input("请输入AppSecret: ").strip() or "94051e8239a7a5181f32695c3c4895d9"
    env_id = input("请输入云环境ID: ").strip() or "cloud1-1gpp78j208f0f610"
    
    if not all([app_id, app_secret, env_id]):
        print("❌ 缺少必要的环境变量:")
        print("   WECHAT_APP_ID")
        print("   WECHAT_APP_SECRET") 
        print("   WECHAT_ENV_ID")
        return 1
    
    try:
        uploader = MembershipCodeUploader(app_id, app_secret, env_id)
        
        print(f"🚀 开始上传会员码: {args.file}")
        print(f"📦 批次大小: {args.batch_size}")
        print(f"🔄 跳过已存在: {'否' if args.force else '是'}")
        
        # 上传会员码
        stats = uploader.upload_from_csv(
            args.file,
            batch_size=args.batch_size,
            skip_existing=not args.force
        )
        
        # 显示结果
        print("\n" + "="*50)
        print("📊 上传结果统计:")
        print(f"   总计数量: {stats['total']}")
        print(f"   成功上传: {stats['uploaded']}")
        print(f"   上传失败: {stats['failed']}")
        print(f"   已存在: {stats.get('existing', 0)}")
        print(f"   批次数量: {stats['batches']}")
        
        success_rate = (stats['uploaded'] / stats['total']) * 100 if stats['total'] > 0 else 0
        print(f"   成功率: {success_rate:.1f}%")
        
        if stats['failed'] > 0:
            print("\n⚠️  部分会员码上传失败，请检查日志和网络连接")
            return 1
        else:
            print("\n✅ 所有会员码上传成功！")
            return 0
            
    except Exception as e:
        print(f"\n❌ 上传过程出错: {e}")
        return 1


if __name__ == "__main__":
    exit(main())