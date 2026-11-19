(sceneSpec) => {
  const T = FigureThree;
  const scene = new T.Scene();
  const shapes = {
    box: () => new T.BoxGeometry(1, 1, 1),
    sphere: () => new T.SphereGeometry(0.5, 18, 12),
    cylinder: () => new T.CylinderGeometry(0.5, 0.5, 1, 32),
  };
  for (const item of sceneSpec.objects) {
    const mesh = new T.Mesh(shapes[item.shape](), new T.MeshLambertMaterial({color: item.color}));
    mesh.position.fromArray(item.position);
    mesh.scale.fromArray(item.size);
    scene.add(mesh);
  }
  const bounds = new T.Box3().setFromObject(scene);
  const center = bounds.getCenter(new T.Vector3());
  const span = bounds.getSize(new T.Vector3()).length();
  const camera = new T.OrthographicCamera(-span / 2, span / 2, span / 2, -span / 2, 0.01 * span, 6 * span);
  camera.position.copy(center).addScaledVector(new T.Vector3(1, 0.8, 1.25).normalize(), 2 * span);
  camera.lookAt(center);
  const key = new T.DirectionalLight(0xffffff, 0.75);
  key.position.set(2, 5, 3);
  scene.add(new T.AmbientLight(0xffffff, 0.65), key);
  const renderer = new T.SVGRenderer();
  renderer.setSize(512, 512);
  renderer.setPrecision(3);
  renderer.render(scene, camera);
  const svg = renderer.domElement;
  document.body.appendChild(svg);
  const output = document.createElementNS(svg.namespaceURI, 'svg');
  for (const face of svg.querySelectorAll('path')) {
    const path = document.createElementNS(svg.namespaceURI, 'path');
    path.setAttribute('d', face.getAttribute('d'));
    path.setAttribute('fill', face.style.fill);
    output.appendChild(path);
  }
  const box = svg.getBBox();
  if (!box.width || !box.height) throw new Error('empty legend projection');
  const margin = 0.04 * Math.max(box.width, box.height);
  const w = box.width + 2 * margin, h = box.height + 2 * margin;
  output.setAttribute('viewBox', [box.x - margin, box.y - margin, w, h].join(' '));
  output.setAttribute('width', Math.ceil(w));
  output.setAttribute('height', Math.ceil(h));
  const title = document.createElementNS(svg.namespaceURI, 'title');
  title.textContent = sceneSpec.title;
  output.prepend(title);
  return new XMLSerializer().serializeToString(output);
}
