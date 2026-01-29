import streamlit as st
import requests

from file_utils import read_pdf, read_docx, save_pdf, save_docx

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Resume Generator", layout="wide")
st.title("🧑‍💻 AI Resume & Cover Letter Generator (Open Source)")
st.caption("Ollama + FastAPI + Streamlit | ATS Resume + Cover Letter + Missing Skills + LinkedIn Summary + Job Scraper Agent")

# Session token
if "token" not in st.session_state:
    st.session_state.token = None

# JD Prefill
if "job_desc_prefill" not in st.session_state:
    st.session_state.job_desc_prefill = ""

# Rate-limit flag for job search button
if "job_search_running" not in st.session_state:
    st.session_state.job_search_running = False


def safe_json(resp: requests.Response):
    """Return JSON if possible else return None (prevents JSONDecodeError)."""
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype.lower():
        try:
            return resp.json()
        except Exception:
            return None
    return None


# -------------------- AUTH UI --------------------
st.sidebar.header("🔐 Login / Register")
mode = st.sidebar.radio("Choose", ["Login", "Register"], horizontal=True)

# -------- REGISTER --------
if mode == "Register":
    username = st.sidebar.text_input("Username", key="reg_user")
    email = st.sidebar.text_input("Email", key="reg_email")
    password = st.sidebar.text_input("Password", type="password", key="reg_pass")

    if st.sidebar.button("Register", use_container_width=True):
        if not username or not email or not password:
            st.sidebar.warning("Please fill all fields.")
        else:
            # bcrypt limit
            if len(password.encode("utf-8")) > 72:
                st.sidebar.error("Password too long. Max 72 bytes. Use shorter password.")
                st.stop()

            r = requests.post(f"{API}/register", json={
                "username": username,
                "email": email,
                "password": password
            })

            data = safe_json(r)
            if r.status_code == 200:
                st.sidebar.success("Registered ✅ Now Login")
            else:
                if data and "detail" in data:
                    st.sidebar.error(data["detail"])
                else:
                    st.sidebar.error(f"Register failed: {r.text}")

# -------- LOGIN --------
if mode == "Login":
    username = st.sidebar.text_input("Username", key="login_user")
    password = st.sidebar.text_input("Password", type="password", key="login_pass")

    if st.sidebar.button("Login", use_container_width=True):
        if not username or not password:
            st.sidebar.warning("Enter username & password.")
        else:
            r = requests.post(f"{API}/login", json={
                "username": username,
                "password": password
            })

            data = safe_json(r)
            if r.status_code == 200 and data:
                st.session_state.token = data["access_token"]
                st.sidebar.success("Logged in ✅")
                st.rerun()
            else:
                if data and "detail" in data:
                    st.sidebar.error(data["detail"])
                else:
                    st.sidebar.error(f"Login failed: {r.text}")

# -------- LOGOUT --------
if st.session_state.token:
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.token = None
        st.rerun()

