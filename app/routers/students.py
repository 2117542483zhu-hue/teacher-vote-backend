from fastapi import APIRouter, HTTPException

from ..database import get_db
from ..models import StudentCreateRequest

router = APIRouter(tags=["学生管理"])


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


@router.post("/api/students")
def add_student(data: StudentCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username=%s", (data.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")
            cursor.execute(
                "INSERT INTO users (username, password, role, vote_status) VALUES (%s,%s,'student',0)",
                (data.username, data.password),
            )
            conn.commit()
            return {"code": 200, "message": "添加学生成功"}


@router.put("/api/students/{student_id}")
def update_student(student_id: int, data: StudentCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id=%s", (student_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="学生用户不存在")
            cursor.execute(
                "UPDATE users SET username=%s, password=COALESCE(NULLIF(%s,''),NULLIF(%s,'__KEEP_OLD__'),password) WHERE id=%s",
                (data.username, data.password, data.password, student_id),
            )
            conn.commit()
            return {"code": 200, "message": "修改学生信息成功"}


@router.delete("/api/students/{student_id}")
def delete_student(student_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 查询学生是否存在及投票状态
            cursor.execute("SELECT id, vote_status FROM users WHERE id=%s AND role='student'", (student_id,))
            student = cursor.fetchone()
            if not student:
                raise HTTPException(status_code=404, detail="学生不存在")

            # 如果学生已投票(vote_status=1)，需要将对应教师的票数减回
            if student["vote_status"] == 1:
                cursor.execute("SELECT teacher_id FROM vote_records WHERE student_id=%s", (student_id,))
                records = cursor.fetchall()
                for record in records:
                    cursor.execute(
                        "UPDATE teachers SET vote_count = GREATEST(vote_count - 1, 0) WHERE id = %s",
                        (record["teacher_id"],),
                    )

            # 删除投票记录和学生用户
            cursor.execute("DELETE FROM vote_records WHERE student_id=%s", (student_id,))
            cursor.execute("DELETE FROM users WHERE id=%s AND role='student'", (student_id,))
            conn.commit()
            return {"code": 200, "message": "删除学生成功"}
