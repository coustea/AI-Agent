(function () {
  "use strict"

  const SVG_NS = "http://www.w3.org/2000/svg"
  const q = (selector, root = document) => root.querySelector(selector)
  const qa = (selector, root = document) => Array.from(root.querySelectorAll(selector))

  const edgeKey = (edge) => edge ? edge.dataset.edge || `${edge.dataset.source}:${edge.dataset.target}` : ""

  function ensureSvgAssets(svg) {
    if (!svg || q("defs[data-cartoon-defs]", svg)) return

    const defs = document.createElementNS(SVG_NS, "defs")
    defs.dataset.cartoonDefs = "true"

    const marker = document.createElementNS(SVG_NS, "marker")
    marker.id = "cartoon-arrow"
    marker.setAttribute("viewBox", "0 0 10 10")
    marker.setAttribute("refX", "8.6")
    marker.setAttribute("refY", "5")
    marker.setAttribute("markerWidth", "7")
    marker.setAttribute("markerHeight", "7")
    marker.setAttribute("orient", "auto-start-reverse")
    marker.setAttribute("markerUnits", "strokeWidth")

    const arrow = document.createElementNS(SVG_NS, "path")
    arrow.setAttribute("d", "M 0 0 L 10 5 L 0 10 z")
    arrow.setAttribute("fill", "context-stroke")
    marker.appendChild(arrow)
    defs.appendChild(marker)
    svg.prepend(defs)
  }

  function ensureEdgeLabels(scene) {
    const svg = q(".visual-edges", scene)
    if (!svg) return
    ensureSvgAssets(svg)

    const existing = new Map(
      qa(".visual-edge-label", svg).map((label) => [label.dataset.edgeLabelFor, label])
    )

    qa(".visual-edge", svg).forEach((edge) => {
      const labelText = String(edge.dataset.label || "").trim()
      if (!labelText) return
      const key = edgeKey(edge)
      if (existing.has(key)) return

      const text = document.createElementNS(SVG_NS, "text")
      text.classList.add("visual-edge-label")
      if (edge.classList.contains("is-future")) text.classList.add("is-future")
      text.dataset.edgeLabelFor = key
      text.textContent = labelText
      svg.appendChild(text)
      existing.set(key, text)
    })
  }

  function labelForEdge(scene, edge) {
    const svg = q(".visual-edges", scene)
    if (!svg || !edge) return null
    const key = edgeKey(edge)
    return qa(".visual-edge-label", svg).find((label) => label.dataset.edgeLabelFor === key) || null
  }

  function rectCenter(rect, base) {
    return {
      x: rect.left - base.left + rect.width / 2,
      y: rect.top - base.top + rect.height / 2
    }
  }

  function boundaryPoint(fromRect, toRect, base) {
    const from = rectCenter(fromRect, base)
    const to = rectCenter(toRect, base)
    const dx = to.x - from.x
    const dy = to.y - from.y
    const halfWidth = Math.max(1, fromRect.width / 2)
    const halfHeight = Math.max(1, fromRect.height / 2)
    const scale = 1 / Math.max(Math.abs(dx) / halfWidth, Math.abs(dy) / halfHeight, 1)
    return {
      x: from.x + dx * scale,
      y: from.y + dy * scale
    }
  }

  function drawEdges(scene) {
    const svg = q(".visual-edges", scene)
    if (!svg) return
    ensureSvgAssets(svg)
    ensureEdgeLabels(scene)

    const base = svg.getBoundingClientRect()
    const nodesById = new Map(qa("[data-node]", scene).map((item) => [item.dataset.node, item]))
    qa(".visual-edge", scene).forEach((edge) => {
      const source = nodesById.get(edge.dataset.source)
      const target = nodesById.get(edge.dataset.target)
      if (!source || !target) return

      const sourceRect = source.getBoundingClientRect()
      const targetRect = target.getBoundingClientRect()
      const from = boundaryPoint(sourceRect, targetRect, base)
      const to = boundaryPoint(targetRect, sourceRect, base)

      edge.setAttribute("x1", from.x.toFixed(2))
      edge.setAttribute("y1", from.y.toFixed(2))
      edge.setAttribute("x2", to.x.toFixed(2))
      edge.setAttribute("y2", to.y.toFixed(2))

      const label = labelForEdge(scene, edge)
      if (label) {
        const midX = (from.x + to.x) / 2
        const midY = (from.y + to.y) / 2
        const normalLength = Math.hypot(to.x - from.x, to.y - from.y) || 1
        const offsetX = -(to.y - from.y) / normalLength * 12
        const offsetY = (to.x - from.x) / normalLength * 12
        label.setAttribute("x", (midX + offsetX).toFixed(2))
        label.setAttribute("y", (midY + offsetY).toFixed(2))
      }
    })
  }

  function edgeLength(edge) {
    try {
      return Math.max(1, edge.getTotalLength())
    } catch (_) {
      const x1 = Number(edge.getAttribute("x1") || 0)
      const y1 = Number(edge.getAttribute("y1") || 0)
      const x2 = Number(edge.getAttribute("x2") || 0)
      const y2 = Number(edge.getAttribute("y2") || 0)
      return Math.max(1, Math.hypot(x2 - x1, y2 - y1))
    }
  }

  function revealEdges(tl, scene, edges, time, duration) {
    edges.forEach((edge, index) => {
      const at = time + index * 0.06
      tl.set(edge, { visibility: "visible", opacity: 0 }, at)
      tl.to(edge, {
        opacity: 1,
        duration: Math.max(0.2, duration - index * 0.03),
        ease: "power2.out"
      }, at)

      const label = labelForEdge(scene, edge)
      if (label) {
        tl.set(label, { visibility: "visible", opacity: 0 }, at)
        tl.to(label, {
          opacity: 1,
          duration: 0.2,
          ease: "power1.out"
        }, at + Math.min(0.2, duration * 0.55))
      }
    })
  }

  function hideEdges(tl, scene, edges, time, duration) {
    edges.forEach((edge) => {
      const label = labelForEdge(scene, edge)
      tl.to(edge, {
        opacity: 0,
        duration,
        ease: "power1.in"
      }, time)
      tl.set(edge, { visibility: "hidden" }, time + duration)
      if (label) {
        tl.to(label, {
          opacity: 0,
          duration: Math.min(duration, 0.18),
          ease: "power1.in"
        }, time)
        tl.set(label, { visibility: "hidden" }, time + Math.min(duration, 0.18))
      }
    })
  }

  function intensityScale(intensity) {
    if (intensity === "strong") return 1.08
    if (intensity === "subtle") return 1.025
    return 1.05
  }

  function pulseTargets(tl, targets, time, duration, options = {}) {
    if (!targets.length) return
    const scale = options.scale || 1.05
    const lift = options.lift == null ? -4 : options.lift
    const half = Math.max(0.12, duration * 0.43)

    tl.to(targets, {
      scale,
      y: lift,
      duration: half,
      stagger: targets.length > 1 ? 0.05 : 0,
      ease: "power2.out"
    }, time)
    tl.to(targets, {
      scale: 1,
      y: 0,
      duration: Math.max(0.14, duration - half),
      stagger: targets.length > 1 ? 0.04 : 0,
      ease: "power1.out"
    }, time + half)
  }

  function flowEdges(tl, edges, time, duration) {
    edges.forEach((edge, index) => {
      const at = time + index * 0.05
      tl.set(edge, { visibility: "visible", opacity: 1 }, at)
      tl.to(edge, {
        opacity: 0.34,
        duration: Math.max(0.16, duration * 0.38),
        ease: "power1.inOut"
      }, at)
      tl.to(edge, {
        opacity: 1,
        duration: Math.max(0.18, duration * 0.42),
        ease: "power1.out"
      }, at + Math.max(0.18, duration * 0.46))
    })
  }

  function prepareScene(scene) {
    ensureEdgeLabels(scene)
    drawEdges(scene)

    qa(".visual-node", scene).forEach((item) => {
      if (item.classList.contains("is-future") || item.dataset.initialVisible === "false") {
        gsap.set(item, { visibility: "hidden", opacity: 0, scale: 0.78, y: 12 })
      } else {
        gsap.set(item, { visibility: "visible", opacity: 1, scale: 1, x: 0, y: 0 })
      }
    })

    qa(".visual-edge", scene).forEach((edge) => {
      const label = labelForEdge(scene, edge)
      if (edge.classList.contains("is-future")) {
        gsap.set(edge, { visibility: "hidden", opacity: 0 })
        if (label) gsap.set(label, { visibility: "hidden", opacity: 0 })
      } else {
        gsap.set(edge, { visibility: "visible", opacity: 1 })
        if (label) gsap.set(label, { visibility: "visible", opacity: 1 })
      }
    })
  }

  window.Runtime = {
    prepare() {
      qa(".teaching-scene").forEach(prepareScene)
      qa(".caption").forEach((caption) => gsap.set(caption, { visibility: "hidden", opacity: 0, y: 10 }))
      qa("[data-step-summary]").forEach((summary) => gsap.set(summary, { visibility: "hidden", opacity: 0, x: 14 }))
      window.addEventListener("resize", () => qa(".teaching-scene").forEach(drawEdges), { passive: true })
    },

    progress(tl, selector, time, duration) {
      tl.to(selector, {
        width: "100%",
        duration,
        ease: "none"
      }, time)
    },

    sceneIn(tl, scene, time, duration) {
      if (!scene) return
      const header = q('[data-slot="header"]', scene)
      const stage = q('[data-slot="stage"]', scene)
      const rail = q('[data-slot="state-rail"]', scene)
      const panel = q('[data-slot="teaching-panel"]', scene)

      tl.set(scene, { visibility: "visible" }, time)
      tl.fromTo(scene, { opacity: 0 }, {
        opacity: 1,
        duration,
        ease: "power2.out"
      }, time)
      if (header) {
        tl.fromTo(header, { opacity: 0, y: -10 }, {
          opacity: 1,
          y: 0,
          duration: Math.max(0.24, duration),
          ease: "power2.out"
        }, time + 0.03)
      }
      if (stage) {
        tl.fromTo(stage, { opacity: 0, scale: 0.992 }, {
          opacity: 1,
          scale: 1,
          duration: Math.max(0.28, duration + 0.06),
          ease: "power2.out"
        }, time + 0.04)
      }
      if (rail) {
        tl.fromTo(rail, { opacity: 0, x: 8 }, {
          opacity: 1,
          x: 0,
          duration: 0.24,
          ease: "power1.out"
        }, time + 0.12)
      }
      if (panel) {
        tl.fromTo(panel, { opacity: 0, x: 12 }, {
          opacity: 1,
          x: 0,
          duration: Math.max(0.26, duration + 0.04),
          ease: "power2.out"
        }, time + 0.08)
      }
    },

    sceneOut(tl, scene, time, duration) {
      if (!scene) return
      tl.to(scene, {
        opacity: 0,
        duration,
        ease: "power1.in"
      }, time)
      tl.set(scene, { visibility: "hidden" }, time + duration)
    },

    step(tl, scene, index, time) {
      if (!scene) return
      const chips = qa("[data-step-chip]", scene)
      const active = chips[index]
      const done = chips.slice(0, index)
      const pending = chips.slice(index + 1)
      const summaries = qa("[data-step-summary]", scene)
      const activeSummary = summaries[index]
      const inactiveSummaries = summaries.filter((summary) => summary !== activeSummary)

      tl.call(() => {
        chips.forEach((chip, chipIndex) => {
          chip.classList.toggle("is-active", chipIndex === index)
          chip.classList.toggle("is-done", chipIndex < index)
        })
      }, null, time)

      if (chips.length) {
        tl.to(chips, {
          scale: 1,
          opacity: 0.48,
          duration: 0.14,
          ease: "power1.out"
        }, time)
      }

      if (done.length) {
        tl.to(done, {
          opacity: 0.74,
          duration: 0.14,
          ease: "power1.out"
        }, time + 0.01)
      }

      if (pending.length) {
        tl.to(pending, {
          opacity: 0.48,
          duration: 0.14,
          ease: "power1.out"
        }, time + 0.01)
      }

      if (active) {
        tl.fromTo(active, {
          scale: 0.75,
          opacity: 0.72
        }, {
          scale: 1.12,
          opacity: 1,
          duration: 0.24,
          ease: "back.out(2.2)"
        }, time)
        tl.to(active, {
          scale: 1,
          duration: 0.16,
          ease: "power1.out"
        }, time + 0.24)
      }

      if (inactiveSummaries.length) {
        tl.to(inactiveSummaries, {
          opacity: 0,
          x: -8,
          duration: 0.16,
          ease: "power1.in"
        }, time)
        tl.set(inactiveSummaries, { visibility: "hidden" }, time + 0.16)
      }

      if (activeSummary) {
        tl.set(activeSummary, { visibility: "visible" }, time + 0.02)
        tl.fromTo(activeSummary, {
          opacity: 0,
          x: 14
        }, {
          opacity: 1,
          x: 0,
          duration: 0.28,
          ease: "power2.out"
        }, time + 0.04)
      }
    },

    action(tl, refs, payload, time) {
      const scene = refs.scene
      if (!scene) return

      const targets = refs.targets || []
      const duration = Math.max(0.2, Number(payload.duration) || 0.7)
      const scale = intensityScale(payload.intensity)
      const activeEdges = refs.edges || []

      if (payload.kind === "reveal" || payload.kind === "insert") {
        tl.set(targets, { visibility: "visible" }, time)
        tl.to(targets, {
          opacity: 1,
          scale: 1,
          x: 0,
          y: 0,
          duration,
          stagger: targets.length > 1 ? 0.08 : 0,
          ease: "back.out(1.5)"
        }, time)
        return
      }

      if (payload.kind === "remove") {
        tl.to(targets, {
          opacity: 0,
          scale: 0.72,
          duration,
          stagger: targets.length > 1 ? 0.05 : 0,
          ease: "power2.in"
        }, time)
        tl.set(targets, { visibility: "hidden" }, time + duration)
        return
      }

      if (payload.kind === "connect") {
        revealEdges(tl, scene, activeEdges, time, duration)
        return
      }

      if (payload.kind === "transfer") {
        flowEdges(tl, activeEdges, time + 0.06, Math.max(0.28, duration * 0.82))
        const source = refs.source
        const destination = refs.destination
        pulseTargets(tl, [source].filter(Boolean), time, Math.min(0.42, duration * 0.42), {
          scale: 1.035,
          border: "var(--flow)",
          ring: "0 0 0 6px rgba(2, 132, 199, 0.11)"
        })
        if (destination) {
          pulseTargets(tl, [destination], time + Math.max(0.18, duration * 0.62), Math.max(0.22, duration * 0.32), {
            scale: 1.055,
            border: "var(--success)",
            ring: "0 0 0 7px rgba(21, 128, 61, 0.11)"
          })
        }
        return
      }

      if (payload.kind === "traverse") {
        const perTarget = Math.max(0.18, duration / Math.max(1, targets.length))
        targets.forEach((target, index) => {
          pulseTargets(tl, [target], time + index * perTarget, perTarget * 0.86, {
            scale,
            border: "var(--flow)",
            ring: "0 0 0 6px rgba(2, 132, 199, 0.11)"
          })
        })
        flowEdges(tl, activeEdges, time, duration)
        return
      }

      if (payload.kind === "compare") {
        pulseTargets(tl, targets, time, duration, {
          scale,
          border: "var(--state)",
          ring: "0 0 0 7px rgba(49, 93, 220, 0.11)"
        })
        return
      }

      if (payload.kind === "mutate") {
        tl.to(targets, {
          x: -7,
          scale: 1.035,
          duration: Math.max(0.12, duration * 0.22),
          ease: "power1.inOut"
        }, time)
        tl.to(targets, {
          x: 7,
          scale: 1.055,
          duration: Math.max(0.12, duration * 0.22),
          ease: "power1.inOut"
        }, time + Math.max(0.12, duration * 0.22))
        tl.to(targets, {
          x: 0,
          scale: 1,
          duration: Math.max(0.18, duration * 0.34),
          ease: "power1.out"
        }, time + Math.max(0.24, duration * 0.52))
        return
      }

      if (payload.kind === "focus") {
        const others = qa(".visual-node", scene).filter((item) => !targets.includes(item))
        tl.to(others, {
          opacity: 0.26,
          duration: 0.2,
          ease: "power1.out"
        }, time)
        pulseTargets(tl, targets, time + 0.03, Math.max(0.24, duration * 0.66), { scale })
        tl.to(others, {
          opacity: 1,
          duration: 0.22,
          ease: "power1.out"
        }, time + Math.max(0.3, duration - 0.22))
        return
      }

      pulseTargets(tl, targets, time, duration, { scale })
    },

    patch(tl, refs, patch, time) {
      const scene = refs.scene
      if (!scene) return
      const target = refs.target
      const duration = 0.24

      if (patch.op === "add_node" && patch.node) {
        const added = refs.target
        if (added) {
          tl.set(added, { visibility: "visible" }, time)
          tl.to(added, {
            opacity: 1,
            scale: 1,
            x: 0,
            y: 0,
            duration: 0.42,
            ease: "back.out(1.6)"
          }, time)
        }
      } else if (patch.op === "remove_node" && target) {
        tl.to(target, {
          opacity: 0,
          scale: 0.72,
          duration: 0.32,
          ease: "power2.in"
        }, time)
        tl.set(target, { visibility: "hidden" }, time + 0.32)
      } else if (patch.op === "set_label" && target) {
        const label = q("strong", target)
        if (label) {
          tl.to(label, {
            opacity: 0,
            y: -6,
            duration: 0.12,
            ease: "power1.in"
          }, time)
          tl.call(() => {
            label.textContent = String(patch.value ?? "")
          }, null, time + 0.12)
          tl.to(label, {
            opacity: 1,
            y: 0,
            duration: 0.18,
            ease: "power2.out"
          }, time + 0.13)
        }
      } else if (patch.op === "set_state" && target) {
        tl.call(() => {
          target.dataset.state = String(patch.value ?? "idle")
        }, null, time)
        pulseTargets(tl, [target], time + 0.02, 0.38, {
          scale: 1.055,
          border: "var(--state)",
          ring: "0 0 0 7px rgba(49, 93, 220, 0.11)"
        })
      } else if (patch.op === "set_value" && target) {
        let value = q("[data-node-value]", target)
        if (!value) {
          value = document.createElement("em")
          value.dataset.nodeValue = ""
          target.appendChild(value)
        }
        tl.to(value, {
          opacity: 0,
          scale: 0.72,
          duration: 0.1,
          ease: "power1.in"
        }, time)
        tl.call(() => {
          value.textContent = String(patch.value ?? "")
        }, null, time + 0.1)
        tl.to(value, {
          opacity: 1,
          scale: 1,
          duration: 0.2,
          ease: "back.out(1.8)"
        }, time + 0.11)
      } else if (patch.op === "add_edge" && patch.edge) {
        revealEdges(tl, scene, refs.edges || [], time, 0.38)
      } else if (patch.op === "remove_edge" && patch.edge) {
        hideEdges(tl, scene, refs.edges || [], time, duration)
      }
    },

    caption(tl, caption, time, duration) {
      const exitAt = time + Math.max(0.44, duration - 0.24)
      if (!caption) return
      tl.fromTo(caption, {
        visibility: "visible",
        opacity: 0,
        y: 10,
        scale: 0.992
      }, {
        visibility: "visible",
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.22,
        ease: "power2.out"
      }, time)
      tl.to(caption, {
        opacity: 0,
        y: -8,
        duration: 0.18,
        ease: "power1.in"
      }, exitAt)
      tl.set(caption, { visibility: "hidden" }, exitAt + 0.18)
    }
  }
})()
