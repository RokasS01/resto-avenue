import * as THREE from 'three';
import { flat } from './assets.js';

/** Dessine le texte de l'enseigne dans une texture, une fois la police chargée. */
async function signTexture(text) {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 176;
  const context = canvas.getContext('2d');
  const font = '600 104px "Fraunces Variable", Georgia, serif';
  try {
    await document.fonts.load(font, text);
  } catch {
    /* police de secours */
  }
  context.font = font;
  context.fillStyle = '#ae3037';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text, canvas.width / 2, canvas.height / 2 + 6, canvas.width - 40);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

/** Immeuble voisin très simple, pour fermer la rue de part et d'autre de la devanture. */
function neighbour(width, height, depth, wall, x) {
  const block = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), flat(wall));
  body.position.y = height / 2;
  const roof = new THREE.Mesh(new THREE.BoxGeometry(width + 0.3, 0.28, depth + 0.3), flat(0xc9714a));
  roof.position.y = height + 0.14;
  block.add(body, roof);
  const shutter = flat(0x6f9aa8);
  const columns = Math.max(2, Math.round(width / 2.2));
  for (let floor = 0; floor < Math.floor(height / 2.8); floor++) {
    for (let i = 0; i < columns; i++) {
      const pane = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.3, 0.08), shutter);
      pane.position.set(-width / 2 + (width / columns) * (i + 0.5), 1.7 + floor * 2.8, depth / 2 + 0.02);
      block.add(pane);
    }
  }
  block.position.set(x, 0, -depth / 2);
  return block;
}

/** Construit la rue du restaurant : devanture, camionnette garée et appareil photo. */
export async function buildDiorama({ storefront, van, prop }) {
  const group = new THREE.Group();

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(160, 160), flat(0xeadcc0));
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.01;
  const street = new THREE.Mesh(new THREE.PlaneGeometry(160, 5.4), flat(0xb9aea0));
  street.rotation.x = -Math.PI / 2;
  street.position.set(0, 0, 8.2);
  group.add(ground, street, storefront);

  storefront.updateWorldMatrix(true, true);
  const bounds = new THREE.Box3().setFromObject(storefront);
  group.add(
    neighbour(7, 8.6, 3, 0xe9c2a6, bounds.min.x - 3.6),
    neighbour(6, 5.6, 3, 0xf0dcb8, bounds.max.x + 3.1),
    neighbour(8, 7.4, 3, 0xe6cfa2, bounds.max.x + 10.2),
    neighbour(8, 6.2, 3, 0xf0dcb8, bounds.min.x - 11.2),
  );

  const sign = storefront.getObjectByName('sign');
  if (sign) {
    const box = new THREE.Box3().setFromObject(sign);
    const size = box.getSize(new THREE.Vector3());
    const label = new THREE.Mesh(
      new THREE.PlaneGeometry(size.x * 0.94, size.y * 0.9),
      new THREE.MeshBasicMaterial({ map: await signTexture('Votre restaurant'), transparent: true }),
    );
    label.position.set((box.min.x + box.max.x) / 2, (box.min.y + box.max.y) / 2, box.max.z + 0.012);
    group.add(label);
  }

  const door = storefront.getObjectByName('door');
  const doorBox = door ? new THREE.Box3().setFromObject(door) : new THREE.Box3(new THREE.Vector3(-0.5, 0, 0), new THREE.Vector3(0.5, 2.2, 0));
  const doorCenter = doorBox.getCenter(new THREE.Vector3());
  let doorSwing = 1;
  if (door) {
    const hinge = door.getWorldPosition(new THREE.Vector3());
    doorSwing = doorCenter.x >= hinge.x ? 1 : -1;
  }

  van.position.set(bounds.min.x + 0.4, 0, 7.6);
  van.rotation.y = Math.PI / 2 - 0.12;
  group.add(van);

  const shadow = new THREE.Mesh(
    new THREE.CircleGeometry(1, 20),
    new THREE.MeshBasicMaterial({ color: 0x3a2a20, transparent: true, opacity: 0.2, depthWrite: false }),
  );
  shadow.rotation.x = -Math.PI / 2;
  shadow.scale.set(2.4, 1.2, 1);
  shadow.rotation.z = van.rotation.y - Math.PI / 2;
  shadow.position.set(van.position.x, 0.02, van.position.z);
  group.add(shadow);

  group.add(prop);
  const flash = prop.getObjectByName('cam_flash');
  let flashMaterial = null;
  if (flash) {
    flash.traverse((node) => {
      if (!node.isMesh) return;
      flashMaterial = new THREE.MeshLambertMaterial({ color: 0xfff6e0, emissive: 0xffffff, emissiveIntensity: 0 });
      node.material = flashMaterial;
    });
  }
  const shutter = prop.getObjectByName('cam_shutter');
  const shutterY = shutter ? shutter.position.y : 0;

  return {
    group,
    prop,
    door,
    doorSwing,
    doorCenter,
    bounds,
    flashMaterial,
    /** Enfonce le déclencheur et allume le flash selon l'avancement du tir (0 à 1). */
    setFire(amount) {
      if (flashMaterial) flashMaterial.emissiveIntensity = amount * 3;
      if (shutter) shutter.position.y = shutterY - amount * 0.03;
    },
  };
}
