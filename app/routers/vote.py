# =============================================================================
# 文件: app/routers/vote.py — 投票核心业务路由
# 负责人: 人三 (投票核心流程模块)
# 讲解要点:
#   1. 候选人推荐 — 管理员从全体教师中选出最多 10 人作为候选人
#   2. 学生投票 — 三重校验（用户存在/未投过/不超 3 票），超 3 票自动作废
#   3. 投票记录写入 — INSERT INTO vote_records + UPDATE vote_count
#   4. 投票结果统计 — 支持按票数排序，只查 is_candidate=1 的教师
#   5. 系统重置 — 一键清空投票记录、归零票数、清除候选人、删除学生
# =============================================================================

from fastapi import APIRouter, HTTPException

from ..database import get_db
from ..models import RecommendRequest, VoteRequest

router = APIRouter(tags=["投票"])


# ===== 第一阶段：管理员推荐候选人 =====
# 人三讲解：POST /api/admin/recommend
# 业务流程：
#   1. 校验候选人数量不超过 10 人
#   2. 先将所有教师 is_candidate 清零（重置）
#   3. 再将选中教师 is_candidate 设为 1（新候选人）
#   4. 动态生成 IN 子句 — 根据 teacher_ids 的数量拼接占位符
@router.post("/api/admin/recommend")
def recommend_candidates(data: RecommendRequest):
    # 人三讲解：业务规则校验 — 最多推荐 10 名候选人
    if len(data.teacher_ids) > 10:
        raise HTTPException(status_code=400, detail="最多只能推荐10名候选人！")

    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人三讲解：第一步 — 清除旧候选人状态（将所有教师 is_candidate 设为 0）
            cursor.execute("UPDATE teachers SET is_candidate=0 WHERE is_candidate=1")
            if data.teacher_ids:
                # 人三讲解：第二步 — 动态生成 IN 子句
                # 例如选了 3 个教师 → placeholders = "%s,%s,%s"
                # 使用参数化查询防止 SQL 注入
                placeholders = ",".join(["%s"] * len(data.teacher_ids))
                cursor.execute(
                    f"UPDATE teachers SET is_candidate=1 WHERE id IN ({placeholders})",
                    tuple(data.teacher_ids),
                )
            conn.commit()
            return {"code": 200, "message": "初选名单生成成功"}


# ===== 第二阶段：学生投票 =====
# 人三讲解：POST /api/student/vote
# 业务规则（核心难点）：
#   1. 学生必须存在                    → 否则 404
#   2. 学生之前不能投过票（vote_status=0）→ 否则 400
#   3. 如果选了超过 3 人              → 选票作废（vote_status=2），不写入投票记录
#   4. 正常投票（≤3人）              → 写入投票记录，更新教师票数，标记已投（vote_status=1）
@router.post("/api/student/vote")
def student_vote(data: VoteRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人三讲解：校验 1 — 学生用户是否存在
            cursor.execute("SELECT vote_status FROM users WHERE id=%s", (data.student_id,))
            student = cursor.fetchone()
            if not student:
                raise HTTPException(status_code=404, detail="学生用户不存在")

            # 人三讲解：校验 2 — 是否已经投过票（vote_status=1 已投，vote_status=2 已作废）
            # 只有 vote_status=0（未投票）才能继续
            if student["vote_status"] != 0:
                raise HTTPException(status_code=400, detail="您已经提交过投票或投票已被作废，无法重复投票！")

            # 人三讲解：规则 3 — 超过 3 票则作废
            # 作废时只标记 vote_status=2，不写入 vote_records，不更新教师票数
            if len(data.teacher_ids) > 3:
                cursor.execute("UPDATE users SET vote_status=2 WHERE id=%s", (data.student_id,))
                conn.commit()
                return {"code": 200, "message": "投票已提交！但检测到您勾选超过3项，根据规则您的推荐结果已作废。"}

            # 人三讲解：规则 4 — 正常投票流程
            # 4a: 更新教师票数 — vote_count + 1（原子递增，避免并发问题）
            if data.teacher_ids:
                placeholders = ",".join(["%s"] * len(data.teacher_ids))
                cursor.execute(
                    f"UPDATE teachers SET vote_count=vote_count+1 WHERE id IN ({placeholders})",
                    tuple(data.teacher_ids),
                )
                # 4b: 写入投票记录 — executemany 批量插入，一条 SQL 插入多行
                values = [(data.student_id, t_id) for t_id in data.teacher_ids]
                cursor.executemany(
                    "INSERT INTO vote_records (student_id, teacher_id) VALUES (%s,%s)", values
                )

            # 人三讲解：4c: 标记学生投票状态为"已投票"（1），防止重复投票
            cursor.execute("UPDATE users SET vote_status=1 WHERE id=%s", (data.student_id,))
            conn.commit()
            return {"code": 200, "message": "投票成功！感谢您的参与。"}


# ===== 第三阶段：投票结果统计 =====
# 人三讲解：GET /api/vote/result
# 只返回候选人（is_candidate=1）的投票结果
# sort_by_vote 参数控制排序方式：
#   - false（默认）：按教师 id 升序排列
#   - true：按得票数降序排列
@router.get("/api/vote/result")
def get_vote_result(sort_by_vote: bool = False):
    with get_db() as conn:
        with conn.cursor() as cursor:
            order = "vote_count DESC" if sort_by_vote else "id ASC"
            cursor.execute(f"SELECT * FROM teachers WHERE is_candidate=1 ORDER BY {order}")
            return {"code": 200, "data": cursor.fetchall()}


# 人三讲解：POST /api/admin/reset — 系统重置（附加功能）
# 一键将系统恢复到初始状态：
#   1. 清空所有投票记录
#   2. 将所有教师票数归零、候选人标记清除
#   3. 删除所有学生账号（保留管理员）
# ⚠ 此操作不可逆！
@router.post("/api/admin/reset")
def reset_system():
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 人三讲解：按顺序执行四步清理操作
            cursor.execute("DELETE FROM vote_records")                               # 1. 清空投票记录
            cursor.execute("UPDATE teachers SET vote_count = 0, is_candidate = 0")   # 2. 重置教师票数和候选状态
            cursor.execute("DELETE FROM users WHERE role = 'student'")               # 3. 删除所有学生账号
            conn.commit()
            return {"code": 200, "message": "系统已重置：投票记录已清空、教师票数已归零、候选人名单已清除、学生账号已全部删除"}
