#version 330

in vec2 texcoord;
uniform sampler2D tex;
uniform float corner_radius;

vec4 default_post_processing(vec4 color);

vec4 window_shader() {
    vec4 pixel = texelFetch(tex, ivec2(texcoord), 0);

    // Match `border pixel 3` in i3/config. Fullscreen windows have no rounding.
    const float frame_width = 3.0;
    if (corner_radius > frame_width) {
        ivec2 size = textureSize(tex, 0);
        vec2 half_size = vec2(size) * 0.5;
        vec2 offset = abs(texcoord - half_size) - half_size + corner_radius;
        float edge_distance = length(max(offset, vec2(0.0)))
                            + min(max(offset.x, offset.y), 0.0) - corner_radius;

        // Sample i3's actual border so focus and color changes stay automatic.
        vec4 frame_color = texelFetch(tex, ivec2(0, size.y / 2), 0);
        float frame_coverage = smoothstep(-frame_width, -frame_width + 1.0,
                                         edge_distance);
        pixel = mix(pixel, frame_color, frame_coverage);
    }

    // Preserve picom's opacity, dimming and antialiased outer corners.
    return default_post_processing(pixel);
}
