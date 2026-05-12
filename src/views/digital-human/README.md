# 数字人互动模式

此目录用于数字人互动功能集成，包含前端播放器画布组件与控制逻辑。

## 目录说明

- **DigitalHumanCanvas.vue** - 数字人视频渲染容器与连接状态 UI
- **useDigitalHuman.ts** - 数字人连接、消息协议、语音输入与播放器控制 Composable

## 已实现能力

- WebSocket 连接数字人桥接服务（`/ws/avatar`）
- 接收 `stream_info` 并初始化 RTCPlayer 播放
- 文本输入驱动数字人对话
- 麦克风采集 + VAD 音频分片上传
- 会话历史清空、停止播报、断线重连

## 后续可扩展方向

- TTS 声线和情感参数可配置
- Viseme/表情驱动联动
- 3D 数字人渲染引擎替换（如 Three.js / MetaHuman）
- 多角色数字人切换
