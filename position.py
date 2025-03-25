'''
单纯用于获取鼠标的坐标
与主程序无关
此段程序(position.py)全部由Chat-GPT 4-Turbo, 编写
'''

"""
已经被整合到main.py中
"""

import pyautogui
import tkinter

class the_mouse_position():
    global update_mouse_position
    
    def update_mouse_position():
        # 获取鼠标当前的位置
        x, y = pyautogui.position()
        # 更新标签显示的位置
        position_label.config(text=f"Mouse Position: X: {x}, Y: {y}")
        # 每100毫秒调用一次自己，以便更新位置
        root.after(100, update_mouse_position)

if __name__ == "__main__" :
    # 创建主窗口
    root = tkinter.Tk()
    root.title("Mouse Position Tracker")

    # 创建一个标签来显示鼠标位置
    position_label = tkinter.Label(root, text="", font=("Arial", 14))
    position_label.pack(padx=20, pady=20)

    # 开始更新鼠标位置
    update_mouse_position()

    # 启动主循环
    root.mainloop()