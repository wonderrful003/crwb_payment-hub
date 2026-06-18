# Payment Hub

A Django web application for converting bank payment Excel files into semicolon-delimited text files compatible with the CRWB/OBDX payment processing spec. Supports five payment types, auto-generates sequential reference numbers, and lets users download the output as CSV, TXT, or XLSX.

---

## Features

- **Five payment types** — Supplier, Salary, Remittance PRN, Remittance TR, and Foreign payments, each with its own conversion logic and file format
- **Auto-generated reference numbers** — atomic, sequential, per-type references (e.g. `SLR00000001`, `SUP00000042`) with database-level locking to prevent duplicates under concurrent uploads
- **Client-side template validation** — the upload form reads the Excel headers in the browser (via SheetJS) before submission and blocks the upload if required columns are missing, showing exactly which columns are absent
- **Downloadable templates** — admins upload Excel templates through Django Admin; users download the correct template for their payment type, fill it in, and upload it back
- **Three output formats** — every converted file can be downloaded as `.csv`, `.txt`, or `.xlsx`
- **Job history** — full searchable and filterable log of every upload with status, record count, reference range, timestamps, and error details
- **Job detail view** — inline data preview of the first 10 rows with auto-filled reference numbers
- **Role-based visibility** — staff/admin users see all jobs; regular users see only their own
- **Live dashboard stats** — stat cards (Total Jobs, Successful, Failed, Records Processed) refresh every 60 seconds, but only when the tab is visible and the dashboard panel is active

---

## Payment Types & Reference Prefixes

| Payment Type    | File Prefix | Reference Prefix | Output Header  |
|-----------------|-------------|------------------|----------------|
| Supplier        | `OBDXPMN`   | `SUP`            | `OBDXSP`       |
| Salary          | `OBDXSF`    | `SLR`            | _(row-level)_  |
| Remittance PRN  | `OBDXRP`    | `PRN`            | `OBDXPRN`      |
| Remittance TR   | `OBDXRM`    | `TRN`            | `CRWB`         |
| Foreign         | `OBDXFX`    | `FRX`            | `CRWB`         |

Output filenames follow the OBDX naming spec: `{PREFIX}_{PARTYID}_{DD.MM.YYYY}{HHMMSS}.txt`, where `PARTYID` is the first 9 digits of the debit account number. Filenames are capped at 50 characters.

---

## Tech Stack

- **Backend** — Django 4.x, Python 3.10+
- **Data processing** — pandas, openpyxl
- **Frontend** — Bootstrap 5, DataTables, Chart.js, SheetJS (client-side Excel reading), Font Awesome
- **Database** — MySQL (via WAMP on Windows) or PostgreSQL; SQLite works for quick local development

---

## Project Structure

```
uploads/
├── models.py       # UploadJob, ReferenceCounter, PaymentTemplate
├── views.py        # index, download_file, download_template, stats_api
├── utils.py        # Converters for each payment type + shared helpers
├── forms.py        # UploadForm with file type/size validation
├── urls.py         # URL routing for the uploads app
├── admin.py        # Django Admin registration
└── apps.py

templates/
├── base.html       # Sidebar layout, notification system, panel navigation
└── index.html      # All four panels: Dashboard, Upload, History, Job Detail
```

---

## Setup

Two paths are documented: **WAMP + MySQL** (Windows local development) and **standard** (Linux/macOS or any environment with PostgreSQL/SQLite).

---

### Option A — WAMP + MySQL (Windows)

#### 1. Install WAMP and start services

