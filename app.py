import datetime, os, re, sqlite3, streamlit as st
from dotenv import load_dotenv
load_dotenv()
st.set_page_config(page_title="Health Prediction System", page_icon="🏥", layout="wide")
DB_FILE = "patient_records.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL, dob TEXT NOT NULL, 
        email TEXT NOT NULL UNIQUE, 
        glucose REAL NOT NULL, haemoglobin REAL NOT NULL, 
        cholesterol REAL NOT NULL, remarks TEXT)""")
    conn.commit(); conn.close()
init_db()

def is_email_exists(email, exclude_id=None):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    if exclude_id:
        cur.execute("SELECT id FROM patients WHERE lower(email)=lower(?) AND id!=?", (email, exclude_id))
    else:
        cur.execute("SELECT id FROM patients WHERE lower(email)=lower(?)", (email,))
    exists = cur.fetchone() is not None
    conn.close(); return exists

def add_patient(full_name, dob, email, glucose, haemoglobin, cholesterol, remarks):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO patients VALUES (NULL,?,?,?,?,?,?,?)",
                 (full_name, dob, email, glucose, haemoglobin, cholesterol, remarks))
    conn.commit(); conn.close()

def get_all_patients():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor(); cur.execute("SELECT * FROM patients ORDER BY id DESC")
    rows = cur.fetchall(); conn.close(); return rows

def update_patient(patient_id, full_name, dob, email, glucose, haemoglobin, cholesterol, remarks):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE patients SET full_name=?, dob=?, email=?, glucose=?, haemoglobin=?, cholesterol=?, remarks=? WHERE id=?",
                 (full_name, dob, email, glucose, haemoglobin, cholesterol, remarks, patient_id))
    conn.commit(); conn.close()

def delete_patient(patient_id):
    conn = sqlite3.connect(DB_FILE); conn.execute("DELETE FROM patients WHERE id=?", (patient_id,))
    conn.commit(); conn.close()

def validate_input(full_name, dob_str, email, glucose, haemoglobin, cholesterol, exclude_id=None):
    errors=[]
    if not full_name.strip(): errors.append("Full Name empty")
    if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email): errors.append(f"Invalid email: {email}")
    elif is_email_exists(email, exclude_id): errors.append(f"Duplicate! Email '{email}' already exists - must be unique")
    parsed_dob=None
    for fmt in ["%d.%m.%Y","%d/%m/%Y","%d-%m-%Y"]:
        try: parsed_dob=datetime.datetime.strptime(dob_str.strip(), fmt).date(); break
        except: continue
    if not parsed_dob: errors.append(f"Invalid Date: {dob_str}")
    elif parsed_dob > datetime.date.today(): errors.append(f"DOB future: {dob_str}")
    try:
        if float(glucose)<=0 or float(haemoglobin)<=0 or float(cholesterol)<=0: errors.append("Blood values >0")
    except: errors.append("Blood values numeric")
    return errors, parsed_dob

def generate_ai_remarks(glucose, haemoglobin, cholesterol):
    api_key=os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client=OpenAI(api_key=api_key)
            prompt=f"Blood Test: Glucose {glucose}, Hb {haemoglobin}, Chol {cholesterol}. 1-2 line risk."
            res=client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role":"user","content":prompt}], max_tokens=80)
            return res.choices[0].message.content.strip()
        except: pass
    risks=[]
    if glucose>200: risks.append("High Glucose (Diabetes)")
    if haemoglobin<11: risks.append("Low Hb (Anemia)")
    elif haemoglobin>17: risks.append("High Hb")
    if cholesterol>240: risks.append("High Cholesterol")
    return "Risks: "+", ".join(risks) if risks else "Normal Profile - Low Risk"

def show_records(rows):
    if not rows: st.info("No records."); return
    for r in rows: st.markdown(f"**ID {r[0]} | {r[1]} | {r[2]} | {r[3]}** | Glucose: {r[4]} | Hb: {r[5]} | Chol: {r[6]} | _{r[7]}_")
    st.success(f"Total: {len(rows)}")

st.title("🏥 Health Prediction System")
tab1, tab2, tab3, tab4 = st.tabs(["➕ Add", "📋 View", "✏️ Edit", "🗑️ Delete"])
with tab1:
    with st.form("add_form"):
        c1,c2=st.columns(2)
        with c1: full_name=st.text_input("Full Name"); dob_input=st.text_input("DOB dd.mm.yyyy"); email=st.text_input("Email")
        with c2: glucose=st.number_input("Glucose",0.0); haemoglobin=st.number_input("Haemoglobin",0.0); cholesterol=st.number_input("Cholesterol",0.0)
        if st.form_submit_button("Submit & Generate AI Prediction"):
            errs, vd=validate_input(full_name, dob_input, email, glucose, haemoglobin, cholesterol)
            if errs:
                for e in errs: st.error(f"❌ {e}")
            else:
                fd=vd.strftime("%d/%m/%Y"); remarks=generate_ai_remarks(glucose, haemoglobin, cholesterol)
                try:
                    add_patient(full_name, fd, email, glucose, haemoglobin, cholesterol, remarks)
                    st.success("✅ Patient saved!"); st.info(f"AI Remark: {remarks}")
                except sqlite3.IntegrityError: st.error(f"❌ Duplicate! Email {email} already exists")

with tab2: st.subheader("Records"); show_records(get_all_patients())
with tab3:
    rows=get_all_patients()
    if rows:
        sel=st.selectbox("Select to Edit", [f"{r[0]} - {r[1]} - {r[3]}" for r in rows], key="e")
        pid=int(sel.split(" - ")[0]); row=[r for r in rows if r[0]==pid][0]
        with st.form("edit_form"):
            c1,c2=st.columns(2)
            with c1: fn=st.text_input("Full Name", value=row[1]); db=st.text_input("DOB", value=row[2]); em=st.text_input("Email", value=row[3])
            with c2: gl=st.number_input("Glucose", value=float(row[4])); hb=st.number_input("Haemoglobin", value=float(row[5])); ch=st.number_input("Cholesterol", value=float(row[6]))
            if st.form_submit_button("Update"):
                errs, vd=validate_input(fn, db, em, gl, hb, ch, exclude_id=pid)
                if errs:
                    for e in errs: st.error(f"❌ {e}")
                else:
                    fd=vd.strftime("%d/%m/%Y"); remarks=generate_ai_remarks(gl, hb, ch)
                    update_patient(pid, fn, fd, em, gl, hb, ch, remarks); st.success(f"✅ ID {pid} updated!"); st.rerun()
with tab4:
    rows=get_all_patients()
    if rows:
        sel=st.selectbox("Select to Delete", [f"{r[0]} - {r[1]} - {r[3]}" for r in rows], key="d")
        pid=int(sel.split(" - ")[0])
        if st.button("Delete Record", type="primary"): delete_patient(pid); st.warning(f"❌ ID {pid} deleted!"); st.rerun()
        show_records(rows)