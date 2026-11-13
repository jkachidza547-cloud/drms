import streamlit as st
import pandas as pd
import plotly.express as px
import os, secrets, hashlib, shutil, sqlite3
from pathlib import Path
from datetime import date, datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from core.database import init_db, db, hash_password, verify_password, DB_PATH, UPLOAD_PATH, audit
from core.services import create_client, create_vacancy, submit_application, change_status, save_assessment

st.set_page_config(page_title="DRMS | Delintel Analytics", page_icon="📋", layout="wide", initial_sidebar_state="expanded")
init_db()

NAVY = "#102B50"
NAVY_DARK = "#0B203B"
WHITESMOKE = "#F5F5F5"
BORDER = "#D6DEE8"

st.markdown(f"""
<style>
:root {{
  --drms-navy: {NAVY};
  --drms-bg: {WHITESMOKE};
}}

/* Apply Century Gothic to text elements WITHOUT breaking Streamlit Material Icons */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"],
p, label, input, textarea, select, button, h1, h2, h3, h4, h5, h6,
[data-baseweb="select"], [data-baseweb="popover"], [data-testid="stMetric"],
[data-testid="stDataFrame"], [data-testid="stTable"] {{
  font-family: "Century Gothic", "Montserrat", sans-serif !important;
  color: var(--drms-navy);
}}

/* Preserve Material Symbols icon font so icon ligatures never render as raw text */
[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined,
span[translate="no"] {{
  font-family: "Material Symbols Rounded", "Material Symbols Outlined", sans-serif !important;
}}

.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
  background: var(--drms-bg) !important;
}}
[data-testid="stHeader"] {{
  background: rgba(245, 245, 245, 0.96) !important;
}}
[data-testid="stSidebar"] {{
  background: #EEF1F5 !important;
  border-right: 1px solid {BORDER};
  min-width: 250px;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
  overflow-wrap: anywhere;
}}

h1, h2, h3, h4, h5, h6, .stMarkdown, h1 p, h2 p, h3 p {{
  color: {NAVY} !important;
}}
p, li, label, [data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"] {{
  color: {NAVY} !important;
}}

/* Text & number inputs */
input, textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {{
  color: {NAVY} !important;
  background-color: {WHITESMOKE} !important;
  -webkit-text-fill-color: {NAVY} !important;
  border-color: {BORDER} !important;
  border-radius: 8px !important;
  line-height: 1.4 !important;
}}
input::placeholder, textarea::placeholder {{
  color: #526780 !important;
  opacity: 1 !important;
}}

/* ALL Dropdowns (Selectbox, Multiselect, Popover Menus & Options): Whitesmoke BG + Navy Forecolor */
[data-baseweb="select"],
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div,
[data-baseweb="select"] [data-testid="stMarkdownContainer"],
[data-baseweb="select"] input,
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="option"],
[data-baseweb="popover"] ul,
[data-baseweb="popover"] li,
[data-baseweb="menu"],
[data-baseweb="menu"] div,
[data-baseweb="menu"] span,
[data-baseweb="menu"] li {{
  background-color: {WHITESMOKE} !important;
  color: {NAVY} !important;
  border-color: {BORDER} !important;
}}

[data-baseweb="select"] svg,
[data-baseweb="popover"] svg {{
  fill: {NAVY} !important;
  color: {NAVY} !important;
}}

[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [aria-selected="true"],
[data-baseweb="menu"] li:hover {{
  background-color: #E2E8F0 !important;
  color: {NAVY} !important;
}}

/* Selected tags inside multiselect */
[data-baseweb="tag"] {{
  background-color: #E2E8F0 !important;
  color: {NAVY} !important;
}}
[data-baseweb="tag"] span, [data-baseweb="tag"] svg {{
  color: {NAVY} !important;
  fill: {NAVY} !important;
}}

/* Radios & Checkboxes */
[data-baseweb="radio"], [data-baseweb="checkbox"],
[data-baseweb="radio"] label, [data-baseweb="checkbox"] label,
[data-testid="stRadio"] label, [data-testid="stCheckbox"] label {{
  color: {NAVY} !important;
}}
[data-testid="stRadio"] [role="radio"], [data-testid="stCheckbox"] input {{
  accent-color: {NAVY} !important;
}}
[data-testid="stRadio"] > div {{
  flex-wrap: wrap !important;
  gap: 0.45rem 0.9rem !important;
}}
[data-testid="stRadio"] label {{
  align-items: flex-start !important;
}}

/* Buttons & File Upload Buttons (Whitesmoke background, Navy Blue text) */
.stButton > button,
[data-testid="stFormSubmitButton"] button,
[data-testid="stFileUploader"] section button,
[data-testid="stDownloadButton"] > button {{
  background-color: {WHITESMOKE} !important;
  color: {NAVY} !important;
  border: 1px solid {BORDER} !important;
  border-radius: 9px !important;
  min-height: 2.7rem;
  width: 100%;
  max-width: 100%;
  white-space: normal !important;
  line-height: 1.25 !important;
  padding: 0.65rem 1rem !important;
  font-weight: 600;
  box-sizing: border-box;
}}

.stButton > button p, [data-testid="stFormSubmitButton"] button p,
.stButton > button span, [data-testid="stFormSubmitButton"] button span,
[data-testid="stFileUploader"] section button *,
[data-testid="stDownloadButton"] > button * {{
  color: {NAVY} !important;
}}

.stButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stFileUploader"] section button:hover,
[data-testid="stDownloadButton"] > button:hover {{
  background-color: #E2E8F0 !important;
  border-color: {NAVY} !important;
}}

/* File Uploader Dropzone Box */
[data-testid="stFileUploader"] {{
  background-color: #FFFFFF !important;
  border: 1px dashed {BORDER} !important;
  border-radius: 12px !important;
  padding: 12px !important;
}}
[data-testid="stFileUploader"] section {{
  background-color: {WHITESMOKE} !important;
  border-radius: 10px !important;
  border: 1px solid {BORDER} !important;
}}
[data-testid="stFileUploader"] section * {{
  color: {NAVY} !important;
}}

/* Tables (DataFrames & Static Tables): Whitesmoke background + Navy Blue text */
[data-testid="stDataFrame"],
[data-testid="stTable"],
div[data-testid="stDataFrame"] > div,
div[data-testid="stTable"] > div {{
  background-color: {WHITESMOKE} !important;
  color: {NAVY} !important;
  border-radius: 10px !important;
  border: 1px solid {BORDER} !important;
}}

[data-testid="stDataFrame"] table,
[data-testid="stTable"] table,
.dataframe {{
  background-color: {WHITESMOKE} !important;
  color: {NAVY} !important;
}}

[data-testid="stDataFrame"] th,
[data-testid="stTable"] th,
.dataframe th {{
  background-color: #E4EAF1 !important;
  color: {NAVY} !important;
  font-weight: 700 !important;
  border-bottom: 2px solid {BORDER} !important;
}}

[data-testid="stDataFrame"] td,
[data-testid="stTable"] td,
.dataframe td {{
  background-color: {WHITESMOKE} !important;
  color: {NAVY} !important;
  border-bottom: 1px solid {BORDER} !important;
}}

[data-testid="stDataFrame"] * {{
  color: {NAVY} !important;
}}

/* Cards, Metrics, Forms */
div[data-testid="stMetric"], div[data-testid="stForm"], .drms-card,
div[data-testid="stExpander"] {{
  background: #FFFFFF !important;
  border: 1px solid {BORDER} !important;
  border-radius: 12px !important;
}}
div[data-testid="stMetric"] {{ padding: 16px; }}
div[data-testid="stForm"] {{ padding: 20px; }}
[data-testid="stAlert"] * {{ color: {NAVY} !important; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 12px !important; }}
hr {{ border-color: {BORDER} !important; }}

/* Labels & Wrapping */
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
[data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] *,
.stRadio label, .stCheckbox label {{
  white-space: normal !important;
  overflow-wrap: anywhere !important;
  word-break: normal !important;
  line-height: 1.45 !important;
}}
[data-testid="stWidgetLabel"] {{
  min-height: 1.35rem;
  margin-bottom: 0.35rem !important;
}}

/* Login & Hero Components */
.drms-login-brand {{
  background: {NAVY};
  padding: 28px 30px;
  border-radius: 16px 16px 0 0;
  color: #FFFFFF !important;
  text-align: center;
}}
.drms-login-brand h1, .drms-login-brand p {{
  color: #FFFFFF !important;
  margin: 0;
}}
.drms-home-hero {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  width: 100%;
  min-height: clamp(230px, 20vw, 330px);
  padding: clamp(1.5rem, 3.5vw, 3rem);
  margin: 0.3rem 0 1.4rem;
  border-radius: 18px;
  background: {NAVY};
  color: #FFFFFF;
  box-shadow: 0 12px 28px rgba(16, 43, 80, 0.12);
  box-sizing: border-box;
}}
.drms-home-hero * {{ color: #FFFFFF !important; }}
.drms-hero-copy {{ max-width: 760px; }}
.drms-hero-copy h1 {{
  font-size: clamp(2rem, 3.8vw, 3.25rem);
  line-height: 1.12;
  margin: 0.55rem 0 0.8rem;
}}
.drms-hero-copy p {{
  font-size: clamp(0.95rem, 1.3vw, 1.1rem);
  max-width: 680px;
  line-height: 1.65;
  opacity: 0.92;
}}
.drms-eyebrow {{
  font-size: 0.75rem;
  letter-spacing: 0.16em;
  font-weight: 700;
  opacity: 0.85;
}}
.drms-hero-stat {{
  min-width: 150px;
  padding: 1.3rem 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 14px;
  text-align: center;
  flex-shrink: 0;
}}
.drms-hero-stat strong {{
  display: block;
  font-size: 2.6rem;
  line-height: 1.1;
}}
.drms-hero-stat span {{
  font-size: 0.88rem;
  opacity: 0.9;
}}
.drms-section-heading {{ margin: 1.4rem 0 0.8rem; }}
.drms-section-heading h2 {{ margin-bottom: 0.25rem; }}
.drms-section-heading p {{ margin-top: 0; opacity: 0.8; }}
.drms-home-card {{
  height: 100%;
  min-height: 180px;
  padding: 1.4rem;
  border: 1px solid {BORDER};
  border-radius: 14px;
  background: #FFFFFF;
  margin-bottom: 0.8rem;
  min-width: 0;
  overflow-wrap: anywhere;
  box-sizing: border-box;
}}
.drms-home-card h3 {{ margin-top: 0; line-height: 1.3; }}
.drms-home-card p {{ line-height: 1.6; }}

/* Responsive Layout Container across Mobile, Laptop, Desktop & Ultrawide */
[data-testid="stAppViewContainer"] .main .block-container,
section.main > div.block-container {{
  width: 100% !important;
  max-width: 100% !important;
  margin-left: auto !important;
  margin-right: auto !important;
  padding-top: 1.75rem !important;
  padding-bottom: 3rem !important;
  padding-left: clamp(1.25rem, 3vw, 4rem) !important;
  padding-right: clamp(1.25rem, 3vw, 4rem) !important;
  box-sizing: border-box !important;
}}
[data-testid="stHorizontalBlock"] {{
  align-items: stretch !important;
  gap: clamp(0.85rem, 1.5vw, 1.75rem) !important;
}}
[data-testid="column"] {{ min-width: 0 !important; }}

@media (max-width: 760px) {{
  [data-testid="stAppViewContainer"] .main .block-container,
  section.main > div.block-container {{
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-top: 1rem !important;
  }}
  .drms-home-hero {{
    flex-direction: column;
    align-items: flex-start;
    gap: 1.1rem;
    padding: 1.35rem;
  }}
  .drms-hero-stat {{
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.7rem 1rem;
    min-width: 0;
    width: 100%;
    text-align: left;
  }}
  .drms-hero-stat strong {{ font-size: 1.8rem; }}
  div[data-testid="stForm"] {{ padding: 12px !important; }}
}}

@media (min-width: 1600px) {{
  [data-testid="stAppViewContainer"] .main .block-container,
  section.main > div.block-container {{
    max-width: 1920px !important;
    padding-left: 4.5rem !important;
    padding-right: 4.5rem !important;
  }}
  .drms-home-card {{ padding: 1.75rem; min-height: 205px; }}
  div[data-testid="stMetric"] {{ padding: 20px; }}
}}
</style>
""", unsafe_allow_html=True)

