# theory_video.md DSL 规则

## 顶层格式

```markdown
# 视频标题
@course: 课程名称
@topic: 知识点名称
@duration: 总秒数
```

## Scene 格式

```markdown
## Scene N: 场景标题
@id: scene-id
@start: 起始秒
@duration: 场景秒数
@type: problem|model|mechanism|trace|state|contrast|recap
@layout: hero|mechanism|trace|state-sync|compare|recap|structure|flow
@focus: 当前镜头聚焦对象

### Narration
旁白文本

### HTML
```html
scene 内部 HTML
```

### Timeline
```js
Runtime 调用
```
```

## 强制要求

1. 总时长 60 到 420 秒。
2. 场景数量 5 到 8 个。
3. 必须包含 mechanism、trace、recap。
4. scene id 必须唯一，只能小写字母开头，包含小写字母、数字、连字符、下划线。
5. 第一个 scene 必须从 0 秒开始。
6. 场景时间不能重叠。
7. 场景之间不能有长空白。
8. 每个 scene 必须有 Narration、HTML、Timeline。
9. Narration 必须解释因果关系，不能只描述画面。
10. HTML 只能写 scene 内部片段。
11. HTML 禁止 section/html/head/body/main/script/style/canvas/video/audio/img/pre/code。
12. HTML 禁止事件属性和远程链接。
13. 默认禁止代码讲解，不允许 code-board、source-code、pre、code、def、class、function、for、while 等源码展示倾向。
14. 每个 scene 必须有理论动画对象类。
15. 每个 scene 内所有 id 必须带 scene id 前缀。
16. Timeline 只能调用 Runtime 方法。
17. Timeline 禁止 gsap/document/Math.random/Date.now/setTimeout/window.__timelines/const tl。
18. Runtime 调用必须单行，并以分号结尾。
19. Timeline selector 必须引用存在的 id。
20. T("scene_id", local_seconds) 必须引用存在 scene，local_seconds 不能超过 scene duration。
21. 每个 scene 至少 4 个 Runtime 调用。
22. 全视频至少 35 个 Runtime 调用。
23. trace 场景必须包含对象移动、路径绘制、连线变化或专用理论动作。
24. state 场景必须包含状态同步动作。
25. 全视频必须包含镜头语言：sceneIn、sceneOut、cameraZoom、cameraPan、cameraFocus 至少一种。
26. 至少使用 3 种 layout。
27. 不能像 PPT 页面，必须像视频镜头：主舞台、主对象、运动路径、少量浮层、字幕解释。

## 推荐 scene 组织

### problem
提出为什么需要这个机制。

### model
把抽象知识转换成可见对象。

### mechanism
解释规则如何驱动对象变化。

### trace
逐步播放对象运动、路径变化、结构变化。

### state
同步更新状态表、队列、页框、时间线、窗口、栈等。

### contrast
展示错误理解和正确机制的差异。

### recap
用结构图总结知识点。
