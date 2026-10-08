// All WGSL below is original package code, not a preset copied from shaders.com.
import {defineShader,wgsl} from 'shaders/std';
import {recipeCatalog} from './catalog.mjs';

const bodies = {
  'luminous-order': `
    let q = (uv - vec2f(0.54, 0.5)) * vec2f(aspect, 1.0);
    let t = time * tempo * 0.36;
    let sweep = 0.5 + 0.5 * sin(t);
    let curve = q.y + bend * 0.24 * sin(q.x * 2.3 + 0.7) + q.x * 0.28;
    let interval = 0.96 / discipline;
    let band = floor((curve + 0.65) / interval);
    let v = fract((curve + 0.65) / interval);
    let edge = exp(-pow((v - 0.15) / (aperture * 0.8 + 0.025), 2.0));
    let face = smoothstep(0.15, 0.37, v) * (1.0 - smoothstep(0.63, 0.96, v));
    let traveling = exp(-pow((q.x - (sweep * 1.8 - 0.9) + band * 0.035) / 0.4, 2.0));
    let falloff = exp(-length(q * vec2f(0.65, 0.55)) * 0.9);
    let ambient = vec3f(0.018, 0.048, 0.055) + face * vec3f(0.015, 0.036, 0.039);
    let silver = mix(vec3f(0.53, 0.91, 0.94), vec3f(1.0, 0.78, 0.49), warmth);
    let illumination = edge * (0.12 + 0.88 * traveling) * falloff;
    let sheen = face * traveling * 0.13 + pow(max(0.0, 1.0 - abs(v - 0.18) * 5.5), 5.0) * traveling * 0.14;
    let frame = 1.0 - smoothstep(0.36, 1.3, length(q));
    return vec4f((ambient + silver * (illumination + sheen)) * (0.4 + 0.6 * frame), 1.0);
  `,
  'envelop-reveal': `
    let q = (uv - vec2f(0.5, 0.5)) * vec2f(aspect, 1.0);
    let breath = sin(time * tempo * 0.45) * 0.045;
    let gap = opening * 0.37 + breath;
    let arch = sqrt(max(0.001, 1.0 - pow(q.x * 0.8, 2.0)));
    let contour = abs(q.y + sin(q.x * 2.0) * wrap * 0.06) - gap * arch;
    let shell = smoothstep(-0.005, 0.008, contour);
    let outer = clamp(contour / (0.23 + softness * 0.24), 0.0, 1.0);
    let folded = exp(-pow(contour / (0.025 + softness * 0.075), 2.0));
    let sideLight = 0.45 + 0.55 * smoothstep(-0.7, 0.9, q.x);
    let clay = mix(vec3f(0.22, 0.29, 0.25), vec3f(0.59, 0.19, 0.095), warmth);
    let ivory = mix(vec3f(0.7, 0.8, 0.7), vec3f(0.98, 0.79, 0.57), warmth);
    let surface = mix(ivory, clay, smoothstep(0.0, 1.0, outer)) * sideLight;
    let lip = folded * vec3f(0.16, 0.095, 0.045) * (0.7 + wrap);
    let innerGlow = exp(-length(q * vec2f(1.1, 3.0)) * 3.5);
    let interior = vec3f(0.018, 0.027, 0.025) + innerGlow * vec3f(0.028, 0.065, 0.047);
    let horizon = exp(-pow(q.y / 0.014, 2.0)) * exp(-q.x * q.x * 5.0) * (1.0 - shell);
    return vec4f(mix(interior + horizon * vec3f(0.43, 0.49, 0.30), surface + lip, shell), 1.0);
  `,
  'affinity-field': `
    let q = (uv - vec2f(0.5, 0.5)) * vec2f(aspect, 1.0);
    let t = time * tempo * 0.24;
    let pulse = 0.5 + 0.5 * sin(t);
    let radius = mix(0.45, 0.16, cohesion * (0.5 + pulse * 0.5));
    var nodes: array<vec2f, 6>;
    for (var i: i32 = 0; i < 6; i = i + 1) {
      let a = f32(i) * 1.04719755 + t * 0.2;
      nodes[i] = vec2f(cos(a) * radius * 1.35, sin(a) * radius * 0.84);
    }
    var connections = 0.0;
    var bodies = 0.0;
    var halo = 0.0;
    for (var i: i32 = 0; i < 6; i = i + 1) {
      let dist = length(q - nodes[i]);
      bodies = max(bodies, 1.0 - smoothstep(0.036 * scale, 0.039 * scale + 0.003, dist));
      halo = halo + exp(-dist * dist / (0.006 + scale * 0.008)) * 0.2;
      for (var j: i32 = 0; j < 6; j = j + 1) {
        if (j > i) {
          let ab = nodes[j] - nodes[i];
          let h = clamp(dot(q - nodes[i], ab) / max(0.00001, dot(ab, ab)), 0.0, 1.0);
          let d = length(q - nodes[i] - ab * h);
          let strength = 1.0 - smoothstep(reach * 0.23, reach * 0.95, length(ab));
          connections = max(connections, exp(-d * d / 0.000012) * strength);
        }
      }
    }
    let paper = mix(vec3f(0.66, 0.75, 0.69), vec3f(0.94, 0.82, 0.64), warmth);
    let vignette = exp(-length(q * vec2f(0.7, 0.9)) * 0.45);
    let graphite = vec3f(0.025, 0.043, 0.038);
    let background = paper * vignette + halo * vec3f(0.05, 0.025, 0.005);
    let ink = clamp(connections * 0.66 + bodies, 0.0, 1.0);
    return vec4f(mix(background, graphite, ink), 1.0);
  `,
};

export const originalDefinitions = recipeCatalog.map(recipe => defineShader({
  name:recipe.componentType,role:'generator',
  props:Object.fromEntries(Object.entries(recipe.parameters).map(([key,contract])=>[key,{default:contract.default}])),
  paint:wgsl({body:bodies[recipe.id]}),
}));
