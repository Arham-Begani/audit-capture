/* Finite visual transitions. Data changes immediately; no fabricated counters or timing. */
'use strict';
(() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const toggle = document.getElementById('motion-toggle');
  const previewButton = document.getElementById('animate-preview');
  const active = new Set();
  let preference = 'on';
  try { preference = localStorage.getItem('audit-capture-motion') || 'on'; } catch (_) { /* Storage is optional. */ }
  const enabled = () => !reduce.matches && preference !== 'off';
  const visible = el => {
    const box = el.getBoundingClientRect();
    return box.bottom > 0 && box.top < innerHeight && box.width > 0;
  };
  function animate(el, frames, options) {
    if (!el || !enabled() || !visible(el)) return null;
    for (const previous of active) if (previous.effect?.target === el) previous.cancel();
    const animation = el.animate(frames, {duration:500,easing:'cubic-bezier(.2,.75,.2,1)',...options});
    active.add(animation);
    animation.finished.catch(() => {}).finally(() => active.delete(animation));
    return animation;
  }
  function cancel() {
    for (const animation of active) animation.cancel();
    active.clear();
    document.querySelectorAll('.review-sweep').forEach(el => el.remove());
  }
  function update() {
    const on = enabled();
    document.documentElement.dataset.motion = on ? 'on' : 'off';
    toggle.setAttribute('aria-pressed', String(on));
    toggle.textContent = reduce.matches ? 'Reduced motion' : on ? 'Motion on' : 'Motion off';
    toggle.disabled = reduce.matches;
    toggle.title = reduce.matches ? 'Your system reduced-motion preference is respected.' : 'Turn visual effects on or off.';
    previewButton.disabled = !on;
    if (!on) cancel();
  }
  function preview() {
    if (!enabled()) return;
    const queue = document.getElementById('attention-preview');
    if (!visible(queue)) return;
    queue.querySelectorAll('.review-sweep').forEach(el => el.remove());
    const rows = queue.querySelectorAll('.preview-row');
    rows.forEach((row,index) => {
      animate(row.querySelector('.preview-track i'), [{transform:'scaleX(.05)'},{transform:'scaleX(1)'}], {duration:650,delay:index*55});
      if (row.classList.contains('is-reviewed')) animate(row.querySelector('.preview-review'), [{transform:'translateY(4px)'},{transform:'translateY(0)'}], {duration:450,delay:180+index*80});
    });
    const sweep = document.createElement('span');
    sweep.className = 'review-sweep';
    sweep.setAttribute('aria-hidden','true');
    queue.append(sweep);
    const animation = animate(sweep,[{transform:'translateY(0)',opacity:0},{opacity:1,offset:.15},{transform:`translateY(${queue.clientHeight-2}px)`,opacity:0}],{duration:1050,easing:'ease-in-out'});
    if (animation) animation.finished.catch(() => {}).finally(() => sweep.remove());
    else sweep.remove();
  }
  function replay() {
    if (!enabled()) return;
    preview();
    document.querySelectorAll('#queue .event').forEach((row,index) => animate(row,[{transform:'translateY(9px)'},{transform:'translateY(0)'}],{duration:400,delay:index*40}));
    document.querySelectorAll('.metrics strong').forEach(el => animate(el,[{transform:'translateY(6px)'},{transform:'translateY(0)'}],{duration:450}));
    animate(document.getElementById('outcome-explanation'),[{transform:'translateX(-5px)'},{transform:'translateX(0)'}],{duration:450,delay:100});
  }
  function study() {
    document.querySelectorAll('.interval-band').forEach((el,index) => animate(el,[{transform:'scaleX(0)',transformOrigin:'left'},{transform:'scaleX(1)',transformOrigin:'left'}],{duration:450,delay:index*40}));
  }
  toggle.addEventListener('click',() => {
    preference = enabled() ? 'off' : 'on';
    try { localStorage.setItem('audit-capture-motion',preference); } catch (_) { /* No persistence needed to operate. */ }
    update();
  });
  previewButton.addEventListener('click',preview);
  reduce.addEventListener('change',update);
  update();
  // Content is never hidden while waiting for JS, fonts, or the observer.
  document.fonts.ready.then(() => {
    document.querySelectorAll('.intro-copy > *').forEach((el,index) => animate(el,[{transform:'translateY(16px)'},{transform:'translateY(0)'}],{duration:650,delay:index*55}));
    animate(document.querySelector('.attention-window'),[{translate:'0 16px'},{translate:'0 0'}],{duration:700,delay:150});
  });
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) if (entry.isIntersecting) {
      animate(entry.target,[{transform:'translateY(16px)'},{transform:'translateY(0)'}],{duration:550});
      observer.unobserve(entry.target);
    }
  },{threshold:.15});
  document.querySelectorAll('.section-heading,.limits,.contrast-heading').forEach(el => observer.observe(el));
  window.AuditMotion = Object.freeze({replay,study});
})();
