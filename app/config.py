# =============================================================================
# 文件: app/config.py — 系统配置（数据库连接 + 文件上传目录）
# 负责人: 人二 (管理员数据管理模块)
# 讲解要点:
#   1. 使用 python-dotenv 从 .env 文件读取敏感配置，避免密码硬编码
#   2. PyMySQL 连接参数字典结构 — host/port/user/password/database/charset
#   3. DictCursor 的作用 — 查询结果以字典返回而非元组，便于用字段名取值
#   4. UPLOAD_DIR 目录自动创建
# =============================================================================

import os
import pymysql
from dotenv import load_dotenv

# 人二讲解：加载 .env 文件中的环境变量，os.getenv() 读取
# .env 文件不会被提交到 Git（已在 .gitignore 中排除），保护数据库密码
load_dotenv()

# 人二讲解：数据库连接配置字典 — PyMySQL 通过 **DB_CONFIG 解包传入
# os.getenv("键", "默认值") 从环境变量读取，不存在则用默认值
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),        # 数据库地址
    "port": int(os.getenv("DB_PORT", "3306")),         # 数据库端口（需转 int）
    "user": os.getenv("DB_USER", "root"),              # 数据库用户名
    "password": os.getenv("DB_PASSWORD"),              # 数据库密码（从 .env 读取）
    "database": os.getenv("DB_NAME", "teacher_vote"),  # 数据库名
    "charset": "utf8mb4",                              # 字符集，支持 emoji
    "cursorclass": pymysql.cursors.DictCursor,         # 查询结果返回字典格式
}

# 人二讲解：上传文件存储目录 — 照片上传后保存在此目录
# os.makedirs 带 exist_ok=True 表示目录已存在时不报错
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
