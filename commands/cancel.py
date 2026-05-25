"""!취소"""
from datetime import datetime
import database as db
from config import CANCEL_TIME_LIMIT_SECONDS
from utils import fmt_oz, display_status


def handle(args: str, user_id: str, user_name: str) -> str:
    history = db.get_last_command(user_id)
    if not history:
        return "취소할 수 있는 명령이 없습니다."

    executed_at = datetime.strptime(history["executed_at"], "%Y-%m-%d %H:%M:%S")
    elapsed = (datetime.now() - executed_at).total_seconds()
    if elapsed > CANCEL_TIME_LIMIT_SECONDS:
        return f"취소 가능 시간({CANCEL_TIME_LIMIT_SECONDS // 60}분)이 지났습니다. (실행 시각: {history['executed_at']})"

    rollback = history["rollback_data"]
    cmd = history["command"]
    rtype = rollback.get("type", "")

    if cmd == "!사용" and rtype in ("재료", "레시피"):
        return _cancel_usage(user_id, user_name, rollback)
    elif cmd == "!소진" and rtype == "소진":
        return _cancel_exhaust(user_id, user_name, rollback)
    elif cmd == "!추가" and rtype == "추가":
        return _cancel_add(user_id, user_name, rollback)
    else:
        return f"'{cmd}' 명령어는 취소할 수 없습니다."


def _cancel_usage(user_id, user_name, rollback):
    ingredients = rollback["ingredients"]
    db.restore_ingredients(ingredients)
    db.delete_last_command(user_id)
    db.add_log(user_id, user_name, "취소(!사용)", ", ".join(f"{n} +{fmt_oz(o)}" for n, o in ingredients.items()))
    lines = ["[취소 완료 — !사용]"]
    for name, oz in ingredients.items():
        item = db.get_inventory_item(name)
        if item:
            lines.append(f"  {name} +{fmt_oz(oz)} → 남은 양 {fmt_oz(item['remaining_oz'])} ({display_status(item['status'])})")
    return "\n".join(lines)


def _cancel_exhaust(user_id, user_name, rollback):
    items = rollback["items"]
    for entry in items:
        db.restore_exhaust(
            entry["name"],
            entry["bottle_info"],
            entry["prev_bottle_count"],
            entry["prev_remaining_oz"],
            entry["prev_status"],
        )
    db.delete_last_command(user_id)
    names = ", ".join(e["name"] for e in items)
    db.add_log(user_id, user_name, "취소(!소진)", names)
    return f"[취소 완료 — !소진]\n  {names} 소진 처리가 되돌려졌습니다."


def _cancel_add(user_id, user_name, rollback):
    bottles = rollback["bottles"]
    for b in bottles:
        db.remove_bottle_by_number(b["name"], b["bottle_number"])
    db.delete_last_command(user_id)
    names = ", ".join(f"{b['name']} 병{b['bottle_number']}" for b in bottles)
    db.add_log(user_id, user_name, "취소(!추가)", names)
    return f"[취소 완료 — !추가]\n  {names} 추가 처리가 되돌려졌습니다."
