# Pixiv 爬虫

这是一个用于爬取 Pixiv 图片的 Python 爬虫项目，支持按画师 ID 和标签两种模式进行爬取。

## 功能特点

- 支持两种爬取模式：
  - 画师模式：爬取指定画师的所有作品
  - 标签模式：爬取指定标签下的作品
- 自动过滤 AI 生成的作品
- 支持设置最小收藏数过滤
- 支持多页作品下载
- 支持自定义保存路径
- 支持从配置文件读取 Cookie
- 提供图形界面和命令行两种使用方式

## 环境要求

- Python 3.6+
- 依赖包：
  - requests
  - configparser
  - PyQt5 (GUI模式需要)

## 安装

1. 克隆项目到本地：
```bash
git clone https://github.com/cnYvesLi/PixivCrawler)
cd PixivCrawler
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 创建配置文件：
在项目根目录中的 `config.json` 文件，添加cookie：
```ini
[Pixiv]
cookie = 你的Pixiv Cookie
```

## 使用方法

### 图形界面使用

1. 启动图形界面：
```bash
./gui.sh
```

2. 界面功能说明：
   - Cookie 输入框：输入 Pixiv 的 Cookie
   - 模式选择：选择画师模式或标签模式
   - 画师模式：
     - 输入画师 ID
   - 标签模式：
     - 输入标签名
     - 设置最小收藏数
     - 设置最大页数
     - 添加/删除过滤标签
   - 预览区域：显示爬取到的图片预览
   - 控制按钮：
     - 开始：开始爬取
     - 暂停：暂停爬取
     - 继续：继续爬取
     - 停止：停止爬取

3. 使用步骤：
   - 输入 Cookie（或从配置文件读取）
   - 选择爬取模式
   - 填写相应参数
   - 点击"开始"按钮开始爬取
   - 可以随时暂停/继续/停止爬取
   - 在预览区域查看爬取进度

### 命令行使用

#### 画师模式

```bash
python PixivCrawlerArtist.py [--cookie COOKIE]
```

参数说明：
- `--cookie`, `-c`: Pixiv 的 Cookie（可选，默认从配置文件读取）

#### 标签模式

```bash
python PixivCrawlerTag.py [--tag TAG] [--bookmarks BOOKMARKS] [--cookie COOKIE] [--pages PAGES]
```

参数说明：
- `--tag`, `-t`: 要爬取的角色标签名
- `--bookmarks`, `-b`: 最小收藏数
- `--cookie`, `-c`: Pixiv 的 Cookie（可选，默认从配置文件读取）
- `--pages`, `-p`: 爬取的最大页数

### 使用示例

1. 图形界面：
   - 启动程序后按照界面提示操作
   - 可以实时查看爬取进度和预览图片

2. 命令行：
   - 爬取画师作品：
   ```bash
   python PixivCrawlerArtist.py
   ```
   - 爬取标签作品：
   ```bash
   python PixivCrawlerTag.py --tag "喜多郁代" --bookmarks 1000 --pages 5
   ```

## 注意事项

1. 使用前请确保已登录 Pixiv 并获取有效的 Cookie
2. 建议在 `config.json` 中配置 Cookie，避免每次都需要输入
3. 爬取时请遵守 Pixiv 的使用规则和版权规定
4. 建议适当设置延时，避免请求过于频繁
5. 下载的图片默认保存在 `pixiv_images` 目录下
6. 图形界面模式下可以实时预览和暂停，更适合长时间爬取
7. 命令行模式适合批量处理或自动化脚本
