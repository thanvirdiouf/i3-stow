#version 330
// SPDX-License-Identifier: GPL-3.0-or-later
// Inspired by ikz87's i3lock + Picom shader technique:
// https://github.com/ikz87/picom-shaders/blob/main/3DCamera/lock.glsl
// The marked 256px corner of i3lock's PNG carries the Superman texture.
// Without that PNG, the original procedural purple padlock remains available.

in vec2 texcoord;
uniform sampler2D tex;
uniform float time; // Picom supplies milliseconds and redraws animated shaders.

const float PI = 3.14159265;
const vec3 BACKGROUND = vec3(30.0, 30.0, 46.0) / 255.0;
const vec3 PURPLE = vec3(189.0, 147.0, 249.0) / 255.0;
const vec3 CYAN = vec3(139.0, 233.0, 253.0) / 255.0;
const int AVATAR_SIZE = 256;

vec3 avatar_color(vec2 image_uv) {
    // Bilinear sampling inside the corner patch, without sampling its surround.
    vec2 pixel = clamp(image_uv, vec2(0.0), vec2(1.0)) * float(AVATAR_SIZE - 1);
    ivec2 a = ivec2(floor(pixel));
    ivec2 b = min(a + ivec2(1), ivec2(AVATAR_SIZE - 1));
    vec2 f = fract(pixel);
    return mix(mix(texelFetch(tex, a, 0).rgb,
                   texelFetch(tex, ivec2(b.x, a.y), 0).rgb, f.x),
               mix(texelFetch(tex, ivec2(a.x, b.y), 0).rgb,
                   texelFetch(tex, b, 0).rgb, f.x), f.y);
}

float rounded_box(vec2 p, vec2 half_size, float radius) {
    vec2 q = abs(p) - half_size + radius;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
}

float lock_shape(vec2 p) {
    float body = rounded_box(p - vec2(0.0, -0.19), vec2(0.33, 0.27), 0.07);
    vec2 shackle = p - vec2(0.0, 0.16);
    float arch = max(abs(length(shackle) - 0.23) - 0.055, -shackle.y);
    float left = rounded_box(p - vec2(-0.23, 0.095), vec2(0.055, 0.09), 0.02);
    float right = rounded_box(p - vec2(0.23, 0.095), vec2(0.055, 0.09), 0.02);
    return min(min(body, arch), min(left, right));
}

