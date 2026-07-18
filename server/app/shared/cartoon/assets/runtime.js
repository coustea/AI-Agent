(function () {
  "use strict";

  function byId(id) { return document.getElementById(id); }
  function mapById(items) { return Object.fromEntries(items.map(function (item) { return [item.id, item]; })); }
  function stateById(scene, id) { return scene.program.states.find(function (state) { return state.id === id; }); }
  function sceneById(payload) { return mapById(payload.scenes); }

  function grid(count, width, height, centerX, centerY) {
    if (count === 0) return [];
    var columns = count <= 3 ? count : count <= 6 ? 3 : count <= 10 ? 4 : 6;
    var rows = Math.ceil(Math.max(1, count) / columns);
    var cellW = Math.min(width / columns - 3, 26);
    var cellH = Math.min(Math.max(height / rows - 4, 8), 30);
    var layoutHeight = Math.max(height, rows * (cellH + 4));
    return Array.from({ length: count }, function (_item, index) {
      return { x: centerX - width / 2 + (index % columns + 0.5) * width / columns,
        y: centerY - layoutHeight / 2 + (Math.floor(index / columns) + 0.5) * layoutHeight / rows,
        w: cellW, h: cellH };
    });
  }

  function clamp(value, minimum, maximum) { return Math.min(maximum, Math.max(minimum, value)); }
  function textUnits(text) {
    return Array.from(text || "").reduce(function (units, character) {
      return units + (/\s/.test(character) ? 0.35 : character.charCodeAt(0) > 255 ? 1 : 0.58);
    }, 0);
  }
  function footprint(object, placement) {
    var labelUnits = textUnits(object.label || "");
    var valueUnits = textUnits(placement.value || object.value || "");
    var longest = Math.max(labelUnits, valueUnits, 1);
    if (object.role === "pointer") {
      return { w: clamp(9 + longest * 1.35, 14, 29), h: clamp(6 + Math.ceil(longest / 12) * 2, 8, 13) };
    }
    var width = clamp(12 + longest * 1.05, 15, 34);
    var lines = Math.max(1, Math.ceil(longest / Math.max(7, width - 4)));
    return { w: width, h: clamp(12 + lines * 6 + (valueUnits ? 5 : 0), 14, 34) };
  }
  function bounded(box) {
    var width = Math.min(box.w, 92); var height = Math.min(box.h, 82);
    return {
      x: clamp(box.x, width / 2 + 2, 98 - width / 2),
      y: clamp(box.y, height / 2 + 3, 97 - height / 2),
      w: width, h: height
    };
  }
  function overlapArea(first, second, gap) {
    var padding = gap || 0;
    var width = Math.max(0, Math.min(first.x + first.w / 2 + padding, second.x + second.w / 2 + padding) - Math.max(first.x - first.w / 2 - padding, second.x - second.w / 2 - padding));
    var height = Math.max(0, Math.min(first.y + first.h / 2 + padding, second.y + second.h / 2 + padding) - Math.max(first.y - first.h / 2 - padding, second.y - second.h / 2 - padding));
    return width * height;
  }
  function collisionScore(box, occupied) {
    return occupied.reduce(function (score, entry) { return score + overlapArea(box, entry, 1.25); }, 0);
  }
  function openBox(preferred, size, occupied, rotation) {
    var angles = [-90, -35, -145, 0, 180, 40, 140, 90, -68, -112, 68, 112];
    var radii = [0, 4, 8, 14, 21, 29, 38];
    var best = null; var bestScore = Infinity;
    [1, 0.88, 0.76, 0.64].forEach(function (scale) {
      var candidates = [];
      var candidateSize = { w: Math.max(11, size.w * scale), h: Math.max(7, size.h * scale) };
      radii.forEach(function (radius) {
        angles.forEach(function (angle) {
          var radians = (angle + (rotation || 0) * 29) * Math.PI / 180;
          candidates.push(bounded({ x: preferred.x + Math.cos(radians) * radius, y: preferred.y + Math.sin(radians) * radius, w: candidateSize.w, h: candidateSize.h }));
        });
      });
      candidates.forEach(function (candidate) {
        var score = collisionScore(candidate, occupied);
        if (score < bestScore) { best = candidate; bestScore = score; }
      });
    });
    return best;
  }
  function anchoredBox(anchor, size, order) {
    var angles = [-90, -35, -145, 0, 180, 40, 140, 90];
    var angle = angles[order % angles.length] * Math.PI / 180;
    var ring = Math.max(anchor.w / 2 + size.w / 2 + 2, anchor.h / 2 + size.h / 2 + 2) + Math.floor(order / angles.length) * 9;
    return { x: anchor.x + Math.cos(angle) * ring, y: anchor.y + Math.sin(angle) * ring, w: size.w, h: size.h };
  }

  function freeLayout(scene, state, objects) {
    var layout = {};
    var free = state.placements.filter(function (placement) {
      var object = objects[placement.object_id];
      var region = placement.region || "main";
      return object && object.role !== "container" && object.role !== "pointer"
        && !placement.container_id && !placement.anchor_id && (region === "main" || region === "input");
    });
    var topology = scene.topology;
    var positions;
    var hasContainers = scene.program.objects.some(function (object) { return object.role === "container"; });
    var dense = (topology === "flow" && free.length > 5)
      || (topology === "sequence" && free.length > 5)
      || (topology === "hierarchical" && free.length > 8)
      || (topology === "network" && free.length > 10)
      || (topology === "spatial" && free.length > 6);
    if (hasContainers) {
      positions = grid(free.length, 80, 22, 50, 18);
    } else if (dense) {
      positions = grid(free.length, 76, 62, 50, 51);
    } else if (topology === "flow") {
      positions = free.map(function (_item, index) { return { x: 16 + index * (68 / Math.max(1, free.length - 1)), y: 50, w: 18, h: 18 }; });
    } else if (topology === "sequence") {
      positions = free.map(function (_item, index) { return { x: 16 + index * (68 / Math.max(1, free.length - 1)), y: 53 + (index % 2 ? 8 : -8), w: 17, h: 17 }; });
    } else if (topology === "hierarchical") {
      positions = free.map(function (_item, index) {
        var row = index === 0 ? 0 : index <= 2 ? 1 : 2;
        var count = row === 0 ? 1 : row === 1 ? Math.min(2, Math.max(0, free.length - 1)) : Math.max(1, free.length - 3);
        var offset = row === 0 ? 0 : index - (row === 1 ? 1 : 3);
        return { x: 50 + (offset - (count - 1) / 2) * (row === 2 ? 21 : 30), y: 25 + row * 29, w: 17, h: 17 };
      });
    } else if (topology === "network") {
      positions = free.map(function (_item, index) {
        var angle = (Math.PI * 2 * index / Math.max(1, free.length)) - Math.PI / 2;
        return { x: 50 + Math.cos(angle) * 30, y: 49 + Math.sin(angle) * 25, w: 16, h: 16 };
      });
    } else if (topology === "spatial") {
      positions = free.map(function (_item, index) {
        var angles = [-2.1, -0.65, 0.35, 1.6, 2.65, 3.65];
        var angle = angles[index % angles.length];
        return index === 0 ? { x: 50, y: 50, w: 24, h: 20 } : { x: 50 + Math.cos(angle) * 31, y: 50 + Math.sin(angle) * 27, w: 17, h: 15 };
      });
    } else {
      positions = grid(free.length, 70, 58, 50, 50);
    }
    free.forEach(function (placement, index) { layout[placement.object_id] = positions[index]; });
    return layout;
  }

  function layout(scene, state) {
    var objects = mapById(scene.program.objects);
    var result = freeLayout(scene, state, objects);
    var containers = scene.program.objects.filter(function (object) { return object.role === "container"; });
    var containerBoxes;
    if (containers.length <= 3) {
      var containerGroupWidth = containers.length === 1 ? 72 : containers.length === 2 ? 78 : 92;
      var containerGap = 4;
      var availableWidth = containerGroupWidth - Math.max(0, containers.length - 1) * containerGap;
      var capacities = containers.map(function (container) { return Math.max(1, container.capacity || 1); });
      var totalCapacity = capacities.reduce(function (sum, capacity) { return sum + capacity; }, 0);
      var cursor = 50 - containerGroupWidth / 2;
      containerBoxes = containers.map(function (container, index) {
        var width = availableWidth * capacities[index] / totalCapacity;
        var box = { x: cursor + width / 2, y: 62, w: width, h: 50 };
        cursor += width + containerGap;
        return box;
      });
    } else {
      containerBoxes = grid(containers.length, 86, 58, 50, 57);
    }
    containers.forEach(function (container, index) {
      result[container.id] = containerBoxes[index];
    });
    var regionCounts = {};
    state.placements.forEach(function (placement) {
      var object = objects[placement.object_id];
      if (!object || object.role === "container" || object.role === "pointer") return;
      if (placement.container_id && placement.slot !== null && placement.slot !== undefined) {
        var container = result[placement.container_id];
        var capacity = (objects[placement.container_id] || {}).capacity || 1;
        if (container) {
          var slots = grid(capacity, container.w * 0.82, container.h * 0.58, container.x, container.y + 4);
          result[object.id] = slots[placement.slot];
        }
        return;
      }
      if (placement.container_id) {
        var logicalContainer = result[placement.container_id];
        if (logicalContainer) {
          var members = state.placements.filter(function (item) {
            return item.container_id === placement.container_id && (item.slot === null || item.slot === undefined);
          });
          var memberIndex = members.findIndex(function (item) { return item.object_id === placement.object_id; });
          var memberBoxes = grid(members.length, logicalContainer.w * 0.78, logicalContainer.h * 0.58, logicalContainer.x, logicalContainer.y + 3);
          result[object.id] = memberBoxes[memberIndex];
          return;
        }
      }
      if (placement.anchor_id) return;
      if (result[object.id]) return;
      var region = placement.region || "main";
      var index = regionCounts[region] || 0;
      regionCounts[region] = index + 1;
      var anchors = { input: [11, 48], output: [89, 48], left: [14, 50], right: [86, 50], top: [50, 16], bottom: [50, 83], code: [22, 76], result: [80, 76], main: [50, 50] };
      var anchor = anchors[region] || anchors.main;
      result[object.id] = { x: anchor[0], y: anchor[1] + index * 13, w: 15, h: 14 };
    });

    // Resolve attachments after every structural object has a box.  Anchored
    // objects used to share a single fixed offset, so concurrent pointers and
    // markers routinely covered one another or the object they described.
    var occupied = state.placements.reduce(function (boxes, placement) {
      var object = objects[placement.object_id];
      if (placement.visible && object && object.role !== "container" && result[object.id]) boxes.push(result[object.id]);
      return boxes;
    }, []);
    var anchorOrders = {};
    var pending = state.placements.filter(function (placement) { return placement.anchor_id && objects[placement.object_id]; }).sort(function (left, right) {
      var leftRole = objects[left.object_id].role === "pointer" ? 1 : 0;
      var rightRole = objects[right.object_id].role === "pointer" ? 1 : 0;
      return leftRole - rightRole;
    });
    var unresolved = pending.slice();
    for (var pass = 0; unresolved.length && pass < pending.length; pass += 1) {
      var next = [];
      unresolved.forEach(function (placement) {
        var object = objects[placement.object_id]; var anchor = result[placement.anchor_id];
        if (!anchor) { next.push(placement); return; }
        var order = anchorOrders[placement.anchor_id] || 0;
        anchorOrders[placement.anchor_id] = order + 1;
        var size = footprint(object, placement);
        var preferred = anchoredBox(anchor, size, order);
        var box = openBox(preferred, size, occupied, order);
        result[object.id] = box;
        if (placement.visible) occupied.push(box);
      });
      if (next.length === unresolved.length) break;
      unresolved = next;
    }
    unresolved.forEach(function (placement, index) {
      var object = objects[placement.object_id]; var size = footprint(object, placement);
      var box = openBox({ x: 50, y: 15 + index * 10 }, size, occupied, index);
      result[object.id] = box;
      if (placement.visible) occupied.push(box);
    });
    // Unanchored pointers are legal while an explanation introduces them.
    // They still need a real box: leaving CSS left/top unset collapses every
    // such pointer into the stage origin and creates an opaque text pile-up.
    var standalone = 0;
    state.placements.forEach(function (placement) {
      var object = objects[placement.object_id];
      if (!object || result[object.id]) return;
      var size = footprint(object, placement);
      var preferred = { x: 12 + (standalone % 4) * 25, y: 13 + Math.floor(standalone / 4) * 12 };
      var box = openBox(preferred, size, occupied, standalone);
      result[object.id] = box;
      if (placement.visible) occupied.push(box);
      standalone += 1;
    });
    return result;
  }

  function relationKey(relation) { return [relation.source_id, relation.target_id].join("|"); }
  function relations(scene) {
    var keys = [];
    scene.program.states.forEach(function (state) { state.relations.forEach(function (relation) { var key = relationKey(relation); if (!keys.includes(key)) keys.push(key); }); });
    return keys.sort();
  }
  function relationGeometry(boxes, key) {
    var parts = key.split("|"); var source = boxes[parts[0]]; var target = boxes[parts[1]];
    if (!source || !target) return null;
    var dx = target.x - source.x; var dy = target.y - source.y;
    var distance = Math.max(Math.abs(dx), Math.abs(dy), 1);
    return { x1: source.x + dx * Math.min(0.4, source.w / distance * 0.45), y1: source.y + dy * Math.min(0.4, source.h / distance * 0.45),
      x2: target.x - dx * Math.min(0.4, target.w / distance * 0.45), y2: target.y - dy * Math.min(0.4, target.h / distance * 0.45) };
  }

  function textVars(node, text, box) {
    var label = node.querySelector(".entity-label");
    var role = node.dataset.role;
    if (role === "pointer") return {};
    var available = Math.max(72, (box.w / 100) * 1744 - 36);
    var availableHeight = Math.max(28, (box.h / 100) * 738 - (role === "node" ? 14 : 28));
    var labelUnits = textUnits(label.textContent || "");
    var valueUnits = textUnits(text);
    var widest = Math.max(labelUnits, valueUnits, 1);
    var labelSize = clamp(Math.floor(available / widest * 0.92), 10, 23);
    labelSize = Math.min(labelSize, Math.max(10, Math.floor(availableHeight / (text ? 3.1 : 1.25))));
    return {
      "--entity-label-size": labelSize + "px",
      "--entity-value-size": clamp(Math.floor(labelSize * 0.72), 10, 16) + "px"
    };
  }
  function content(scene, state, boxes, timeline, at) {
    state.placements.forEach(function (placement) {
      var node = byId("entity-" + scene.id + "-" + placement.object_id); if (!node) return;
      var value = node.querySelector(".entity-value");
      var text = placement.value || "";
      var styles = textVars(node, text, boxes[placement.object_id] || { w: 20 });
      if (timeline) {
        timeline.set(value, { textContent: text, display: text ? "block" : "none" }, at);
        timeline.set(node, Object.assign({ attr: { "data-status": placement.status } }, styles), at);
      } else {
        value.textContent = text;
        value.style.display = text ? "block" : "none";
        node.dataset.status = placement.status;
        Object.keys(styles).forEach(function (name) { node.style.setProperty(name, styles[name]); });
      }
    });
  }
  function vars(box, placement, focus) {
    return { left: box.x + "%", top: box.y + "%", width: box.w + "%", height: box.h + "%", xPercent: -50, yPercent: -50, autoAlpha: placement.visible ? 1 : 0, scale: focus ? 1.06 : 1 };
  }
  function setRelations(scene, state, boxes, timeline, at, duration) {
    var active = new Set(state.relations.map(relationKey));
    relations(scene).forEach(function (key, index) {
      var group = byId("relation-" + scene.id + "-" + index); if (!group) return;
      var shape = relationGeometry(boxes, key); var visible = active.has(key) && shape;
      var line = group.querySelector("line"); var head = group.querySelector("circle");
      if (shape) { timeline.set(line, { attr: { x1: shape.x1, y1: shape.y1, x2: shape.x2, y2: shape.y2 } }, at); timeline.set(head, { attr: { cx: shape.x2, cy: shape.y2 } }, at); }
      timeline.to(group, { autoAlpha: visible ? 1 : 0, duration: Math.min(0.38, duration * 0.3), ease: "power1.out" }, at);
    });
  }
  function setState(scene, state) {
    var boxes = layout(scene, state); content(scene, state, boxes);
    state.placements.forEach(function (placement) { var node = byId("entity-" + scene.id + "-" + placement.object_id); if (node && boxes[placement.object_id]) window.gsap.set(node, vars(boxes[placement.object_id], placement, placement.status === "active")); });
    var active = new Set(state.relations.map(relationKey));
    relations(scene).forEach(function (key, index) {
      var group = byId("relation-" + scene.id + "-" + index); var shape = relationGeometry(boxes, key);
      if (!group) return;
      if (shape) {
        var line = group.querySelector("line"); var head = group.querySelector("circle");
        line.setAttribute("x1", shape.x1); line.setAttribute("y1", shape.y1); line.setAttribute("x2", shape.x2); line.setAttribute("y2", shape.y2);
        head.setAttribute("cx", shape.x2); head.setAttribute("cy", shape.y2);
      }
      window.gsap.set(group, { autoAlpha: active.has(key) && shape ? 1 : 0 });
    });
  }
  function tweenState(scene, beat, after, timeline, at, duration) {
    var boxes = layout(scene, after); content(scene, after, boxes, timeline, at);
    var action = beat.actions[0];
    after.placements.forEach(function (placement) {
      var node = byId("entity-" + scene.id + "-" + placement.object_id); var box = boxes[placement.object_id]; if (!node || !box) return;
      var focused = action.subject_id === placement.object_id || action.target_id === placement.object_id;
      var verb = focused ? action.verb : "settle";
      var motion = vars(box, placement, focused);
      if (verb === "reveal") { motion.scale = focused ? 1.08 : 1; motion.duration = duration * 0.62; motion.ease = "back.out(1.7)"; }
      else if (verb === "traverse" || verb === "move" || verb === "place" || verb === "remove") { motion.duration = duration; motion.ease = "power3.inOut"; }
      else if (verb === "compare") { motion.duration = duration * 0.72; motion.ease = "elastic.out(1,0.55)"; }
      else { motion.duration = duration * 0.65; motion.ease = "power2.out"; }
      timeline.to(node, motion, at);
      if (focused && (verb === "traverse" || verb === "compare" || verb === "focus")) timeline.to(node, { scale: 1.1, duration: duration * 0.3, yoyo: true, repeat: 1, ease: "sine.inOut" }, at + duration * 0.38);
    });
    setRelations(scene, after, boxes, timeline, at + duration * 0.2, duration);
  }

  function tween(scene, beat, timeline, at, duration) {
    var states = beat.action_state_ids;
    var segment = duration / states.length;
    states.forEach(function (stateId, index) {
      var actionBeat = {
        actions: [beat.actions[index]]
      };
      var next = stateById(scene, stateId);
      tweenState(scene, actionBeat, next, timeline, at + segment * index, segment);
    });
  }

  function mount(payload) {
    if (!window.gsap) throw new Error("GSAP failed to load");
    var timeline = window.gsap.timeline({ paused: true }); var scenes = sceneById(payload); var windows = {};
    payload.beats.forEach(function (item) { var range = windows[item.scene_id] || { start: item.start_ms, end: item.end_ms }; range.start = Math.min(range.start, item.start_ms); range.end = Math.max(range.end, item.end_ms); windows[item.scene_id] = range; });
    payload.scenes.forEach(function (scene) {
      var node = byId("scene-" + scene.id); var range = windows[scene.id]; var startsAtZero = range.start === 0;
      setState(scene, stateById(scene, scene.program.beats[0].before_state_id));
      window.gsap.set(node, { autoAlpha: startsAtZero ? 1 : 0 });
      if (!startsAtZero) timeline.set(node, { autoAlpha: 1 }, range.start / 1000);
      timeline.set(node, { autoAlpha: 0 }, range.end / 1000);
    });
    payload.beats.forEach(function (timed) { var scene = scenes[timed.scene_id]; var beat = scene.program.beats.find(function (item) { return item.id === timed.beat_id; }); var start = timed.start_ms / 1000; var at = start + Math.min(0.72, timed.duration_ms / 1000 * 0.13); var duration = Math.min(3.0, Math.max(1.05, timed.duration_ms / 1000 * 0.44)); tween(scene, beat, timeline, at, duration); });
    payload.captions.forEach(function (cue, index) { var node = byId("caption-" + index); if (node) { timeline.set(node, { autoAlpha: 1 }, cue.start_ms / 1000); timeline.set(node, { autoAlpha: 0 }, cue.end_ms / 1000); } });
    timeline.fromTo(byId("progress-fill"), { scaleX: 0 }, { scaleX: 1, duration: payload.duration_ms / 1000, ease: "none" }, 0);
    timeline.to({}, { duration: payload.duration_ms / 1000 }, 0);
    return timeline;
  }
  window.CartoonRuntime = { mount: mount };
}());
