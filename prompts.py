RESUME_PROMPT = """
You are an expert ATS resume writer.

TASK:
Rewrite resume to match job description.

RULES:
- ATS-friendly formatting
- No tables, no icons, no images
- Strong action verbs + metrics
- Keep clean headings: Summary, Skills, Experience, Projects, Education
- Do not hallucinate fake experiences

INPUT RESUME:
{resume}

JOB DESCRIPTION:
{job}

Return ONLY the rewritten resume.
"""

COVER_LETTER_PROMPT = """
You are an expert career writer.

TASK:
Generate a professional cover letter tailored to the job.

RULES:
- 250-350 words
- 3 paragraphs
- Mention relevant skills + projects from resume
- Formal tone

ATS RESUME:
{resume}

JOB DESCRIPTION:
{job}

Return ONLY the cover letter.
"""

MISSING_SKILLS_PROMPT = """
You are a technical recruiter.

TASK:
Compare resume vs job description and list missing/weak skills.

OUTPUT FORMAT:
1) Missing Skills (bullets)
2) Suggested Keywords (bullets)
3) Best Projects to Add (bullets)

RESUME:
{resume}

JOB DESCRIPTION:
{job}
"""

LINKEDIN_SUMMARY_PROMPT = """
You are an expert LinkedIn profile writer.

TASK:
Write a LinkedIn About/Summary section.

RULES:
- 120-200 words
- Recruiter-friendly
- Mention domain + skills + achievements + career goal
- No emojis

ATS RESUME:
{resume}
"""
