import json
import csv
from datetime import datetime, date

print("Loading candidates... this will take 1-2 minutes")

# ============================================================
# STEP 1: Load all 100,000 candidates from the file
# ============================================================
candidates = []
with open("candidates.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            candidates.append(json.loads(line))

print(f"Loaded {len(candidates)} candidates. Now scoring...")

# ============================================================
# STEP 2: Define what a great candidate looks like
# ============================================================

# Job titles that are a STRONG match for Senior AI Engineer
GREAT_TITLES = [
    "ai engineer", "ml engineer", "machine learning engineer",
    "data scientist", "nlp engineer", "research engineer",
    "applied scientist", "senior engineer", "software engineer",
    "backend engineer", "full stack engineer", "deep learning engineer",
    "computer vision engineer", "senior ml", "senior ai",
    "founding engineer", "staff engineer", "principal engineer"
]

# Job titles that are a TERRIBLE match (keyword stuffers trap)
BAD_TITLES = [
    "marketing manager", "hr manager", "content writer",
    "graphic designer", "accountant", "sales executive",
    "operations manager", "business analyst", "project manager",
    "customer support", "civil engineer", "mechanical engineer",
    "recruiter", "teacher", "finance manager"
]

# Keywords that should appear in career descriptions for a REAL AI engineer
CAREER_KEYWORDS = [
    "embedding", "embeddings", "vector", "retrieval", "ranking",
    "llm", "language model", "transformer", "fine-tun", "rag",
    "faiss", "pinecone", "weaviate", "qdrant", "elasticsearch",
    "recommendation", "search", "neural", "pytorch", "tensorflow",
    "huggingface", "bert", "gpt", "inference", "model", "nlp",
    "machine learning", "deep learning", "python", "production",
    "deployed", "pipeline", "a/b test", "evaluation", "benchmark"
]

# India locations that match the job (Pune/Noida preferred)
TOP_LOCATIONS = ["pune", "noida", "delhi", "ncr", "hyderabad", "mumbai", "bangalore", "bengaluru", "gurgaon", "gurugram"]
OK_LOCATIONS = ["india", "chennai", "kolkata", "ahmedabad", "jaipur"]

# ============================================================
# STEP 3: Scoring function — scores each candidate 0.0 to 1.0
# ============================================================

def score_candidate(c):
    total_score = 0.0

    # --- Get basic info about the candidate ---
    profile = c.get("profile", {})
    current_title = profile.get("current_title", "").lower()
    years_exp = profile.get("years_of_experience", 0)
    location = profile.get("location", "").lower()
    country = profile.get("country", "").lower()
    career_history = c.get("career_history", [])
    skills = c.get("skills", [])
    signals = c.get("redrob_signals", {})

    # -----------------------------------------------
    # A. JOB TITLE SCORE (40 points max)
    # This is the most important signal.
    # A marketing manager listing AI skills is a trap!
    # -----------------------------------------------
    title_score = 0

    # Check if current title is a TERRIBLE match — penalize heavily
    is_bad_title = any(bad in current_title for bad in BAD_TITLES)
    if is_bad_title:
        title_score = 0  # Zero score for wrong-role candidates

    # Check career history titles — did they EVER work as an AI/ML engineer?
    else:
        career_titles = [job.get("title", "").lower() for job in career_history]
        all_titles = [current_title] + career_titles

        great_match = any(
            any(great in title for great in GREAT_TITLES)
            for title in all_titles
        )
        if great_match:
            title_score = 40
        else:
            title_score = 10  # Has some engineering background but not ideal

    total_score += title_score

    # -----------------------------------------------
    # B. CAREER HISTORY SCORE (25 points max)
    # Did they actually DO AI/ML work in their jobs?
    # -----------------------------------------------
    career_score = 0
    all_descriptions = " ".join([
        job.get("description", "") for job in career_history
    ]).lower()

    # Count how many relevant keywords appear in their work descriptions
    keyword_hits = sum(1 for kw in CAREER_KEYWORDS if kw in all_descriptions)

    # More keyword hits = more relevant actual experience
    if keyword_hits >= 10:
        career_score = 25
    elif keyword_hits >= 6:
        career_score = 18
    elif keyword_hits >= 3:
        career_score = 10
    elif keyword_hits >= 1:
        career_score = 5
    else:
        career_score = 0

    total_score += career_score

    # -----------------------------------------------
    # C. EXPERIENCE YEARS SCORE (15 points max)
    # Job wants 5-9 years. Outside that range = less points.
    # -----------------------------------------------
    exp_score = 0
    if 5 <= years_exp <= 9:
        exp_score = 15        # Perfect range
    elif 4 <= years_exp <= 11:
        exp_score = 10        # Close enough
    elif 3 <= years_exp <= 13:
        exp_score = 6         # Acceptable
    else:
        exp_score = 2         # Too junior or too senior

    total_score += exp_score

    # -----------------------------------------------
    # D. LOCATION SCORE (10 points max)
    # Job is in Pune/Noida, India. Indian candidates preferred.
    # -----------------------------------------------
    location_score = 0
    willing_to_relocate = signals.get("willing_to_relocate", False)

    if any(loc in location for loc in TOP_LOCATIONS) or "india" in country:
        location_score = 10
    elif willing_to_relocate:
        location_score = 6
    else:
        location_score = 2

    total_score += location_score

    # -----------------------------------------------
    # E. BEHAVIORAL SIGNALS SCORE (10 points max)
    # Is this person actually available and responsive?
    # A perfect-on-paper candidate who never replies is useless.
    # -----------------------------------------------
    signal_score = 0

    response_rate = signals.get("recruiter_response_rate", 0)
    open_to_work = signals.get("open_to_work_flag", False)
    notice_days = signals.get("notice_period_days", 90)
    github_score = signals.get("github_activity_score", -1)
    interview_rate = signals.get("interview_completion_rate", 0)

    # Response rate — most important behavioral signal
    if response_rate >= 0.6:
        signal_score += 4
    elif response_rate >= 0.3:
        signal_score += 2
    else:
        signal_score += 0

    # Open to work flag
    if open_to_work:
        signal_score += 2

    # Notice period — shorter is better for a startup
    if notice_days <= 30:
        signal_score += 2
    elif notice_days <= 60:
        signal_score += 1

    # GitHub activity (AI engineers should have this)
    if github_score >= 50:
        signal_score += 2
    elif github_score >= 20:
        signal_score += 1

    total_score += min(signal_score, 10)  # Cap at 10

    # -----------------------------------------------
    # Convert to 0.0 - 1.0 scale (total was out of 100)
    # -----------------------------------------------
    final_score = round(total_score / 100.0, 4)
    return final_score


# ============================================================
# STEP 4: Score every candidate
# ============================================================
print("Scoring all candidates...")
scored = []
for c in candidates:
    s = score_candidate(c)
    scored.append((s, c))

# Sort by score — highest first
scored.sort(key=lambda x: x[0], reverse=True)

# Take only top 100
top100 = scored[:100]
print(f"Top 100 selected. Writing CSV...")

# ============================================================
# STEP 5: Write the submission CSV
# ============================================================

def make_reasoning(c, score):
    """Write a 1-2 sentence explanation for why this candidate was chosen."""
    profile = c.get("profile", {})
    title = profile.get("current_title", "Unknown")
    years = profile.get("years_of_experience", 0)
    location = profile.get("location", "Unknown")
    signals = c.get("redrob_signals", {})
    response_rate = signals.get("recruiter_response_rate", 0)
    career_history = c.get("career_history", [])

    all_descriptions = " ".join([
        job.get("description", "") for job in career_history
    ]).lower()

    keyword_hits = sum(1 for kw in CAREER_KEYWORDS if kw in all_descriptions)

    reasoning = (
        f"{title} with {years} yrs experience in {location}; "
        f"{keyword_hits} AI/ML career signals; "
        f"response rate {response_rate:.2f}."
    )
    return reasoning


with open("submission.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["candidate_id", "rank", "score", "reasoning"])

    for rank, (score, candidate) in enumerate(top100, start=1):
        cid = candidate["candidate_id"]
        reasoning = make_reasoning(candidate, score)
        writer.writerow([cid, rank, f"{score:.4f}", reasoning])

print("")
print("SUCCESS! submission.csv has been created in your C:\\ai-ranker folder.")
print("Now run: python validate_submission.py submission.csv")
