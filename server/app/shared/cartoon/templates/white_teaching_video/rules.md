# cartoon.md DSL 规则

## 格式

```
# 视频标题
@duration: 总秒数

## Scene N: 场景标题
@id: scene-id
@start: 起始秒
@duration: 场景秒数
@type: intro|trace|sync|contrast|recap

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

## 必须满足

1. 标题不能为空
2. 总时长 ≥ 90 秒
3. 场景数量 5-8 个
4. 每个 scene 必须有 @id、@start、@duration、@type
5. scene id 必须唯一，只含小写字母数字连字符下划线，不能数字开头
6. scene start ≥ 0，duration > 0
7. 场景时间不能重叠
8. 最后一个 scene 的结束时间不能超过总 duration 太多（≤15秒）
9. 每个场景必须有 Narration、HTML、Timeline
10. HTML 不允许包含 section、html、head、body、main、script 标签
11. Timeline 不允许包含 const tl 或 window.__timelines
12. Timeline 必须使用 Runtime.xxx 调用
13. T("scene_id", time) 中的 scene_id 必须引用存在的 scene @id
14. T() 中的 local time 不能超过对应 scene duration
15. 全视频 Runtime 调用数量至少 25
16. 每个 scene 至少 3 个 Runtime 调用
17. 至少包含 reveal / move 或 moveTo / highlight / setText 中的三类
18. 不允许所有 scene 使用相同布局
