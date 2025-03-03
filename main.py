import numpy as np
import easyocr
import time
from mss import mss
import threading
import cv2
from queue import Queue
import datetime  
import tkinter as tk
from tkinter import ttk  # 导入ttk，提供更现代的控件样式
# import requests
# from requests.adapters import HTTPAdapter
# from requests.packages.urllib3.util.retry import Retry
import os

"""唯一需要修改的数据"""
# 屏幕截图区域坐标
# 左上角
x1 = 5
y1 = 877
#右下角
x3 = 1505
y3 = 921
"""唯一需要修改的数据"""

# 设置代理（根据实际情况修改）
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'  # 如果使用 Clash
# 或
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:1087'  # 如果使用 V2Ray

# 配置参数
SCREEN_REGION = {'top': y1, 'left': x1, 'width': x3 - x1, 'height': y3 - y1}
USE_GPU = True  # 启用 M1/M2 GPU 加速
PREPROCESS = True  # 开启预处理（针对复杂背景）

# 全局变量，用于控制程序运行状态
running = False
stable = True  # 假设初始状态是稳定运行的

# 添加重试逻辑
def initialize_reader(max_retries = 3):
    # 确保目录存在
    model_dir = os.path.expanduser('~/.EasyOCR/model')
    os.makedirs(model_dir, exist_ok=True)
    
    for attempt in range(max_retries):
        try:
            print(f"尝试初始化 EasyOCR ({attempt + 1}/{max_retries})...")
            return easyocr.Reader(
                ['en'],
                gpu=USE_GPU,
                model_storage_directory=model_dir,
                download_enabled=True,
                verbose=True  # 显示详细下载信息
            )
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"初始化失败: {str(e)}")
                raise e
            print(f"初始化失败，等待重试... ({attempt + 1}/{max_retries})")
            print(f"错误信息: {str(e)}")
            time.sleep(5)  # 等待5秒后重试

# 使用重试逻辑初始化
reader = initialize_reader()

# 多线程共享队列（截图 -> OCR）
frame_queue = Queue(maxsize=2)  # 避免内存堆积

# 在导入部分下方添加日志文件相关的初始化代码
def initialize_log_directory():
    """初始化日志目录"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
    os.makedirs(log_dir, exist_ok=True)
    # 生成日志文件名：格式为 YYYY-MM-DD_HH-MM-SS_log.txt
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"{timestamp}_log.txt")
    return log_file

# 在程序启动时初始化日志文件路径
LOG_FILE = initialize_log_directory()

def screen_capture():
    """高速截屏线程"""
    global running, stable
    try:
        with mss() as sct:
            while running:  # 只有running为True时才运行
                frame = np.array(sct.grab(SCREEN_REGION))  # 直接截取为 numpy 数组
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)  # 转换颜色通道
                if PREPROCESS:
                    # 极简预处理（按需调整）
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    frame = cv2.merge([binary, binary, binary])  # 转为3通道
                if frame_queue.empty():
                    frame_queue.put(frame)
                time.sleep(0.1)  # 降低CPU占用
        stable = False  # 线程退出，标记为不稳定
    except Exception as e:
        print(f"截图线程出错: {e}")
        stable = False

def ocr_process():
    """OCR 处理线程"""
    global running, stable
    try:
        while running:
            if not frame_queue.empty():
                frame = frame_queue.get()
                results = reader.readtext(
                    frame,
                    decoder='beamsearch',  # 加速解码
                    batch_size=4,  # 利用多线程
                    detail=0,
                    paragraph=True  # 合并段落
                )
                if results:
                    ocr_text = results[0]  # 获取识别到的文字
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取当前时间戳
                    log_message = f"{timestamp}: {ocr_text}\n"  # 构建日志消息

                    print("识别结果:", ocr_text)  # 打印到控制台

                    # 使用全局定义的日志文件路径
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(log_message)
            time.sleep(1)  # 降低CPU占用
    except Exception as e:
        print(f"OCR线程出错: {e}")
        stable = False

def start_stop():
    """启动/停止程序"""
    global running
    running = not running
    if running:
        start_stop_button.config(text="停止")
        status_label.config(text="程序已启动", foreground="green")
        # 启动线程
        threading.Thread(target=screen_capture, daemon=True).start()
        threading.Thread(target=ocr_process, daemon=True).start()
    else:
        start_stop_button.config(text="启动")
        status_label.config(text="程序已停止", foreground="red")

# 创建GUI窗口
root = tk.Tk()
root.title("字幕提取工具")
root.geometry("400x200")

# 使用ttk主题
style = ttk.Style()
style.theme_use('clam')  # 尝试 'clam', 'alt', 'default', 'classic'

# 坐标显示
coordinates_label = ttk.Label(root, text=f"坐标: x1={x1}, y1={y1}, x3={x3}, y3={y3}")
coordinates_label.pack(pady=5)

# 启动/停止按钮
start_stop_button = ttk.Button(root, text="启动", command=start_stop)
start_stop_button.pack(pady=10)

# 状态标签
status_label = ttk.Label(root, text="程序未启动", foreground="red")
status_label.pack(pady=5)

# 稳定运行状态标签
def update_stability_label():
    if stable:
        stability_label.config(text="运行稳定", foreground="green")
    else:
        stability_label.config(text="运行不稳定", foreground="red")
    root.after(5000, update_stability_label)  # 每5秒检查一次

stability_label = ttk.Label(root, text="正在初始化...", foreground="gray")
stability_label.pack(pady=5)

# 初始状态更新
update_stability_label()

# 运行GUI主循环
root.mainloop()