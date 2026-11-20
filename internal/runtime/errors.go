package runtime

import "errors"

var (
	// ErrNoPrincipal 调用链上没有已认证身份，属于编程错误而非用户错误。
	ErrNoPrincipal = errors.New("runtime: 缺少已认证用户上下文")
	// ErrNotConfigured 依赖未配置（模型、外部引擎、凭据缺失）。
	// 上层应据此返回明确的「未启用」而不是降级成假结果。
	ErrNotConfigured = errors.New("runtime: 能力未配置")
	// ErrForbidden 跨用户访问被拒绝。
	ErrForbidden = errors.New("runtime: 无权访问该资源")
)
