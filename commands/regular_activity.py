"""!정기활동 등록 / 시작 / 종료"""
import database as db
from utils import parse_recipe_count, split_items, fmt_oz
from config import ADMIN_USER_IDS


def handle(args: str, user_id: str, user_name: str) -> str:
    if not args:
        return "사용법:\n!정기활동 [레시피] [잔수], ...\n!정기활동 시작\n!정기활동 종료"

    first = args.split(None, 1)[0]
    if first == "시작":
        return _start(user_id, user_name)
    if first == "종료":
        return _end(user_id, user_name)
    return _register(args, user_id, user_name)


def _register(text: str, user_id: str, user_name: str) -> str:
    tokens = split_items(text)
    if not tokens:
        return "레시피와 잔수를 입력해주세요. 예: !정기활동 모히토 2, 마가리타 1"

    parsed = []
    errors = []
    for token in tokens:
        result = parse_recipe_count(token)
        if not result:
            errors.append(f"'{token}' — 형식 오류 (예: 모히토 2)")
            continue
        rname, count = result
        recipe = db.get_recipe(rname)
        if not recipe:
            errors.append(f"'{rname}' — 레시피 DB에 없습니다.")
        else:
            parsed.append({"name": rname, "count": count, "ingredients": recipe["ingredients"]})

    if errors:
        return "입력 오류:\n" + "\n".join(errors)

    db.save_regular_activity(parsed)
    db.add_log(user_id, user_name, "정기활동 등록", ", ".join(f"{r['name']} {r['count']}잔" for r in parsed))

    total: dict[str, float] = {}
    for r in parsed:
        for ing, oz in r["ingredients"].items():
            total[ing] = total.get(ing, 0) + oz * r["count"]

    all_items = {i["name"]: i for i in db.get_all_inventory()}
    warnings = []
    blocked = []
    for ing, required_oz in total.items():
        item = all_items.get(ing)
        if not item:
            blocked.append(f"{ing} (재고 없음)")
        elif item["status"] in ("소진", "만료"):
            blocked.append(f"{ing} ({item['status']})")
        else:
            remaining = item["remaining_oz"] or 0.0
            simulated = remaining - required_oz
            if simulated <= 0:
                warnings.append(f"{ing} (차감 후 {fmt_oz(simulated)} — 부족)")
            elif simulated <= 5:
                warnings.append(f"{ing} (차감 후 {fmt_oz(simulated)} — 위험)")

    lines = ["[정기활동 등록 완료]"]
    for r in parsed:
        lines.append(f"  {r['name']} {r['count']}잔")
    lines.append("\n!정기활동 시작 을 치면 재고가 차감됩니다.")

    if blocked:
        lines.append("\n[제작 불가 재료]")
        for b in blocked:
            lines.append(f"  {b}")
    if warnings:
        lines.append("\n[재고 경고]")
        for w in warnings:
            lines.append(f"  {w}")
    return "\n".join(lines)


def _start(user_id: str, user_name: str) -> str:
    activity = db.get_regular_activity()
    if not activity["recipes"]:
        return "등록된 정기활동이 없습니다. 먼저 !정기활동 [레시피] [잔수] 로 등록해주세요."

    total: dict[str, float] = {}
    for r in activity["recipes"]:
        for ing, oz in r["ingredients"].items():
            total[ing] = total.get(ing, 0) + oz * r["count"]

    db.deduct_ingredients(total)
    db.set_regular_activity_active(True)
    db.add_log(user_id, user_name, "정기활동 시작", ", ".join(f"{r['name']} {r['count']}잔" for r in activity["recipes"]))

    return "[정기활동 시작]\n정기활동이 시작되었습니다."


def _end(user_id: str, user_name: str) -> str:
    db.set_regular_activity_active(False)
    db.add_log(user_id, user_name, "정기활동 종료", "")
    return "[정기활동 종료]\n정기활동이 종료되었습니다."
