import type { SlideIntent, PptDocument, ContentElement } from '../model/slideIntent'
import type { ResolvedSlide } from '../model/resolvedSlide'

type CompositionId = ResolvedSlide['composition_id']

// Helper to determine the density weight of each element type
function getElementWeight(el: ContentElement): number {
  switch (el.type) {
    case 'code':
      return 8
    case 'table':
      return 6
    case 'image':
      return 5
    case 'definition':
      return 4
    case 'step':
      return 3
    case 'formula':
      return 3
    case 'quote':
      return 3
    case 'statement':
      return 2
    case 'hierarchy_node':
    case 'state_node':
    case 'sequence_participant':
    case 'process_node':
      return 2
    default:
      return 1.5
  }
}

// Splits a slide if its elements exceed the weight capacity or element count limit (Overflow detection & split)
function splitSlideIfNeeded(slide: SlideIntent): SlideIntent[] {
  if (slide.role === 'cover' || slide.role === 'ending' || slide.role === 'summary') {
    return [slide]
  }

  const maxCapacity = 10
  const maxElements = 5
  const elements = slide.elements || []

  if (elements.length <= 1) {
    return [slide]
  }

  const pages: ContentElement[][] = []
  let currentPage: ContentElement[] = []
  let currentWeight = 0

  for (const el of elements) {
    const w = getElementWeight(el)
    if ((currentWeight + w > maxCapacity || currentPage.length >= maxElements) && currentPage.length > 0) {
      pages.push(currentPage)
      currentPage = [el]
      currentWeight = w
    } else {
      currentPage.push(el)
      currentWeight += w
    }
  }
  if (currentPage.length > 0) {
    pages.push(currentPage)
  }

  if (pages.length <= 1) {
    return [slide]
  }

  return pages.map((pageElements, index) => {
    const suffix = ` (${index + 1}/${pages.length})`
    return {
      ...slide,
      id: `${slide.id}_split_${index}`,
      title: `${slide.title}${suffix}`,
      elements: pageElements,
      relations: (slide.relations || []).filter(rel => {
        const hasSource = pageElements.some(e => e.label === rel.source || e.content === rel.source)
        const hasTarget = pageElements.some(e => e.label === rel.target || e.content === rel.target)
        return hasSource && hasTarget
      }),
      density: 'medium',
    }
  })
}

// Calculate absolute coordinates for elements and slots based on the slide layout
function calculateCoordinates(
  compId: CompositionId,
  slots: Record<string, ContentElement[]>
): Record<string, { left: number; top: number; width: number; height: number }> {
  const coords: Record<string, { left: number; top: number; width: number; height: number }> = {}

  // 1. Assign slot coordinates in standard 1280x720 frame
  if (compId === 'TheoryCover' || compId === 'ChapterSummary' || compId === 'SectionBreak') {
    coords.main = { left: 60, top: 120, width: 1160, height: 480 }
  } else if (compId === 'DefinitionFocus') {
    coords.focus = { left: 60, top: 100, width: 420, height: 520 }
    coords.main = { left: 520, top: 100, width: 700, height: 520 }
  } else if (compId === 'Comparison') {
    coords.left = { left: 60, top: 100, width: 550, height: 520 }
    coords.right = { left: 670, top: 100, width: 550, height: 520 }
  } else if (compId === 'CauseEffect') {
    coords.cause = { left: 60, top: 100, width: 550, height: 520 }
    coords.effect = { left: 670, top: 100, width: 550, height: 520 }
  } else if (compId === 'WorkedExample') {
    coords.code = { left: 60, top: 100, width: 680, height: 520 }
    coords.explanation = { left: 780, top: 100, width: 440, height: 520 }
  } else {
    coords.main = { left: 60, top: 100, width: 1160, height: 520 }
  }

  // 2. Assign coordinates to individual elements within slots
  for (const [slotName, elements] of Object.entries(slots)) {
    const slotCoord = coords[slotName]
    if (!slotCoord || elements.length === 0) continue

    if (elements.length === 1 && elements[0]) {
      coords[elements[0].label || elements[0].content || `el-${elements[0].type}-0`] = { ...slotCoord }
    } else {
      const gap = 16
      const totalGaps = (elements.length - 1) * gap
      const availableHeight = slotCoord.height - totalGaps
      const itemHeight = Math.max(40, availableHeight / elements.length)

      elements.forEach((el, idx) => {
        coords[el.label || el.content || `el-${el.type}-${idx}`] = {
          left: slotCoord.left,
          top: slotCoord.top + idx * (itemHeight + gap),
          width: slotCoord.width,
          height: itemHeight,
        }
      })
    }
  }

  return coords
}

