
## v1.0.3 responsive layout update

The interface now has explicit laptop, desktop and ultrawide layout rules in addition to its mobile styling. Main content uses a fluid width with controlled maximum widths, spacing and padding. Tables and columns are protected against horizontal overflow, and dashboard cards and metrics scale with the viewport.

## v1.0.2 user-interface and application-flow update

- Fixed vacancy-card application buttons so they switch the public portal to the application form and retain the selected vacancy.
- Added a responsive public careers homepage with vacancy highlights, clear navigation and application-tracking shortcuts.
- Improved form validation and upload-size checks for public applications.
- Standardised dropdown menus and input surfaces to whitesmoke with navy text; improved label wrapping and line-height to prevent text collisions.
- Added interview date/time, location or meeting-link, and interview status to the applicant's Track Application panel. Confidential panel notes and assessment data remain hidden.
- Preserved the existing SQLite schema and recruitment workflows.


## v1.0.1 maintenance update

- Fixed Streamlit widget option failures caused by passing unpicklable `sqlite3.Row` objects. The UI query helper now returns ordinary dictionaries.
- Reworked the staff sign-in layout into a centered, branded login panel.
- Standardised the application styling around a whitesmoke background and navy text, including form controls, labels, radio buttons, checkboxes, dropdowns, tables, alerts and buttons.
- Preserved the existing database schema and recruitment workflows.

# DRMS — Delintel Recruitment Management System

A Streamlit + SQLite recruitment management application. The SQLite database and storage folders are created automatically on first run.

## Included functionality

- Public vacancy portal and open application submission
- Multi-step-style application form with education, experience, questions and document uploads
- Unique application references and duplicate-application prevention per vacancy
- Applicant status tracking using application reference + registered phone
- Internal staff login and forced first-login password change
- Multi-client and vacancy management
- Application register, search, status changes and candidate profiles
- Screening records, configurable weighted assessment templates and scoring
- Interview scheduling
- Candidate recommendations
- Advertising campaigns and source tracking codes
- Dashboard KPIs and charts
- CSV, Excel and PDF reporting
- User creation/deactivation, role assignment and audit log
- SQLite backup function

## First-run administrator

Default bootstrap login:

- Username: `admin`
- Temporary password: `ChangeMe123!`

You will be required to change this password immediately after login. Set a strong unique password of at least 12 characters.

The bootstrap account is created only when the database has no users. Do not expose the default credentials publicly.

## Run locally

Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown by Streamlit. The database is created at `data/drms.db` on first run. Uploads are stored in `storage/uploads/`.

## Initial setup

1. Sign in with the temporary administrator credentials.
2. Change the temporary password.
3. Create D&S Holdings under Clients.
4. Create the Stock Controller vacancy.
5. Set the vacancy status to `published`.
6. Share the public portal URL with applicants.
7. Create campaign/source tracking codes as required.

## Cloud deployment

Deploy to a host that supports a persistent disk/volume. Configure:

- `DRMS_DB_PATH=/data/drms.db`
- `DRMS_UPLOAD_PATH=/data/uploads`

Mount a persistent volume at `/data`. Keep the database and uploaded files on persistent storage. Configure HTTPS, backups and host-level access controls. Do not use an ephemeral filesystem for live recruitment data.

Example Streamlit start command:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

## Important production hardening

This is a functional initial release, not a claim of completed independent security certification. Before processing real applicant data:

- Configure a client-specific privacy notice and obtain legal review.
- Enable HTTPS and host-level secrets management.
- Configure malware scanning for uploaded documents.
- Configure encrypted off-site backups and restoration tests.
- Review access policies and test tenant separation.
- Add an email/SMS provider if automatic applicant notifications are required.
- Restrict the hosting account and persistent storage.
- Establish retention and secure deletion procedures.

## Current limitations

- The tracking portal verifies reference + phone; a production rollout should add rate limiting and one-time verification codes.
- Applicant notification events are logged in-app; no email/SMS gateway is configured.
- Client representative portal permissions and fully isolated client-specific reporting are foundations for the next release, not complete external client accounts.
- Assessment templates and candidate scoring are functional; additional vacancy-specific rubrics and interview panel workflows can be expanded.
- SQLite is suitable for a modest initial deployment on one application instance. Migrate to PostgreSQL for larger concurrent workloads.
