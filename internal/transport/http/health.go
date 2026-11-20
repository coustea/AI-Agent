package http

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"mentorly/internal/response"
)

// HealthHandler 健康检查接口。
type HealthHandler struct {
	db *gorm.DB
}

// NewHealthHandler 构造健康检查 handler。
func NewHealthHandler(db *gorm.DB) *HealthHandler {
	return &HealthHandler{db: db}
}

// Live 存活探针，只检查进程是否存活。
func (h *HealthHandler) Live(c *gin.Context) {
	response.OK(c, gin.H{"status": "up"})
}

// Ready 就绪探针，检查 MySQL 连通性。
//
// MySQL 是唯一硬依赖：会话、消息、记忆、附件、产物元数据都在里面，
// 连不上就真的无法服务，必须返回 503 而不是谎报健康。
func (h *HealthHandler) Ready(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 3*time.Second)
	defer cancel()

	result := gin.H{}
	healthy := true

	if h.db == nil {
		result["mysql"] = "unavailable"
		healthy = false
	} else if sqlDB, err := h.db.DB(); err != nil {
		result["mysql"] = "error: " + err.Error()
		healthy = false
	} else if err := sqlDB.PingContext(ctx); err != nil {
		result["mysql"] = "error: " + err.Error()
		healthy = false
	} else {
		result["mysql"] = "up"
	}

	if !healthy {
		// 直接构造 Body 以带上各项依赖明细，复用 Fail 会丢掉 data。
		c.JSON(http.StatusServiceUnavailable, response.Body{
			Code:    response.CodeUnavailable,
			Message: "dependencies unhealthy",
			Data:    result,
		})
		return
	}

	response.OK(c, result)
}
