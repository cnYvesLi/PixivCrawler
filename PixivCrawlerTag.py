import requests
import json
import os
import time
import re
import argparse
import configparser

sleep_time = 0.5

class PixivTagCrawler:
    def __init__(self, cookie, save_path=None):
        self.session = requests.Session()
        self.session.verify = False  # 禁用SSL验证
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Referer': 'https://www.pixiv.net/',
            'Cookie': cookie
        }
        # 使用传入的保存路径或默认路径
        self.save_path = save_path if save_path else 'pixiv_images'
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    def get_artworks_by_tag(self, tag, min_bookmarks=1000, page=1):
        # URL编码标签名称
        encoded_tag = requests.utils.quote(tag)
        url = f'https://www.pixiv.net/ajax/search/artworks/{encoded_tag}?word={encoded_tag}&order=date_d&mode=all&p={page}&s_mode=s_tag&type=all&lang=zh'
        
        print(f'正在获取第{page}页的作品...')
        response = self.session.get(url, headers=self.headers, verify=False)
        
        downloaded_count = 0
        
        if response.status_code == 200:
            data = response.json()
            if data['error'] == False:
                artworks = data['body']['illustManga']['data']
                
                print(f"本页共找到 {len(artworks)} 个作品")
                
                # 获取所有作品ID并处理
                artwork_ids = [artwork['id'] for artwork in artworks]
                
                for artwork_id in artwork_ids:
                    # 获取每个作品的详细信息以获取准确的收藏数
                    details = self.get_artwork_details(artwork_id)
                    if details:
                        if details.get('ai_detected', False):
                            print(f"作品ID: {artwork_id} 被检测为AI生成")
                            continue
                        
                        bookmark_count = details.get('bookmarkCount', 0)
                        print(f"作品ID: {artwork_id}, 收藏数: {bookmark_count}")
                        
                        # 检查收藏数是否达到要求
                        if bookmark_count >= min_bookmarks:
                            # 检查是否为AI生成的作品
                            tags = details.get('tags', {}).get('tags', [])
                            
                            # 检查是否为漫画作品（页数>10或包含漫画标签）
                            is_manga = details.get('pageCount', 0) > 10 or self.has_manga_tags(tags)
                            if is_manga:
                                print(f"  ✗ 漫画作品，跳过下载")
                                continue
                            
                            if not self.is_ai_generated_from_tags(tags):
                                print(f"  ✓ 符合要求，开始下载...")
                                # 立即下载符合条件的作品
                                success = self.download_artwork(artwork_id, details)
                                if success:
                                    downloaded_count += 1
                                    print(f"  ✓ 下载成功！")
                                else:
                                    print(f"  ✗ 下载失败")
                            else:
                                print(f"  ✗ AI生成作品")
                        else:
                            print(f"  ✗ 收藏数不足")
                    
                    # 添加延时避免请求过于频繁
                    time.sleep(sleep_time)
                
                return downloaded_count, data['body']['illustManga']['total']
        
        print(f"请求失败: {response.status_code}")
        try:
            print(response.json())
        except:
            print("无法解析响应")
        
        return 0, 0

    def is_ai_generated_from_tags(self, tags):
        # 这个方法已不再需要检查标签，因为我们直接使用aiType字段
        # 但保留此方法是为了兼容性，返回False即可
        return False

    def has_manga_tags(self, tags):
        """检查作品标签中是否包含漫画相关标签"""
        manga_keywords = ['漫画', '4コマ', '4格漫画', 'comic', 'manga', 'Comics']
        for tag in tags:
            tag_name = tag.get('tag', '').lower()
            for keyword in manga_keywords:
                if keyword.lower() in tag_name:
                    print(f"  发现漫画标签: {tag_name}")
                    return True
        return False

    def get_artwork_details(self, artwork_id):
        url = f'https://www.pixiv.net/ajax/illust/{artwork_id}'
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            if data['error'] == False:
                # 获取详细信息
                details = data['body']
                
                # 检查aiType字段，如果值为2则标记为AI生成
                if details.get('aiType') == 2:
                    print(f"  ✗ Pixiv标记为AI生成作品 (aiType=2)")
                    details['ai_detected'] = True
                    return details
                        
                return details
        return None

    def download_image(self, url, filename):
        try:
            print(f'开始下载: {url}')
            response = self.session.get(url, headers=self.headers)
            if response.status_code == 200:
                file_path = os.path.join(self.save_path, filename)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f'下载完成: {filename}')
                return True
            else:
                print(f'下载失败: {filename}，状态码: {response.status_code}')
                return False
        except Exception as e:
            print(f'下载出错: {filename}，错误: {str(e)}')
            return False

    def download_artwork(self, artwork_id, details=None):
        if details is None:
            details = self.get_artwork_details(artwork_id)
        
        if details:
            bookmark_count = details.get('bookmarkCount', 0)
            try:
                # 检查是否为多页作品
                if details.get('pageCount', 1) > 1:
                    # 多页作品需要使用不同的API端点
                    return self.download_multi_page_artwork(artwork_id, details)
                else:
                    # 单页作品直接下载原图
                    original_url = details['urls']['original']
                    
                    # 打印URL以便调试
                    print(f"  原始图片URL: {original_url}")
                    
                    # 确保Referer头部正确设置
                    custom_headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                        'Referer': f'https://www.pixiv.net/artworks/{artwork_id}',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6',
                        'sec-ch-ua': '"Chromium";v="96", "Google Chrome";v="96", ";Not A Brand";v="99"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"Windows"',
                        'sec-fetch-dest': 'image',
                        'sec-fetch-mode': 'no-cors',
                        'sec-fetch-site': 'cross-site'
                    }
                    
                    # 添加原始Cookie
                    for key, value in [item.split('=', 1) for item in self.headers.get('Cookie', '').split('; ') if '=' in item]:
                        custom_headers[key] = value
                    
                    title = details.get('title', artwork_id)
                    # 移除文件名中的非法字符
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
                    filename = f"{artwork_id}_{safe_title}_{bookmark_count}.{original_url.split('.')[-1]}"
                    
                    # 限制文件名长度
                    if len(filename) > 200:
                        filename = f"{artwork_id}_{bookmark_count}.{original_url.split('.')[-1]}"
                    
                    print(f"  尝试下载: {filename}")
                    try:
                        # 使用会话保持cookie
                        with requests.Session() as session:
                            for key, value in custom_headers.items():
                                session.headers[key] = value
                                
                            response = session.get(original_url, timeout=30)
                            if response.status_code == 200:
                                file_path = os.path.join(self.save_path, filename)
                                with open(file_path, 'wb') as f:
                                    f.write(response.content)
                                print(f'  下载完成: {filename}, 大小: {len(response.content)} 字节')
                                return True
                            else:
                                print(f'  下载失败: HTTP状态码 {response.status_code}')
                                print(f'  响应头: {response.headers}')
                                if response.status_code == 403:
                                    print('  可能是Referer检查失败或Cookie无效')
                    except requests.exceptions.RequestException as e:
                        print(f'  请求异常: {str(e)}')
            except Exception as e:
                print(f'处理作品 {artwork_id} 时出错: {str(e)}')
                import traceback
                traceback.print_exc()
        return False

    def download_multi_page_artwork(self, artwork_id, details):
        try:
            # 获取多页作品的所有页面
            page_count = details.get('pageCount', 0)
            bookmark_count = details.get('bookmarkCount', 0)
            title = details.get('title', artwork_id)
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
            
            # 打印调试信息
            print(f"  多页作品, 共 {page_count} 页")
            
            # 确保Referer头部正确设置
            custom_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'Referer': f'https://www.pixiv.net/artworks/{artwork_id}',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6',
                'sec-ch-ua': '"Chromium";v="96", "Google Chrome";v="96", ";Not A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'image',
                'sec-fetch-mode': 'no-cors',
                'sec-fetch-site': 'cross-site'
            }
            
            # 添加原始Cookie
            for key, value in [item.split('=', 1) for item in self.headers.get('Cookie', '').split('; ') if '=' in item]:
                custom_headers[key] = value
            
            # 获取多页作品的图片URL模式
            original_url = details['urls']['original']
            print(f"  原始URL: {original_url}")
            
            base_url_parts = original_url.rsplit('_p0', 1)
            if len(base_url_parts) != 2:  # 无法拆分URL
                print(f"  无法获取多页作品 {artwork_id} 的URL模式")
                return False
            
            base_url = base_url_parts[0]
            extension = base_url_parts[1]  # 包括.jpg/.png等扩展名
            
            success = False
            for i in range(page_count):
                page_url = f"{base_url}_p{i}{extension}"
                short_filename = f"{artwork_id}_p{i}{extension}"
                
                print(f"  尝试下载第 {i+1}/{page_count} 页: {page_url}")
                
                try:
                    with requests.Session() as session:
                        for key, value in custom_headers.items():
                            session.headers[key] = value
                        
                        response = session.get(page_url, timeout=30)
                        if response.status_code == 200:
                            file_path = os.path.join(self.save_path, short_filename)
                            with open(file_path, 'wb') as f:
                                f.write(response.content)
                            print(f'  下载完成: {short_filename}, 大小: {len(response.content)} 字节')
                            success = True
                        else:
                            print(f'  下载失败: HTTP状态码 {response.status_code}')
                            if response.status_code == 403:
                                print('  可能是Referer检查失败或Cookie无效')
                except requests.exceptions.RequestException as e:
                    print(f'  请求异常: {str(e)}')
                
                time.sleep(sleep_time)  # 避免请求过快
            
            return success
        except Exception as e:
            print(f'处理多页作品 {artwork_id} 时出错: {str(e)}')
            import traceback
            traceback.print_exc()
            return False

    def crawl_tag_artworks(self, tag, min_bookmarks=1000, max_pages=5):
        print(f'开始获取标签 "{tag}" 下收藏数超过 {min_bookmarks} 的非AI作品...')
        
        page = 1
        total_downloaded = 0
        total_artworks = 0
        
        while page <= max_pages:
            downloaded_count, total = self.get_artworks_by_tag(tag, min_bookmarks, page)
            total_downloaded += downloaded_count
            
            if page == 1:
                total_artworks = total
                print(f'该标签下共有 {total} 个作品，正在筛选并下载符合条件的作品...')
            
            print(f'第 {page} 页已下载 {downloaded_count} 个符合条件的作品')
            
            if downloaded_count == 0:
                print(f'第 {page} 页没有找到符合条件的作品，尝试下一页')
            
            page += 1
            time.sleep(3)  # 页面之间的延时
            
            if page > max_pages:
                print(f'已达到设定的最大页数 {max_pages}')
                break
        
        print(f'爬取完成！共下载 {total_downloaded} 个作品')

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='Pixiv角色标签爬虫 - 爬取指定角色标签下收藏数超过特定数量的非AI作品')
    parser.add_argument('--tag', '-t', type=str, help='要爬取的角色标签名')
    parser.add_argument('--bookmarks', '-b', type=int, help='最小收藏数')
    parser.add_argument('--cookie', '-c', type=str, help='Pixiv的Cookie，留空则使用配置文件中的值')
    parser.add_argument('--pages', '-p', type=int, help='爬取的最大页数')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 默认值
    default_tag = '喜多郁代'
    default_bookmarks = 100
    default_pages = 50
    
    # 从配置文件读取cookie
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    if os.path.exists(config_path):
        config.read(config_path)
        default_cookie = config.get('Pixiv', 'cookie', fallback='')
    else:
        default_cookie = ''
    
    # 如果命令行没有提供标签，交互式询问用户
    tag = args.tag
    if tag is None:
        tag = input(f'请输入要爬取的角色标签名 [默认: {default_tag}]: ')
        if not tag:
            tag = default_tag
    
    # 如果命令行没有提供最小收藏数，交互式询问用户
    bookmarks = args.bookmarks
    if bookmarks is None:
        try:
            bookmarks_input = input(f'请输入最小收藏数 [默认: {default_bookmarks}]: ')
            bookmarks = int(bookmarks_input) if bookmarks_input else default_bookmarks
        except ValueError:
            print(f'无效的输入，使用默认值: {default_bookmarks}')
            bookmarks = default_bookmarks
    
    # 如果命令行没有提供最大页数，交互式询问用户
    pages = args.pages
    if pages is None:
        try:
            pages_input = input(f'请输入爬取的最大页数 [默认: {default_pages}]: ')
            pages = int(pages_input) if pages_input else default_pages
        except ValueError:
            print(f'无效的输入，使用默认值: {default_pages}')
            pages = default_pages
    
    # 如果命令行没有提供Cookie，使用配置文件中的值
    cookie = args.cookie if args.cookie else default_cookie
    
    if not cookie:
        print('错误：未找到Cookie配置。请在config.ini文件中设置cookie，或通过命令行参数提供。')
        return
    
    # 实例化爬虫并开始爬取
    crawler = PixivTagCrawler(cookie)
    crawler.crawl_tag_artworks(tag=tag, min_bookmarks=bookmarks, max_pages=pages)

if __name__ == '__main__':
    main()