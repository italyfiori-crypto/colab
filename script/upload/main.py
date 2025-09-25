#!/usr/bin/env python3
"""
微信云服务书籍数据上传脚本 - 主流程控制器
用于将output目录下的有声书数据上传到微信云数据库和存储
"""

import time
import logging
import os
import argparse
from wechat_api import WeChatCloudAPI
from data_parser import DataParser
from book_uploader import BookUploader
from vocabulary_uploader import VocabularyUploader
from subtitle_analysis_uploader import SubtitleAnalysisUploader


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='微信云服务书籍数据上传脚本')
    parser.add_argument('input_dir', help='输入目录路径(必填)')
    parser.add_argument('--books', action='store_true', help='上传书籍信息')
    parser.add_argument('--chapters', action='store_true', help='上传章节信息') 
    parser.add_argument('--analysis', action='store_true', help='上传字幕解析信息')
    parser.add_argument('--vocabulary', action='store_true', help='上传词汇信息')
    return parser.parse_args()


def get_enabled_content_types(args):
    """获取启用的内容类型，无标志时默认全部启用"""
    if not any([args.books, args.chapters, args.analysis, args.vocabulary]):
        return {'books', 'chapters', 'analysis', 'vocabulary'}  # 默认全部
    
    enabled = set()
    if args.books: enabled.add('books')
    if args.chapters: enabled.add('chapters') 
    if args.analysis: enabled.add('analysis')
    if args.vocabulary: enabled.add('vocabulary')
    return enabled


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


def get_books_to_process(input_dir: str):
    """获取需要处理的书籍列表"""
    if not os.path.exists(input_dir):
        raise ValueError(f"输入目录不存在: {input_dir}")
    
    # 检查是否为单本书籍目录
    if os.path.exists(os.path.join(input_dir, "meta.json")):
        book_id = os.path.basename(input_dir)
        return [(input_dir, book_id)]
    
    # 检查是否为书籍根目录
    books = []
    for d in os.listdir(input_dir):
        book_path = os.path.join(input_dir, d)
        if os.path.isdir(book_path) and os.path.exists(os.path.join(book_path, "meta.json")):
            books.append((book_path, d))
    
    if not books:
        raise ValueError(f"在目录 {input_dir} 中未找到任何包含meta.json的书籍目录")
    
    return books


def process_single_book(book_dir: str, book_id: str, content_types: set, 
                       api_client: WeChatCloudAPI, parser: DataParser,
                       book_uploader: BookUploader, vocab_uploader: VocabularyUploader, 
                       subtitle_uploader: SubtitleAnalysisUploader) -> dict:
    """处理单本书籍的上传"""
    stats = {'success': False, 'chapters_success': 0, 'chapters_failed': 0}
    
    try:
        # 解析书籍数据
        book_data, chapters_data = parser.parse_book_data(book_dir, book_id)
        book_title = book_data.get('title', book_id)

        if book_data["done"]:
            print(f"书籍：{book_title} 已经为处理完成状态")
            stats['success'] = True
            return stats

        # 处理书籍信息
        if 'books' in content_types:
            # 查询现有数据
            existing_book_list = api_client.query_database('books', {'_id': book_id}, limit=1)
            existing_book = existing_book_list[0] if existing_book_list else None

            needs_update, changed_fields = parser.compare_book_data(book_data, existing_book)
            if needs_update:
                if not existing_book:
                    print(f"🆕 新书籍: {book_title}")
                else:
                    print(f"🔄 更新书籍: {book_title} (变化: {', '.join(changed_fields)})")
                    
                if not book_uploader.upload_book_if_needed(book_data, existing_book, changed_fields):
                    print(f"❌ 书籍处理失败: {book_title}")
                    return stats
            else:
                print(f"⏭️ 书籍无变化: {book_title}")
        
        # 处理章节信息
        if 'chapters' in content_types and chapters_data:
            existing_chapters = api_client.query_all_records('chapters', {'book_id': book_id})
            existing_chapters_dict = {ch['_id']: ch for ch in existing_chapters}
            
            print(f"📖 处理 {len(chapters_data)} 个章节...")
            chapter_stats = {'chapters_added': 0, 'chapters_updated': 0, 'chapters_skipped': 0, 'chapters_failed': 0}
            
            for chapter_data in chapters_data:
                if book_uploader.process_single_chapter(book_dir, book_id, chapter_data, existing_chapters_dict, chapter_stats):
                    stats['chapters_success'] += 1
                else:
                    stats['chapters_failed'] += 1
            
            print(f"📊 章节处理统计: 新增{chapter_stats['chapters_added']}, 更新{chapter_stats['chapters_updated']}, 跳过{chapter_stats['chapters_skipped']}, 失败{chapter_stats['chapters_failed']}")
        
        # 处理字幕解析信息
        if 'analysis' in content_types:
            print(f"📝 开始处理字幕解析信息...")
            analysis_stats = subtitle_uploader.process_book_analysis(book_dir, book_id)
            if analysis_stats['total_records'] > 0:
                print(f"📊 字幕解析统计: 新增{analysis_stats['added']}, 更新{analysis_stats['updated']}, 跳过{analysis_stats['skipped']}, 失败{analysis_stats['failed']}")

        # 处理词汇
        if 'vocabulary' in content_types:
            print(f"📚 开始处理词汇...")
            vocab_uploader.upload_vocabularies(book_dir)
        
        print(f"✅ 书籍 {book_title} 处理完成")
        stats['success'] = True
        
    except Exception as e:
        print(f"❌ 书籍 {book_id} 处理失败: {e}")
    
    return stats


