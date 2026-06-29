# =============================================================================
# 文件: app/routers/teachers.py — 教师管理路由（CRUD）
# 负责人: 人二 (管理员数据管理模块)
# 讲解要点:
#   1. RESTful API 设计 — GET查/POST增/PUT改/DELETE删 四种操作
#   2. 路径参数 {teacher_id} — FastAPI 自动解析为函数参数
#   3. 查询参数 name — 可选，实现模糊搜索功能
#   4. LIKE %s 模糊查询语法
#   5. 各接口对应的 SQL 语句及 PyMySQL 执行方式
# =============================================================================

from fastapi import APIRouter

from ..database import get_db
from ..models import TeacherCreateRequest

router = APIRouter(tags=["教师管理"])


# 人二讲解：查询教师列表 GET /api/teachers
# 支持可选的 ?name=关键词 模糊搜索，不传则返回全部教师
@router.get("/api/teachers")
def get_teachers(name: str = None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人二讲解：动态 SQL — 根据是否传入 name 参数决定查询方式
            # LIKE %关键词% 模糊匹配，%% 是 Python 字符串中 % 的转义写法
            if name:
                cursor.execute("SELECT * FROM teachers WHERE name LIKE %s", (f"%{name}%",))
            else:
                cursor.execute("SELECT * FROM teachers")
            return {"code": 200, "data": cursor.fetchall()}


# 人二讲解：添加教师 POST /api/teachers
# 接收 TeacherCreateRequest 中定义的所有字段
@router.post("/api/teachers")
def add_teacher(data: TeacherCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人二讲解：INSERT INTO — 字段与值一一对应
            # 新教师默认 vote_count=0, is_candidate=0（数据库表有默认值）
            cursor.execute(
                "INSERT INTO teachers (name, college, title, age, photo_url) VALUES (%s,%s,%s,%s,%s)",
                (data.name, data.college, data.title, data.age, data.photo_url),
            )
            conn.commit()
            return {"code": 200, "message": "添加教师成功"}


# 人二讲解：编辑教师 PUT /api/teachers/{teacher_id}
# {teacher_id} 是路径参数 — FastAPI 自动从 URL 中提取并转为 int
@router.put("/api/teachers/{teacher_id}")
def update_teacher(teacher_id: int, data: TeacherCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人二讲解：UPDATE SET — 根据主键 id 更新对应教师的所有字段
            cursor.execute(
                "UPDATE teachers SET name=%s,college=%s,title=%s,age=%s,photo_url=%s WHERE id=%s",
                (data.name, data.college, data.title, data.age, data.photo_url, teacher_id),
            )
            conn.commit()
            return {"code": 200, "message": "修改教师信息成功"}


# 人二讲解：删除教师 DELETE /api/teachers/{teacher_id}
@router.delete("/api/teachers/{teacher_id}")
def delete_teacher(teacher_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人二讲解：DELETE FROM — 根据主键删除，WHERE 条件必不可少
            cursor.execute("DELETE FROM teachers WHERE id=%s", (teacher_id,))
            conn.commit()
            return {"code": 200, "message": "删除教师成功"}
