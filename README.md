# Resto Avenue : landing page

Refonte de la page d'accueil de resto-avenue.fr : voyage 3D de ville en ville, séquence « restaurateurs », contact.
La conception est décrite dans [docs/CONCEPTION.md](docs/CONCEPTION.md).

## Commandes

```bash
npm install
npm run dev      # développement, http://localhost:5173
npm run build    # site statique dans dist/
npm run preview  # sert dist/ en local
npm run shots    # captures de contrôle (installe puppeteer-core à la volée, Chrome requis)
```

## Organisation

- `index.html` : tout le contenu et les liens (lisible sans JavaScript).
- `src/main.js` : relie le défilement à la page et à la scène 3D.
- `src/three/` : scène Three.js (`map.js` la carte, `diorama.js` la rue du restaurant, `world.js` caméra et rendu).
- `public/models/` : modèles GLB.
- `assets-src/blender/` : scripts Blender qui génèrent les modèles (`blender --background --python build_van.py`), fichiers `.blend` et aperçus.

## Modifier les contenus

- Textes, liens des villes, coordonnées : `index.html`.
- Étiquettes de trajet (distances) : `LEGS` dans `src/main.js`.
- Position des villes et tracé de la route : `CITIES` et `ROAD` dans `src/three/map.js`.
