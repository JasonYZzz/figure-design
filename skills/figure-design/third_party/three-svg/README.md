# Three.js SVG runtime

The local vector renderer bundles named exports from three@0.186.1 and its SVGRenderer addon. The browser runs the bundle without a server, GPU context, CDN, or Node.js. Sources are distributed by [Three.js](https://www.npmjs.com/package/three/v/0.186.1) under the [MIT license](LICENSE).

The camera and mesh workflow draws on the fundamentals and geometry topics in [CloudAI-X/threejs-skills](https://github.com/CloudAI-X/threejs-skills). The scene format and figure integration were written for this project.

To reproduce runtime.js, copy exports.js into an empty build directory, then run the following commands there.

```sh
npm install --no-save three@0.186.1 esbuild@0.28.2
./node_modules/.bin/esbuild exports.js --bundle --minify --format=iife --global-name=FigureThree --outfile=runtime.js
```
