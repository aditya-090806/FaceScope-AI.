import os, sqlite3, json
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ.get("FACE_APP_DB_PATH", str(BASE_DIR / "face_analysis.db"))).expanduser().resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

app = Flask(__name__)
app.secret_key = os.environ.get("FACE_APP_SECRET", "change-this-for-local-demo")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

@contextmanager
def db():
    """Open a short-lived SQLite connection and always close it safely."""
    con = sqlite3.connect(str(DB_PATH), timeout=15)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA busy_timeout = 15000")
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def init_db():
    """Create the database folder and sessions table safely; can run repeatedly."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            filename TEXT NOT NULL,
            dominant_expression TEXT NOT NULL,
            scores_json TEXT NOT NULL,
            face_count INTEGER NOT NULL CHECK (face_count >= 0)
        )""")
        # Fail early with a clear startup error if an unexpected/old table is present.
        columns = {row["name"] for row in con.execute("PRAGMA table_info(sessions)").fetchall()}
        required = {"id", "created_at", "filename", "dominant_expression", "scores_json", "face_count"}
        missing = required - columns
        if missing:
            raise RuntimeError(
                "Database table 'sessions' is missing required columns: " + ", ".join(sorted(missing))
            )

# Initialize the database during import as well as direct execution. This is required
# when the app is served by a WSGI server (for example, Gunicorn on Render).
init_db()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_image(path):
    # DeepFace uses a pretrained model; the first run may download model weights.
    from deepface import DeepFace
    results = DeepFace.analyze(
        img_path=str(path),
        actions=["emotion"],
        enforce_detection=True,
        detector_backend="opencv",
        silent=True
    )
    if isinstance(results, dict):
        results = [results]
    faces = []
    for item in results:
        scores = item.get("emotion", {}) or {}
        dominant = item.get("dominant_emotion", "unknown")
        faces.append({
            "dominant": str(dominant).capitalize(),
            "scores": {str(k).capitalize(): round(float(v), 2) for k, v in scores.items()},
            "region": item.get("region", {})
        })
    return faces

@app.route("/")
def index():
    with db() as con:
        recent = con.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 5").fetchall()
        total = con.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"]
        week = con.execute("SELECT COUNT(*) AS n FROM sessions WHERE created_at >= ?",
                           ((datetime.now() - timedelta(days=7)).isoformat(timespec="seconds"),)).fetchone()["n"]
    return render_template("index.html", recent=recent, total=total, week=week)

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("image")
    if not file or not file.filename:
        flash("Choose an image first.", "error")
        return redirect(url_for("index"))
    if not allowed_file(file.filename):
        flash("Please upload a PNG, JPG, JPEG, or WEBP image.", "error")
        return redirect(url_for("index"))
    safe_name = secure_filename(file.filename)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = UPLOAD_DIR / f"{stamp}_{safe_name}"
    file.save(path)
    try:
        faces = analyze_image(path)
        if not faces:
            raise ValueError("No face was detected.")
        primary = faces[0]
        created = datetime.now().isoformat(timespec="seconds")
        with db() as con:
            cur = con.execute(
                "INSERT INTO sessions(created_at, filename, dominant_expression, scores_json, face_count) VALUES(?,?,?,?,?)",
                (created, path.name, primary["dominant"], json.dumps(primary["scores"]), len(faces))
            )
            session_id = cur.lastrowid
        return render_template("result.html", faces=faces, filename=path.name, session_id=session_id, created=created)
    except Exception as exc:
        # Keep technical details in server logs; show a safe, actionable message to the user.
        app.logger.exception("Analysis failed")
        message = "Analysis could not complete. Try a clear, front-facing photo with good lighting."
        if "No face" in str(exc) or "Face could not be detected" in str(exc):
            message = "No face was detected. Try a clear, front-facing photo with good lighting."
        flash(message, "error")
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return redirect(url_for("index"))

@app.route("/camera", methods=["POST"])
def camera():
    # Browser camera sends a captured JPEG frame in the same image upload format.
    return analyze()

@app.route("/reports")
def reports():
    since = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
    with db() as con:
        rows = con.execute("SELECT * FROM sessions WHERE created_at >= ? ORDER BY created_at DESC", (since,)).fetchall()
        total = con.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"]
    counts = {}
    for row in rows:
        counts[row["dominant_expression"]] = counts.get(row["dominant_expression"], 0) + 1
    return render_template("reports.html", rows=rows, counts=counts, total=total)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "Face Analysis", "model": "DeepFace emotion analysis"})

@app.errorhandler(413)
def too_large(_):
    flash("Image is too large. Maximum upload size is 8 MB.", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    host = os.environ.get("FACE_APP_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)