Download and install [WampServer](https://www.wampserver.com/en/). Start it and confirm the tray icon turns **green** (Apache + MySQL both running).

#### 2. Create the database

Open **phpMyAdmin** (`http://localhost/phpmyadmin`) and run:

```sql
CREATE DATABASE paymenthub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'paymenthub_user'@'localhost' IDENTIFIED BY 'yourpassword';
GRANT ALL PRIVILEGES ON paymenthub.* TO 'paymenthub_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 3. Install the MySQL Python driver

```bash
pip install mysqlclient
```

> If `mysqlclient` fails to build on Windows, use `pymysql` instead:
> ```bash
> pip install pymysql
> ```
> Then add this to the top of your `settings.py`:
> ```python
> import pymysql
> pymysql.install_as_MySQLdb()
> ```

#### 4. Clone the repository

```bash
git clone https://github.com/your-username/payment-hub.git
cd payment-hub
```

#### 5. Create and activate a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

#### 6. Install dependencies

```bash
pip install -r requirements.txt
```

#### 7. Configure settings

Copy `.env.example` to `.env` and set:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.mysql
DB_NAME=paymenthub
DB_USER=paymenthub_user
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=3306
```

Your `settings.py` `DATABASES` block should read from these env vars:

```python
DATABASES = {
    "default": {
        "ENGINE":   os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME":     os.environ.get("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER":     os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST":     os.environ.get("DB_HOST", ""),
        "PORT":     os.environ.get("DB_PORT", ""),
    }
}
```

#### 8. Run migrations

```bash
python manage.py migrate
```

#### 9. Create a superuser

```bash
python manage.py createsuperuser
```

#### 10. Run the development server

```bash
python manage.py runserver
```

The app will be available at `http://localhost:8000`. MySQL is served by WAMP on port 3306 as normal.

---

### Option B — Standard (Linux / macOS / PostgreSQL)

#### 1. Clone the repository

```bash
git clone https://github.com/your-username/payment-hub.git
cd payment-hub
```

#### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

The app requires at minimum:

```
django
pandas
openpyxl
xlrd
mysqlclient   # if using MySQL
psycopg2-binary  # if using PostgreSQL
```

#### 4. Configure settings

Copy `.env.example` to `.env` and set your database credentials (see the WAMP example above for the env var names — same keys, different values).

#### 5. Run migrations

```bash
python manage.py migrate
```

#### 6. Create a superuser

```bash
python manage.py createsuperuser
```

#### 7. Collect static files (production)

```bash
python manage.py collectstatic
```

#### 8. Run the development server

```bash
python manage.py runserver
```

---

## Uploading Templates (Admin)

Templates are Excel files that users download, fill in, and upload back. To add or update a template:

1. Go to `/admin/` and log in as a staff user
2. Navigate to **Uploads → Payment Templates**
3. Click **Add Payment Template**
4. Select the payment type, upload the `.xlsx` file, set the version, and mark it as active
5. Only one active template per payment type is served to users

If no active template exists for a payment type, the download button on the Upload panel shows a "No template" badge instead.

---

## Reference Number Generation

Reference numbers are generated atomically using `SELECT FOR UPDATE` on the `ReferenceCounter` table. Each payment type has its own counter identified by prefix. This guarantees no two uploads receive duplicate references, even under concurrent requests.

The first and last reference generated in each job are stored as `reference_range` on the `UploadJob` record (e.g. `SLR00000001 – SLR00000025`).

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET`  | `/` | Main dashboard / upload form |
| `POST` | `/` | Submit an Excel file for conversion |
| `GET`  | `/history/` | Redirects to index (history panel) |
| `GET`  | `/job/<id>/` | Redirects to index (detail panel) |
| `GET`  | `/download/<id>/?format=csv\|txt\|xlsx` | Download converted file |
| `GET`  | `/template/<payment_type>/` | Download blank Excel template |
| `GET`  | `/api/stats/` | JSON stats for live dashboard polling |

---

## Access Control

The `_visible_jobs()` helper in `views.py` enforces visibility:

- **Staff / superusers** — see all upload jobs from all users
- **Regular users** — see only their own jobs

All views require login (`@login_required`). Authentication is handled by a separate `accounts` app (not included in this module).

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a pull request

---

## License

MIT