from fastapi import APIRouter

from ..database import get_db
from ..models import TeacherCreateRequest

router = APIRouter(tags=["教师管理"])


@router.get("/api/teachers")
def get_teachers(name: str = None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            if name:
                cursor.execute("SELECT * FROM teachers WHERE name LIKE %s", (f"%{name}%",))
            else:
                cursor.execute("SELECT * FROM teachers")
            return {"code": 200, "data": cursor.fetchall()}


@router.post("/api/teachers")
def add_teacher(data: TeacherCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO teachers (name, college, title, age, photo_url) VALUES (%s,%s,%s,%s,%s)",
                (data.name, data.college, data.title, data.age, data.photo_url),
            )
            conn.commit()
            return {"code": 200, "message": "添加教师成功"}


@router.put("/api/teachers/{teacher_id}")
def update_teacher(teacher_id: int, data: TeacherCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE teachers SET name=%s,college=%s,title=%s,age=%s,photo_url=%s WHERE id=%s",
                (data.name, data.college, data.title, data.age, data.photo_url, teacher_id),
            )
            conn.commit()
            return {"code": 200, "message": "修改教师信息成功"}


@router.delete("/api/teachers/{teacher_id}")
def delete_teacher(teacher_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM teachers WHERE id=%s", (teacher_id,))
            conn.commit()
            return {"code": 200, "message": "删除教师成功"}
