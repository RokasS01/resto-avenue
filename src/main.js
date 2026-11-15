import '@fontsource-variable/fraunces/wght.css';
import '@fontsource-variable/fraunces/wght-italic.css';
import '@fontsource-variable/dm-sans/wght.css';
import './styles.css';

const LEGS = [
  'Nîmes → Montpellier · ≈ 55 km',
  'Montpellier → Béziers · ≈ 70 km',
  'Béziers → Perpignan · ≈ 95 km',
  'Perpignan → Toulouse · ≈ 205 km',
];
const PHASES = [0.2, 0.4, 0.62, 0.86];

const root = document.documentElement;
const clamp01 = (v) => Math.min(1, Math.max(0, v));

/** Avancement d'une section haute dont le contenu reste collé à l'écran. */
function progressOf(rect, viewport) {
  return clamp01(-rect.top / Math.max(1, rect.height - viewport));
}

/** Démarre l'expérience 3D ; en cas d'échec la page retombe sur sa version statique. */
async function start() {
  const canvas = document.getElementById('scene');
  const hero = document.querySelector('.hero');
  const trip = document.querySelector('.trip');
  const curtain = document.querySelector('.curtain');
  const pro = document.querySelector('.pro');
  const proSticky = document.querySelector('.pro__sticky');
  const contact = document.querySelector('.contact');
  const contactStage = document.querySelector('.contact__stage');
  const contactSticky = document.querySelector('.contact__sticky');
  const spotList = document.querySelector('.spots');
  const spotLinks = [...document.querySelectorAll('.spot')];
  const cards = [...document.querySelectorAll('.city')];
  const stops = [...document.querySelectorAll('.trip__rail button')];
  const leg = document.querySelector('.trip__leg');
  const flash = document.querySelector('.flash');
  const photo = document.querySelector('.shot__photo');

  const { createWorld } = await import('./three/world.js');
  const world = await createWorld(canvas, {
    onSnapshot: (url) => (photo.style.backgroundImage = `url(${url})`),
    onInterior: () => contact.classList.add('is-live'),
  });

  const target = { hero: 0, trip: 0, pro: 0, contact: 0 };
  const state = { hero: 0, trip: 0, pro: 0, contact: 0, stage: 'map' };
  const dom = { city: -2, leg: -2, phase: -1, fade: -1, spots: null };
  const damping = window.matchMedia('(pointer: coarse)').matches ? 14 : 7;
  let covered = false;
  let tripVisible = false;
  let last = performance.now();
  let first = true;

  /** Lit la position des sections et en déduit les avancements bruts. */
  function measure() {
    const viewport = window.innerHeight;
    const tripRect = trip.getBoundingClientRect();
    const curtainRect = curtain.getBoundingClientRect();
    const proRect = pro.getBoundingClientRect();
    target.hero = clamp01(window.scrollY / Math.max(1, hero.offsetHeight));
    target.trip = progressOf(tripRect, viewport);
    target.pro = progressOf(proRect, viewport);
    state.stage = curtainRect.top + curtainRect.height / 2 < viewport / 2 ? 'diorama' : 'map';
    tripVisible = tripRect.top < viewport * 0.5 && tripRect.bottom > viewport * 0.75;
    const stageRect = contactStage.getBoundingClientRect();
    const live = contact.classList.contains('is-live');
    if (live && stageRect.top < viewport) state.stage = 'interior';
    target.contact = clamp01((viewport - stageRect.top) / Math.max(1, stageRect.height));
    covered =
      (curtainRect.top <= 0 && curtainRect.bottom >= viewport) ||
      (live ? stageRect.bottom <= 0 : stageRect.top <= 0) ||
      document.hidden;
  }

  /** Reflète l'état du voyage dans les cartes de ville, le rail et l'étiquette de trajet. */
  function updateTrip() {
    const x = state.trip * (cards.length - 1);
    const nearest = Math.round(x);
    const atStop = Math.abs(x - nearest) < 0.3;
    const city = tripVisible && atStop ? nearest : -1;
    const route = tripVisible && !atStop ? Math.min(Math.floor(x), LEGS.length - 1) : -1;
    if (city !== dom.city) {
      dom.city = city;
      cards.forEach((card, i) => card.classList.toggle('is-active', i === city));
      stops.forEach((stop, i) => {
        stop.classList.toggle('is-active', i === city);
        stop.classList.toggle('is-done', i < x - 0.3);
        if (i === city) stop.setAttribute('aria-current', 'step');
        else stop.removeAttribute('aria-current');
      });
    }
    if (route !== dom.leg) {
      dom.leg = route;
      if (route >= 0) leg.textContent = LEGS[route];
      leg.classList.toggle('is-active', route >= 0);
      stops.forEach((stop, i) => stop.classList.toggle('is-done', i < x - 0.3));
    }
  }

  /** Reflète l'état de la séquence restaurateurs : phase affichée, flash, fondu final. */
  function updatePro(previous) {
    const phase = PHASES.findIndex((limit) => state.pro < limit);
    const current = phase === -1 ? PHASES.length : phase;
    if (current !== dom.phase) {
      dom.phase = current;
      proSticky.dataset.phase = current;
    }
    if (previous < PHASES[1] && state.pro >= PHASES[1] && state.stage === 'diorama') {
      world.fire();
      flash.classList.remove('is-firing');
      void flash.offsetWidth;
      flash.classList.add('is-firing');
    }
    const fade = state.stage === 'interior' ? 1 : Math.round(clamp01((state.pro - 0.93) / 0.06) * 100) / 100;
    if (fade !== dom.fade) {
      dom.fade = fade;
      proSticky.style.setProperty('--fade', fade);
    }
  }

  /** Colle les boutons de contact sur leurs objets 3D dans la salle du restaurant. */
  function updateSpots() {
    const on = state.stage === 'interior' && state.contact > 0.58;
    if (on !== dom.spots) {
      dom.spots = on;
      spotList.classList.toggle('is-on', on);
    }
    if (state.stage !== 'interior') return;
    const origin = contactSticky.getBoundingClientRect();
    spotLinks.forEach((link) => {
      const spot = world.spots.find((item) => item.name === link.dataset.spot);
      link.parentElement.style.transform = `translate3d(${spot.x - origin.left}px, ${spot.y - origin.top}px, 0)`;
    });
  }

  /** Boucle d'animation : lisse le défilement puis met à jour la page et la scène. */
  function frame(now) {
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    measure();
    const k = first ? 1 : 1 - Math.exp(-dt * damping);
    const previousPro = state.pro;
    state.hero += (target.hero - state.hero) * k;
    state.trip += (target.trip - state.trip) * k;
    state.pro += (target.pro - state.pro) * k;
    updateTrip();
    updatePro(previousPro);
    state.contact += (target.contact - state.contact) * k;
    if (!covered || first) world.update(state, now / 1000, dt);
    updateSpots();
    if (first) {
      first = false;
      canvas.classList.add('is-ready');
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  stops.forEach((stop, i) => {
    stop.addEventListener('click', () => {
      const top = trip.getBoundingClientRect().top + window.scrollY;
      const span = trip.offsetHeight - window.innerHeight;
      window.scrollTo({ top: top + (i / (stops.length - 1)) * span + 2, behavior: 'smooth' });
    });
  });

  spotLinks.forEach((link) => {
    link.addEventListener('pointerenter', () => world.focus(link.dataset.spot));
    link.addEventListener('pointerleave', () => world.focus(null));
    link.addEventListener('focus', () => world.focus(link.dataset.spot));
    link.addEventListener('blur', () => world.focus(null));
  });

  if (import.meta.env.DEV) window.__world = { world, state, target };
}

/** Affiche le détail d'un service au survol, au focus ou au toucher de son étiquette. */
function setupExtras() {
  const detail = document.querySelector('.extras__detail');
  const extras = [...document.querySelectorAll('.extra')];
  const select = (extra) => {
    if (extra.classList.contains('is-active')) return;
    extras.forEach((item) => {
      item.classList.toggle('is-active', item === extra);
      item.setAttribute('aria-pressed', item === extra);
    });
    detail.textContent = extra.dataset.info;
    detail.classList.remove('is-changing');
    void detail.offsetWidth;
    detail.classList.add('is-changing');
  };
  extras.forEach((extra) => {
    extra.addEventListener('pointerenter', () => select(extra));
    extra.addEventListener('focus', () => select(extra));
    extra.addEventListener('click', () => select(extra));
  });
}
setupExtras();

if (root.classList.contains('has-3d')) {
  start().catch((error) => {
    console.warn('[resto-avenue] 3D indisponible, affichage statique', error);
    root.classList.remove('has-3d');
  });
}
