.PHONY: build run test clean

# 编译生成名为 coustea 的可执行程序
build:
	go build -o coustea ./cmd/coustea

# 直接运行 coustea
run:
	go run ./cmd/coustea

# 运行单元测试
test:
	go test -v ./internal/...

# 清理构建产物与临时文件
clean:
	rm -f coustea test_config.json
