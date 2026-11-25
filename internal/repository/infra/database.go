// Package infra 提供 MySQL 连接与迁移。
package infra

import (
	"context"
	"fmt"
	"time"

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
		Logger:         gormlogger.Default.LogMode(gormlogger.Warn),
		TranslateError: true,
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
		_ = sqlDB.Close()
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

// AutoMigrate 建表。
//
// 使用 GORM 同步模型，不执行项目自定义的数据迁移脚本。
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
