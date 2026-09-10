/* Sliders d'écrans + visionneuse. Sans dépendance.
   Un slider = une piste de figures ; les vidéos ne jouent que sur la vue
   active et seulement quand le slider est à l'écran. Un clic ouvre la vue en
   grand dans la visionneuse. Flèches du clavier et balayage tactile compris.
   Les libellés suivent la langue de la page (<html lang>). */
(function () {
  'use strict';
  var reduit = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var EN = (document.documentElement.lang || 'fr').slice(0, 2) === 'en';
  var L = EN ? { fermer: 'Close ×', prec: 'Previous', suiv: 'Next', ecran: 'Screen ' }
             : { fermer: 'Fermer ×', prec: 'Précédent', suiv: 'Suivant', ecran: 'Écran ' };

  // ---- visionneuse -------------------------------------------------------
  var vis = document.createElement('div');
  vis.className = 'vis'; vis.hidden = true;
  vis.innerHTML = '<button class="vis-close" aria-label="' + L.fermer + '">' + L.fermer + '</button>' +
    '<button class="vis-nav vis-prev" aria-label="' + L.prec + '">←</button>' +
    '<figure class="vis-fig"></figure>' +
    '<button class="vis-nav vis-next" aria-label="' + L.suiv + '">→</button>' +
    '<div class="vis-cap mono"></div>';
  document.body.appendChild(vis);
  var visFig = vis.querySelector('.vis-fig'), visCap = vis.querySelector('.vis-cap');
  var visCourant = null; // {slider, index}

  function montrer(slider, i) {
    var slides = slider.slides; i = (i + slides.length) % slides.length;
    visCourant = { slider: slider, index: i };
    var src = slides[i];
    visFig.innerHTML = '';
    var media = src.querySelector('img, video');
    var clone;
    if (media.tagName === 'VIDEO') {
      clone = document.createElement('video');
      clone.src = media.currentSrc || media.src; clone.muted = true; clone.loop = true; clone.playsInline = true;
      clone.controls = true; clone.autoplay = true;
      if (media.poster) clone.poster = media.poster;
    } else {
      clone = document.createElement('img');
      clone.src = media.currentSrc || media.src; clone.alt = media.alt || '';
    }
    visFig.appendChild(clone);
    var cap = src.querySelector('figcaption');
    visCap.textContent = (i + 1) + ' / ' + slides.length + (cap ? ' — ' + cap.textContent : '');
    vis.hidden = false; document.body.style.overflow = 'hidden';
    vis.querySelector('.vis-close').focus();
  }
  function fermer() {
    vis.hidden = true; document.body.style.overflow = '';
    visFig.innerHTML = '';
    if (visCourant) { visCourant.slider.aller(visCourant.index); visCourant.slider.root.focus(); }
    visCourant = null;
  }
  vis.querySelector('.vis-close').addEventListener('click', fermer);
  vis.querySelector('.vis-prev').addEventListener('click', function () { if (visCourant) montrer(visCourant.slider, visCourant.index - 1); });
  vis.querySelector('.vis-next').addEventListener('click', function () { if (visCourant) montrer(visCourant.slider, visCourant.index + 1); });
  vis.addEventListener('click', function (e) { if (e.target === vis) fermer(); });
  document.addEventListener('keydown', function (e) {
    if (vis.hidden) return;
    if (e.key === 'Escape') fermer();
    if (e.key === 'ArrowLeft' && visCourant) montrer(visCourant.slider, visCourant.index - 1);
    if (e.key === 'ArrowRight' && visCourant) montrer(visCourant.slider, visCourant.index + 1);
  });

  // ---- sliders -----------------------------------------------------------
  var visibles = new WeakMap();
  var io = 'IntersectionObserver' in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      var s = en.target.__slider; if (!s) return;
      visibles.set(en.target, en.isIntersecting);
      s.jouer();
    });
  }, { threshold: 0.35 }) : null;

  document.querySelectorAll('[data-slider]').forEach(function (root) {
    var track = root.querySelector('.slider-track');
    var slides = Array.prototype.slice.call(track.children);
    var count = root.querySelector('.slider-count');
    var dots = root.querySelector('.slider-dots');
    var i = 0;
    var s = { root: root, slides: slides };
    root.__slider = s;

    if (dots) slides.forEach(function (_, k) {
      var b = document.createElement('button'); b.type = 'button';
      b.setAttribute('aria-label', L.ecran + (k + 1));
      b.addEventListener('click', function () { s.aller(k); });
      dots.appendChild(b);
    });

    s.jouer = function () {
      var actif = visibles.get(root) !== false;
      slides.forEach(function (sl, k) {
        var v = sl.querySelector('video'); if (!v) return;
        if (k === i && actif && !reduit) { if (v.preload === 'none') v.preload = 'metadata'; v.play().catch(function () {}); }
        else v.pause();
      });
    };
    s.aller = function (k) {
      i = (k + slides.length) % slides.length;
      track.style.transform = 'translateX(' + (-i * 100) + '%)';
      slides.forEach(function (sl, k2) { sl.setAttribute('aria-hidden', k2 === i ? 'false' : 'true'); });
      if (count) count.textContent = (i + 1) + ' / ' + slides.length;
      if (dots) Array.prototype.forEach.call(dots.children, function (b, k2) { b.classList.toggle('on', k2 === i); });
      s.jouer();
    };

    root.querySelector('.slider-prev').addEventListener('click', function () { s.aller(i - 1); });
    root.querySelector('.slider-next').addEventListener('click', function () { s.aller(i + 1); });
    root.addEventListener('keydown', function (e) {
      if (e.target !== root) return;
      if (e.key === 'ArrowLeft') { s.aller(i - 1); e.preventDefault(); }
      if (e.key === 'ArrowRight') { s.aller(i + 1); e.preventDefault(); }
      if (e.key === 'Enter') montrer(s, i);
    });
    slides.forEach(function (sl, k) {
      sl.addEventListener('click', function () { montrer(s, k); });
    });

    // balayage tactile
    var x0 = null;
    track.addEventListener('pointerdown', function (e) { if (e.pointerType === 'touch') x0 = e.clientX; });
    track.addEventListener('pointerup', function (e) {
      if (x0 === null) return; var dx = e.clientX - x0; x0 = null;
      if (Math.abs(dx) > 40) s.aller(dx < 0 ? i + 1 : i - 1);
    });

    if (io) io.observe(root);
    s.aller(0);
  });
})();
