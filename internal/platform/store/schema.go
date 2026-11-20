package store

// Migrator 由各存储包实现，声明自己拥有的表。
//
// 让存储包自己声明表结构，而不是在 main 里罗列所有 model：
// 加一张表只需要在拥有它的包里改一处，main 无需知道细节。
type Migrator interface {
	// Schema 返回该包拥有的 GORM 行类型实例。
	Schema() []any
}
