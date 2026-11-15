// Captures d'écran de contrôle : node scripts/shots.mjs [url] [dossier] [vues] [étapes]
// Exemple : node scripts/shots.mjs http://localhost:5173 /tmp/shots mobile,desktop hero:0,trip:0.5
import { mkdirSync } from 'node:fs';
import puppeteer from 'puppeteer-core';

const [url = 'http://localhost:5173', out = 'shots', viewsArg, stepsArg] = process.argv.slice(2);

const VIEWS = {
  mobile: { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  tablet: { width: 820, height: 1180, deviceScaleFactor: 1.5, isMobile: true, hasTouch: true },
  desktop: { width: 1440, height: 900, deviceScaleFactor: 1 },
  small: { width: 360, height: 640, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  landscape: { width: 844, height: 390, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
};
const STEPS = [
  'hero:0', 'hero:0.6', 'trip:0', 'trip:0.125', 'trip:0.25', 'trip:0.5', 'trip:0.75', 'trip:0.88', 'trip:1',
  'curtain:0.5', 'pro:0.05', 'pro:0.3', 'pro:0.5', 'pro:0.75', 'pro:0.9', 'pro:0.96', 'contact:0.6', 'contact:1',
];
const SELECTORS = { hero: '.hero', trip: '.trip', curtain: '.curtain', pro: '.pro', contact: '.contact__stage' };

const views = viewsArg ? viewsArg.split(',') : Object.keys(VIEWS).slice(0, 3);
const steps = stepsArg ? stepsArg.split(',') : STEPS;
mkdirSync(out, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: process.env.CHROME || '/usr/bin/google-chrome',
  headless: true,
  args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars'],
});

for (const name of views) {
  const page = await browser.newPage();
  await page.setViewport(VIEWS[name]);
  page.on('console', (message) => {
    if (['error', 'warn'].includes(message.type())) console.log(`[${name}] ${message.type()}: ${message.text()}`);
  });
  page.on('pageerror', (error) => console.log(`[${name}] pageerror: ${error.message}`));
  await page.goto(url, { waitUntil: 'networkidle0' });
  await new Promise((resolve) => setTimeout(resolve, 2500));
  for (const step of steps) {
    const [section, amount] = step.split(':');
    await page.evaluate(
      (selector, p) => {
        const element = document.querySelector(selector);
        const top = element.getBoundingClientRect().top + window.scrollY;
        const span = Math.max(0, element.offsetHeight - window.innerHeight);
        window.scrollTo({ top: top + span * p, behavior: 'instant' });
      },
      SELECTORS[section],
      Number(amount),
    );
    await new Promise((resolve) => setTimeout(resolve, 1600));
    await page.screenshot({ path: `${out}/${name}-${step.replace(':', '-')}.png` });
  }
  await page.close();
}
await browser.close();
