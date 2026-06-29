# =============================================================================
# 文件: app/routers/students.py — 学生管理路由（CRUD）
# 负责人: 人二 (管理员数据管理模块)
# 讲解要点:
#   1. 学生查询 — 只返回 role='student' 的用户，不显示管理员
#   2. 添加学生时的用户名去重校验
#   3. 编辑学生 — COALESCE + NULLIF 实现"留空不修改密码"机制
#   4. 删除学生 — 先退回已投的票，再删投票记录，最后删用户（事务性操作）
#   5. GREATEST(vote_count - 1, 0) 防止票数变成负数
# =============================================================================

from fastapi import APIRouter, HTTPException

from ..database import get_db
from ..models import StudentCreateRequest

router = APIRouter(tags=["学生管理"])


# 人二讲解：查询学生列表 GET /api/students
# 只查 role='student' 的用户，排除管理员
# 支持可选的 ?username=关键词 模糊搜索
@router.get("/api/students")
def get_students(username: str = None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            if username:
                cursor.execute(
                    "SELECT id, username, role, vote_status FROM users WHERE role='student' AND username LIKE %s",
                    (f"%{username}%",),
                )
            else:
                cursor.execute("SELECT id, username, role, vote_status FROM users WHERE role='student'")
            return {"code": 200, "data": cursor.fetchall()}


# 人二讲解：添加学生 POST /api/students
# 管理员可手动添加学生账号
@router.post("/api/students")
def add_student(data: StudentCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人二讲解：用户名去重检查
            cursor.execute("SELECT id FROM users WHERE username=%s", (data.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")
            cursor.execute(
                "INSERT INTO users (username, password, role, vote_status) VALUES (%s,%s,'student',0)",
                (data.username, data.password),
            )
            conn.commit()
            return {"code": 200, "message": "添加学生成功"}


# 人二讲解：编辑学生 PUT /api/students/{student_id}
# 核心设计：如果前端传 '__KEEP_OLD__' 或空字符串，则保留原密码不变
@router.put("/api/students/{student_id}")
def update_student(student_id: int, data: StudentCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人二讲解：先验证学生是否存在
            cursor.execute("SELECT id FROM users WHERE id=%s", (student_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="学生用户不存在")
            # 人二讲解：COALESCE + NULLIF 组合实现"留空不修改密码"
            # NULLIF(password, '') — 空字符串转 NULL
            # NULLIF(password, '__KEEP_OLD__') — 占位符转 NULL
            # COALESCE(...password) — 三者依次尝试，直到取到非 NULL 值
            cursor.execute(
                "UPDATE users SET username=%s, password=COALESCE(NULLIF(%s,''),NULLIF(%s,'__KEEP_OLD__'),password) WHERE id=%s",
                (data.username, data.password, data.password, student_id),
            )
            conn.commit()
            return {"code": 200, "message": "修改学生信息成功"}


# 人二讲解：删除学生 DELETE /api/students/{student_id}
# 关键：删除已投票的学生时，需要先将其投出的票数从对应教师的 vote_count 中扣回
# 这是一个小型事务操作——多步 SQL 要么全部成功，要么全部失败
@router.delete("/api/students/{student_id}")
def delete_student(student_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人二讲解：1. 查询学生是否存在及投票状态
            cursor.execute("SELECT id, vote_status FROM users WHERE id=%s AND role='student'", (student_id,))
            student = cursor.fetchone()
            if not student:
                raise HTTPException(status_code=404, detail="学生不存在")

            # 人二讲解：2. 如果学生已投票(vote_status=1)，需要将对应教师的票数减回
            # GREATEST(vote_count - 1, 0) 确保票数不会变成负数
            if student["vote_status"] == 1:
                cursor.execute("SELECT teacher_id FROM vote_records WHERE student_id=%s", (student_id,))
                records = cursor.fetchall()
                for record in records:
                    cursor.execute(
                        "UPDATE teachers SET vote_count = GREATEST(vote_count - 1, 0) WHERE id = %s",
                        (record["teacher_id"],),
                    )

            # 人二讲解：3. 先删投票记录（外键约束），再删用户
            cursor.execute("DELETE FROM vote_records WHERE student_id=%s", (student_id,))
            cursor.execute("DELETE FROM users WHERE id=%s AND role='student'", (student_id,))
            conn.commit()
            return {"code": 200, "message": "删除学生成功"}
