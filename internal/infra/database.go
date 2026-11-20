// Package infra 提供基础设施：数据库连接、缓存与分布式锁。
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

// InitMySQL 建立 GORM MySQL 连接并配置连接池。
func InitMySQL(cfg *config.Config) (*gorm.DB, error) {
	dsn := cfg.Database.MySQL.BuildDSN()

	logLevel := gormlogger.Warn
	if !cfg.APP.IsProd() {
		logLevel = gormlogger.Info
	}

	// TranslateError 开启后，驱动原始错误会被翻译成 gorm 哨兵错误
	// （如唯一键冲突 → gorm.ErrDuplicatedKey），上层才能据此区分业务异常。
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{
		TranslateError: true,
		Logger:         gormlogger.Default.LogMode(logLevel),
		NowFunc:        func() time.Time { return time.Now().Local() },
	})
	if err != nil {
		// 保留原始错误，否则排障时分不清是 DSN 写错、网络不通还是鉴权失败。
		return nil, fmt.Errorf("连接 MySQL 失败: %w", err)
	}

	// 取出底层 *sql.DB 才能设置标准库的连接池参数。
	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("获取底层连接池失败: %w", err)
	}

	// 连接池三参数：
	//   MaxIdleConns    —— 空闲时保留的连接数，供下次复用、免重建握手；
	//   MaxOpenConns    —— 并发连接上限，超出部分在池上排队；
	//   ConnMaxLifetime —— 连接最长存活期，定期轮换，避免被 MySQL 的
	//                      wait_timeout 在服务端悄悄掐断。
	sqlDB.SetMaxIdleConns(cfg.Database.MySQL.MaxIdleConns)
	sqlDB.SetMaxOpenConns(cfg.Database.MySQL.MaxOpenConns)
	sqlDB.SetConnMaxLifetime(cfg.Database.MySQL.ConnMaxLifetime)

	// gorm.Open 是惰性建连，这里主动 Ping 一次，让配置错误在启动期暴露。
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := sqlDB.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("MySQL 连通性检查失败: %w", err)
	}

	return db, nil
}

// CloseMySQL 关闭连接池，用于优雅退出。
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

// InitRedis 创建 go-redis 客户端并做一次 PING 校验。
func InitRedis(cfg *config.Config) (*redis.Client, error) {
	r := cfg.Database.Redis

	client := redis.NewClient(&redis.Options{
		Addr:     r.Addr,
		Password: r.Password,
		DB:       r.DB,
		PoolSize: r.PoolSize,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := client.Ping(ctx).Err(); err != nil {
		_ = client.Close()
		return nil, fmt.Errorf("连接 Redis 失败: %w", err)
	}

	return client, nil
}

// CloseRedis 关闭客户端，用于优雅退出。
func CloseRedis(client *redis.Client) error {
	if client == nil {
		return nil
	}
	return client.Close()
}

// AutoMigrate 执行表结构迁移。
func AutoMigrate(db *gorm.DB, models ...any) error {
	if err := db.AutoMigrate(models...); err != nil {
		return fmt.Errorf("自动迁移失败: %w", err)
	}
	zap.L().Info("数据库迁移完成", zap.Int("tables", len(models)))
	return nil
}
