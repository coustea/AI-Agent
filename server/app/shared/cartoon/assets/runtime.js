(function () {
  "use strict";

  function byId(id) {
    return document.getElementById(id);
  }

  function sceneMap(payload) {
    const result = {};
    payload.scenes.forEach(function (scene) { result[scene.id] = scene; });
    return result;
  }

  function stateById(scene, stateId) {
    return scene.states.find(function (state) { return state.id === stateId; });
  }

  function placementById(state, entityId) {
    return state.placements.find(function (item) { return item.entity_id === entityId; });
  }

  function entityById(scene, entityId) {
    return scene.entities.find(function (item) { return item.id === entityId; });
  }

  function gridSpec(count) {
    const columns = count <= 4 ? 2 : count <= 9 ? 3 : 4;
    const rows = Math.ceil(Math.max(1, count) / columns);
    const width = columns === 2 ? 38 : columns === 3 ? 27 : 20;
    const height = Math.min(62, (88 - (rows - 1) * 6) / rows);
    const xs = Array.from({ length: columns }, function (_value, index) {
      return 50 + (index - (columns - 1) / 2) * (width + 4);
    });
    const ys = Array.from({ length: rows }, function (_value, index) {
      return 50 + (index - (rows - 1) / 2) * (height + 6);
    });
    return { columns: columns, width: width, height: height, xs: xs, ys: ys };
  }

  function stateLayout(scene, state) {
    // A scene owns fixed cells. Reordering cells during a tween creates crossing
    // paths, which can temporarily put an opaque card over another card's text.
    // State changes are communicated through visibility, emphasis, values and edges.
    const ordered = scene.entities;
    const grid = gridSpec(ordered.length);
    const layout = {};
    ordered.forEach(function (entity, index) {
      const column = index % grid.columns;
      const row = Math.floor(index / grid.columns);
      layout[entity.id] = {
        x: grid.xs[column],
        y: grid.ys[row],
        w: grid.width,
        h: grid.height
      };
    });
    return layout;
  }

  function relationKey(relation) {
    return [relation.source_id, relation.target_id, relation.label].join("|");
  }

  function relationCatalog(scene) {
    const keys = [];
    scene.states.forEach(function (state) {
      state.relations.forEach(function (relation) {
        const key = relationKey(relation);
        if (!keys.includes(key)) keys.push(key);
      });
    });
    return keys.sort();
  }

  function relationGeometry(layout, key) {
    const parts = key.split("|");
    const source = layout[parts[0]];
    const target = layout[parts[1]];
    if (!source || !target) return null;
    return { x1: source.x, y1: source.y, x2: target.x, y2: target.y };
  }

  function setTextScale(node) {
    const label = node.querySelector(".entity-label");
    const value = node.querySelector(".entity-value");
    const length = ((label && label.textContent) || "").length + ((value && value.textContent) || "").length;
    const labelSize = length > 96 ? 13 : length > 64 ? 16 : length > 40 ? 19 : 25;
    const valueSize = length > 96 ? 11 : length > 64 ? 13 : 16;
    node.style.setProperty("--entity-label-size", labelSize + "px");
    node.style.setProperty("--entity-value-size", valueSize + "px");
  }

  function applyEntityContent(scene, state) {
    state.placements.forEach(function (placement) {
      const entity = entityById(scene, placement.entity_id);
      const node = byId("entity-" + scene.id + "-" + entity.id);
      if (!node) return;
      const valueNode = node.querySelector(".entity-value");
      const value = placement.value || "";
      if (valueNode) {
        valueNode.textContent = value;
        valueNode.style.display = value ? "block" : "none";
      }
      node.dataset.status = placement.status;
      setTextScale(node);
    });
  }

  function entityVars(box, placement, focused) {
    return {
      left: box.x + "%", top: box.y + "%", width: box.w + "%", height: box.h + "%",
      xPercent: -50, yPercent: -50,
      autoAlpha: placement.visible ? 1 : 0,
      scale: focused ? 1.035 : 1
    };
  }

  function entityMotionVars(box, focused) {
    return {
      left: box.x + "%", top: box.y + "%", width: box.w + "%", height: box.h + "%",
      xPercent: -50, yPercent: -50,
      scale: focused ? 1.035 : 1
    };
  }

  function moveVector(region) {
    const distance = 16;
    const vectors = {
      left: { x: -distance, y: 0 }, right: { x: distance, y: 0 },
      top: { x: 0, y: -distance }, bottom: { x: 0, y: distance },
      input: { x: -distance, y: 0 }, output: { x: distance, y: 0 },
      code: { x: -distance, y: 0 }, result: { x: distance, y: 0 },
      main: { x: 0, y: -distance }
    };
    return vectors[region] || vectors.main;
  }

  function setRelations(scene, state, layout, immediate, timeline, at) {
    const activeRelations = new Set(state.relations.map(relationKey));
    relationCatalog(scene).forEach(function (key, index) {
      const group = byId("relation-" + scene.id + "-" + index);
      if (!group) return;
      const geometry = relationGeometry(layout, key);
      const visible = activeRelations.has(key) && geometry;
      const line = group.querySelector("line");
      const head = group.querySelector("circle");
      if (geometry) {
        const attrs = { x1: geometry.x1, y1: geometry.y1, x2: geometry.x2, y2: geometry.y2 };
        if (immediate) {
          line.setAttribute("x1", attrs.x1); line.setAttribute("y1", attrs.y1);
          line.setAttribute("x2", attrs.x2); line.setAttribute("y2", attrs.y2);
          head.setAttribute("cx", geometry.x2); head.setAttribute("cy", geometry.y2);
        } else {
          timeline.set(line, { attr: attrs }, at);
          timeline.set(head, { attr: { cx: geometry.x2, cy: geometry.y2 } }, at);
        }
      }
      if (immediate) window.gsap.set(group, { autoAlpha: visible ? 1 : 0 });
      else timeline.to(group, { autoAlpha: visible ? 1 : 0, duration: 0.24 }, at);
    });
  }

  function setState(scene, state) {
    const layout = stateLayout(scene, state);
    applyEntityContent(scene, state);
    state.placements.forEach(function (placement) {
      const entity = entityById(scene, placement.entity_id);
      const node = byId("entity-" + scene.id + "-" + entity.id);
      const box = layout[entity.id];
      if (node && box) window.gsap.set(node, entityVars(box, placement, placement.status === "active"));
    });
    setRelations(scene, state, layout, true);
  }

  function addStateTween(timeline, scene, state, at, duration, focusIds, transitionKind, transitionEntityIds) {
    const layout = stateLayout(scene, state);
    timeline.call(function () { applyEntityContent(scene, state); }, null, at);
    state.placements.forEach(function (placement) {
      const entity = entityById(scene, placement.entity_id);
      const node = byId("entity-" + scene.id + "-" + entity.id);
      const box = layout[entity.id];
      if (!node || !box) return;
      // Text must never be partially transparent: sampled transition frames
      // would blend its ink with the paper and make contrast nondeterministic.
      // Visibility changes are atomic; emphasis still moves through scale.
      timeline.set(node, { autoAlpha: placement.visible ? 1 : 0 }, at);
      const motion = entityMotionVars(box, focusIds.includes(entity.id));
      const isMove = transitionKind === "move" && transitionEntityIds.includes(entity.id);
      if (isMove) {
        const vector = moveVector(placement.region);
        // Keep a card inside its own grid cell. This makes a move explicit
        // without reintroducing inter-card crossings or text occlusion.
        timeline.to(node, Object.assign({}, motion, vector, {
          duration: duration * 0.45, ease: "power2.out"
        }), at);
        timeline.to(node, Object.assign({}, motion, {
          x: 0, y: 0, duration: duration * 0.55, ease: "power2.in"
        }), at + duration * 0.45);
      } else {
        timeline.to(node, Object.assign(motion, {
          duration: duration, ease: "power2.inOut"
        }), at);
      }
    });
    setRelations(scene, state, layout, false, timeline, at);
  }

  function mount(payload) {
    if (!window.gsap) throw new Error("GSAP failed to load");
    const scenes = sceneMap(payload);
    const timeline = window.gsap.timeline({ paused: true });
    const sceneTimes = {};

    payload.beats.forEach(function (beat) {
      const range = sceneTimes[beat.scene_id] || { start: beat.start_ms, end: beat.start_ms + beat.duration_ms };
      range.start = Math.min(range.start, beat.start_ms);
      range.end = Math.max(range.end, beat.start_ms + beat.duration_ms);
      sceneTimes[beat.scene_id] = range;
    });

    payload.scenes.forEach(function (scene) {
      const sceneNode = byId("scene-" + scene.id);
      const firstBeat = scene.beats[0];
      setState(scene, stateById(scene, firstBeat.before_state_id));
      window.gsap.set(sceneNode, { autoAlpha: 0 });
      const range = sceneTimes[scene.id];
      // A scene contains text. Fading its parent changes every descendant's
      // effective foreground color, so scene transitions are deliberately
      // discrete. Card and relation motion provides the visual transition.
      timeline.set(sceneNode, { autoAlpha: 1 }, range.start / 1000);
      timeline.set(sceneNode, { autoAlpha: 0 }, range.end / 1000);
    });

    payload.beats.forEach(function (timedBeat) {
      const scene = scenes[timedBeat.scene_id];
      const beat = scene.beats.find(function (item) { return item.id === timedBeat.beat_id; });
      const state = stateById(scene, beat.after_state_id);
      const at = (timedBeat.start_ms + Math.min(900, timedBeat.duration_ms * 0.22)) / 1000;
      const duration = Math.min(1.1, Math.max(0.62, timedBeat.duration_ms / 5000));
      addStateTween(
        timeline,
        scene,
        state,
        at,
        duration,
        beat.focus_entity_ids,
        beat.transition.kind,
        beat.transition.entity_ids
      );
    });

    payload.captions.forEach(function (cue, index) {
      const node = byId("caption-" + index);
      if (!node) return;
      const start = cue.start_ms / 1000;
      const end = cue.end_ms / 1000;
      // Caption fades make white text partially transparent and fail contrast
      // checks on sampled transition frames. Visibility changes are discrete;
      // scene motion still supplies the visual rhythm.
      timeline.set(node, { autoAlpha: 1, y: 0 }, start);
      timeline.set(node, { autoAlpha: 0 }, end);
    });

    const progress = byId("progress-fill");
    timeline.fromTo(progress, { scaleX: 0 }, { scaleX: 1, duration: payload.duration_ms / 1000, ease: "none" }, 0);
    timeline.to({}, { duration: payload.duration_ms / 1000 }, 0);
    return timeline;
  }

  window.CartoonRuntime = { mount: mount };
}());
