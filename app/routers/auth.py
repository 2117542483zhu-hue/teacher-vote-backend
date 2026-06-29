from fastapi import APIRouter, HTTPException

from ..database import get_db
from ..models import LoginRequest, StudentCreateRequest

router = APIRouter(tags=["认证"])


@router.post("/api/login")
def login(data: LoginRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, role, vote_status FROM users WHERE username=%s AND password=%s",
                (data.username, data.password),
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=400, detail="用户名或密码错误")
            return {
                "code": 200,
                "message": "登录成功",
                "data": {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"],
                    "vote_status": user["vote_status"],
                },
            }


@router.post("/api/register")
def register(data: StudentCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username=%s", (data.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="该用户名已被注册，请换一个")
            cursor.execute(
                "INSERT INTO users (username, password, role, vote_status) VALUES (%s,%s,'student',0)",
                (data.username, data.password),
            )
            conn.commit()
            return {"code": 200, "message": "注册成功，请登录"}
