# 数字人互动模式

此目录为数字人互动功能的占位实现，用于未来集成。

## 预期集成

- **DigitalHumanCanvas.vue** - 数字人 3D 渲染画布组件
- **useDigitalHuman.ts** - 数字人控制 Composable

## 未来技术选型

- TTS: 文本转语音服务（如阿里云、讯飞、Edge TTS）
- 唇形同步: 基于 Viseme 映射驱动面部动画
- 3D 渲染: Three.js / Unreal MetaHuman / 开源数字人方案
- 语音识别: Web Speech API 或第三方 ASR 服务

## 当前状态

Tutor.vue 中已包含数字人模式的 UI 框架（头像展示、语音波形动画、状态标识）。
此目录的组件将在实际数字人服务接入后替换占位内容。