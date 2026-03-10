# 信用卡追踪 · Card Tracker

> 多卡福利追踪桌面应用，追踪 Amex、Chase 等信用卡的年度/月度福利使用情况。
> A Windows desktop app to track credit card annual/monthly benefit usage across multiple cards and users.

![License](https://img.shields.io/badge/license-GPL%20v3-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![Python](https://img.shields.io/badge/python-3.10%2B-green)

---

## ✨ 功能特点 / Features

- **多卡管理** — 同时追踪 Amex Platinum、Gold，Chase Sapphire Reserve、Preferred，Marriott 等多张卡
- **多用户** — 支持家庭成员各自独立追踪
- **自动账单分析** — 上传 PDF 账单，自动识别哪些福利已触发，支持批量上传
- **从网页添加新卡** — 输入信用卡介绍页网址，自动爬取福利信息
- **年度/月度/季度/半年/开关** 多种福利类型支持
- **中英文界面** — 一键切换
- **数据本地存储** — 所有数据存在本机，不上传任何服务器

---

## 📦 下载使用 / Download (End Users)

前往 **[Releases](../../releases/latest)** 页面下载最新版 `CardTracker-win64.zip`，解压后运行 `CardTracker.exe`。

**系统要求：**
- Windows 10 / 11（64位）
- [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)（Win11 已内置）

---

## 🛠 开发环境运行 / Run from Source

### 依赖安装

```bash
pip install flask flask-cors pywebview pdfplumber pycryptodome
```

### 运行

```bash
python app.py
```

浏览器也可以直接访问 `http://127.0.0.1:5099` 调试前端。

---

## 📦 打包为 EXE / Build

需要先安装 [Inno Setup 6](https://jrsoftware.org/isdl.php)（可选，用于生成安装包）。

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包（Windows）
build.bat
```

或手动执行：

```bash
python -m PyInstaller app.spec --noconfirm --distpath dist
```

输出在 `dist/CardTracker/CardTracker.exe`。

---

## 🗂 项目结构 / Project Structure

```
├── app.py          # 程序入口，PyWebView 桌面窗口
├── server.py       # Flask 后端 + SQLite 数据库 + PDF 扫描逻辑
├── index.html      # 前端（React + Tailwind CSS，单文件）
├── app.spec        # PyInstaller 打包配置
├── build.bat       # 一键打包脚本
└── README.md
```

---

## 💳 支持的信用卡 / Supported Cards

| 卡片 | 年费 | 主要福利 |
|------|------|---------|
| Amex Platinum | $895 | 旅行/酒店/Uber/航空/Equinox... |
| Amex Gold | $325 | 餐饮/Uber/Dunkin/Resy... |
| Chase Sapphire Reserve | $795 | 旅行/酒店/DoorDash/Apple... |
| Chase Sapphire Reserve Business | $795 | 旅行/酒店/Google Workspace... |
| Chase Sapphire Preferred | $95 | 酒店 |
| Chase Marriott Bonvoy Premier Plus | $95 | 免费住宿券 |

> 支持通过网页 URL 自动添加更多卡片

---

## 🤝 贡献 / Contributing

欢迎贡献新卡片数据或改进功能，请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 许可证 / License

[GNU General Public License v3.0](LICENSE)

Copyright © 2025 Yu Guan (Teddy)

本软件遵循 GPL v3 协议开源。任何基于本项目的衍生作品必须同样开源，**不得用于闭源商业产品**。
