// Package infra 提供基础设施装配：MySQL、Redis 与迁移。
//
// 与旧结构的区别：不再有 llm.go / lock.go。
// 模型装配归 runtime（多 Agent 共享），会话锁已随新架构取消
// （异步任务与官方 Middleware 不需要跨进程锁）。
package infra

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	gormlogger "gorm.io/gorm/logger"

	"mentorly/internal/config"
)

// InitMySQL 连接 MySQL。
//
// 连接失败必须返回错误让进程退出：数据库是硬依赖，
// 带病启动只会让所有请求在运行时报错。
func InitMySQL(cfg config.MySQLConfig, log *zap.Logger) (*gorm.DB, error) {
	gormCfg := &gorm.Config{
		Logger: gormlogger.Default.LogMode(gormlogger.Warn),
		// 表名不做复数化：本项目所有 TableName 都是显式声明的，
		// 关闭命名策略可以避免意外差异。
		NamingStrategy: nil,
	}

	db, err := gorm.Open(mysql.Open(cfg.BuildDSN()), gormCfg)
	if err != nil {
		return nil, fmt.Errorf("连接 MySQL 失败: %w", err)
	}

	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("获取 MySQL 连接池失败: %w", err)
	}

	if cfg.MaxIdleConns > 0 {
		sqlDB.SetMaxIdleConns(cfg.MaxIdleConns)
	}
	if cfg.MaxOpenConns > 0 {
		sqlDB.SetMaxOpenConns(cfg.MaxOpenConns)
	}
	if cfg.ConnMaxLifetime > 0 {
		sqlDB.SetConnMaxLifetime(cfg.ConnMaxLifetime)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := sqlDB.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("MySQL 连通性检查失败: %w", err)
	}

	log.Info("MySQL 连接成功", zap.String("database", cfg.Database))
	return db, nil
}

// CloseMySQL 关闭连接池。
func CloseMySQL(db *gorm.DB) error {
	if db == nil {
		return nil
	}
	sqlDB, err := db.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}

// InitRedis 连接 Redis。
//
// 返回 (nil, nil) 表示未配置：Redis 在当前架构中是可选依赖，
// 不应因为它缺失而拒绝启动。
func InitRedis(cfg config.RedisConfig, log *zap.Logger) (*redis.Client, error) {
	if cfg.Addr == "" {
		log.Info("未配置 Redis，跳过")
		return nil, nil
	}

	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.Addr,
		Password: cfg.Password,
		DB:       cfg.DB,
	})
	if cfg.PoolSize > 0 {
		rdb.Options().PoolSize = cfg.PoolSize
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		// 连接失败不阻塞启动：Redis 只用于就绪探针与未来扩展。
		_ = rdb.Close()
		log.Warn("Redis 连接失败，将以未配置状态继续", zap.Error(err))
		return nil, nil
	}

	log.Info("Redis 连接成功", zap.String("addr", cfg.Addr))
	return rdb, nil
}

// CloseRedis 关闭 Redis 连接。
func CloseRedis(rdb *redis.Client) error {
	if rdb == nil {
		return nil
	}
	return rdb.Close()
}

// AutoMigrate 建表。
//
// 只做「新增表与新增列」，不做删列与改类型：
// 破坏性变更必须走 migrations/ 下的显式 SQL，
// 由人确认后执行，避免启动时静默丢数据。
func AutoMigrate(db *gorm.DB, models []any, log *zap.Logger) error {
	if len(models) == 0 {
		return nil
	}
	if err := db.AutoMigrate(models...); err != nil {
		return fmt.Errorf("自动迁移失败: %w", err)
	}
	log.Info("数据库表结构已就绪", zap.Int("tables", len(models)))
	return nil
}
