# =============================================================================
# 文件: app/routers/upload.py — 照片上传路由
# 负责人: 人二 (管理员数据管理模块)
# 讲解要点:
#   1. FastAPI UploadFile — 接收前端 FormData 中的文件
#   2. 文件扩展名校验 — 白名单机制，只允许图片格式
#   3. uuid 生成唯一文件名 — 防止文件名冲突
#   4. StaticFiles 挂载 — main.py 中已将 /uploads 映射为静态目录
#   5. 前端通过返回的 URL 路径直接访问图片
# =============================================================================

import os
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File

from ..config import UPLOAD_DIR

router = APIRouter(tags=["文件上传"])


# 人二讲解：上传照片 POST /api/upload
# UploadFile 是 FastAPI 提供的文件类型 — 自动处理 multipart/form-data 格式
@router.post("/api/upload")
def upload_photo(file: UploadFile = File(...)):
    # 人二讲解：1. 安全检查 — 从文件名提取扩展名，转为小写
    # os.path.splitext 将 "photo.jpg" 拆成 ("photo", ".jpg")
    ext = os.path.splitext(file.filename)[1].lower()

    # 人二讲解：2. 白名单校验 — 只允许这 5 种图片格式
    # 不在白名单中的格式直接返回 400 错误，阻止恶意文件上传
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(status_code=400, detail="仅支持 jpg、png、gif、webp 格式的图片")

    # 人二讲解：3. 生成唯一文件名 — uuid4().hex 生成 32 位随机十六进制字符串
    # 例如: a1b2c3d4e5f6...jpg — 即使上传同名文件也不会覆盖
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 人二讲解：4. 写入文件 — 以二进制写模式打开，写入文件内容
    with open(filepath, "wb") as f:
        f.write(file.file.read())

    # 人二讲解：5. 返回图片的访问 URL — /uploads/ 路径由 main.py 中的 StaticFiles 提供
    # 前端拿到后直接设置给 <el-avatar :src="url" /> 显示图片
    return {"code": 200, "data": f"/uploads/{filename}"}
