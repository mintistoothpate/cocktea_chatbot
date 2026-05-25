from commands import (
    usage, exhausted, recommend, add_item, inventory_cmd,
    cancel, help_cmd, ingredient, craftable, regular_activity,
    room, enter, done, admin_room,
)

COMMANDS = {
    "사용":        usage.handle,
    "소진":        exhausted.handle,
    "추천":        recommend.handle,
    "추가":        add_item.handle,
    "재고":        inventory_cmd.handle,
    "취소":        cancel.handle,
    "도움말":      help_cmd.handle,
    "재료":        ingredient.handle,
    "제작가능":    craftable.handle,
    "정기활동":    regular_activity.handle,
    "동방":        room.handle,
    "입장":        enter.handle,
    "완료":        done.handle,
    "동방인원수정": admin_room.handle,
}


def route(utterance: str, user_id: str, user_name: str) -> str:
    text = utterance.strip()
    if not text.startswith("!"):
        return None  # 봇이 처리하지 않음

    rest = text[1:]
    parts = rest.split(None, 1)
    cmd_name = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    handler = COMMANDS.get(cmd_name)
    if handler is None:
        return f"'{cmd_name}' — 알 수 없는 명령어입니다.\n사용 가능한 명령어 목록: !도움말"

    try:
        return handler(args, user_id, user_name)
    except Exception as e:
        return f"처리 중 오류가 발생했습니다: {e}"
