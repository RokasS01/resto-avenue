import * as THREE from 'three';
import { clamp01, ease, loadModel, mix } from './assets.js';
import { buildDiorama } from './diorama.js';
import { buildMap, geo } from './map.js';

const SKY = 0xf6efe4;
const VAN_SCALE = 0.32;
const WHEEL_RADIUS = 0.36;
const MODELS = `${import.meta.env.BASE_URL}models/`;

const SPOTS = ['spot_phone', 'spot_mail', 'spot_insta', 'spot_map'];

const v = (x, y, z) => new THREE.Vector3(x, y, z);

/** Interpole une suite de plans de caméra (position, cible, décalage) selon l'avancement. */
function sampleKeys(keys, q, out) {
  let i = 0;
  while (i < keys.length - 2 && q > keys[i + 1].q) i++;
  const a = keys[i];
  const b = keys[i + 1];
  const t = ease(clamp01((q - a.q) / (b.q - a.q)));
  out.pos.lerpVectors(a.pos, b.pos, t);
  out.look.lerpVectors(a.look, b.look, t);
  out.shift.lerpVectors(a.shift, b.shift, t);
}

/** Répartit l'avancement du voyage en étapes : arrêt en ville, trajet, arrêt suivant. */
function tripPose(cities, progress) {
  const legs = cities.length - 1;
  const x = clamp01(progress) * legs;
  const i = Math.min(Math.floor(x), legs - 1);
  const t = ease(clamp01((x - i - 0.2) / 0.6));
  return {
    u: mix(cities[i].u, cities[i + 1].u, t),
    focus: t < 0.5 ? i : i + 1,
    hold: Math.abs(Math.cos(Math.PI * t)),
  };
}

