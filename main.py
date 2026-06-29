from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.config import UPLOAD_DIR
from app.routers import auth, teachers, students, vote, upload

app = FastAPI(title="我最喜爱的教师投票系统 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 注册各模块路由
app.include_router(auth.router)
app.include_router(teachers.router)
app.include_router(students.router)
app.include_router(vote.router)
app.include_router(upload.router)


@app.get("/")
def read_root():
    return {"message": "Python 后端已成功启动！"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
