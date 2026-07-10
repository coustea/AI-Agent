/* White Teaching Video Runtime: deterministic GSAP wrappers for HyperFrames. */

(function () {
  function q(selector) {
    return document.querySelector(selector);
  }

  function qa(selector) {
    return Array.prototype.slice.call(document.querySelectorAll(selector));
  }

  function duration(value, fallback) {
    return typeof value === "number" && value > 0 ? value : fallback;
  }

  function ensurePositioned(el) {
    if (!el) return;
    var computed = window.getComputedStyle(el);
    if (computed.position === "static") el.style.position = "absolute";
    if (!el.style.left) el.style.left = "0px";
    if (!el.style.top) el.style.top = "0px";
  }

  function centerRelativeTo(target, reference) {
    var parent = target.offsetParent || target.parentElement || document.body;
    var parentRect = parent.getBoundingClientRect();
    var refRect = reference.getBoundingClientRect();
    return {
      left: refRect.left - parentRect.left + refRect.width / 2 - target.offsetWidth / 2,
      top: refRect.top - parentRect.top + refRect.height / 2 - target.offsetHeight / 2
    };
  }

  function setLine(edge, from, to) {
    if (!edge || !from || !to) return;
    var svg = edge.ownerSVGElement;
    if (!svg) return;

    var svgRect = svg.getBoundingClientRect();
    var fromRect = from.getBoundingClientRect();
    var toRect = to.getBoundingClientRect();

    edge.setAttribute("x1", String(fromRect.left - svgRect.left + fromRect.width / 2));
    edge.setAttribute("y1", String(fromRect.top - svgRect.top + fromRect.height / 2));
    edge.setAttribute("x2", String(toRect.left - svgRect.left + toRect.width / 2));
    edge.setAttribute("y2", String(toRect.top - svgRect.top + toRect.height / 2));
  }

  function applyState(el, stateName) {
    if (!el) return;
    el.setAttribute("data-state", stateName || "active");
    el.classList.remove("state-ok", "state-warn", "state-error", "state-active");

    if (stateName === "ok" || stateName === "success" || stateName === "done") {
      el.classList.add("state-ok");
    } else if (stateName === "warn" || stateName === "waiting") {
      el.classList.add("state-warn");
    } else if (stateName === "error" || stateName === "wrong") {
      el.classList.add("state-error");
    } else {
      el.classList.add("state-active");
    }
  }

  window.Runtime = {
    sceneIn(tl, selector, time, dur) {
      dur = duration(dur, 0.6);
      tl.fromTo(
        selector,
        { autoAlpha: 0, scale: 1.01 },
        { autoAlpha: 1, scale: 1, duration: dur, ease: "power2.out", immediateRender: false },
        time
      );
    },

    sceneOut(tl, selector, time, dur) {
      dur = duration(dur, 0.5);
      tl.to(selector, { autoAlpha: 0, scale: 0.995, duration: dur, ease: "power2.inOut" }, time);
    },

    reveal(tl, selector, time, dur) {
      dur = duration(dur, 0.6);
      tl.fromTo(
        selector,
        { autoAlpha: 0, y: 20, scale: 0.98 },
        { autoAlpha: 1, y: 0, scale: 1, duration: dur, ease: "power2.out", immediateRender: false },
        time
      );
    },

    fadeIn(tl, selector, time, dur) {
      dur = duration(dur, 0.45);
      tl.fromTo(
        selector,
        { autoAlpha: 0 },
        { autoAlpha: 1, duration: dur, ease: "power1.inOut", immediateRender: false },
        time
      );
    },

    popIn(tl, selector, time, dur) {
      dur = duration(dur, 0.55);
      tl.fromTo(
        selector,
        { autoAlpha: 0, scale: 0.72 },
        { autoAlpha: 1, scale: 1, duration: dur, ease: "back.out(1.25)", immediateRender: false },
        time
      );
    },

    slideIn(tl, selector, x, y, time, dur) {
      dur = duration(dur, 0.65);
      tl.fromTo(
        selector,
        { autoAlpha: 0, x: x, y: y },
        { autoAlpha: 1, x: 0, y: 0, duration: dur, ease: "power2.out", immediateRender: false },
        time
      );
    },

    spawn(tl, selector, fromSelector, time, dur) {
      dur = duration(dur, 0.6);
      tl.call(function () {
        var target = q(selector);
        var source = q(fromSelector);
        if (target) {
          ensurePositioned(target);
          if (source) {
            var point = centerRelativeTo(target, source);
            target.style.left = point.left + "px";
            target.style.top = point.top + "px";
          }
        }
      }, null, time);

      tl.fromTo(
        selector,
        { autoAlpha: 0, scale: 0.4 },
        { autoAlpha: 1, scale: 1, duration: dur, ease: "back.out(1.25)", immediateRender: false },
        time
      );
    },

    move(tl, selector, toSelector, time, dur) {
      dur = duration(dur, 1.0);
      tl.call(function () {
        var target = q(selector);
        if (target) ensurePositioned(target);
      }, null, time);

      tl.to(
        selector,
        {
          left: function (_index, target) {
            var dest = q(toSelector);
            if (!dest) return parseFloat(target.style.left || "0");
            return centerRelativeTo(target, dest).left;
          },
          top: function (_index, target) {
            var dest = q(toSelector);
            if (!dest) return parseFloat(target.style.top || "0");
            return centerRelativeTo(target, dest).top;
          },
          autoAlpha: 1,
          duration: dur,
          ease: "power2.inOut"
        },
        time
      );
    },

    moveTo(tl, selector, x, y, time, dur) {
      dur = duration(dur, 1.0);
      tl.call(function () {
        var target = q(selector);
        if (target) ensurePositioned(target);
      }, null, time);

      tl.to(selector, { left: x, top: y, autoAlpha: 1, duration: dur, ease: "power2.inOut" }, time);
    },

    transfer(tl, selector, fromSelector, toSelector, time, dur) {
      dur = duration(dur, 1.0);
      this.move(tl, selector, toSelector, time, dur);
      this.highlight(tl, fromSelector, time, Math.min(0.5, dur));
      this.highlight(tl, toSelector, time + dur * 0.55, Math.min(0.5, dur));
    },

    connect(tl, edgeSelector, fromSelector, toSelector, time, dur) {
      dur = duration(dur, 0.8);
      tl.call(function () {
        qa(edgeSelector).forEach(function (edge) {
          setLine(edge, q(fromSelector), q(toSelector));
        });
      }, null, time);

      tl.fromTo(
        edgeSelector,
        { autoAlpha: 0, strokeDasharray: "0 900" },
        { autoAlpha: 1, strokeDasharray: "900 0", duration: dur, ease: "power2.out", immediateRender: false },
        time
      );
    },

    drawPath(tl, selector, time, dur) {
      dur = duration(dur, 1.0);
      tl.fromTo(
        selector,
        { autoAlpha: 0, strokeDasharray: "0 1200" },
        { autoAlpha: 1, strokeDasharray: "1200 0", duration: dur, ease: "power2.out", immediateRender: false },
        time
      );
    },

    highlight(tl, selector, time, dur) {
      dur = duration(dur, 0.75);
      tl.to(
        selector,
        {
          scale: 1.045,
          boxShadow: "0 0 0 10px var(--focus-soft)",
          borderColor: "var(--ink)",
          duration: dur * 0.45,
          ease: "power2.out"
        },
        time
      );
      tl.to(
        selector,
        {
          scale: 1,
          boxShadow: "var(--shadow)",
          borderColor: "var(--line)",
          duration: dur * 0.45,
          ease: "power2.inOut"
        },
        time + dur * 0.5
      );
    },

    pulse(tl, selector, time, dur) {
      dur = duration(dur, 0.8);
      tl.fromTo(
        selector,
        { scale: 1 },
        { scale: 1.08, duration: dur * 0.35, yoyo: true, repeat: 1, ease: "power2.inOut" },
        time
      );
    },

    focus(tl, selector, time, dur) {
      dur = duration(dur, 0.8);
      tl.to(selector, { scale: 1.06, filter: "drop-shadow(0 18px 34px rgba(15,23,42,.14))", duration: dur * 0.5, ease: "power2.out" }, time);
      tl.to(selector, { scale: 1, filter: "none", duration: dur * 0.5, ease: "power2.inOut" }, time + dur * 0.55);
    },

    spotlight(tl, selector, time, dur) {
      dur = duration(dur, 0.8);
      tl.to(selector, { zIndex: 20, scale: 1.08, duration: dur, ease: "power2.out" }, time);
    },

    compare(tl, selectorA, selectorB, label, time, dur) {
      dur = duration(dur, 0.8);
      tl.to([selectorA, selectorB], { scale: 1.04, borderColor: "var(--ink)", duration: dur * 0.45, ease: "power2.out" }, time);
      tl.to([selectorA, selectorB], { scale: 1, borderColor: "var(--line)", duration: dur * 0.45, ease: "power2.inOut" }, time + dur * 0.55);
    },

    switchState(tl, selector, stateText, stateName, time, dur) {
      dur = duration(dur, 0.5);
      tl.call(function () {
        var el = q(selector);
        if (!el) return;
        el.textContent = stateText;
        applyState(el, stateName);
      }, null, time);
      this.highlight(tl, selector, time, dur);
    },

    setText(tl, selector, text, time, dur) {
      dur = duration(dur, 0.5);
      tl.call(function () {
        var el = q(selector);
        if (el) el.textContent = text;
      }, null, time);
      this.highlight(tl, selector, time, dur);
    },

    updateList(tl, selector, items, time, dur) {
      dur = duration(dur, 0.6);
      tl.call(function () {
        var el = q(selector);
        if (!el) return;
        el.innerHTML = "";
        items.forEach(function (text, index) {
          var span = document.createElement("span");
          span.textContent = text;
          span.setAttribute("data-index", String(index));
          el.appendChild(span);
        });
      }, null, time);
      this.highlight(tl, selector, time, dur);
    },

    updateTable(tl, selector, rows, time, dur) {
      dur = duration(dur, 0.6);
      tl.call(function () {
        var el = q(selector);
        if (!el) return;
        var tbody = el.querySelector("tbody") || el;
        tbody.innerHTML = "";
        rows.forEach(function (cells) {
          var tr = document.createElement("tr");
          cells.forEach(function (cell) {
            var td = document.createElement("td");
            td.textContent = cell;
            tr.appendChild(td);
          });
          tbody.appendChild(tr);
        });
      }, null, time);
      this.highlight(tl, selector, time, dur);
    },

    markStep(tl, selector, stepIndex, time, dur) {
      dur = duration(dur, 0.4);
      tl.call(function () {
        var root = q(selector);
        if (!root) return;
        qa(selector + " .step-chip").forEach(function (item, index) {
          item.classList.toggle("is-active", index === stepIndex);
          item.classList.toggle("is-done", index < stepIndex);
        });
      }, null, time);
      this.highlight(tl, selector, time, dur);
    },

    advanceTrack(tl, selector, stepIndex, time, dur) {
      this.markStep(tl, selector, stepIndex, time, dur);
    },

    sendPacket(tl, selector, fromSelector, toSelector, time, dur) {
      dur = duration(dur, 1.0);
      this.transfer(tl, selector, fromSelector, toSelector, time, dur);
      this.pulse(tl, toSelector, time + dur * 0.7, 0.5);
    },

    returnAck(tl, selector, fromSelector, toSelector, time, dur) {
      dur = duration(dur, 1.0);
      this.transfer(tl, selector, fromSelector, toSelector, time, dur);
      this.highlight(tl, selector, time + dur * 0.4, 0.5);
    },

    replaceFrame(tl, oldSelector, newSelector, slotSelector, time, dur) {
      dur = duration(dur, 1.0);
      tl.to(oldSelector, { autoAlpha: 0, y: 40, scale: 0.8, duration: dur * 0.45, ease: "power2.in" }, time);
      this.move(tl, newSelector, slotSelector, time + dur * 0.45, dur * 0.55);
      this.highlight(tl, slotSelector, time + dur * 0.65, 0.5);
    },

    insertNode(tl, nodeSelector, parentSelector, slotSelector, edgeSelector, time, dur) {
      dur = duration(dur, 1.2);
      this.transfer(tl, nodeSelector, parentSelector, slotSelector, time, dur * 0.65);
      this.connect(tl, edgeSelector, parentSelector, nodeSelector, time + dur * 0.65, dur * 0.35);
      this.highlight(tl, nodeSelector, time + dur * 0.75, 0.5);
    },

    rotateTree(tl, rootSelector, pivotSelector, time, dur) {
      dur = duration(dur, 1.0);
      tl.to(rootSelector, { rotation: -8, x: -70, y: 54, duration: dur, ease: "power2.inOut" }, time);
      tl.to(pivotSelector, { rotation: 6, x: 70, y: -54, duration: dur, ease: "power2.inOut" }, time);
    },

    cameraZoom(tl, selector, scale, x, y, time, dur) {
      dur = duration(dur, 1.0);
      tl.to(selector, { scale: scale, transformOrigin: x + "px " + y + "px", duration: dur, ease: "power2.inOut" }, time);
    },

    cameraPan(tl, selector, x, y, time, dur) {
      dur = duration(dur, 1.0);
      tl.to(selector, { x: x, y: y, duration: dur, ease: "power2.inOut" }, time);
    },

    cameraFocus(tl, cameraSelector, targetSelector, scale, time, dur) {
      dur = duration(dur, 1.0);
      tl.call(function () {
        var camera = q(cameraSelector);
        var target = q(targetSelector);
        if (!camera || !target) return;
        var stage = camera.getBoundingClientRect();
        var rect = target.getBoundingClientRect();
        var cx = rect.left - stage.left + rect.width / 2;
        var cy = rect.top - stage.top + rect.height / 2;
        camera.style.transformOrigin = cx + "px " + cy + "px";
      }, null, time);
      tl.to(cameraSelector, { scale: scale, duration: dur, ease: "power2.inOut" }, time);
    },

    cameraReset(tl, selector, time, dur) {
      dur = duration(dur, 0.8);
      tl.to(selector, { scale: 1, x: 0, y: 0, rotation: 0, duration: dur, ease: "power2.inOut" }, time);
    },

    caption(tl, selector, time, dur) {
      dur = duration(dur, 4.0);
      tl.fromTo(
        selector,
        { autoAlpha: 0, y: 12 },
        { autoAlpha: 1, y: 0, duration: Math.min(0.35, dur * 0.25), ease: "power2.out", immediateRender: false },
        time
      );
      tl.to(
        selector,
        { autoAlpha: 0, y: -8, duration: Math.min(0.3, dur * 0.22), ease: "power2.in" },
        time + dur * 0.78
      );
    }
  };
})();