/** Crée la scène 3D et renvoie de quoi la piloter depuis le défilement de la page. */
export async function createWorld(canvas, { onSnapshot, onInterior } = {}) {
  const coarse = window.matchMedia('(pointer: coarse)').matches;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setClearColor(SKY);
  let pixelRatio = Math.min(window.devicePixelRatio || 1, coarse ? 1.75 : 2);
  renderer.setPixelRatio(pixelRatio);

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(SKY, 30, 75);
  scene.add(new THREE.HemisphereLight(0xfffaf0, 0xd8cbb6, 1.75));
  const sun = new THREE.DirectionalLight(0xfff4e0, 1.7);
  sun.position.set(-6, 12, 7);
  scene.add(sun);

  const camera = new THREE.PerspectiveCamera(32, 1, 0.3, 240);
  const snapCamera = new THREE.PerspectiveCamera(36, 1, 0.3, 240);
  let width = 1;
  let height = 1;
  let portrait = false;

  /** Aligne le rendu sur la taille réelle du canevas. */
  function resize() {
    width = canvas.clientWidth || window.innerWidth;
    height = canvas.clientHeight || window.innerHeight;
    portrait = width / height < 1;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.fov = portrait ? 44 : 32;
    camera.updateProjectionMatrix();
  }
  resize();
  new ResizeObserver(resize).observe(canvas);

  const [cityModels, vanModel] = await Promise.all([loadModel(`${MODELS}cities.glb`), loadModel(`${MODELS}van.glb`)]);
  const map = buildMap(cityModels);
  scene.add(map.group);
  const length = map.curve.getLength();

  const vanParked = vanModel.clone();
  const van = vanModel;
  van.scale.setScalar(VAN_SCALE);
  map.group.add(van);
  const wheels = ['wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr'].map((name) => van.getObjectByName(name)).filter(Boolean);
  const vanShadow = new THREE.Mesh(
    new THREE.CircleGeometry(1, 18),
    new THREE.MeshBasicMaterial({ color: 0x3a2a20, transparent: true, opacity: 0.22, depthWrite: false }),
  );
  vanShadow.rotation.x = -Math.PI / 2;
  vanShadow.scale.set(0.5, 0.85, 1);
  map.group.add(vanShadow);

  let diorama = null;
  let snapshotPending = false;
  let keysLandscape = null;
  let keysPortrait = null;
  const propHome = v(0, 0, 0);

  Promise.all([loadModel(`${MODELS}storefront.glb`), loadModel(`${MODELS}camera.glb`)])
    .then(([storefront, prop]) => buildDiorama({ storefront, van: vanParked, prop }))
    .then((built) => {
      const dx = built.doorCenter.x;
      keysLandscape = [
        { q: 0, pos: v(11, 5.2, 21), look: v(0.4, 3.0, 2), shift: v(0.17, 0.02, 0) },
        { q: 0.2, pos: v(8, 3.8, 18.5), look: v(0.4, 2.9, 2), shift: v(0.12, 0.02, 0) },
        { q: 0.4, pos: v(1.4, 2.9, 15.6), look: v(-0.5, 2.9, 0), shift: v(0, 0.03, 0) },
        { q: 0.62, pos: v(1.1, 2.8, 15), look: v(-0.5, 2.9, 0), shift: v(0, 0.03, 0) },
        { q: 0.86, pos: v(dx + 0.7, 1.9, 9), look: v(dx, 1.6, 0), shift: v(0, 0, 0) },
        { q: 1, pos: v(dx, 1.55, 1.5), look: v(dx, 1.45, -2), shift: v(0, 0, 0) },
      ];
      keysPortrait = [
        { q: 0, pos: v(5.5, 6, 30), look: v(0, 3.4, 1), shift: v(0, 0.2, 0) },
        { q: 0.2, pos: v(4, 5, 27), look: v(0, 3.4, 1), shift: v(0, 0.12, 0) },
        { q: 0.4, pos: v(1.9, 3.4, 21.5), look: v(0, 3.3, 0), shift: v(0, -0.04, 0) },
        { q: 0.62, pos: v(1.7, 3.3, 21), look: v(0, 3.3, 0), shift: v(0, -0.04, 0) },
        { q: 0.86, pos: v(dx + 0.4, 2.1, 12), look: v(dx, 1.7, 0), shift: v(0, 0, 0) },
        { q: 1, pos: v(dx, 1.6, 2.2), look: v(dx, 1.5, -2), shift: v(0, 0, 0) },
      ];
      built.group.visible = false;
      scene.add(built.group);
      diorama = built;
      snapshotPending = true;
    })
    .catch((error) => console.warn('[resto-avenue] décor restaurateurs indisponible', error));

  let interior = null;
  let focused = null;
  const spots = SPOTS.map((name) => ({ name, x: 0, y: 0 }));
  loadModel(`${MODELS}interior.glb`)
    .then((room) => {
      const nodes = SPOTS.map((name) => room.getObjectByName(name));
      if (nodes.some((node) => !node)) throw new Error('points de contact manquants');
      room.visible = false;
      scene.add(room);
      room.updateWorldMatrix(true, true);
      interior = {
        group: room,
        nodes,
        homes: nodes.map((node) => node.position.clone()),
        tops: nodes.map((node) => new THREE.Box3().setFromObject(node).max.y - node.getWorldPosition(v(0, 0, 0)).y),
      };
      onInterior?.();
    })
    .catch((error) => console.warn('[resto-avenue] salle de contact indisponible', error));

  const rig = { pos: v(0, 0, 0), look: v(0, 0, 0), shift: v(0, 0, 0) };
  const wide = { pos: v(0, 0, 0), look: v(0, 0, 0) };
  const follow = { pos: v(0, 0, 0), look: v(0, 0, 0) };
  const tangent = v(0, 0, 0);
  const vanPosition = v(0, 0, 0);
  const aim = v(0, 0, 0);
  const wideLook = geo(3.72, 43.5, 0.4);
  const pointer = { x: 0, y: 0 };
  if (!coarse) {
    window.addEventListener('pointermove', (event) => {
      pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
      pointer.y = (event.clientY / window.innerHeight) * 2 - 1;
    });
  }
  let fireTime = Infinity;
  let slowFrames = 0;
  let frameTime = 16;

  /** Place la caméra et la camionnette sur la carte selon le défilement. */
  function updateMap(state, time) {
    const pose = tripPose(map.cities, state.trip);
    map.curve.getPointAt(pose.u, vanPosition);
    map.curve.getTangentAt(pose.u, tangent);
    const moving = 1 - pose.hold;
    van.position.copy(vanPosition);
    van.position.y += Math.sin(time * 14) * 0.006 * moving;
    van.rotation.y = Math.atan2(tangent.x, tangent.z);
    van.rotation.z = Math.sin(time * 9) * 0.012 * moving;
    const spin = (pose.u * length) / (WHEEL_RADIUS * VAN_SCALE);
    wheels.forEach((wheel) => (wheel.rotation.x = spin));
    vanShadow.position.set(vanPosition.x, vanPosition.y + 0.03, vanPosition.z);
    vanShadow.rotation.z = van.rotation.y;

    map.cities.forEach((city, i) => {
      const active = i === pose.focus && pose.hold > 0.6 ? 1 : 0.7;
      city.pin.scale.setScalar(mix(city.pin.scale.x, active, 0.12));
      city.pin.position.y = 3.25 + Math.sin(time * 2 + i * 1.7) * 0.1;
      city.pin.rotation.y = time * 0.8 + i;
    });

    const city = map.cities[pose.focus];
    follow.look.copy(vanPosition).lerp(city.position, 0.46 * pose.hold);
    follow.look.y = 0.7;
    const distance = portrait ? mix(23, 19.5, pose.hold) : mix(15.5, 12.5, pose.hold);
    follow.pos.set(portrait ? 0.08 : 0.16, portrait ? 0.7 : 0.62, portrait ? 0.72 : 0.78).normalize().multiplyScalar(distance).add(follow.look);

    wide.look.copy(wideLook);
    wide.look.x += Math.sin(time * 0.25) * 0.5;
    wide.pos.set(0.12, 0.68, 0.74).normalize().multiplyScalar(portrait ? 46 : 29).add(wide.look);

    const e = ease(clamp01(state.hero));
    rig.pos.lerpVectors(wide.pos, follow.pos, e);
    rig.look.lerpVectors(wide.look, follow.look, e);
    if (portrait) rig.shift.set(0, mix(0.3, -0.13, e), 0);
    else if (height < 560) rig.shift.set(mix(0.3, 0.13, e), mix(0.05, 0.02, e), 0);
    else rig.shift.set(mix(0, 0.13, e), mix(0.27, 0.02, e), 0);
  }

  /** Joue la séquence restaurateurs : approche, cadrage, photo puis entrée par la porte. */
  function updateDiorama(state, time, dt) {
    const q = clamp01(state.pro);
    sampleKeys(portrait ? keysPortrait : keysLandscape, q, rig);
    rig.pos.x += Math.sin(time * 0.5) * 0.12 * (1 - q);
    rig.pos.y += Math.sin(time * 0.7) * 0.06 * (1 - q);

    const arrive = ease(clamp01((q - 0.04) / 0.18));
    const leave = ease(clamp01((q - 0.66) / 0.14));
    if (portrait) propHome.set(1.5, 1.9, 15.5);
    else propHome.set(4.3, 1.75, 10.8);
    diorama.prop.position.set(
      propHome.x + (1 - arrive) * 5 + leave * 7,
      propHome.y + (1 - arrive) * 4 + leave * 3 + Math.sin(time * 1.6) * 0.07,
      propHome.z,
    );
    aim.set(Math.sin(time * 0.9) * 0.25, 2.7, 0);
    diorama.prop.lookAt(aim);
    diorama.prop.rotateZ(Math.sin(time * 1.1) * 0.03);

    fireTime += dt;
    diorama.setFire(fireTime < 0.45 ? 1 - fireTime / 0.45 : 0);
    if (diorama.door) diorama.door.rotation.y = diorama.doorSwing * ease(clamp01((q - 0.82) / 0.12)) * 1.8;
  }

  /** Cadre la salle du restaurant et calcule la position à l'écran des points de contact. */
  function updateInterior(state, time) {
    const e = ease(clamp01(state.contact));
    if (portrait) {
      rig.pos.set(0, mix(2.9, 2.0, e), mix(13, 8.6, e));
      rig.look.set(0, 1.75, -3);
      rig.shift.set(0, width < 640 ? 0.1 : 0.03, 0);
    } else {
      rig.pos.set(pointer.x * 0.5, mix(2.7, 1.9, e) + pointer.y * 0.15, mix(10, 6.1, e));
      rig.look.set(0, 1.6, -3);
      rig.shift.set(0, height < 560 ? 0.13 : 0.1, 0);
    }
    interior.nodes.forEach((node, i) => {
      const lift = node.name === focused ? 0.12 : 0;
      node.position.y = mix(node.position.y, interior.homes[i].y + lift + Math.sin(time * 2 + i * 1.5) * 0.025, 0.2);
      node.rotation.y = node.name === focused ? Math.sin(time * 6) * 0.12 : 0;
    });
  }

  /** Projette les points de contact à l'écran, une fois la caméra placée. */
  function projectSpots() {
    interior.nodes.forEach((node, i) => {
      node.getWorldPosition(aim);
      aim.y += interior.tops[i] + 0.02;
      aim.project(camera);
      spots[i].x = (aim.x * 0.5 + 0.5) * width;
      spots[i].y = (-aim.y * 0.5 + 0.5) * height;
    });
  }

  /** Prend la « photo » de la devanture affichée ensuite dans la carte du service phare. */
  function snapshot() {
    snapshotPending = false;
    if (!onSnapshot) return;
    const target = 4 / 3;
    const aspect = width / height;
    const cropWidth = aspect > target ? height * target : width;
    const cropHeight = cropWidth / target;
    const half = Math.tan(THREE.MathUtils.degToRad(19)) * (height / cropHeight);
    snapCamera.fov = THREE.MathUtils.radToDeg(Math.atan(half)) * 2;
    snapCamera.aspect = aspect;
    snapCamera.position.set(1.2, 2.3, 17);
    snapCamera.lookAt(0, 3.1, 0);
    snapCamera.updateProjectionMatrix();
    const mapVisible = map.group.visible;
    map.group.visible = false;
    diorama.group.visible = true;
    diorama.prop.visible = false;
    scene.fog.near = 40;
    scene.fog.far = 110;
    renderer.render(scene, snapCamera);
    const output = document.createElement('canvas');
    output.width = 640;
    output.height = 480;
    const scale = renderer.domElement.width / width;
    output
      .getContext('2d')
      .drawImage(
        renderer.domElement,
        ((width - cropWidth) / 2) * scale,
        ((height - cropHeight) / 2) * scale,
        cropWidth * scale,
        cropHeight * scale,
        0,
        0,
        640,
        480,
      );
    diorama.prop.visible = true;
    map.group.visible = mapVisible;
    onSnapshot(output.toDataURL('image/jpeg', 0.82));
  }

  /** Baisse la résolution de rendu si l'appareil ne tient pas la cadence. */
  function adapt(dt) {
    frameTime = mix(frameTime, dt * 1000, 0.08);
    slowFrames = frameTime > 26 ? slowFrames + 1 : 0;
    if (slowFrames > 45 && pixelRatio > 1) {
      pixelRatio = Math.max(1, pixelRatio - 0.25);
      renderer.setPixelRatio(pixelRatio);
      renderer.setSize(width, height, false);
      slowFrames = 0;
      frameTime = 16;
    }
  }

  return {
    /** Déclenche le flash de l'appareil photo. */
    fire() {
      fireTime = 0;
    },
    spots,
    /** Met en avant un point de contact (ou aucun). */
    focus(name) {
      focused = name;
    },
    get dioramaReady() {
      return diorama !== null;
    },
    /** Met à jour puis dessine une image. */
    update(state, time, dt) {
      if (snapshotPending) snapshot();
      const showInterior = state.stage === 'interior' && interior !== null;
      const showDiorama = !showInterior && state.stage !== 'map' && diorama !== null;
      map.group.visible = !showDiorama && !showInterior;
      if (diorama) diorama.group.visible = showDiorama;
      if (interior) interior.group.visible = showInterior;
      if (showInterior) {
        scene.fog.near = 40;
        scene.fog.far = 110;
        updateInterior(state, time);
      } else if (showDiorama) {
        scene.fog.near = 40;
        scene.fog.far = 110;
        updateDiorama(state, time, dt);
      } else {
        scene.fog.near = portrait ? 34 : 26;
        scene.fog.far = portrait ? 90 : 70;
        updateMap(state, time);
      }
      camera.position.copy(rig.pos);
      camera.lookAt(rig.look);
      camera.setViewOffset(width, height, -rig.shift.x * width, -rig.shift.y * height, width, height);
      if (showInterior) {
        camera.updateMatrixWorld();
        projectSpots();
      }
      renderer.render(scene, camera);
      adapt(dt);
    },
  };
}
