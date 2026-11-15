import * as THREE from 'three';
import { flat, seeded } from './assets.js';

const LON0 = 2.9;
const LAT0 = 43.3;
const SCALE = 9;
// Un degré de latitude vaut environ 1,38 degré de longitude à cette latitude.
const LAT_RATIO = 1.38;

/** Convertit une longitude / latitude en position sur le plateau. */
export function geo(lon, lat, y = 0) {
  return new THREE.Vector3((lon - LON0) * SCALE, y, -(lat - LAT0) * SCALE * LAT_RATIO);
}

const COAST = [
  [3.22, 41.6],
  [3.2, 42.3],
  [3.05, 42.55],
  [3.04, 42.78],
  [3.06, 43.0],
  [3.13, 43.15],
  [3.28, 43.25],
  [3.5, 43.28],
  [3.7, 43.4],
  [3.95, 43.54],
  [4.15, 43.5],
  [4.4, 43.44],
  [4.75, 43.38],
  [5.6, 43.34],
  [7.2, 43.3],
];

const ROAD = [
  [6.2, 44.5],
  [5.4, 44.22],
  [4.8, 43.98],
  [4.36, 43.8],
  [4.1, 43.68],
  [3.88, 43.58],
  [3.55, 43.47],
  [3.22, 43.33],
  [3.02, 43.17],
  [3.0, 42.95],
  [2.97, 42.72],
  [2.84, 42.6],
  [2.55, 42.62],
  [2.25, 42.85],
  [1.95, 43.15],
  [1.7, 43.42],
  [1.46, 43.56],
  [0.95, 43.8],
  [0.3, 44.02],
  [-0.5, 44.2],
  [-1.4, 44.3],
];

const GARONNE = [
  [0.55, 42.6],
  [0.95, 43.05],
  [1.14, 43.38],
  [1.2, 43.66],
  [1.04, 43.96],
  [0.7, 44.25],
  [0.25, 44.55],
  [-0.4, 44.8],
];

const FIELD_COLORS = [0xf2c45a, 0x9db06b, 0xbaa6d0, 0xecd9a0, 0xd9b58c, 0xb7c587];

export const CITIES = [
  { id: 'nimes', name: 'Nîmes', stop: [4.36, 43.8], offset: [0.1, -2.6] },
  { id: 'montpellier', name: 'Montpellier', stop: [3.88, 43.58], offset: [0.2, -2.6] },
  { id: 'beziers', name: 'Béziers', stop: [3.22, 43.33], offset: [-0.4, -2.7] },
  { id: 'perpignan', name: 'Perpignan', stop: [2.84, 42.6], offset: [-1.0, -2.6] },
  { id: 'toulouse', name: 'Toulouse', stop: [1.46, 43.56], offset: [0.3, -2.6] },
];

const LAND_Y = 0.25;

/** Construit le contour de la terre : côte lissée puis bords lointains hors champ. */
function landOutline() {
  const coast = new THREE.CatmullRomCurve3(COAST.map(([lon, lat]) => geo(lon, lat))).getPoints(70);
  const far = [
    [7.2, 45.8],
    [-3.6, 45.8],
    [-3.6, 41.6],
  ].map(([lon, lat]) => geo(lon, lat));
  return [...coast, ...far];
}

/** Indique si un point du plateau est sur la terre. */
function inside(outline, x, z) {
  let hit = false;
  for (let i = 0, j = outline.length - 1; i < outline.length; j = i++) {
    const a = outline[i];
    const b = outline[j];
    if (a.z > z !== b.z > z && x < ((b.x - a.x) * (z - a.z)) / (b.z - a.z) + a.x) hit = !hit;
  }
  return hit;
}

