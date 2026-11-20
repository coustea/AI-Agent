APP_NAME := mentorly
BINARY   := bin/$(APP_NAME)

.PHONY: help
help: ## 显示可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: env
env: ## 从模板生成本地 .env（已存在则不覆盖）
	@test -f .env || cp .env.example .env
	@echo ".env 已就绪，按需修改 MySQL / Redis / LLM 配置"

.PHONY: deps
deps: ## 下载并校验依赖
	go mod download
	go mod verify

.PHONY: run
run: ## 本地启动 HTTP 服务
	go run ./cmd/server

.PHONY: build
build: ## 编译二进制到 bin/
	@mkdir -p bin
	go build -trimpath -ldflags "-s -w" -o $(BINARY) ./cmd/server

.PHONY: tidy
tidy: ## 整理 go.mod / go.sum
	go mod tidy

.PHONY: vet
vet: ## 静态检查
	go vet ./...

.PHONY: fmt
fmt: ## 格式化代码
	gofmt -w $$(find . -name '*.go' -not -path './vendor/*' -not -path './workspace/*')

.PHONY: test
test: ## 运行测试
	go test ./... -race -count=1

.PHONY: check
check: fmt vet build ## 格式化 + 检查 + 编译

.PHONY: migrate
migrate: ## 执行数据库迁移（保留现有用户数据）
	@mysql -u$${MYSQL_USERNAME:-root} -p$${MYSQL_PASSWORD} -D $${MYSQL_DATABASE:-mentorly} < migrations/001_agent_first.sql

.PHONY: backup
backup: ## 备份数据库到 /tmp
	@mkdir -p /tmp/mentorly-backup
	@mysqldump -u$${MYSQL_USERNAME:-root} -p$${MYSQL_PASSWORD} --single-transaction \
		$${MYSQL_DATABASE:-mentorly} > /tmp/mentorly-backup/$$(date +%Y%m%d-%H%M%S).sql
	@echo "备份完成: /tmp/mentorly-backup/"

.PHONY: doctor
doctor: ## 检查运行时依赖（ffmpeg / 字体 / 数据库）
	@echo "--- ffmpeg ---"; command -v ffmpeg || echo "缺失（视频能力不可用）"
	@echo "--- 字体 ---"; ls /Library/Fonts/Arial\ Unicode.ttf 2>/dev/null || \
		ls /System/Library/Fonts/Supplemental/Songti.ttc 2>/dev/null || echo "缺失（视频能力不可用）"
	@echo "--- MySQL ---"; command -v mysql >/dev/null && echo "ok" || echo "缺失"

.PHONY: clean
clean: ## 清理构建产物与日志
	rm -rf bin logs
	@echo "注意：workspace/ 下的会话文件与产物未删除，如需清理请手动执行"

.PHONY: db
db: ## 创建本地数据库（需 mysql 客户端与 MySQL 凭据）
	@mysql -u$${MYSQL_USERNAME:-root} -p$${MYSQL_PASSWORD} \
		-e "CREATE DATABASE IF NOT EXISTS $${MYSQL_DATABASE:-mentorly} \
		DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
	@echo "数据库已就绪"