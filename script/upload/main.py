#!/usr/bin/env python3
"""
微信云服务书籍数据上传脚本 - 主流程控制器
用于将output目录下的有声书数据上传到微信云数据库和存储
"""

import time
import logging
import os
from wechat_api import WeChatCloudAPI
from data_parser import DataParser
from book_uploader import BookUploader
from vocabulary_uploader import VocabularyUploader
from subtitle_analysis_uploader import SubtitleAnalysisUploader


def setup_logging():
    """配置简化日志系统"""
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler],
        force=True
    )


def get_user_config():
    """获取用户配置"""
    print("微信云服务书籍数据上传脚本")
    print("=" * 50)
    
    app_id = input("请输入AppID (默认: wx7040936883aa6dad): ").strip() or "wx7040936883aa6dad"
    app_secret = input("请输入AppSecret: ").strip() or "94051e8239a7a5181f32695c3c4895d9"
    env_id = input("请输入云环境ID: ").strip() or "cloud1-1gpp78j208f0f610"
    
    if not app_secret or not env_id:
        raise ValueError("AppSecret和云环境ID不能为空")
    
    # 显示配置信息
    print(f"\n配置信息:")
    print(f"AppID: {app_id}")
    print(f"AppSecret: {'*' * len(app_secret)}")
    print(f"云环境ID: {env_id}")
    
    # 确认操作
    confirm = input("\n确认开始上传？(y/N): ").strip().lower()
    if confirm != 'y':
        raise KeyboardInterrupt("操作已取消")
    
    return app_id, app_secret, env_id


def validate_connection(api_client: WeChatCloudAPI):
    """验证微信云连接"""
    try:
        token = api_client.get_access_token()
        print(f"✅ 连接成功")
    except Exception as e:
        raise ConnectionError(f"连接失败: {e}")


