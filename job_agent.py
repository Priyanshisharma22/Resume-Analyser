import os
import requests
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "jsearch.p.rapidapi.com"


@lru_cache(maxsize=50)
def fetch_jobs(keyword: str, location: str = "India", page: int = 1):
    if not RAPIDAPI_KEY:
        raise RuntimeError("RAPIDAPI_KEY missing. Add it in .env")

    url = "https://jsearch.p.rapidapi.com/search"
    params = {
        "query": f"{keyword} in {location}",
        "page": str(page),
        "num_pages": "1",
        "country": "in",
    }

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    r = requests.get(url, headers=headers, params=params, timeout=60)

    # ✅ Debug prints
    print("STATUS:", r.status_code)
    print("BODY:", r.text[:500])

    r.raise_for_status()

    jobs = r.json().get("data", [])
    results = []
    for j in jobs:
        results.append({
            "job_id": j.get("job_id"),
            "title": j.get("job_title"),
            "company": j.get("employer_name"),
            "location": j.get("job_city") or j.get("job_country"),
            "employment_type": j.get("job_employment_type"),
            "apply_link": j.get("job_apply_link"),
            "publisher": j.get("job_publisher"),
            "snippet": (j.get("job_description") or "")[:700],
        })

    return results
