"""
app.py — 桌面应用入口
启动 Flask 后端线程，然后用 pywebview (EdgeChromium) 打开原生桌面窗口
"""
import sys
import os
import threading
import time
import urllib.request
import webview

# 确保 PyInstaller 打包后也能找到 server 模块
if hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)

from server import app as flask_app, init_db

PORT = 5000


def start_flask():
    flask_app.run(
        host='127.0.0.1',
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def wait_for_flask(timeout=15):
    """轮询直到 Flask 真正开始响应请求"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{PORT}/', timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


if __name__ == '__main__':
    # 初始化数据库
    init_db()

    # 在后台线程启动 Flask
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # 等到 Flask 真正就绪再打开窗口
    wait_for_flask()

    # 创建原生桌面窗口，明确使用 EdgeChromium (WebView2) 引擎
    # 时间戳参数确保 WebView2 每次都加载最新页面，不使用缓存
    window = webview.create_window(
        title='信用卡追踪',
        url=f'http://127.0.0.1:{PORT}/?_={int(time.time())}',
        width=960,
        height=740,
        min_size=(700, 580),
        resizable=True,
        text_select=False,
    )
    # gui='edgechromium' 强制使用 Edge WebView2，支持现代 JS/React
    webview.start(gui='edgechromium', debug=True)
