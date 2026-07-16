(function () {
  "use strict";

  const REGION_POSITIONS = {
    main: [50, 50], input: [11, 50], output: [89, 50], left: [25, 50],
    right: [75, 50], top: [50, 18], bottom: [50, 68], code: [26, 50], result: [76, 72]
  };

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

  function freePosition(scene, state, placement, index) {
    const base = REGION_POSITIONS[placement.region] || REGION_POSITIONS.main;
    const sameRegion = scene.entities.filter(function (entity) {
      const current = placementById(state, entity.id);
      return current && current.region === placement.region && !current.container_id;
    });
    const count = Math.max(1, sameRegion.length);
    const ownIndex = Math.max(0, sameRegion.findIndex(function (item) {
      return item.id === placement.entity_id;
    }));
    if (scene.grammar === "concept" && placement.region === "main") {
      const angle = (Math.PI * 2 * ownIndex / count) - Math.PI / 2;
      const radius = count <= 2 ? 18 : 30;
      return { x: 50 + Math.cos(angle) * radius, y: 50 + Math.sin(angle) * radius, w: 18, h: 14 };
    }
    if (count === 1) return { x: base[0], y: base[1], w: 20, h: 15 };
    const offset = (ownIndex - (count - 1) / 2) * Math.min(19, 62 / count);
    return { x: base[0], y: base[1] + offset, w: 20, h: 14 };
  }

  function containerGeometry(scene, state, entity, placement) {
    const containers = scene.entities.filter(function (item) { return item.kind === "container"; });
    const index = Math.max(0, containers.findIndex(function (item) { return item.id === entity.id; }));
    const count = containers.length;
    const base = REGION_POSITIONS[placement.region] || REGION_POSITIONS.main;
    if (entity.orientation === "horizontal") {
      return { x: base[0], y: base[1] + (index - (count - 1) / 2) * 32, w: 58, h: 25 };
    }
    if (count > 1) {
      return { x: 34 + index * (32 / Math.max(1, count - 1)), y: base[1], w: 25, h: 62 };
    }
    return { x: base[0], y: base[1], w: 28, h: 64 };
  }

  function geometry(scene, state, entity, placement, cache) {
    if (cache[entity.id]) return cache[entity.id];
    if (entity.kind === "container") {
      cache[entity.id] = containerGeometry(scene, state, entity, placement);
      return cache[entity.id];
    }
    if (placement.container_id) {
      const container = entityById(scene, placement.container_id);
      const containerPlacement = placementById(state, placement.container_id);
      const parent = geometry(scene, state, container, containerPlacement, cache);
      const slot = placement.slot === null ? 0 : placement.slot;
      if (container.orientation === "horizontal") {
        cache[entity.id] = {
          x: parent.x - parent.w / 2 + 8 + slot * 10,
          y: parent.y + (entity.kind === "pointer" ? parent.h / 2 + 8 : 3),
          w: 10,
          h: 9
        };
      } else {
        cache[entity.id] = {
          x: parent.x + (entity.kind === "pointer" ? parent.w / 2 + 9 : 0),
          y: parent.y + parent.h / 2 - 8 - slot * 10,
          w: 10,
          h: 9
        };
      }
      return cache[entity.id];
    }
    cache[entity.id] = freePosition(scene, state, placement, scene.entities.indexOf(entity));
    return cache[entity.id];
  }

  function stateLayout(scene, state) {
    const cache = {};
    state.placements.forEach(function (placement) {
      const entity = entityById(scene, placement.entity_id);
      geometry(scene, state, entity, placement, cache);
    });
    return cache;
  }

  function relationKey(relation) {
    return [relation.source_id, relation.target_id, relation.label, relation.directed].join("|");
  }

  function relationCatalog(scene) {
    const keys = [];
    scene.states.forEach(function (state) {
      state.relations.forEach(function (relation) {
        const key = relationKey(relation);
        if (!keys.includes(key)) keys.push(key);
      });
    });
    keys.sort();
    return keys;
  }

  function relationGeometry(state, layout, key) {
    const sourceId = key.split("|")[0];
    const targetId = key.split("|")[1];
    const source = layout[sourceId];
    const target = layout[targetId];
    if (!source || !target) return null;
    let labelX = (source.x + target.x) / 2;
    let labelY = (source.y + target.y) / 2 - 1.6;
    const sourcePlacement = placementById(state, sourceId);
    const targetPlacement = placementById(state, targetId);
    if (
      sourcePlacement && targetPlacement && sourcePlacement.container_id &&
      sourcePlacement.container_id === targetPlacement.container_id
    ) {
      const parent = layout[sourcePlacement.container_id];
      if (parent) {
        labelX = parent.x;
        labelY = parent.y - parent.h / 2 - 2.5;
      }
    } else if (sourcePlacement && sourcePlacement.container_id === targetId) {
      labelX = target.x;
      labelY = target.y - target.h / 2 - 2.5;
    } else if (targetPlacement && targetPlacement.container_id === sourceId) {
      labelX = source.x;
      labelY = source.y - source.h / 2 - 2.5;
    }
    return {
      x1: source.x, y1: source.y, x2: target.x, y2: target.y,
      labelX: labelX, labelY: labelY
    };
  }

  function applyEntityContent(scene, state) {
    state.placements.forEach(function (placement) {
      const entity = entityById(scene, placement.entity_id);
      const node = byId("entity-" + scene.id + "-" + entity.id);
      if (!node) return;
      const value = placement.value || entity.initial_value || "";
      const valueNode = node.querySelector(".entity-value");
      if (valueNode) {
        valueNode.textContent = value;
        valueNode.style.display = value ? "block" : "none";
      }
      node.dataset.status = placement.status;
    });
    const note = byId("state-note-" + scene.id);
    if (note) note.textContent = state.annotation || state.label;
  }

  function setState(scene, state, immediate) {
    const layout = stateLayout(scene, state);
    state.placements.forEach(function (placement) {
      const entity = entityById(scene, placement.entity_id);
      const node = byId("entity-" + scene.id + "-" + entity.id);
      const box = layout[entity.id];
      if (!node || !box) return;
      const vars = {
        left: box.x + "%", top: box.y + "%", width: box.w + "%", minHeight: box.h + "%",
        xPercent: -50, yPercent: -50,
        autoAlpha: placement.visible ? 1 : 0, scale: placement.status === "active" ? 1.06 : 1
      };
      if (immediate) window.gsap.set(node, vars);
    });
    const activeRelations = new Set(state.relations.map(relationKey));
    const catalog = relationCatalog(scene);
    catalog.forEach(function (key, index) {
      const group = byId("relation-" + scene.id + "-" + index);
      if (!group) return;
      const relation = state.relations.find(function (item) { return relationKey(item) === key; });
      const geometry = relationGeometry(state, layout, key);
      if (geometry) {
        const line = group.querySelector("line");
        const head = group.querySelector("circle");
        const label = group.querySelector("text");
        line.setAttribute("x1", geometry.x1); line.setAttribute("y1", geometry.y1);
        line.setAttribute("x2", geometry.x2); line.setAttribute("y2", geometry.y2);
        head.setAttribute("cx", geometry.x2); head.setAttribute("cy", geometry.y2);
        label.setAttribute("x", geometry.labelX);
        label.setAttribute("y", geometry.labelY);
      }
      if (immediate) window.gsap.set(group, { autoAlpha: relation && activeRelations.has(key) ? 1 : 0 });
    });
    applyEntityContent(scene, state);
  }

  function addStateTween(timeline, scene, state, at, duration, focusIds) {
    const layout = stateLayout(scene, state);
    timeline.call(function () { applyEntityContent(scene, state); }, null, at);
    state.placements.forEach(function (placement) {
      const entity = entityById(scene, placement.entity_id);
      const node = byId("entity-" + scene.id + "-" + entity.id);
      const box = layout[entity.id];
      if (!node || !box) return;
      timeline.to(node, {
        left: box.x + "%", top: box.y + "%", width: box.w + "%", minHeight: box.h + "%",
        xPercent: -50, yPercent: -50,
        scale: focusIds.includes(entity.id) ? 1.06 : 1,
        duration: duration, ease: "power2.inOut"
      }, at);
      timeline.to(node, {
        autoAlpha: placement.visible ? 1 : 0,
        duration: 0.18,
        ease: "power1.inOut"
      }, placement.visible ? at + duration * 0.62 : at);
    });
    const activeRelations = new Set(state.relations.map(relationKey));
    relationCatalog(scene).forEach(function (key, index) {
      const group = byId("relation-" + scene.id + "-" + index);
      if (!group) return;
      const relationBox = relationGeometry(state, layout, key);
      if (relationBox) {
        timeline.set(group.querySelector("line"), {
          attr: { x1: relationBox.x1, y1: relationBox.y1, x2: relationBox.x2, y2: relationBox.y2 }
        }, at);
        timeline.set(group.querySelector("circle"), {
          attr: { cx: relationBox.x2, cy: relationBox.y2 }
        }, at);
        timeline.set(group.querySelector("text"), {
          attr: { x: relationBox.labelX, y: relationBox.labelY }
        }, at);
      }
      timeline.to(group, { autoAlpha: activeRelations.has(key) ? 1 : 0, duration: 0.28 }, at);
    });
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
      setState(scene, stateById(scene, firstBeat.before_state_id), true);
      window.gsap.set(sceneNode, { autoAlpha: 0 });
      const range = sceneTimes[scene.id];
      timeline.to(sceneNode, { autoAlpha: 1, duration: 0.42, ease: "power2.out" }, range.start / 1000);
      timeline.to(sceneNode, { autoAlpha: 0, duration: 0.34, ease: "power2.in" }, Math.max(range.start, range.end - 340) / 1000);
    });

    payload.beats.forEach(function (timedBeat) {
      const scene = scenes[timedBeat.scene_id];
      const beat = scene.beats.find(function (item) { return item.id === timedBeat.beat_id; });
      const state = stateById(scene, beat.after_state_id);
      const at = (timedBeat.start_ms + Math.min(900, timedBeat.duration_ms * 0.22)) / 1000;
      const duration = Math.min(1.1, Math.max(0.62, timedBeat.duration_ms / 5000));
      addStateTween(timeline, scene, state, at, duration, beat.focus_entity_ids);
    });

    payload.captions.forEach(function (cue, index) {
      const node = byId("caption-" + index);
      if (!node) return;
      const start = cue.start_ms / 1000;
      const end = cue.end_ms / 1000;
      timeline.fromTo(node, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, duration: 0.18, ease: "power1.out" }, start);
      timeline.to(node, { autoAlpha: 0, y: -5, duration: 0.16, ease: "power1.in" }, Math.max(start + 0.2, end - 0.16));
    });

    const progress = byId("progress-fill");
    timeline.fromTo(progress, { scaleX: 0 }, { scaleX: 1, duration: payload.duration_ms / 1000, ease: "none" }, 0);
    timeline.to({}, { duration: payload.duration_ms / 1000 }, 0);
    return timeline;
  }

  window.CartoonRuntime = { mount: mount };
}());
