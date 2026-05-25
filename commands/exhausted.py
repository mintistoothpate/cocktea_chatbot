"""!소진 재료, 재료, ..."""
import database as db
from utils import split_items, fmt_oz, display_status


def handle(args: str, user_id: str, user_name: str) -> str:
    if not args:
        return "소진할 재료를 입력해주세요. 예: !소진 럼\n여러 개: !소진 럼, 라임주스"

    names = split_items(args)
    errors = []
    processed = []

    for name in names:
        item = db.get_inventory_item(name)
        if not item:
            errors.append(f"'{name}' — 재고 DB에 없습니다. 오타를 확인해주세요.")
            continue

        prev_info = {
            "bottle_count": item["bottle_count"],
            "remaining_oz": item["remaining_oz"],
            "status": item["status"],
        }
        bottle_info = db.exhaust_item(name)
        processed.append((name, prev_info, bottle_info))

    if errors:
        return "입력 오류:\n" + "\n".join(errors)

    if not processed:
        return "처리된 재료가 없습니다."

    rollback_list = [
        {
            "name": name,
            "prev_bottle_count": prev["bottle_count"],
            "prev_remaining_oz": prev["remaining_oz"],
            "prev_status": prev["status"],
            "bottle_info": bottle_info,
        }
        for name, prev, bottle_info in processed
    ]
    db.save_command_history(
        user_id, user_name, "!소진",
        {"names": names},
        {"type": "소진", "items": rollback_list},
    )
    db.add_log(user_id, user_name, "소진", ", ".join(n for n, _, _ in processed))

    lines = ["[소진 처리 완료]"]
    for name, _, _ in processed:
        item = db.get_inventory_item(name)
        if item:
            lines.append(f"  {name}: {display_status(item['status'])} (병 {item['bottle_count']}개, 남은 양 {fmt_oz(item['remaining_oz'])})")
    return "\n".join(lines)
