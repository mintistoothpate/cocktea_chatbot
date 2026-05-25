"""!추천"""
import database as db


def handle(args: str, user_id: str, user_name: str) -> str:
    db.check_and_update_expiry()

    all_items = {i["name"]: i for i in db.get_all_inventory()}
    recipes = db.get_all_recipes()

    craftable = []
    maybe = []

    for recipe in recipes:
        ings = recipe["ingredients"]
        blocked = False
        warnings = []

        for ing_name, required_oz in ings.items():
            item = all_items.get(ing_name)
            if not item:
                blocked = True
                break
            if item["status"] in ("소진", "만료"):
                blocked = True
                break
            if item["status"] in ("위험", "부족"):
                warnings.append(ing_name)

        if blocked:
            continue
        if warnings:
            maybe.append((recipe, warnings))
        else:
            craftable.append(recipe)

    if not craftable and not maybe:
        return "현재 재고로 만들 수 있는 칵테일이 없습니다."

    lines = ["[칵테일 추천]"]
    if craftable:
        lines.append("\n제작 가능:")
        for r in craftable:
            feat = f" — {r['features']}" if r.get("features") else ""
            lines.append(f"  {r['name']}{feat}")
    if maybe:
        lines.append("\n재료 부족 가능 (제작은 가능할 수 있음):")
        for r, warns in maybe:
            feat = f" — {r['features']}" if r.get("features") else ""
            lines.append(f"  {r['name']}{feat}")
            lines.append(f"    (부족할 수 있는 재료: {', '.join(warns)})")
    return "\n".join(lines)
