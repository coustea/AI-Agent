# 示例：队列处理流程

@duration: 96

## Scene 1: 输入请求进入系统
@id: intro
@start: 0
@duration: 14
@type: intro

### Narration
这段视频讲解队列处理流程。输入请求按顺序到达，根据规则选择处理资源，最终形成时间线记录。

### HTML
```html
<div class="scene-inner flex-col gap-lg">
  <div class="stage main-stage">
    <div id="input-strip" class="input-strip">
      <span>A</span><span>B</span><span>C</span>
    </div>
  </div>
  <div class="flex-row gap-lg">
    <div id="queue" class="panel operation-panel">等待队列：空</div>
    <div id="resource" class="panel metric-panel">
      <div class="metric-value">空闲</div>
      <div class="metric-label">处理资源</div>
    </div>
  </div>
</div>
```

### Timeline
```js
Runtime.reveal(tl, "#scene-intro #input-strip", T("intro", 0.4), 0.6);
Runtime.reveal(tl, "#scene-intro #queue", T("intro", 1.0), 0.6);
Runtime.reveal(tl, "#scene-intro #resource", T("intro", 1.6), 0.6);
Runtime.caption(tl, "#caption-intro", T("intro", 2.4), 4.0);
Runtime.pulse(tl, "#scene-intro #input-strip", T("intro", 6.0), 0.8);
```

## Scene 2: 请求 A 占用资源
@id: process-a
@start: 14
@duration: 16
@type: trace

### Narration
请求 A 从等待队列中取出，占用处理资源。队列更新，资源状态变为处理中。

### HTML
```html
<div class="scene-inner flex-col gap-lg">
  <div class="stage main-stage">
    <div id="token-a" class="token">A</div>
  </div>
  <div class="flex-row gap-lg">
    <div id="queue2" class="panel operation-panel">等待队列：B, C</div>
    <div id="resource2" class="panel metric-panel">
      <div class="metric-value">处理 A</div>
      <div class="metric-label">处理资源</div>
    </div>
  </div>
</div>
```

### Timeline
```js
Runtime.spawn(tl, "#scene-process-a #token-a", "#scene-process-a #queue2", T("process-a", 0.2), 0.5);
Runtime.move(tl, "#scene-process-a #token-a", "#scene-process-a #resource2", T("process-a", 1.0), 1.2);
Runtime.setText(tl, "#scene-process-a #resource2 .metric-value", "处理 A", T("process-a", 2.4), 0.5);
Runtime.setText(tl, "#scene-process-a #queue2", "等待队列：B, C", T("process-a", 2.6), 0.5);
Runtime.caption(tl, "#caption-process-a", T("process-a", 3.5), 5.0);
```
