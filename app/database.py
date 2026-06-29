from contextlib import contextmanager
from fastapi import HTTPException
import pymysql

from .config import DB_CONFIG


def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG)
    except pymysql.err.OperationalError as e:
        raise HTTPException(status_code=503, detail=f"数据库连接失败: {e}")


@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
