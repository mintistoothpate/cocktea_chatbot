"""!사용 재료 ... / !사용 레시피 ..."""
import database as db
from utils import parse_item_amount, parse_recipe_count, split_items, fmt_oz, display_status


def handle(args: str, user_id: str, user_name: str) -> str:
    if not args:
        return "사용법:\n!사용 재료 [재료] [양], ...\n!사용 레시피 [레시피] [잔수], ..."

    parts = args.split(None, 1)
    mode = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    if mode == "재료":
        return _use_ingredients(rest, user_id, user_name)
    elif mode == "레시피":
        return _use_recipe(rest, user_id, user_name)
    else:
        return f"첫 번째 인자는 '재료' 또는 '레시피'로 입력해주세요.\n예: !사용 재료 럼 2oz\n예: !사용 레시피 모히토 2"


def _use_ingredients(text: str, user_id: str, user_name: str) -> str:
    tokens = split_items(text)
    if not tokens:
        return "재료와 양을 입력해주세요. 예: !사용 재료 럼 2oz, 라임주스 30mL"

    parsed = []
    errors = []
    for token in tokens:
        result = parse_item_amount(token)
        if not result:
            errors.append(f"'{token}' — 형식 오류 (예: 럼 2oz 또는 럼 60mL)")
            continue
        name, oz = result
        if not db.get_inventory_item(name):
            errors.append(f"'{name}' — 재고 DB에 없는 재료입니다. 오타를 확인해주세요.")
        else:
            parsed.append((name, oz))

    if errors:
        return "입력 오류:\n" + "\n".join(errors)

    ingredients = {name: oz for name, oz in parsed}
    db.deduct_ingredients(ingredients)
    db.add_room_user(user_id, user_name)

    rollback = {"type": "재료", "ingredients": ingredients}
    db.save_command_history(user_id, user_name, "!사용", {"type": "재료", "items": text}, rollback)
    db.add_log(user_id, user_name, "사용(재료)", ", ".join(f"{n} {fmt_oz(o)}" for n, o in parsed))

    lines = ["[사용 완료]"]
    for name, oz in parsed:
        item = db.get_inventory_item(name)
        lines.append(f"  {name} -{fmt_oz(oz)} → 남은 양 {fmt_oz(item['remaining_oz'])} ({display_status(item['status'])})")
    return "\n".join(lines)


def _use_recipe(text: str, user_id: str, user_name: str) -> str:
    tokens = split_items(text)
    if not tokens:
        return "레시피와 잔수를 입력해주세요. 예: !사용 레시피 모히토 2"

    parsed = []
    errors = []
    for token in tokens:
        result = parse_recipe_count(token)
        if not result:
            errors.append(f"'{token}' — 형식 오류 (예: 모히토 2)")
            continue
        recipe_name, count = result
        recipe = db.get_recipe(recipe_name)
        if not recipe:
            errors.append(f"'{recipe_name}' — 레시피 DB에 없습니다. 오타를 확인해주세요.")
        else:
            parsed.append((recipe_name, count, recipe))

    if errors:
        return "입력 오류:\n" + "\n".join(errors)

    total_ingredients: dict[str, float] = {}
    for _, count, recipe in parsed:
        for ing, oz in recipe["ingredients"].items():
            total_ingredients[ing] = total_ingredients.get(ing, 0) + oz * count

    db.deduct_ingredients(total_ingredients)
    db.add_room_user(user_id, user_name)

    rollback = {"type": "레시피", "ingredients": total_ingredients}
    detail = ", ".join(f"{n} {c}잔" for n, c, _ in parsed)
    db.save_command_history(user_id, user_name, "!사용", {"type": "레시피", "items": text}, rollback)
    db.add_log(user_id, user_name, "사용(레시피)", detail)

    lines = ["[레시피 사용 완료]", detail, "", "[재고 변동]"]
    for name, oz in total_ingredients.items():
        item = db.get_inventory_item(name)
        if item:
            lines.append(f"  {name} -{fmt_oz(oz)} → 남은 양 {fmt_oz(item['remaining_oz'])} ({display_status(item['status'])})")
    return "\n".join(lines)
