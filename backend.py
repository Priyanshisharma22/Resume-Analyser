from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import requests

from prompts import (
    RESUME_PROMPT,
    COVER_LETTER_PROMPT,
    MISSING_SKILLS_PROMPT,
    LINKEDIN_SUMMARY_PROMPT
)
from scorer import job_match_score
from db import (
    init_db, create_user, get_user_by_username,
    save_history, get_user_history, get_history_item,
    get_conn
)
from auth import hash_password, verify_password, create_access_token, decode_token

# ✅ Job Agent
from job_agent import fetch_jobs

OLLAMA_URL = "http://localhost:11434/api/generate"

app = FastAPI()
init_db()


# -------------------- MODELS --------------------
class RegisterReq(BaseModel):
    username: str
    email: str
    password: str


class LoginReq(BaseModel):
    username: str
    password: str


class GenReq(BaseModel):
    resume: str
    job: str
    model: str = "llama3"
    job_title: str = ""


class JobSearchReq(BaseModel):
    keyword: str
    location: str = "India"
    page: int = 1


# -------------------- HELPERS --------------------
def ollama_generate(prompt: str, model: str = "llama3") -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    r = requests.post(OLLAMA_URL, json=payload, timeout=300)

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Ollama error: {r.text}")

    out = r.json().get("response", "")
    return out.strip()


def get_current_user(authorization: str | None):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid/Expired token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# -------------------- AUTH ROUTES --------------------
@app.post("/register")
def register(req: RegisterReq):
    # Username unique check
    existing = get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Email unique check
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = ?", (req.email,))
        email_exists = cur.fetchone()
        conn.close()
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already exists")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

    try:
        pw_hash = hash_password(req.password)
        create_user(req.username, req.email, pw_hash)
        return {"message": "User registered successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Register error: {str(e)}")


@app.post("/login")
def login(req: LoginReq):
    user = get_user_by_username(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    stored_hash = user["password_hash"]

    if not verify_password(req.password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user["username"], "user_id": user["id"]})
    return {"access_token": token, "token_type": "bearer"}


# -------------------- JOB SCRAPER AGENT --------------------
@app.post("/jobs/search")
def jobs_search(req: JobSearchReq, authorization: str | None = Header(default=None)):
    _ = get_current_user(authorization)  # login required
    try:
        jobs = fetch_jobs(req.keyword, req.location, req.page)
        return {"jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job search error: {str(e)}")


# -------------------- GENERATE + HISTORY --------------------
@app.post("/generate")
def generate(req: GenReq, authorization: str | None = Header(default=None)):
    user = get_current_user(authorization)

    ats_resume = ollama_generate(
        RESUME_PROMPT.format(resume=req.resume, job=req.job),
        model=req.model
    )
    cover_letter = ollama_generate(
        COVER_LETTER_PROMPT.format(resume=ats_resume, job=req.job),
        model=req.model
    )
    missing_skills = ollama_generate(
        MISSING_SKILLS_PROMPT.format(resume=ats_resume, job=req.job),
        model=req.model
    )
    linkedin_summary = ollama_generate(
        LINKEDIN_SUMMARY_PROMPT.format(resume=ats_resume),
        model=req.model
    )

    score = job_match_score(ats_resume, req.job)

    save_history(
        user_id=user["id"],
        job_title=req.job_title,
        resume_input=req.resume,
        job_description=req.job,
        ats_resume=ats_resume,
        cover_letter=cover_letter,
        missing_skills=missing_skills,
        linkedin_summary=linkedin_summary,
        job_match_score=score,
        model=req.model
    )

    return {
        "ats_resume": ats_resume,
        "cover_letter": cover_letter,
        "missing_skills": missing_skills,
        "linkedin_summary": linkedin_summary,
        "job_match_score": score
    }


@app.get("/history")
def history(authorization: str | None = Header(default=None)):
    user = get_current_user(authorization)
    rows = get_user_history(user["id"], limit=30)
    return {"history": [dict(r) for r in rows]}


@app.get("/history/{history_id}")
def history_item(history_id: int, authorization: str | None = Header(default=None)):
    user = get_current_user(authorization)
    row = get_history_item(history_id, user["id"])
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"item": dict(row)}