# Must login to proceed
if st.session_state.token is None:
    st.warning("Please login to use the generator.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# -------------------- HISTORY UI --------------------
st.sidebar.header("📌 History")

hist = []
try:
    hist_resp = requests.get(f"{API}/history", headers=headers, timeout=60)
    hist_data = safe_json(hist_resp)
    if hist_resp.status_code == 200 and hist_data:
        hist = hist_data.get("history", [])
except Exception as e:
    st.sidebar.error(f"History fetch error: {e}")

if hist:
    options = [
        f"{h['id']} | {h.get('job_title','')} | {h['created_at']} | {h['job_match_score']}% | {h['model']}"
        for h in hist
    ]
    selected = st.sidebar.selectbox("Load Previous Output", ["None"] + options)

    if selected != "None":
        hist_id = int(selected.split("|")[0].strip())
        item_resp = requests.get(f"{API}/history/{hist_id}", headers=headers, timeout=60)
        item_data = safe_json(item_resp)

        if item_resp.status_code == 200 and item_data:
            item = item_data["item"]

            st.subheader("✅ Loaded Saved Output")
            st.write(f"**Job Title:** {item.get('job_title','')}")
            st.write(
                f"**Created:** {item['created_at']} | "
                f"**Match Score:** {item['job_match_score']}% | "
                f"**Model:** {item['model']}"
            )

            st.text_area("ATS Resume", item["ats_resume"], height=260)
            st.text_area("Cover Letter", item["cover_letter"], height=200)
            st.text_area("Missing Skills", item["missing_skills"], height=160)
            st.text_area("LinkedIn Summary", item["linkedin_summary"], height=140)

            st.stop()
        else:
            st.error(f"Could not load history item: {item_resp.text}")
else:
    st.sidebar.info("No history saved yet.")

st.divider()

# -------------------- JOB SCRAPER AGENT --------------------
st.subheader("🔍 Job Scraper Agent (JSearch / RapidAPI)")

kw = st.text_input("Keyword", "Python Developer")
loc = st.text_input("Location", "India")

if st.button("Search Jobs", use_container_width=True):
    if st.session_state.job_search_running:
        st.warning("Please wait... request already running")
        st.stop()

    st.session_state.job_search_running = True

    try:
        jr = requests.post(
            f"{API}/jobs/search",
            headers=headers,
            json={"keyword": kw, "location": loc, "page": 1},
            timeout=120
        )
        jdata = safe_json(jr)

        if jr.status_code != 200 or not jdata:
            st.error(jr.text)
        else:
            jobs = jdata.get("jobs", [])
            if not jobs:
                st.info("No jobs found.")
            else:
                st.success(f"Found {len(jobs)} jobs ✅")
                for idx, j in enumerate(jobs[:10], start=1):
                    with st.expander(f"{idx}. {j.get('title')} — {j.get('company')}"):
                        st.write(f"📍 {j.get('location')}")
                        st.write(f"🌐 Source: {j.get('publisher')}")
                        st.write("### Description (snippet)")
                        st.write(j.get("snippet", ""))

                        if j.get("apply_link"):
                            st.link_button("Apply Link", j["apply_link"])

                        if st.button(f"Use this JD #{idx}", key=f"usejd_{idx}"):
                            st.session_state.job_desc_prefill = j.get("snippet", "")
                            st.success("Job Description loaded ✅ Scroll down to generator")
    finally:
        st.session_state.job_search_running = False

st.divider()

# -------------------- MAIN GENERATOR UI --------------------
st.subheader("🧠 Resume Generator")

model = st.selectbox("Choose Model", ["llama3", "mistral", "gemma"])
job_title = st.text_input("Job Title (optional)", "")

uploaded = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

resume_text = ""
if uploaded:
    if uploaded.name.lower().endswith(".pdf"):
        resume_text = read_pdf(uploaded)
    elif uploaded.name.lower().endswith(".docx"):
        resume_text = read_docx(uploaded)

col1, col2 = st.columns(2)

with col1:
    resume = st.text_area("📄 Resume Text", value=resume_text, height=350)

with col2:
    job_default = st.session_state.get("job_desc_prefill", "")
    job = st.text_area("🧾 Job Description", value=job_default, height=350)

if st.button("🚀 Generate All Outputs", use_container_width=True):
    if resume.strip() == "" or job.strip() == "":
        st.error("Please provide Resume and Job Description.")
        st.stop()

    with st.spinner("Generating..."):
        try:
            res = requests.post(
                f"{API}/generate",
                headers=headers,
                json={"resume": resume, "job": job, "model": model, "job_title": job_title},
                timeout=300
            )
        except Exception as e:
            st.error(f"Backend connection error: {e}")
            st.stop()

    data = safe_json(res)
    if res.status_code != 200 or not data:
        st.error("Backend returned an invalid response.")
        st.code(res.text)
        st.stop()

    st.subheader(f"✅ Job Match Score: {data['job_match_score']}%")

    ats_resume = st.text_area("📌 ATS Resume", data["ats_resume"], height=300)
    cover_letter = st.text_area("✉️ Cover Letter", data["cover_letter"], height=220)
    missing_skills = st.text_area("🧠 Missing Skills", data["missing_skills"], height=180)
    linkedin_summary = st.text_area("🔗 LinkedIn Summary", data["linkedin_summary"], height=160)

    st.subheader("⬇️ Download Files")

    resume_pdf_path = save_pdf(ats_resume, "ATS_Resume.pdf")
    resume_docx_path = save_docx(ats_resume, "ATS_Resume.docx")

    cover_pdf_path = save_pdf(cover_letter, "CoverLetter.pdf")
    cover_docx_path = save_docx(cover_letter, "CoverLetter.docx")

    with open(resume_pdf_path, "rb") as f:
        st.download_button("Download ATS Resume (PDF)", f, file_name="ATS_Resume.pdf")

    with open(resume_docx_path, "rb") as f:
        st.download_button("Download ATS Resume (DOCX)", f, file_name="ATS_Resume.docx")

    with open(cover_pdf_path, "rb") as f:
        st.download_button("Download Cover Letter (PDF)", f, file_name="CoverLetter.pdf")

    with open(cover_docx_path, "rb") as f:
        st.download_button("Download Cover Letter (DOCX)", f, file_name="CoverLetter.docx")