export function resolveSlide(
  slide: SlideIntent,
  index: number,
  themeId: PptDocument['theme_id'],
  prevCompositionId: CompositionId | null = null
): ResolvedSlide {
  const role = slide.role
  const elements = slide.elements || []
  const relations = slide.relations || []

  // 1. Determine Composition
  let composition_id: CompositionId = 'ConceptBreakdown'

  if (role === 'cover') {
    composition_id = 'TheoryCover'
  } else if (role === 'ending' || role === 'summary') {
    composition_id = 'ChapterSummary'
  } else if (role === 'section' || role === 'roadmap' || role === 'objectives' || role === 'prerequisite') {
    composition_id = 'SectionBreak'
  } else {
    // Score all compositions based on semantic roles, elements, and relations
    const scores: Record<CompositionId, number> = {
      TheoryCover: 0,
      SectionBreak: 0,
      DefinitionFocus: 1,
      ConceptBreakdown: 2, // Default concept fallback
      HierarchyMap: 1,
      ComponentArchitecture: 1,
      StateTransition: 1,
      SequenceTimeline: 1,
      DataFlow: 1,
      ProtocolStack: 1,
      AlgorithmProcess: 1,
      Comparison: 1,
      CauseEffect: 1,
      WorkedExample: 1,
      KnowledgeMap: 1,
      ChapterSummary: 0,
    }

    const hasRelation = (type: string) => relations.some(r => r.type === type)
    const hasElement = (type: string) => elements.some(e => e.type === type)

    // Check relations
    if (hasRelation('parent_child')) {
      scores.HierarchyMap += 10
      scores.KnowledgeMap += 5
    }
    if (hasRelation('transition') || hasElement('state_node')) {
      scores.StateTransition += 12
    }
    if (hasRelation('sequence') || hasElement('sequence_participant')) {
      scores.SequenceTimeline += 12
    }
    if (hasRelation('data_flow') || hasElement('process_node')) {
      scores.DataFlow += 12
    }
    if (hasRelation('comparison')) {
      scores.Comparison += 12
    }
    if (hasRelation('cause_effect')) {
      scores.CauseEffect += 12
    }
    if (hasRelation('dependency')) {
      scores.ComponentArchitecture += 8
      scores.ProtocolStack += 4
    }
    if (hasRelation('association')) {
      scores.KnowledgeMap += 6
      scores.ConceptBreakdown += 3
    }

    // Check elements
    if (hasElement('code') || hasElement('formula')) {
      scores.WorkedExample += 12
    }
    if (hasElement('definition')) {
      scores.DefinitionFocus += 10
    }
    if (hasElement('step')) {
      scores.AlgorithmProcess += 10
    }

    // Check specific roles
    if (role === 'definition') scores.DefinitionFocus += 15
    if (role === 'concept') scores.ConceptBreakdown += 15
    if (role === 'hierarchy' || role === 'concept_relation') scores.HierarchyMap += 15
    if (role === 'architecture' || role === 'architecture_diagram') scores.ComponentArchitecture += 15
    if (role === 'state_transition') scores.StateTransition += 15
    if (role === 'sequence') scores.SequenceTimeline += 15
    if (role === 'data_flow') scores.DataFlow += 15
    if (role === 'process' || role === 'process_demo') scores.AlgorithmProcess += 15
    if (role === 'comparison' || role === 'concept_compare') scores.Comparison += 15
    if (role === 'cause_effect') scores.CauseEffect += 15
    if (role === 'worked_example' || role === 'code_walkthrough' || role === 'algorithm_visualization') {
      scores.WorkedExample += 15
    }
    if (role === 'misconception') {
      scores.DefinitionFocus += 10
    }

    // ProtocolStack Specific scoring paths
    if (role === 'protocol_stack') {
      scores.ProtocolStack += 20
    }
    // Check if element has "layer", "stack", "protocol" in label or title
    const hasProtocolKeyword = elements.some(e => {
      const txt = (e.content || e.label || '').toLowerCase()
      return txt.includes('layer') || txt.includes('stack') || txt.includes('protocol') || txt.includes('osi') || txt.includes('tcp')
    })
    if (hasProtocolKeyword) {
      scores.ProtocolStack += 12
    }

    // KnowledgeMap Specific scoring paths
    if (role === 'knowledge_map') {
      scores.KnowledgeMap += 20
    }
    const hasKnowledgeKeyword = elements.some(e => {
      const txt = (e.content || e.label || '').toLowerCase()
      return txt.includes('knowledge') || txt.includes('map') || txt.includes('overview') || txt.includes('outline')
    })
    if (hasKnowledgeKeyword) {
      scores.KnowledgeMap += 12
    }
    if (elements.filter(e => e.type === 'concept').length >= 3) {
      scores.KnowledgeMap += 8
    }

    // Rank candidates
    const candidates = Object.entries(scores)
      .map(([compId, score]) => ({ compId: compId as CompositionId, score }))
      .sort((a, b) => b.score - a.score)

    if (candidates[0]) {
      composition_id = candidates[0].compId
    }

    // Front-back adjacent deduplication: If composition_id is the same as previous slide,
    // fallback to the second-highest score candidate if its score is positive.
    if (
      prevCompositionId &&
      composition_id === prevCompositionId &&
      composition_id !== 'TheoryCover' &&
      composition_id !== 'ChapterSummary' &&
      composition_id !== 'SectionBreak'
    ) {
      if (candidates[1] && candidates[1].score > 0) {
        composition_id = candidates[1].compId
      }
    }
  }

  // 2. Perform element slot routing based on Composition
  const slots: Record<string, ContentElement[]> = {}

  if (composition_id === 'TheoryCover' || composition_id === 'ChapterSummary' || composition_id === 'SectionBreak') {
    slots.main = elements
  } else if (composition_id === 'DefinitionFocus') {
    slots.focus = elements.filter(e => e.type === 'definition' || e.type === 'concept')
    slots.main = elements.filter(e => e.type !== 'definition' && e.type !== 'concept')
    if (slots.focus.length === 0 && elements.length > 0 && elements[0]) {
      slots.focus = [elements[0]]
      slots.main = elements.slice(1)
    }
  } else if (composition_id === 'Comparison') {
    const half = Math.ceil(elements.length / 2)
    slots.left = elements.slice(0, half)
    slots.right = elements.slice(half)
  } else if (composition_id === 'CauseEffect') {
    slots.cause = elements.filter(e => e.label === 'cause' || e.type === 'statement')
    slots.effect = elements.filter(e => e.label === 'effect' || e.type === 'definition' || e.type === 'concept')
    if (slots.cause.length === 0) {
      const half = Math.ceil(elements.length / 2)
      slots.cause = elements.slice(0, half)
      slots.effect = elements.slice(half)
    }
  } else if (composition_id === 'WorkedExample') {
    slots.code = elements.filter(e => e.type === 'code' || e.type === 'formula')
    slots.explanation = elements.filter(e => e.type !== 'code' && e.type !== 'formula')
    if (slots.code.length === 0 && elements.length > 0 && elements[0]) {
      slots.code = [elements[0]]
      slots.explanation = elements.slice(1)
    }
  } else {
    slots.main = elements
  }

  const speaker_notes = slide.visual_hints?.speaker_notes || `接下来我们讲解：${slide.title}。其核心要点是：${slide.key_message}`
  const coordinates = calculateCoordinates(composition_id, slots)

  return {
    id: slide.id,
    index,
    role,
    title: slide.title,
    key_message: slide.key_message,
    theme_id: themeId,
    composition_id,
    elements,
    relations,
    density: slide.density,
    slots,
    speaker_notes,
    coordinates,
  }
}

export function resolveDocument(doc: PptDocument): ResolvedSlide[] {
  // 1. Density analysis & page splitting
  const slides: SlideIntent[] = []
  for (const slide of doc.slides) {
    slides.push(...splitSlideIfNeeded(slide))
  }

  // 2. Rhythm planning adjustments
  if (slides.length > 0) {
    const firstSlide = slides[0]
    const lastSlide = slides[slides.length - 1]
    if (firstSlide && firstSlide.role !== 'cover') {
      firstSlide.role = 'cover'
    }
    if (lastSlide && lastSlide.role !== 'ending' && lastSlide.role !== 'summary') {
      lastSlide.role = 'ending'
    }
  }

  // 3. Resolve each slide one by one, keeping track of previous composition to avoid duplicates
  const resolved: ResolvedSlide[] = []
  let prevCompositionId: CompositionId | null = null

  for (let i = 0; i < slides.length; i++) {
    const slide = slides[i]
    if (slide) {
      const resSlide = resolveSlide(slide, i + 1, doc.theme_id, prevCompositionId)
      resolved.push(resSlide)
      prevCompositionId = resSlide.composition_id
    }
  }

  return resolved
}
