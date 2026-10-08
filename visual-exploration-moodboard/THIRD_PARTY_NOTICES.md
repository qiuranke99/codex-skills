# Third-party code and content

The runtime uses pinned npm dependencies, resolved by `package-lock.json`:

- `shaders` 4.0.2, Shader Effects Inc., MIT: https://github.com/shaders/shaders
- `esbuild` 0.28.2, Evan Wallace, MIT: https://github.com/evanw/esbuild
- `playwright` 1.64.0, Microsoft Corporation, Apache-2.0: https://github.com/microsoft/playwright

Their installed distributions retain their license/notice files. A bundled or redistributed runtime must include those notices and the transitive dependencies' notices; use the package lock and installed license files as the exact distribution authority. Chromium is installed separately and retains its own licenses.

The three WGSL studies in `assets/recipes/original-fields.mjs` are original Skill code. No shaders.com Free or Pro presets, preview media, template content, fonts or customer assets are redistributed. The upstream code license does not grant rights to website content or third-party project references. A reference URL or ability to view a work is not a redistribution license.

## Shaders MIT notice

MIT License

Copyright (c) 2026 Shader Effects Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
