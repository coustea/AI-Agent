package dto

// AttachmentResp 是附件响应结构。
type AttachmentResp struct {
	ID           string `json:"id"`
	Filename     string `json:"filename"`
	Kind         string `json:"kind"`
	MIME         string `json:"mime"`
	Size         int64  `json:"size"`
	TextLength   int    `json:"text_length,omitempty"`
	Truncated    bool   `json:"truncated,omitempty"`
	ExtractError string `json:"extract_error,omitempty"`
	DownloadURL  string `json:"download_url"`
}

// FileResp 是工作区文件响应结构。
type FileResp struct {
	Name        string `json:"name"`
	Path        string `json:"path"`
	Size        int64  `json:"size"`
	ModifiedAt  string `json:"modified_at"`
	DownloadURL string `json:"download_url"`
}
