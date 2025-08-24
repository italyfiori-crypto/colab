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
    
    def __init__(self, app_id: str, app_secret: str, env_id: str):
        """
        初始化上传器
        
        Args:
            app_id: 微信小程序AppID
            app_secret: 微信小程序AppSecret
            env_id: 微信云环境ID
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.env_id = env_id
        
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
        # 文件处理器 - 记录所有日志
        file_handler = logging.FileHandler('upload_books.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # 控制台处理器 - 只记录重要信息
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        
        # 配置根日志器
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler]
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
        filename = os.path.basename(local_path)
        
        if not os.path.exists(local_path):
            self.logger.error(f"❌ 本地文件不存在: {local_path}")
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
            
            if result.get('errcode') != 0:
                self.logger.error(f"❌ 获取上传链接失败: {result}")
                return None
            
            # 检查必要字段是否存在
            required_fields = ['url', 'file_id']
            for field in required_fields:
                if field not in result:
                    self.logger.error(f"❌ API响应缺少必要字段 '{field}': {result}")
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
                
                upload_response = requests.post(upload_url, files=files, timeout=60)
                upload_response.raise_for_status()
            
            self.logger.info(f"✅ 文件上传成功: {filename}")
            return file_id
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ 网络请求失败 {os.path.basename(local_path)}: {e}")
            return None
        except KeyError as e:
            self.logger.error(f"❌ API响应字段缺失 {os.path.basename(local_path)}: 缺少字段 {e}")
            self.logger.error(f"完整API响应: {locals().get('result', 'API响应未获取')}")
            return None
        except Exception as e:
            self.logger.error(f"❌ 文件上传失败 {os.path.basename(local_path)}: {type(e).__name__}: {e}")
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
                self.logger.error(f"❌ 数据库插入失败: {result}")
                return False
                
            self.logger.info(f"✅ 成功插入{len(records)}条记录到{collection}集合")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据库操作失败: {e}")
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
            'cover_url': '',  # 稍后上传封面后填充
            'category': book_info.get('category', ''),  # 默认文学类
            'description': book_info.get('description', ''),
            'total_chapters': book_info.get('total_chapters', 0),
            'total_duration': book_info.get('total_duration', 0), 
            'is_active': True,
            'tags': book_info.get('tags', []),
            'local_cover_file': book_info.get('local_cover_file', ''),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # 构造chapters表数据
        chapters_data = []
        
        for i, chapter_info in enumerate(chapters_info):
            chapter_data = {
                '_id': f"{book_id}_{chapter_info['chapter_number']}_{i}",
                'book_id': book_id,
                'chapter_number': chapter_info['chapter_number'],
                'title': chapter_info['title_cn'] or chapter_info['title'],
                'duration': chapter_info['duration'],
                'is_active': True,
                'audio_url': '',  # 稍后上传音频后填充
                'subtitle_url': '',  # 稍后上传字幕后填充
                'local_audio_file': chapter_info.get('local_audio_file', ''),
                'local_subtitle_file': chapter_info.get('local_subtitle_file', ''),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            chapters_data.append(chapter_data)
            
        return book_data, chapters_data
        
    def upload_book_cover(self, book_dir: Path, book_id: str, book_data: Dict) -> str:
        """
        上传书籍封面文件
        
        Args:
            book_dir: 书籍目录
            book_id: 书籍ID
            
        Returns:
            cover_file_id
        """
        # 上传封面
        cover_file = os.path.join(book_dir, book_data.get('local_cover_file', ''))
        if os.path.exists(cover_file):
            cloud_path = f"books/{book_id}/cover.jpg"
            cover_file_id = self.upload_file(str(cover_file), cloud_path)
        else:
            self.logger.warning(f"⚠️  封面文件不存在: {cover_file}")
            cover_file_id = ""

        return cover_file_id
        
    def upload_chapter_files(self, book_dir: Path, book_id: str, chapter: Dict) -> Tuple[str, str]:
        """
        上传单个章节的音频和字幕文件
        
        Args:
            book_dir: 书籍目录
            book_id: 书籍ID
            chapter: 章节数据
            
        Returns:
            (audio_file_id, subtitle_file_id) 元组
        """
        audio_file_id = ""
        subtitle_file_id = ""
        
        # 上传音频文件
        audio_file = chapter.get('local_audio_file', '')
        if audio_file and os.path.exists(audio_file):
            audio_filename = os.path.basename(audio_file)
            audio_cloud_path = f"books/{book_id}/audio/{audio_filename}"
            audio_file_id = self.upload_file(audio_file, audio_cloud_path)

        # 上传字幕文件
        subtitle_file = chapter.get('local_subtitle_file', '')
        if subtitle_file and os.path.exists(subtitle_file):
            subtitle_filename = os.path.basename(subtitle_file)
            subtitle_cloud_path = f"books/{book_id}/subtitles/{subtitle_filename}"
            subtitle_file_id = self.upload_file(subtitle_file, subtitle_cloud_path)

        return audio_file_id, subtitle_file_id
        
    def upload_all_books(self) -> bool:
        """
        上传所有书籍数据
        
        Returns:
            成功返回True，失败返回False
        """
        if not self.output_dir.exists():
            self.logger.error(f"❌ 输出目录不存在: {self.output_dir}")
            return False
            
        book_dirs = [d for d in self.output_dir.iterdir() 
                    if d.is_dir() and (d / "meta.json").exists()]
                    
        if not book_dirs:
            self.logger.error("❌ 未找到任何包含meta.json的书籍目录")
            return False
            
        self.logger.info(f"📚 发现{len(book_dirs)}本书籍: {[d.name for d in book_dirs]}")
        
        success = True
        
        for book_dir in book_dirs:
            try:
                book_id = book_dir.name
                self.logger.info(f"\n📖 处理书籍: {book_id}")
                
                # 解析书籍数据
                book_data, chapters_data = self.parse_book_data(book_dir)
                
                # 上传封面
                cover_file_id = self.upload_book_cover(book_dir, book_id, book_data)
                if cover_file_id:
                    book_data['cover_url'] = cover_file_id
                    
                # 先插入书籍数据
                self.logger.info(f"💾 插入书籍数据: {book_data['title']}")
                if not self.add_database_records('books', [book_data]):
                    self.logger.error(f"❌ 书籍数据插入失败: {book_id}")
                    success = False
                    continue
                
                # 逐个处理章节，上传文件后立即插入数据库
                for i, chapter in enumerate(chapters_data):
                    try:
                        # 上传章节文件
                        audio_file_id, subtitle_file_id = self.upload_chapter_files(book_dir, book_id, chapter)
                        
                        # 更新章节文件URL
                        if audio_file_id:
                            chapter['audio_url'] = audio_file_id
                        if subtitle_file_id:
                            chapter['subtitle_url'] = subtitle_file_id
                        
                        # 清理本地文件路径
                        del chapter['local_audio_file']
                        del chapter['local_subtitle_file']
                        
                        # 立即插入章节数据
                        self.logger.info(f"📝 插入章节 {i+1}/{len(chapters_data)}: {chapter['title']}")
                        if not self.add_database_records('chapters', [chapter]):
                            self.logger.error(f"❌ 章节数据插入失败: {chapter['title']}")
                            success = False
                            continue
                            
                    except Exception as e:
                        self.logger.error(f"❌ 处理章节失败: {chapter.get('title', 'Unknown')} - {e}")
                        success = False
                        continue
                
                # 清理书籍数据中的本地文件路径
                del book_data['local_cover_file']
                
                self.logger.info(f"✅ 书籍{book_id}处理完成")
                
            except Exception as e:
                self.logger.error(f"❌ 处理书籍{book_dir.name}失败: {e}")
                import traceback
                self.logger.error(f"详细错误信息: {traceback.format_exc()}")
                success = False
                continue
                    
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
    
    confirm = input("\n确认开始上传？(y/N): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        return
        
    # 创建上传器
    uploader = WeChatCloudUploader(app_id, app_secret, env_id)
    
    # 测试连接
    try:
        token = uploader.get_access_token()
        print(f"✅ 连接成功，Access Token: {token[:20]}...")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return
        
    # 开始上传
    print("\n🚀 开始上传书籍数据...")
    start_time = time.time()
    
    try:
        success = uploader.upload_all_books()
        
        elapsed_time = time.time() - start_time
        
        if success:
            print(f"\n🎉 上传完成！耗时: {elapsed_time:.2f}秒")
            print("📋 请检查微信云控制台确认数据是否正确上传")
        else:
            print(f"\n❌ 上传过程中出现错误，请查看日志文件: upload_books.log")
            
    except Exception as e:
        print(f"\n❌ 上传失败: {e}")
        
    print("\n📝 详细日志已保存到: upload_books.log")


if __name__ == "__main__":
    main()