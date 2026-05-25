"""!입장 / !입장 [이름], ..."""
import database as db
from utils import split_items


def handle(args: str, user_id: str, user_name: str) -> str:
    db.add_room_user(user_id, user_name)
    db.add_log(user_id, user_name, "방문", "")

    added = [user_name]

    if args:
        companions = split_items(args)
        for name in companions:
            db.admin_add_room_user_by_name(name)
            added.append(name)
        db.add_log(user_id, user_name, "방문(동반)", ", ".join(companions))

    return f"[방문] {', '.join(added)} — 동방에 방문하셨습니다."