vec4 window_shader() {
    vec4 source = texelFetch(tex, ivec2(texcoord), 0);
    // These two exact marker pixels distinguish the image-backed lock from the
    // solid fallback. On this 1920x1080 layout the patch is far from the indicator.
    bool has_avatar = distance(texelFetch(tex, ivec2(0, 0), 0).rgb, PURPLE) < 0.005
                   && distance(texelFetch(tex, ivec2(1, 0), 0).rgb, CYAN) < 0.005;
    bool image_patch = has_avatar && texcoord.x < float(AVATAR_SIZE)
                                  && texcoord.y < float(AVATAR_SIZE);

    vec2 size = vec2(textureSize(tex, 0));
    vec2 centered = texcoord - size * 0.5;
    float radius = clamp(size.y / 12.0, 60.0, 150.0);

    // Stock i3lock 2.14.1 paints a 75%-opaque black/blue/red disk behind
    // its indicator. Remove only those flat fills within the ball, so typing
    // cannot replace it with a dark disk. Keep the native ring, keypress arcs,
    // black text, Caps Lock notices, and all other changed pixels on top.
    // Colors are composited over --color=1e1e2e, as in unlock_indicator.c.
    vec3 idle_fill = BACKGROUND * 0.25;
    vec3 verify_fill = mix(BACKGROUND, vec3(0.0, 114.0 / 255.0, 1.0), 0.75);
    vec3 wrong_fill = mix(BACKGROUND, vec3(250.0 / 255.0, 0.0, 0.0), 0.75);
    bool indicator_fill = dot(centered, centered) < radius * radius
                       && (distance(source.rgb, idle_fill) < 0.006
                        || distance(source.rgb, verify_fill) < 0.006
                        || distance(source.rgb, wrong_fill) < 0.006);
    if (!image_patch && !indicator_fill && distance(source.rgb, BACKGROUND) > 0.015) {
        return vec4(source.rgb, 1.0);
    }

    vec2 uv = centered / size.y;
    float seconds = time / 1000.0;

    // A quiet purple glow and moving contours behind the rotating emblem.
    float glow = exp(-3.5 * dot(uv, uv));
    vec3 color = BACKGROUND + PURPLE * glow * 0.055;
    float wave = sin(uv.x * 5.0 + seconds * 0.22) * 0.04;
    float contour = abs(sin((uv.y + wave) * 22.0 + seconds * 0.15));
    color += PURPLE * pow(contour, 40.0) * 0.012 * glow;

    vec2 p = centered / radius;
    float distance_squared = dot(p, p);
    if (distance_squared < 1.0) {
        vec3 normal = vec3(p.x, -p.y, sqrt(1.0 - distance_squared));
        float angle = seconds * 0.65;
        vec3 rotated = vec3(cos(angle) * normal.x + sin(angle) * normal.z,
                            normal.y,
                           -sin(angle) * normal.x + cos(angle) * normal.z);

        // Repeat the lock on both faces of the sphere as it rotates.
        float longitude = atan(rotated.x, rotated.z);
        longitude = mod(longitude + PI * 0.5, PI) - PI * 0.5;
        vec2 emblem = vec2(longitude / 0.95, rotated.y * 1.25);
        float mark = 1.0 - smoothstep(-0.012, 0.012, lock_shape(emblem));
        float keyhole = min(length(emblem - vec2(0.0, -0.13)) - 0.065,
                            rounded_box(emblem - vec2(0.0, -0.23),
                                        vec2(0.028, 0.075), 0.01));
        mark *= smoothstep(-0.008, 0.008, keyhole);

        vec3 light = normalize(vec3(-0.5, 0.7, 1.0));
        float diffuse = max(dot(normal, light), 0.0);
        float rim = pow(1.0 - normal.z, 3.0);
        vec3 surface = mix(vec3(0.13, 0.11, 0.20), PURPLE * 0.85, mark);
        if (has_avatar) {
            // Fit the whole shield onto a circular badge on both faces. The
            // vertical flip keeps the image upright in the sphere's UV space.
            vec2 image_uv = emblem / 1.8 + 0.5;
            image_uv.y = 1.0 - image_uv.y;
            float badge = 1.0 - smoothstep(0.86, 0.91, length(emblem));
            vec3 image_color = avatar_color(image_uv);
            // Remove this photo's blue backdrop in the material, leaving the
            // red/gold shield directly on the purple sphere, with soft edges.
            float blue_background = smoothstep(0.10, 0.30, image_color.b - image_color.r)
                                  * smoothstep(0.02, 0.12, image_color.g - image_color.r);
            float artwork = smoothstep(0.015, 0.06, distance(image_color, BACKGROUND))
                          * (1.0 - blue_background);
            surface = mix(vec3(0.13, 0.11, 0.20), image_color, badge * artwork);
        }
        surface *= has_avatar ? 0.70 + 0.40 * diffuse : 0.45 + 0.65 * diffuse;
        surface += PURPLE * rim * 0.55;
        surface += vec3(0.16) * pow(max(dot(reflect(-light, normal),
                                               vec3(0.0, 0.0, 1.0)), 0.0), 24.0);
        surface *= 0.98 + 0.02 * sin(texcoord.y * 2.2);
        float edge = 1.0 - smoothstep(0.97, 1.0, distance_squared);
        color = mix(color, surface, edge);
    }

    // Always opaque: no part of the desktop is revealed through the locker.
    // Bypass rounded corners/dimming; this rule covers the entire lock window.
    return vec4(color, 1.0);
}
