# Cartoon Semantic Motion Recovery Design

## Context

The generated artifact at
`server/static/coustea/resources/14/cartoon/video.mp4` is a valid 1920x1080,
24 fps, 130.8-second MP4 with audio, but it is not an animated computer-science
explainer. Its four scenes show text cards appearing and then remaining still.

Measured evidence:

- all four scenes have `execution_program = null`;
- the storyboard uses `concept`, `model`, and `evidence`, so the current
  "three grammars" check passes without one executable scene;
- 93.7% of adjacent frames are nearly static;
- only 0.9% of adjacent frames show material visual change;
- the HyperFrames report contains zero motion findings, which the current
  pipeline interprets as success rather than absence of motion.

The failure is upstream of GSAP. The planner accepts generic labels and text,
the non-trace compiler turns them into region-based cards, and the runtime can
only animate the weak state changes it receives. Adding CSS entrance effects
would preserve the broken teaching contract.

This design corrects the drift between the existing Cartoon goals and the
active implementation. It replaces card-oriented success with a mandatory,
generic semantic-animation contract.

## Goals

- Every published scene contains visible dynamic animation.
- Process-oriented teaching visibly changes object position, relation, value,
  or state; text replacement and card reveal alone do not qualify.
- The engine supports computer-science theory broadly without branches for a
  named course, algorithm, data structure, or protocol.
- Nodes, vertices, containers, processes, pointers, ports, and relations have
  stable visual meaning and deterministic geometry.
- Cards and nodes never overlap each other or the title/caption safe areas.
- Relation lines meet node boundaries exactly: no dangling gaps and no lines
  extending through node interiors.
- Captions use a transparent background and dark text in a reserved safe area.
- Motion, layout, relation geometry, audio, and media output are all enforced
  before publication.

## Non-Goals

- Do not add decorative looping motion to make a static lesson appear active.
- Do not let the LLM generate coordinates, HTML, CSS, selectors, or JavaScript.
- Do not create modules named for binary trees, Dijkstra, AVL, operating-system
  scheduling, or other individual subjects.
- Do not preserve the current generic-card path as a fallback for an invalid
  process scene.
- Do not replace HyperFrames or the existing TTS provider.
- Do not merge standalone resource records with learning-path records.

## Chosen Direction

Use the semantic-animation closure approach selected as option B:

1. plan stable semantic objects, relations, topology, and ordered actions;
2. validate and replay every state transition before layout;
3. select a generic topology layout, not a subject-specific renderer;
4. compute collision-free object geometry and exact relation endpoints;
5. schedule finite, seekable semantic animation against TTS timing;
6. reject output that lacks rendered motion, even if HyperFrames reports no
   explicit motion finding.

A minimal "require one trace scene" patch was rejected because concept and
model scenes would remain card-based. A full template-platform rebuild was
deferred because the immediate defect can be fixed at the shared semantic,
geometry, timeline, and quality boundaries without introducing a second theme.

## Unified Semantic Scene Program

The active contract should converge on one renderer-neutral scene program:

```text
Lesson
  scenes[]
    mode
    topology
    objects[]
    relations[]
    steps[]
      narration
      actions[]
```

`mode` describes teaching intent such as concept, mechanism, execution,
comparison, or evidence. `topology` selects a generic geometry strategy:

- `hierarchical`: trees, call hierarchies, ownership and dependency layers;
- `network`: graphs, topology, dependency networks and search frontiers;
- `flow`: processes, pipelines, state machines and transaction stages;
- `sequence`: protocol messages, request/response and actor interactions;
- `grid`: arrays, tables, memory, matrices and state cells;
- `spatial`: small free relationship models that do not fit the above.

Objects use reusable roles rather than subject names:

- square node or vertex;
- structural container/card;
- rounded process or stage;
- token/value;
- pointer/cursor;
- port/endpoint;
- metric/marker.

Actions use a closed vocabulary such as reveal, focus, place, move, remove,
connect, disconnect, update, compare, traverse, and settle. Every action names
known objects and must produce a replayable state delta.

