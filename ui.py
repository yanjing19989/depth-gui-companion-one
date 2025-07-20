import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageEnhance
import os
import cv2
import torch
import numpy as np
from safetensors.torch import load_file
from depth_anything_v2.dpt import DepthAnythingV2
import yaml
from depth_render import run_hologram_render

def set_center(window, width=300, height=150):
    x = (window.winfo_screenwidth() - width) / 2
    y = (window.winfo_screenheight() - height - 200) / 2
    window.geometry("%dx%d+%d+%d" % (width, height, x, y))

class ImageConverterApp(ctk.CTk):
    def __init__(self):
        ctk.set_widget_scaling(1.2)
        ctk.set_window_scaling(1.2)
        super().__init__()

        self.title("Image Converter")
        self.geometry("900x800")
        set_center(self, 900, 800)

        self.tabview = ctk.CTkTabview(self, width=900, height=800)
        self.tabview.pack()
        self.image_converter_tab()
        self.mov_converter_tab()
        self.batch_converter_tab()

    def image_converter_tab(self):
        self.tabview.add("图像转换")
        self.tabview.tab("图像转换").columnconfigure((0,1), weight=1)
        self.tabview.tab("图像转换").rowconfigure(0, weight=1)

        # 左侧源图像展示框
        left_frame = ctk.CTkFrame(self.tabview.tab("图像转换"), width=400, height=600)
        left_frame.grid(row=0, column=0, padx=20, pady=20)

        source_image_preview_name = ctk.CTkLabel(left_frame, text="源图像")
        source_image_preview_name.pack()
        
        self.source_image_preview = ctk.CTkLabel(left_frame, text="点击选择源图像", 
                                                 width=400, height=200, bg_color="#202020", font=("黑体", 16))
        self.source_image_preview.pack()
        self.source_image_preview.bind("<Button-1>", self.select_source_image)

        # 右侧目标图像展示框
        right_frame = ctk.CTkFrame(self.tabview.tab("图像转换"), width=400, height=600)
        right_frame.grid(row=0, column=1, padx=20, pady=20)

        target_image_preview_name = ctk.CTkLabel(right_frame, text="深度图像")
        target_image_preview_name.pack()
        
        self.target_image_preview = ctk.CTkLabel(right_frame, text="请先选择源图像", 
                                                 width=400, height=200, bg_color="#202020", font=("黑体", 16))
        self.target_image_preview.pack()

        # 添加复选框
        down_frame_batch = ctk.CTkFrame(self.tabview.tab("图像转换"), width=400, height=600)
        down_frame_batch.grid(row=1, column=0, columnspan=2, padx=20, pady=20)
        down_frame_batch.columnconfigure((0, 1, 2), weight=1)

        self.enhance_var = ctk.BooleanVar(value=False)
        enhance_checkbox = ctk.CTkCheckBox(down_frame_batch, text="增强图像饱和度", variable=self.enhance_var)
        enhance_checkbox.grid(row=0, column=0, padx=5)
        self.force_916 = ctk.BooleanVar(value=False)
        force_916_checkbox = ctk.CTkCheckBox(down_frame_batch, text="强制9:16", variable=self.force_916)
        force_916_checkbox.grid(row=0, column=1, padx=5)
        self.save_interlaced_var = ctk.BooleanVar(value=False)
        save_interlaced_checkbox = ctk.CTkCheckBox(down_frame_batch, text="生成交织图", variable=self.save_interlaced_var)
        save_interlaced_checkbox.grid(row=0, column=2, padx=5)

        # 底部转换按钮
        convert_button = ctk.CTkButton(self.tabview.tab("图像转换"), text="转换", command=self.start_convert_image)
        convert_button.grid(row=4, column=0, columnspan=2, pady=10)

        # 滑条拖到选择数值
        self.slider = ctk.CTkSlider(self.tabview.tab("图像转换"), from_=378, to=840, number_of_steps=33, 
                                    command=lambda x: self.slide_label.configure(text=int(x)))
        self.slider.set(518)
        self.slider.grid(row=2, column=0, columnspan=2)
        slide_label = ctk.CTkLabel(self.tabview.tab("图像转换"), text=int(self.slider.get()))
        slide_label.grid(row=3, column=0, columnspan=2)

        self.source_image_path = None
        
    def select_source_image(self, event):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.bmp;*.gif")])
        if file_path:
            self.source_image_path = file_path
            image = Image.open(file_path)
            photo = ctk.CTkImage(image, size=(400, image.height * 400 // image.width))
            self.source_image_preview.configure(image=photo, text="")

    def start_convert_image(self):
        if self.source_image_path:
            target_image_path = os.path.splitext(self.source_image_path)[0] + "_depth.png"
            # 处理图像
            self.convert_image(self.source_image_path, target_image_path, input_size=int(self.slider.get()))
            # 显示目标图像
            image = Image.open(target_image_path)
            photo = ctk.CTkImage(image, size=(400, image.height * 400 // image.width))
            self.target_image_preview.configure(image=photo, text="")
            messagebox.showinfo("提示", "转换完成！")

    def mov_converter_tab(self):
        self.tabview.add("视频转换")
        self.tabview.tab("视频转换").columnconfigure((0,1), weight=1)
        self.tabview.tab("视频转换").rowconfigure(0, weight=1)

        # 左侧源视频展示框
        left_frame_video = ctk.CTkFrame(self.tabview.tab("视频转换"), width=400, height=600)
        left_frame_video.grid(row=0, column=0, padx=20, pady=20)
        
        self.source_video_preview = ctk.CTkLabel(left_frame_video, text="点击选择源视频", 
                                                 width=400, height=200, bg_color="#202020", font=("黑体", 16))
        self.source_video_preview.pack()
        self.source_video_preview.bind("<Button-1>", self.select_source_video)

        # 右侧目标视频展示框
        right_frame_video = ctk.CTkFrame(self.tabview.tab("视频转换"), width=400, height=600)
        right_frame_video.grid(row=0, column=1, padx=20, pady=20)

        self.target_video_preview = ctk.CTkLabel(right_frame_video, text="请先选择源视频", 
                                                 width=400, height=200, bg_color="#202020", font=("黑体", 16))
        self.target_video_preview.pack()

        # 底部转换按钮
        convert_video_button = ctk.CTkButton(self.tabview.tab("视频转换"), text="转换", command=self.start_convert_video)
        convert_video_button.grid(row=3, column=0, columnspan=2, pady=10)

        # 滑条拖到选择数值
        self.video_slider = ctk.CTkSlider(self.tabview.tab("视频转换"), from_=378, to=840, number_of_steps=33, 
                                          command=lambda x: self.video_slide_label.configure(text=int(x)))
        self.video_slider.set(518)
        self.video_slider.grid(row=1, column=0, columnspan=2)
        video_slide_label = ctk.CTkLabel(self.tabview.tab("视频转换"), text=int(self.video_slider.get()))
        video_slide_label.grid(row=2, column=0, columnspan=2)

        self.source_video_path = None

    def select_source_video(self, event):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.mov;*.avi;*.mkv")])
        if file_path != self.source_video_path and file_path:
            self.source_video_path = file_path
            self.source_video_preview.configure(text=os.path.basename(file_path))
            self.preview_video(file_path)
    
    def preview_video(self, file_path):
        # use ffmpeg to extract the all frame of the video
        os.system("rmdir /s /q tmp && mkdir tmp")
        os.system(f"ffmpeg -i {file_path} -vf fps=30 -qscale:v 2 tmp/%05d.jpg")
        image = Image.open("tmp/00001.jpg")
        photo = ctk.CTkImage(image, size=(400, image.height * 400 // image.width))
        self.source_video_preview.configure(image=photo)

    def start_convert_video(self):
        if self.source_video_path:
            target_video_path = os.path.splitext(self.source_video_path)[0] + "_converted.mp4"
            # convert tmp/%d.jpg to greyscale
            self.show_progress_window()
            total = len(os.listdir("tmp"))
            self.progressbar.configure(determinate_speed=50.0/total)
            self.progress_callback(0, 100)
            for file in os.listdir("tmp"):
                file_path = os.path.join("tmp", file)
                self.convert_image(file_path, file_path, input_size=int(self.video_slider.get()))
                self.progressbar.step()
                self.progressbar.update()
            
            self.target_video_preview.configure(text=os.path.basename(target_video_path))
            # use ffmpeg to convert the frames to video
            os.system(f"ffmpeg -y -i tmp/%05d.jpg -c:v libx264 -vf fps=30 {target_video_path}")
            self.progress_callback(100, 100)
            self.progress_window.destroy()
            image = Image.open("tmp/00001.jpg")
            photo = ctk.CTkImage(image, size=(400, image.height * 400 // image.width))
            self.target_video_preview.configure(image=photo)
            messagebox.showinfo("提示", "转换完成！")

    def progress_callback(self, current, total):
        self.progressbar.set(current/total*100)
        self.progressbar.update()
    
    def select_source_directory(self, event):
        directory = filedialog.askdirectory(title="选择源目录")
        if directory:
            self.source_directory = directory
            # 显示完整路径，和当前目录下的图片数量
            source_dir_info = f"{directory} \n ({len(os.listdir(directory))} files)"
            self.source_dir_label.configure(text=source_dir_info)
    
    def select_target_directory(self, event):
        directory = filedialog.askdirectory(title="选择目标目录")
        if directory:
            self.target_directory = directory
            self.target_dir_label.configure(text=directory)

    def start_convert_batch(self):
        if not self.source_directory:
            messagebox.showerror("错误", "请先选择源目录")
            return
        if self.target_dir_label.cget("text") == "点击选择目标目录":
            self.target_directory = self.source_directory + "/output/"
            if not os.path.exists(self.target_directory):
                os.makedirs(self.target_directory)
            self.target_dir_label.configure(text=self.target_directory)

        self.show_progress_window()
        self.progressbar.configure(determinate_speed=50.0/len(os.listdir(self.source_directory)))
        self.progress_callback(0, 100)

        for file in os.listdir(self.source_directory):
            file_path = os.path.join(self.source_directory, file)
            if os.path.isfile(file_path) and file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                target_file_path = os.path.join(self.target_directory, f"{os.path.splitext(file)[0]}_d.png")
                self.convert_image(file_path, target_file_path, input_size=int(self.batch_slider.get()))
                self.progressbar.step()
                self.progressbar.update()

        self.progress_callback(100, 100)
        self.progress_window.destroy()
        messagebox.showinfo("提示", "批量转换完成！")

    def batch_converter_tab(self):
        self.tabview.add("批量转换")
        self.tabview.tab("批量转换").columnconfigure((0,1), weight=1)
        self.tabview.tab("批量转换").rowconfigure(0, weight=1)

        # 左侧源目录选择框
        left_frame_batch = ctk.CTkFrame(self.tabview.tab("批量转换"), width=400, height=600)
        left_frame_batch.grid(row=0, column=0, padx=20, pady=20)
        
        source_dir_label_name = ctk.CTkLabel(left_frame_batch, text="源目录")
        source_dir_label_name.pack()

        self.source_dir_label = ctk.CTkLabel(left_frame_batch, text="点击选择源目录", 
                                             width=400, height=200, bg_color="#202020", font=("黑体", 16))
        self.source_dir_label.pack()
        self.source_dir_label.bind("<Button-1>", self.select_source_directory)

        # 右侧目标目录选择框
        right_frame_batch = ctk.CTkFrame(self.tabview.tab("批量转换"), width=400, height=600)
        right_frame_batch.grid(row=0, column=1, padx=20, pady=20)

        target_dir_label_name = ctk.CTkLabel(right_frame_batch, text="目标目录")
        target_dir_label_name.pack()

        self.target_dir_label = ctk.CTkLabel(right_frame_batch, text="点击选择目标目录", 
                                             width=400, height=200, bg_color="#202020", font=("黑体", 16))
        self.target_dir_label.pack()
        self.target_dir_label.bind("<Button-1>", self.select_target_directory)

        # 添加复选框
        down_frame_batch = ctk.CTkFrame(self.tabview.tab("批量转换"), width=400, height=600)
        down_frame_batch.grid(row=1, column=0, columnspan=2, padx=20, pady=20)
        down_frame_batch.columnconfigure((0, 1, 2), weight=1)

        enhance_checkbox = ctk.CTkCheckBox(down_frame_batch, text="增强图像饱和度", variable=self.enhance_var)
        enhance_checkbox.grid(row=0, column=0, padx=5)
        force_916_checkbox = ctk.CTkCheckBox(down_frame_batch, text="强制9:16", variable=self.force_916)
        force_916_checkbox.grid(row=0, column=1, padx=5)
        save_interlaced_checkbox = ctk.CTkCheckBox(down_frame_batch, text="生成交织图", variable=self.save_interlaced_var)
        save_interlaced_checkbox.grid(row=0, column=2, padx=5)

        # 底部转换按钮
        convert_batch_button = ctk.CTkButton(self.tabview.tab("批量转换"), text="转换", command=self.start_convert_batch)
        convert_batch_button.grid(row=4, column=0, columnspan=2, pady=10)

        # 滑条拖到选择数值
        self.batch_slider = ctk.CTkSlider(self.tabview.tab("批量转换"), from_=378, to=840, number_of_steps=33,
                                          command=lambda x: self.batch_slide_label.configure(text=int(x)))
        self.batch_slider.set(518)
        self.batch_slider.grid(row=2, column=0, columnspan=2)
        batch_slide_label = ctk.CTkLabel(self.tabview.tab("批量转换"), text=int(self.batch_slider.get()))
        batch_slide_label.grid(row=3, column=0, columnspan=2)

        self.source_directory = None

    def show_progress_window(self):
        self.progress_window = ctk.CTkToplevel(self)
        self.progress_window.title("处理中")
        set_center(self.progress_window, 300, 40)
        self.progressbar = ctk.CTkProgressBar(self.progress_window, orientation="horizontal")
        self.progressbar.pack(fill="both", padx=10, pady=10)
        self.progress_window.attributes("-topmost", True)
        self.progress_window.deiconify()
        self.progress_window.update()

    def convert_image(self, image_path, save_path, input_size=518):
        if self.enhance_var or self.force_916:
            tmp_directory = self.target_directory + "/tmp/"
            if not os.path.exists(tmp_directory):
                os.makedirs(tmp_directory)
            image = Image.open(image_path)
            if self.enhance_var:
                image = enhance_image(image)
            if self.force_916:
                width, height = image.size
                # 计算9:16的目标高度
                target_height = int(width * 16 / 9)
                if target_height > height:
                    # 如果目标高度大于原图高度，则以高度为基准，裁剪宽度
                    target_width = int(height * 9 / 16)
                    left = (width - target_width) // 2
                    right = left + target_width
                    top = 0
                    bottom = height
                    image = image.crop((left, top, right, bottom))
                else:
                    # 以宽度为基准，裁剪高度
                    top = (height - target_height) // 2
                    bottom = top + target_height
                    left = 0
                    right = width
                    image = image.crop((left, top, right, bottom))
            image_path = tmp_directory + os.path.splitext(os.path.basename(image_path))[0] + ".jpg"
            image.save(image_path, quality=90)
        gen_depth_image(image_path, save_path, input_size)
        if self.save_interlaced_var:
            config = load_config_yaml("tools/depth_config.yaml")
            interlaced_directory = self.target_directory + "/interlaced/"
            if not os.path.exists(interlaced_directory):
                os.makedirs(interlaced_directory)
            # 合并命令行参数覆盖yaml
            params = dict(config)
            params['image_file'] = image_path
            params['depth_file'] = save_path
            params['output_file'] = interlaced_directory + f"{os.path.splitext(os.path.basename(image_path))[0]}.png"
            run_hologram_render(**params)

            
def load_config_yaml(yaml_path):
    if not os.path.exists(yaml_path):
        return {}
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def gen_depth_image(image_path, save_path, input_size=518):
    raw_img = cv2.imdecode(np.fromfile(image_path,dtype=np.uint8),-1)

    depth = model.infer_image(raw_img, input_size) # HxW raw depth map in numpy
    depth_normalized = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
    depth_normalized = depth_normalized.astype(np.uint8)

    cv2.imencode('.png', depth_normalized)[1].tofile(save_path)

def enhance_image(image):
    # 提高image饱和度30%
    enhancer = ImageEnhance.Color(image)
    image = enhancer.enhance(1.3)
    return image

if __name__ == "__main__":
    DEVICE = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
    encoder = 'vitl' # or 'vits', 'vitb', 'vitl'
    #encoder = 'vitb'
    depth_path = f'E:/AI/webui_forge_cu121_torch231/webui/models/ControlNetPreprocessor/depth_anything_v2/depth_anything_v2_{encoder}.safetensors'
    # 配置模型
    model_configs = {
        'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
        'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
        'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
        'vitg': {'encoder': 'vitg', 'features': 384, 'out_channels': [1536, 1536, 1536, 1536]}
    }

    model = DepthAnythingV2(**model_configs[encoder])
    model.load_state_dict(load_file(depth_path))
    model = model.to(DEVICE).eval().half()

    app = ImageConverterApp()
    app.mainloop()