def process_upload(input_dir: str, content_types: set, api_client: WeChatCloudAPI) -> bool:
    """处理上传流程"""
    # 硬编码项目根路径
    program_root = "/Users/yulu/Documents/code/mini_lang"
    
    # 创建上传器实例
    parser = DataParser()
    book_uploader = BookUploader(api_client)
    vocab_uploader = VocabularyUploader(api_client, program_root)
    subtitle_uploader = SubtitleAnalysisUploader(api_client)
    
    # 获取需要处理的书籍列表
    books_to_process = get_books_to_process(input_dir)
    print(f"📚 发现 {len(books_to_process)} 本书籍")
    
    # 统计信息
    total_stats = {
        'books_processed': 0, 'books_success': 0, 'books_failed': 0,
        'chapters_success': 0, 'chapters_failed': 0
    }
    
    # 处理每本书籍
    for i, (book_dir, book_id) in enumerate(books_to_process):
        print(f"\n📖 处理书籍 {i+1}/{len(books_to_process)}: {book_id}")
        
        book_stats = process_single_book(
            book_dir, book_id, content_types, api_client, parser,
            book_uploader, vocab_uploader, subtitle_uploader
        )
        
        total_stats['books_processed'] += 1
        if book_stats['success']:
            total_stats['books_success'] += 1
        else:
            total_stats['books_failed'] += 1
            
        total_stats['chapters_success'] += book_stats['chapters_success']
        total_stats['chapters_failed'] += book_stats['chapters_failed']
    
    # 输出最终统计
    print(f"\n📊 上传完成统计:")
    print(f"📚 书籍: 成功 {total_stats['books_success']}, 失败 {total_stats['books_failed']}")
    if total_stats['chapters_success'] > 0 or total_stats['chapters_failed'] > 0:
        print(f"📖 章节: 成功 {total_stats['chapters_success']}, 失败 {total_stats['chapters_failed']}")
    
    return total_stats['books_failed'] == 0 and total_stats['chapters_failed'] == 0


def main():
    """主函数 - 纯流程控制"""
    setup_logging()
    
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 获取启用的内容类型
        content_types = get_enabled_content_types(args)
        print(f"📋 将要上传的内容类型: {', '.join(sorted(content_types))}")
        
        # 获取配置
        app_id, app_secret, env_id = get_user_config()
        
        # 创建API客户端
        api_client = WeChatCloudAPI(app_id, app_secret, env_id)
        
        # 验证连接
        validate_connection(api_client)
        
        # 执行上传
        print("\n🚀 开始上传...")
        start_time = time.time()
        
        success = process_upload(args.input_dir, content_types, api_client)
        
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