from fastapi import APIRouter, HTTPException

from ..database import get_db
from ..models import RecommendRequest, VoteRequest

router = APIRouter(tags=["投票"])


@router.post("/api/admin/recommend")
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


@router.post("/api/student/vote")
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
                placeholders = ",".join(["%s"] * len(data.teacher_ids))
                cursor.execute(
                    f"UPDATE teachers SET vote_count=vote_count+1 WHERE id IN ({placeholders})",
                    tuple(data.teacher_ids),
                )
                values = [(data.student_id, t_id) for t_id in data.teacher_ids]
                cursor.executemany(
                    "INSERT INTO vote_records (student_id, teacher_id) VALUES (%s,%s)", values
                )

            cursor.execute("UPDATE users SET vote_status=1 WHERE id=%s", (data.student_id,))
            conn.commit()
            return {"code": 200, "message": "投票成功！感谢您的参与。"}


@router.get("/api/vote/result")
def get_vote_result(sort_by_vote: bool = False):
    with get_db() as conn:
        with conn.cursor() as cursor:
            order = "vote_count DESC" if sort_by_vote else "id ASC"
            cursor.execute(f"SELECT * FROM teachers WHERE is_candidate=1 ORDER BY {order}")
            return {"code": 200, "data": cursor.fetchall()}


@router.post("/api/admin/reset")
def reset_system():
    """重置整个投票系统：清空投票记录、重置教师票数和候选状态、删除所有学生"""
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 1. 清空投票记录
            cursor.execute("DELETE FROM vote_records")
            # 2. 重置所有教师票数和候选状态
            cursor.execute("UPDATE teachers SET vote_count = 0, is_candidate = 0")
            # 3. 删除所有学生账号（保留管理员）
            cursor.execute("DELETE FROM users WHERE role = 'student'")
            conn.commit()
            return {"code": 200, "message": "系统已重置：投票记录已清空、教师票数已归零、候选人名单已清除、学生账号已全部删除"}
