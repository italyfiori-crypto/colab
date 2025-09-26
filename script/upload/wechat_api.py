#!/usr/bin/env python3
"""
微信云服务API基础类
提供Token管理、数据库操作、云存储等基础API功能
"""

import os
import json
import time
import requests
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re


class WeChatCloudAPI:
    """微信云服务API基础类"""
    
    def __init__(self, app_id: str, app_secret: str, env_id: str):
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
        self.cloud_function_url = "https://api.weixin.qq.com/tcb/invokecloudfunction"
        
        self.logger = logging.getLogger(__name__)
        
    def clean_vocabulary_data(self, word_data: Dict) -> Dict:
        """
        专门清理词汇数据中的特殊字符，按字段进行精确处理
        主要解决translation字段中的转义符号问题
        """
        cleaned_data = word_data.copy()
        
        # 清理translation字段
        if 'translation' in cleaned_data and isinstance(cleaned_data['translation'], list):
            cleaned_translations = []
            for translation_item in cleaned_data['translation']:
                if isinstance(translation_item, dict):
                    cleaned_item = translation_item.copy()
                    
                    # 清理meaning字段中的异常符号
                    if 'meaning' in cleaned_item and isinstance(cleaned_item['meaning'], str):
                        meaning = cleaned_item['meaning']     
                        meaning = meaning.replace('"', '')                   
                        cleaned_item['meaning'] = meaning
                    
                    # 清理example字段（如果存在同样问题）
                    if 'example' in cleaned_item and isinstance(cleaned_item['example'], str):
                        example = cleaned_item['example']
                        example = example.replace('"', '')
                        cleaned_item['example'] = example
                    
                    cleaned_translations.append(cleaned_item)
            
            cleaned_data['translation'] = cleaned_translations
        
        return cleaned_data
        
    def calculate_md5(self, file_path: str) -> str:
        """计算文件MD5值"""
        if not os.path.exists(file_path):
            return ""
            
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"计算MD5失败 {file_path}: {e}")
            return ""
        
    def get_access_token(self) -> str:
        """获取微信Access Token"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
            
        params = {
            'grant_type': 'client_credential',
            'appid': self.app_id,
            'secret': self.app_secret
        }
        
        try:
            response = requests.get(self.token_url, params=params, timeout=30)
            result = response.json()
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                expires_in = result.get('expires_in', 7200)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                return self.access_token
            else:
                raise Exception(f"获取Token失败: {result}")
                
        except Exception as e:
            raise Exception(f"获取Access Token出错: {e}")
    
    def upload_file(self, local_path: str, cloud_path: str) -> Optional[str]:
        """上传文件到云存储"""
        if not os.path.exists(local_path):
            self.logger.error(f"本地文件不存在: {local_path}")
            return None
            
        try:
            # 获取上传链接
            token = self.get_access_token()
            filename = os.path.basename(local_path)
            
            get_upload_url_data = {
                "env": self.env_id,
                "path": cloud_path
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                f"{self.upload_file_url}?access_token={token}",
                data=json.dumps(get_upload_url_data),
                headers=headers,
                timeout=30
            )
            
            result = response.json()
            if result.get('errcode') != 0:
                self.logger.error(f"获取上传链接失败: {result}")
                return None
                
            # 检查必要字段
            required_fields = ['url', 'token', 'authorization', 'file_id', 'cos_file_id']
            for field in required_fields:
                if field not in result:
                    self.logger.error(f"API响应缺少必要字段 '{field}': {result}")
                    return None
            
            # 上传文件
            upload_data = {
                'key': cloud_path,
                'Signature': result['authorization'],
                'x-cos-security-token': result['token'],
                'x-cos-meta-fileid': result['cos_file_id']
            }
            
            with open(local_path, 'rb') as f:
                files = {'file': (filename, f, 'application/octet-stream')}
                upload_response = requests.post(result['url'], data=upload_data, files=files, timeout=60)
            
            if upload_response.status_code == 204:
                return result['file_id']
            else:
                self.logger.error(f"文件上传失败: HTTP {upload_response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"文件上传失败 {os.path.basename(local_path)}: {e}")
            return None

    def add_database_records(self, collection: str, records: List[Dict]) -> bool:
        """批量添加数据库记录"""
        if not records:
            return True
            
        try:
            token = self.get_access_token()
            
            # 转换数据格式并处理特殊字符
            formatted_records = []
            for record in records:
                # 针对词汇数据进行字段级清理
                cleaned_record = self.clean_vocabulary_data(record)
                record_str = json.dumps(cleaned_record, ensure_ascii=False, separators=(',', ':'))
                formatted_records.append(record_str)
            
            query_str = f"db.collection('{collection}').add({{data: [{','.join(formatted_records)}]}})"
            
            data = {
                "env": self.env_id,
                "query": query_str
            }
            
            response = requests.post(
                f"{self.database_add_url}?access_token={token}",
                data=json.dumps(data),
                headers={'Content-Type': 'application/json;charset=utf8'},
                timeout=30
            )
            
            result = response.json()
            if result.get('errcode') != 0:
                self.logger.error(f"数据库添加失败: {result.get('errmsg', '未知错误')}")
                return False
            
            return result.get('errcode') == 0
            
        except Exception as e:
            self.logger.error(f"数据库操作失败: {e}")
            return False

    def query_database(self, collection: str, query_filter: Dict = None, skip: int = 0, limit: int = 20) -> List[Dict]:
        """查询数据库记录"""
        try:
            token = self.get_access_token()
            
            if query_filter:
                filter_str = json.dumps(query_filter, ensure_ascii=False)
                query_str = f"db.collection('{collection}').where({filter_str}).skip({skip}).limit({limit}).get()"
            else:
                query_str = f"db.collection('{collection}').skip({skip}).limit({limit}).get()"
            
            data = {
                "env": self.env_id,
                "query": query_str
            }
            
            response = requests.post(
                f"{self.database_query_url}?access_token={token}",
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            result = response.json()
            
            if result.get('errcode') == 0:
                data = result.get('data', [])
                
                # 处理返回数据：如果元素是字符串，解析为字典
                if isinstance(data, list):
                    parsed_data = []
                    for item in data:
                        if isinstance(item, str):
                            try:
                                parsed_item = json.loads(item)
                                parsed_data.append(parsed_item)
                            except json.JSONDecodeError:
                                self.logger.error(f"JSON解析失败: {item}")
                                parsed_data.append(item)
                        else:
                            parsed_data.append(item)
                    return parsed_data
                else:
                    return data
            else:
                self.logger.error(f"数据库查询失败: {result}")
                return []
                
        except Exception as e:
            self.logger.error(f"数据库查询失败: {e}")
            return []

    def update_database_record(self, collection: str, record_id: str, update_data: Dict) -> bool:
        """更新数据库记录"""
        try:
            token = self.get_access_token()
            
            # 先清理特殊字符
            cleaned_update_data = self.clean_vocabulary_data(update_data)
            update_str = json.dumps(cleaned_update_data, ensure_ascii=False, separators=(',', ':'))
            
            query_str = f"db.collection('{collection}').doc('{record_id}').update({{data: {update_str}}})"
            
            data = {
                "env": self.env_id,
                "query": query_str
            }
            
            response = requests.post(
                f"{self.database_update_url}?access_token={token}",
                data=json.dumps(data),
                headers={'Content-Type': 'application/json;charset=utf8'},
                timeout=30
            )
            
            result = response.json()
            if result.get('errcode') != 0:
                self.logger.error(f"数据库更新失败: {result}")
                return False
            return result.get('errcode') == 0
            
        except Exception as e:
            self.logger.error(f"数据库更新失败: {e}")
            return False

    def upsert_database_record(self, collection: str, record_data: Dict) -> bool:
        """Upsert数据库记录（存在则更新，不存在则创建）"""
        try:
            record_id = record_data.get('_id')
            if not record_id:
                self.logger.error("记录缺少_id字段，无法执行upsert操作")
                return False
            
            # 先查询记录是否存在
            existing_records = self.query_database(collection, {'_id': record_id}, limit=1)
            
            if existing_records:
                # 记录存在，执行更新操作
                update_data = record_data.copy()
                # 保留原有的created_at，更新updated_at
                if 'created_at' in existing_records[0]:
                    update_data['created_at'] = existing_records[0]['created_at']
                update_data['updated_at'] = int(time.time() * 1000)
                
                return self.update_database_record(collection, record_id, update_data)
            else:
                # 记录不存在，执行创建操作
                return self.add_database_records(collection, [record_data])
                
        except Exception as e:
            self.logger.error(f"数据库upsert失败: {e}")
            return False

    def delete_database_record(self, collection: str, record_id: str) -> bool:
        """删除数据库记录"""
        try:
            token = self.get_access_token()
            
            query_str = f"db.collection('{collection}').doc('{record_id}').remove()"
            
            data = {
                "env": self.env_id,
                "query": query_str
            }
            
            response = requests.post(
                f"{self.database_delete_url}?access_token={token}",
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            result = response.json()
            return result.get('errcode') == 0
            
        except Exception as e:
            self.logger.error(f"删除数据库记录失败: {e}")
            return False

    def query_all_records(self, collection: str, query_filter: Dict = None) -> List[Dict]:
        """查询所有记录（分页获取）"""
        all_records = []
        skip = 0
        limit = 100
        
        while True:
            records = self.query_database(collection, query_filter, skip, limit)
            if not records:
                break
            all_records.extend(records)
            if len(records) < limit:
                break
            skip += limit
            
        return all_records

    def extract_file_id_from_url(self, url: str) -> Optional[str]:
        """从云存储URL中提取文件ID"""
        if not url:
            return None
        
        # 从URL中提取文件ID
        match = re.search(r'/([^/]+)$', url)
        return match.group(1) if match else None

    def delete_cloud_file(self, file_id: str) -> bool:
        """删除云存储文件"""
        try:
            token = self.get_access_token()
            
            data = {
                "env": self.env_id,
                "fileid_list": [file_id]
            }
            
            response = requests.post(
                f"https://api.weixin.qq.com/tcb/batchdeletefile?access_token={token}",
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            result = response.json()
            return result.get('errcode') == 0
            
        except Exception as e:
            self.logger.error(f"删除云存储文件失败: {e}")
            return False

    def invoke_cloud_function(self, function_name: str, function_params: Dict) -> Optional[Dict]:
        """调用云函数"""
        try:
            token = self.get_access_token()
            
            # 按照微信官方API规范：env和name通过URL参数传递，参数直接作为请求体
            url = f"{self.cloud_function_url}?access_token={token}&env={self.env_id}&name={function_name}"
            
            # 请求体直接是参数的JSON字符串
            response = requests.post(
                url,
                data=json.dumps(function_params),
                headers={'Content-Type': 'application/json'},
                timeout=60  # 云函数可能需要更长时间处理
            )
            
            result = response.json()
            
            if result.get('errcode') != 0:
                self.logger.error(f"调用云函数失败: {result}")
                return None
            
            # 解析云函数返回结果
            resp_data = result.get('resp_data')
            if resp_data:
                try:
                    return json.loads(resp_data)
                except json.JSONDecodeError:
                    self.logger.error(f"云函数返回数据JSON解析失败: {resp_data}")
                    return None
            
            return result
            
        except Exception as e:
            self.logger.error(f"调用云函数异常: {e}")
            return None

    def process_analysis_via_cloud_function(self, file_id: str, book_id: str, chapter_id: str) -> Dict:
        """通过云函数处理字幕解析文件"""
        params = {
            'action': 'processAnalysisFile',
            'fileId': file_id,
            'bookId': book_id,
            'chapterId': chapter_id
        }
        
        self.logger.info(f"调用云函数处理字幕解析文件: {chapter_id}")
        result = self.invoke_cloud_function('upload', params)
        
        if result and result.get('success'):
            return result.get('stats', {})
        else:
            error_msg = result.get('error', '云函数调用失败') if result else '云函数调用返回空结果'
            self.logger.error(f"云函数处理字幕解析失败: {error_msg}")
            return {'processed': 0, 'added': 0, 'updated': 0, 'skipped': 0, 'failed': 1}