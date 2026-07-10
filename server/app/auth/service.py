# 认证业务服务层：负责用户账号持久化（CRUD）与认证用例编排（注册/登录/登出/更新）
"""认证业务服务层。

负责用户账号的持久化存储（CRUD）以及认证相关用例的编排，
包括注册、登录、登出、用户信息更新等操作。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserLogin, UserRead, UserRegister, UserUpdate
from app.auth.security import create_token, hash_password, revoke_token, verify_password
from app.infra.logging import get_logger
from app.infra.models import User

logger = get_logger(__name__)


# 将 User ORM 对象转换为对外响应的 UserRead 模型
def _read_user(user: User) -> UserRead:
    """将 User ORM 对象转换为 UserRead 响应模型。"""
    # 将 ORM 对象映射为对外响应的 UserRead 模型
    return UserRead.model_validate(user)


# 认证操作结果载体：统一封装成功/失败的返回数据
@dataclass
class AuthResult:
    """认证操作结果 — 统一成功/失败的数据载体。

    成功时 data 有值，失败时 error_field + error_message 有值。
    前端可根据 error_field 将错误绑定到对应表单字段。
    """
    success: bool = False
    data: dict | None = None
    # 失败时：错误对应的表单字段（username / password / email / "" 表示全局）
    error_field: str = ""
    # 失败时：面向用户的精确错误提示
    error_message: str = ""

    # 支持以字典方式访问 data 中的字段
    def __getitem__(self, key):
        if self.data is not None and key in self.data:
            return self.data[key]
        raise KeyError(key)


# 用户账号持久化层：负责用户记录的增删改查
class UserAccountStore:
    """用户账号持久化 — 负责 CRUD 操作。"""

    # 注册新用户：先查重，再写库，处理并发冲突
    async def register(self, session: AsyncSession, data: UserRegister) -> AuthResult:
        """注册新用户，返回 AuthResult。"""
        # 查询用户名是否已存在
        existing = (await session.exec(select(User).where(User.username == data.username))).first()
        # 用户名已存在，返回字段级错误
        if existing:
            logger.warning("[Auth] 注册失败，用户名已存在: %s", data.username)
            return AuthResult(error_field="username", error_message="该用户名已被注册，请换一个试试")

        # 构造用户对象，密码经哈希后存储
        user = User(
            username=data.username,
            password=hash_password(data.password),
            email=data.email,
        )
        session.add(user)
        # 提交事务，捕获唯一约束冲突（并发注册）
        try:
            await session.commit()
        except IntegrityError:
            # 并发冲突：回滚并返回字段级错误
            await session.rollback()
            logger.warning("[Auth] 注册并发冲突: %s", data.username)
            return AuthResult(error_field="username", error_message="该用户名已被注册，请换一个试试")
        # 提交后刷新对象并构造成功结果
        await session.refresh(user)
        # 注册成功，返回新建用户数据
        return AuthResult(success=True, data={"user": _read_user(user)})

    # 用户认证：校验用户名与密码，成功则签发 Token
    async def authenticate(self, session: AsyncSession, username: str, password: str) -> AuthResult:
        """验证用户名密码，返回 AuthResult。

        失败时 error_field 指向具体的表单字段，error_message 提供精确原因。
        """
        # 根据用户名查询用户记录
        user = (await session.exec(select(User).where(User.username == username))).first()
        # 用户不存在，返回字段级错误
        if not user:
            logger.warning("[Auth] 登录失败，用户不存在: %s", username)
            return AuthResult(error_field="username", error_message="该用户名未注册")

        # 刷新用户确保密码字段已加载
        await session.refresh(user)
        # 校验密码，不匹配则返回字段级错误
        if not verify_password(password, user.password):
            logger.warning("[Auth] 登录失败，密码错误: user_id=%s", user.id)
            return AuthResult(error_field="password", error_message="密码不正确，请重新输入")

        # 登录成功，记录日志并签发 Token
        logger.info("[Auth] 登录成功: user_id=%s", user.id)
        user_read = _read_user(user)
        # 调用安全模块创建 Token（写入白名单）
        token = await create_token(user.id, session)
        # 返回 Token 与用户信息
        # 认证成功，返回 Token 与用户信息
        return AuthResult(success=True, data={"token": token, "user": user_read})

    # 更新用户信息：仅更新提交的非空字段
    async def update(self, session: AsyncSession, user_id: int, data: UserUpdate) -> User | None:
        """更新用户信息，仅更新提交的非空字段。"""
        # 查询目标用户
        user = await session.get(User, user_id)
        # 用户不存在直接返回 None
        if not user:
            return None
        await session.refresh(user)
        # 提取提交的字段（排除未设置的字段）
        update_data = data.model_dump(exclude_unset=True)
        # 无更新内容时直接返回原用户
        if not update_data:
            return user
        # 应用更新并提交
        user.sqlmodel_update(update_data)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # 返回更新后的用户对象
        return user


# 认证用例编排层：组合账号存储层实现业务用例
class AuthUseCases:
    """认证相关用例：注册、登录、登出、更新。"""

    # 初始化用例层，注入账号存储依赖
    def __init__(self, account_store: UserAccountStore) -> None:
        self.account_store = account_store

    # 注册用例：委托账号存储层完成
    async def register(self, session: AsyncSession, data: UserRegister) -> AuthResult:
        """注册新用户。"""
        return await self.account_store.register(session, data)

    # 登录用例：委托账号存储层完成认证
    async def login(self, session: AsyncSession, data: UserLogin) -> AuthResult:
        """用户登录，验证凭据并签发 Token。"""
        return await self.account_store.authenticate(session, data.username, data.password)

    # 更新当前用户信息用例
    async def update_me(self, session: AsyncSession, user_id: int, data: UserUpdate) -> User | None:
        """更新当前用户信息。"""
        return await self.account_store.update(session, user_id, data)

    # 登出用例：撤销 Token 使其失效
    async def logout(self, session: AsyncSession, token: str) -> None:
        """用户登出，撤销 Token。"""
        await revoke_token(token, session)

    # 登出时更新用户画像（当前版本无兼容数据需同步）
    async def upsert_profile_on_logout(self, user_id: int) -> None:
        """登出时更新用户画像（V2 版本暂无需要同步的兼容性数据）。"""
        return None


# 模块级单例：共享的账号存储与用例实例
account_store = UserAccountStore()
auth_usecases = AuthUseCases(account_store)
