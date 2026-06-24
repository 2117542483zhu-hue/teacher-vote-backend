from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pymysql
import uvicorn
import os
import uuid

app = FastAPI(title="我最喜爱的教师投票系统 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "zyn5525",
    "database": "teacher_vote",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


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


# ---------- Pydantic 模型 ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class TeacherCreateRequest(BaseModel):
    name: str
    college: str = None
    title: str = None
    age: int = None
    photo_url: str = "/uploads/default.jpg"


class RecommendRequest(BaseModel):
    teacher_ids: list[int]


class StudentCreateRequest(BaseModel):
    username: str
    password: str


class VoteRequest(BaseModel):
    student_id: int
    teacher_ids: list[int]


# ---------- 接口 0：测试 ----------

@app.get("/")
def read_root():
    return {"message": "Python 后端已成功启动！"}


# ---------- 接口 1：登录 ----------

@app.post("/api/login")
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


# ---------- 接口 2：学生注册 ----------

@app.post("/api/register")
def register(data: StudentCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username=%s", (data.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="该用户名已被注册，请换一个")
            cursor.execute(
                "INSERT INTO users (username, password, role, vote_status) VALUES (%s, %s, 'student', 0)",
                (data.username, data.password),
            )
            conn.commit()
            return {"code": 200, "message": "注册成功，请登录"}


# ---------- 接口 3：上传照片 ----------

@app.post("/api/upload")
def upload_photo(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(status_code=400, detail="仅支持 jpg、png、gif、webp 格式的图片")

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return {"code": 200, "data": f"/uploads/{filename}"}


# ---------- 教师管理 CRUD ----------

@app.get("/api/teachers")
def get_teachers(name: str = None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            if name:
                cursor.execute("SELECT * FROM teachers WHERE name LIKE %s", (f"%{name}%",))
            else:
                cursor.execute("SELECT * FROM teachers")
            return {"code": 200, "data": cursor.fetchall()}


@app.post("/api/teachers")
def add_teacher(data: TeacherCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO teachers (name, college, title, age, photo_url) VALUES (%s,%s,%s,%s,%s)",
                (data.name, data.college, data.title, data.age, data.photo_url),
            )
            conn.commit()
            return {"code": 200, "message": "添加教师成功"}


@app.put("/api/teachers/{teacher_id}")
def update_teacher(teacher_id: int, data: TeacherCreateRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE teachers SET name=%s,college=%s,title=%s,age=%s,photo_url=%s WHERE id=%s",
                (data.name, data.college, data.title, data.age, data.photo_url, teacher_id),
            )
            conn.commit()
            return {"code": 200, "message": "修改教师信息成功"}


@app.delete("/api/teachers/{teacher_id}")
def delete_teacher(teacher_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM teachers WHERE id=%s", (teacher_id,))
            conn.commit()
            return {"code": 200, "message": "删除教师成功"}


# ---------- 学生管理 CRUD ----------

@app.get("/api/students")
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


@app.post("/api/students")
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


@app.put("/api/students/{student_id}")
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


@app.delete("/api/students/{student_id}")
def delete_student(student_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM vote_records WHERE student_id=%s", (student_id,))
            cursor.execute("DELETE FROM users WHERE id=%s AND role='student'", (student_id,))
            conn.commit()
            return {"code": 200, "message": "删除学生成功"}


# ---------- 接口 7：管理员推荐候选人 ----------

@app.post("/api/admin/recommend")
def recommend_candidates(data: RecommendRequest):
    if len(data.teacher_ids) > 10:
        raise HTTPException(status_code=400, detail="最多只能推荐10名候选人！")

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE teachers SET is_candidate=0 WHERE is_candidate=1")
            if data.teacher_ids:
                placeholders = ",".join(["%s"] * len(data.teacher_ids))
                cursor.execute(
                    f"UPDATE teachers SET is_candidate=1 WHERE id IN ({placeholders})",
                    tuple(data.teacher_ids),
                )
            conn.commit()
            return {"code": 200, "message": "初选名单生成成功"}


# ---------- 接口 8：学生提交投票 ----------

@app.post("/api/student/vote")
def student_vote(data: VoteRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT vote_status FROM users WHERE id=%s", (data.student_id,))
            student = cursor.fetchone()
            if not student:
                raise HTTPException(status_code=404, detail="学生用户不存在")
            if student["vote_status"] != 0:
                raise HTTPException(status_code=400, detail="您已经提交过投票或投票已被作废，无法重复投票！")

            if len(data.teacher_ids) > 3:
                cursor.execute("UPDATE users SET vote_status=2 WHERE id=%s", (data.student_id,))
                conn.commit()
                return {"code": 200, "message": "投票已提交！但检测到您勾选超过3项，根据规则您的推荐结果已作废。"}

            if data.teacher_ids:
                # 批量更新票数
                placeholders = ",".join(["%s"] * len(data.teacher_ids))
                cursor.execute(
                    f"UPDATE teachers SET vote_count=vote_count+1 WHERE id IN ({placeholders})",
                    tuple(data.teacher_ids),
                )
                # 批量写入投票记录
                values = [(data.student_id, t_id) for t_id in data.teacher_ids]
                cursor.executemany(
                    "INSERT INTO vote_records (student_id, teacher_id) VALUES (%s,%s)", values
                )

            cursor.execute("UPDATE users SET vote_status=1 WHERE id=%s", (data.student_id,))
            conn.commit()
            return {"code": 200, "message": "投票成功！感谢您的参与。"}


# ---------- 接口 9：统计投票结果 ----------

@app.get("/api/vote/result")
def get_vote_result(sort_by_vote: bool = False):
    with get_db() as conn:
        with conn.cursor() as cursor:
            order = "vote_count DESC" if sort_by_vote else "id ASC"
            cursor.execute(f"SELECT * FROM teachers WHERE is_candidate=1 ORDER BY {order}")
            return {"code": 200, "data": cursor.fetchall()}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
