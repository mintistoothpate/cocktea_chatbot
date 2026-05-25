"""!동방"""
import database as db


def handle(args: str, user_id: str, user_name: str) -> str:
    users = db.get_room_users()
    activity = db.get_regular_activity()

    lines = []

    if not users:
        lines.append("[동방] 현재 사용 인원 없음")
    else:
        lines.append(f"[동방] 현재 {len(users)}명")
        for u in users:
            lines.append(f"  {u['user_name']} ({u['entered_at'][11:16]}~)")

    if activity["is_active"] and activity["recipes"]:
        lines.append("\n[현재 정기활동이 진행중 입니다.]")
        for r in activity["recipes"]:
            lines.append(f"  {r['name']}")

    return "\n".join(lines)
