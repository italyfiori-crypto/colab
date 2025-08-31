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
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re

# 获取项目根目录
program_root = os.path.dirname(os.path.dirname(__file__))


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
        self.database_query_url = "https://api.weixin.qq.com/tcb/databasequery"
        self.database_update_url = "https://api.weixin.qq.com/tcb/databaseupdate"
        self.database_delete_url = "https://api.weixin.qq.com/tcb/databasedelete"
        
        # 配置日志
        self._setup_logging()
        
        # 数据目录
        self.output_dir = Path("output")
        
    def _setup_logging(self):
        """配置日志系统"""
        # 控制台处理器 - 只记录重要信息
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        
        # 配置根日志器
        logging.basicConfig(
            level=logging.INFO,
            handlers=[console_handler]
        )
        self.logger = logging.getLogger(__name__)
        
    def calculate_md5(self, file_path: str) -> str:
        """
        计算文件的MD5哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件的MD5哈希值，如果文件不存在返回空字符串
        """
        if not os.path.exists(file_path):
            return ""
            
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"❌ 计算MD5失败 {file_path}: {e}")
            return ""
        
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
            
            # 构造数据库查询语句 - 使用安全的字符串处理
            records_str = json.dumps(records, ensure_ascii=False)
            # 转义JavaScript中的特殊字符
            records_str_escaped = records_str.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            query = f"db.collection('{collection}').add({{data: {records_str_escaped}}})"
            
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
            
    def update_database_records(self, collection: str, record_id: str, update_data: Dict) -> bool:
        """
        更新数据库记录
        
        Args:
            collection: 集合名称
            record_id: 记录ID
            update_data: 更新数据
            
        Returns:
            成功返回True，失败返回False
        """
        if not update_data:
            return True
            
        try:
            access_token = self.get_access_token()
            
            # 构造数据库更新语句
            # 过滤掉_id字段，因为更新时不能包含_id
            filtered_data = {k: v for k, v in update_data.items() if k != '_id'}
            update_str = json.dumps(filtered_data, ensure_ascii=False)
            query = f"db.collection('{collection}').doc('{record_id}').update({{data: {update_str}}})"
            
            data = {
                "env": self.env_id,
                "query": query
            }
            
            response = requests.post(
                f"{self.database_update_url}?access_token={access_token}",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') != 0:
                self.logger.error(f"❌ 数据库更新失败: {result}")
                return False
                
            modified_count = result.get('modified', 0)
            if modified_count > 0:
                self.logger.info(f"✅ 成功更新记录: {record_id}")
            else:
                self.logger.warning(f"⚠️ 记录未发生变化: {record_id}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据库更新失败: {e}")
            return False
            
    def query_database(self, collection: str, query_filter: Dict = None, skip: int = 0, limit: int = 20) -> List[Dict]:
        """
        查询数据库记录
        
        Args:
            collection: 集合名称
            query_filter: 查询条件，如果为None则查询所有记录
            skip: 跳过的记录数
            limit: 限制返回的记录数（最大20）
            
        Returns:
            查询结果列表
        """
        try:
            access_token = self.get_access_token()
            
            # 构造查询语句
            if query_filter:
                filter_str = json.dumps(query_filter, ensure_ascii=False)
                query = f"db.collection('{collection}').where({filter_str}).skip({skip}).limit({limit}).get()"
            else:
                query = f"db.collection('{collection}').skip({skip}).limit({limit}).get()"
            
            data = {
                "env": self.env_id,
                "query": query
            }
            
            response = requests.post(
                f"{self.database_query_url}?access_token={access_token}",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') != 0:
                self.logger.error(f"❌ 数据库查询失败: {result}")
                return []
                
            # 解析查询结果
            data_list = result.get('data', [])
            if isinstance(data_list, str):
                # 如果返回的是字符串，需要解析JSON
                data_list = json.loads(data_list)
            
            # 确保数据格式正确，处理嵌套JSON字符串
            if isinstance(data_list, list):
                parsed_list = []
                for item in data_list:
                    if isinstance(item, str):
                        # 如果列表中的项是字符串，尝试解析为JSON
                        try:
                            parsed_item = json.loads(item)
                            parsed_list.append(parsed_item)
                        except json.JSONDecodeError:
                            # 如果不是JSON格式，保持原样
                            parsed_list.append(item)
                    else:
                        # 如果已经是字典，直接添加
                        parsed_list.append(item)
                return parsed_list
            else:
                return []
            
        except Exception as e:
            self.logger.error(f"❌ 数据库查询失败: {e}")
            return []
            
    def query_all_records(self, collection: str, query_filter: Dict = None) -> List[Dict]:
        """
        分批查询所有记录，自动处理分页
        
        Args:
            collection: 集合名称
            query_filter: 查询条件，如果为None则查询所有记录
            
        Returns:
            所有查询结果的列表
        """
        all_records = []
        batch_size = 20  # 每批20条记录
        skip = 0
        
        self.logger.info(f"🔍 开始分批查询{collection}集合...")
        
        while True:
            # 查询当前批次
            batch_records = self.query_database(collection, query_filter, skip, batch_size)
            
            if not batch_records:
                # 没有更多记录，退出循环
                break
                
            all_records.extend(batch_records)
            
            # 如果返回的记录数少于批次大小，说明已经是最后一批
            if len(batch_records) < batch_size:
                break
                
            skip += batch_size
            self.logger.info(f"📄 已查询{len(all_records)}条记录...")
        
        self.logger.info(f"✅ 完成查询{collection}集合，共{len(all_records)}条记录")
        return all_records
            
    def compare_book_data(self, new_data: Dict, existing_data: Dict) -> Tuple[bool, List[str]]:
        """
        比较书籍数据是否需要更新
        
        Args:
            new_data: 新的书籍数据
            existing_data: 数据库中的现有数据
            
        Returns:
            (需要更新, 变化字段列表) 元组
        """
        if not existing_data:
            return True, ["new_book"]
            
        # 类型检查和转换
        if isinstance(existing_data, str):
            try:
                existing_data = json.loads(existing_data)
            except json.JSONDecodeError:
                self.logger.error(f"❌ 无法解析现有数据: {existing_data}")
                return True, ["data_parse_error"]
        
        if not isinstance(existing_data, dict):
            self.logger.error(f"❌ 现有数据格式错误: {type(existing_data)}")
            return True, ["data_format_error"]
        
        # 需要比较的字段列表
        compare_fields = [
            'title', 'author', 'description', 'category', 
            'total_chapters', 'total_duration', 'is_active', 
            'cover_md5', 'tags'
        ]
        
        changed_fields = []
        
        for field in compare_fields:
            new_value = new_data.get(field, '')
            existing_value = existing_data.get(field, '')
            
            # 转换为字符串进行比较，避免类型问题
            new_str = str(new_value).strip()
            existing_str = str(existing_value).strip()
            if new_str != existing_str:
                changed_fields.append(field)
                # self.logger.info(f"🔄 书籍字段变化 [{field}]: {existing_str} → {new_str}")
        
        needs_update = len(changed_fields) > 0
        return needs_update, changed_fields
        
    def compare_chapter_data(self, new_data: Dict, existing_data: Dict) -> Tuple[bool, List[str]]:
        """
        比较章节数据是否需要更新
        
        Args:
            new_data: 新的章节数据
            existing_data: 数据库中的现有数据
            
        Returns:
            (需要更新, 变化字段列表) 元组
        """
        if not existing_data:
            return True, ["new_chapter"]
        
        # 需要比较的字段列表
        compare_fields = [
            'title', 'duration', 'is_active', 
            'audio_md5', 'subtitle_md5', 'chapter_number'
        ]
        
        changed_fields = []
        
        for field in compare_fields:
            new_value = new_data.get(field, '')
            existing_value = existing_data.get(field, '')
            
            # 转换为字符串进行比较，避免类型问题
            new_str = str(new_value).strip()
            existing_str = str(existing_value).strip()
            if new_str != existing_str:
                changed_fields.append(field)
                # self.logger.info(f"🔄 章节字段变化 [{field}]: {existing_str} → {new_str}")
        
        needs_update = len(changed_fields) > 0
        return needs_update, changed_fields
        
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
        
        # 计算封面文件MD5
        cover_file_path = os.path.join(book_dir, book_info.get('local_cover_file', ''))
        cover_md5 = self.calculate_md5(cover_file_path)
        
        # 构造books表数据
        book_data = {
            '_id': book_id,
            'title': book_info['title'],
            'author': book_info.get('author', ''),
            'cover_url': '',  # 稍后上传封面后填充
            'cover_md5': cover_md5,  # 新增封面MD5字段
            'category': book_info.get('category', ''),  # 默认文学类
            'description': book_info.get('description', ''),
            'total_chapters': book_info.get('total_chapters', 0),
            'total_duration': int(book_info.get('total_duration', 0)), 
            'is_active': True,
            'tags': book_info.get('tags', []),
            'local_cover_file': cover_file_path,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'done': book_info.get('done', False)
        }
        
        # 构造chapters表数据
        chapters_data = []
        
        for i, chapter_info in enumerate(chapters_info):
            # 计算音频文件MD5
            audio_file_path = os.path.join(book_dir, chapter_info.get('local_audio_file', ''))
            audio_md5 = self.calculate_md5(audio_file_path)
            
            # 计算字幕文件MD5
            subtitle_file_path = os.path.join(book_dir, chapter_info.get('local_subtitle_file', ''))
            subtitle_md5 = self.calculate_md5(subtitle_file_path)

            # 从音频文件路径提取子章节文件名作为ID
            audio_filename = os.path.basename(chapter_info.get('local_audio_file', ''))
            subchapter_name = os.path.splitext(audio_filename)[0]  # 去掉扩展名
            
            chapter_data = {
                '_id': f"{book_id}_{subchapter_name}",
                'book_id': book_id,
                'chapter_number': chapter_info['chapter_number'],
                'title': chapter_info['title_cn'] or chapter_info['title'],
                'duration': int(chapter_info['duration']) if chapter_info['duration'] else 0,
                'is_active': True,
                'audio_url': '',  # 稍后上传音频后填充
                'audio_md5': audio_md5,  # 新增音频MD5字段
                'subtitle_url': '',  # 稍后上传字幕后填充
                'subtitle_md5': subtitle_md5,  # 新增字幕MD5字段
                'local_audio_file': audio_file_path,
                'local_subtitle_file': subtitle_file_path,
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
        cover_file = book_data.get('local_cover_file', '')
        if os.path.exists(cover_file):
            cloud_path = f"books/{book_id}/cover.jpg"
            cover_file_id = self.upload_file(str(cover_file), cloud_path)
        else:
            self.logger.warning(f"⚠️  封面文件不存在: {cover_file}")
            cover_file_id = ""

        return cover_file_id
        
    def upload_book_if_needed(self, book_dir: Path, book_data: Dict, existing_book: Dict, changed_fields: List[str]) -> bool:
        """
        根据变化字段决定是否上传书籍相关文件
        
        Args:
            book_dir: 书籍目录
            book_data: 书籍数据
            existing_book: 数据库中的现有书籍数据
            changed_fields: 发生变化的字段列表
            
        Returns:
            上传是否成功
        """
        book_id = book_data['_id']
        
        # 检查是否需要上传封面
        if 'cover_md5' in changed_fields or not existing_book:
            cover_file_id = self.upload_book_cover(book_dir, book_id, book_data)
            if cover_file_id:
                book_data['cover_url'] = cover_file_id
                return True
            elif not existing_book:
                # 新书但封面上传失败
                return False
            else:
                # 更新书籍但封面上传失败，保留原URL
                book_data['cover_url'] = existing_book.get('cover_url', '')
                return True
        else:
            # 封面没有变化，保留原URL
            book_data['cover_url'] = existing_book.get('cover_url', '')
            return True
            
    def upload_chapter_if_needed(self, book_dir: Path, book_id: str, chapter_data: Dict, existing_chapter: Dict, changed_fields: List[str]) -> bool:
        """
        根据变化字段决定是否上传章节相关文件
        
        Args:
            book_dir: 书籍目录
            book_id: 书籍ID
            chapter_data: 章节数据
            existing_chapter: 数据库中的现有章节数据
            changed_fields: 发生变化的字段列表
            
        Returns:
            上传是否成功
        """
        audio_file_id = ""
        subtitle_file_id = ""
        
        # 检查是否需要上传音频文件
        if 'audio_md5' in changed_fields or not existing_chapter:
            audio_file = chapter_data.get('local_audio_file', '')
            if audio_file and os.path.exists(audio_file):
                audio_filename = os.path.basename(audio_file)
                audio_cloud_path = f"books/{book_id}/audio/{audio_filename}"
                audio_file_id = self.upload_file(audio_file, audio_cloud_path)
                if not audio_file_id and not existing_chapter:
                    return False  # 新章节音频上传失败
        else:
            # 音频没有变化，保留原URL
            audio_file_id = existing_chapter.get('audio_url', '')
        
        # 检查是否需要上传字幕文件
        if 'subtitle_md5' in changed_fields or not existing_chapter:
            subtitle_file = chapter_data.get('local_subtitle_file', '')
            if subtitle_file and os.path.exists(subtitle_file):
                subtitle_filename = os.path.basename(subtitle_file)
                subtitle_cloud_path = f"books/{book_id}/subtitles/{subtitle_filename}"
                subtitle_file_id = self.upload_file(subtitle_file, subtitle_cloud_path)
        else:
            # 字幕没有变化，保留原URL
            subtitle_file_id = existing_chapter.get('subtitle_url', '')
        
        # 更新章节文件URL
        if audio_file_id:
            chapter_data['audio_url'] = audio_file_id
        if subtitle_file_id:
            chapter_data['subtitle_url'] = subtitle_file_id
            
        return True
        
    def process_single_chapter(self, book_dir: Path, book_id: str, chapter_data: Dict, existing_chapters_dict: Dict, stats: Dict) -> bool:
        """
        处理单个章节的上传和数据库更新
        
        Args:
            book_dir: 书籍目录
            book_id: 书籍ID
            chapter_data: 章节数据
            existing_chapters_dict: 现有章节数据字典
            stats: 统计信息
            
        Returns:
            处理是否成功
        """
        chapter_id = chapter_data['_id']
        existing_chapter = existing_chapters_dict.get(chapter_id)
        
        # 比较章节数据是否需要更新
        needs_update, changed_fields = self.compare_chapter_data(chapter_data, existing_chapter)
        
        if not needs_update:
            stats['skipped_chapters'] += 1
            self.logger.info(f"⏭️ 章节无变化，跳过: {chapter_data['title']}")
            return True
        
        # 记录变化信息
        if existing_chapter:
            stats['updated_chapters'] += 1
            self.logger.info(f"📝 检测到章节变化 {chapter_data['title']}: {', '.join(changed_fields)}")
        else:
            stats['new_chapters'] += 1
            self.logger.info(f"🆕 新章节: {chapter_data['title']}")
        
        # 上传章节文件（如果需要）
        if not self.upload_chapter_if_needed(book_dir, book_id, chapter_data, existing_chapter, changed_fields):
            self.logger.error(f"❌ 章节文件上传失败: {chapter_data['title']}")
            return False
        
        # 更新时间戳
        chapter_data['updated_at'] = datetime.now().isoformat()
        if existing_chapter:
            chapter_data['created_at'] = existing_chapter.get('created_at', chapter_data['created_at'])
        
        # 清理本地文件路径
        chapter_clean = chapter_data.copy()
        del chapter_clean['local_audio_file']
        del chapter_clean['local_subtitle_file']
        
        # 插入或更新章节数据
        self.logger.info(f"🔍 章节ID: {chapter_id}, 是否存在: {existing_chapter is not None}")
        if existing_chapter:
            # 更新现有记录
            self.logger.info(f"💾 更新章节数据: {chapter_data['title']}")
            if not self.update_database_records('chapters', chapter_id, chapter_clean):
                self.logger.error(f"❌ 章节数据更新失败: {chapter_data['title']}")
                return False
        else:
            # 插入新记录
            self.logger.info(f"💾 插入章节数据: {chapter_data['title']}")
            if not self.add_database_records('chapters', [chapter_clean]):
                self.logger.error(f"❌ 章节数据插入失败: {chapter_data['title']}")
                return False
        
        return True
        
    def process_single_book(self, book_dir: Path, stats: Dict) -> bool:
        """
        处理单本书的上传和数据库更新
        
        Args:
            book_dir: 书籍目录
            stats: 统计信息
            
        Returns:
            处理是否成功
        """
        book_id = book_dir.name
        self.logger.info(f"\n📖 处理书籍: {book_id}")
        
        try:
            # 解析书籍数据
            book_data, chapters_data = self.parse_book_data(book_dir)

            # 如果书籍已处理完成，则跳过
            if book_data and book_data['done']:
                stats['skipped_books'] += 1
                stats['skipped_chapters'] += len(chapters_data)
                self.logger.info(f"⏭️ 书籍已处理完成，跳过: {book_id}")
                return True
            
            # 查询数据库中的书籍记录
            existing_books = self.query_database('books', {'_id': book_id})
            existing_book = existing_books[0] if existing_books else None
            
            # 比较书籍数据是否需要更新
            book_needs_update, changed_fields = self.compare_book_data(book_data, existing_book)
            
            # 处理书籍数据
            if book_needs_update:
                # 记录变化信息
                if existing_book:
                    stats['updated_books'] += 1
                    self.logger.info(f"📚 检测到书籍变化 {book_data['title']}: {', '.join(changed_fields)}")
                else:
                    stats['new_books'] += 1
                    self.logger.info(f"🆕 新书籍: {book_data['title']}")
                
                # 上传书籍文件（如果需要）
                if not self.upload_book_if_needed(book_dir, book_data, existing_book, changed_fields):
                    self.logger.error(f"❌ 书籍文件上传失败: {book_id}")
                    return False
                
                # 更新时间戳
                book_data['updated_at'] = datetime.now().isoformat()
                if existing_book:
                    book_data['created_at'] = existing_book.get('created_at', book_data['created_at'])
                
                # 清理本地文件路径
                book_data_clean = book_data.copy()
                del book_data_clean['local_cover_file']
                
                # 插入或更新书籍数据
                if existing_book:
                    # 更新现有记录
                    self.logger.info(f"💾 更新书籍数据: {book_data['title']}")
                    if not self.update_database_records('books', book_id, book_data_clean):
                        self.logger.error(f"❌ 书籍数据更新失败: {book_id}")
                        return False
                else:
                    # 插入新记录
                    self.logger.info(f"💾 插入书籍数据: {book_data['title']}")
                    if not self.add_database_records('books', [book_data_clean]):
                        self.logger.error(f"❌ 书籍数据插入失败: {book_id}")
                        return False
            else:
                stats['skipped_books'] += 1
                self.logger.info(f"⏭️ 书籍无变化，跳过: {book_data['title']}")
            
            # 查询数据库中的章节记录（分批查询）
            existing_chapters = self.query_all_records('chapters', {'book_id': book_id})
            existing_chapters_dict = {ch['_id']: ch for ch in existing_chapters}
            
            # 处理章节数据
            for i, chapter in enumerate(chapters_data):
                self.logger.info(f"📝 处理章节 {i+1}/{len(chapters_data)}: {chapter['title']}")
                if not self.process_single_chapter(book_dir, book_id, chapter, existing_chapters_dict, stats):
                    return False

            # 清理云端多余的章节数据
            self.logger.info(f"🧹 检查并清理云端多余的章节数据...")
            local_chapter_ids = set(chapter['_id'] for chapter in chapters_data)
            if not self.cleanup_orphaned_chapters(book_id, local_chapter_ids, existing_chapters_dict):
                self.logger.warning(f"⚠️ 章节数据清理部分失败")
            
            # 处理词汇数据
            self.logger.info(f"📚 开始处理词汇数据...")
            if not self.upload_vocabularies(book_dir, book_id):
                self.logger.error(f"❌ 词汇数据上传失败: {book_id}")
                return False
            
            self.logger.info(f"✅ 书籍{book_id}处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 处理书籍{book_dir.name}失败: {e}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
            
    def print_upload_statistics(self, stats: Dict) -> None:
        """
        打印上传统计信息
        
        Args:
            stats: 统计信息字典
        """
        self.logger.info(f"\n📊 上传统计:")
        self.logger.info(f"   总书籍数: {stats['total_books']}")
        self.logger.info(f"   新增书籍: {stats['new_books']}")
        self.logger.info(f"   更新书籍: {stats['updated_books']}")
        self.logger.info(f"   跳过书籍: {stats['skipped_books']}")
        self.logger.info(f"   新增章节: {stats['new_chapters']}")
        self.logger.info(f"   更新章节: {stats['updated_chapters']}")
        self.logger.info(f"   跳过章节: {stats['skipped_chapters']}")
        
    def upload_all_books(self) -> bool:
        """
        智能上传所有书籍数据（支持增量更新）
        
        Returns:
            成功返回True，失败返回False
        """
        # 验证输出目录
        if not self.output_dir.exists():
            self.logger.error(f"❌ 输出目录不存在: {self.output_dir}")
            return False
            
        # 获取书籍目录列表
        book_dirs = [d for d in self.output_dir.iterdir() 
                    if d.is_dir() and (d / "meta.json").exists()]
                    
        if not book_dirs:
            self.logger.error("❌ 未找到任何包含meta.json的书籍目录")
            return False
            
        self.logger.info(f"📚 发现{len(book_dirs)}本书籍: {[d.name for d in book_dirs]}")
        
        # 初始化统计信息
        stats = {
            'total_books': len(book_dirs),
            'new_books': 0,
            'updated_books': 0,
            'skipped_books': 0,
            'new_chapters': 0,
            'updated_chapters': 0,
            'skipped_chapters': 0
        }
        
        # 处理所有书籍
        success = True
        for book_dir in book_dirs:
            if not self.process_single_book(book_dir, stats):
                success = False
        
        # 输出统计信息
        self.print_upload_statistics(stats)
                    
        return success
    
    def parse_vocabulary_data(self, master_vocab_path: str) -> Dict[str, Dict]:
        """解析总词汇表数据并转换为数据库格式"""
        vocabulary_data = {}
        
        if not os.path.exists(master_vocab_path):
            self.logger.warning(f"⚠️ 总词汇表不存在: {master_vocab_path}")
            return vocabulary_data
            
        try:
            with open(master_vocab_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        word_data = json.loads(line.strip())
                        
                        # 解析tags字符串为数组
                        tags_str = word_data.get('tags', '')
                        tags = tags_str.split() if tags_str else []
                        
                        # 解析translation字符串为对象数组
                        translation_str = word_data.get('translation', '')
                        translation = self._parse_translation(translation_str)
                        
                        # 解析exchange字符串为对象数组
                        exchange_str = word_data.get('exchange', '')
                        exchange = self._parse_exchange(exchange_str)
                        
                        # 构造数据库格式
                        db_word_data = {
                            '_id': word_data['word'],
                            'word': word_data['word'],
                            'phonetic': word_data.get('phonetic', ''),
                            'translation': translation,
                            'tags': tags,
                            'exchange': exchange,
                            'bnc': word_data.get('bnc', 0),
                            'frq': word_data.get('frq', 0),
                            'audio_url': word_data.get('audio', ''),
                            'created_at': datetime.now().isoformat(),
                            'updated_at': datetime.now().isoformat()
                        }
                        
                        vocabulary_data[word_data['word']] = db_word_data
                        
        except Exception as e:
            self.logger.error(f"❌ 解析词汇数据失败: {e}")
            
        return vocabulary_data
    
    def _parse_translation(self, translation_str: str) -> List[Dict]:
        """解析翻译字符串为对象数组"""
        if not translation_str:
            return []
            
        translations = []
        # 按换行符分割不同含义
        parts = translation_str.split('\\n')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # 匹配词性和含义 (如: "n. 意外事件, 机遇")
            match = re.match(r'^([a-z]+\.)\s*(.+)$', part)
            if match:
                pos_type = match.group(1)
                meaning = match.group(2)
                translations.append({
                    'type': pos_type,
                    'meaning': meaning,
                    'example': ''
                })
            else:
                # 如果没有词性标记，作为通用翻译
                translations.append({
                    'type': '',
                    'meaning': part,
                    'example': ''
                })
                
        return translations
    
    def _parse_exchange(self, exchange_str: str) -> List[Dict]:
        """解析词形变化字符串为对象数组"""
        if not exchange_str:
            return []
            
        exchanges = []
        # exchange格式通常是: "p:past/d:done/i:doing"
        if ':' in exchange_str:
            parts = exchange_str.split('/')
            for part in parts:
                if ':' in part:
                    type_code, form = part.split(':', 1)
                    exchanges.append({
                        'type': type_code.strip(),
                        'form': form.strip()
                    })
        
        return exchanges
    
    def upload_vocabularies(self, book_dir: Path, book_id: str) -> bool:
        """上传当前书籍的词汇数据到数据库"""
        try:
            # 1. 先从章节词汇文件中收集当前书籍的所有单词
            vocab_subchapters_dir = book_dir / "vocabulary" / "subchapters"
            if not vocab_subchapters_dir.exists():
                self.logger.warning(f"⚠️ 章节词汇目录不存在: {vocab_subchapters_dir}，跳过词汇上传")
                return True
                
            chapter_vocab_files = list(vocab_subchapters_dir.glob("*.json"))
            if not chapter_vocab_files:
                self.logger.warning(f"⚠️ 未找到章节词汇文件，跳过词汇上传")
                return True
            
            # 收集当前书籍的所有单词（保持顺序）
            book_words = []
            seen_words = set()
            for vocab_file in chapter_vocab_files:
                try:
                    with open(vocab_file, 'r', encoding='utf-8') as f:
                        chapter_data = json.load(f)
                    words = chapter_data.get('words', [])
                    # 保持顺序，但去重
                    for word in words:
                        if word not in seen_words:
                            book_words.append(word)
                            seen_words.add(word)
                except Exception as e:
                    self.logger.warning(f"⚠️ 读取章节词汇文件失败: {vocab_file}, {e}")
                    continue
            
            if not book_words:
                self.logger.warning(f"⚠️ 当前书籍没有词汇数据")
                return True
                
            self.logger.info(f"📝 当前书籍包含 {len(book_words)} 个唯一单词")
            
            # 2. 从总词汇表中筛选当前书籍的单词信息
            master_vocab_path = Path(os.path.join(program_root, "output/vocabulary/master_vocabulary.json"))
            if not master_vocab_path.exists():
                self.logger.warning(f"⚠️ 未找到总词汇表文件: {master_vocab_path}，跳过词汇上传")
                return True
            
            vocabulary_data = self.parse_vocabulary_data(str(master_vocab_path))
            if not vocabulary_data:
                self.logger.warning(f"⚠️ 总词汇表为空")
                return True
            
            # 筛选出当前书籍需要的单词
            book_vocabulary_data = {}
            for word in book_words:
                if word in vocabulary_data:
                    book_vocabulary_data[word] = vocabulary_data[word]
                    
            self.logger.info(f"📝 从总词汇表中筛选出 {len(book_vocabulary_data)} 个单词信息")
            
            # 3. 先查询后插入，避免重复键错误
            filtered_words = list(book_vocabulary_data.values())
            if filtered_words:
                self.logger.info(f"📝 准备上传 {len(filtered_words)} 个单词到vocabularies表...")
                
                # 逐个查询和插入单词
                success_count = 0
                skip_count = 0
                
                self.logger.info(f"📝 开始逐个处理 {len(filtered_words)} 个单词...")
                
                for idx, word_data in enumerate(filtered_words):
                    word = word_data['word']
                    
                    # 查询单词是否已存在
                    existing_word = self.query_database('vocabularies', {'word': word}, limit=1)
                    
                    if existing_word:
                        skip_count += 1
                        if (idx + 1) % 10 == 0:  # 每处理50个单词打印一次进度
                            self.logger.info(f"📝 进度: {idx + 1}/{len(filtered_words)}, 新增: {success_count}, 跳过: {skip_count}")
                        continue
                    
                    # 如果不存在，立即插入
                    retry_count = 0
                    max_retries = 3
                    
                    while retry_count < max_retries:
                        try:
                            if self.add_database_records('vocabularies', [word_data]):
                                success_count += 1
                                break
                            else:
                                retry_count += 1
                                if retry_count < max_retries:
                                    self.logger.warning(f"⚠️ 单词 '{word}' 插入失败，重试 {retry_count}/{max_retries}...")
                                    time.sleep(1)
                                else:
                                    self.logger.error(f"❌ 单词 '{word}' 插入失败，超过最大重试次数")
                        except Exception as e:
                            retry_count += 1
                            if retry_count < max_retries:
                                self.logger.warning(f"⚠️ 单词 '{word}' 网络错误，重试 {retry_count}/{max_retries}: {e}")
                                time.sleep(2)
                            else:
                                self.logger.error(f"❌ 单词 '{word}' 插入失败，网络错误: {e}")
                                break
                    
                    # 打印进度（每处理50个单词）
                    if (idx + 1) % 50 == 0:
                        self.logger.info(f"📝 进度: {idx + 1}/{len(filtered_words)}, 新增: {success_count}, 跳过: {skip_count}")
                
                self.logger.info(f"✅ 词汇上传完成: 新增 {success_count} 个, 跳过 {skip_count} 个已存在")
            else:
                self.logger.info(f"📝 没有词汇需要上传")
            
            # 上传章节词汇关联
            return self.upload_chapter_vocabularies(book_dir, book_id, book_vocabulary_data)
            
        except Exception as e:
            self.logger.error(f"❌ 词汇上传失败: {e}")
            return False
    
    def upload_chapter_vocabularies(self, book_dir: Path, book_id: str, vocabulary_data: Dict) -> bool:
        """上传章节词汇关联数据"""
        try:
            vocab_subchapters_dir = book_dir / "vocabulary" / "subchapters"
            if not vocab_subchapters_dir.exists():
                self.logger.warning(f"⚠️ 章节词汇目录不存在: {vocab_subchapters_dir}")
                return True
                
            # 读取所有章节词汇文件
            chapter_vocab_files = list(vocab_subchapters_dir.glob("*.json"))
            if not chapter_vocab_files:
                self.logger.warning(f"⚠️ 未找到章节词汇文件")
                return True
                
            self.logger.info(f"📝 处理 {len(chapter_vocab_files)} 个章节的词汇关联...")
            
            chapter_vocab_records = []
            for vocab_file in chapter_vocab_files:
                try:
                    with open(vocab_file, 'r', encoding='utf-8') as f:
                        chapter_data = json.load(f)
                        
                    subchapter_id = chapter_data.get('subchapter_id', '')
                    words = chapter_data.get('words', [])
                    
                    if not subchapter_id or not words:
                        continue
                    
                    # 生成统一的chapter_id格式: book_id + 子章节文件名
                    chapter_id = f"{book_id}_{subchapter_id}"
                    
                    # 过滤出存在于词汇表中的单词（保持原始顺序）
                    filtered_words = [word for word in words if word in vocabulary_data]
                    
                    if filtered_words:
                        # 创建章节词汇记录（新表结构：每个章节一条记录）
                        record = {
                            '_id': chapter_id,
                            'book_id': book_id,
                            'chapter_id': chapter_id,
                            'words': filtered_words,  # 单词数组，保持顺序
                            'created_at': datetime.now().isoformat()
                        }
                        chapter_vocab_records.append(record)
                            
                except Exception as e:
                    self.logger.error(f"❌ 处理章节词汇文件失败 {vocab_file}: {e}")
                    continue
            
            # 批量上传章节词汇关联
            if chapter_vocab_records:
                self.logger.info(f"📝 上传 {len(chapter_vocab_records)} 条章节词汇关联...")
                
                # 分批上传
                batch_size = 100
                for i in range(0, len(chapter_vocab_records), batch_size):
                    batch = chapter_vocab_records[i:i + batch_size]
                    if not self.add_database_records('chapter_vocabularies', batch):
                        self.logger.error(f"❌ 章节词汇关联批次上传失败")
                        return False
                        
                self.logger.info(f"✅ 章节词汇关联上传完成")
            else:
                self.logger.warning(f"⚠️ 没有章节词汇关联数据需要上传")
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 章节词汇关联上传失败: {e}")
            return False
    
    def delete_database_record(self, collection: str, record_id: str) -> bool:
        """删除数据库记录"""
        try:
            access_token = self.get_access_token()
            
            # 构造删除查询语句（参考微信官方文档格式）
            query = f"db.collection('{collection}').where({{_id: '{record_id}'}}).remove()"
            
            data = {
                "env": self.env_id,
                "query": query
            }
            
            response = requests.post(
                f"{self.database_delete_url}?access_token={access_token}",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') == 0:
                deleted_count = result.get('deleted', 0)
                if deleted_count > 0:
                    self.logger.info(f"✅ 删除记录成功: {collection}.{record_id}")
                else:
                    self.logger.warning(f"⚠️ 记录不存在或已删除: {collection}.{record_id}")
                return True
            else:
                self.logger.error(f"❌ 删除记录失败: {collection}.{record_id}, {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 删除记录异常: {collection}.{record_id}, {e}")
            return False

    def cleanup_orphaned_chapters(self, book_id: str, local_chapter_ids: set, existing_chapters_dict: dict) -> bool:
        """清理云端多余的章节数据"""
        try:
            # 找出云端存在但本地不存在的章节
            cloud_chapter_ids = set(existing_chapters_dict.keys())
            orphaned_chapter_ids = cloud_chapter_ids - local_chapter_ids
            
            if not orphaned_chapter_ids:
                self.logger.info(f"✅ 没有需要清理的章节数据")
                return True
                
            self.logger.info(f"🧹 发现 {len(orphaned_chapter_ids)} 个需要清理的章节:")
            for chapter_id in orphaned_chapter_ids:
                chapter_title = existing_chapters_dict[chapter_id].get('title', chapter_id)
                self.logger.info(f"  - {chapter_title} ({chapter_id})")
            
            # 1. 删除chapters表记录
            for chapter_id in orphaned_chapter_ids:
                if not self.delete_database_record('chapters', chapter_id):
                    self.logger.error(f"❌ 删除章节记录失败: {chapter_id}")
                    return False
            
            # 2. 删除对应的chapter_vocabularies记录（新表结构：每个章节一条记录）
            for chapter_id in orphaned_chapter_ids:
                # 直接删除章节词汇记录（_id就是chapter_id）
                if not self.delete_database_record('chapter_vocabularies', chapter_id):
                    self.logger.warning(f"⚠️ 删除章节词汇关联失败: {chapter_id}")
            
            # 3. 删除云存储中的音频和字幕文件
            for chapter_id in orphaned_chapter_ids:
                chapter_data = existing_chapters_dict[chapter_id]
                # 删除音频文件
                if 'audio_url' in chapter_data and chapter_data['audio_url']:
                    file_id = self.extract_file_id_from_url(chapter_data['audio_url'])
                    if file_id:
                        self.delete_cloud_file(file_id)
                
                # 删除字幕文件  
                if 'subtitle_url' in chapter_data and chapter_data['subtitle_url']:
                    file_id = self.extract_file_id_from_url(chapter_data['subtitle_url'])
                    if file_id:
                        self.delete_cloud_file(file_id)
            
            self.logger.info(f"✅ 清理完成: 删除了 {len(orphaned_chapter_ids)} 个章节及其关联数据")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 章节数据清理失败: {e}")
            return False

    def extract_file_id_from_url(self, url: str) -> Optional[str]:
        """从云存储URL中提取文件ID"""
        try:
            # 假设URL格式类似: https://xxx.com/file_id
            # 需要根据实际微信云存储URL格式调整
            if url and '/' in url:
                return url.split('/')[-1]
            return None
        except Exception:
            return None

    def delete_cloud_file(self, file_id: str) -> bool:
        """删除云存储文件"""
        try:
            # 使用微信云存储API删除文件
            url = f"https://api.weixin.qq.com/tcb/deletefile"
            data = {
                "env": self.env_id,
                "fileid_list": [file_id]
            }
            
            response = requests.post(url, 
                                   params={'access_token': self.access_token},
                                   json=data,
                                   timeout=30)
            
            result = response.json()
            if result.get('errcode') == 0:
                self.logger.info(f"✅ 删除云存储文件成功: {file_id}")
                return True
            else:
                self.logger.warning(f"⚠️ 删除云存储文件失败: {file_id}, {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 删除云存储文件异常: {file_id}, {e}")
            return False


def main():
    """主函数"""
    # 创建临时uploader实例以使用统一的日志系统
    temp_uploader = WeChatCloudUploader("temp", "temp", "temp")
    logger = temp_uploader.logger
    
    logger.info("微信云服务书籍数据上传脚本")
    logger.info("=" * 50)
    logger.info("此脚本将把output目录下的有声书数据上传到微信云服务")
    logger.info("请确保已经创建了books和chapters数据库集合")
    logger.info("=" * 50)
    
    # 获取用户输入
    app_id = input("请输入AppID (默认: wx7040936883aa6dad): ").strip() or "wx7040936883aa6dad"
    app_secret = input("请输入AppSecret: ").strip() or "94051e8239a7a5181f32695c3c4895d9"
    env_id = input("请输入云环境ID: ").strip() or "cloud1-1gpp78j208f0f610"
    
    if not app_secret or not env_id:
        logger.error("错误: AppSecret和云环境ID不能为空")
        return
        
    # 确认操作
    logger.info(f"\n配置信息:")
    logger.info(f"AppID: {app_id}")
    logger.info(f"AppSecret: {'*' * len(app_secret)}")
    logger.info(f"云环境ID: {env_id}")
    
    confirm = input("\n确认开始上传？(y/N): ").strip().lower()
    if confirm != 'y':
        logger.info("操作已取消")
        return
        
    # 创建正式的上传器
    uploader = WeChatCloudUploader(app_id, app_secret, env_id)
    
    # 测试连接
    try:
        token = uploader.get_access_token()
        uploader.logger.info(f"✅ 连接成功，Access Token: {token[:20]}...")
    except Exception as e:
        uploader.logger.error(f"❌ 连接失败: {e}")
        return
        
    # 开始上传
    uploader.logger.info("\n🚀 开始上传书籍数据...")
    start_time = time.time()
    
    try:
        success = uploader.upload_all_books()
        
        elapsed_time = time.time() - start_time
        
        if success:
            uploader.logger.info(f"\n🎉 上传完成！耗时: {elapsed_time:.2f}秒")
            uploader.logger.info("📋 请检查微信云控制台确认数据是否正确上传")
        else:
            uploader.logger.error(f"\n❌ 上传过程中出现错误，请检查控制台输出")
            
    except Exception as e:
        uploader.logger.error(f"\n❌ 上传失败: {e}")
        
    uploader.logger.info("\n📝 详细日志已显示在控制台")


if __name__ == "__main__":
    main()