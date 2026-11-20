package attachments

import (
	"bytes"
	"compress/flate"
	"compress/zlib"
	"fmt"
	"io"
)

// inflate 尝试解压 FlateDecode 流。
//
// PDF 的 FlateDecode 是 zlib 包装（带 2 字节头），但也存在裸 deflate 的情况，
// 因此先试 zlib，失败再试裸 flate。
func inflate(data []byte) (string, error) {
	data = bytes.TrimSpace(data)
	if len(data) == 0 {
		return "", fmt.Errorf("空流")
	}

	// 先试 zlib
	if zr, err := zlib.NewReader(bytes.NewReader(data)); err == nil {
		defer zr.Close()
		out, err := io.ReadAll(io.LimitReader(zr, 32<<20))
		if err == nil && len(out) > 0 {
			return string(out), nil
		}
	}

	// 再试裸 deflate
	fr := flate.NewReader(bytes.NewReader(data))
	defer fr.Close()
	out, err := io.ReadAll(io.LimitReader(fr, 32<<20))
	if err != nil || len(out) == 0 {
		return "", fmt.Errorf("无法解压流")
	}
	return string(out), nil
}
