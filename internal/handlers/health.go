package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"gorm.io/gorm"

	"mentorly/pkg/response"
)

// HealthHandler 健康检查接口
type HealthHandler struct {
	db  *gorm.DB
	rdb *redis.Client
}

func NewHealthHandler(db *gorm.DB, rdb *redis.Client) *HealthHandler {
	return &HealthHandler{db: db, rdb: rdb}
}

// Live 存活探针，只检查进程是否存活。
func (h *HealthHandler) Live(c *gin.Context) {
	response.OK(c, gin.H{"status": "up"})
}

// Ready 就绪探针，检查 MySQL 与 Redis 连通性。
// 依赖为 nil 表示启动时连接失败（降级模式），对 readiness 而言即不可用，
// 不能因为「没配置」而谎报健康。
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

	if h.rdb == nil {
		result["redis"] = "unavailable"
		healthy = false
	} else if err := h.rdb.Ping(ctx).Err(); err != nil {
		result["redis"] = "error: " + err.Error()
		healthy = false
	} else {
		result["redis"] = "up"
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
