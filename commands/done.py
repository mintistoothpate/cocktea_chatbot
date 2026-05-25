"""!완료"""
import database as db


def handle(args: str, user_id: str, user_name: str) -> str:
    removed = db.remove_room_user(user_id)
    db.add_log(user_id, user_name, "완료(나감)", "")

    if removed:
        return f"[완료] {user_name} — 동방에서 나갔습니다. 수고하셨습니다!"
    return f"[완료] {user_name} — 동방 인원에 없었지만 나감 기록은 저장했습니다."
