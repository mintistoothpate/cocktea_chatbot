"""!재고 / !재고 [상태] / !재고 [재료] (관리자 전용)"""
import database as db
from utils import fmt_oz, display_status, STATUS_INPUT_NORMALIZE
from config import ADMIN_USER_IDS

VALID_STATUSES = set(STATUS_INPUT_NORMALIZE.keys())
MAX_OUTPUT = 20


def handle(args: str, user_id: str, user_name: str) -> str:
    if user_id not in ADMIN_USER_IDS:
        return "이 명령어는 관리자만 사용할 수 있습니다."

    db.check_and_update_expiry()

    if not args:
        return _all_issues()

    query = args.strip()
    if query in VALID_STATUSES:
        return _by_status(STATUS_INPUT_NORMALIZE[query])
    return _by_name(query)


def _all_issues() -> str:
    items = db.get_all_inventory()
    issues = [i for i in items if i["status"] != "이상없음"]
    if not issues:
        return "현재 이상 없는 재고만 있습니다."

    if len(issues) > MAX_OUTPUT:
        return f"결과가 너무 많습니다 ({len(issues)}개). 조건을 좁혀 다시 검색해 주세요.\n예: !재고 위험"

    groups: dict[str, list] = {}
    for item in issues:
        groups.setdefault(item["status"], []).append(item["name"])

    priority = ["만료", "소진", "부족", "위험"]
    lines = ["[이상 있는 재고]"]
    for status in priority:
        if status in groups:
            lines.append(f"\n{display_status(status)}: {', '.join(groups[status])}")
    return "\n".join(lines)


def _by_status(status: str) -> str:
    items = db.get_all_inventory()
    filtered = [i for i in items if i["status"] == status]
    if not filtered:
        return f"'{status}' 상태의 재료가 없습니다."
    if len(filtered) > MAX_OUTPUT:
        return f"결과가 너무 많습니다 ({len(filtered)}개). 조건을 좁혀 다시 검색해 주세요."

    lines = [f"[{display_status(status)} 재료 목록]"]
    for item in filtered:
        lines.append(f"  {item['name']}: {fmt_oz(item['remaining_oz'])} (병 {item['bottle_count']}개)")
    return "\n".join(lines)


def _by_name(name: str) -> str:
    item = db.get_inventory_item(name)
    if not item:
        return f"'{name}' — 재고 DB에 없는 재료입니다. 오타를 확인해주세요."

    bottles = db.get_bottles(name)
    lines = [
        f"[{name} 재고 상세]",
        f"  상태: {display_status(item['status'])}",
        f"  남은 양: {fmt_oz(item['remaining_oz'])}",
        f"  병 개수: {item['bottle_count']}개",
    ]
    if bottles:
        lines.append("  병 상세:")
        for b in bottles:
            expiry = b["expiry_date"] if b["expiry_date"] else "없음"
            lines.append(f"    병 {b['bottle_number']}: 용량 {fmt_oz(b['capacity_oz'])}, 소비기한 {expiry}")
    return "\n".join(lines)
