APP_NAME := mentorly
BINARY   := bin/$(APP_NAME)

.PHONY: help
help: ## 显示可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: env
env: ## 从模板生成本地 .env（已存在则不覆盖）
	@test -f .env || cp .env.example .env
	@echo ".env 已就绪，按需修改 MySQL / LLM 配置"

.PHONY: deps
deps: ## 下载并校验依赖
	go mod download
	go mod verify

.PHONY: skills-deps
skills-deps: ## 安装官方文档技能所需 Python 环境
	@test -x "$(HOME)/.local/share/mentorly/skills-python/bin/python3" || uv venv "$(HOME)/.local/share/mentorly/skills-python" --python 3.12
	uv pip install --python "$(HOME)/.local/share/mentorly/skills-python/bin/python" -r internal/agent/skills/requirements.txt

.PHONY: run
run: ## 本地启动 HTTP 服务
	go run ./cmd/server

.PHONY: build
build: ## 编译服务二进制到 bin/
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

.PHONY: backup
backup: ## 备份数据库到 /tmp
	@mkdir -p /tmp/mentorly-backup
	@mysqldump -u$${MYSQL_USERNAME:-root} -p$${MYSQL_PASSWORD} --single-transaction \
		$${MYSQL_DATABASE:-mentorly} > /tmp/mentorly-backup/$$(date +%Y%m%d-%H%M%S).sql
	@echo "备份完成: /tmp/mentorly-backup/"

.PHONY: doctor
doctor: ## 检查运行时与 Skills 工具链依赖
	@echo "--- ripgrep (rg) ---"; command -v rg || echo "缺失（grep 文件工具不可用）"
	@echo "--- skills-python ---"; \
		PY="$(HOME)/.local/share/mentorly/skills-python/bin/python"; \
		if [ -x "$$PY" ]; then echo "$$PY"; "$$PY" -c "import pptx, defusedxml, lxml, PIL; print('python-pptx/defusedxml/lxml/PIL ok')" || echo "依赖不全，请运行 make skills-deps"; \
		else echo "未安装，请运行 make skills-deps"; fi
	@echo "--- node & 全局 Skills 包 ---"; \
		if command -v node >/dev/null 2>&1; then \
			node -v; \
			NODE_PATH="$$(npm root -g 2>/dev/null)" node -e "for (const m of ['pptxgenjs','docx','react','react-dom','react-icons','sharp']) { try { require.resolve(m); console.log('  ' + m + ': ok'); } catch { console.log('  ' + m + ': 缺失'); } }"; \
		else echo "node 缺失"; fi
	@echo "--- LibreOffice (soffice) ---"; command -v soffice || echo "缺失（PPT/DOCX 转 PDF 视觉自检不可用，可 brew install --cask libreoffice）"
	@echo "--- Poppler (pdftoppm / pdftotext) ---"; command -v pdftoppm || echo "pdftoppm 缺失"; command -v pdftotext || echo "pdftotext 缺失（PDF 附件提取不可用）"
	@echo "--- ffmpeg ---"; command -v ffmpeg || echo "缺失（视频渲染不可用）"
	@echo "--- MySQL ---"; command -v mysql >/dev/null && echo "ok" || echo "缺失"

.PHONY: clean
clean: ## 清理构建产物与日志
	rm -rf bin logs
	@echo "注意：workspace/ 下的会话文件与产物未删除，如需清理请手动执行"

.PHONY: web-install
web-install: ## 安装前端依赖（web/）
	pnpm --dir web install

.PHONY: web-dev
web-dev: ## 启动前端开发服务（代理 /api 到 :8080）
	pnpm --dir web dev

.PHONY: web-build
web-build: ## 类型检查并构建前端生产包
	pnpm --dir web build

.PHONY: db
db: ## 创建本地数据库（需 mysql 客户端与 MySQL 凭据）
	@mysql -u$${MYSQL_USERNAME:-root} -p$${MYSQL_PASSWORD} \
		-e "CREATE DATABASE IF NOT EXISTS $${MYSQL_DATABASE:-mentorly} \
		DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
	@echo "数据库已就绪"
