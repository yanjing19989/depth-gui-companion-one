import moderngl
import numpy as np
from PIL import Image
import argparse
import sys
import os
import yaml

def load_shader_code(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

# --- 2. 辅助函数 ---
def hex_to_rgb(hex_color):
    """将十六进制颜色字符串转换为归一化的RGB元组 (0.0-1.0)"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

# --- 3. 主渲染逻辑 ---
def run_hologram_render(
    image_file="input.jpg",
    depth_file="depth.png",
    output_file="output_hologram.png",
    output_width=1440,
    output_height=2560,
    threshold=15.0,
    protrude=0,
    line_number=19.61603,
    obliquity=0.101593,
    deviation=15.83299625,
    scale_x=1.0,
    scale_y=1.0,
    offset_x=0.0,
    offset_y=0.0,
    blur_size=5.0,
    blur_depth=0.25,
    depth_image_blur_size=50.0,
    border_color="#FFFFFF",
    border_size_x=0.02,
    border_size_y=0.01,
    vertex_shader_path="shaders/vertex_shader.glsl",
    fragment_shader_path="shaders/depth_fragment_shader.glsl"
):
    # 创建ModernGL上下文 (离屏渲染)
    try:
        ctx = moderngl.create_context(standalone=True)
        print("OpenGL context created.")
    except Exception as e:
        print(f"创建ModernGL上下文时出错: {e}")
        print("这可能是因为没有找到兼容的OpenGL驱动程序，或者在没有显示功能的环境中运行。")
        sys.exit(1)

    # --- 加载图像 ---
    try:
        img_orig = Image.open(image_file).convert('RGBA')
        img_depth = Image.open(depth_file).convert('RGBA')
        print(f"Loaded quilt image: {image_file} ({img_orig.width}x{img_orig.height})")
        print(f"Loaded depth image: {depth_file} ({img_depth.width}x{img_depth.height})")
        # 创建纹理
        # g_Texture1 (原始图像, quilt)
        texture_image = ctx.texture(img_orig.size, 4, img_orig.tobytes())
        texture_image.filter = (moderngl.LINEAR, moderngl.LINEAR) # 线性过滤
        texture_image.repeat_x = False  # 相当于 CLAMP_TO_EDGE (边缘钳制)
        texture_image.repeat_y = False  # 相当于 CLAMP_TO_EDGE (边缘钳制)
        texture_image.use(1)
        
        # g_Texture2 (深度图)
        texture_depth = ctx.texture(img_depth.size, 4, img_depth.tobytes())
        texture_depth.filter = (moderngl.LINEAR, moderngl.LINEAR) # 线性过滤
        texture_depth.repeat_x = False  # 相当于 CLAMP_TO_EDGE (边缘钳制)
        texture_depth.repeat_y = False  # 相当于 CLAMP_TO_EDGE (边缘钳制)
        texture_depth.use(2)
    except FileNotFoundError as e:
        print(f"错误: {e}. 请检查图像文件路径。")
        return
    except Exception as e:
        print(f"加载图像时出错: {e}")
        return

    # --- 创建帧缓冲区用于离屏渲染 ---
    # 创建一个纹理作为渲染目标
    render_texture = ctx.texture((output_width, output_height), 4) # RGBA纹理

    # 创建一个帧缓冲区对象并将渲染纹理附加到它
    fbo = ctx.framebuffer(render_texture)

    # 绑定帧缓冲区，以便渲染到它
    fbo.use()
    ctx.viewport = (0, 0, output_width, output_height) # 设置视口
    ctx.clear(0.0, 0.0, 0.0, 1.0) # 清空帧缓冲区 (黑色，不透明)

    # --- 加载着色器 ---
    vertex_shader_source = load_shader_code(vertex_shader_path)
    fragment_shader_source = load_shader_code(fragment_shader_path)

    program = ctx.program(
        vertex_shader=vertex_shader_source,
        fragment_shader=fragment_shader_source,
    )


    # --- 设置几何体 (全屏四边形) ---
    # 顶点数据: x, y, z, u, v
    vertices = np.array([
        -1.0, -1.0, 0.0, 0.0, 1.0,  # 左下角
         1.0, -1.0, 0.0, 1.0, 1.0,  # 右下角
        -1.0,  1.0, 0.0, 0.0, 0.0,  # 左上角
         1.0,  1.0, 0.0, 1.0, 0.0   # 右上角
    ], dtype='f4') # 'f4' 表示 float32

    vbo = ctx.buffer(vertices)
    
    # 定义顶点缓冲区数据如何映射到着色器属性
    vao = ctx.vertex_array(program, [(vbo, '3f 2f', 'a_Position', 'a_TexCoord')])

    # --- 设置Uniform变量 ---
    # 分配纹理单元
    program['g_Texture1'].value = 1 # texture_image 将使用纹理单元1
    program['g_Texture2'].value = 2 # texture_depth 将使用纹理单元2


    # 设置来自argparse参数的uniform变量
    program['g_Screen'].value = (float(output_width), float(output_height), 1.0)
    program['g_Texture1Resolution'].value = (float(img_orig.width), float(img_orig.height))
    program['u_threshold'].value = threshold
    program['u_protrude'].value = protrude
    program['u_lineNumber'].value = line_number
    program['u_obliquity'].value = obliquity
    program['u_Deviation'].value = deviation

     # 视图内变换参数
    program['u_scaleX'].value = scale_x
    program['u_scaleY'].value = scale_y
    program['u_offsetX'].value = offset_x
    program['u_offsetY'].value = offset_y

    # 深度图效果参数
    program['u_blurSize'].value = blur_size
    program['u_blurDepth'].value = blur_depth
    program['u_depthImageBlurSize'].value = depth_image_blur_size

    # 边框效果参数
    border_color_rgb = hex_to_rgb(border_color)
    program['u_borderColor'].value = border_color_rgb
    program['u_borderSizeX'].value = border_size_x
    program['u_borderSizeY'].value = border_size_y

    # --- 渲染 ---
    vao.render(moderngl.TRIANGLE_STRIP) # 使用三角形带模式渲染全屏四边形

    # --- 读取像素并保存图像 ---
    image_data = fbo.read(components=4, dtype='f1') # 'f1' 表示8位无符号整数 (字节)
    
    # 将字节数据转换为PIL图像
    output_image = Image.frombytes('RGBA', (output_width, output_height), image_data)
    
    # 翻转图像，因为OpenGL的Y轴原点在左下角，PIL的Y轴原点在左上角
    output_image = output_image.transpose(Image.FLIP_TOP_BOTTOM)
    
    output_image.save(output_file, compress_level=1)
    print(f"Rendered image saved to {output_file}")

    # --- 清理资源 ---
    # 在独立上下文中，资源通常在脚本退出时自动清理。
    # 如果上下文不退出，显式释放是良好的实践。
    fbo.release()
    render_texture.release()
    texture_image.release()
    texture_depth.release()
    vbo.release()
    vao.release()
    program.release()
    ctx.release()

def load_config_yaml(yaml_path):
    if not os.path.exists(yaml_path):
        return {}
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="使用ModernGL进行全息3D图像渲染。")
    parser.add_argument('-c', '--config', type=str, default="depth_config.yaml", help="外部配置文件 (YAML)")
    # 允许命令行参数覆盖yaml
    parser.add_argument('-i', '--image_file', type=str, help="原始图像的路径。")
    parser.add_argument('-d', '--depth_file', type=str, help="灰度深度图图像的路径。")
    parser.add_argument('-o', '--output_file', type=str, help="渲染输出图像的保存路径。")
    parser.add_argument('--output_width', type=int, help="输出渲染图像的宽度。")
    parser.add_argument('--output_height', type=int, help="输出渲染图像的高度。")
    parser.add_argument('--threshold', type=float, help="3D阈值 (u_threshold)")
    parser.add_argument('--protrude', type=float, help="突出量 (u_protrude)")
    parser.add_argument('--line_number', type=float, help="线数 (u_lineNumber)")
    parser.add_argument('--obliquity', type=float, help="倾斜度 (u_obliquity)")
    parser.add_argument('--deviation', type=float, help="偏差 (u_Deviation)")
    parser.add_argument('--scale_x', type=float, help="X轴缩放 (u_scaleX)")
    parser.add_argument('--scale_y', type=float, help="Y轴缩放 (u_scaleY)")
    parser.add_argument('--offset_x', type=float, help="X轴偏移 (u_offsetX)")
    parser.add_argument('--offset_y', type=float, help="Y轴偏移 (u_offsetY)")
    parser.add_argument('--blur_size', type=float, help="模糊尺寸 (u_blurSize)")
    parser.add_argument('--blur_depth', type=float, help="模糊深度阈值 (u_blurDepth)")
    parser.add_argument('--depth_image_blur_size', type=float, help="深度图像模糊尺寸 (u_depthImageBlurSize)")
    parser.add_argument('--border_color', type=str, help="边框颜色 (u_borderColor)")
    parser.add_argument('--border_size_x', type=float, help="水平边框尺寸 (u_borderSizeX)")
    parser.add_argument('--border_size_y', type=float, help="垂直边框尺寸 (u_borderSizeY)")
    parser.add_argument('--vertex_shader_path', type=str, default="shaders/vertex_shader.glsl", help="顶点着色器文件路径")
    parser.add_argument('--fragment_shader_path', type=str, default="shaders/depth_fragment_shader.glsl", help="片元着色器文件路径")
    args = parser.parse_args()
    config = load_config_yaml(args.config)

    # 合并命令行参数覆盖yaml
    params = dict(config)
    for k, v in vars(args).items():
        if v is not None and k != 'config':
            params[k] = v
    run_hologram_render(**params)

if __name__ == "__main__":
    main()