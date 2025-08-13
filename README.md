# depth_gui_companion_one

[English](#english-version) | [中文](#depth_gui_companion_one)

一个用于 Companion One 等柱状透镜/裸眼3D 显示器的深度与交织图生成工具。

本项目提供：
- 基于 Depth Anything V2 的单图/视频/批量深度图生成 GUI（CustomTkinter）。
- 基于 ModernGL 的离屏渲染器，将彩色图 + 深度图转换为符合屏参的 3D 交织图（interlaced PNG）。
- 通过 YAML 配置与命令行参数精细化控制渲染参数（线数、倾斜度、偏差、阈值、缩放偏移、模糊与边框等）。


## 功能一览
- 图像转换
  - 选择单张图片，生成灰度深度图（支持输入分辨率 378–840 步进可调）。
  - 可选：增强饱和度、强制裁剪为 9:16、在生成深度图后自动生成交织图。
- 视频转换
  - 通过 ffmpeg 抽帧，逐帧生成深度图并回编为视频（深度视频）。
  - 可选同上增强/裁剪/生成交织图（交织图为逐帧 PNG，转换开销较大）。
- 批量转换
  - 对目录内图片批处理生成深度图，可选增强/裁剪/生成交织图。
- 交织渲染（命令行或由 GUI 调用）
  - 读取彩色图与对应深度图，输出面向指定显示器参数的交织 PNG。


## 目录结构
- `ui.py`：GUI 主程序（图像/视频/批量）。
- `depth_render.py`：ModernGL 渲染交织图（离屏），可命令行调用。
- `depth_config.yaml`：交织渲染默认参数配置（可被命令行覆盖）。
- `shaders/vertex_shader.glsl`、`shaders/depth_fragment_shader.glsl`：渲染着色器。
- `depth_anything_v2/`：Depth Anything V2 推理所需代码与模块。
- `run.bat`：Windows 一键启动 GUI。


## 环境需求
- Python 3.9+（建议 3.10/3.11）
- 操作系统：Windows（推荐）、Linux、macOS
- 显卡/驱动：建议具备 OpenGL 3.3+ 的显卡驱动，用于 ModernGL 离屏渲染
- 深度推理：
  - CUDA GPU（NVIDIA）或 Apple MPS（macOS）可显著加速；无 GPU 也可在 CPU 上运行但较慢
  - PyTorch 需与 CUDA 版本匹配（请从 PyTorch 官网选择合适的安装命令）
- ffmpeg：用于视频抽帧与回编，请安装并确保可在命令行调用


## 安装
1) 创建并激活虚拟环境（可选）
2) 安装依赖（示例包名，按需调整版本）
   - customtkinter
   - pillow
   - opencv-python
   - torch（根据你的 CUDA/MPS/CPU 环境安装合适版本）
   - safetensors
   - numpy
   - moderngl
   - pyyaml

你也可以自行创建 `requirements.txt` 并一次性安装。


## 准备 Depth Anything V2 模型权重
- 从官方发布页或常用模型仓库下载 Depth Anything V2 的 `.safetensors` 权重（如 `depth_anything_v2_vitl.safetensors`）。
- 在 `ui.py` 中设置权重路径变量 `depth_path` 指向你的权重文件位置：
  - 变量示例：`depth_path = 'D:/models/depth_anything_v2/depth_anything_v2_vitl.safetensors'`
- 可选择不同编码器规格：`vits`、`vitb`、`vitl`、`vitg`（默认 `vitl`，体积较大、精度更高）。

设备选择逻辑：程序会优先使用 `cuda`，其次 `mps`，否则回落到 `cpu`。


## 快速开始
- Windows 直接双击 `run.bat`，或在命令行中运行 GUI：
  - `python ui.py`

### 图像转换流程
1. 在“图像转换”标签页，点击左侧选择图片。
2. 可勾选：增强饱和度、强制 9:16、生成交织图。
3. 调整滑条“输入分辨率”（378–840，默认 518），用于深度网络推理尺寸。
4. 点击“转换”，将在同目录生成深度图（文件名后缀 `_depth.png`）。
5. 若勾选“生成交织图”，将同时生成交织 PNG（输出位于同目录下的 `interlaced/`）。

