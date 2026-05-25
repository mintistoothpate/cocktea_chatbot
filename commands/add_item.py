"""!추가 재료 양mL 소비기한, ... (관리자 전용)"""
import database as db
from utils import parse_add_item, split_items, fmt_oz, display_status
from config import ADMIN_USER_IDS


def handle(args: str, user_id: str, user_name: str) -> str:
    if user_id not in ADMIN_USER_IDS:
        return "이 명령어는 관리자만 사용할 수 있습니다."
    if not args:
        return "사용법: !추가 [재료] [양mL] [소비기한], ...\n예: !추가 럼 700mL 없음, 라임주스 500mL 20261231"

    tokens = split_items(args)
    errors = []
    parsed = []

    for token in tokens:
        result = parse_add_item(token)
        if not result:
            errors.append(f"'{token}' — 형식 오류 (예: 럼 700mL 없음 또는 라임주스 500mL 20261231)")
            continue
        name, oz, expiry = result
        parsed.append((name, oz, expiry))

    if errors:
        return "입력 오류:\n" + "\n".join(errors)

    new_items = []
    added_bottles = []

    for name, oz, expiry in parsed:
        is_new = db.ensure_inventory_item(name)
        if is_new:
            new_items.append(name)
        bottle = db.add_bottle(name, oz, expiry)
        added_bottles.append({"name": name, "bottle_number": bottle["bottle_number"], "oz": oz})

    rollback = {"type": "추가", "bottles": added_bottles}
    db.save_command_history(
        user_id, user_name, "!추가",
        {"items": args},
        rollback,
    )
    db.add_log(user_id, user_name, "추가", ", ".join(f"{n} {fmt_oz(o)}" for n, o, _ in parsed))

    lines = ["[재고 추가 완료]"]
    for name, oz, expiry in parsed:
        item = db.get_inventory_item(name)
        expiry_str = expiry if expiry else "없음"
        lines.append(f"  {name}: +{fmt_oz(oz)} (소비기한: {expiry_str}) → 총 {fmt_oz(item['remaining_oz'])} ({display_status(item['status'])})")
    if new_items:
        lines.append("")
        lines.append("[새 재료 등록됨]")
        for n in new_items:
            lines.append(f"  {n} — 오타라면 !취소로 되돌릴 수 있습니다.")
    return "\n".join(lines)
