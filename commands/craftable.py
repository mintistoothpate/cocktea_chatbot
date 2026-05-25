"""!제작가능 [레시피]"""
import database as db
from utils import fmt_oz, display_status


def handle(args: str, user_id: str, user_name: str) -> str:
    name = args.strip()
    if not name:
        return "레시피 이름을 입력해주세요. 예: !제작가능 모히토"

    recipe = db.get_recipe(name)
    if not recipe:
        return f"'{name}' — 레시피 DB에 없습니다. 오타를 확인해주세요."

    all_items = {i["name"]: i for i in db.get_all_inventory()}
    blocked = []
    warnings = []

    for ing, oz in recipe["ingredients"].items():
        item = all_items.get(ing)
        if not item:
            blocked.append(f"{ing} (재고 없음)")
        elif item["status"] in ("소진", "만료"):
            blocked.append(f"{ing} ({item['status']})")
        elif item["status"] in ("위험", "부족"):
            warnings.append(f"{ing} ({display_status(item['status'])}, {fmt_oz(item['remaining_oz'])} 남음)")

    if blocked:
        lines = [f"[{name}] 제작 불가"]
        lines.append("문제 재료:")
        for b in blocked:
            lines.append(f"  {b}")
        return "\n".join(lines)

    if warnings:
        lines = [f"[{name}] 제작 가능 (재료 부족 가능)"]
        lines.append("부족할 수 있는 재료:")
        for w in warnings:
            lines.append(f"  {w}")
        return "\n".join(lines)

    ing_list = ", ".join(f"{i} {fmt_oz(o)}" for i, o in recipe["ingredients"].items())
    return f"[{name}] 제작 가능\n재료: {ing_list}"
