# =============================================================================
# 文件: app/models.py — Pydantic 请求体数据模型
# 负责人: 三人共用（各取所需）
#   人一讲解: LoginRequest, StudentCreateRequest（注册部分）
#   人二讲解: TeacherCreateRequest, StudentCreateRequest（管理部分）
#   人三讲解: RecommendRequest, VoteRequest
# 讲解要点:
#   1. Pydantic BaseModel — FastAPI 自动校验请求体格式
#   2. 类型注解 — str/int/list[int] 定义字段类型
#   3. 默认值 — = None 表示可选字段
#   4. FastAPI 收到请求时自动将 JSON 反序列化为这些 Python 对象
# =============================================================================

from pydantic import BaseModel


# 人一讲解：登录请求体
# FastAPI 会自动校验: username 和 password 必须是字符串，缺失则返回 422 错误
class LoginRequest(BaseModel):
    username: str
    password: str


# 人二讲解：教师创建/编辑请求体
# college、title、age、photo_url 有默认值 = None，表示可选字段
# photo_url 默认指向 default.jpg（默认头像）
class TeacherCreateRequest(BaseModel):
    name: str
    college: str = None
    title: str = None
    age: int = None
    photo_url: str = "/uploads/default.jpg"


# 人三讲解：候选人推荐请求体
# teacher_ids 是一个整数列表，前端将选中的教师 ID 数组发过来
# FastAPI 会自动校验: 必须是整数组成的列表
class RecommendRequest(BaseModel):
    teacher_ids: list[int]


# 人一 + 人二讲解：学生创建请求体
# 人一负责注册功能，人二负责管理功能 — 两者共用同一个请求体模型
# role 字段在管理端可设置为 admin 或 student
class StudentCreateRequest(BaseModel):
    username: str
    password: str


# 人三讲解：投票请求体
# student_id 标识哪个学生在投票
# teacher_ids 是学生选中的教师 ID 列表（最多 3 个，后端额外校验）
class VoteRequest(BaseModel):
    student_id: int
    teacher_ids: list[int]
