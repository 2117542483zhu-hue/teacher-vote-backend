# =============================================================================
# 文件: main.py — FastAPI 应用入口
# 负责人: 人一 (用户认证与权限体系)
# 讲解要点:
#   1. FastAPI 应用创建与标题设置
#   2. CORS 中间件 — 为什么需要跨域、如何配置 allow_origins=["*"]
#   3. StaticFiles 静态文件挂载 — 让前端能通过 URL 访问上传的照片
#   4. include_router 路由注册机制 — 各功能模块如何"插拔式"挂载
#   5. uvicorn.run 启动参数 — host="0.0.0.0" 允许局域网访问，reload=True 热更新
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.config import UPLOAD_DIR
from app.routers import auth, teachers, students, vote, upload

# 人一讲解：创建 FastAPI 应用实例，title 会显示在自动生成的 API 文档中
app = FastAPI(title="我最喜爱的教师投票系统 API")

# 人一讲解：CORS 跨域中间件 — 前端运行在 localhost:5173，后端在 localhost:8000
# 浏览器默认禁止跨域请求，必须添加此中间件才能让前端正常调用后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 允许所有来源（生产环境应限制为具体域名）
    allow_credentials=True,    # 允许携带 Cookie
    allow_methods=["*"],       # 允许所有 HTTP 方法（GET/POST/PUT/DELETE 等）
    allow_headers=["*"],       # 允许所有请求头
)

# 人一讲解：挂载静态文件目录 — /uploads 路径映射到本地 uploads 文件夹
# 前端访问 http://localhost:8000/uploads/xxx.jpg 即可看到上传的照片
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 人一讲解：注册各功能模块的路由 — 采用 FastAPI 的 Router 机制实现模块化拆分
# 每个模块独立管理自己的 API 端点，main.py 只负责"拼装"
app.include_router(auth.router)      # 人一负责：登录/注册
app.include_router(teachers.router)  # 人二负责：教师 CRUD
app.include_router(students.router)  # 人二负责：学生 CRUD
app.include_router(vote.router)      # 人三负责：投票/推荐/统计/重置
app.include_router(upload.router)    # 人二负责：照片上传


# 人一讲解：根路径测试接口 — 验证后端是否正常启动
@app.get("/")
def read_root():
    return {"message": "Python 后端已成功启动！"}


# 人一讲解：程序入口 — uvicorn 是 ASGI 服务器，负责接收 HTTP 请求并转发给 FastAPI
# host="0.0.0.0" 让同一局域网的其他设备也能访问
# reload=True 使代码修改后自动重启（仅开发环境使用）
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
