import tkinter as tk
from tkinter import ttk, filedialog, messagebox
# import difflib
from collections import defaultdict
# import re
from datetime import datetime
import logging
import os
# import shutil

def setup_logging(status_text):
    """配置日志处理"""
    class TextHandler(logging.Handler):
        def __init__(self, text_widget):
            super().__init__()
            self.text_widget = text_widget

        def emit(self, record):
            msg = self.format(record) + '\n'
            self.text_widget.insert(tk.END, msg)
            self.text_widget.see(tk.END)

    handler = TextHandler(status_text)
    formatter = logging.Formatter('%(asctime)s - %(message)s', '%H:%M:%S')
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def browse_file(file_path):
    """打开文件选择对话框"""
    filename = filedialog.askopenfilename(
        filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
    )
    if filename:
        file_path.set(filename)

def update_threshold_label(threshold_var, threshold_label):
    """更新相似度阈值显示"""
    threshold_label.config(text=f"{threshold_var.get():.2f}")

def initialize_log_directory():
    """初始化日志目录"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(current_dir, 'log_plus')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def get_output_filename():
    """生成输出文件名"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{timestamp}_log_plus.txt"

def process_file(file_path, threshold_var):
    """处理文件"""
    input_file = file_path.get()
    if not input_file or not os.path.exists(input_file):
        messagebox.showerror("错误", "请选择有效的输入文件")
        return

    try:
        # 使用新的输出路径
        log_dir = initialize_log_directory()
        output_filename = get_output_filename()
        output_file = os.path.join(log_dir, output_filename)

        logging.info(f"开始处理文件: {input_file}")

        # 存储句子和时间戳
        sentence_groups = defaultdict(list)

        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:  # 跳过空行
                    continue
                    
                # 假设每行的格式为: "时间戳 句子内容"
                try:
                    # 分割时间戳和句子内容
                    parts = line.split(' ', 1)
                    if len(parts) != 2:
                        continue
                        
                    timestamp_str, sentence = parts
                    try:
                        # 解析时间戳
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d_%H:%M:%S')
                    except ValueError:
                        continue
                    
                    # 将句子和时间戳添加到对应的组中
                    sentence_groups[sentence].append((sentence, timestamp))
                except Exception as e:
                    logging.warning(f"处理行时出错: {line}, 错误: {str(e)}")
                    continue

        # 写入结果
        original_stats = os.stat(input_file)

        with open(output_file, 'w', encoding='utf-8') as f:
            for sentence, occurrences in sentence_groups.items():
                if not occurrences:  # 跳过空组
                    continue
                    
                timestamps = [t for _, t in occurrences]
                
                f.write(f"原始句子: {sentence}\n")
                f.write(f"出现次数: {len(occurrences)}\n")
                f.write(f"首次出现: {min(timestamps).strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"最后出现: {max(timestamps).strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n")

        os.utime(output_file, (original_stats.st_atime, original_stats.st_mtime))

        logging.info(f"处理完成，结果保存至: {output_file}")
        messagebox.showinfo("成功", "文件处理完成！")

    except Exception as e:
        logging.error(f"处理过程中出错: {str(e)}")
        messagebox.showerror("错误", f"处理失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("文本相似度处理工具")
    root.geometry("612x395")

    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # 文件选择部分
    file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="5")
    file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    file_path = tk.StringVar()
    file_entry = ttk.Entry(file_frame, textvariable=file_path, width=50)
    file_entry.grid(row=0, column=0, padx=5)

    browse_button = ttk.Button(
        file_frame,
        text="浏览",
        command=lambda: browse_file(file_path)
    )
    browse_button.grid(row=0, column=1, padx=5)

    # 相似度阈值调整
    threshold_frame = ttk.LabelFrame(main_frame, text="相似度阈值", padding="5")
    threshold_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    threshold_var = tk.DoubleVar(value=0.85)
    threshold_scale = ttk.Scale(
        threshold_frame,
        from_=0.5,
        to=1.0,
        variable=threshold_var,
        orient=tk.HORIZONTAL,
        length=200
    )
    threshold_scale.grid(row=0, column=0, padx=5)

    threshold_label = ttk.Label(threshold_frame, text="0.85")
    threshold_label.grid(row=0, column=1, padx=5)

    # 设置阈值标签更新回调
    threshold_var.trace('w', lambda *args: update_threshold_label(threshold_var, threshold_label))

    # 处理按钮
    process_button = ttk.Button(
        main_frame,
        text="开始处理",
        command=lambda: process_file(file_path, threshold_var)
    )
    process_button.grid(row=2, column=0, columnspan=2, pady=10)

    # 状态显示
    status_frame = ttk.LabelFrame(main_frame, text="处理状态", padding="5")
    status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    status_text = tk.Text(status_frame, height=10, width=50, wrap=tk.WORD)
    status_text.grid(row=0, column=0, padx=5, pady=5)

    scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=status_text.yview)
    scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    status_text['yscrollcommand'] = scrollbar.set

    # 配置日志
    setup_logging(status_text)
    
    # 添加启动成功提示
    logging.info("程序成功启动")

    root.mainloop()