### 视频转换流程
1. 在“视频转换”标签页，选择视频文件。
2. 调整输入尺寸，点击“转换”。程序会：
   - 抽帧到 `tmp/`，逐帧推理生成深度帧并回编为 `*_converted.mp4`（深度视频）。
   - 如勾选“生成交织图”，会在 `tmp/interlaced/` 生成逐帧 PNG（时间较久）。

### 批量转换流程
1. 在“批量转换”标签页，选择源目录与（可选）目标目录。
2. 勾选增强/裁剪/生成交织图与输入尺寸。
3. 点击“转换”，在目标目录输出对应结果。


## 交织渲染（命令行）
渲染器读取彩色图与对应深度图，输出交织 PNG：
- 默认配置位于 `depth_config.yaml`，可被命令行参数覆盖。
- 典型使用：
  - 使用默认配置：`python depth_render.py -c depth_config.yaml`
  - 覆盖部分参数（示例）：
    - `python depth_render.py -c depth_config.yaml -i input.jpg -d depth.png -o out.png --line_number 19.61603 --obliquity 0.101593 --deviation 15.83299625`

主要参数说明（与 `shaders/depth_fragment_shader.glsl` 对应）：
- 输出与画面：`output_width`/`output_height`、`scale_x`/`scale_y`、`offset_x`/`offset_y`
- 显示器相关：`line_number`（线数/视差节距）、`obliquity`（倾斜度）、`deviation`（中心偏差）
- 立体与边缘：`threshold`（3D 阈值/强度控制）、`protrude`（前后景偏置）
- 模糊与深度：`blur_size`、`blur_depth`、`depth_image_blur_size`
- 边框与颜色：`border_color`（十六进制，如 `#FFFFFF`）、`border_size_x`/`border_size_y`

注意：片段着色器中包含针对 1440×2560 竖屏的常量，已通过 uniforms 提供可调参数；确保输出尺寸与目标设备匹配以获得最佳效果。

## 常见问题与排查
- ModernGL 创建上下文失败
  - 更新/安装显卡驱动，确保支持 OpenGL 3.3+；避免在完全无图形驱动的环境运行。
- 未找到 ffmpeg
  - 请安装 ffmpeg 并加入系统 PATH。
- PyTorch GPU 不可用或版本不匹配
  - 从 PyTorch 官网选择与你 CUDA 对应的安装命令；或退回 CPU 运行但速度较慢。
- 模型权重未加载
  - 确认 `depth_path` 指向正确的 `.safetensors` 文件，且与所选编码器规格一致。

## 免责声明与许可证
- 本仓库包含的 `depth_anything_v2/` 目录及其 LICENSE 受原作者协议约束，请遵循其使用条款。
- 其余代码如未另行声明，遵循 Apache License 2.0 协议。

## 致谢
- Depth Anything V2 及其作者与社区贡献者。
- ModernGL 与相关开源生态。

---

## <a name="english-version"></a>English Version

# depth_gui_companion_one

A depth and interlaced image generation tool for autostereoscopic/barrier 3D displays such as Companion One.

This project provides:
- GUI (CustomTkinter) for single image/video/batch depth map generation based on Depth Anything V2.
- Offscreen renderer based on ModernGL, converting color + depth maps into 3D interlaced PNGs matching display parameters.
- Fine-grained rendering control via YAML config and command-line (line number, obliquity, deviation, threshold, scaling/offset, blur, border, etc).

## Features
- Image conversion
  - Select a single image to generate a grayscale depth map (input resolution 378–840, adjustable step).
  - Optional: enhance saturation, force crop to 9:16, auto-generate interlaced image after depth map.
- Video conversion
  - Use ffmpeg to extract frames, generate depth map per frame, and re-encode as video (depth video).
  - Optional: same as above (enhance/crop/interlaced, interlaced PNGs per frame, time-consuming).
- Batch conversion
  - Batch process images in a folder to generate depth maps, with optional enhance/crop/interlaced.
- Interlaced rendering (CLI or GUI)
  - Read color + depth map, output interlaced PNG for specified display parameters.

## Directory Structure
- `ui.py`: Main GUI (image/video/batch).
- `depth_render.py`: ModernGL interlaced renderer (offscreen), CLI callable.
- `depth_config.yaml`: Default rendering config (overridable by CLI).
- `shaders/vertex_shader.glsl`, `shaders/depth_fragment_shader.glsl`: Shaders.
- `depth_anything_v2/`: Depth Anything V2 inference code and modules.
- `run.bat`: One-click GUI launcher for Windows.

