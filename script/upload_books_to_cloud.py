#!/usr/bin/env python3
"""
微信云服务书籍数据上传脚本
用于将output目录下的有声书数据上传到微信云数据库和存储
"""

import os
import json
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class WeChatCloudUploader:
    """微信云服务上传器"""
    
    def __init__(self, app_id: str, app_secret: str, env_id: str, debug: bool = False):
        """
        初始化上传器
        
        Args:
            app_id: 微信小程序AppID
            app_secret: 微信小程序AppSecret
            env_id: 微信云环境ID
            debug: 是否开启调试模式
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.env_id = env_id
        self.debug = debug
        
        # Access Token相关
        self.access_token = None
        self.token_expires_at = None
        
        # API端点
        self.token_url = "https://api.weixin.qq.com/cgi-bin/token"
        self.upload_file_url = "https://api.weixin.qq.com/tcb/uploadfile"
        self.database_add_url = "https://api.weixin.qq.com/tcb/databaseadd"
        
        # 配置日志
        self._setup_logging()
        
        # 数据目录
        self.output_dir = Path("output")
        
    def _setup_logging(self):
        """配置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('upload_books.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_access_token(self) -> str:
        """
        获取Access Token
        
        Returns:
            access_token字符串
        """
        # 检查token是否过期
        if (self.access_token and self.token_expires_at and 
            datetime.now() < self.token_expires_at):
            return self.access_token
            
        self.logger.info("正在获取新的Access Token...")
        
        params = {
            'grant_type': 'client_credential',
            'appid': self.app_id,
            'secret': self.app_secret
        }
        
        try:
            response = requests.get(self.token_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if 'access_token' in data:
                self.access_token = data['access_token']
                # 提前5分钟过期，避免边界情况
                expires_in = data.get('expires_in', 7200) - 300
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                self.logger.info(f"Access Token获取成功，有效期至: {self.token_expires_at}")
                return self.access_token
            else:
                raise Exception(f"获取Access Token失败: {data}")
                
        except Exception as e:
            self.logger.error(f"获取Access Token出错: {e}")
            raise
            
    def upload_file(self, local_path: str, cloud_path: str) -> Optional[str]:
        """
        上传文件到云存储
        
        Args:
            local_path: 本地文件路径
            cloud_path: 云存储路径
            
        Returns:
            上传成功返回file_id，失败返回None
        """
        if not os.path.exists(local_path):
            self.logger.error(f"本地文件不存在: {local_path}")
            return None
            
        try:
            # 1. 获取上传链接
            access_token = self.get_access_token()
            
            upload_data = {
                "env": self.env_id,
                "path": cloud_path
            }
            
            response = requests.post(
                f"{self.upload_file_url}?access_token={access_token}",
                json=upload_data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 详细记录API响应用于调试
            self.logger.info(f"获取上传链接响应: {result}")
            
            if result.get('errcode') != 0:
                self.logger.error(f"获取上传链接失败: {result}")
                return None
            
            # 检查必要字段是否存在
            required_fields = ['url', 'file_id']
            for field in required_fields:
                if field not in result:
                    self.logger.error(f"API响应缺少必要字段 '{field}': {result}")
                    return None
                    
            upload_url = result['url']
            file_id = result['file_id']
            
            # 2. 上传文件
            # 按照官方文档格式：POST multipart/form-data
            with open(local_path, 'rb') as f:
                # 构建POST表单，严格按照官方文档格式
                files = {
                    'key': (None, cloud_path),                              # 请求包中的 path 字段  
                    'Signature': (None, result['authorization']),           # 返回数据的 authorization 字段
                    'x-cos-security-token': (None, result['token']),        # 返回数据的 token 字段
                    'x-cos-meta-fileid': (None, result['cos_file_id']),     # 返回数据的 cos_file_id 字段
                    'file': (os.path.basename(local_path), f)               # 文件的二进制内容
                }
                
                self.logger.info(f"上传参数: {list(files.keys())}")
                if self.debug:
                    form_debug = {k: v[1] if k != 'file' else f'<文件:{os.path.basename(local_path)}>' 
                                for k, v in files.items()}
                    self.logger.info(f"表单数据: {form_debug}")
                
                upload_response = requests.post(upload_url, files=files, timeout=60)
                
                self.logger.info(f"上传响应状态码: {upload_response.status_code}")
                if self.debug:
                    self.logger.info(f"上传响应内容: {upload_response.text}")
                    
                upload_response.raise_for_status()
            
            return file_id
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"网络请求失败 {local_path}: {e}")
            return None
        except KeyError as e:
            self.logger.error(f"API响应字段缺失 {local_path}: 缺少字段 {e}")
            self.logger.error(f"完整API响应: {locals().get('result', 'API响应未获取')}")
            return None
        except Exception as e:
            self.logger.error(f"文件上传失败 {local_path}: {type(e).__name__}: {e}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None
            
    def add_database_records(self, collection: str, records: List[Dict]) -> bool:
        """
        批量添加数据库记录
        
        Args:
            collection: 集合名称
            records: 记录列表
            
        Returns:
            成功返回True，失败返回False
        """
        if not records:
            return True
            
        try:
            access_token = self.get_access_token()
            
            # 构造数据库查询语句
            records_str = json.dumps(records, ensure_ascii=False)
            query = f"db.collection('{collection}').add({{data: {records_str}}})"
            
            data = {
                "env": self.env_id,
                "query": query
            }
            
            response = requests.post(
                f"{self.database_add_url}?access_token={access_token}",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') != 0:
                self.logger.error(f"数据库插入失败: {result}")
                return False
                
            self.logger.info(f"成功插入{len(records)}条记录到{collection}集合")
            return True
            
        except Exception as e:
            self.logger.error(f"数据库操作失败: {e}")
            return False
            
    def parse_book_data(self, book_dir: Path) -> Tuple[Dict, List[Dict]]:
        """
        解析单本书的数据
        
        Args:
            book_dir: 书籍目录路径
            
        Returns:
            (book_data, chapters_data) 元组
        """
        book_id = book_dir.name
        meta_file = book_dir / "meta.json"
        
        if not meta_file.exists():
            raise FileNotFoundError(f"未找到meta.json文件: {meta_file}")
            
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta_data = json.load(f)
            
        book_info = meta_data['book']
        chapters_info = meta_data['chapters']
        
        # 构造books表数据
        book_data = {
            '_id': book_id,
            'title': book_info['title'],
            'author': book_info.get('author', ''),
            'cover': '',  # 稍后上传封面后填充
            'category': book_info.get('category', ''),  # 默认文学类
            'description': book_info.get('description', ''),
            'difficulty': book_info.get('difficulty', ''),  # 默认中等难度
            'total_chapters': book_info['total_chapters'],
            'total_duration': book_info.get('total_duration', 0), 
            'is_active': True,
            'tags': book_info.get('tags', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # 构造chapters表数据
        chapters_data = []
        
        for chapter_info in chapters_info:
            chapter_data = {
                '_id': f"{book_id}_{chapter_info['index']}_{chapter_info['sub_index']}",
                'book_id': book_id,
                'chapter_number': chapter_info['chapter_number'],
                'title': chapter_info['title'],
                'duration': chapter_info['duration'],
                'is_active': True,
                'audio_url': '',  # 稍后上传音频后填充
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            chapters_data.append(chapter_data)
            
        return book_data, chapters_data
        
    def upload_book_assets(self, book_dir: Path, book_id: str) -> Tuple[str, List[str]]:
        """
        上传书籍相关文件（封面和音频）
        
        Args:
            book_dir: 书籍目录
            book_id: 书籍ID
            
        Returns:
            (cover_file_id, audio_file_ids) 元组
        """
        cover_file_id = ""
        audio_file_ids = []
        
        # 上传封面
        cover_files = list(book_dir.glob("cover.*")) + list(book_dir.glob("*.jpg")) + list(book_dir.glob("*.png"))
        if cover_files:
            cover_file = cover_files[0]
            cloud_path = f"books/{book_id}/cover{cover_file.suffix}"
            cover_file_id = self.upload_file(str(cover_file), cloud_path)
            if cover_file_id:
                self.logger.info(f"封面上传成功: {cover_file_id}")
            
        # 上传音频文件
        audio_dir = book_dir / "audio"
        if audio_dir.exists():
            for audio_file in audio_dir.glob("*.wav"):
                cloud_path = f"books/{book_id}/audio/{audio_file.name}"
                file_id = self.upload_file(str(audio_file), cloud_path)
                if file_id:
                    audio_file_ids.append(file_id)
                    
        self.logger.info(f"音频文件上传完成，共{len(audio_file_ids)}个文件")
        return cover_file_id, audio_file_ids
        
    def upload_all_books(self) -> bool:
        """
        上传所有书籍数据
        
        Returns:
            成功返回True，失败返回False
        """
        if not self.output_dir.exists():
            self.logger.error(f"输出目录不存在: {self.output_dir}")
            return False
            
        book_dirs = [d for d in self.output_dir.iterdir() 
                    if d.is_dir() and (d / "meta.json").exists()]
                    
        if not book_dirs:
            self.logger.error("未找到任何包含meta.json的书籍目录")
            return False
            
        self.logger.info(f"发现{len(book_dirs)}本书籍: {[d.name for d in book_dirs]}")
        
        all_books_data = []
        all_chapters_data = []
        
        for book_dir in book_dirs:
            try:
                book_id = book_dir.name
                self.logger.info(f"处理书籍: {book_id}")
                
                # 解析书籍数据
                book_data, chapters_data = self.parse_book_data(book_dir)
                
                # 上传文件资源
                cover_file_id, audio_file_ids = self.upload_book_assets(book_dir, book_id)
                
                # 更新封面URL
                if cover_file_id:
                    book_data['cover'] = cover_file_id
                    
                # 更新章节音频URL（简化处理，使用文件名匹配）
                for chapter in chapters_data:
                    chapter_audio_pattern = chapter['title'].replace(' ', '_')
                    for audio_id in audio_file_ids:
                        if chapter_audio_pattern in audio_id:
                            chapter['audio_url'] = audio_id
                            break
                
                all_books_data.append(book_data)
                all_chapters_data.extend(chapters_data)
                
                self.logger.info(f"书籍{book_id}数据准备完成")
                
            except Exception as e:
                self.logger.error(f"处理书籍{book_dir.name}失败: {e}")
                continue
                
        # 批量插入数据库
        success = True
        
        if all_books_data:
            self.logger.info(f"开始插入{len(all_books_data)}本书籍数据...")
            if not self.add_database_records('books', all_books_data):
                success = False
                
        if all_chapters_data:
            self.logger.info(f"开始插入{len(all_chapters_data)}个章节数据...")
            # 分批插入，避免单次请求过大
            batch_size = 20
            for i in range(0, len(all_chapters_data), batch_size):
                batch = all_chapters_data[i:i+batch_size]
                if not self.add_database_records('chapters', batch):
                    success = False
                    
        return success


def main():
    """主函数"""
    print("微信云服务书籍数据上传脚本")
    print("=" * 50)
    print("此脚本将把output目录下的有声书数据上传到微信云服务")
    print("请确保已经创建了books和chapters数据库集合")
    print("=" * 50)
    
    # 获取用户输入
    app_id = input("请输入AppID (默认: wx7040936883aa6dad): ").strip() or "wx7040936883aa6dad"
    app_secret = input("请输入AppSecret: ").strip() or "94051e8239a7a5181f32695c3c4895d9"
    env_id = input("请输入云环境ID: ").strip() or "cloud1-1gpp78j208f0f610"
    
    if not app_secret or not env_id:
        print("错误: AppSecret和云环境ID不能为空")
        return
        
    # 确认操作
    print(f"\n配置信息:")
    print(f"AppID: {app_id}")
    print(f"AppSecret: {'*' * len(app_secret)}")
    print(f"云环境ID: {env_id}")
    
    # 询问是否开启调试模式
    debug_mode = input("\n开启调试模式？(显示详细API响应) (y/N): ").strip().lower() == 'y'
    
    confirm = input("\n确认开始上传？(y/N): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        return
        
    # 创建上传器
    uploader = WeChatCloudUploader(app_id, app_secret, env_id, debug=debug_mode)
    
    # 测试连接
    try:
        token = uploader.get_access_token()
        print(f"✓ 连接成功，Access Token: {token[:20]}...")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return
        
    # 开始上传
    print("\n开始上传书籍数据...")
    start_time = time.time()
    
    try:
        success = uploader.upload_all_books()
        
        elapsed_time = time.time() - start_time
        
        if success:
            print(f"\n✓ 上传完成！耗时: {elapsed_time:.2f}秒")
            print("请检查微信云控制台确认数据是否正确上传")
        else:
            print(f"\n✗ 上传过程中出现错误，请查看日志文件: upload_books.log")
            
    except Exception as e:
        print(f"\n✗ 上传失败: {e}")
        
    print("\n详细日志已保存到: upload_books.log")


if __name__ == "__main__":
    main()