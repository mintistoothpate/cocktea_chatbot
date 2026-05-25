"""!동방인원수정 추가/제거 [이름] (관리자 전용)"""
import database as db
from config import ADMIN_USER_IDS


def handle(args: str, user_id: str, user_name: str) -> str:
    if user_id not in ADMIN_USER_IDS:
        return "이 명령어는 관리자만 사용할 수 있습니다."
    if not args:
        return "사용법:\n!동방인원수정 추가 [이름]\n!동방인원수정 제거 [이름]"

    parts = args.split(None, 1)
    if len(parts) < 2:
        return "이름을 입력해주세요."

    action, target_name = parts[0], parts[1].strip()

    if action == "추가":
        db.admin_add_room_user_by_name(target_name)
        db.add_log(user_id, user_name, "동방인원수정(추가)", target_name)
        return f"[동방인원수정] {target_name} — 동방에 들어온 것으로 처리했습니다."
    elif action == "제거":
        removed = db.admin_remove_room_user_by_name(target_name)
        db.add_log(user_id, user_name, "동방인원수정(제거)", target_name)
        if removed:
            return f"[동방인원수정] {target_name} — 동방에서 나간 것으로 처리했습니다."
        return f"[동방인원수정] '{target_name}' — 동방 인원에 없는 이름입니다."
    else:
        return f"'{action}' — '추가' 또는 '제거'로 입력해주세요."
