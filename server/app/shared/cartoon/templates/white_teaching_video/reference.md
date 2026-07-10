# 示例：二叉搜索树插入机制

@course: 数据结构
@topic: 二叉搜索树插入
@duration: 96

## Scene 1: 为什么需要按规则插入
@id: problem
@start: 0
@duration: 12
@type: problem
@layout: hero
@focus: 有序结构

### Narration
因为二叉搜索树要支持快速查找，所以新节点不能随便放入，而必须根据大小关系沿路径移动到正确位置。

### HTML
```html
<div class="video-stage hero-stage">
  <div id="problem-main" class="concept-node hero-node">BST</div>
  <div id="problem-token" class="data-token action-token">6</div>
  <div id="problem-rule" class="rule-bubble">插入规则：小于当前节点走左边，大于当前节点走右边</div>
</div>
```

### Timeline
```js
Runtime.sceneIn(tl, "#scene-problem", T("problem", 0.0), 0.6);
Runtime.popIn(tl, "#scene-problem #problem-main", T("problem", 0.5), 0.6);
Runtime.spawn(tl, "#scene-problem #problem-token", "#scene-problem #problem-main", T("problem", 1.3), 0.5);
Runtime.reveal(tl, "#scene-problem #problem-rule", T("problem", 2.0), 0.6);
Runtime.cameraZoom(tl, "#scene-problem #camera-problem", 1.08, 860, 360, T("problem", 3.0), 1.0);
Runtime.caption(tl, "#caption-problem", T("problem", 3.4), 5.0);
Runtime.sceneOut(tl, "#scene-problem", T("problem", 11.2), 0.6);
```

## Scene 2: 建立可视化模型
@id: model
@start: 12
@duration: 16
@type: model
@layout: structure
@focus: 根节点与左右子树

### Narration
当插入开始时，算法从根节点出发，因为根节点把整棵树分成左小右大的两个范围。

### HTML
```html
<div class="video-stage structure-stage">
  <svg class="path-layer">
    <line id="model-edge-left" class="graph-edge"></line>
    <line id="model-edge-right" class="graph-edge"></line>
  </svg>
  <div id="model-root" class="tree-node pos-top-center">8</div>
  <div id="model-left" class="tree-node pos-left-mid">3</div>
  <div id="model-right" class="tree-node pos-right-mid">10</div>
  <div id="model-new" class="data-token pos-center">6</div>
  <div id="model-rule" class="rule-bubble pos-right-top">当前比较：6 &lt; 8，所以转向左子树</div>
</div>
```

### Timeline
```js
Runtime.sceneIn(tl, "#scene-model", T("model", 0.0), 0.5);
Runtime.popIn(tl, "#scene-model #model-root", T("model", 0.4), 0.5);
Runtime.popIn(tl, "#scene-model #model-left", T("model", 1.0), 0.5);
Runtime.popIn(tl, "#scene-model #model-right", T("model", 1.4), 0.5);
Runtime.connect(tl, "#scene-model #model-edge-left", "#scene-model #model-root", "#scene-model #model-left", T("model", 2.0), 0.6);
Runtime.connect(tl, "#scene-model #model-edge-right", "#scene-model #model-root", "#scene-model #model-right", T("model", 2.4), 0.6);
Runtime.spawn(tl, "#scene-model #model-new", "#scene-model #model-root", T("model", 3.2), 0.5);
Runtime.reveal(tl, "#scene-model #model-rule", T("model", 4.0), 0.6);
Runtime.cameraFocus(tl, "#scene-model #camera-model", "#scene-model #model-root", 1.12, T("model", 5.0), 1.0);
Runtime.caption(tl, "#caption-model", T("model", 5.4), 5.0);
Runtime.sceneOut(tl, "#scene-model", T("model", 15.2), 0.5);
```

## Scene 3: 沿比较路径移动
@id: trace
@start: 28
@duration: 20
@type: trace
@layout: trace
@focus: 插入路径

### Narration
因为 6 小于 8，所以新节点先移动到左子树；又因为 6 大于 3，所以继续沿右分支寻找空位置。

### HTML
```html
<div class="video-stage trace-stage">
  <svg class="path-layer">
    <path id="trace-path" class="arrow-path" d="M820 160 C720 260,640 330,610 430 C650 500,720 540,790 560"></path>
  </svg>
  <div id="trace-root" class="tree-node pos-top-center">8</div>
  <div id="trace-left" class="tree-node pos-left-mid">3</div>
  <div id="trace-target" class="data-slot pos-bottom-center">空位</div>
  <div id="trace-new" class="data-token pos-center">6</div>
  <div id="trace-track" class="timeline-track pos-bottom-track">
    <span class="step-chip">比较 8</span>
    <span class="step-chip">转向左</span>
    <span class="step-chip">比较 3</span>
    <span class="step-chip">转向右</span>
  </div>
</div>
```

