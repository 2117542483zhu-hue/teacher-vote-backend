# =============================================================================
# 文件: app/routers/auth.py — 用户认证路由（登录 + 注册）
# 负责人: 人一 (用户认证与权限体系)
# 讲解要点:
#   1. APIRouter — FastAPI 模块化路由，tags 用于 API 文档分组
#   2. 登录流程: 查 users 表 → 验证密码 → 返回 role 和 vote_status
#   3. 注册流程: 查重 → INSERT → 返回成功
#   4. HTTPException — 业务异常处理，前端 Axios 拦截器统一捕获
#   5. 返回格式统一为 { code: 200, message/data } 便于前端拦截器解包
# =============================================================================

from fastapi import APIRouter, HTTPException

from ..database import get_db
from ..models import LoginRequest, StudentCreateRequest

router = APIRouter(tags=["认证"])


# 人一讲解：登录接口 POST /api/login
# 1. 接收用户名密码 → 2. 查数据库验证 → 3. 返回用户信息（id/role/vote_status）
# 前端拿到 role 后决定跳转到管理端 (/admin) 还是学生端 (/student)
@router.post("/api/login")
def login(data: LoginRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人一讲解：参数化查询 — %s 是占位符，PyMySQL 自动转义防止 SQL 注入
            cursor.execute(
                "SELECT id, username, role, vote_status FROM users WHERE username=%s AND password=%s",
                (data.username, data.password),
            )
            user = cursor.fetchone()
            # 人一讲解：fetchone() 返回单行字典，如果查不到返回 None
            if not user:
                raise HTTPException(status_code=400, detail="用户名或密码错误")
            # 人一讲解：统一返回格式 — code=200 表示成功，data 放业务数据
            # 前端 Axios 拦截器看到 code=200 自动解包返回 data
            return {
                "code": 200,
                "message": "登录成功",
                "data": {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"],           # "admin" 或 "student"
                    "vote_status": user["vote_status"],  # 0=未投 1=已投 2=作废
                },
            }


# 人一讲解：注册接口 POST /api/register
# 1. 检查用户名是否已存在 → 2. 写入新用户（默认 role='student'）
# 管理员账号由数据库预设，注册只能创建学生账号
@router.post("/api/register")
def register(data: StudentCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人一讲解：先查重 — 用户名唯一约束
            cursor.execute("SELECT id FROM users WHERE username=%s", (data.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="该用户名已被注册，请换一个")
            # 人一讲解：插入新用户 — vote_status=0 表示"未投票"初始状态
            cursor.execute(
                "INSERT INTO users (username, password, role, vote_status) VALUES (%s,%s,'student',0)",
                (data.username, data.password),
            )
            # 人一讲解：commit() 提交事务 — 不调用则数据不会真正写入数据库
            conn.commit()
            return {"code": 200, "message": "注册成功，请登录"}
