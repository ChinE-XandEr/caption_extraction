import numpy as np
import easyocr
import time
import pyautogui
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
# import gc
# 添加线程锁
from threading import Lock  # 用于线程同步
import logging  # 用于日志记录
import sys
from tkinter import messagebox  # 添加 messagebox 导入

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('error.log'),
        logging.StreamHandler()
    ]
)

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
USE_GPU = True  # 启用 M系列的 Metal GPU 加速
PREPROCESS = True  # 开启预处理（针对复杂背景）

# 全局变量，用于控制程序运行状态
running = False
stable = True  # 假设初始状态是稳定运行的
updating_mouse_position = False  # 统一变量名
mouse_x = 0  # 初始化鼠标位置变量
mouse_y = 0

# 添加GPU加速切换逻辑
def toggle_gpu_acceleration():
    # 切换GPU加速状态
    global USE_GPU
    USE_GPU = not USE_GPU
    if USE_GPU:
        gpu_acceleration_button.config(text="关闭GPU加速")
        print("已开启GPU加速")
    else:
        gpu_acceleration_button.config(text="开启GPU加速")
        print("已关闭GPU加速")

#时时获取鼠标位置
def mouse_position():
    """更新鼠标位置"""
    global updating_mouse_position, mouse_x, mouse_y
    if updating_mouse_position:
        mouse_x, mouse_y = pyautogui.position()
        the_mouse_position.config(text=f"鼠标位置：x={mouse_x}, y={mouse_y}")
    root.after(100, mouse_position)

def toggle_mouse_tracking():
    """切换鼠标位置追踪状态"""
    global updating_mouse_position
    updating_mouse_position = not updating_mouse_position
    if updating_mouse_position:
        
        update_mouse_postion_button.config(text="停止追踪")
    else:
        update_mouse_postion_button.config(text="开始追踪")

# 添加重试逻辑
def initialize_reader(max_retries = 3):
    # 确保目录存在
    model_dir = os.path.expanduser('~/.EasyOCR/model')
    os.makedirs(model_dir, exist_ok=True)
    
    for attempt in range(max_retries):
        try:
            print(f"尝试初始化 EasyOCR ({attempt + 1}/{max_retries})...")
            reader = easyocr.Reader(
                ['en'],
                gpu=USE_GPU,
                model_storage_directory=model_dir,
                download_enabled=True,
                verbose=True
            )
            # 添加简单的测试确保初始化成功
            test_result = reader.readtext(np.zeros((100, 100, 3), dtype=np.uint8))
            return reader
        except Exception as e:
            print(f"初始化失败: {str(e)}")
            time.sleep(5)
    # 添加初始化失败的处理
    raise Exception("EasyOCR 初始化失败，已达到最大重试次数")

# 使用重试逻辑初始化
try:
    reader = initialize_reader()
except Exception as e:
    logging.error(f"EasyOCR 初始化失败: {e}")
    sys.exit(1)

# 多线程共享队列（截图 -> OCR）
frame_queue = Queue(maxsize=2)  # 增加队列容量

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

# 创建锁对象
frame_lock = Lock()

def screen_capture():
    """高速截屏线程"""
    global running, stable
    logging.info("截图线程启动")
    try:
        with mss() as sct:
            while running:
                try:
                    with frame_lock:
                        frame = np.array(sct.grab(SCREEN_REGION))
                        if frame is None or frame.size == 0:
                            logging.error("截图失败：空图像")
                            continue
                            
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                        if PREPROCESS:
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                            frame = cv2.merge([binary, binary, binary])
                            
                        if frame_queue.empty():
                            frame_queue.put(frame)
                            logging.debug("成功截取新帧")
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(f"截图过程错误: {e}")
                    continue
        stable = False
    except Exception as e:
        logging.error(f"截图线程出错: {e}")
        stable = False
    logging.info("截图线程退出")

def ocr_process():
    """OCR 处理线程"""
    global running, stable
    logging.info("OCR线程启动")
    try:
        while running:
            try:
                if not frame_queue.empty():
                    frame = frame_queue.get()
                    logging.debug("获取到新帧，开始OCR识别")
                    results = reader.readtext(
                        frame,
                        decoder='beamsearch',
                        batch_size=4,
                        detail=0,
                        paragraph=True
                    )
                    if results and isinstance(results[0], str):
                        ocr_text = results[0]
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_message = f"{timestamp}: {ocr_text}\n"
                        
                        # 写入日志文件
                        with open(LOG_FILE, "a", encoding="utf-8") as f:
                            f.write(log_message)
                        
                        logging.info(f"识别结果: {ocr_text}")
                    else:
                        logging.warning("OCR未识别到文本")
                time.sleep(0.2)  # 降低CPU占用
            except Exception as e:
                logging.error(f"OCR识别错误: {e}")
                continue
    except Exception as e:
        logging.error(f"OCR线程出错: {e}")
        stable = False
    logging.info("OCR线程退出")

