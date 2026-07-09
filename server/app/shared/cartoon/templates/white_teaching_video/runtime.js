/* === White Teaching Video Runtime === */
/* Provides Runtime.reveal, fadeIn, spawn, move, moveTo, compare,
   highlight, pulse, connect, setText, updateList, updateTable,
   zoom, caption — all deterministic GSAP wrappers. */

window.Runtime = {
  /* --- Appear / Disappear --- */

  reveal(tl, selector, time, duration) {
    tl.fromTo(selector,
      { autoAlpha: 0, y: 24, scale: 0.96 },
      { autoAlpha: 1, y: 0, scale: 1, duration: duration, ease: 'power2.out', immediateRender: false },
      time
    );
  },

  fadeIn(tl, selector, time, duration) {
    tl.fromTo(selector,
      { autoAlpha: 0 },
      { autoAlpha: 1, duration: duration, ease: 'power1.inOut', immediateRender: false },
      time
    );
  },

  /* --- Motion --- */

  spawn(tl, selector, fromSelector, time, duration) {
    tl.call(function() {
      var target = document.querySelector(selector);
      var source = fromSelector ? document.querySelector(fromSelector) : null;
      if (target && source) {
        var rect = source.getBoundingClientRect();
        var parent = target.offsetParent || document.body;
        var parentRect = parent.getBoundingClientRect();
        gsap.set(target, {
          left: rect.left - parentRect.left + rect.width / 2,
          top: rect.top - parentRect.top + rect.height / 2
        });
      }
    }, null, time);
    tl.fromTo(selector,
      { autoAlpha: 0, scale: 0.3 },
      { autoAlpha: 1, scale: 1, duration: duration, ease: 'back.out(1.4)', immediateRender: false },
      time
    );
  },

  move(tl, selector, toSelector, time, duration) {
    tl.call(function() {
      var target = document.querySelector(selector);
      var dest = document.querySelector(toSelector);
      if (target && dest) {
        var destRect = dest.getBoundingClientRect();
        var parent = target.offsetParent || document.body;
        var parentRect = parent.getBoundingClientRect();
        gsap.set(target, { autoAlpha: 1 });
        tl.to(selector, {
          left: destRect.left - parentRect.left + destRect.width / 2,
          top: destRect.top - parentRect.top + destRect.height / 2,
          duration: duration,
          ease: 'power2.inOut'
        }, time);
      }
    }, null, time);
  },

  moveTo(tl, selector, x, y, time, duration) {
    tl.to(selector, { left: x, top: y, duration: duration, ease: 'power2.inOut' }, time);
  },

  /* --- Comparison --- */

  compare(tl, selectorA, selectorB, label, time, duration) {
    tl.to([selectorA, selectorB], {
      scale: 1.06,
      borderColor: 'var(--action)',
      duration: duration * 0.4,
      ease: 'power2.out'
    }, time);
    tl.to([selectorA, selectorB], {
      scale: 1,
      borderColor: 'var(--line)',
      duration: duration * 0.5,
      ease: 'power2.inOut'
    }, time + duration * 0.5);
  },

  /* --- Highlight / Emphasis --- */

  highlight(tl, selector, time, duration) {
    tl.to(selector, {
      borderColor: 'var(--accent)',
      backgroundColor: 'var(--accent-soft)',
      scale: 1.05,
      duration: duration * 0.4,
      ease: 'power2.out'
    }, time);
    tl.to(selector, {
      scale: 1,
      borderColor: 'var(--line)',
      backgroundColor: 'var(--surface)',
      duration: duration * 0.5,
      ease: 'power2.inOut'
    }, time + duration * 0.5);
  },

  pulse(tl, selector, time, duration) {
    tl.fromTo(selector,
      { scale: 1 },
      { scale: 1.12, duration: duration * 0.35, yoyo: true, repeat: 1, ease: 'power2.inOut' },
      time
    );
  },

  /* --- Connection --- */

  connect(tl, edgeSelector, fromSelector, toSelector, time, duration) {
    tl.fromTo(edgeSelector,
      { autoAlpha: 0, strokeDasharray: '0 999' },
      { autoAlpha: 1, strokeDasharray: '999 0', duration: duration, ease: 'power2.out', immediateRender: false },
      time
    );
  },

  /* --- Text / Data --- */

  setText(tl, selector, text, time, duration) {
    tl.call(function() {
      var el = document.querySelector(selector);
      if (el) el.textContent = text;
    }, null, time);
    Runtime.highlight(tl, selector, time, duration);
  },

  updateList(tl, selector, items, time, duration) {
    tl.call(function() {
      var el = document.querySelector(selector);
      if (!el) return;
      el.innerHTML = '';
      items.forEach(function(text, index) {
        var span = document.createElement('span');
        span.textContent = text;
        span.setAttribute('data-index', String(index));
        el.appendChild(span);
      });
    }, null, time);
    Runtime.highlight(tl, selector, time, duration);
  },

  updateTable(tl, selector, rows, time, duration) {
    tl.call(function() {
      var el = document.querySelector(selector);
      if (!el) return;
      var tbody = el.querySelector('tbody') || el;
      tbody.innerHTML = '';
      rows.forEach(function(cells) {
        var tr = document.createElement('tr');
        cells.forEach(function(cell) {
          var td = document.createElement('td');
          td.textContent = cell;
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
    }, null, time);
    Runtime.highlight(tl, selector, time, duration);
  },

  /* --- Zoom --- */

  zoom(tl, selector, scale, x, y, time, duration) {
    tl.to(selector, {
      scale: scale,
      transformOrigin: x + 'px ' + y + 'px',
      duration: duration,
      ease: 'power2.inOut'
    }, time);
  },

  /* --- Caption --- */

  caption(tl, selector, time, duration) {
    tl.fromTo(selector,
      { autoAlpha: 0, y: 12 },
      { autoAlpha: 1, y: 0, duration: Math.min(0.3, duration * 0.3), ease: 'power2.out', immediateRender: false },
      time
    );
    tl.to(selector,
      { autoAlpha: 0, y: -8, duration: Math.min(0.25, duration * 0.25), ease: 'power2.in' },
      time + duration * 0.75
    );
  }
};