Every scene must have at least one dynamic action. Execution and mechanism
scenes must include a structural delta: move/place/remove, connection change,
or value/state mutation. Reveal, focus, caption change, and camera movement
alone cannot satisfy that requirement.

If the planner cannot produce a valid program, generation fails. It must not
publish explanatory cards as a substitute.

## Visual Language

The composition remains white and restrained. Shape communicates semantic
role:

- nodes and graph vertices use compact squares with at most 5px radius;
- process and stage objects use rounded rectangles;
- stacks, queues, arrays and grouped state use structural cards or cells;
- pointers and relations are explicit and remain visually lighter than nodes;
- active state uses one semantic accent, not glow-heavy decoration;
- decorative gradients, dark panels, and nested cards are excluded.

The fixed canvas regions are:

- title and scene metadata: 15% of canvas height;
- main teaching stage: approximately 67%;
- transparent caption safe area: 10.5%;
- progress rail: 5px at the bottom.

The stage uses measured tracks with stable gaps. A layout may allocate tracks
to structural objects, state containers, or process explanation, but these are
layout roles, not mandatory three-column content. The solver may use one, two,
or three tracks based on topology and object count.

Captions use no black background. They render as dark text on the paper canvas
inside the reserved caption area, separated from the stage by a fine neutral
rule. Caption content never changes stage geometry.

## Collision-Free Layout

Layout runs before HTML publication and produces measured bounding boxes for
every visible semantic object in every state.

The solver must enforce:

- no intersection between visible non-decorative object boxes;
- no object box entering the title, caption, or progress safe areas;
- minimum object-to-object and object-to-edge gaps;
- readable labels after fitting, without solving overflow by overlap;
- deterministic output for the same validated scene program.

If the first layout does not fit, the solver may reduce internal object scale,
change track allocation, or select another compatible topology arrangement.
It may not stack cards on top of each other or silently clip content. A scene
that still cannot fit fails with object IDs and conflicting boxes.

## Simple Relation Geometry

Relation visuals are deliberately simple:

- default line width is approximately 1.7px;
- active relations may use approximately 2.2px and the primary accent color;
- straight paths are preferred;
- one orthogonal bend is allowed when needed for obstacle avoidance;
- arrowheads are small and appear only when direction has meaning;
- ports remain hidden in the final video;
- curves, glow, thick arrows, and multi-bend decorative paths are excluded;
- labels appear only for semantic data such as weight or condition.

The geometry engine still provides precise behavior:

1. Compute the path between source and target centers.
2. Intersect that path with the actual source and target shape boundaries.
3. Place a plain line endpoint on the border stroke center.
4. For a directed relation, place the arrow tip on the target border and stop
   the shaft exactly one arrowhead length earlier.
5. Reject a path that crosses an unrelated object box; retry with one
   orthogonal bend or another compatible port direction.
6. Recompute and tween the path in the same timeline whenever either endpoint
   moves or changes size.

At sampled initial, midpoint, and final states, the endpoint-to-boundary error
must be no more than 1.5px. A gap greater than that is too short; line or arrow
geometry inside the node beyond that tolerance is too long. Either failure
blocks publication.

## Motion and Timing Contract

TTS duration remains the master clock. Each scene is divided into narration
steps, and each step schedules one or more semantic actions.

Required timing:

- first meaningful visible change within 1.0 second of scene start;
- at least one semantic change every 3.0 seconds while narration is active;
- final meaningful change no earlier than 2.2 seconds before narration ends;
- primary transitions generally take 0.6-1.2 seconds;
- short reading holds are allowed, but no hold may replace a required action;
- every animation is finite, deterministic, and seekable.

Connection and traversal may use a simple line draw or accent change. Moving
objects tween between canonical layouts while their incident lines update in
the same interval. Value and state changes use a concise highlight, then settle
to the stable state. No unrelated object loops continuously.

Dynamic animation is mandatory at three levels:

- schema: every scene contains actions and every process scene contains a
  structural action;
- timeline: every required action receives a non-zero scheduled interval and
  satisfies the maximum semantic-gap rule;
