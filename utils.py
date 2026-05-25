import re
from config import OZ_PER_ML, STATUS_DANGER_THRESHOLD_OZ


def ml_to_oz(ml: float) -> float:
    return round(ml * OZ_PER_ML, 4)


def compute_quantity_status(remaining_oz) -> str:
    """oz 기준으로 이상없음/위험/부족 판정. 소진·만료는 별도 처리."""
    if remaining_oz is None:
        return "소진"
    if remaining_oz <= 0:
        return "부족"
    if remaining_oz <= STATUS_DANGER_THRESHOLD_OZ:
        return "위험"
    return "이상없음"


def fmt_oz(oz) -> str:
    if oz is None:
        return "-"
    val = round(oz, 2)
    if val == int(val):
        return f"{int(val)}oz"
    return f"{val}oz"


# ---------- 파싱 헬퍼 ----------

_ITEM_AMOUNT_RE = re.compile(
    r"^(.+?)\s+(\d+(?:\.\d+)?)\s*(oz|mL|ml|ML|OZ)?$"
)
_ADD_ITEM_RE = re.compile(
    r"^(.+?)\s+(\d+(?:\.\d+)?)\s*(?:mL|ml|ML)?\s+(\S+)$"
)
_RECIPE_COUNT_RE = re.compile(r"^(.+?)\s+(\d+)$")


def parse_item_amount(token: str):
    """'재료명 양[단위]' → (name, oz) 또는 None"""
    m = _ITEM_AMOUNT_RE.match(token.strip())
    if not m:
        return None
    name = m.group(1).strip()
    amount = float(m.group(2))
    unit = (m.group(3) or "oz").lower()
    if unit in ("ml",):
        amount = ml_to_oz(amount)
    return name, amount


def parse_add_item(token: str):
    """'재료명 양mL 소비기한' → (name, oz, expiry_or_none) 또는 None"""
    m = _ADD_ITEM_RE.match(token.strip())
    if not m:
        return None
    name = m.group(1).strip()
    amount_ml = float(m.group(2))
    expiry_str = m.group(3).strip()
    expiry = None if expiry_str in ("-", "없음") else expiry_str
    return name, ml_to_oz(amount_ml), expiry


def parse_recipe_count(token: str):
    """'레시피명 수량' → (name, count) 또는 None"""
    m = _RECIPE_COUNT_RE.match(token.strip())
    if not m:
        return None
    return m.group(1).strip(), int(m.group(2))


def split_items(text: str) -> list[str]:
    """쉼표로 구분된 항목 리스트 반환"""
    return [t.strip() for t in text.split(",") if t.strip()]


# 출력용 상태명 (내부 DB값 → 사용자 표시명)
STATUS_DISPLAY = {
    "이상없음": "충분",
    "위험":     "소진위험",
    "부족":     "부족",
    "소진":     "소진",
    "만료":     "만료",
}

# 입력 정규화 (사용자 입력 → 내부 DB값)
STATUS_INPUT_NORMALIZE = {
    "충분":     "이상없음",
    "이상없음": "이상없음",
    "소진위험": "위험",
    "위험":     "위험",
    "부족":     "부족",
    "소진":     "소진",
    "만료":     "만료",
}


def display_status(status: str) -> str:
    return STATUS_DISPLAY.get(status, status)
