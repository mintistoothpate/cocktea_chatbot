import sqlite3
import json
from datetime import datetime, date
from config import DB_PATH
from utils import compute_quantity_status


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS inventory (
            name TEXT PRIMARY KEY,
            bottle_count INTEGER NOT NULL DEFAULT 0,
            remaining_oz REAL,
            status TEXT NOT NULL DEFAULT '이상없음'
        );

        CREATE TABLE IF NOT EXISTS bottle_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            bottle_number INTEGER NOT NULL,
            capacity_oz REAL NOT NULL,
            expiry_date TEXT,
            UNIQUE(item_name, bottle_number)
        );

        CREATE TABLE IF NOT EXISTS recipe (
            name TEXT PRIMARY KEY,
            ingredients TEXT NOT NULL,
            features TEXT
        );

        CREATE TABLE IF NOT EXISTS command_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            user_name TEXT NOT NULL,
            command TEXT NOT NULL,
            input_data TEXT,
            executed_at TEXT NOT NULL,
            rollback_data TEXT
        );

        CREATE TABLE IF NOT EXISTS room_users (
            user_id TEXT PRIMARY KEY,
            user_name TEXT NOT NULL,
            entered_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS regular_activity (
            id INTEGER PRIMARY KEY DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 0,
            recipes TEXT,
            registered_at TEXT
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT
        );
        """)
        conn.execute("INSERT OR IGNORE INTO regular_activity (id, is_active) VALUES (1, 0)")
        _seed_recipes(conn)
        conn.commit()


def _seed_recipes(conn):
    samples = [
        ("모히토",   json.dumps({"럼": 2.0, "라임주스": 1.0, "심플시럽": 0.5}, ensure_ascii=False),  "상큼하고 달콤한 여름 칵테일"),
        ("마가리타", json.dumps({"데킬라": 2.0, "트리플섹": 1.0, "라임주스": 1.0}, ensure_ascii=False), "새콤달콤한 클래식"),
        ("진토닉",   json.dumps({"진": 2.0, "토닉워터": 4.0}, ensure_ascii=False),                    "산뜻하고 약간 쓴맛"),
        ("코스모폴리탄", json.dumps({"보드카": 1.5, "트리플섹": 0.5, "크랜베리주스": 1.0, "라임주스": 0.25}, ensure_ascii=False), "세련된 핑크빛"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO recipe (name, ingredients, features) VALUES (?, ?, ?)",
        samples,
    )


# ──────────────────────────────
# Inventory
# ──────────────────────────────

def get_all_inventory() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM inventory ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_inventory_item(name: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM inventory WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None


def ensure_inventory_item(name: str) -> bool:
    """없으면 새로 등록하고 True 반환. 이미 있으면 False."""
    with get_conn() as conn:
        existing = conn.execute("SELECT name FROM inventory WHERE name = ?", (name,)).fetchone()
        if existing:
            return False
        conn.execute(
            "INSERT INTO inventory (name, bottle_count, remaining_oz, status) VALUES (?, 0, 0, '이상없음')",
            (name,),
        )
        conn.commit()
        return True


def deduct_ingredients(ingredients: dict) -> dict:
    """
    ingredients: {name: oz, ...}
    재고를 차감하고 {name: new_remaining_oz} 반환.
    """
    result = {}
    with get_conn() as conn:
        for name, oz in ingredients.items():
            row = conn.execute("SELECT remaining_oz, status FROM inventory WHERE name = ?", (name,)).fetchone()
            if not row:
                continue
            new_remaining = (row["remaining_oz"] or 0.0) - oz
            new_status = row["status"]
            if new_status not in ("만료", "소진"):
                new_status = compute_quantity_status(new_remaining)
            conn.execute(
                "UPDATE inventory SET remaining_oz = ?, status = ? WHERE name = ?",
                (new_remaining, new_status, name),
            )
            result[name] = new_remaining
        conn.commit()
    return result


def restore_ingredients(ingredients: dict):
    """!취소 시 차감했던 양을 되돌림. ingredients: {name: oz_to_restore}"""
    with get_conn() as conn:
        for name, oz in ingredients.items():
            row = conn.execute("SELECT remaining_oz, status FROM inventory WHERE name = ?", (name,)).fetchone()
            if not row:
                continue
            restored = (row["remaining_oz"] or 0.0) + oz
            new_status = row["status"]
            if new_status not in ("만료",):
                new_status = compute_quantity_status(restored)
            conn.execute(
                "UPDATE inventory SET remaining_oz = ?, status = ? WHERE name = ?",
                (restored, new_status, name),
            )
        conn.commit()


def exhaust_item(name: str) -> str:
    """병 1개를 소진 처리. 병 개수가 0이 되면 '소진' 상태."""
    with get_conn() as conn:
        oldest = conn.execute(
            "SELECT id, bottle_number, capacity_oz, expiry_date FROM bottle_detail "
            "WHERE item_name = ? ORDER BY bottle_number ASC LIMIT 1",
            (name,),
        ).fetchone()
        bottle_info = dict(oldest) if oldest else None

        if oldest:
            conn.execute("DELETE FROM bottle_detail WHERE id = ?", (oldest["id"],))

        row = conn.execute("SELECT bottle_count, remaining_oz FROM inventory WHERE name = ?", (name,)).fetchone()
        if not row:
            conn.commit()
            return None

        new_count = max(0, (row["bottle_count"] or 0) - 1)
        if new_count == 0:
            conn.execute(
                "UPDATE inventory SET bottle_count = 0, remaining_oz = NULL, status = '소진' WHERE name = ?",
                (name,),
            )
        else:
            new_status = compute_quantity_status(row["remaining_oz"])
            conn.execute(
                "UPDATE inventory SET bottle_count = ?, status = ? WHERE name = ?",
                (new_count, new_status, name),
            )
        conn.commit()
    return bottle_info


def restore_exhaust(name: str, bottle_info: dict, prev_bottle_count: int, prev_remaining_oz, prev_status: str):
    """!취소 시 소진 처리를 되돌림."""
    with get_conn() as conn:
        if bottle_info:
            conn.execute(
                "INSERT OR IGNORE INTO bottle_detail (item_name, bottle_number, capacity_oz, expiry_date) "
                "VALUES (?, ?, ?, ?)",
                (name, bottle_info["bottle_number"], bottle_info["capacity_oz"], bottle_info.get("expiry_date")),
            )
        conn.execute(
            "UPDATE inventory SET bottle_count = ?, remaining_oz = ?, status = ? WHERE name = ?",
            (prev_bottle_count, prev_remaining_oz, prev_status, name),
        )
        conn.commit()


# ──────────────────────────────
# Bottle detail
# ──────────────────────────────

def add_bottle(item_name: str, capacity_oz: float, expiry_date: str | None) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(bottle_number) as max_num FROM bottle_detail WHERE item_name = ?",
            (item_name,),
        ).fetchone()
        next_num = (row["max_num"] or 0) + 1
        conn.execute(
            "INSERT INTO bottle_detail (item_name, bottle_number, capacity_oz, expiry_date) VALUES (?, ?, ?, ?)",
            (item_name, next_num, capacity_oz, expiry_date),
        )
        conn.execute(
            "UPDATE inventory SET bottle_count = bottle_count + 1, "
            "remaining_oz = COALESCE(remaining_oz, 0) + ? WHERE name = ?",
            (capacity_oz, item_name),
        )
        inv = conn.execute("SELECT remaining_oz, status FROM inventory WHERE name = ?", (item_name,)).fetchone()
        if inv and inv["status"] not in ("만료",):
            new_status = compute_quantity_status(inv["remaining_oz"])
            conn.execute("UPDATE inventory SET status = ? WHERE name = ?", (new_status, item_name))
        conn.commit()
        return {"item_name": item_name, "bottle_number": next_num, "capacity_oz": capacity_oz, "expiry_date": expiry_date}


def remove_bottle_by_number(item_name: str, bottle_number: int):
    """!취소 시 특정 병 삭제."""
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM bottle_detail WHERE item_name = ? AND bottle_number = ?",
            (item_name, bottle_number),
        )
        row = conn.execute("SELECT bottle_count, remaining_oz FROM inventory WHERE name = ?", (item_name,)).fetchone()
        if row:
            new_count = max(0, (row["bottle_count"] or 0) - 1)
            new_remaining = max(0.0, (row["remaining_oz"] or 0.0))
            new_status = compute_quantity_status(new_remaining) if new_count > 0 else "소진"
            remaining_val = new_remaining if new_count > 0 else None
            conn.execute(
                "UPDATE inventory SET bottle_count = ?, remaining_oz = ?, status = ? WHERE name = ?",
                (new_count, remaining_val, new_status, item_name),
            )
        conn.commit()


def get_bottles(item_name: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM bottle_detail WHERE item_name = ? ORDER BY bottle_number",
            (item_name,),
        ).fetchall()
        return [dict(r) for r in rows]


# ──────────────────────────────
# 만료 lazy 체크
# ──────────────────────────────

def check_and_update_expiry(item_name: str | None = None) -> list[str]:
    """소비기한 지난 재료 상태를 '만료'로 갱신. 갱신된 재료명 목록 반환."""
    today = date.today().strftime("%Y%m%d")
    updated = []
    with get_conn() as conn:
        query = (
            "SELECT DISTINCT item_name FROM bottle_detail "
            "WHERE expiry_date IS NOT NULL AND expiry_date < ?"
        )
        params = [today]
        if item_name:
            query += " AND item_name = ?"
            params.append(item_name)
        rows = conn.execute(query, params).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE inventory SET status = '만료' WHERE name = ? AND status != '만료'",
                (row["item_name"],),
            )
            updated.append(row["item_name"])
        conn.commit()
    return updated


# ──────────────────────────────
# Recipe
# ──────────────────────────────

def get_recipe(name: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM recipe WHERE name = ?", (name,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["ingredients"] = json.loads(d["ingredients"])
        return d


def get_all_recipes() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM recipe").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["ingredients"] = json.loads(d["ingredients"])
            result.append(d)
        return result


# ──────────────────────────────
# Room users
# ──────────────────────────────

def get_room_users() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM room_users ORDER BY entered_at").fetchall()
        return [dict(r) for r in rows]


def add_room_user(user_id: str, user_name: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO room_users (user_id, user_name, entered_at) VALUES (?, ?, ?)",
            (user_id, user_name, now),
        )
        conn.commit()


def remove_room_user(user_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM room_users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0


def is_user_in_room(user_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM room_users WHERE user_id = ?", (user_id,)).fetchone()
        return row is not None


def admin_add_room_user_by_name(user_name: str):
    """관리자가 이름으로 추가 (user_id = name 임시 사용)."""
    add_room_user(f"__admin__{user_name}", user_name)


def admin_remove_room_user_by_name(user_name: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM room_users WHERE user_name = ?", (user_name,))
        conn.commit()
        return cur.rowcount > 0


# ──────────────────────────────
# Regular activity
# ──────────────────────────────

def get_regular_activity() -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM regular_activity WHERE id = 1").fetchone()
        if not row:
            return {"is_active": 0, "recipes": None, "registered_at": None}
        d = dict(row)
        if d["recipes"]:
            d["recipes"] = json.loads(d["recipes"])
        return d


def save_regular_activity(recipes: list):
    """레시피 등록만 (재고 차감 X)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute(
            "UPDATE regular_activity SET recipes = ?, registered_at = ? WHERE id = 1",
            (json.dumps(recipes, ensure_ascii=False), now),
        )
        conn.commit()


def set_regular_activity_active(active: bool):
    with get_conn() as conn:
        conn.execute("UPDATE regular_activity SET is_active = ? WHERE id = 1", (1 if active else 0,))
        conn.commit()


# ──────────────────────────────
# Command history (for !취소)
# ──────────────────────────────

def save_command_history(user_id: str, user_name: str, command: str, input_data: dict, rollback_data: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO command_history "
            "(user_id, user_name, command, input_data, executed_at, rollback_data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                user_name,
                command,
                json.dumps(input_data, ensure_ascii=False),
                now,
                json.dumps(rollback_data, ensure_ascii=False),
            ),
        )
        conn.commit()


def get_last_command(user_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM command_history WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["input_data"] = json.loads(d["input_data"]) if d["input_data"] else {}
        d["rollback_data"] = json.loads(d["rollback_data"]) if d["rollback_data"] else {}
        return d


def delete_last_command(user_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM command_history WHERE user_id = ?", (user_id,))
        conn.commit()


# ──────────────────────────────
# Activity log
# ──────────────────────────────

def add_log(user_id: str, user_name: str, action: str, detail: str = ""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity_log (timestamp, user_id, user_name, action, detail) VALUES (?, ?, ?, ?, ?)",
            (now, user_id, user_name, action, detail),
        )
        conn.commit()
