import requests
import json
import os
import time
import re
import argparse
import configparser

sleep_time = 0.5

class PixivArtistCrawler:
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

    def get_artist_artworks(self, artist_id):
        # 获取作者作品列表的API
        url = f'https://www.pixiv.net/ajax/user/{artist_id}/profile/all'
        
        print(f'正在获取作者 {artist_id} 的所有作品...')
        response = self.session.get(url, headers=self.headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data['error'] == False:
                # 获取所有插画作品ID
                artworks = data['body']['illusts']
                artwork_ids = list(artworks.keys())
                
                print(f"共找到 {len(artwork_ids)} 个作品")
                
                # 下载每个作品
                for artwork_id in artwork_ids:
                    # 获取作品详细信息
                    details = self.get_artwork_details(artwork_id)
                    if details:
                        print(f"正在处理作品ID: {artwork_id}")
                        # 下载作品
                        success = self.download_artwork(artwork_id, details)
                        if success:
                            print(f"  ✓ 下载成功！")
                        else:
                            print(f"  ✗ 下载失败")
                    
                    # 添加延时避免请求过于频繁
                    time.sleep(sleep_time)
                
                return len(artwork_ids)
        
        print(f"请求失败: {response.status_code}")
        try:
            print(response.json())
        except:
            print("无法解析响应")
        
        return 0

    def get_artwork_details(self, artwork_id):
        url = f'https://www.pixiv.net/ajax/illust/{artwork_id}'
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            if data['error'] == False:
                return data['body']
        return None

    def download_artwork(self, artwork_id, details=None):
        if details is None:
            details = self.get_artwork_details(artwork_id)
        
        if details:
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
                    filename = f"{artwork_id}_{safe_title}.{original_url.split('.')[-1]}"
                    
                    # 限制文件名长度
                    if len(filename) > 200:
                        filename = f"{artwork_id}.{original_url.split('.')[-1]}"
                    
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

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='Pixiv作者作品爬虫 - 爬取指定作者的所有作品')
    parser.add_argument('--cookie', '-c', type=str, help='Pixiv的Cookie，留空则使用配置文件中的值')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 默认值
    default_artist_id = '114514'
    
    # 从配置文件读取cookie
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    if os.path.exists(config_path):
        config.read(config_path)
        default_cookie = config.get('Pixiv', 'cookie', fallback='')
    else:
        default_cookie = ''
    
    # 获取用户输入的artist_id
    artist_id = input('请输入要爬取的作者ID（直接回车使用默认值）：').strip()
    if not artist_id:
        artist_id = default_artist_id
        print(f'使用默认作者ID：{default_artist_id}')
    
    # 使用命令行参数或配置文件中的值
    cookie = args.cookie if args.cookie else default_cookie
    
    if not cookie:
        print('错误：未找到Cookie配置。请在config.ini文件中设置cookie，或通过命令行参数提供。')
        return
    
    # 初始化爬虫
    crawler = PixivArtistCrawler(cookie)
    
    # 开始爬取
    print(f'\n开始爬取作者 {artist_id} 的作品...')
    artwork_count = crawler.get_artist_artworks(artist_id)
    
    # 显示爬取结果
    print(f'\n爬取完成！共处理了 {artwork_count} 个作品')
    print(f'图片保存在目录: {crawler.save_path}/')

if __name__ == '__main__':
    main()