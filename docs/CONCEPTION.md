# Refonte de la landing page Resto Avenue : conception

## 1. Constat sur le site actuel

- Une page unique découpée en 7 sections (Accueil, Rubriques, Villes, Avec vous, Partenaires, L'Équipe, Contact). Le message principal est noyé : il faut lire un long paragraphe pour comprendre ce qu'est Resto Avenue.
- Les 5 sites de ville (le vrai produit) n'apparaissent que sous forme de petits liens, deux fois.
- Socle technique daté (Bootstrap 3, jQuery 1.11, 10 scripts, animations au défilement calculées en JavaScript), d'où les saccades sur mobile.

## 2. Objectifs

1. Comprendre en 3 secondes : qui (Resto Avenue), quoi (le guide des restaurants d'Occitanie), où (5 villes), pour quoi faire (trouver où manger).
2. Emmener le visiteur vers le site de sa ville en un geste.
3. Donner envie aux restaurateurs de prendre contact, en mettant un service en avant plutôt qu'une liste.
4. Rester fluide sur téléphone, tablette et ordinateur.

## 3. Deux publics, un seul fil

| Public | Ce qu'il cherche | Où il trouve la réponse |
|---|---|---|
| Le gourmand | « Où manger dans ma ville ? » | Accueil puis voyage de ville en ville |
| Le restaurateur | « Que peut faire Resto Avenue pour moi ? » | Séquence « On vient filmer chez vous », puis contact |

Le fil conducteur est une **camionnette de tournage aux couleurs de la marque**. Elle roule de ville en ville (partie gourmands), puis se gare devant un restaurant pour le filmer (partie restaurateurs). Une voiture plutôt qu'un avion : les villes sont à 55–205 km les unes des autres, et la camionnette incarne l'équipe « sur le terrain ».

## 4. Déroulé de la page

### Acte 1 : Accueil
- En-tête réduit au logo et à un bouton « Contact ».
- Titre centré : « Les bonnes tables d'Occitanie, ville par ville. », une phrase qui cite les 5 villes, deux boutons (« Choisir ma ville », « Je suis restaurateur »).
- En fond : la carte de l'Occitanie en relief, vue de haut, avec les 5 villes signalées par un repère rouge.

### Acte 2 : Le voyage (remplace « Accueil » et « Villes »)
- Au défilement, la caméra plonge sur la carte et suit la camionnette le long de la route : **Nîmes → Montpellier → Béziers → Perpignan → Toulouse** (ordre géographique, d'est en ouest).
- Chaque ville est une miniature reconnaissable à son monument : Arènes, arc du Peyrou, cathédrale Saint-Nazaire et Pont Vieux, Castillet, Capitole.
- À chaque arrêt, une carte s'affiche : nom, accroche, bouton « Les restaurants à … » vers le site de la ville. Entre deux arrêts, une étiquette indique le trajet (« Nîmes → Montpellier · ≈ 55 km »).
- Un rail de 5 points permet de sauter directement à une ville.

### Transition : le rideau
- Un grand panneau rouge traverse l'écran : « Et si la prochaine adresse, c'était la vôtre ? ». Il marque le changement de public et masque le changement de décor.

### Acte 3 : Les services (remplace « Rubriques » et « Avec vous »)
- Décor : une devanture de restaurant du Sud, terrasse, camionnette garée. L'enseigne affiche « Votre restaurant ».
- Séquence : un appareil photo entre dans le champ, le viseur s'affiche (REC), **flash**, et la photo prise devient la carte du service phare.
- **Service phare : la vidéo découverte** (c'est ce que montre le compte Instagram : un clip tourné sur place avec dégustation).
- Les autres services apparaissent ensuite sous la carte, en six mots seulement (« Et aussi » : page dans le guide, portrait, recette de chef, bons plans, jeu-concours, marketplace), pour ne pas surcharger.

### Acte 4 : Contact
- « Poussez la porte. » : la porte du restaurant s'ouvre, la caméra entre, l'écran fond vers la page contact.
- On se retrouve dans la salle du restaurant, en 3D. Quatre objets portent une étiquette cliquable, comme dans un jeu vidéo : le téléphone du comptoir (« Appeler »), l'enveloppe sur la table (« Écrire »), le cadre photo (« Instagram ») et le plan au mur (« Nous trouver »).
- Sans 3D, les quatre mêmes liens s'affichent en liste simple.
- Pied de page : liens des 5 villes, partenaires en une ligne, mentions.

### Ce qui disparaît
- « L'Équipe » et « Devenez collaborateur » : hors objectif de la landing page.
- « Partenaires » : réduit à une ligne en pied de page.

## 5. Direction artistique

- Couleurs : rouge de la marque `#ae3037`, crème `#f6efe4`, encre `#1d1a1a`, touches soleil `#f2b84b` et mer `#63b3bf`.
- Typographie : Fraunces (titres, esprit carte de restaurant) et DM Sans (texte), hébergées avec le site.
- 3D : style maquette low-poly en aplats de couleur, sans texture.

## 6. Choix techniques et performance

- **Vite + Three.js**, sans framework ni jQuery. Le texte s'affiche tout de suite ; la 3D est chargée après, dans un fichier séparé.
- **Défilement natif** : les sections utilisent `position: sticky`, aucune bibliothèque ne détourne le scroll. C'est ce qui garantit la fluidité sur mobile.
- Modèles 3D réalisés dans Blender par script (`assets-src/blender/`), exportés en GLB sans texture.
- Rendu allégé : matériaux simples, pas d'ombres calculées, pas d'effets plein écran ; la résolution de rendu baisse d'elle-même si l'appareil ne suit pas ; le rendu s'arrête quand la scène est masquée.
- **Repli sans 3D** : si WebGL est absent ou si l'utilisateur a demandé moins d'animations, la page s'affiche en version statique avec le même contenu.
- Accessibilité et référencement : tout le contenu et tous les liens sont dans le HTML, navigables au clavier.

## 7. Points à valider avec Resto Avenue

- Téléphone : le site actuel affiche le 06 21 56 61 10 mais son lien compose le 04 67 64 42 42. La landing utilise le 06.
- Textes des services et accroches des villes : rédigés à partir du site et d'Instagram, à faire relire.
- Mesure d'audience : Google Analytics n'a pas été repris (il demande un bandeau de consentement).
- Mentions légales : page à relier dans le pied de page.
