// Package chat 是「对话」限界上下文：会话、消息、一轮对话的执行与上下文压缩。
//
// # 文件职责
//
//	entity.go    Session / Message / Role / Status —— 零框架依赖的领域类型
//	store.go     GORM 行类型（私有）+ Store 仓储
//	service.go   业务面：会话 CRUD、配置、异步标题
//	turn.go      一轮对话的生命周期：Begin → Run → Close
//	window.go    token 估算与窗口裁剪（纯计算，无 IO）
//	compress.go  上下文滚动压缩：阈值判断、摘要生成、基线重算
//	agent.go     eino ADK 封装：按轮构建 Agent、流式消费、文本补全
//	prompt.go    System Prompt 组装
//	sandbox.go   文件系统沙箱（安全边界）
//	handler.go   HTTP handlers + SSE writer
//	dto.go       请求 / 响应结构
//	route.go     Register：把本模块路由挂到 gin
//
// # 一轮对话
//
//	Begin    加锁 · 归属校验 · 落库 user 消息（必须在写 SSE 头之前完成）
//	Run      Pre-Run 管线 → 构建 Agent → 流式执行 → 终态收口落库
//	Close    释放会话锁（幂等，调用方无条件 defer）
//
// Pre-Run 管线只有两步：上下文压缩 → 重建窗口与 Prompt。
// 顺序不可交换：先压缩，重建时读到的才是压缩后的最小历史。
//
// # SSE 帧契约
//
// 与前端约定，变更需同步：
//
//	delta  {"text": "..."}      增量文本
//	reset  {}                   清空已渲染内容（工具调用前的过渡语作废）
//	done   {"message_id": 123, "status": "completed|failed|cancelled"}
//	error  {"message": "..."}
//	: ping                      心跳注释行
//
// 帧编码只发生在 handler.go，业务代码只处理 Chunk{Text, Reset}。
//
// # 设计取舍
//
//  1. 单包而非多子包：本模块只有一个聚合根（Session）和一个主用例（一轮对话），
//     再拆 domain/app/adapter 层只会让 service 退化成纯转发。
//  2. 配置不嵌入模块：Service 只接收拍平后的 Config 值对象，
//     不 import internal/config，对配置文件与数据库连接零知识。
//  3. token 基线必须用真实值：eino 注入的工具 Schema 约 4.5k token
//     本地估算器看不到，详见 compress.go 的 newBaseline。
package chat
