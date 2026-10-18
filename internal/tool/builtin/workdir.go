package builtin

import (
	"os"
	"sync"
)

// WorkDirRef 是工具沙箱共享的工作目录引用。
// 所有内置工具持有同一引用，因此装配顺序无关：
// 先构造工具、后设置工作目录也能保证沙箱根一致。
type WorkDirRef struct {
	mu  sync.RWMutex
	dir string
}

func NewWorkDirRef(dir string) *WorkDirRef {
	return &WorkDirRef{dir: dir}
}

// Get 返回当前工作目录；未设置时回退到进程工作目录
func (r *WorkDirRef) Get() string {
	r.mu.RLock()
	dir := r.dir
	r.mu.RUnlock()
	if dir != "" {
		return dir
	}
	if wd, err := os.Getwd(); err == nil {
		return wd
	}
	return "."
}

func (r *WorkDirRef) Set(dir string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.dir = dir
}
