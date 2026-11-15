import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
const materials = new Map();

/** Remplace un matériau PBR par un Lambert partagé, bien moins coûteux sur mobile. */
function toLambert(source) {
  const key = source.name || source.uuid;
  if (!materials.has(key)) {
    const material = new THREE.MeshLambertMaterial({ name: source.name, color: source.color });
    if (source.emissive && source.emissive.getHex() !== 0) {
      // Couleur de base neutralisée : sinon l'éclairage s'ajoute à l'émissif et sature en jaune citron.
      material.color.set(0x000000);
      material.emissive.copy(source.emissive);
    }
    materials.set(key, material);
  }
  return materials.get(key);
}

/** Charge un GLB et renvoie sa scène avec des matériaux allégés. */
export async function loadModel(url) {
  const gltf = await loader.loadAsync(url);
  gltf.scene.traverse((node) => {
    if (!node.isMesh) return;
    node.material = Array.isArray(node.material) ? node.material.map(toLambert) : toLambert(node.material);
    node.matrixAutoUpdate = true;
  });
  return gltf.scene;
}

/** Renvoie un matériau Lambert partagé par couleur. */
export function flat(color) {
  const key = `flat:${color}`;
  if (!materials.has(key)) materials.set(key, new THREE.MeshLambertMaterial({ color }));
  return materials.get(key);
}

/** Générateur pseudo-aléatoire déterministe, pour un décor identique à chaque visite. */
export function seeded(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const clamp01 = (v) => Math.min(1, Math.max(0, v));
export const ease = (t) => t * t * (3 - 2 * t);
export const mix = (a, b, t) => a + (b - a) * t;
