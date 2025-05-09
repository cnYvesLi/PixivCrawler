import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from PixivCrawlerArtist import PixivArtistCrawler
from PixivCrawlerTag import PixivTagCrawler
import queue
import sys
from PIL import Image, ImageTk
import os
import time
import re
from datetime import datetime
import glob
import subprocess  # 添加这行
import json

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.update_timer = None

    def write(self, string):
        self.queue.put(string)
        if self.update_timer is None:
            self.update_timer = self.text_widget.after(100, self.update_text)

    def update_text(self):
        while not self.queue.empty():
            string = self.queue.get()
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, string)
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.update_timer = None

    def flush(self):
        pass

class PixivCrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixiv 爬虫")
        self.root.geometry("1200x800")  # 增加窗口大小以适应预览
        
        # 加载配置文件
        self.config = self.load_config()
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 左侧控制面板
        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Cookie输入
        ttk.Label(self.control_frame, text="Cookie:").grid(row=0, column=0, sticky=tk.W)
        self.cookie_text = scrolledtext.ScrolledText(self.control_frame, height=3, width=70)
        self.cookie_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # 模式选择
        ttk.Label(self.control_frame, text="模式:").grid(row=2, column=0, sticky=tk.W)
        self.mode_var = tk.StringVar(value="tag")
        ttk.Radiobutton(self.control_frame, text="标签模式", variable=self.mode_var, 
                       value="tag", command=self.toggle_mode).grid(row=2, column=1, sticky=tk.W)
        ttk.Radiobutton(self.control_frame, text="画师模式", variable=self.mode_var,
                       value="artist", command=self.toggle_mode).grid(row=2, column=1, sticky=tk.E)
        
        # 标签模式框架
        self.tag_frame = ttk.LabelFrame(self.control_frame, text="标签设置", padding="5")
        self.tag_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # 标签输入
        ttk.Label(self.tag_frame, text="标签:").grid(row=0, column=0, sticky=tk.W)
        self.tag_entry = ttk.Entry(self.tag_frame, width=30)
        self.tag_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # 过滤标签
        ttk.Label(self.tag_frame, text="过滤标签:").grid(row=1, column=0, sticky=tk.W)
        self.filter_tags_text = scrolledtext.ScrolledText(self.tag_frame, height=3, width=50)
        self.filter_tags_text.grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        # 最小收藏数
        ttk.Label(self.tag_frame, text="最小收藏数:").grid(row=2, column=0, sticky=tk.W)
        self.min_bookmarks_var = tk.StringVar(value="1000")
        self.min_bookmarks_entry = ttk.Entry(self.tag_frame, textvariable=self.min_bookmarks_var, width=10)
        self.min_bookmarks_entry.grid(row=2, column=1, sticky=tk.W)
        
        # 最大页数
        ttk.Label(self.tag_frame, text="最大页数:").grid(row=3, column=0, sticky=tk.W)
        self.max_pages_var = tk.StringVar(value="5")
        self.max_pages_entry = ttk.Entry(self.tag_frame, textvariable=self.max_pages_var, width=10)
        self.max_pages_entry.grid(row=3, column=1, sticky=tk.W)
        
        # 画师模式框架
        self.artist_frame = ttk.LabelFrame(self.control_frame, text="画师设置", padding="5")
        self.artist_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # 画师ID输入
        ttk.Label(self.artist_frame, text="画师ID:").grid(row=0, column=0, sticky=tk.W)
        self.artist_id_var = tk.StringVar()
        self.artist_id_entry = ttk.Entry(self.artist_frame, textvariable=self.artist_id_var, width=30)
        self.artist_id_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # 控制按钮框架
        self.button_frame = ttk.Frame(self.control_frame)
        self.button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        # 开始/暂停按钮
        self.start_button = ttk.Button(self.button_frame, text="开始爬取", command=self.toggle_crawling)
        self.start_button.grid(row=0, column=0, padx=5)
        
        # 暂停标志
        self.is_paused = False
        self.is_running = False
        
        # 输出框
        self.output_text = scrolledtext.ScrolledText(self.control_frame, height=15, width=80)
        self.output_text.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.output_text.configure(state='disabled')
        
        # 右侧预览面板
        self.preview_frame = ttk.LabelFrame(self.main_frame, text="图片预览", padding="5")
        self.preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 预览图片标签
        self.preview_label = ttk.Label(self.preview_frame)
        self.preview_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 预览信息标签
        self.preview_info = ttk.Label(self.preview_frame, text="等待开始...")
        self.preview_info.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 添加打开文件夹按钮
        self.open_folder_button = ttk.Button(self.preview_frame, text="打开下载文件夹", 
                                           command=self.open_current_folder)
        self.open_folder_button.grid(row=2, column=0, pady=5)
        self.open_folder_button.configure(state='disabled')  # 初始状态禁用
        
        # 保存当前下载目录
        self.current_save_dir = None
        
        # 配置网格权重
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # 重定向标准输出到文本框
        sys.stdout = RedirectText(self.output_text)
        
        # 初始化显示
        self.toggle_mode()
        
        # 设置默认值
        self.cookie_text.insert(tk.END, self.config.get('default_cookie', ''))
        self.tag_entry.insert(0, "喜多郁代")
        self.filter_tags_text.insert(tk.END, "AIイラスト")
        
        # 添加预览刷新定时器
        self.preview_timer = None
        self.last_preview_path = None
        
        # 开始预览刷新
        self.start_preview_refresh()
        
        # 添加爬虫线程变量
        self.crawler_thread = None

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 如果配置文件不存在，创建默认配置
                default_config = {
                    "default_cookie": ""
                }
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=4)
                return default_config
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            return {"default_cookie": ""}

    def save_config(self):
        """保存配置到文件"""
        try:
            config = {
                "default_cookie": self.cookie_text.get("1.0", tk.END).strip()
            }
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")

    def toggle_mode(self):
        """切换模式时停止当前爬虫"""
        # 如果正在运行，先停止爬虫
        if self.is_running:
            self.stop_crawler()
        
        mode = self.mode_var.get()
        if mode == "tag":
            self.tag_frame.grid()
            self.artist_frame.grid_remove()
        else:
            self.tag_frame.grid_remove()
            self.artist_frame.grid()
        
        # 重置按钮状态
        self.start_button.configure(text="开始爬取")
        self.is_running = False
        self.is_paused = False

    def stop_crawler(self):
        """停止爬虫"""
        self.is_running = False
        self.is_paused = False
        if self.crawler_thread and self.crawler_thread.is_alive():
            self.crawler_thread.join(timeout=1.0)
        self.start_button.configure(text="开始爬取")
        print("爬虫已停止")

    def toggle_crawling(self):
        """切换爬虫状态（开始/暂停）"""
        if not self.is_running:
            self.start_crawling()
        else:
            self.toggle_pause()

    def toggle_pause(self):
        """切换暂停状态"""
        self.is_paused = not self.is_paused
        self.start_button.configure(text="继续爬取" if self.is_paused else "暂停爬取")
        print(f"爬虫已{'暂停' if self.is_paused else '继续'}")

    def start_preview_refresh(self):
        """开始定期刷新预览"""
        self.refresh_preview()
        self.preview_timer = self.root.after(1000, self.start_preview_refresh)  # 每秒刷新一次

    def refresh_preview(self):
        """刷新预览图片"""
        try:
            # 获取最新的图片文件
            image_files = []
            for ext in ['*.jpg', '*.png', '*.jpeg']:
                image_files.extend(glob.glob(os.path.join('pixiv_images', '**', ext), recursive=True))
            
            if image_files:
                # 按修改时间排序，获取最新的图片
                latest_image = max(image_files, key=os.path.getmtime)
                
                # 如果图片路径发生变化，更新预览
                if latest_image != self.last_preview_path:
                    self.last_preview_path = latest_image
                    self.update_preview(latest_image)
        except Exception as e:
            print(f"预览刷新失败: {str(e)}")

    def update_preview(self, image_path):
        """更新预览图片"""
        try:
            # 打开并调整图片大小
            image = Image.open(image_path)
            # 计算调整后的尺寸，保持宽高比
            width, height = image.size
            max_size = (400, 400)
            ratio = min(max_size[0]/width, max_size[1]/height)
            new_size = (int(width*ratio), int(height*ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # 更新预览
            self.preview_label.configure(image=photo)
            self.preview_label.image = photo  # 保持引用
            
            # 更新预览信息
            filename = os.path.basename(image_path)
            folder = os.path.basename(os.path.dirname(image_path))
            self.preview_info.configure(text=f"文件夹: {folder}\n文件名: {filename}")
        except Exception as e:
            print(f"预览更新失败: {str(e)}")

    def open_current_folder(self):
        """打开当前下载文件夹"""
        if self.current_save_dir and os.path.exists(self.current_save_dir):
            try:
                if sys.platform == 'win32':
                    os.startfile(self.current_save_dir)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', self.current_save_dir])
                else:  # Linux
                    subprocess.run(['xdg-open', self.current_save_dir])
            except Exception as e:
                print(f"打开文件夹失败: {str(e)}")
        else:
            print("下载文件夹不存在")

    def start_crawling(self):
        cookie = self.cookie_text.get("1.0", tk.END).strip()
        if not cookie:
            messagebox.showerror("错误", "请输入Cookie")
            return
        
        # 如果已经在运行，先停止
        if self.is_running:
            self.stop_crawler()
            return
        
        self.is_running = True
        self.is_paused = False
        self.start_button.configure(text="暂停爬取")
        self.output_text.configure(state='normal')
        self.output_text.delete("1.0", tk.END)
        self.output_text.configure(state='disabled')
        
        # 禁用打开文件夹按钮，直到新的下载开始
        self.open_folder_button.configure(state='disabled')
        
        # 在新线程中运行爬虫
        self.crawler_thread = threading.Thread(target=self.run_crawler)
        self.crawler_thread.daemon = True
        self.crawler_thread.start()

    def run_crawler(self):
        try:
            cookie = self.cookie_text.get("1.0", tk.END).strip()
            mode = self.mode_var.get()
            
            # 创建保存目录
            current_date = datetime.now().strftime("%Y%m%d")
            if mode == "tag":
                tag = self.tag_entry.get().strip()
                if not tag:
                    messagebox.showerror("错误", "请输入标签")
                    return
                
                self.current_save_dir = f"pixiv_images/tag_{tag}_{current_date}"
                min_bookmarks = int(self.min_bookmarks_var.get())
                max_pages = int(self.max_pages_var.get())
                
                crawler = PixivTagCrawler(cookie, self.current_save_dir)
                # 启用打开文件夹按钮
                self.open_folder_button.configure(state='normal')
                crawler.crawl_tag_artworks(tag=tag, min_bookmarks=min_bookmarks, max_pages=max_pages)
            else:
                artist_id = self.artist_id_var.get().strip()
                if not artist_id:
                    messagebox.showerror("错误", "请输入画师ID")
                    return
                
                self.current_save_dir = f"pixiv_images/artist_{artist_id}_{current_date}"
                crawler = PixivArtistCrawler(cookie, self.current_save_dir)
                # 启用打开文件夹按钮
                self.open_folder_button.configure(state='normal')
                crawler.get_artist_artworks(artist_id)
                
        except Exception as e:
            print(f"发生错误: {str(e)}")
        finally:
            self.is_running = False
            self.is_paused = False
            self.start_button.configure(text="开始爬取")

    def __del__(self):
        """清理定时器并保存配置"""
        if self.preview_timer:
            self.root.after_cancel(self.preview_timer)
        self.save_config()

def main():
    root = tk.Tk()
    app = PixivCrawlerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 