# 在程序启动前添加坐标检查
def validate_coordinates():
    if x1 < 0 or y1 < 0 or x3 <= x1 or y3 <= y1:
        logging.error(f"无效的坐标值: x1={x1}, y1={y1}, x3={x3}, y3={y3}")
        return False
    return True

def start_stop():
    """启动/停止程序"""
    global running
    running = not running
    if running:
        logging.info("尝试启动程序...")
        if not validate_coordinates():
            messagebox.showerror("错误", "无效的坐标值")
            return
        start_stop_button.config(text="停止")
        status_label.config(text="程序已启动", foreground="green")
        # 启动线程
        try:
            threading.Thread(target=screen_capture, daemon=True).start()
            threading.Thread(target=ocr_process, daemon=True).start()
            logging.info("线程启动成功")
        except Exception as e:
            logging.error(f"线程启动失败: {e}")
            running = False
            start_stop_button.config(text="启动")
            status_label.config(text="启动失败", foreground="red")
    else:
        logging.info("停止程序")
        start_stop_button.config(text="启动")
        status_label.config(text="程序已停止", foreground="red")

# 在主窗口创建之前添加
def handle_exception(exc_type, exc_value, exc_traceback):
    logging.error("未捕获的异常", exc_info=(exc_type, exc_value, exc_traceback))

# GPU 加速状态标签更新
def update_gpu_status_label():
    if USE_GPU:
        gpu_status_label.config(text="GPU加速已开启", foreground="green")
    else:
        gpu_status_label.config(text="GPU加速已关闭", foreground="red")
    root.after(5000, update_gpu_status_label)  # 每5秒检查一次

# 稳定运行状态标签更新
def update_stability_label():
    if stable:
        stability_label.config(text="运行稳定", foreground="green")
    else:
        stability_label.config(text="运行不稳定", foreground="red")
    root.after(5000, update_stability_label)  # 每5秒检查一次

def on_closing():
    # 程序关闭时的清理工作
    global running
    running = False
    logging.info("程序正在关闭...")
    root.quit()

sys.excepthook = handle_exception

if __name__ == "__main__":
    root = tk.Tk()
    root.title("字幕提取工具")
    root.geometry("264x454")

    # 主框架
    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # 鼠标位置追踪框架
    mouse_frame = ttk.LabelFrame(main_frame, text="鼠标位置追踪", padding="5")
    mouse_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    update_mouse_postion_button = ttk.Button(
        mouse_frame,
        text="开始追踪",
        command=toggle_mouse_tracking,
        width=20
    )
    update_mouse_postion_button.grid(row=0, column=0, padx=5, pady=5)

    the_mouse_position = ttk.Label(mouse_frame, text="鼠标位置：x=0, y=0")
    the_mouse_position.grid(row=1, column=0, padx=5, pady=5)

    # GPU控制框架
    gpu_frame = ttk.LabelFrame(main_frame, text="GPU设置", padding="5")
    gpu_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    gpu_acceleration_button = ttk.Button(
        gpu_frame,
        text="开启GPU加速",
        command=toggle_gpu_acceleration,
        width=20
    )
    gpu_acceleration_button.grid(row=0, column=0, padx=5, pady=5)

    gpu_status_label = ttk.Label(gpu_frame, text="GPU加速已开启", foreground="green")
    gpu_status_label.grid(row=1, column=0, padx=5, pady=5)

    # 运行控制框架
    control_frame = ttk.LabelFrame(main_frame, text="运行控制", padding="5")
    control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    start_stop_button = ttk.Button(
        control_frame,
        text="启动",
        command=start_stop,
        width=20
    )
    start_stop_button.grid(row=0, column=0, padx=5, pady=5)

    # 状态显示框架
    status_frame = ttk.LabelFrame(main_frame, text="运行状态", padding="5")
    status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    coordinates_label = ttk.Label(
        status_frame,
        text=f"截图区域: ({x1}, {y1}) - ({x3}, {y3})"
    )
    coordinates_label.grid(row=0, column=0, padx=5, pady=5)

    status_label = ttk.Label(status_frame, text="程序未启动", foreground="red")
    status_label.grid(row=1, column=0, padx=5, pady=5)

    stability_label = ttk.Label(status_frame, text="正在初始化...", foreground="gray")
    stability_label.grid(row=2, column=0, padx=5, pady=5)

    # 启动更新函数
    mouse_position()
    update_stability_label()
    update_gpu_status_label()

    # 设置窗口关闭处理
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # 运行GUI主循环
    root.mainloop()