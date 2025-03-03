# 介绍
用视觉方案把字幕提取出来

写进一个文档里

完美应对"daily task"的美剧填空



# 环境
Macbook Pro 14’ 2025 based on M4 

python3.12.7

MacOS Sequoia 15.3.1

VScode & Copilot



# 下载依赖
pip3 install easyocr numpy time mss threading opencv-python queue datetime tkinter ttk 



# 备用方案
在浏览器中下载以下文件
wget https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/craft_mlt_25k.pth
wget https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.pth

将下载的文件移动到模型目录
mv craft_mlt_25k.pth ~/.EasyOCR/model/
mv english_g2.pth ~/.EasyOCR/model/


reader = easyocr.Reader(
    ['en'],
    gpu=USE_GPU,
    model_storage_directory=os.path.expanduser('~/.EasyOCR/model'),
    download_enabled=False  # 禁用自动下载
)





# 最后
这是个临时开发的项目
readme没有写好
别喷