def process_all_books(api_client: WeChatCloudAPI) -> bool:
    """处理所有书籍的上传"""
    # 硬编码项目根路径
    program_root = "/Users/yulu/Documents/code/mini_lang"
    output_dir = os.path.join(program_root, "output")
    
    parser = DataParser(program_root)
    book_uploader = BookUploader(api_client, program_root)
    vocab_uploader = VocabularyUploader(api_client, program_root)
    subtitle_uploader = SubtitleAnalysisUploader(api_client, program_root)

    if not os.path.exists(output_dir):
        print(f"❌ 输出目录不存在: {output_dir}")
        return False
    
    # 获取书籍目录列表
    book_dirs = []
    for d in os.listdir(output_dir):
        book_path = os.path.join(output_dir, d)
        if os.path.isdir(book_path) and os.path.exists(os.path.join(book_path, "meta.json")):
            book_dirs.append(d)
    
    if not book_dirs:
        print("❌ 未找到任何包含meta.json的书籍目录")
        return False
    
    print(f"📚 发现 {len(book_dirs)} 本书籍")
    
    # 统计信息
    total_stats = {
        'books_processed': 0, 'books_success': 0, 'books_failed': 0,
        'chapters_processed': 0, 'chapters_success': 0, 'chapters_failed': 0
    }
    
    # 处理每本书籍

    for i in range(len(book_dirs)):
        book_id = book_dirs[i]
        book_dir = os.path.join(output_dir, book_id)
        print(f"\n📖 处理书籍 {i+1}/{len(book_dirs)}: {book_id}")
        
        try:
            # 解析书籍数据
            book_data, chapters_data = parser.parse_book_data(book_dir, book_id)
            book_title = book_data.get('title', book_id)

            if book_data["done"]:
                print(f"书籍：{book_title} 已经为处理完成状态")
                continue
            
            # 查询现有数据
            existing_book_list = api_client.query_database('books', {'_id': book_id}, limit=1)
            existing_book = existing_book_list[0] if existing_book_list else None
            
            existing_chapters = api_client.query_all_records('chapters', {'book_id': book_id})
            existing_chapters_dict = {ch['_id']: ch for ch in existing_chapters}
            
            # 处理书籍
            needs_update, changed_fields = parser.compare_book_data(book_data, existing_book)
            if needs_update:
                if not existing_book:
                    print(f"🆕 新书籍: {book_title}")
                else:
                    print(f"🔄 更新书籍: {book_title} (变化: {', '.join(changed_fields)})")
                    
                if book_uploader.upload_book_if_needed(book_dir, book_data, existing_book, changed_fields):
                    total_stats['books_success'] += 1
                    print(f"✅ 书籍处理成功: {book_title}")
                else:
                    total_stats['books_failed'] += 1
                    print(f"❌ 书籍处理失败: {book_title}")
                    continue
            else:
                total_stats['books_success'] += 1
                print(f"⏭️ 书籍无变化: {book_title}")
            
            total_stats['books_processed'] += 1
            
            # 处理章节
            if chapters_data:
                print(f"📖 处理 {len(chapters_data)} 个章节...")
                local_chapter_ids = {ch['_id'] for ch in chapters_data}
                chapter_stats = {'chapters_added': 0, 'chapters_updated': 0, 'chapters_skipped': 0, 'chapters_failed': 0}
                
                for chapter_data in chapters_data:
                    if book_uploader.process_single_chapter(book_dir, book_id, chapter_data, existing_chapters_dict, chapter_stats):
                        total_stats['chapters_success'] += 1
                    else:
                        total_stats['chapters_failed'] += 1
                    total_stats['chapters_processed'] += 1
                
                print(f"📊 章节处理统计: 新增{chapter_stats['chapters_added']}, 更新{chapter_stats['chapters_updated']}, 跳过{chapter_stats['chapters_skipped']}, 失败{chapter_stats['chapters_failed']}")
                
                # 清理孤立章节
                # book_uploader.cleanup_orphaned_chapters(book_id, local_chapter_ids, existing_chapters_dict)
            
            # 处理词汇
            print(f"📚 开始处理词汇...")
            vocab_uploader.upload_vocabularies(book_dir)
            
            # 处理字幕解析信息
            print(f"📝 开始处理字幕解析信息...")
            analysis_stats = subtitle_uploader.process_book_analysis(book_dir, book_id)
            if analysis_stats['total_records'] > 0:
                print(f"📊 字幕解析统计: 新增{analysis_stats['added']}, 更新{analysis_stats['updated']}, 跳过{analysis_stats['skipped']}, 失败{analysis_stats['failed']}")
            
            print(f"✅ 书籍 {book_title} 处理完成")
            
        except Exception as e:
            total_stats['books_failed'] += 1
            total_stats['books_processed'] += 1
            print(f"❌ 书籍 {book_id} 处理失败: {e}")
    
    # 输出最终统计
    print(f"\n📊 上传完成统计:")
    print(f"📚 书籍: 成功 {total_stats['books_success']}, 失败 {total_stats['books_failed']}")
    print(f"📖 章节: 成功 {total_stats['chapters_success']}, 失败 {total_stats['chapters_failed']}")
    
    return total_stats['books_failed'] == 0 and total_stats['chapters_failed'] == 0


def main():
    """主函数 - 纯流程控制"""
    setup_logging()
    
    try:
        # 获取配置
        app_id, app_secret, env_id = get_user_config()
        
        # 创建API客户端
        api_client = WeChatCloudAPI(app_id, app_secret, env_id)
        
        # 验证连接
        validate_connection(api_client)
        
        # 执行上传
        print("\n🚀 开始上传...")
        start_time = time.time()
        
        success = process_all_books(api_client)
        
        elapsed_time = time.time() - start_time
        
        if success:
            print(f"\n🎉 上传完成！耗时: {elapsed_time:.2f}秒")
        else:
            print(f"\n❌ 上传过程中出现错误")
            
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"\n❌ 上传失败: {e}")


if __name__ == "__main__":
    main()