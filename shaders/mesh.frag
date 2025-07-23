#version 330

in vec3 v_normal;
in vec3 v_position;

out vec4 f_color;

uniform vec3 light_pos;
uniform vec3 view_pos;
uniform vec3 object_color;

void main() {
    // Normalize vectors
    vec3 norm = normalize(v_normal);
    vec3 light_dir = normalize(light_pos - v_position);
    vec3 view_dir = normalize(view_pos - v_position);
    vec3 reflect_dir = reflect(-light_dir, norm);

    // Ambient lighting (brighter to improve base visibility)
    float ambient_strength = 0.3;
    vec3 ambient = ambient_strength * vec3(1.0);

    // Diffuse lighting
    float diff = max(dot(norm, light_dir), 0.0);
    vec3 diffuse = diff * vec3(1.0);

    // Specular lighting (sharp highlight for metallic look)
    float specular_strength = 0.6;
    float spec = pow(max(dot(view_dir, reflect_dir), 0.0), 64.0);
    vec3 specular = specular_strength * spec * vec3(1.0);

    // View-facing fill light (prevents dark areas when facing camera)
    float view_alignment = max(dot(norm, view_dir), 0.0);
    vec3 fill_light = 0.1 * view_alignment * vec3(1.0);

    // Combine lighting and apply object color
    vec3 result = (ambient + diffuse + specular + fill_light) * object_color;
    f_color = vec4(result, 1.0);
}
