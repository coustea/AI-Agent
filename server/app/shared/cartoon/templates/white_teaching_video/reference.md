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
  <div id="model-root" class="tree-node">8</div>
  <div id="model-left" class="tree-node">3</div>
  <div id="model-right" class="tree-node">10</div>
  <div id="model-new" class="data-token">6</div>
  <div id="model-rule" class="rule-bubble">当前比较：6 &lt; 8，所以转向左子树</div>
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
