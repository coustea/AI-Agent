from datetime import datetime
from typing import Optional

from api.db.models import User


class UserMemoryRepository:
    def __init__(self):
        pass

    # ================= CRUD 操作 =================

    def get_user_memory(self, user_id: int) -> Optional[str]:
        """获取用户的长期记忆。"""
        from api.db.models import settings

        # 连接到 agent 数据库
        import pymysql

        conn = pymysql.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
        )
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT memory_summary FROM user_memory WHERE user_id = %s", (user_id,)
            )
            result = cursor.fetchone()

            if result:
                return result[0]
            return None
        finally:
            cursor.close()
            conn.close()

    def set_user_memory(self, user_id: int, memory_summary: str) -> bool:
        """设置用户的长期记忆（存在则更新，不存在则创建）。"""
        from api.db.models import settings

        import pymysql

        conn = pymysql.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
        )
        cursor = conn.cursor()

        try:
            # 检查是否已存在
            cursor.execute("SELECT id FROM user_memory WHERE user_id = %s", (user_id,))
            existing = cursor.fetchone()

            if existing:
                # 更新
                cursor.execute(
                    "UPDATE user_memory SET memory_summary = %s, updated_at = NOW() WHERE user_id = %s",
                    (memory_summary, user_id),
                )
            else:
                # 插入
                cursor.execute(
                    "INSERT INTO user_memory (user_id, memory_summary) VALUES (%s, %s)",
                    (user_id, memory_summary),
                )

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def update_user_memory(self, user_id: int, memory_summary: str) -> bool:
        """更新用户的长期记忆。"""
        from api.db.models import settings

        import pymysql

        conn = pymysql.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
        )
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE user_memory SET memory_summary = %s, updated_at = NOW() WHERE user_id = %s",
                (memory_summary, user_id),
            )
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows > 0
        except Exception as e:
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def delete_user_memory(self, user_id: int) -> bool:
        """删除用户的长期记忆。"""
        from api.db.models import settings

        import pymysql

        conn = pymysql.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
        )
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM user_memory WHERE user_id = %s", (user_id,))
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows > 0
        except Exception as e:
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def check_memory_exists(self, user_id: int) -> bool:
        """检查用户的长期记忆是否存在。"""
        memory = self.get_user_memory(user_id)
        return memory is not None and len(memory.strip()) > 0
