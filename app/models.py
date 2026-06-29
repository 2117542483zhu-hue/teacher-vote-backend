from pydantic import BaseModel


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
