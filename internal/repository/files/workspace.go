package files

import (
	"fmt"
	"os"
	"sort"
	"syscall"
	"time"

	"mentorly/internal/utils"
)

type File struct {
	Name       string
	Size       int64
	ModifiedAt time.Time
}

type Workspace struct{ root string }

func NewWorkspace(root string) *Workspace { return &Workspace{root: root} }

func (s *Workspace) List(userID, conversationID string) ([]File, error) {
	dir, err := utils.SafeJoin(s.root, userID, conversationID)
	if err != nil {
		return nil, err
	}
	entries, err := os.ReadDir(dir)
	if os.IsNotExist(err) {
		return []File{}, nil
	}
	if err != nil {
		return nil, fmt.Errorf("读取工作区失败: %w", err)
	}
	out := make([]File, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() || entry.Type()&os.ModeSymlink != 0 {
			continue
		}
		info, err := entry.Info()
		if err != nil || !info.Mode().IsRegular() {
			continue
		}
		out = append(out, File{Name: entry.Name(), Size: info.Size(), ModifiedAt: info.ModTime()})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ModifiedAt.After(out[j].ModifiedAt) })
	return out, nil
}

func (s *Workspace) Open(userID, conversationID, name string) (*os.File, os.FileInfo, error) {
	dir, err := utils.SafeJoin(s.root, userID, conversationID)
	if err != nil {
		return nil, nil, err
	}
	path, err := utils.SafeJoin(dir, name)
	if err != nil {
		return nil, nil, err
	}
	f, err := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, nil, err
	}
	info, err := f.Stat()
	if err != nil || !info.Mode().IsRegular() {
		f.Close()
		return nil, nil, fmt.Errorf("文件不存在")
	}
	return f, info, nil
}
