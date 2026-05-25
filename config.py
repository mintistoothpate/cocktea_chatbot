# 관리자로 지정할 카카오 user.id 목록 — 카카오 i 오픈빌더에서 확인 후 추가
ADMIN_USER_IDS: list[str] = ["fa8ede184a5703f9632b6dc32ca948b4253544bf4dd41ec1e3635d40c5e33f30fc"]

CANCEL_TIME_LIMIT_SECONDS = 3600  # !취소 가능 시간 (1시간)

ML_PER_OZ = 30.0
OZ_PER_ML = 1.0 / ML_PER_OZ

STATUS_DANGER_THRESHOLD_OZ = 5.0  # 위험 판정 기준

DB_PATH = "cocktea.db"
