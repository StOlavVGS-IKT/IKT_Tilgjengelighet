import os, json, time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, abort

APP_ROOT = Path(__file__).parent.resolve()
DATA_DIR = APP_ROOT / "data"
STATIC_DIR = APP_ROOT / "static"
CONTENT_DIR = STATIC_DIR / "content"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

STATUS_FILE = DATA_DIR / "status.json"

# Konfig via miljøvariabler
ALLOWED_STATUSES = [
    s.strip() for s in os.getenv(
        "ALLOWED_STATUSES",
        "Tilgjengelig,Møte,Ute på oppdrag"
    ).split(",")
    if s.strip()
]
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "").strip()  # tom = ingen auth

app = Flask(__name__, static_url_path="", static_folder=str(STATIC_DIR))

def load_status():
    if STATUS_FILE.exists():
        with STATUS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    # default
    return {"status": ALLOWED_STATUSES[0], "updated_at": int(time.time())}

def save_status(state):
    with STATUS_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)

state = load_status()

def slugify(label: str) -> str:
    # veldig enkel "slug": norske tegn -> ascii-ish, mellomrom -> bindestrek
    trans = str.maketrans({
        "æ": "ae", "Æ": "Ae",
        "ø": "o",  "Ø": "O",
        "å": "a",  "Å": "A"
    })
    s = label.translate(trans).lower()
    s = s.replace(" ", "-")
    return "".join(c for c in s if c.isalnum() or c in "-_")

def check_auth():
    if not AUTH_TOKEN:
        return True
    # token kan komme i Authorization: Bearer <TOKEN> eller ?token=...
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth.split(" ", 1)[1] == AUTH_TOKEN:
        return True
    if request.args.get("token", "") == AUTH_TOKEN:
        return True
    return False

@app.get("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")

@app.get("/control.html")
def control():
    return send_from_directory(str(STATIC_DIR), "control.html")

@app.get("/api/status")
def api_get_status():
    return jsonify({
        "status": state["status"],
        "allowed": ALLOWED_STATUSES,
        "image": f"/static/content/{slugify(state['status'])}.png",
        "updated_at": state.get("updated_at", 0)
    })

@app.get("/set")
def set_get():
    if not check_auth():
        return abort(401)
    new_status = request.args.get("status")
    if new_status not in ALLOWED_STATUSES:
        return jsonify({"error": "Ugyldig status", "allowed": ALLOWED_STATUSES}), 400
    state["status"] = new_status
    state["updated_at"] = int(time.time())
    save_status(state)
    return jsonify({"ok": True, **state})

@app.post("/set")
def set_post():
    if not check_auth():
        return abort(401)
    body = request.get_json(force=True, silent=True) or {}
    new_status = body.get("status")
    if new_status not in ALLOWED_STATUSES:
        return jsonify({"error": "Ugyldig status", "allowed": ALLOWED_STATUSES}), 400
    state["status"] = new_status
    state["updated_at"] = int(time.time())
    save_status(state)
    return jsonify({"ok": True, **state})

if __name__ == "__main__":
    # Lytt eksternt (Azure VM / Docker)
    app.run(host="0.0.0.0", port=8080)
