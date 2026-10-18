.PHONY: build run test clean

# 编译参数：支持自动从本地环境变量提取 SPARK_API_KEY 作为内置免费凭证注入
SPARK_FREE_KEY ?= $(shell echo $${SPARK_API_KEY:-$$MAAS_API_KEY})
LDFLAGS := -X my-agent/internal/config.DefaultSparkAPIKey=$(SPARK_FREE_KEY)

# 编译生成名为 tide 的可执行程序
build:
	go build -ldflags "$(LDFLAGS)" -o tide ./cmd/tide

# 直接运行 tide
run:
	go run -ldflags "$(LDFLAGS)" ./cmd/tide

# 运行单元测试
test:
	go test -v ./internal/...

# 清理构建产物与临时文件
clean:
	rm -f tide coustea test_config.json
