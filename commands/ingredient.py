"""!재료 [재료명]"""
import database as db
from utils import fmt_oz, display_status

STATUS_MSG = {
    "이상없음": "충분합니다",
    "위험":    "소진 위험 상태입니다",
    "부족":    "부족합니다",
    "소진":    "소진되었습니다",
    "만료":    "만료되었습니다",
}


def handle(args: str, user_id: str, user_name: str) -> str:
    name = args.strip()
    if not name:
        return "확인할 재료 이름을 입력해주세요. 예: !재료 럼"

    db.check_and_update_expiry(name)
    item = db.get_inventory_item(name)
    if not item:
        return f"'{name}' — 재고 DB에 없는 재료입니다. 오타를 확인해주세요."

    status = item["status"]
    msg = STATUS_MSG.get(status, status)
    remaining = fmt_oz(item["remaining_oz"])
    return f"{name}: {msg} ({display_status(status)})\n남은 양: {remaining} / 병 {item['bottle_count']}개"