STATUSES = ["submitted", "under_review", "screening", "screening_passed", "assessment", "interview", "shortlisted", "client_review", "selected", "not_selected", "withdrawn", "on_hold"]
STATUS_LABELS = {s: s.replace("_", " ").title() for s in STATUSES}

def q(sql, args=()):
    with db() as c:
        return [dict(row) for row in c.execute(sql, args).fetchall()]

def execute(sql, args=()):
    with db() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid

def log_action(action, etype=None, eid=None, details=None):
    audit(st.session_state.get("uid"), action, etype, eid, details)

def user_roles(uid):
    return [r["name"] for r in q("SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id=r.id WHERE ur.user_id=?", (uid,))]

def has_role(*roles):
    return bool(set(roles) & set(st.session_state.get("roles", [])))

def logged_in():
    return bool(st.session_state.get("uid"))

def logout():
    for k in ["uid", "username", "full_name", "roles", "must_change"]:
        st.session_state.pop(k, None)
    st.rerun()

def login():
    left, center, right = st.columns([1.2, 1, 1.2])
    with center:
        st.markdown("""
        <div class="drms-login-brand" style="margin-top:4vh;">
          <h1>DRMS</h1>
          <p>Delintel Recruitment Management System</p>
          <p style="margin-top:10px;font-size:.9rem;">Secure recruitment workspace</p>
        </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            st.subheader("Staff sign in")
            username = st.text_input("Username", placeholder="Enter your username", key="login_user")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
            ok = st.form_submit_button("Sign in", use_container_width=True)
    if ok:
        rows = q("SELECT * FROM users WHERE username=? AND active=1", (username.strip(),))
        if rows and verify_password(password, rows[0]["password_hash"]):
            u = rows[0]
            st.session_state.uid = u["id"]
            st.session_state.username = u["username"]
            st.session_state.full_name = u["full_name"]
            st.session_state.roles = user_roles(u["id"])
            st.session_state.must_change = bool(u["must_change_password"])
            execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (u["id"],))
            log_action("login", "user", u["id"])
            st.rerun()
        else:
            st.error("Invalid username or password.")

def force_password_change():
    st.title("Change your temporary password")
    st.warning("You must replace the initial password before accessing DRMS.")
    with st.form("force_change"):
        p1 = st.text_input("New password", type="password")
        p2 = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Update password")
    if submitted:
        if len(p1) < 12:
            st.error("Use at least 12 characters.")
        elif p1 != p2:
            st.error("Passwords do not match.")
        else:
            execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?",
                    (hash_password(p1), st.session_state.uid))
            st.session_state.must_change = False
            log_action("changed_temporary_password", "user", st.session_state.uid)
            st.success("Password updated.")
            st.rerun()

def _go_to_public_page(page):
    st.session_state["public_nav"] = page

def _go_to_application(vacancy_id):
    st.session_state["public_vacancy"] = int(vacancy_id)
    st.session_state["public_nav"] = "Apply for a vacancy"

def public_portal():
    vacancies = q("""SELECT v.*, c.name AS client_name FROM vacancies v JOIN clients c ON c.id=v.client_id
                     WHERE v.status='published' AND (v.closing_date IS NULL OR date(v.closing_date)>=date('now'))
                     ORDER BY v.created_at DESC""")

    st.markdown(f"""
    <section class="drms-home-hero">
      <div class="drms-hero-copy">
        <span class="drms-eyebrow">DELINTEL ANALYTICS · CAREERS</span>
        <h1>Find your next opportunity.</h1>
        <p>Explore current vacancies, submit your application and follow your recruitment progress in one place.</p>
      </div>
      <div class="drms-hero-stat">
        <strong>{len(vacancies)}</strong>
        <span>Open vacancies</span>
      </div>
    </section>
    """, unsafe_allow_html=True)

    pages = ["Home", "Available vacancies", "Apply for a vacancy", "Track application", "Privacy notice"]
    if "public_nav" not in st.session_state or st.session_state["public_nav"] not in pages:
        st.session_state["public_nav"] = "Home"
    page = st.radio("Portal navigation", pages, key="public_nav", horizontal=True, label_visibility="collapsed")

    if page == "Home":
        st.markdown("<div class='drms-section-heading'><h2>Welcome to DRMS Careers</h2><p>Your recruitment journey starts here.</p></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([1.15, 1], gap="large")
        with c1:
            st.markdown("<div class='drms-home-card'><h3>Explore opportunities</h3><p>Browse active roles, review the requirements and apply for a position that matches your experience.</p></div>", unsafe_allow_html=True)
            st.button("Browse available vacancies", key="home_browse", use_container_width=True,
                      on_click=_go_to_public_page, args=("Available vacancies",))
        with c2:
            st.markdown("<div class='drms-home-card'><h3>Already applied?</h3><p>Use your application reference and registered phone number to check your current status and interview arrangements.</p></div>", unsafe_allow_html=True)
            st.button("Track my application", key="home_track", use_container_width=True,
                      on_click=_go_to_public_page, args=("Track application",))
        st.markdown("<div class='drms-section-heading'><h2>Latest opportunities</h2><p>Recently published vacancies accepting applications.</p></div>", unsafe_allow_html=True)
        if not vacancies:
            st.info("There are no published vacancies at the moment. Please check again later.")
        else:
            cols = st.columns(min(len(vacancies[:3]), 3), gap="large")
            for idx, v in enumerate(vacancies[:3]):
                with cols[idx]:
                    with st.container(border=True):
                        st.subheader(v["title"])
                        st.caption(f'{v["client_name"]} · {v["location"] or "Location to be confirmed"}')
                        st.write((v["description"] or "")[:280] + ("…" if len(v["description"] or "") > 280 else ""))
                        st.caption(f'Closing date: {v["closing_date"] or "Not specified"}')
                        st.button("Apply for this vacancy", key=f'home_apply_{v["id"]}',
                                  on_click=_go_to_application, args=(v["id"],), use_container_width=True)

    elif page == "Available vacancies":
        st.markdown("<div class='drms-section-heading'><h2>Available vacancies</h2><p>Review the role details before applying.</p></div>", unsafe_allow_html=True)
        if not vacancies:
            st.info("There are no published vacancies at the moment.")
        for v in vacancies:
            with st.container(border=True):
                st.subheader(v["title"])
                st.caption(f'{v["client_name"]} · {v["location"] or "Location to be confirmed"}')
                st.write(v["description"])
                if v["requirements"]:
                    with st.expander("View requirements"):
                        st.write(v["requirements"])
                st.caption(f'Closing date: {v["closing_date"] or "Not specified"} · Positions: {v["positions_available"]}')
                st.button("Apply for this vacancy", key=f'apply_{v["id"]}',
                          on_click=_go_to_application, args=(v["id"],), use_container_width=True)

    elif page == "Apply for a vacancy":
        st.markdown("<div class='drms-section-heading'><h2>Application form</h2><p>Complete the required information and attach your CV.</p></div>", unsafe_allow_html=True)
        if not vacancies:
            st.info("No vacancies are currently accepting applications.")
        else:
            default = st.session_state.get("public_vacancy", vacancies[0]["id"])
            ids = [v["id"] for v in vacancies]
            if default not in ids:
                default = ids[0]
            chosen = st.selectbox(
                "Select vacancy",
                ids,
                format_func=lambda x: next(v["title"] + " — " + v["client_name"] for v in vacancies if v["id"] == x),
                index=ids.index(default),
                key="application_vacancy_select",
            )
            with st.form("public_application", clear_on_submit=True):
                st.markdown("**Personal information**")
                r1a, r1b = st.columns(2)
                first = r1a.text_input("First name *", key="app_first_name")
                middle = r1b.text_input("Middle name", key="app_middle_name")

                r2a, r2b = st.columns(2)
                surname = r2a.text_input("Surname *", key="app_surname")
                email = r2b.text_input("Email address *", key="app_email")

                r3a, r3b = st.columns(2)
                phone = r3a.text_input("Phone number *", key="app_phone")
                alt = r3b.text_input("Alternative phone", key="app_alt_phone")

                r4a, r4b = st.columns(2)
                location = r4a.text_input("Town / City", key="app_location")
                dob = r4b.date_input("Date of birth", value=None, min_value=date(1940, 1, 1), max_value=date.today(), key="app_dob")

                st.markdown("**Education**")
                e1, e2, e3 = st.columns([2, 2, 1])
                qualification = e1.text_input("Highest relevant qualification", key="app_qual")
                institution = e2.text_input("Institution", key="app_inst")
                year = e3.number_input("Year completed", min_value=0, max_value=2100, value=0, key="app_year")

                st.markdown("**Employment and experience**")
                j1, j2 = st.columns(2)
                employer = j1.text_input("Most recent employer", key="app_employer")
                position = j2.text_input("Most recent position", key="app_position")

                years = st.selectbox("Relevant stock / inventory experience", ["No experience", "Less than 1 year", "1–2 years", "3–5 years", "More than 5 years"], key="app_exp_years")
                q1, q2, q3 = st.columns(3)
                stocktake = q1.selectbox("Conducted physical stocktakes?", ["Select", "Yes", "No"], key="app_stocktake")
                reconciliation = q2.selectbox("Reconciled physical stock?", ["Select", "Yes", "No"], key="app_reconcile")
                excel = q3.selectbox("Microsoft Excel proficiency", ["Select", "Basic", "Intermediate", "Advanced"], key="app_excel")

                systems = st.text_area("Inventory systems / software used", key="app_systems")
                responsibilities = st.text_area("Briefly describe relevant responsibilities", key="app_resp")

                st.markdown("**Documents**")
                uploads = st.file_uploader("Upload your CV and supporting certificates (PDF, DOC, DOCX; max 5 MB each)", type=["pdf", "doc", "docx"], accept_multiple_files=True, key="app_uploads")
                consent = st.checkbox("I confirm that the information supplied is accurate and acknowledge the privacy notice and processing of my application for this recruitment purpose. *", key="app_consent")
                source_code = st.text_input("Campaign code (if provided)", key="app_source_code")
                submit = st.form_submit_button("Submit application", use_container_width=True)

            if submit:
                if not all([first.strip(), surname.strip(), email.strip(), phone.strip(), consent]):
                    st.error("Complete all required fields and acknowledge the privacy notice.")
                elif "@" not in email or "." not in email.split("@")[-1]:
                    st.error("Enter a valid email address.")
                elif stocktake == "Select" or reconciliation == "Select" or excel == "Select":
                    st.error("Complete all required experience questions.")
                elif not uploads or not any(Path(f.name).suffix.lower() in {".pdf", ".doc", ".docx"} for f in uploads):
                    st.error("Please upload your CV in PDF, DOC or DOCX format.")
                elif any(f.size > 5 * 1024 * 1024 for f in uploads):
                    st.error("Each uploaded document must be 5 MB or smaller.")
                else:
                    try:
                        source = q("SELECT id,campaign_id FROM ad_sources WHERE tracking_code=?", (source_code.strip(),)) if source_code.strip() else []
                        data = {
                            "vacancy_id": chosen,
                            "first_name": first.strip(),
                            "middle_name": middle.strip(),
                            "surname": surname.strip(),
                            "email": email.strip(),
                            "phone": phone.strip(),
                            "alternative_phone": alt.strip(),
                            "date_of_birth": dob.isoformat() if dob else None,
                            "location": location.strip(),
                            "education": [{"qualification": qualification.strip(), "institution": institution.strip(), "year_completed": year or None}],
                            "employment": [{"employer": employer.strip(), "position": position.strip(), "responsibilities": responsibilities.strip()}],
                            "answers": {
                                "Relevant experience": years,
                                "Conducted physical stocktakes": stocktake,
                                "Reconciled physical stock": reconciliation,
                                "Inventory systems": systems,
                                "Excel proficiency": excel,
                            },
                            "campaign_id": source[0]["campaign_id"] if source else None,
                            "source_id": source[0]["id"] if source else None,
                        }
                        ref = submit_application(data, uploads)
                        st.success(f"Application submitted successfully. Your reference is **{ref}**.")
                        st.info("Keep your application reference and registered phone number safe to check your status and interview arrangements.")
                        st.session_state["last_application_ref"] = ref
                    except Exception as e:
                        st.error(str(e))

    elif page == "Track application":
        st.markdown("<div class='drms-section-heading'><h2>Track your application</h2><p>Enter the reference and phone number used when you applied.</p></div>", unsafe_allow_html=True)
        with st.form("tracking"):
            t1, t2 = st.columns(2)
            ref = t1.text_input("Application reference", value=st.session_state.get("last_application_ref", ""), key="track_ref")
            phone = t2.text_input("Registered phone number", key="track_phone")
            go = st.form_submit_button("Check status", use_container_width=True)
        if go:
            rows = q("""SELECT a.id, a.application_ref, a.status, a.submitted_at, a.updated_at, v.title, c.name AS client
                        FROM applications a JOIN applicants p ON p.id=a.applicant_id
                        JOIN vacancies v ON v.id=a.vacancy_id JOIN clients c ON c.id=v.client_id
                        WHERE a.application_ref=? AND REPLACE(p.phone,' ','')=REPLACE(?,' ','')""",
                     (ref.strip(), phone.strip()))
            if rows:
                r = rows[0]
                st.success("Application record found")
                st.metric("Current status", STATUS_LABELS.get(r["status"], r["status"]))
                st.write(f'**Vacancy:** {r["title"]} · **Client:** {r["client"]}')
                st.write(f'**Submitted:** {r["submitted_at"]}')
                interviews = q("""SELECT scheduled_at, location, status FROM interviews
                                  WHERE application_id=? ORDER BY scheduled_at DESC""", (r["id"],))
                if interviews:
                    st.markdown("### Interview arrangements")
                    for idx, it in enumerate(interviews, 1):
                        with st.container(border=True):
                            st.markdown(f"**Interview {idx}**")
                            st.write(f'**Date and time:** {it["scheduled_at"] or "To be confirmed"}')
                            st.write(f'**Location / meeting link:** {it["location"] or "To be confirmed"}')
                            st.write(f'**Interview status:** {(it["status"] or "scheduled").replace("_", " ").title()}')
                elif r["status"] == "interview":
                    st.info("Your application has reached the interview stage. Interview details will appear here once they have been recorded.")
                else:
                    st.info("No interview has been scheduled for this application yet.")
                st.caption("Internal assessment scores and confidential recruitment notes are not displayed.")
            else:
                st.error("We could not verify that reference and phone number combination.")
    else:
        st.markdown("<div class='drms-section-heading'><h2>Privacy notice</h2></div>", unsafe_allow_html=True)
        st.write("Delintel Analytics processes applicant information for recruitment administration, candidate assessment and communication on behalf of the recruiting client. Information is accessed only by authorised personnel for the recruitment purpose, subject to applicable law and the relevant client agreement.")
        st.write("Applicants may contact the recruitment administrator to request access to or correction of their information, or to ask questions about its handling.")
        st.caption("Notice version 1.0 — the client-specific notice and legal review should be completed before publication.")
    st.divider()
    st.caption("Recruitment administration by Delintel Analytics · DRMS")

def render_overview():
    st.title("Recruitment dashboard")
    total = q("SELECT COUNT(*) n FROM applications")[0]["n"]
    pending = q("SELECT COUNT(*) n FROM applications WHERE status IN ('submitted','under_review')")[0]["n"]
    shortlisted = q("SELECT COUNT(*) n FROM applications WHERE status='shortlisted'")[0]["n"]
    interviews = q("SELECT COUNT(*) n FROM applications WHERE status='interview'")[0]["n"]
    a, b, c, d = st.columns(4)
    a.metric("Total applications", total)
    b.metric("Pending review", pending)
    c.metric("Shortlisted", shortlisted)
    d.metric("Interview stage", interviews)
    rows = q("""SELECT date(submitted_at) day, COUNT(*) count FROM applications
                GROUP BY date(submitted_at) ORDER BY day""")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Applications over time")
        if rows:
            st.plotly_chart(px.line(pd.DataFrame([dict(Date=r["day"], Applications=r["count"]) for r in rows]), x="Date", y="Applications", markers=True), use_container_width=True)
        else:
            st.info("Application activity will appear here.")
    rows = q("""SELECT status, COUNT(*) count FROM applications GROUP BY status ORDER BY count DESC""")
    with col2:
        st.subheader("Application status")
        if rows:
            st.plotly_chart(px.pie(pd.DataFrame([dict(Status=STATUS_LABELS.get(r["status"], r["status"]), Applications=r["count"]) for r in rows]), names="Status", values="Applications", hole=.45), use_container_width=True)
        else:
            st.info("No applications yet.")
    rows = q("""SELECT c.name client, v.title vacancy, COUNT(a.id) applications
                FROM vacancies v JOIN clients c ON c.id=v.client_id
                LEFT JOIN applications a ON a.vacancy_id=v.id GROUP BY v.id ORDER BY applications DESC""")
    st.subheader("Applications by vacancy")
    if rows:
        st.dataframe(pd.DataFrame([dict(Client=r["client"], Vacancy=r["vacancy"], Applications=r["applications"]) for r in rows]), use_container_width=True, hide_index=True)

def render_clients():
    st.title("Client management")
    with st.expander("Add client"):
        with st.form("add_client"):
            name = st.text_input("Organisation name *")
            industry = st.text_input("Industry")
            contact = st.text_input("Contact person")
            email = st.text_input("Contact email")
            phone = st.text_input("Phone")
            ok = st.form_submit_button("Create client")
        if ok:
            if not name.strip():
                st.error("Client name is required.")
            else:
                try:
                    cid = create_client(name, industry, contact, email, phone)
                    log_action("create_client", "client", cid)
                    st.success("Client created.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    rows = q("SELECT * FROM clients ORDER BY created_at DESC")
    if rows:
        st.dataframe(pd.DataFrame([dict(ID=r["id"], Name=r["name"], Industry=r["industry"], Contact=r["contact_name"], Email=r["contact_email"], Status=r["status"]) for r in rows]), use_container_width=True, hide_index=True)

def render_vacancies():
    st.title("Vacancy management")
    clients = q("SELECT * FROM clients WHERE status='active' ORDER BY name")
    with st.expander("Create vacancy", expanded=not bool(q("SELECT id FROM vacancies"))):
        if not clients:
            st.warning("Create a client first.")
        else:
            with st.form("new_vacancy"):
                client = st.selectbox("Client", clients, format_func=lambda x: x["name"])
                title = st.text_input("Job title")
                location = st.text_input("Location")
                desc = st.text_area("Job description")
                req = st.text_area("Requirements")
                positions = st.number_input("Number of positions", 1, 100, 1)
                deadline = st.date_input("Closing date", value=date.today())
                status = st.selectbox("Initial status", ["draft", "published"])
                ok = st.form_submit_button("Save vacancy")
            if ok:
                if not title.strip() or not desc.strip():
                    st.error("Job title and description are required.")
                else:
                    vid = create_vacancy(client["id"], title, location, desc, req, positions, deadline.isoformat(), status)
                    log_action("create_vacancy", "vacancy", vid)
                    st.success("Vacancy created.")
                    st.rerun()
    rows = q("""SELECT v.*, c.name AS client FROM vacancies v JOIN clients c ON c.id=v.client_id ORDER BY v.created_at DESC""")
    for r in rows:
        with st.container(border=True):
            st.subheader(r["title"])
            st.caption(f'{r["client"]} · {r["location"] or "Location not specified"} · {r["status"]}')
            st.write(r["description"])
            a, b = st.columns([2, 1])
            with a:
                st.caption(f'Closing: {r["closing_date"] or "Not specified"} · Positions: {r["positions_available"]}')
            with b:
                new = st.selectbox("Vacancy status", ["draft", "published", "paused", "closed", "cancelled"],
                                   index=["draft", "published", "paused", "closed", "cancelled"].index(r["status"]),
                                   key=f"vstatus{r['id']}")
                if st.button("Update", key=f"vupdate{r['id']}"):
                    execute("UPDATE vacancies SET status=? WHERE id=?", (new, r["id"]))
                    log_action("update_vacancy_status", "vacancy", r["id"], {"status": new})
                    st.rerun()

def application_frame():
    rows = q("""SELECT a.id, a.application_ref, p.first_name, p.surname, p.email, p.phone, p.location,
                       v.title AS vacancy, c.name AS client, a.status, a.submitted_at
                FROM applications a JOIN applicants p ON p.id=a.applicant_id
                JOIN vacancies v ON v.id=a.vacancy_id JOIN clients c ON c.id=v.client_id
                ORDER BY a.submitted_at DESC""")
    return pd.DataFrame([dict(
        ID=r["id"],
        Reference=r["application_ref"],
        Name=f'{r["first_name"]} {r["surname"]}',
        Email=r["email"],
        Phone=r["phone"],
        Location=r["location"],
        Client=r["client"],
        Vacancy=r["vacancy"],
        Status=STATUS_LABELS.get(r["status"], r["status"]),
        Submitted=r["submitted_at"]
    ) for r in rows])

def render_applications():
    st.title("Applications")
    df = application_frame()
    if df.empty:
        st.info("No applications have been received.")
        return
    f1, f2 = st.columns([2, 1])
    search = f1.text_input("Search name, reference, email or phone", key="app_search")
    statuses = f2.multiselect("Filter by status", sorted(df.Status.unique()), key="app_status_filter")
    if search:
        df = df[df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)]
    if statuses:
        df = df[df.Status.isin(statuses)]
    st.caption(f"{len(df)} application(s)")
    if df.empty:
        st.info("No applications match your filter.")
        return
    st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
    st.download_button("Download filtered applications (CSV)", df.drop(columns=["ID"]).to_csv(index=False).encode(), "applications.csv", "text/csv")
    st.divider()
    st.subheader("Open candidate record")
    selected = st.selectbox(
        "Select candidate application",
        df.ID.tolist(),
        format_func=lambda i: df[df.ID == i].iloc[0]["Reference"] + " — " + df[df.ID == i].iloc[0]["Name"],
        label_visibility="collapsed",
        key="selected_candidate_app"
    )
    render_candidate(selected)

def render_candidate(app_id):
    rows = q("""SELECT a.id AS app_id, a.application_ref, a.applicant_id, a.status AS app_status, a.submitted_at,
                       p.first_name, p.middle_name, p.surname, p.email, p.phone, p.alternative_phone, p.location,
                       v.title AS vacancy, c.name AS client
                FROM applications a
                JOIN applicants p ON p.id=a.applicant_id
                JOIN vacancies v ON v.id=a.vacancy_id
                JOIN clients c ON c.id=v.client_id
                WHERE a.id=?""", (app_id,))
    if not rows:
        return
    r = rows[0]
    with st.container(border=True):
        st.subheader(f'{r["first_name"]} {r["surname"]}')
        st.caption(f'{r["application_ref"]} · {r["vacancy"]} · {r["client"]}')
        x, y, z = st.columns(3)
        x.write("**Email**")
        x.write(r["email"])
        y.write("**Phone**")
        y.write(r["phone"])
        z.write("**Location**")
        z.write(r["location"] or "—")
        st.write("**Status:**", STATUS_LABELS.get(r["app_status"], r["app_status"]))

        docs = q("SELECT * FROM documents WHERE application_id=?", (app_id,))
        st.markdown("**Documents**")
        if not docs:
            st.caption("No documents attached.")
        for doc in docs:
            p = Path(doc["storage_path"])
            if p.exists():
                st.download_button(f'Download {doc["original_filename"]}', p.read_bytes(), doc["original_filename"], key=f'doc_{app_id}_{doc["id"]}')

        edu = q("SELECT * FROM education WHERE applicant_id=?", (r["applicant_id"],))
        if edu:
            st.markdown("**Education**")
            st.dataframe(pd.DataFrame([dict(Qualification=e["qualification"], Institution=e["institution"], Year=e["year_completed"]) for e in edu]), hide_index=True, use_container_width=True)

        jobs = q("SELECT * FROM employment_history WHERE applicant_id=?", (r["applicant_id"],))
        if jobs:
            st.markdown("**Employment history**")
            st.dataframe(pd.DataFrame([dict(Employer=e["employer"], Position=e["position"], Responsibilities=e["responsibilities"]) for e in jobs]), hide_index=True, use_container_width=True)

        answers = q("SELECT * FROM application_answers WHERE application_id=?", (app_id,))
        if answers:
            st.markdown("**Application answers**")
            st.dataframe(pd.DataFrame([dict(Question=a["question"], Answer=a["answer"]) for a in answers]), hide_index=True, use_container_width=True)

        st.markdown("**Update application status**")
        with st.form(f"status_form_{app_id}"):
            current_idx = STATUSES.index(r["app_status"]) if r["app_status"] in STATUSES else 0
            new_status = st.selectbox("New status", STATUSES, index=current_idx, format_func=lambda s: STATUS_LABELS.get(s, s), key=f"new_status_{app_id}")
            reason = st.text_input("Reason / internal note", key=f"status_reason_{app_id}")
            ok_status = st.form_submit_button("Save status")
        if ok_status:
            change_status(app_id, new_status, st.session_state.uid, reason)
            log_action("change_application_status", "application", app_id, {"status": new_status})
            st.success("Status updated.")
            st.rerun()

        st.markdown("**Screening record**")
        with st.form(f"screen_form_{app_id}"):
            result = st.selectbox("Screening outcome", ["eligible", "not_eligible", "needs_review"], key=f"screen_res_{app_id}")
            score = st.number_input("Screening score (optional)", 0.0, 100.0, 0.0, key=f"screen_score_{app_id}")
            notes = st.text_area("Screening notes", key=f"screen_notes_{app_id}")
            ok_screen = st.form_submit_button("Save screening")
        if ok_screen:
            execute("INSERT INTO screening_records(application_id,officer_id,result,score,notes) VALUES(?,?,?,?,?)",
                    (app_id, st.session_state.uid, result, score, notes))
            log_action("screen_application", "application", app_id)
            st.success("Screening saved.")
            st.rerun()

        st.markdown("**Recommendation**")
        with st.form(f"recommend_form_{app_id}"):
            rec = st.selectbox("Recommendation", ["strongly_recommend", "recommend", "further_review", "do_not_recommend"], key=f"rec_val_{app_id}")
            justification = st.text_area("Evidence-based justification", key=f"rec_just_{app_id}")
            ok_rec = st.form_submit_button("Save recommendation")
        if ok_rec:
            if not justification.strip():
                st.error("Provide a justification.")
            else:
                execute("INSERT INTO recommendations(application_id,prepared_by,recommendation,justification) VALUES(?,?,?,?)",
                        (app_id, st.session_state.uid, rec, justification))
                log_action("create_recommendation", "application", app_id)
                st.success("Recommendation saved.")
                st.rerun()

def render_assessments():
    st.title("Assessment management")
    vacancies = q("SELECT * FROM vacancies ORDER BY title")
    if not vacancies:
        st.info("Create a vacancy first.")
        return
    with st.expander("Create assessment template"):
        with st.form("template"):
            v = st.selectbox("Vacancy", vacancies, format_func=lambda x: x["title"])
            name = st.text_input("Assessment name", "Stock Controller Assessment")
            passscore = st.number_input("Suggested pass score", 0.0, 100.0, 60.0)
            st.caption("Enter six category weights. They must total 100.")
            names = ["Relevant experience", "Inventory knowledge", "Stock reconciliation", "Computer/reporting skills", "Integrity/accountability", "Communication/organisation"]
            cols = st.columns(3)
            weights = []
            defaults = [20, 20, 20, 15, 15, 10]
            for i, n in enumerate(names):
                weights.append(cols[i % 3].number_input(n, 0.0, 100.0, float(defaults[i]), key=f"w{i}"))
            ok = st.form_submit_button("Create template")
        if ok:
            if abs(sum(weights) - 100) > 0.01:
                st.error("Weights must total 100.")
            else:
                tid = execute("INSERT INTO assessment_templates(vacancy_id,name,max_score,pass_score) VALUES(?,?,100,?)", (v["id"], name, passscore))
                for n, w in zip(names, weights):
                    execute("INSERT INTO assessment_criteria(template_id,name,weight,max_score) VALUES(?,?,?,100)", (tid, n, w))
                log_action("create_assessment_template", "assessment_template", tid)
                st.success("Template created.")
                st.rerun()

    templates = q("""SELECT t.*, v.title AS vacancy FROM assessment_templates t JOIN vacancies v ON v.id=t.vacancy_id WHERE t.active=1""")
    if not templates:
        st.info("No assessment templates created yet.")
        return
    with st.form("score_assessment"):
        template = st.selectbox("Assessment template", templates, format_func=lambda x: x["name"] + " — " + x["vacancy"])
        apps = q("""SELECT a.id, a.application_ref, p.first_name, p.surname FROM applications a JOIN applicants p ON p.id=a.applicant_id
                    WHERE a.vacancy_id=?""", (template["vacancy_id"],))
        if not apps:
            st.info("No applications for this vacancy.")
            ok = False
        else:
            app = st.selectbox("Candidate", apps, format_func=lambda x: x["application_ref"] + " — " + x["first_name"] + " " + x["surname"])
            criteria = q("SELECT * FROM assessment_criteria WHERE template_id=?", (template["id"],))
            vals = {}
            for cr in criteria:
                vals[cr["id"]] = st.slider(cr["name"], 0.0, float(cr["max_score"]), 75.0, key=f"score_{template['id']}_{cr['id']}")
            comments = st.text_area("Assessment evidence and comments")
            ok = st.form_submit_button("Save assessment")
        if ok and apps:
            try:
                score = save_assessment(app["id"], template["id"], st.session_state.uid, {str(k): v for k, v in vals.items()}, comments)
                log_action("save_assessment", "application", app["id"], {"score": score})
                st.success(f"Assessment saved. Weighted score: {score:.2f}/100")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    st.subheader("Recorded assessment results")
    rows = q("""SELECT r.*, a.application_ref, p.first_name, p.surname, t.name AS template, u.full_name AS assessor
                FROM assessment_results r JOIN applications a ON a.id=r.application_id
                JOIN applicants p ON p.id=a.applicant_id JOIN assessment_templates t ON t.id=r.template_id
                JOIN users u ON u.id=r.assessor_id ORDER BY r.completed_at DESC""")
    if rows:
        st.dataframe(pd.DataFrame([dict(Reference=r["application_ref"], Candidate=r["first_name"] + " " + r["surname"], Assessment=r["template"], Score=round(r["total_score"] or 0, 2), Assessor=r["assessor"], Date=r["completed_at"]) for r in rows]), use_container_width=True, hide_index=True)

def render_interviews():
    st.title("Interview management")
    apps = q("""SELECT a.id, a.application_ref, p.first_name, p.surname, v.title AS vacancy FROM applications a
                JOIN applicants p ON p.id=a.applicant_id JOIN vacancies v ON v.id=a.vacancy_id ORDER BY a.submitted_at DESC""")
    if not apps:
        st.info("No applications available.")
        return
    with st.form("new_interview"):
        app = st.selectbox("Candidate", apps, format_func=lambda x: x["application_ref"] + " — " + x["first_name"] + " " + x["surname"])
        when = st.text_input("Date and time (e.g. 2026-11-20 10:00)")
        location = st.text_input("Interview location / meeting link")
        notes = st.text_area("Panel instructions")
        ok = st.form_submit_button("Schedule interview")
    if ok:
        if not when.strip():
            st.error("Enter the interview date and time.")
        else:
            execute("INSERT INTO interviews(application_id,scheduled_at,location,notes,created_by) VALUES(?,?,?,?,?)",
                    (app["id"], when, location, notes, st.session_state.uid))
            change_status(app["id"], "interview", st.session_state.uid, "Interview scheduled")
            log_action("schedule_interview", "application", app["id"])
            st.success("Interview scheduled.")
            st.rerun()
    rows = q("""SELECT i.*, a.application_ref, p.first_name, p.surname, v.title AS vacancy FROM interviews i
                JOIN applications a ON a.id=i.application_id JOIN applicants p ON p.id=a.applicant_id
                JOIN vacancies v ON v.id=a.vacancy_id ORDER BY i.scheduled_at""")
    if rows:
        st.dataframe(pd.DataFrame([dict(Reference=r["application_ref"], Candidate=r["first_name"] + " " + r["surname"], Vacancy=r["vacancy"], When=r["scheduled_at"], Location=r["location"], Status=r["status"]) for r in rows]), use_container_width=True, hide_index=True)

def render_campaigns():
    st.title("Advertising campaigns")
    clients = q("SELECT * FROM clients ORDER BY name")
    vacancies = q("SELECT * FROM vacancies ORDER BY title")
    with st.expander("Create campaign"):
        if not clients or not vacancies:
            st.warning("Create a client and vacancy first.")
        else:
            with st.form("campaign"):
                client = st.selectbox("Client", clients, format_func=lambda x: x["name"])
                vacs = [v for v in vacancies if v["client_id"] == client["id"]]
                if vacs:
                    vacancy = st.selectbox("Vacancy", vacs, format_func=lambda x: x["title"])
                    name = st.text_input("Campaign name")
                    budget = st.number_input("Budget (USD)", 0.0, 1000000.0, 0.0)
                    start = st.date_input("Start date")
                    end = st.date_input("End date")
                    ok = st.form_submit_button("Create campaign")
                else:
                    st.info("This client has no vacancies.")
                    ok = False
            if ok:
                cid = execute("INSERT INTO campaigns(client_id,vacancy_id,name,start_date,end_date,budget) VALUES(?,?,?,?,?,?)",
                              (client["id"], vacancy["id"], name, start.isoformat(), end.isoformat(), budget))
                log_action("create_campaign", "campaign", cid)
                st.success("Campaign created.")
                st.rerun()
    campaigns = q("""SELECT ca.*, c.name AS client, v.title AS vacancy FROM campaigns ca JOIN clients c ON c.id=ca.client_id
                     JOIN vacancies v ON v.id=ca.vacancy_id ORDER BY ca.created_at DESC""")
    for ca in campaigns:
        with st.container(border=True):
            st.write(f'**{ca["name"]}** · {ca["client"]} · {ca["vacancy"]}')
            with st.form(f"source{ca['id']}"):
                source = st.text_input("Advertising source (e.g. Facebook)", key=f"src{ca['id']}")
                code = st.text_input("Tracking code", key=f"code{ca['id']}", value=f"CAMPAIGN-{ca['id']}-FB")
                ok = st.form_submit_button("Add source")
            if ok:
                try:
                    execute("INSERT INTO ad_sources(campaign_id,source_name,tracking_code) VALUES(?,?,?)", (ca["id"], source, code))
                    st.success("Source added.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    rows = q("""SELECT s.source_name, s.tracking_code, COUNT(a.id) applications FROM ad_sources s
                LEFT JOIN applications a ON a.source_id=s.id GROUP BY s.id""")
    if rows:
        st.subheader("Source performance")
        st.dataframe(pd.DataFrame([dict(Source=r["source_name"], Code=r["tracking_code"], Applications=r["applications"]) for r in rows]), use_container_width=True, hide_index=True)

def render_reports():
    st.title("Reports and exports")
    df = application_frame()
    if df.empty:
        st.info("No recruitment data available.")
        return
    st.subheader("Recruitment summary")
    st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
    c1, c2, c3 = st.columns(3)
    c1.download_button("Export applications to Excel", excel_export(df.drop(columns=["ID"])), "DRMS_recruitment_report.xlsx", use_container_width=True)
    c2.download_button("Export applications to CSV", df.drop(columns=["ID"]).to_csv(index=False).encode(), "DRMS_recruitment_report.csv", use_container_width=True)
    if c3.button("Generate PDF summary", use_container_width=True):
        pdf = make_pdf(df.drop(columns=["ID"]))
        st.download_button("Download PDF report", pdf, "DRMS_recruitment_summary.pdf", "application/pdf")

def excel_export(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Applications")
    return out.getvalue()

def make_pdf(df):
    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Delintel Analytics — Recruitment Summary", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Generated: {datetime.now():%Y-%m-%d %H:%M}", styles["Normal"]),
        Spacer(1, 12),
    ]
    data = [list(df.columns)] + df.astype(str).values.tolist()
    data = [row[:6] for row in data]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), .25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    doc.build(story)
    return out.getvalue()

def render_users():
    st.title("User management")
    with st.expander("Create user"):
        with st.form("create_user"):
            username = st.text_input("Username")
            fullname = st.text_input("Full name")
            email = st.text_input("Email")
            password = st.text_input("Temporary password", type="password")
            roles = q("SELECT * FROM roles ORDER BY name")
            role = st.selectbox("Role", roles, format_func=lambda x: x["name"])
            ok = st.form_submit_button("Create user")
        if ok:
            if not all([username, fullname, email, password]) or len(password) < 12:
                st.error("Complete all fields. Password must be at least 12 characters.")
            else:
                try:
                    uid = execute("INSERT INTO users(username,email,full_name,password_hash,must_change_password) VALUES(?,?,?,?,1)",
                                  (username, email, fullname, hash_password(password)))
                    execute("INSERT INTO user_roles(user_id,role_id) VALUES(?,?)", (uid, role["id"]))
                    log_action("create_user", "user", uid)
                    st.success("User created. They must change their temporary password at first login.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    rows = q("""SELECT u.*, GROUP_CONCAT(r.name, ', ') roles FROM users u LEFT JOIN user_roles ur ON ur.user_id=u.id
                LEFT JOIN roles r ON r.id=ur.role_id GROUP BY u.id ORDER BY u.id""")
    if rows:
        st.dataframe(pd.DataFrame([dict(ID=r["id"], Username=r["username"], Name=r["full_name"], Email=r["email"], Roles=r["roles"], Active=bool(r["active"]), LastLogin=r["last_login"]) for r in rows]), use_container_width=True, hide_index=True)
        selected = st.selectbox("Manage account", rows, format_func=lambda x: x["username"] + " — " + x["full_name"])
        if selected["id"] != st.session_state.uid:
            active = st.toggle("Account active", value=bool(selected["active"]), key="useractive")
            if st.button("Save account status"):
                execute("UPDATE users SET active=? WHERE id=?", (int(active), selected["id"]))
                log_action("update_user_active", "user", selected["id"], {"active": active})
                st.rerun()

def render_audit():
    st.title("Audit logs")
    rows = q("""SELECT a.*, u.username FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.created_at DESC LIMIT 500""")
    if rows:
        st.dataframe(pd.DataFrame([dict(Time=r["created_at"], User=r["username"] or "System", Action=r["action"], Entity=r["entity_type"], Record=r["entity_id"], Details=r["details"]) for r in rows]), use_container_width=True, hide_index=True)
    else:
        st.info("No audit activity recorded.")

def render_settings():
    st.title("System settings")
    st.write("Database location:", str(DB_PATH))
    st.write("Upload storage:", str(UPLOAD_PATH))
    st.write("Database size:", f"{DB_PATH.stat().st_size/1024:.1f} KB" if DB_PATH.exists() else "Not created")
    with st.expander("Create database backup"):
        if st.button("Back up database now"):
            backup_dir = Path("storage/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            dest = backup_dir / f"drms_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
            source = sqlite3.connect(DB_PATH)
            target = sqlite3.connect(dest)
            source.backup(target)
            target.close()
            source.close()
            st.success(f"Backup created: {dest}")
    st.warning("Backups created here remain on this server. Configure independent encrypted off-site backups before production.")
    with st.form("change_own_password"):
        st.subheader("Change your password")
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password (12+ characters)", type="password")
        confirm = st.text_input("Confirm password", type="password")
        ok = st.form_submit_button("Change password")
    if ok:
        u = q("SELECT * FROM users WHERE id=?", (st.session_state.uid,))[0]
        if not verify_password(old, u["password_hash"]):
            st.error("Current password is incorrect.")
        elif len(new) < 12:
            st.error("Password must contain at least 12 characters.")
        elif new != confirm:
            st.error("Passwords do not match.")
        else:
            execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?", (hash_password(new), u["id"]))
            log_action("change_password", "user", u["id"])
            st.success("Password changed.")

def internal_app():
    if st.session_state.get("must_change"):
        force_password_change()
        return
    st.sidebar.markdown("## DRMS")
    st.sidebar.caption("Delintel Analytics")
    st.sidebar.write(f'**{st.session_state.full_name}**')
    st.sidebar.caption(" · ".join(st.session_state.roles))
    nav = ["Dashboard", "Clients", "Vacancies", "Applications", "Assessments", "Interviews", "Advertising", "Reports"]
    if has_role("Super Administrator"):
        nav += ["User Management", "Audit Logs", "Settings"]
    elif has_role("Recruitment Manager"):
        nav += ["Audit Logs"]
    page = st.sidebar.radio("Navigation", nav)
    if st.sidebar.button("Log out", use_container_width=True):
        log_action("logout", "user", st.session_state.uid)
        logout()
    if page == "Dashboard":
        render_overview()
    elif page == "Clients":
        if has_role("Super Administrator", "Recruitment Manager"):
            render_clients()
        else:
            st.error("You do not have permission to manage clients.")
    elif page == "Vacancies":
        if has_role("Super Administrator", "Recruitment Manager", "HR Officer"):
            render_vacancies()
        else:
            st.error("Access denied.")
    elif page == "Applications":
        if has_role("Super Administrator", "Recruitment Manager", "HR Officer", "Assessment Officer"):
            render_applications()
        else:
            st.error("Access denied.")
    elif page == "Assessments":
        if has_role("Super Administrator", "Recruitment Manager", "Assessment Officer"):
            render_assessments()
        else:
            st.error("Access denied.")
    elif page == "Interviews":
        if has_role("Super Administrator", "Recruitment Manager", "HR Officer"):
            render_interviews()
        else:
            st.error("Access denied.")
    elif page == "Advertising":
        if has_role("Super Administrator", "Recruitment Manager", "Marketing Officer"):
            render_campaigns()
        else:
            st.error("Access denied.")
    elif page == "Reports":
        render_reports()
    elif page == "User Management":
        if has_role("Super Administrator"):
            render_users()
        else:
            st.error("Access denied.")
    elif page == "Audit Logs":
        if has_role("Super Administrator", "Recruitment Manager"):
            render_audit()
        else:
            st.error("Access denied.")
    elif page == "Settings":
        if has_role("Super Administrator"):
            render_settings()
        else:
            st.error("Scan denied.")

if not logged_in():
    mode = st.radio("Access", ["Applicant portal", "Staff login"], horizontal=True, label_visibility="collapsed")
    if mode == "Applicant portal":
        public_portal()
    else:
        login()
else:
    internal_app()