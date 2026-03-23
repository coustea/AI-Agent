import redis
from typing import Optional, List, Dict, Union, Any


class RedisService:
    """
    Redis 操作封装类
    提供连接池管理以及对常见数据结构（String, List, Hash, Set）的操作封装。
    """

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None,
                 **kwargs):
        """
        初始化 Redis 连接池
        """
        try:
            self.pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,  # 自动将返回的 bytes 解码为 str
                **kwargs
            )
            self.client = redis.Redis(connection_pool=self.pool)

            # 初始化时测试连接
            self.client.ping()
        except redis.ConnectionError as e:
            print(f"Redis 初始化连接失败: {e}")
            raise

    # ================= 1. 通用 Key 操作 =================

    def delete(self, *keys: str) -> int:
        """删除一个或多个 key"""
        return self.client.delete(*keys)

    def exists(self, key: str) -> bool:
        """检查 key 是否存在"""
        return self.client.exists(key) > 0

    def expire(self, key: str, time: int) -> bool:
        """为 key 设置过期时间（秒）"""
        return self.client.expire(key, time)

    # ================= 2. String (字符串) 操作 =================

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置键值对，ex 为过期时间（秒）"""
        return self.client.set(key, value, ex=ex)

    def get(self, key: str) -> Optional[str]:
        """获取键的值"""
        return self.client.get(key)

    # ================= 3. List (列表) 操作 =================

    def lpush(self, key: str, *values: Any) -> int:
        """从列表左侧插入一个或多个值"""
        return self.client.lpush(key, *values)

    def rpush(self, key: str, *values: Any) -> int:
        """从列表右侧插入一个或多个值"""
        return self.client.rpush(key, *values)

    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        """获取列表指定范围内的元素（默认获取全部）"""
        return self.client.lrange(key, start, end)

    # ================= 4. Hash (哈希) 操作 =================

    def hset(self, name: str, key: str, value: Any) -> int:
        """设置 Hash 表中的字段和值"""
        return self.client.hset(name, key, value)

    def hget(self, name: str, key: str) -> Optional[str]:
        """获取 Hash 表中指定字段的值"""
        return self.client.hget(name, key)

    def hgetall(self, name: str) -> Dict[str, str]:
        """获取 Hash 表中的所有字段和值"""
        return self.client.hgetall(name)

    # ================= 5. Set (集合) 操作 =================

    def sadd(self, name: str, *values: Any) -> int:
        """向集合中添加一个或多个元素"""
        return self.client.sadd(name, *values)

    def smembers(self, name: str) -> set:
        """获取集合中的所有元素"""
        return self.client.smembers(name)