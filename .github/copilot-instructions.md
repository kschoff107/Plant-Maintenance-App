# GitHub Copilot / AI agent instructions — Plant Maintenance App

Purpose: give an AI coding agent immediately-actionable knowledge to be productive in this Flask micro-app.

- **Run (dev):** `python app.py` — app runs with `debug=True` on `0.0.0.0:5000`. The app auto-initializes the SQLite DB on startup.
- **Dependencies:** See `requirements.txt` for exact pinned packages (Flask 3.x, Flask-Login, Werkzeug).

- **Entry point:** `app.py` — sets up `LoginManager`, registers blueprints from `routes`, and calls `init_database()`.
- **Config:** `config.py` provides `Config.SECRET_KEY` and `DATABASE_PATH`. Prefer using `SECRET_KEY` env var in production.

- **Database:** SQLite file at `database/plant_maintenance.db` (created by `database/init_db.py`). Use `get_connection()` from `database/init_db.py` for queries; it sets `row_factory=sqlite3.Row` so rows support column access by name.
  - Default admin is created on first run: username `Admin`, password `Admin1` (printed to console). Treat this as temporary.

- **Auth & Users:** `models/user.py` defines `User` (extends `UserMixin`) with helpers:
  - `check_password(password)` — uses `werkzeug.security.check_password_hash`
  - `hash_password(password)` — to create hashes when inserting users
  - role helpers: `is_admin()`, `is_supervisor()`, `is_technician()` — follow these role checks when gating features

- **Routes / Blueprints:** `routes/auth.py` (auth_bp) and `routes/main.py` (main_bp). `routes/__init__.py` exposes `auth_bp`, `main_bp`, and `get_user_by_id` for `app.py` to import.
  - `auth.py` provides `get_user_by_username()` and `get_user_by_id()` patterns — copy these for other user lookups.
  - Protected pages use `@login_required` and render templates under `templates/`.

- **UI / Templates:** module pages are under `templates/modules/` (e.g., `equipment.html`, `work_orders.html`). Add a new module by:
  1. Adding `templates/modules/<name>.html`
  2. Adding a route in `routes/main.py` that returns `render_template('modules/<name>.html', module_name='...')` guarded with `@login_required`.

- **DB change convention:** Modify `database/init_db.py` for schema migrations in development. This project has no migration tool; for non-trivial schema changes, add a one-off migration script and update `init_database()` carefully.

- **Code patterns to preserve:**
  - Use the `get_connection()` helper for DB access (ensures consistent `row_factory`).
  - Use parameterized SQL (`?` placeholders) to avoid injection.
  - Use `User.hash_password()` when creating users and `User.check_password()` when verifying.
  - Register blueprints in `app.py` via imports from `routes` (do not rewire blueprint naming).

- **Where to add tests or scripts:** There are no tests currently. If adding tests, follow small-unit style and exercise `database/get_connection()` with a temporary DB file.

- **Quick examples:**
  - Query pattern (follow `auth.py`):
    ```py
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = cur.fetchone()
    conn.close()
    ```
  - New module route example (follow `main.py` patterns):
    ```py
    @main_bp.route('/my-module')
    @login_required
    def my_module():
        return render_template('modules/my_module.html', module_name='My Module')
    ```

- **Security & production notes (explicit, discoverable):**
  - `Config.SECRET_KEY` has a default; set `SECRET_KEY` in environment for production.
  - Default admin credentials are created by `init_database()`; rotate/remove in production.

If anything above is unclear or you want more detail (e.g., common refactor patterns, recommended migration approach, or suggested tests), tell me which area to expand. 