/** Ruban plat qui suit une courbe, utilisé pour la route et sa ligne centrale. */
function ribbon(points, halfWidth, y) {
  const positions = [];
  const indices = [];
  const up = new THREE.Vector3(0, 1, 0);
  const side = new THREE.Vector3();
  points.forEach((point, i) => {
    const next = points[Math.min(i + 1, points.length - 1)];
    const prev = points[Math.max(i - 1, 0)];
    side.subVectors(next, prev).normalize().cross(up).multiplyScalar(halfWidth);
    positions.push(point.x - side.x, y, point.z - side.z, point.x + side.x, y, point.z + side.z);
    if (i < points.length - 1) {
      const k = i * 2;
      indices.push(k, k + 1, k + 2, k + 1, k + 3, k + 2);
    }
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

/** Tire des positions sur la terre, à l'écart des zones déjà occupées. */
function sample({ count, random, outline, area, blocked, clearance, spacing = 0 }) {
  const points = [];
  let guard = 0;
  while (points.length < count && guard++ < count * 60) {
    const x = area.x0 + random() * (area.x1 - area.x0);
    const z = area.z0 + random() * (area.z1 - area.z0);
    if (!inside(outline, x, z)) continue;
    if (blocked.some((b) => Math.hypot(b.x - x, b.z - z) < clearance + (b.r ?? 0))) continue;
    if (spacing && points.some((p) => Math.hypot(p.x - x, p.z - z) < spacing)) continue;
    points.push({ x, z });
  }
  return points;
}

/** Crée un maillage instancié à partir d'une liste de poses. */
function instances(geometry, material, poses) {
  const mesh = new THREE.InstancedMesh(geometry, material, poses.length);
  const dummy = new THREE.Object3D();
  const color = new THREE.Color();
  poses.forEach((pose, i) => {
    dummy.position.set(pose.x, pose.y, pose.z);
    dummy.rotation.set(0, pose.turn ?? 0, 0);
    dummy.scale.set(pose.sx ?? 1, pose.sy ?? 1, pose.sz ?? 1);
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
    if (pose.color !== undefined) mesh.setColorAt(i, color.setHex(pose.color));
  });
  mesh.instanceMatrix.needsUpdate = true;
  return mesh;
}

/** Construit le plateau « Occitanie » : mer, terre, route, villes, repères et décor. */
export function buildMap(cityModels) {
  const group = new THREE.Group();
  const outline = landOutline();
  const random = seeded(2015);
  const between = (a, b) => a + random() * (b - a);

  const sea = new THREE.Mesh(new THREE.PlaneGeometry(260, 260), flat(0x63b3bf));
  sea.rotation.x = -Math.PI / 2;
  sea.position.y = 0.06;
  group.add(sea);

  const shape = new THREE.Shape(outline.map((p) => new THREE.Vector2(p.x, -p.z)));
  const land = new THREE.Mesh(
    new THREE.ExtrudeGeometry(shape, { depth: LAND_Y, bevelEnabled: false, curveSegments: 1 }),
    flat(0xe9e0c8),
  );
  land.rotation.x = -Math.PI / 2;
  group.add(land);

  const etang = new THREE.Mesh(new THREE.CircleGeometry(0.55, 14), flat(0x63b3bf));
  etang.rotation.x = -Math.PI / 2;
  etang.scale.set(1.7, 0.7, 1);
  etang.rotation.z = 0.5;
  etang.position.copy(geo(3.63, 43.42, LAND_Y + 0.01));
  group.add(etang);

  const river = new THREE.CatmullRomCurve3(GARONNE.map(([lon, lat]) => geo(lon, lat, LAND_Y))).getSpacedPoints(90);
  group.add(new THREE.Mesh(ribbon(river, 0.26, LAND_Y + 0.006), flat(0x63b3bf)));

  const curve = new THREE.CatmullRomCurve3(ROAD.map(([lon, lat]) => geo(lon, lat, LAND_Y)), false, 'catmullrom', 0.5);
  curve.arcLengthDivisions = 800;
  const roadPoints = curve.getSpacedPoints(480);
  group.add(new THREE.Mesh(ribbon(roadPoints, 0.3, LAND_Y + 0.014), flat(0x5d5550)));
  group.add(new THREE.Mesh(ribbon(roadPoints, 0.035, LAND_Y + 0.022), flat(0xfffaf1)));

  const cities = CITIES.map((city) => {
    const stop = geo(city.stop[0], city.stop[1], LAND_Y);
    const position = stop.clone().add(new THREE.Vector3(city.offset[0], 0, city.offset[1]));
    let best = 0;
    let bestDistance = Infinity;
    roadPoints.forEach((p, i) => {
      const d = p.distanceToSquared(stop);
      if (d < bestDistance) {
        bestDistance = d;
        best = i;
      }
    });
    const model = cityModels.getObjectByName(`city_${city.id}`);
    if (model) {
      model.position.copy(position);
      model.rotation.y = 0.18;
      group.add(model);
    }
    const pin = new THREE.Group();
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.26, 12, 10), flat(0xae3037));
    const tip = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.5, 10), flat(0xae3037));
    tip.rotation.x = Math.PI;
    tip.position.y = -0.36;
    pin.add(head, tip);
    pin.position.copy(position).setY(3.25);
    pin.scale.setScalar(0.7);
    group.add(pin);
    return { ...city, position, pin, u: best / (roadPoints.length - 1) };
  });

  const blocked = [
    ...roadPoints.map((p) => ({ x: p.x, z: p.z })),
    ...river.map((p) => ({ x: p.x, z: p.z })),
    ...cities.map((c) => ({ x: c.position.x, z: c.position.z, r: 1.7 })),
  ];
  const everywhere = { x0: -26, x1: 24, z0: -22, z1: 16 };
  // L'arrivée sur Toulouse est loin de la mer et des autres villes : on y densifie champs et villages.
  const lauragais = { x0: -21, x1: -6, z0: -11, z1: 3 };
  const base = { random, outline, blocked };

  const fieldSpots = sample({ ...base, count: 60, area: everywhere, clearance: 1.5, spacing: 2.3 });
  fieldSpots.push(
    ...sample({
      ...base,
      blocked: [...blocked, ...fieldSpots.map((p) => ({ ...p, r: 0.8 }))],
      count: 26,
      area: lauragais,
      clearance: 1.5,
      spacing: 2.3,
    }),
  );
  group.add(
    instances(
      new THREE.BoxGeometry(1, 0.02, 1),
      new THREE.MeshLambertMaterial({ color: 0xffffff }),
      fieldSpots.map((p) => ({
        ...p,
        y: LAND_Y + 0.011,
        turn: between(0, Math.PI),
        sx: between(0.9, 1.6),
        sz: between(0.7, 1.3),
        color: FIELD_COLORS[Math.floor(random() * FIELD_COLORS.length)],
      })),
    ),
  );
  fieldSpots.forEach((p) => blocked.push({ ...p, r: 0.55 }));

  const villageSpots = [
    ...sample({ ...base, count: 16, area: everywhere, clearance: 1.3 }),
    ...sample({ ...base, count: 9, area: lauragais, clearance: 1.3 }),
  ];
  const walls = [0xf3e6cc, 0xecd3a8, 0xe9c2a6];
  const houses = villageSpots.flatMap((spot) =>
    Array.from({ length: 3 + Math.floor(random() * 3) }, () => ({
      x: spot.x + between(-0.55, 0.55),
      z: spot.z + between(-0.55, 0.55),
      turn: between(0, Math.PI),
      s: between(0.75, 1.15),
      color: walls[Math.floor(random() * walls.length)],
    })),
  );
  const roofGeometry = new THREE.ConeGeometry(0.27, 0.2, 4);
  roofGeometry.rotateY(Math.PI / 4);
  group.add(
    instances(
      new THREE.BoxGeometry(0.34, 0.26, 0.34),
      new THREE.MeshLambertMaterial({ color: 0xffffff }),
      houses.map((h) => ({ ...h, y: LAND_Y + 0.13 * h.s, sx: h.s, sy: h.s, sz: h.s })),
    ),
    instances(
      roofGeometry,
      flat(0xc9714a),
      houses.map((h) => ({ x: h.x, z: h.z, turn: h.turn, y: LAND_Y + 0.36 * h.s, sx: h.s, sy: h.s, sz: h.s })),
    ),
  );
  villageSpots.forEach((p) => blocked.push({ ...p, r: 0.9 }));

  /** Arbres et collines : une forme, une couleur, une hauteur d'ancrage. */
  const plant = (geometry, color, count, area, scale, lift, clearance) =>
    instances(
      geometry,
      flat(color),
      sample({ ...base, count, area, clearance }).map((p) => {
        const s = between(scale[0], scale[1]);
        return { ...p, y: LAND_Y + lift * s, turn: between(0, Math.PI), sx: s, sy: s * between(0.8, 1.3), sz: s };
      }),
    );
  group.add(
    plant(new THREE.ConeGeometry(0.2, 0.62, 5), 0x4f6b4a, 230, everywhere, [0.7, 1.5], 0.31, 0.7),
    plant(new THREE.IcosahedronGeometry(0.24, 0), 0x7c8f5a, 150, everywhere, [0.7, 1.4], 0.16, 0.7),
    plant(new THREE.ConeGeometry(1.5, 1.3, 6), 0xd6c9a4, 30, { x0: -26, x1: 24, z0: -24, z1: -11.5 }, [0.6, 1.3], 0.6, 2.6),
  );

  return { group, curve, cities };
}
