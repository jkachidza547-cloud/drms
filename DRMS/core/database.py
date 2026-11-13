import os, sqlite3, secrets, hashlib, hmac, json
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("DRMS_DB_PATH", ROOT / "data" / "drms.db"))
UPLOAD_PATH = Path(os.getenv("DRMS_UPLOAD_PATH", ROOT / "storage" / "uploads"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS clients(
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, industry TEXT, contact_name TEXT,
 contact_email TEXT, phone TEXT, status TEXT NOT NULL DEFAULT 'active',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, email TEXT NOT NULL UNIQUE,
 full_name TEXT NOT NULL, password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
 must_change_password INTEGER NOT NULL DEFAULT 1, last_login TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS roles(
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT
);
CREATE TABLE IF NOT EXISTS user_roles(
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 role_id INTEGER NOT NULL REFERENCES roles(id), PRIMARY KEY(user_id,role_id)
);
CREATE TABLE IF NOT EXISTS vacancies(
 id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL REFERENCES clients(id),
 title TEXT NOT NULL, location TEXT, description TEXT NOT NULL, requirements TEXT,
 positions_available INTEGER NOT NULL DEFAULT 1, closing_date TEXT,
 status TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS campaigns(
 id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL REFERENCES clients(id),
 vacancy_id INTEGER NOT NULL REFERENCES vacancies(id), name TEXT NOT NULL,
 start_date TEXT, end_date TEXT, budget REAL NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ad_sources(
 id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
 source_name TEXT NOT NULL, tracking_code TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS applicants(
 id INTEGER PRIMARY KEY, applicant_ref TEXT NOT NULL UNIQUE, first_name TEXT NOT NULL,
 middle_name TEXT, surname TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL,
 alternative_phone TEXT, date_of_birth TEXT, location TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_applicants_email ON applicants(email);
CREATE INDEX IF NOT EXISTS idx_applicants_phone ON applicants(phone);
CREATE TABLE IF NOT EXISTS applications(
 id INTEGER PRIMARY KEY, application_ref TEXT NOT NULL UNIQUE,
 applicant_id INTEGER NOT NULL REFERENCES applicants(id),
 vacancy_id INTEGER NOT NULL REFERENCES vacancies(id),
 campaign_id INTEGER REFERENCES campaigns(id), source_id INTEGER REFERENCES ad_sources(id),
 status TEXT NOT NULL DEFAULT 'submitted', assigned_officer INTEGER REFERENCES users(id),
 submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT,
 UNIQUE(applicant_id,vacancy_id)
);
CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_app_vacancy ON applications(vacancy_id);
CREATE TABLE IF NOT EXISTS education(
 id INTEGER PRIMARY KEY, applicant_id INTEGER NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
 qualification TEXT NOT NULL, institution TEXT NOT NULL, year_completed INTEGER
);
CREATE TABLE IF NOT EXISTS employment_history(
 id INTEGER PRIMARY KEY, applicant_id INTEGER NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
 employer TEXT NOT NULL, position TEXT NOT NULL, start_date TEXT, end_date TEXT,
 is_current INTEGER NOT NULL DEFAULT 0, responsibilities TEXT
);
CREATE TABLE IF NOT EXISTS application_answers(
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
 question TEXT NOT NULL, answer TEXT
);
CREATE TABLE IF NOT EXISTS documents(
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
 document_type TEXT NOT NULL, original_filename TEXT NOT NULL, storage_path TEXT NOT NULL,
 mime_type TEXT, file_size INTEGER, checksum TEXT, scan_status TEXT DEFAULT 'pending',
 uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS screening_records(
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
 officer_id INTEGER NOT NULL REFERENCES users(id), result TEXT NOT NULL,
 score REAL, notes TEXT, completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS assessment_templates(
 id INTEGER PRIMARY KEY, vacancy_id INTEGER NOT NULL REFERENCES vacancies(id) ON DELETE CASCADE,
 name TEXT NOT NULL, max_score REAL NOT NULL DEFAULT 100, pass_score REAL,
 active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS assessment_criteria(
 id INTEGER PRIMARY KEY, template_id INTEGER NOT NULL REFERENCES assessment_templates(id) ON DELETE CASCADE,
 name TEXT NOT NULL, weight REAL NOT NULL, max_score REAL NOT NULL DEFAULT 100
);
CREATE TABLE IF NOT EXISTS assessment_results(
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
 template_id INTEGER NOT NULL REFERENCES assessment_templates(id),
 assessor_id INTEGER NOT NULL REFERENCES users(id), total_score REAL,
 comments TEXT, completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS assessment_scores(
 id INTEGER PRIMARY KEY, result_id INTEGER NOT NULL REFERENCES assessment_results(id) ON DELETE CASCADE,
 criterion_id INTEGER NOT NULL REFERENCES assessment_criteria(id), score REAL NOT NULL,
 comments TEXT, UNIQUE(result_id,criterion_id)
);
CREATE TABLE IF NOT EXISTS interviews(
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
 scheduled_at TEXT, location TEXT, status TEXT NOT NULL DEFAULT 'scheduled',
 outcome TEXT, notes TEXT, created_by INTEGER REFERENCES users(id),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS recommendations(
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
 prepared_by INTEGER NOT NULL REFERENCES users(id), recommendation TEXT NOT NULL,
 justification TEXT NOT NULL, approved_by INTEGER REFERENCES users(id),
 approved_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS status_history(
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
 old_status TEXT, new_status TEXT NOT NULL, changed_by INTEGER REFERENCES users(id),
 reason TEXT, changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tracking_tokens(
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
 token_hash TEXT NOT NULL UNIQUE, expires_at TEXT, revoked_at TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_logs(
 id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), action TEXT NOT NULL,
 entity_type TEXT, entity_id TEXT, details TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS privacy_consents(
 id INTEGER PRIMARY KEY, applicant_id INTEGER NOT NULL REFERENCES applicants(id),
 consent_type TEXT NOT NULL, notice_version TEXT NOT NULL, consented INTEGER NOT NULL,
 recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS system_settings(
 setting_key TEXT PRIMARY KEY, setting_value TEXT
);
CREATE TABLE IF NOT EXISTS screening_criteria(
 id INTEGER PRIMARY KEY, vacancy_id INTEGER NOT NULL REFERENCES vacancies(id) ON DELETE CASCADE,
 criterion TEXT NOT NULL, mandatory INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS screening_decisions(
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
 criterion_id INTEGER NOT NULL REFERENCES screening_criteria(id),
 officer_id INTEGER NOT NULL REFERENCES users(id), decision TEXT NOT NULL,
 evidence TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(application_id,criterion_id)
);
CREATE TABLE IF NOT EXISTS interview_scores(
 id INTEGER PRIMARY KEY, interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
 user_id INTEGER NOT NULL REFERENCES users(id), category TEXT NOT NULL,
 score REAL NOT NULL, comments TEXT
);
CREATE TABLE IF NOT EXISTS notification_log(
 id INTEGER PRIMARY KEY, application_id INTEGER REFERENCES applications(id),
 channel TEXT, recipient TEXT, message TEXT, status TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""
def connect():
    con = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=30000")
    return con

@contextmanager
def db():
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return salt.hex() + "$" + digest.hex()

def verify_password(password, encoded):
    try:
        salt_hex, digest_hex = encoded.split("$",1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310000)
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except Exception:
        return False

def audit(user_id, action, entity_type=None, entity_id=None, details=None):
    with db() as con:
        con.execute("""INSERT INTO audit_logs(user_id,action,entity_type,entity_id,details)
                       VALUES(?,?,?,?,?)""",
                    (user_id, action, entity_type, str(entity_id) if entity_id is not None else None,
                     json.dumps(details or {}, ensure_ascii=False)))

def init_db():
    with db() as con:
        con.executescript(SCHEMA)
        if con.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 0:
            con.execute("INSERT INTO schema_version(version) VALUES(1)")
        defaults = [
            ("Super Administrator","Full system access"),
            ("Recruitment Manager","Recruitment operations"),
            ("HR Officer","Application processing"),
            ("Assessment Officer","Candidate assessment"),
            ("Marketing Officer","Campaign management"),
            ("Management Viewer","Read-only management reports"),
            ("Client Representative","Restricted client access")
        ]
        for name, desc in defaults:
            con.execute("INSERT OR IGNORE INTO roles(name,description) VALUES(?,?)",(name,desc))
        if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            # Bootstrap credentials are intentionally changed on first login.
            con.execute("""INSERT INTO users(username,email,full_name,password_hash,must_change_password)
                           VALUES(?,?,?,?,1)""",
                        ("admin","admin@delintel.local","DRMS Administrator",
                         hash_password("ChangeMe123!")))
            uid = con.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            rid = con.execute("SELECT id FROM roles WHERE name='Super Administrator'").fetchone()[0]
            con.execute("INSERT INTO user_roles(user_id,role_id) VALUES(?,?)",(uid,rid))
            con.execute("INSERT OR IGNORE INTO system_settings VALUES('bootstrap_complete','1')")
