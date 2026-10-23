# Pahad_Guard
this project show and priortise the risk of landslide according to some geological features.

# The following steps to run this project :-
bash  python -m venv venv

Windows:
bash  .\venv\Scripts\Activate.ps1
bash  where.exe python
bash  python -m pip --version
bash  python -m pip install --upgrade pip


Linux/macOS:
bash  source venv/bin/activate


Install packages:
bash  pip install -r requirements.txt


Generate data:
bash  python -m src.data.generate_demo_data


Train the model:
bash  python -m src.model.train


Run tests:
bash  pytest -q


Start the dashboard:
bash  streamlit run app.py

Then open:

http://localhost:8501

# Login / Sign up
The dashboard is now behind a login/sign-up screen. On first run, use the
"Sign Up" tab to create an account (name, email, password) — accounts are
stored locally in `data/users.db` (SQLite, password hashed with salted
PBKDF2, never stored in plain text). After that, use the "Login" tab.

# Roles (user / admin / department)
Since the second evaluation, the dashboard is split into three access
levels, decided by the account's role:

- **👤 User** — what a citizen needs: Overview (with the personal location
alert), Risk Map and Alerts. No zone-level internals.
- **🏛️ Department** — full operational dashboard: everything except the
admin panel (Zone Analysis, Coordinate Analysis, Rainfall Simulator,
Model Explanation added).
- **🛡️ Admin** — everything the department sees, plus a **Database** page:
user list, role management and direct access to the monitoring dataset
(including CSV download).

Demo accounts are seeded automatically on first run (only while no admin
exists, so your real users are never touched):

| Role       | Email                    | Password  |
| ---------- | ------------------------ | --------- |
| Admin      | `admin@pahadguard.com`   | `admin123`|
| Department | `department@pahadguard.com` | `dept123`  |
| User       | `user@pahadguard.com`    | `user123`  |

New sign-ups always start as **User**; an admin promotes them via the
Database page. The system refuses to demote the last remaining admin.

# Email notifications (Brevo)
Every login and sign-up can send you an email notification via Brevo's
transactional email API. To enable it:

1. Create a free account at https://www.brevo.com and grab an API key from
   Settings → SMTP & API → API Keys.
2. Copy `.env.example` to `.env` and fill in:
   - `BREVO_API_KEY` — your Brevo API key
   - `NOTIFY_EMAIL` — the email address that should receive notifications
   - `BREVO_SENDER_EMAIL` — a verified sender in your Brevo account
   - `BREVO_SENDER_NAME` — display name for the sender (optional)

If these aren't configured, login/sign-up still work as normal — the app
just skips sending the notification email and shows a small info note.

# Location-based risk alerts
After logging in, a pop-up asks how you'd like to share your location:

- **📍 Current Location** — looks up your position once via the browser's
  GPS/geolocation.
- **🔴 Live Location** — keeps re-checking your position every ~15 seconds
  so the alert stays current as you move.
- **Skip for now** — dismisses the pop-up; no location alert is shown.

Whichever option you pick, the dashboard's **Overview** page shows a
"Your location" block with a short description of where you are (e.g.
"Gangtok, East Sikkim") and a live risk gauge/alert for that exact point,
using the same nearest-zone + live public-data pipeline as Coordinate Analysis.
You can switch modes any time with the **Change** button on that block.

Notes:
- Browsers only allow the Geolocation API over **HTTPS or localhost** — if
  you deploy over plain HTTP, ask users to enter coordinates manually
  instead (an "Enter coordinates manually" option is always available).
- Turning a coordinate into a place name uses OpenStreetMap's free
  Nominatim service and needs outbound internet access; if it's
  unreachable, the app just shows the raw coordinates instead.
- Live mode uses `streamlit-autorefresh`; if it isn't installed the app
  falls back to a manual "Refresh my live location" button.


## Live environmental data (GEE-free)

The live coordinate/location pipeline does not require Google Earth Engine or a Google Cloud project. It uses:

- **Open-Meteo** for hourly precipitation, 24h/3-day/7-day rainfall totals, soil moisture and elevation.
- **OpenTopoData (SRTM 30m)** for elevation samples used to estimate terrain slope.
- **OpenStreetMap Nominatim** for reverse geocoding.

No API key is required for these prototype integrations. Live values are modelled/public-data estimates rather than ground-station measurements; for production use, validate them against IMD/gauge observations.

The demo zone generator also uses real Sikkim place coordinates so map points are geographically meaningful. The demo environmental values remain synthetic until a live-data refresh is performed.
