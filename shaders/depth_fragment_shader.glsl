#version 330 core
precision mediump float;

#define gaussian_blur mat3(1, 2, 1, 2, 4, 2, 1, 2, 1) * 0.0625
#define box_blur mat3(1, 1, 1, 1, 1, 1, 1, 1, 1) * 0.1111

uniform sampler2D g_Texture0;
uniform sampler2D g_Texture1;
uniform sampler2D g_Texture2;
uniform vec3 g_Screen;

uniform float u_threshold;
uniform float u_protrude;
uniform float u_lineNumber;
uniform float u_obliquity;
uniform float u_Deviation;
uniform vec2 g_Texture1Resolution;

uniform float u_scaleX;
uniform float u_scaleY;
uniform float u_offsetX;
uniform float u_offsetY;

uniform float u_blurSize;
uniform float u_blurDepth;
uniform float u_depthImageBlurSize;

uniform vec3 u_borderColor;
uniform float u_borderSizeX, u_borderSizeY;

const float screenWidth = 1440.0;
const float screenHeight = 2560.0;
const vec2 quiltSize = vec2(8., 5.);
const float numViews = quiltSize.x * quiltSize.y;
const float invView = 0.0;

varying vec2 v_TexCoord;

vec2 mirrored(vec2 v) {
    vec2 m = mod(v, 2.);
    return mix(m, 2.0 - m, step(1.0, m));
}

vec4 convolute(vec2 uv, mat3 kernel, float size) {
    if(size < 1.0) return texture2D(g_Texture1, uv);
    vec4 color = vec4(0., 0., 0., 0.);
    for (int x = 0; x < 3; x++) {
        for (int y = 0; y < 3; y++) {
            vec2 offset = vec2(float(x - 1), float(y - 1)) / g_Screen.xy * size;
            color += texture2D(g_Texture1, uv + offset) * kernel[x][y];
        }
    }
    return color;
}

vec4 convoluteDepth(vec2 uv, mat3 kernel, float size) {
    if(size < 1.0) return texture2D(g_Texture2, uv);
    vec4 color = vec4(0., 0., 0., 0.);
    for (int x = 0; x < 3; x++) {
        for (int y = 0; y < 3; y++) {
            vec2 offset = vec2(float(x - 1), float(y - 1)) / g_Screen.xy * size;
            color += texture2D(g_Texture2, uv + offset) * kernel[x][y];
        }
    }
    return color;
}

vec4 depthQuilts(vec2 iuv) {
    vec2 coord = iuv * vec2(quiltSize.x, quiltSize.y);
    vec2 fractCoord = fract(coord);
    vec2 floorCoord = floor(coord);
    float imageId = floorCoord.x + floorCoord.y * quiltSize.x;
    float valueId = imageId / (quiltSize.x * quiltSize.y - 1.);

    vec2 uv = vec2(u_scaleX, u_scaleY) * (fractCoord - 0.5) + 0.5 + vec2(u_offsetX, u_offsetY);

    vec4 depthMap = convoluteDepth(uv, box_blur, u_depthImageBlurSize);
    float xOffset = (depthMap.r - (0.0 - u_protrude) - 0.5) * ((valueId - 0.5) * 2.0 / u_threshold);
    vec2 fake3d = vec2(uv.x + xOffset, uv.y);

    if((valueId > 0.5 ? xOffset < 0. : xOffset > 0.) && 
        (fractCoord.x < u_borderSizeX || fractCoord.y < u_borderSizeY || 
        fractCoord.x > (1. - u_borderSizeX) || fractCoord.y > (1. - u_borderSizeY))) {
        return vec4(u_borderColor, 1.0);
    }

    vec4 color = depthMap.r < u_blurDepth ? 
        convolute(mirrored(fake3d), gaussian_blur, u_blurSize) : 
        texture2D(g_Texture1, fake3d);

    return color;
}

vec2 texArr(vec3 uvz) {
    float z = floor((1.0 - uvz.z) * numViews);
    vec2 viewSize = g_Texture1Resolution / vec2(quiltSize.x, quiltSize.y);

    vec2 pixelCoord;
    pixelCoord.x = (mod(z, quiltSize.x) * viewSize.x + uvz.x * viewSize.x);
    pixelCoord.y = (floor(z / quiltSize.x) * viewSize.y + uvz.y * viewSize.y);

    return pixelCoord / g_Texture1Resolution;
}

void main() {
    vec2 uv = v_TexCoord.xy;

    float pitch = (screenWidth * 3.0) / u_lineNumber;
    float slope = u_obliquity * (screenHeight / screenWidth);
    float subp = 1.0 / (screenWidth * 3.0);
    float center = (u_Deviation * 3.0 / screenWidth) * pitch;

    float r, g, b;

    // 红色通道
    float z = (uv.x + 0.0 * subp + uv.y * slope) * pitch - center;
    z = mod(z + ceil(abs(z)), 1.0);
    z = (1.0 - invView) * z + invView * (1.0 - z);
    vec2 iuv = texArr(vec3(uv, z));
    r = depthQuilts(iuv).r;

    // 绿色通道
    z = (uv.x + 1.0 * subp + uv.y * slope) * pitch - center;
    z = mod(z + ceil(abs(z)), 1.0);
    z = (1.0 - invView) * z + invView * (1.0 - z);
    iuv = texArr(vec3(uv, z));
    g = depthQuilts(iuv).g;

    // 蓝色通道
    z = (uv.x + 2.0 * subp + uv.y * slope) * pitch - center;
    z = mod(z + ceil(abs(z)), 1.0);
    z = (1.0 - invView) * z + invView * (1.0 - z);
    iuv = texArr(vec3(uv, z));
    b = depthQuilts(iuv).b;

    gl_FragColor = vec4(r, g, b, 1.0);
}
