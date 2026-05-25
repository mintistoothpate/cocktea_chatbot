from flask import Flask, request, jsonify
import database
from router import route

app = Flask(__name__)

# gunicorn 등 외부 서버로 실행될 때도 DB가 초기화되도록 모듈 로드 시점에 실행
database.init_db()


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    user = data.get("userRequest", {}).get("user", {})
    user_id = user.get("id", "unknown")
    user_name = user.get("properties", {}).get("nickname", user_id)
    utterance = data.get("userRequest", {}).get("utterance", "").strip()
    print(f"[요청] user_id={user_id} | name={user_name} | utterance={utterance}", flush=True)

    response_text = route(utterance, user_id, user_name)
    if response_text is None:
        response_text = "명령어는 '!'로 시작해주세요. 도움말: !도움말"

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {"simpleText": {"text": response_text}}
            ]
        }
    })


@app.route("/health", methods=["GET"])
def health():
    return "ok"


if __name__ == "__main__":
    import os
    database.init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
