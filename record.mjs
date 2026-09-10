// record.mjs — écrans et mini-vidéos des outils, pilotés par CDP (Chrome sans interface).
//
//   node record.mjs <scénario> [<scénario> …]     (voir scenarios.mjs)
//
// Pour chaque scénario : on démarre le serveur qu'il demande, on ouvre Chrome,
// on rejoue les étapes (naviguer, cliquer, écrire, défiler, capturer) pendant
// que le screencast tourne, puis on assemble la vidéo à 12 i/s avec ffmpeg.
// Aucune dépendance : fetch, WebSocket et child_process de node suffisent.
//
// Un curseur dessiné est injecté dans la page et se déplace avant chaque clic :
// sans lui, une vidéo d'interface ne se lit pas.
import { spawn, execFileSync } from 'node:child_process';
import { writeFileSync, mkdirSync, rmSync, existsSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import SCENARIOS from './scenarios.mjs';

const ICI = dirname(fileURLToPath(import.meta.url));
const SHOTS = join(ICI, 'shots');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const FPS = 12;
const LARGEUR_VIDEO = 960;
const LARGEUR_IMAGE = 1200;
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---------------------------------------------------------------- injection
// Curseur + défilement piloté + masquage des marques (nœuds de texte seulement).
// `flou` : des mots à rendre illisibles — chaque occurrence est remplacée par des
// lettres quelconques de même longueur, puis floutée (le flou ne cache rien si le
// vrai mot reste dessous). `flouSel` : des éléments entiers à flouter (photos,
// logos, vignettes).
function injection(mask, hide, pre, flou, flouSel, exact) {
  return `
(() => {
  if (window.__acmeInjected) return; window.__acmeInjected = true;
  try { ${pre || ''} } catch (e) {}
  const T = ${JSON.stringify(mask || {})}, H = ${JSON.stringify(hide || [])};
  const F = ${JSON.stringify(flou || [])}, FS = ${JSON.stringify(flouSel || [])};
  // « exact » : remplacements réservés à un texte entier (libellé court, valeur de champ), jamais en sous-chaîne
  const X = ${JSON.stringify(exact || {})}, aX = k => Object.prototype.hasOwnProperty.call(X, k);
  const cles = Object.keys(T).sort((a, b) => b.length - a.length);
  const echap = s => s.replace(/[.*+?^\${}()|[\\]\\\\]/g, '\\\\$&');
  const SVG = 'http://www.w3.org/2000/svg';
  const brouiller = t => t.replace(/[A-Za-zÀ-ÿ]/g, c => (c === c.toUpperCase() ? 'M' : 'n')).replace(/[0-9]/g, '8');
  // les formes déjà brouillées sont floutées aussi : une page qui recopie un texte
  // traité (textContent d'une carte vers une modale) ne garde que les lettres, pas le flou
  const FF = F.concat(F.map(brouiller).filter(x => x.length > 3));
  const rxF = FF.length ? new RegExp('(' + [...new Set(FF)].sort((a, b) => b.length - a.length).map(echap).join('|') + ')', 'g') : null;
  function styleFlou() {
    if (document.getElementById('__flou-css') || !document.head) return;
    const s = document.createElement('style'); s.id = '__flou-css';
    s.textContent = '.__flou{filter:blur(.3em);-webkit-filter:blur(.3em);display:inline-block;user-select:none}' +
      '.__flou-svg{filter:blur(3.5px)}' + (FS.length ? FS.join(',') + '{filter:blur(18px) saturate(.3) !important}' : '');
    document.head.appendChild(s);
  }
  function flouter() {
    if (!document.body) return;
    styleFlou();
    if (!rxF) return;
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); const lot = []; let n;
    while ((n = w.nextNode())) {
      const p = n.parentNode; if (!p) continue;
      if (p.id === '__cur' || /^(SCRIPT|STYLE|TEXTAREA)$/.test(p.nodeName) || (p.classList && p.classList.contains('__flou'))) continue;
      rxF.lastIndex = 0; if (rxF.test(n.nodeValue)) lot.push(n);
    }
    lot.forEach(n => {
      const p = n.parentNode;
      if (p.namespaceURI === SVG) {
        // une seule fois par nœud : réécrire une valeur identique relance l'observateur, sans fin
        if (p.classList.contains('__flou-svg')) return;
        rxF.lastIndex = 0; const v = n.nodeValue.replace(rxF, m => brouiller(m));
        if (v !== n.nodeValue) n.nodeValue = v;
        p.classList.add('__flou-svg'); return;
      }
      const frag = document.createDocumentFragment();
      n.nodeValue.split(rxF).forEach((morceau, i) => {
        if (i % 2) { const s = document.createElement('span'); s.className = '__flou'; s.textContent = brouiller(morceau); frag.appendChild(s); }
        else if (morceau) frag.appendChild(document.createTextNode(morceau));
      });
      p.replaceChild(frag, n);
    });
    document.querySelectorAll('[alt],[title],[aria-label]').forEach(e => ['alt', 'title', 'aria-label'].forEach(a => {
      const x = e.getAttribute(a); if (!x) return; rxF.lastIndex = 0; if (rxF.test(x)) { rxF.lastIndex = 0; e.setAttribute(a, x.replace(rxF, m => brouiller(m))); }
    }));
  }
  function passe() {
    flouter();
    H.forEach(s => { try { document.querySelectorAll(s).forEach(e => e.remove()); } catch (e) {} });
    if (!cles.length || !document.body) return;
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
    while ((n = w.nextNode())) {
      if (n.parentNode && n.parentNode.id === '__cur') continue;
      let v = n.nodeValue, o = v;
      const nu = v.trim(); if (nu && aX(nu)) { n.nodeValue = v.replace(nu, X[nu]); continue; }
      // deux passes : une clé longue (traduction) peut ne correspondre qu'après le masquage des marques
      for (let tour = 0; tour < 2; tour++) cles.forEach(k => { if (v.indexOf(k) >= 0) v = v.split(k).join(T[k]); });
      if (v !== o) n.nodeValue = v;
    }
    // les valeurs des champs de formulaire ne sont pas des nœuds de texte : même traitement
    document.querySelectorAll('input:not([type=password]), textarea').forEach(e => {
      if (e.id === 'write' || !e.value) return;
      let v = e.value; const o = v, nu = v.trim();
      if (aX(nu)) v = X[nu]; else cles.forEach(k => { if (v.indexOf(k) >= 0) v = v.split(k).join(T[k]); });
      if (v !== o) e.value = v;
    });
    document.querySelectorAll('[placeholder],[alt],[title],[aria-label]').forEach(e => {
      ['placeholder', 'alt', 'title', 'aria-label'].forEach(a => {
        let x = e.getAttribute(a); if (!x) return; const o = x;
        cles.forEach(k => { x = x.split(k).join(T[k]); });
        if (x !== o) e.setAttribute(a, x);
      });
    });
  }
  function curseur() {
    if (document.getElementById('__cur') || !document.body) return;
    const c = document.createElement('div'); c.id = '__cur';
    c.innerHTML = '<svg width="26" height="30" viewBox="0 0 26 30"><path d="M3 2 L3 24 L9 18.5 L13 27 L17 25.2 L13 16.8 L21 16.5 Z" fill="#fff" stroke="#111" stroke-width="1.8" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, { position: 'fixed', left: '0px', top: '0px', zIndex: 2147483647, pointerEvents: 'none',
      transform: 'translate(-40px,-40px)', transition: 'transform .55s cubic-bezier(.22,1,.36,1), opacity .3s', opacity: '0',
      filter: 'drop-shadow(0 1px 2px rgba(0,0,0,.35))' });
    document.body.appendChild(c);
  }
  window.__cur = (x, y) => { curseur(); const c = document.getElementById('__cur'); c.style.opacity = '1'; c.style.transform = 'translate(' + (x - 3) + 'px,' + (y - 2) + 'px)'; };
  window.__pulse = () => { const c = document.getElementById('__cur'); if (!c) return; c.style.transition = 'transform .12s'; c.style.transform += ' scale(.82)';
    setTimeout(() => { c.style.transform = c.style.transform.replace(' scale(.82)', ''); setTimeout(() => { c.style.transition = 'transform .55s cubic-bezier(.22,1,.36,1), opacity .3s'; }, 130); }, 120); };
  window.__scrollTo = (y, ms) => new Promise(res => {
    const y0 = window.scrollY, d = y - y0, t0 = performance.now();
    const ease = t => 1 - Math.pow(1 - t, 3);
    (function step(now) { const t = Math.min(1, (now - t0) / ms); window.scrollTo(0, y0 + d * ease(t)); if (t < 1) requestAnimationFrame(step); else res(window.scrollY); })(t0);
  });
  // Ce script tourne avant que le document n'ait de racine : l'observateur ne
  // peut s'accrocher qu'une fois le DOM construit, sinon il jette et rien ne
  // suit (le contenu chargé ensuite par l'application restait non masqué).
  function armer() {
    passe(); curseur();
    // passe différée : appelée en microtâche à chaque mutation, elle affamait la
    // boucle d'événements d'une page qui se redessine (la page profil) — plus
    // rien ne répondait, pas même le pilotage.
    let attente = 0;
    try { new MutationObserver(() => { if (!attente) attente = setTimeout(() => { attente = 0; passe(); }, 40); })
      .observe(document.documentElement, { childList: true, subtree: true, characterData: true }); } catch (e) {}
    setInterval(passe, 400);
  }
  if (document.readyState !== 'loading') armer(); else document.addEventListener('DOMContentLoaded', armer);
})();`;
}

// ---------------------------------------------------------------- serveurs
function demarrerServeur(s, port) {
  if (!s || s.type === 'none') return null;
  if (s.type === 'static') {
    return spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1', '--directory', s.dir], { stdio: 'ignore' });
  }
  if (s.type === 'node') {
    return spawn('node', [s.script, ...(s.args || [])], { cwd: s.cwd, env: { ...process.env, ...(s.env || {}), PORT: String(port) }, stdio: s.log ? 'inherit' : 'ignore' });
  }
  throw new Error('serveur inconnu : ' + s.type);
}
async function attendrePort(port, ms = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    try { await fetch(`http://127.0.0.1:${port}/`, { method: 'HEAD' }); return; } catch (e) { await sleep(250); }
  }
  throw new Error('serveur injoignable sur ' + port);
}