- rendered artifact: frame analysis proves that scheduled actions produced
  actual pixel changes outside the caption and progress regions.

## Quality Gates

### Semantic Gate

- all object, relation, and action references resolve;
- state replay succeeds for every step;
- every step has an observable state delta;
- every scene has visible dynamic animation;
- process scenes have structural animation;
- no process scene falls back to generic cards.

### Layout Gate

- visible object boxes do not overlap;
- object boxes stay inside the teaching stage;
- title and caption safe areas remain clear;
- relation paths avoid unrelated objects;
- line and arrow endpoints satisfy the 1.5px boundary tolerance.

Checks run at scene start, action midpoint, transition midpoint, and scene end,
not only at time zero.

### Motion Gate

The quality result must distinguish "no motion defects" from "no motion".
Success requires explicit positive measurements:

- expected semantic actions are mounted on the HyperFrames timeline;
- maximum rendered still interval does not exceed the contract;
- actual frame differences exist around every scheduled structural action;
- motion coverage is above a minimum threshold and below a thrashing threshold;
- measurement excludes caption changes and the global progress rail so they
  cannot fake teaching animation.

The resource-14 artifact would fail this gate because its near-static ratio is
93.7% and none of its scenes has an execution program.

### Media Gate

- HyperFrames strict inspection passes at transitions and sampled action times;
- final output has the configured resolution and frame rate;
- duration matches the scheduled lesson within tolerance;
- both video and audio streams exist;
- captions remain readable and inside their safe area.

Only after all gates pass may the atomic work directory replace the published
Cartoon artifact.

## Error Reporting

Failures identify the boundary and scene/step/object involved:

- `invalid_scene_program`;
- `missing_structural_motion`;
- `layout_collision`;
- `safe_area_violation`;
- `relation_path_blocked`;
- `relation_endpoint_mismatch`;
- `motion_gap_exceeded`;
- `rendered_motion_missing`;
- `media_contract_failed`.

The pipeline keeps the failed audit bundle for diagnosis and does not publish a
partial or static MP4.

## Implementation Boundaries

The change should remain within the current shared Cartoon pipeline:

- `models.py`: unified semantic object, relation, topology, action, and state
  invariants;
- `planner.py` and prompts: generic scene program generation and validation;
- `execution.py`: deterministic replay of all semantic actions;
- `composer.py`: stable semantic DOM without subject-specific branches;
- `assets/runtime.js`: layout motion, simple relation geometry, and exact
  synchronized path updates;
- `assets/theme.css`: shape language, transparent caption zone, and stable
  canvas regions;
- `media.py`: collision, endpoint, motion-density, and rendered-motion gates;
- focused existing Cartoon tests and an end-to-end representative render.

The implementation must not introduce algorithm-name dispatch. It may add or
separate helpers by responsibility, but the public model stays generic and all
topology strategies operate on semantic roles and relations.

## Validation

Validation uses both focused contracts and a real render:

1. focused model/planner/compiler tests for state replay and mandatory motion;
2. geometry checks for square nodes, rounded processes, arrows, movement, and
   collisions across the generic topology strategies;
3. deterministic timeline checks for first action, maximum gap, and final
   action timing;
4. HyperFrames strict inspection at starts, transitions, action midpoints, and
   ends;
5. MP4 frame-difference analysis excluding captions/progress;
6. `ffprobe` verification of resolution, frame rate, duration, and audio;
7. contact-sheet review confirming dynamic object/state progression, transparent
   captions, no overlaps, and exact simple relation endpoints.

Representative lessons should cover hierarchical, network, flow, sequence,
and grid topology, but remain generic fixtures rather than course-specific
production branches.

## Success Criteria

- No published Cartoon scene is motionless.
- No process scene can pass with only cards, text replacement, focus, or camera
  movement.
- No visible card/node collision exists at sampled states or transitions.
- No line or arrow endpoint is visibly short or extends through its node.
- Captions have no black background and never overlap teaching content.
- A video with the resource-14 motion profile is rejected.
- The final implementation contains no named-course or named-algorithm render
  path.
