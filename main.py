from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pymysql
import uvicorn
import os
import shutil
import uuid

app = FastAPI(title="我最喜爱的教师投票系统 API")

# 配置跨域（CORS），允许你的 Vue 3 前端访问这个 Python 后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有前端源，开发阶段最省心
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库连接配置（请根据你 DataGrip 里的实际连接信息修改密码）
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "zyn5525",
    "database": "teacher_vote",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor  # 让返回的数据自动变成字典格式
}


def get_db_connection():
    """每次请求时获取数据库连接"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except pymysql.err.OperationalError as e:
        raise HTTPException(status_code=503, detail=f"数据库连接失败: {e}")


# ----- 定义前端传过来的数据格式 (Pydantic 模型) -----
class LoginRequest(BaseModel):
    username: str
    password: str
# 用于接收添加/修改教师时的表单数据
class TeacherCreateRequest(BaseModel):
    name: str
    college: str = None
    title: str = None
    age: int = None
    photo_url: str = "/uploads/default.jpg" # 默认头像

# 用于接收第一阶段管理员推荐候选人时的教师 ID 列表
class RecommendRequest(BaseModel):
    teacher_ids: list[int]  # 接收一个数字数组，例如 [1, 2, 3]


# 用于接收添加/修改学生时的表单数据
class StudentCreateRequest(BaseModel):
    username: str
    password: str
    role: str = "student"

# 用于接收学生投票时提交的教师 ID 数组
class VoteRequest(BaseModel):
    student_id: int
    teacher_ids: list[int]  # 接收选中的教师 ID 列表，如 [1, 3, 5]

# ----- 接口 1：登录接口 -----
@app.post("/api/login")
def login(data: LoginRequest):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 去数据库查有没有这个用户
            sql = "SELECT id, username, role, vote_status FROM users WHERE username = %s AND password = %s"
            cursor.execute(sql, (data.username, data.password))
            user = cursor.fetchone()

            if user:
                # 查到了，返回用户信息给前端
                return {
                    "code": 200,
                    "message": "登录成功",
                    "data": {
                        "id": user["id"],
                        "username": user["username"],
                        "role": user["role"],
                        "vote_status": user["vote_status"]
                    }
                }
            else:
                # 没查到，抛出 400 错误
                raise HTTPException(status_code=400, detail="用户名或密码错误")
    finally:
        connection.close()


# ----- 接口 1.5：学生注册 -----
@app.post("/api/register")
def register(data: LoginRequest):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (data.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="该用户名已被注册，请换一个")
            # 插入新学生，角色固定为 student
            cursor.execute(
                "INSERT INTO users (username, password, role, vote_status) VALUES (%s, %s, 'student', 0)",
                (data.username, data.password)
            )
            connection.commit()
            return {"code": 200, "message": "注册成功，请登录"}
    finally:
        connection.close()


# 上传目录（不存在则自动创建）
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 挂载静态文件目录，让前端能访问上传的照片
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 测试接口，看看后端通不通
@app.get("/")
def read_root():
    return {"message": "Python 后端已成功启动！"}


# ----- 接口 1.8：上传照片 -----
@app.post("/api/upload")
async def upload_photo(file: UploadFile = File(...)):
    # 只允许图片格式
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(status_code=400, detail="仅支持 jpg、png、gif、webp 格式的图片")

    # 用 uuid 生成唯一文件名，防止覆盖
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 保存文件到 uploads 目录
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 返回访问 URL
    return {"code": 200, "data": f"/uploads/{filename}"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


# ----- 接口 2：获取所有教师列表（包含模糊查询） -----
@app.get("/api/teachers")
def get_teachers(name: str = None):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 如果传了 name 就按名字模糊搜索，否则查全部
            if name:
                sql = "SELECT * FROM teachers WHERE name LIKE %s"
                cursor.execute(sql, (f"%{name}%",))
            else:
                sql = "SELECT * FROM teachers"
                cursor.execute(sql)
            teachers = cursor.fetchall()
            return {"code": 200, "data": teachers}
    finally:
        connection.close()


# ----- 接口 3：添加教师 -----
@app.post("/api/teachers")
def add_teacher(data: TeacherCreateRequest):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO teachers (name, college, title, age, photo_url) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (data.name, data.college, data.title, data.age, data.photo_url))
            connection.commit()  # 增删改操作必须 commit 提交事务
            return {"code": 200, "message": "添加教师成功"}
    finally:
        connection.close()


# ----- 接口 4：修改教师信息 -----
@app.put("/api/teachers/{teacher_id}")
def update_teacher(teacher_id: int, data: TeacherCreateRequest):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE teachers SET name=%s, college=%s, title=%s, age=%s, photo_url=%s WHERE id=%s"
            cursor.execute(sql, (data.name, data.college, data.title, data.age, data.photo_url, teacher_id))
            connection.commit()
            return {"code": 200, "message": "修改教师信息成功"}
    finally:
        connection.close()


# ----- 接口 5：删除教师 -----
@app.delete("/api/teachers/{teacher_id}")
def delete_teacher(teacher_id: int):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM teachers WHERE id = %s"
            cursor.execute(sql, (teacher_id,))
            connection.commit()
            return {"code": 200, "message": "删除教师成功"}
    finally:
        connection.close()


# ----- 接口 6：学生管理 CRUD -----

# 6.1 获取所有学生列表（支持模糊搜索用户名）
@app.get("/api/students")
def get_students(username: str = None):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if username:
                sql = "SELECT id, username, role, vote_status FROM users WHERE role = 'student' AND username LIKE %s"
                cursor.execute(sql, (f"%{username}%",))
            else:
                sql = "SELECT id, username, role, vote_status FROM users WHERE role = 'student'"
                cursor.execute(sql)
            students = cursor.fetchall()
            return {"code": 200, "data": students}
    finally:
        connection.close()

# 6.2 添加学生（管理员在后台添加）
@app.post("/api/students")
def add_student(data: StudentCreateRequest):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (data.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")
            sql = "INSERT INTO users (username, password, role, vote_status) VALUES (%s, %s, %s, 0)"
            cursor.execute(sql, (data.username, data.password, data.role))
            connection.commit()
            return {"code": 200, "message": "添加学生成功"}
    finally:
        connection.close()


# 接口 6.2b：学生自助注册
@app.post("/api/register")
def student_register(data: StudentCreateRequest):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (data.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")
            sql = "INSERT INTO users (username, password, role, vote_status) VALUES (%s, %s, 'student', 0)"
            cursor.execute(sql, (data.username, data.password))
            connection.commit()
            return {"code": 200, "message": "注册成功"}
    finally:
        connection.close()

# 6.3 修改学生信息
@app.put("/api/students/{student_id}")
def update_student(student_id: int, data: StudentCreateRequest):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 如果密码为空或 "__KEEP_OLD__"，则保留原密码
            if not data.password or data.password == "__KEEP_OLD__":
                cursor.execute("SELECT password FROM users WHERE id = %s", (student_id,))
                existing = cursor.fetchone()
                if existing:
                    pwd = existing["password"]
                else:
                    raise HTTPException(status_code=404, detail="学生用户不存在")
            else:
                pwd = data.password
            sql = "UPDATE users SET username=%s, password=%s, role=%s WHERE id=%s"
            cursor.execute(sql, (data.username, pwd, data.role, student_id))
            connection.commit()
            return {"code": 200, "message": "修改学生信息成功"}
    finally:
        connection.close()

# 6.4 删除学生
@app.delete("/api/students/{student_id}")
def delete_student(student_id: int):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 先删除该学生的投票记录（如果投过票）
            cursor.execute("DELETE FROM vote_records WHERE student_id = %s", (student_id,))
            sql = "DELETE FROM users WHERE id = %s AND role = 'student'"
            cursor.execute(sql, (student_id,))
            connection.commit()
            return {"code": 200, "message": "删除学生成功"}
    finally:
        connection.close()


# ----- 接口 7：第一阶段——管理员确认推荐候选人（最多10人） -----
@app.post("/api/admin/recommend")
def recommend_candidates(data: RecommendRequest):
    # 题目要求：最多推荐 10 名教师
    if len(data.teacher_ids) > 10:
        raise HTTPException(status_code=400, detail="最多只能推荐10名候选人！")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. 先把所有教师的候选状态清空（重置）
            cursor.execute("UPDATE teachers SET is_candidate = 0")

            # 2. 如果管理员提交了候选人，批量把这几个教师的 is_candidate 设为 1
            if data.teacher_ids:
                # 构造类似 (1, 2, 3) 的 SQL 占位符字符串
                format_strings = ','.join(['%s'] * len(data.teacher_ids))
                sql = f"UPDATE teachers SET is_candidate = 1 WHERE id IN ({format_strings})"
                cursor.execute(sql, tuple(data.teacher_ids))

            connection.commit()
            return {"code": 200, "message": "初选名单生成成功"}
    finally:
        connection.close()


# ----- 接口 8：第二阶段——学生提交投票（包含超3票作废的硬核逻辑） -----
@app.post("/api/student/vote")
def student_vote(data: VoteRequest):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. 校验该学生是否已经投过票
            cursor.execute("SELECT vote_status FROM users WHERE id = %s", (data.student_id,))
            student = cursor.fetchone()
            if not student:
                raise HTTPException(status_code=404, detail="学生用户不存在")
            if student["vote_status"] != 0:
                raise HTTPException(status_code=400, detail="您已经提交过投票或投票已被作废，无法重复投票！")

            # 2. 核心判断：如果学生提交的选票数 > 3 票
            if len(data.teacher_ids) > 3:
                # 触发作废逻辑：更改学生状态为 2 (已作废)，但不给任何老师加票
                cursor.execute("UPDATE users SET vote_status = 2 WHERE id = %s", (data.student_id,))
                connection.commit()
                # 依旧返回成功，但提示其结果作废
                return {"code": 200, "message": "投票已提交！但检测到您勾选超过3项，根据规则您的推荐结果已作废。"}

            # 3. 正常计票逻辑（<= 3票）
            if data.teacher_ids:
                for t_id in data.teacher_ids:
                    # 给对应的教师票数 +1
                    cursor.execute("UPDATE teachers SET vote_count = vote_count + 1 WHERE id = %s", (t_id,))
                    # 写入明细表备份记录
                    cursor.execute("INSERT INTO vote_records (student_id, teacher_id) VALUES (%s, %s)", (data.student_id, t_id))

            # 将学生状态改为 1 (已正常投票)
            cursor.execute("UPDATE users SET vote_status = 1 WHERE id = %s", (data.student_id,))
            connection.commit()
            return {"code": 200, "message": "投票成功！感谢您的参与。"}
    finally:
        connection.close()


# ----- 接口 9：第三阶段——统计投票结果（支持票数倒序排序） -----
@app.get("/api/vote/result")
def get_vote_result(sort_by_vote: bool = False):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 只统计管理员推荐出来的 10 名初选教师
            if sort_by_vote:
                # 按票数从多到少排序
                sql = "SELECT * FROM teachers WHERE is_candidate = 1 ORDER BY vote_count DESC"
            else:
                # 默认按原本的 ID 排序
                sql = "SELECT * FROM teachers WHERE is_candidate = 1 ORDER BY id ASC"

            cursor.execute(sql)
            results = cursor.fetchall()
            return {"code": 200, "data": results}
    finally:
        connection.close()