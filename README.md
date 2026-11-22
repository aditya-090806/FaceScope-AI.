# FaceScope AI — Internship Demonstration

A responsive Flask web app for face detection and pretrained facial-expression estimation. It supports image upload, browser camera capture, a results dashboard, and locally saved session summaries.

## Important limitations
- Expression categories are model estimates, not proof of actual emotion, intent, mental health, or behavior.
- Scores are model outputs and should not be presented as calibrated probabilities.
- Use images only with the person's permission. This demo stores uploaded images in `uploads/` and session metadata in `face_analysis.db`; delete these when finished.
- This is a local development demo, not a hardened production deployment.

## Requirements
- Python 3.10+ recommended
- Internet connection for initial package/model downloads
- Webcam access is optional

## Windows setup
Open Command Prompt in this folder and run:

```bat
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

The database table is initialized automatically when the app starts, including when launched by a WSGI server.

The first analysis may take longer while DeepFace downloads its pretrained weights. Test with a clear JPG/PNG face image and good lighting.

## Troubleshooting
- If `pip install` fails, copy the full error message and check that the installed Python version is supported by all dependencies.
- If analysis fails on first run, ensure internet access and retry once so model files can download.
- If no face is detected, use a clear, front-facing image with a single visible face.
- The browser camera is optional; use image upload if camera permission is denied.
- Mobile devices can open the app only on the same laptop by default if using `localhost` on that laptop. To access it from a phone on the same Wi-Fi, run `app.run(host="0.0.0.0", port=5000)` and open `http://LAPTOP_LAN_IP:5000` on the phone. Only do this on a trusted network; do not expose the development server publicly.

## Project structure

```text
FaceAnalysis_Internship_Project/
├── app.py                         # Flask routes, analysis, and database logic
├── requirements.txt               # Python dependencies
├── README.md                      # Setup and project documentation
├── templates/
│   ├── base.html                  # Shared layout, navigation, alerts, footer
│   ├── index.html                 # Home/dashboard page; includes the partials below
│   ├── result.html                # Analysis result page
│   ├── reports.html               # Reports/history page
│   └── partials/
│       ├── home_hero.html         # Home page hero/banner section
│       ├── dashboard_stats.html   # Total sessions, weekly sessions, model status
│       ├── analysis_workspace.html# Image upload and camera capture UI
│       └── recent_sessions.html   # Recent activity table
├── static/
│   ├── style.css                  # All visual styling
│   └── script.js                  # Image preview and camera interactions
└── uploads/                       # Uploaded images during local use
```

### Where is each page or feature?
- **Home/dashboard:** `templates/index.html`; its visible sections are separated into `templates/partials/`.
- **Shared header/navigation/footer:** `templates/base.html`.
- **Image upload and camera interface:** `templates/partials/analysis_workspace.html`.
- **Analysis result:** `templates/result.html`.
- **Reports/history:** `templates/reports.html`.
- **Styling:** `static/style.css`.
- **Browser-side JavaScript:** `static/script.js`.
- **Backend routes and analysis logic:** `app.py`.

**Login page:** This version did not contain a login page or authentication system, so no login code has been moved. A real login feature would need a login template, Flask routes, and authentication/session handling; it should not be represented as implemented yet.

The SQLite database file `face_analysis.db` is created automatically when the app initializes the database.

## Viva summary
The application uses a pretrained facial-analysis model through DeepFace. Flask handles HTTP routes and image uploads, OpenCV is used as the face detector backend, SQLite stores session summaries, and Chart.js renders score and weekly summary charts. The application does not infer a person's real psychological state or diagnose disease.


## Online deployment (Render)

1. Upload this project folder to a GitHub repository.
2. In Render, create a new Web Service and connect the repository.
3. Render can use the included `render.yaml` configuration. The build command is `pip install -r requirements.txt` and the start command is `gunicorn app:app`.
4. Wait for the first deployment and open the HTTPS URL Render provides.
5. Test `/health`, image upload, analysis, reports, and mobile layout.

Important deployment notes:
- Never commit uploaded images, the SQLite database, `.env` files, or private data. The included `.gitignore` excludes these.
- The app is an educational demo, not a hardened production service. Do not upload sensitive or non-consented photos.
- A hosting filesystem may be temporary. Without a persistent disk or external database, SQLite records and uploaded files may be lost during redeploy/restart.
- First model inference can be slow because pretrained weights may need to download; hosting memory and build limits can affect DeepFace/OpenCV deployment.
- Browser camera access usually requires HTTPS on a deployed site. Use the hosting HTTPS URL.
- For local network access from a phone, set `FACE_APP_HOST=0.0.0.0` before running on a trusted Wi-Fi network, then open `http://LAPTOP_LAN_IP:5000` on the phone. Do not expose the development server directly to the public internet.


### SQLite database initialization

The app creates `face_analysis.db` automatically at startup. The database location defaults to the project folder and can be overridden with `FACE_APP_DB_PATH` (use an absolute path for deployments). Connections are closed after each operation, and database writes are committed or rolled back safely. The `sessions` table is created idempotently and its required columns are checked at startup.