## Requirements
- Python 3.9+ (3.10/3.11 recommended)
- OS: Windows (recommended), Linux, macOS
- GPU/Driver: OpenGL 3.3+ recommended for ModernGL offscreen rendering
- Depth inference:
  - CUDA GPU (NVIDIA) or Apple MPS (macOS) for acceleration; CPU fallback is slower
  - PyTorch must match CUDA version (see PyTorch official site)
- ffmpeg: For video frame extraction/encoding, must be in PATH

## Installation
1) (Optional) Create and activate a virtual environment
2) Install dependencies (example package names, adjust versions as needed):
   - customtkinter
   - pillow
   - opencv-python
   - torch (install the version matching your CUDA/MPS/CPU)
   - safetensors
   - numpy
   - moderngl
   - pyyaml

You can also create a `requirements.txt` and install all at once.

## Prepare Depth Anything V2 Weights
- Download `.safetensors` weights for Depth Anything V2 from the official release or model hub (e.g. `depth_anything_v2_vitl.safetensors`).
- Set the `depth_path` variable in `ui.py` to your weights file location:
  - Example: `depth_path = 'D:/models/depth_anything_v2/depth_anything_v2_vitl.safetensors'`
- Encoder types: `vits`, `vitb`, `vitl`, `vitg` (default `vitl`, largest and most accurate).

Device selection: The program prefers `cuda`, then `mps`, otherwise falls back to `cpu`.

## Quick Start
- On Windows, double-click `run.bat` or run GUI via command line:
  - `python ui.py`

### Image Conversion
1. In the "Image Conversion" tab, click left to select an image.
2. Options: enhance saturation, force 9:16, generate interlaced image.
3. Adjust "Input Resolution" slider (378–840, default 518) for depth network input size.
4. Click "Convert" to generate a depth map (`_depth.png` suffix in the same folder).
5. If "Generate Interlaced" is checked, an interlaced PNG is also generated (in `interlaced/`).

### Video Conversion
1. In the "Video Conversion" tab, select a video file.
2. Adjust input size, click "Convert". The program:
   - Extracts frames to `tmp/`, infers depth per frame, re-encodes as `*_converted.mp4` (depth video).
   - If "Generate Interlaced" is checked, generates PNGs per frame in `tmp/interlaced/` (slow).

### Batch Conversion
1. In the "Batch Conversion" tab, select source and (optional) target folders.
2. Check enhance/crop/interlaced and input size.
3. Click "Convert" to output results in the target folder.

## Interlaced Rendering (CLI)
The renderer reads color + depth map, outputs interlaced PNG:
- Default config: `depth_config.yaml`, overridable by CLI.
- Typical usage:
  - Default config: `python depth_render.py -c depth_config.yaml`
  - Override params (example):
    - `python depth_render.py -c depth_config.yaml -i input.jpg -d depth.png -o out.png --line_number 19.61603 --obliquity 0.101593 --deviation 15.83299625`

Main parameters (see `shaders/depth_fragment_shader.glsl`):
- Output/image: `output_width`/`output_height`, `scale_x`/`scale_y`, `offset_x`/`offset_y`
- Display: `line_number` (parallax pitch), `obliquity`, `deviation`
- Stereo/edge: `threshold` (3D strength), `protrude` (foreground/background bias)
- Blur/depth: `blur_size`, `blur_depth`, `depth_image_blur_size`
- Border/color: `border_color` (hex, e.g. `#FFFFFF`), `border_size_x`/`border_size_y`

Note: The fragment shader contains constants for 1440×2560 portrait screens, adjustable via uniforms; ensure output size matches your device for best results.

## FAQ
- ModernGL context creation failed
  - Update/install GPU drivers, ensure OpenGL 3.3+ support; avoid running in headless/no-GPU environments.
- ffmpeg not found
  - Install ffmpeg and add to system PATH.
- PyTorch GPU unavailable or version mismatch
  - Install PyTorch matching your CUDA; fallback to CPU is slower.
- Model weights not loaded
  - Ensure `depth_path` points to the correct `.safetensors` file and matches encoder type.

## License
- The `depth_anything_v2/` directory and its LICENSE are subject to the original author's terms.
- Other code is under Apache License 2.0 unless otherwise stated.

## Acknowledgements
- Depth Anything V2 and its authors/community.
- ModernGL and related open source ecosystem.

