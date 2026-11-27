package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"mentorly/internal/handlers/response"
)

type HealthHandler struct {
	ping func(context.Context) error
}

func NewHealthHandler(ping func(context.Context) error) *HealthHandler {
	return &HealthHandler{ping: ping}
}

func (h *HealthHandler) Live(c *gin.Context) {
	response.OK(c, gin.H{"status": "up"})
}

func (h *HealthHandler) Ready(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 3*time.Second)
	defer cancel()

	status := "up"
	if h.ping == nil {
		status = "unavailable"
	} else if err := h.ping(ctx); err != nil {
		status = "error: " + err.Error()
	}

	result := gin.H{"mysql": status}
	if status != "up" {
		c.JSON(http.StatusServiceUnavailable, response.Body{
			Code:    response.CodeUnavailable,
			Message: "dependencies unhealthy",
			Data:    result,
		})
		return
	}
	response.OK(c, result)
}
