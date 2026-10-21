.PHONY: build run test clean install release verify fmt-check vet test-race lint

# 版本与编译参数
VERSION ?= v1.2.0
LDFLAGS := -s -w -X my-agent/internal/config.Version=$(VERSION)

# 编译生成名为 tide 的当前平台可执行程序
build:
	go build -ldflags "$(LDFLAGS)" -o tide ./cmd/tide

# 直接运行 tide
run:
	go run -ldflags "$(LDFLAGS)" ./cmd/tide

# 运行单元测试
test:
	go test -v ./internal/...

# 提交前统一验证：格式 → 静态检查 → 竞态测试 → 构建（与 CI 核心检查一致）
verify: fmt-check vet test-race build
	@echo "==> verify 全部通过"

# 格式检查：gofmt 有输出即视为失败
fmt-check:
	@out=$$(gofmt -l cmd internal pkg); if [ -n "$$out" ]; then echo "以下文件未格式化（执行 gofmt -w）："; echo "$$out"; exit 1; fi

# 静态检查：可疑构造、无效赋值、错误处理缺陷
vet:
	go vet ./...

# 竞态检测：本仓库存在跨 goroutine 共享状态（agent.running、TUI 渲染缓存、工具沙箱目录）
test-race:
	go test -race -count=1 ./...

# 静态分析（需本地安装 golangci-lint v2，CI 亦执行）
lint:
	golangci-lint run ./...

# 安装至本地系统路径 (/usr/local/bin)
install: build
	@echo "==> 安装 tide 至 /usr/local/bin..."
	@install -d /usr/local/bin 2>/dev/null || sudo install -d /usr/local/bin
	@install -m 755 tide /usr/local/bin/tide 2>/dev/null || sudo install -m 755 tide /usr/local/bin/tide
	@echo "==> 安装完成！运行 'tide' 即可启动。"

# 清理构建产物与临时文件
clean:
	rm -rf tide coustea test_config.json dist

# 跨平台全量构建发布包 (Darwin amd64/arm64, Linux amd64/arm64, Windows amd64)
release:
	@rm -rf dist
	@mkdir -p dist
	@echo "==> 构建 Darwin (macOS Intel) amd64..."
	@mkdir -p dist/tide-darwin-amd64 && CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o dist/tide-darwin-amd64/tide ./cmd/tide
	@tar -czf dist/tide-darwin-amd64.tar.gz -C dist/tide-darwin-amd64 tide
	@echo "==> 构建 Darwin (macOS Apple Silicon) arm64..."
	@mkdir -p dist/tide-darwin-arm64 && CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o dist/tide-darwin-arm64/tide ./cmd/tide
	@tar -czf dist/tide-darwin-arm64.tar.gz -C dist/tide-darwin-arm64 tide
	@echo "==> 构建 Linux amd64..."
	@mkdir -p dist/tide-linux-amd64 && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o dist/tide-linux-amd64/tide ./cmd/tide
	@tar -czf dist/tide-linux-amd64.tar.gz -C dist/tide-linux-amd64 tide
	@echo "==> 构建 Linux arm64..."
	@mkdir -p dist/tide-linux-arm64 && CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o dist/tide-linux-arm64/tide ./cmd/tide
	@tar -czf dist/tide-linux-arm64.tar.gz -C dist/tide-linux-arm64 tide
	@echo "==> 构建 Windows amd64..."
	@mkdir -p dist/tide-windows-amd64 && CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o dist/tide-windows-amd64/tide.exe ./cmd/tide
	@cd dist/tide-windows-amd64 && zip -q ../tide-windows-amd64.zip tide.exe
	@echo "==> 生成 SHA256 校验和..."
	@cd dist && (shasum -a 256 *.tar.gz *.zip > checksums.txt 2>/dev/null || sha256sum *.tar.gz *.zip > checksums.txt)
	@rm -rf dist/tide-darwin-amd64 dist/tide-darwin-arm64 dist/tide-linux-amd64 dist/tide-linux-arm64 dist/tide-windows-amd64
	@echo "==> 发布包已就绪！"
	@ls -lh dist/
