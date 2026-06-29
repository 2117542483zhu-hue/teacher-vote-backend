# =============================================================================
# 文件: app/database.py — 数据库连接管理
# 负责人: 人二 (管理员数据管理模块)
# 讲解要点:
#   1. PyMySQL 连接 MySQL 数据库的基本流程
#   2. contextmanager 上下文管理器 — 自动管理资源（with 语句）
#   3. get_db() 中 try-finally 的作用 — 确保无论是否异常都关闭连接
#   4. HTTPException 处理数据库连接失败的情况
# =============================================================================

from contextlib import contextmanager
from fastapi import HTTPException
import pymysql

from .config import DB_CONFIG


# 人二讲解：创建数据库连接 — 调用 PyMySQL.connect 传入配置字典
# 如果 MySQL 未启动或配置错误，抛出 503 状态码（服务不可用）
def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG)
    except pymysql.err.OperationalError as e:
        raise HTTPException(status_code=503, detail=f"数据库连接失败: {e}")


# 人二讲解：上下文管理器 — 使用 @contextmanager 装饰器将生成器函数转为上下文管理器
# 使用方式: with get_db() as conn:
#              # 在此操作数据库
#          # 退出 with 块时自动执行 finally 中的 conn.close()
# 这样做的好处：
#   1. 自动关闭连接，不会因为忘记 close 导致连接泄漏
#   2. 即使代码抛异常，finally 也会确保连接被关闭
@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn      # 向 with 块提供连接对象
    finally:
        conn.close()    # 无论是否异常，都会关闭连接