### Timeline
```js
Runtime.sceneIn(tl, "#scene-trace", T("trace", 0.0), 0.5);
Runtime.popIn(tl, "#scene-trace #trace-root", T("trace", 0.4), 0.5);
Runtime.popIn(tl, "#scene-trace #trace-left", T("trace", 0.8), 0.5);
Runtime.reveal(tl, "#scene-trace #trace-target", T("trace", 1.2), 0.5);
Runtime.spawn(tl, "#scene-trace #trace-new", "#scene-trace #trace-root", T("trace", 1.8), 0.5);
Runtime.reveal(tl, "#scene-trace #trace-track", T("trace", 2.2), 0.5);
Runtime.markStep(tl, "#scene-trace #trace-track", 0, T("trace", 2.8), 0.4);
Runtime.drawPath(tl, "#scene-trace #trace-path", T("trace", 3.2), 1.0);
Runtime.transfer(tl, "#scene-trace #trace-new", "#scene-trace #trace-root", "#scene-trace #trace-left", T("trace", 4.4), 1.0);
Runtime.markStep(tl, "#scene-trace #trace-track", 2, T("trace", 5.8), 0.4);
Runtime.transfer(tl, "#scene-trace #trace-new", "#scene-trace #trace-left", "#scene-trace #trace-target", T("trace", 6.6), 1.0);
Runtime.cameraFocus(tl, "#scene-trace #camera-trace", "#scene-trace #trace-target", 1.15, T("trace", 8.0), 1.0);
Runtime.caption(tl, "#caption-trace", T("trace", 8.4), 5.0);
Runtime.sceneOut(tl, "#scene-trace", T("trace", 19.2), 0.5);
```

## Scene 4: 插入并更新结构
@id: state
@start: 48
@duration: 18
@type: state
@layout: state-sync
@focus: 父子连接

### Narration
当空位置确定后，新节点会成为父节点的右孩子，因此树的结构状态和父子连接必须同步更新。

### HTML
```html
<div class="video-stage state-stage">
  <svg class="path-layer">
    <line id="state-edge" class="graph-edge"></line>
  </svg>
  <div id="state-parent" class="tree-node pos-left-mid">3</div>
  <div id="state-new" class="tree-node pos-center">6</div>
  <div id="state-panel" class="state-panel pos-right-mid">
    <div id="state-row-1" class="state-badge">父节点：3</div>
    <div id="state-row-2" class="state-badge">方向：右孩子</div>
    <div id="state-row-3" class="state-badge">结构：待更新</div>
  </div>
</div>
```

### Timeline
```js
Runtime.sceneIn(tl, "#scene-state", T("state", 0.0), 0.5);
Runtime.popIn(tl, "#scene-state #state-parent", T("state", 0.4), 0.5);
Runtime.popIn(tl, "#scene-state #state-new", T("state", 1.0), 0.5);
Runtime.reveal(tl, "#scene-state #state-panel", T("state", 1.5), 0.5);
Runtime.connect(tl, "#scene-state #state-edge", "#scene-state #state-parent", "#scene-state #state-new", T("state", 2.2), 0.8);
Runtime.switchState(tl, "#scene-state #state-row-3", "结构：已插入", "ok", T("state", 3.4), 0.5);
Runtime.highlight(tl, "#scene-state #state-new", T("state", 4.2), 0.7);
Runtime.cameraFocus(tl, "#scene-state #camera-state", "#scene-state #state-new", 1.12, T("state", 5.0), 1.0);
Runtime.caption(tl, "#caption-state", T("state", 5.4), 5.0);
Runtime.sceneOut(tl, "#scene-state", T("state", 17.2), 0.5);
```

## Scene 5: 总结插入机制
@id: recap
@start: 66
@duration: 30
@type: recap
@layout: recap
@focus: 比较路径与结构更新

### Narration
因此，二叉搜索树插入的本质不是简单添加节点，而是用比较规则确定路径，再把新节点连接到唯一合法的位置。

### HTML
```html
<div class="video-stage recap-stage">
  <div id="recap-a" class="concept-node pos-chain-1">比较</div>
  <div id="recap-arrow-1" class="flow-arrow pos-chain-arrow-1">→</div>
  <div id="recap-b" class="concept-node pos-chain-2">选择方向</div>
  <div id="recap-arrow-2" class="flow-arrow pos-chain-arrow-2">→</div>
  <div id="recap-c" class="concept-node pos-chain-3">寻找空位</div>
  <div id="recap-arrow-3" class="flow-arrow pos-chain-arrow-3">→</div>
  <div id="recap-d" class="concept-node pos-chain-4">连接节点</div>
  <div id="recap-rule" class="rule-bubble pos-bottom-center-wide">核心：比较规则决定路径，路径决定结构位置。</div>
</div>
```

### Timeline
```js
Runtime.sceneIn(tl, "#scene-recap", T("recap", 0.0), 0.5);
Runtime.popIn(tl, "#scene-recap #recap-a", T("recap", 0.5), 0.5);
Runtime.reveal(tl, "#scene-recap #recap-arrow-1", T("recap", 1.2), 0.4);
Runtime.popIn(tl, "#scene-recap #recap-b", T("recap", 1.7), 0.5);
Runtime.reveal(tl, "#scene-recap #recap-arrow-2", T("recap", 2.4), 0.4);
Runtime.popIn(tl, "#scene-recap #recap-c", T("recap", 2.9), 0.5);
Runtime.reveal(tl, "#scene-recap #recap-arrow-3", T("recap", 3.6), 0.4);
Runtime.popIn(tl, "#scene-recap #recap-d", T("recap", 4.1), 0.5);
Runtime.reveal(tl, "#scene-recap #recap-rule", T("recap", 5.0), 0.6);
Runtime.cameraZoom(tl, "#scene-recap #camera-recap", 1.06, 760, 360, T("recap", 6.0), 1.0);
Runtime.caption(tl, "#caption-recap", T("recap", 6.4), 6.0);
Runtime.sceneOut(tl, "#scene-recap", T("recap", 29.2), 0.5);
```