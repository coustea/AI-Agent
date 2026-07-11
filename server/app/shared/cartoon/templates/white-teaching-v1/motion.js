(function () {
  const q = (selector, root = document) => root.querySelector(selector)
  const qa = (selector, root = document) => Array.from(root.querySelectorAll(selector))
  const node = (scene, id) => q(`[data-node="${CSS.escape(id)}"]`, scene)
  const edgesFor = (scene, edge) => qa(".visual-edges line", scene).filter((line) => line.dataset.source === edge.source_id && line.dataset.target === edge.target_id)

  function drawEdges(scene) {
    qa(".visual-edges line", scene).forEach((edge) => {
      const svg = edge.ownerSVGElement
      const source = node(scene, edge.dataset.source)
      const target = node(scene, edge.dataset.target)
      if (!svg || !source || !target) return
      const base = svg.getBoundingClientRect()
      const from = source.getBoundingClientRect()
      const to = target.getBoundingClientRect()
      edge.setAttribute("x1", `${from.left - base.left + from.width / 2}`)
      edge.setAttribute("y1", `${from.top - base.top + from.height / 2}`)
      edge.setAttribute("x2", `${to.left - base.left + to.width / 2}`)
      edge.setAttribute("y2", `${to.top - base.top + to.height / 2}`)
    })
  }

  window.Runtime = {
    prepare() { qa(".teaching-scene").forEach(drawEdges) },
    progress(tl, selector, time, duration) { tl.to(selector, { width: "100%", duration, ease: "none" }, time) },
    sceneIn(tl, selector, time, duration) { tl.to(selector, { autoAlpha: 1, duration, ease: "power2.out" }, time) },
    sceneOut(tl, selector, time, duration) { tl.to(selector, { autoAlpha: 0, duration, ease: "power1.in" }, time) },
    step(tl, selector, index, time) { tl.call(() => { const scene = q(selector); qa("[data-step-chip]", scene).forEach((chip, i) => chip.classList.toggle("is-active", i === index)); qa("[data-step-chip]", scene).forEach((chip, i) => chip.classList.toggle("is-done", i < index)); }, null, time) },
    action(tl, sceneSelector, payload, time) {
      const scene = q(sceneSelector)
      if (!scene) return
      const targets = payload.targets.map((id) => node(scene, id)).filter(Boolean)
      const duration = payload.duration || .7
      if (payload.kind === "connect") {
        const ids = new Set(payload.targets)
        const edges = qa(".visual-edges line", scene).filter((line) => ids.has(line.dataset.source) && ids.has(line.dataset.target))
        tl.to(edges, { autoAlpha: 1, duration: Math.min(.35, duration), ease: "power2.out" }, time)
      } else if (payload.kind === "reveal" || payload.kind === "insert") tl.to(targets, { autoAlpha: 1, scale: 1, duration, ease: "back.out(1.2)" }, time)
      else if (payload.kind === "remove") tl.to(targets, { autoAlpha: 0, scale: .75, duration, ease: "power2.in" }, time)
      else if (payload.kind === "mutate") tl.to(targets, { backgroundColor: "var(--change-soft)", borderColor: "var(--change)", duration: duration * .45, yoyo: true, repeat: 1 }, time)
      else if (payload.kind === "transfer" || payload.kind === "traverse") tl.to(targets, { x: 18, duration: duration * .42, yoyo: true, repeat: 1, ease: "power2.inOut" }, time)
      else tl.to(targets, { scale: 1.08, borderColor: "var(--focus)", boxShadow: "0 0 0 7px var(--focus-soft)", duration: duration * .45, yoyo: true, repeat: 1 }, time)
      tl.call(() => drawEdges(scene), null, time + duration)
    },
    patch(tl, sceneSelector, patch, time) {
      const scene = q(sceneSelector)
      if (!scene) return
      const target = patch.target_id ? node(scene, patch.target_id) : null
      const duration = .22
      if (patch.op === "add_node" && patch.node) {
        tl.to(node(scene, patch.node.id), { autoAlpha: 1, scale: 1, duration, ease: "back.out(1.2)" }, time)
      } else if (patch.op === "remove_node" && target) {
        tl.to(target, { autoAlpha: 0, scale: .75, duration, ease: "power2.in" }, time)
      } else if (patch.op === "set_label" && target) {
        tl.call(() => { const label = q("strong", target); if (label) label.textContent = String(patch.value ?? "") }, null, time)
      } else if (patch.op === "set_state" && target) {
        tl.call(() => { target.dataset.state = String(patch.value ?? "idle") }, null, time)
      } else if (patch.op === "set_value" && target) {
        tl.call(() => { target.dataset.value = String(patch.value ?? "") }, null, time)
      } else if ((patch.op === "add_edge" || patch.op === "remove_edge") && patch.edge) {
        tl.to(edgesFor(scene, patch.edge), { autoAlpha: patch.op === "add_edge" ? 1 : 0, duration, ease: "power2.out" }, time)
      }
      tl.call(() => drawEdges(scene), null, time + duration)
    },
    caption(tl, selector, time, duration) { tl.to(selector, { autoAlpha: 1, y: 0, duration: .2 }, time); tl.to(selector, { autoAlpha: 0, y: -8, duration: .18 }, time + Math.max(.4, duration - .24)) }
  }
})()
