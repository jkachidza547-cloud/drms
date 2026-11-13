import secrets, hashlib, re, mimetypes
from pathlib import Path
from datetime import datetime
from .database import db, UPLOAD_PATH, audit

def slug_ref(prefix, rowid):
    return f"{prefix}-{datetime.now():%Y}-{rowid:06d}"

def create_client(name, industry="", contact_name="", contact_email="", phone=""):
    with db() as c:
        cur=c.execute("""INSERT INTO clients(name,industry,contact_name,contact_email,phone)
                         VALUES(?,?,?,?,?)""",(name.strip(),industry,contact_name,contact_email,phone))
        return cur.lastrowid

def create_vacancy(client_id,title,location,description,requirements,positions,closing_date,status="draft"):
    with db() as c:
        cur=c.execute("""INSERT INTO vacancies(client_id,title,location,description,requirements,
                         positions_available,closing_date,status) VALUES(?,?,?,?,?,?,?,?)""",
                      (client_id,title,location,description,requirements,positions,closing_date,status))
        return cur.lastrowid

def submit_application(data, uploaded_files):
    with db() as c:
        vacancy=c.execute("SELECT * FROM vacancies WHERE id=? AND status='published'",(data["vacancy_id"],)).fetchone()
        if not vacancy:
            raise ValueError("This vacancy is not currently accepting applications.")
        email=data["email"].strip().lower()
        phone=re.sub(r"\s+","",data["phone"])
        applicant=c.execute("SELECT * FROM applicants WHERE lower(email)=? OR phone=?",(email,phone)).fetchone()
        if applicant:
            existing=c.execute("SELECT id FROM applications WHERE applicant_id=? AND vacancy_id=?",
                               (applicant["id"],data["vacancy_id"])).fetchone()
            if existing:
                raise ValueError("An application for this vacancy already exists using these contact details.")
            applicant_id=applicant["id"]
        else:
            cur=c.execute("""INSERT INTO applicants(applicant_ref,first_name,middle_name,surname,email,phone,
                             alternative_phone,date_of_birth,location)
                             VALUES('PENDING',?,?,?,?,?,?,?,?)""",
                          (data["first_name"],data.get("middle_name"),data["surname"],email,phone,
                           data.get("alternative_phone"),data.get("date_of_birth"),data.get("location")))
            applicant_id=cur.lastrowid
            applicant_ref=slug_ref("DRP",applicant_id)
            c.execute("UPDATE applicants SET applicant_ref=? WHERE id=?",(applicant_ref,applicant_id))
        cur=c.execute("""INSERT INTO applications(application_ref,applicant_id,vacancy_id,campaign_id,source_id,status)
                         VALUES('PENDING',?,?,?,?,'submitted')""",
                      (applicant_id,data["vacancy_id"],data.get("campaign_id"),data.get("source_id")))
        app_id=cur.lastrowid
        app_ref=slug_ref("DRMS",app_id)
        c.execute("UPDATE applications SET application_ref=? WHERE id=?",(app_ref,app_id))
        for e in data.get("education",[]):
            if e.get("qualification") and e.get("institution"):
                c.execute("INSERT INTO education(applicant_id,qualification,institution,year_completed) VALUES(?,?,?,?)",
                          (applicant_id,e["qualification"],e["institution"],e.get("year_completed") or None))
        for e in data.get("employment",[]):
            if e.get("employer") and e.get("position"):
                c.execute("""INSERT INTO employment_history(applicant_id,employer,position,start_date,end_date,
                             is_current,responsibilities) VALUES(?,?,?,?,?,?,?)""",
                          (applicant_id,e["employer"],e["position"],e.get("start_date"),e.get("end_date"),
                           int(e.get("is_current",False)),e.get("responsibilities")))
        for q,a in data.get("answers",{}).items():
            c.execute("INSERT INTO application_answers(application_id,question,answer) VALUES(?,?,?)",
                      (app_id,q,str(a)))
        c.execute("INSERT INTO privacy_consents(applicant_id,consent_type,notice_version,consented) VALUES(?,?,?,1)",
                  (applicant_id,"application_processing","1.0"))
        c.execute("INSERT INTO status_history(application_id,old_status,new_status,reason) VALUES(?,NULL,'submitted','Initial submission')",(app_id,))
        for f in uploaded_files:
            original=Path(f.name).name
            suffix=Path(original).suffix.lower()
            allowed={".pdf",".doc",".docx"}
            if suffix not in allowed:
                raise ValueError(f"Unsupported file type: {original}. Upload PDF, DOC or DOCX files only.")
            content=f.getvalue()
            if len(content)>5*1024*1024:
                raise ValueError(f"{original} exceeds the 5 MB limit.")
            if suffix==".pdf" and not content.startswith(b"%PDF"):
                raise ValueError(f"{original} does not appear to be a valid PDF.")
            safe_name=secrets.token_hex(20)+suffix
            target=UPLOAD_PATH/safe_name
            target.write_bytes(content)
            mime=mimetypes.guess_type(original)[0] or "application/octet-stream"
            c.execute("""INSERT INTO documents(application_id,document_type,original_filename,storage_path,
                         mime_type,file_size,checksum) VALUES(?,?,?,?,?,?,?)""",
                      (app_id,"supporting_document",original,str(target),mime,len(content),
                       hashlib.sha256(content).hexdigest()))
        return app_ref

def change_status(app_id,new_status,user_id,reason=""):
    with db() as c:
        old=c.execute("SELECT status FROM applications WHERE id=?",(app_id,)).fetchone()
        if not old: raise ValueError("Application not found.")
        c.execute("UPDATE applications SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(new_status,app_id))
        c.execute("""INSERT INTO status_history(application_id,old_status,new_status,changed_by,reason)
                     VALUES(?,?,?,?,?)""",(app_id,old["status"],new_status,user_id,reason))
        c.execute("INSERT INTO notification_log(application_id,channel,message,status) VALUES(?,?,?,?)",
                  (app_id,"portal",f"Application status changed to {new_status}","recorded"))

def save_assessment(app_id,template_id,user_id,scores,comments):
    with db() as c:
        criteria=c.execute("SELECT * FROM assessment_criteria WHERE template_id=?",(template_id,)).fetchall()
        if not criteria: raise ValueError("Assessment template has no criteria.")
        weight_total=sum(float(x["weight"]) for x in criteria)
        if abs(weight_total-100)>0.01: raise ValueError("Assessment weights must total 100%.")
        weighted=0
        for cr in criteria:
            score=float(scores[str(cr["id"])])
            if score<0 or score>float(cr["max_score"]):
                raise ValueError(f"Score for {cr['name']} is outside its allowed range.")
            weighted += (score/float(cr["max_score"]))*float(cr["weight"])
        cur=c.execute("""INSERT INTO assessment_results(application_id,template_id,assessor_id,total_score,comments)
                         VALUES(?,?,?,?,?)""",(app_id,template_id,user_id,weighted,comments))
        result_id=cur.lastrowid
        for cr in criteria:
            c.execute("INSERT INTO assessment_scores(result_id,criterion_id,score) VALUES(?,?,?)",
                      (result_id,cr["id"],float(scores[str(cr["id"])])))
        return weighted

def add_audit(con,user_id,action,entity_type=None,entity_id=None,details=None):
    import json
    con.execute("""INSERT INTO audit_logs(user_id,action,entity_type,entity_id,details)
                   VALUES(?,?,?,?,?)""",(user_id,action,entity_type,str(entity_id) if entity_id else None,
                                          json.dumps(details or {})))