// ---------------------------------------------------------------- CDP
class Page {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.handlers = new Map();
    ws.onmessage = m => { const d = JSON.parse(m.data);
      if (d.id && this.pending.has(d.id)) { const p = this.pending.get(d.id); this.pending.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); }
      else if (d.method && this.handlers.has(d.method)) this.handlers.get(d.method).forEach(h => h(d.params)); };
  }
  send(method, params = {}) { return new Promise((res, rej) => { const i = ++this.id; this.pending.set(i, { res, rej }); this.ws.send(JSON.stringify({ id: i, method, params })); }); }
  on(method, h) { if (!this.handlers.has(method)) this.handlers.set(method, []); this.handlers.get(method).push(h); }
  off(method, h) { const l = this.handlers.get(method) || []; const i = l.indexOf(h); if (i >= 0) l.splice(i, 1); }
  async eval(expr, awaitPromise = false) {
    const r = await this.send('Runtime.evaluate', { expression: expr, awaitPromise, returnByValue: true });
    if (r.exceptionDetails) throw new Error('JS : ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  }
}

async function ouvrirChrome(port, w, h) {
  const profil = join(tmpdir(), 'acme-rec-' + process.pid + '-' + port);
  const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--window-size=${w},${h}`,
    '--autoplay-policy=no-user-gesture-required', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
    '--disable-dev-shm-usage', '--lang=fr-FR', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
    '--mute-audio', `--user-data-dir=${profil}`, 'about:blank'], { stdio: 'ignore' });
  let url;
  for (let i = 0; i < 60; i++) {
    try { const l = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); const p = l.find(t => t.type === 'page'); if (p) { url = p.webSocketDebuggerUrl; break; } } catch (e) {}
    await sleep(250);
  }
  if (!url) { chrome.kill(); throw new Error('Chrome injoignable'); }
  const ws = new WebSocket(url); await new Promise(r => ws.onopen = r);
  return { chrome, page: new Page(ws), profil };
}

// ---------------------------------------------------------------- assemblage
function assembler(frames, t0, t1, sortie) {
  if (!frames.length) { console.log('   ⚠ aucune image de screencast'); return; }
  // Les premières images arrivent avant que la page ne se peigne : de l'écran noir,
  // qui ouvrait chaque vidéo sur plusieurs secondes vides. Une image d'interface
  // pèse bien plus lourd qu'un aplat : on saute celles qui sont trop légères.
  let debut = 0;
  while (debut < frames.length - 1 && statSync(frames[debut].file).size < 20000) debut++;
  if (debut) { frames.splice(0, debut); t0 = Math.max(t0, frames[0].t); }
  const ticks = Math.max(1, Math.round((t1 - t0) * FPS));
  let j = 0; const lignes = [];
  for (let k = 0; k < ticks; k++) {
    const t = t0 + k / FPS;
    while (j + 1 < frames.length && frames[j + 1].t <= t) j++;
    lignes.push(`file '${frames[j].file}'`);
  }
  lignes.push(`file '${frames[frames.length - 1].file}'`);
  const liste = join(dirname(frames[0].file), 'liste.txt');
  writeFileSync(liste, lignes.join('\n') + '\n');
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-r', String(FPS), '-f', 'concat', '-safe', '0', '-i', liste,
    '-vf', `scale=${LARGEUR_VIDEO}:-2:flags=lanczos`, '-c:v', 'libx264', '-preset', 'slow', '-crf', '27',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', sortie]);
}

// ---------------------------------------------------------------- scénario
async function jouer(nom) {
  const sc = SCENARIOS[nom];
  if (!sc) throw new Error('scénario inconnu : ' + nom);
  const w = sc.width || 1400, h = sc.height || 900;
  const port = sc.port || 4360, cdpPort = 9400 + (port % 100);
  const base = sc.serve?.type === 'none' ? sc.serve.base : `http://127.0.0.1:${port}/`;
  console.log(`▶ ${nom}  (${w}×${h}, ${base})`);
  const serveur = demarrerServeur(sc.serve, port);
  if (serveur) await attendrePort(port);
  const { chrome, page, profil } = await ouvrirChrome(cdpPort, w, h);
  const tmp = join(tmpdir(), 'acme-frames-' + nom + '-' + process.pid); mkdirSync(tmp, { recursive: true });
  const frames = []; let rec = false, tDebut = 0, tFin = 0; const textes = new Set();
  const tmpPng = join(tmp, 'shot.png');
  mkdirSync(SHOTS, { recursive: true });
  try {
    await page.send('Page.enable'); await page.send('Runtime.enable');
    await page.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
    await page.send('Page.addScriptToEvaluateOnNewDocument', { source: injection(sc.mask, sc.hide, sc.pre, sc.flou, sc.flouSel, sc.maskExact) });
    page.on('Page.screencastFrame', p => {
      const f = join(tmp, String(frames.length).padStart(5, '0') + '.jpg');
      writeFileSync(f, Buffer.from(p.data, 'base64'));
      frames.push({ t: p.metadata.timestamp, file: f });
      page.send('Page.screencastFrameAck', { sessionId: p.sessionId }).catch(() => {});
    });
    const startRec = async () => { if (rec) return; rec = true; tDebut = 0;
      await page.send('Page.startScreencast', { format: 'jpeg', quality: 82, maxWidth: w, maxHeight: h, everyNthFrame: 1 }); };
    const stopRec = async () => { if (!rec) return; rec = false; await page.send('Page.stopScreencast'); };
    const now = async () => page.eval('performance.timeOrigin/1000 + performance.now()/1000');

    let etapes = 0;
    for (const st of sc.steps) {
      etapes++;
      if (st.go !== undefined) {
        if (sc.video && !rec) { await startRec(); }
        const url = /^https?:/.test(st.go) ? st.go : base + st.go.replace(/^\//, '');
        const charge = new Promise(res => { const h = () => { page.off('Page.loadEventFired', h); res(); }; page.on('Page.loadEventFired', h); setTimeout(res, 15000); });
        await page.send('Page.navigate', { url }); await charge;
        if (!tDebut) tDebut = await now();
        await sleep(st.ms ?? 1500);
        // Le premier écran mérite une vraie pose, et la touche « Échap » ferme un éventuel bandeau.
        await page.eval('window.__cur && window.__cur(' + Math.round(w * .55) + ',' + Math.round(h * .6) + ')');
      } else if (st.wait !== undefined) {
        await sleep(st.wait);
      } else if (st.js !== undefined) {
        try { const v = await page.eval(st.js, !!st.await); if (st.log) console.log('   ·', String(v).slice(0, 300)); }
        catch (e) { console.log('   ⚠ js :', e.message.slice(0, 120)); }
        await sleep(st.ms ?? 300);
      } else if (st.scroll !== undefined) {
        const cible = typeof st.scroll === 'number' ? String(st.scroll)
          : st.scroll === 'end' ? 'document.documentElement.scrollHeight - innerHeight'
          : `(function(){const e=document.querySelectorAll(${JSON.stringify(st.scroll)})[${st.nth ?? 0}];return e?e.getBoundingClientRect().top+scrollY-${st.marge ?? 24}:scrollY;})()`;
        await page.eval(`window.__scrollTo(Math.max(0, ${cible}), ${st.ms ?? 1200})`, true);
        await sleep(st.pause ?? 700);
      } else if (st.click !== undefined || st.hover !== undefined) {
        const sel = st.click ?? st.hover;
        const rect = await page.eval(`(function(){const l=document.querySelectorAll(${JSON.stringify(sel)});const e=l[${st.nth ?? 0}];if(!e)return null;e.scrollIntoView({block:'center',inline:'nearest'});const r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2,w:r.width,h:r.height};})()`);
        if (!rect) { console.log(`   ⚠ introuvable : ${sel}`); continue; }
        await sleep(350);
        const r2 = await page.eval(`(function(){const e=document.querySelectorAll(${JSON.stringify(sel)})[${st.nth ?? 0}];const r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};})()`);
        const x = Math.round(r2.x), y = Math.round(r2.y);
        await page.eval(`window.__cur(${x},${y})`); await sleep(st.hover !== undefined ? (st.ms ?? 900) : 620);
        await page.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
        if (st.click !== undefined) {
          await page.eval('window.__pulse()');
          await page.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
          await page.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
          await sleep(st.ms ?? 900);
        }
      } else if (st.type !== undefined) {
        if (st.sel) {
          const ok = await page.eval(`(function(){const e=document.querySelector(${JSON.stringify(st.sel)});if(!e)return false;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();window.__cur(r.left+Math.min(r.width-12,60),r.top+r.height/2);e.focus();return true;})()`);
          if (!ok) { console.log(`   ⚠ introuvable : ${st.sel}`); continue; }
          await sleep(500);
        }
        for (const ch of st.type) { await page.send('Input.insertText', { text: ch }); await sleep(st.vitesse ?? 45); }
        await sleep(st.ms ?? 500);
      } else if (st.key !== undefined) {
        const codes = { Enter: 13, Escape: 27, Tab: 9, ArrowDown: 40, ArrowRight: 39 };
        const k = st.key;
        await page.send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code: k, windowsVirtualKeyCode: codes[k] || 0, text: k === 'Enter' ? '\r' : undefined });
        await page.send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code: k, windowsVirtualKeyCode: codes[k] || 0 });
        await sleep(st.ms ?? 700);
      } else if (st.shot !== undefined) {
        await page.eval('(function(){const c=document.getElementById("__cur");if(c)c.style.opacity="0";})()');
        await sleep(120);
        // `clip` : une zone de l'écran, prise à 2× — un composant d'interface
        // se lit ; un plein écran réduit dans une carte, non. Soit un rectangle
        // [x, y, l, h] en pixels CSS de la fenêtre, soit un sélecteur (+ marge).
        // `ratio` : la zone est agrandie autour de son centre jusqu'au format voulu
        // (1.5 = 3:2), en gardant du contexte plutôt qu'en ajoutant des bandes.
        // `hd` (scénario) : sans zone, la fenêtre entière est prise à 2×.
        const params = { format: 'png' };
        if (st.clip) {
          let r;
          if (Array.isArray(st.clip)) r = { x: st.clip[0], y: st.clip[1], w: st.clip[2], h: st.clip[3] };
          else r = await page.eval(`(function(){const e=document.querySelectorAll(${JSON.stringify(st.clip)})[${st.nth ?? 0}];if(!e)return null;const b=e.getBoundingClientRect();const p=${st.pad ?? 0};return {x:b.left-p,y:b.top-p,w:b.width+2*p,h:b.height+2*p};})()`);
          if (!r) { console.log(`   ⚠ zone introuvable : ${st.clip}`); continue; }
          const R = st.ratio ?? sc.ratio;
          if (R) {
            if (r.w / r.h > R) { const nh = r.w / R; r.y -= (nh - r.h) / 2; r.h = nh; } else { const nw = r.h * R; r.x -= (nw - r.w) / 2; r.w = nw; }
            if (r.w > w) { r.w = w; r.h = w / R; }
            if (r.h > h) { r.h = h; r.w = h * R; }
            r.x = Math.min(Math.max(0, r.x), w - r.w); r.y = Math.min(Math.max(0, r.y), h - r.h);
          }
          const sx = await page.eval('scrollX'), sy = await page.eval('scrollY');
          params.clip = { x: Math.max(0, r.x) + sx, y: Math.max(0, r.y) + sy, width: Math.min(r.w, w - Math.max(0, r.x)), height: Math.min(r.h, h - Math.max(0, r.y)), scale: 2 };
          params.captureBeyondViewport = true;
        } else if (sc.hd) {
          const sx = await page.eval('scrollX'), sy = await page.eval('scrollY');
          params.clip = { x: sx, y: sy, width: w, height: h, scale: 2 };
        }
        const s = await page.send('Page.captureScreenshot', params);
        writeFileSync(tmpPng, Buffer.from(s.data, 'base64'));
        const cible = join(SHOTS, st.shot + '.jpg');
        mkdirSync(dirname(cible), { recursive: true });
        const largeur = params.clip ? Math.min(1800, Math.round(params.clip.width * 2)) : LARGEUR_IMAGE;
        execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', tmpPng, '-vf', `scale=${largeur}:-2:flags=lanczos`, '-q:v', '3', cible]);
        console.log(`   ✓ ${st.shot}.jpg${st.clip ? ' (zone 2×)' : sc.hd ? ' (fenêtre 2×)' : ''}`);
        await page.eval('(function(){const c=document.getElementById("__cur");if(c)c.style.opacity="1";})()');
      } else if (st.collect !== undefined) {
        // relevé des textes visibles (pour préparer une traduction de l'interface)
        const t = await page.eval(`(function(){const o=[];const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;while((n=w.nextNode())){const p=n.parentNode;if(!p||/^(SCRIPT|STYLE|TEXTAREA)$/.test(p.nodeName)||p.id==='__cur')continue;const v=n.nodeValue.trim();if(v&&/[A-Za-zÀ-ÿ]/.test(v))o.push(v);}document.querySelectorAll('[placeholder],[title],[aria-label]').forEach(e=>['placeholder','title','aria-label'].forEach(a=>{const v=(e.getAttribute(a)||'').trim();if(v&&/[A-Za-zÀ-ÿ]/.test(v))o.push(v)}));return o;})()`);
        (t || []).forEach(x => textes.add(x));
      } else if (st.rec !== undefined) {
        if (st.rec) await startRec(); else { tFin = await now(); await stopRec(); }
      }
    }
    if (rec) { tFin = await now(); await stopRec(); }
    if (textes.size) {
      const f = join(SHOTS, '_ctl', nom + '-textes.json'); mkdirSync(dirname(f), { recursive: true });
      writeFileSync(f, JSON.stringify([...textes], null, 1)); console.log(`   ✓ ${textes.size} textes relevés → shots/_ctl/${nom}-textes.json`);
    }
    if (sc.video && frames.length) {
      const sortie = join(SHOTS, sc.video + '.mp4'); mkdirSync(dirname(sortie), { recursive: true });
      const t0 = tDebut || frames[0].t, t1 = tFin || frames[frames.length - 1].t + 1 / FPS;
      assembler(frames, Math.min(t0, frames[0].t), Math.max(t1, frames[frames.length - 1].t), sortie);
      const ko = Math.round(execFileSync('stat', ['-f', '%z', sortie]).toString() / 1024);
      console.log(`   ✓ ${sc.video}.mp4  ${frames.length} images → ${((t1 - t0)).toFixed(1)} s, ${ko} Ko`);
    }
  } finally {
    try { page.ws.close(); } catch (e) {}
    try { chrome.kill('SIGKILL'); } catch (e) {}
    if (serveur) { try { serveur.kill(); } catch (e) {} }
    await sleep(800);
    // Chrome écrit encore dans son profil quelques centaines de ms après sa mort.
    for (const d of [profil, tmp]) {
      try { rmSync(d, { recursive: true, force: true, maxRetries: 8, retryDelay: 300 }); } catch (e) {}
    }
  }
}

const voulus = process.argv.slice(2);
if (!voulus.length) { console.log('scénarios : ' + Object.keys(SCENARIOS).join(', ')); process.exit(1); }
for (const n of voulus) {
  try { await jouer(n); } catch (e) { console.log(`   ✗ ${n} : ${e.message}`); process.exitCode = 1; }
}
