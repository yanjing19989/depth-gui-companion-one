#version 330 core
in vec3 a_Position;
in vec2 a_TexCoord;
out vec2 v_TexCoord;

void main() {
    gl_Position = vec4(a_Position, 1.0);
    v_TexCoord = a_TexCoord;
}
