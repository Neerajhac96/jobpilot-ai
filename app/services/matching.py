import re


def normalize(text: str | None) -> str:
    if not text:
        return ""

    text = text.lower()

    # Replace punctuation with spaces
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)

    # Remove duplicate whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def text_contains(candidate_text: str, target: str) -> bool:
    candidate = normalize(candidate_text)
    target = normalize(target)

    if not candidate or not target:
        return False

    return target in candidate


def calculate_skill_match(
    candidate_skills: str | None,
    required_skills: list[str]
) -> dict:

    candidate_text = normalize(candidate_skills)

    matched = []
    missing = []

    for skill in required_skills:
        skill_normalized = normalize(skill)

        if skill_normalized and skill_normalized in candidate_text:
            matched.append(skill)
        else:
            missing.append(skill)

    total = len(required_skills)

    if total == 0:
        score = 100
    else:
        score = round((len(matched) / total) * 100)

    return {
        "score": score,
        "matched": matched,
        "missing": missing
    }


def calculate_role_match(
    preferred_roles: str | None,
    job_title: str
) -> int:

    if not preferred_roles:
        return 0

    job_title_normalized = normalize(job_title)

    roles = [
        role.strip()
        for role in preferred_roles.split(",")
        if role.strip()
    ]

    for role in roles:
        if normalize(role) in job_title_normalized:
            return 100

    # Partial role matching
    job_words = set(job_title_normalized.split())

    for role in roles:
        role_words = set(normalize(role).split())

        if role_words and role_words.intersection(job_words):
            return 60

    return 0


def calculate_location_match(
    preferred_locations: str | None,
    job_location: str | None
) -> int:

    if not preferred_locations or not job_location:
        return 0

    job_location_normalized = normalize(job_location)

    locations = [
        location.strip()
        for location in preferred_locations.split(",")
        if location.strip()
    ]

    for location in locations:
        if normalize(location) in job_location_normalized:
            return 100

    if "remote" in job_location_normalized:
        return 100 if "remote" in normalize(preferred_locations) else 50

    return 0


def calculate_experience_match(
    candidate_experience: str | None,
    job_experience: str | None
) -> int:

    if not job_experience:
        return 100

    if not candidate_experience:
        return 0

    candidate = normalize(candidate_experience)
    required = normalize(job_experience)

    # Basic fresher / junior handling for our first version
    if (
        ("fresher" in candidate or "0-2" in candidate)
        and
        ("0-2" in required or "0 2" in required)
    ):
        return 100

    if "0-1" in required and (
        "fresher" in candidate
        or "0-2" in candidate
    ):
        return 100

    if "1-2" in required and "0-2" in candidate:
        return 90

    if "0" in required and (
        "fresher" in candidate
        or "0-2" in candidate
    ):
        return 100

    return 50


def calculate_match(
    candidate,
    job_analysis: dict,
    job_title: str,
    job_location: str | None
) -> dict:

    skill_result = calculate_skill_match(
        candidate.skills,
        job_analysis.get("required_skills", [])
    )

    role_score = calculate_role_match(
        candidate.preferred_roles,
        job_title
    )

    location_score = calculate_location_match(
        candidate.preferred_locations,
        job_location
    )

    experience_score = calculate_experience_match(
        candidate.experience,
        job_analysis.get("experience_required")
    )

    # Initial education score
    education_score = 100

    if job_analysis.get("education_required"):
        education_score = 70

        if candidate.education:
            education_score = 100

    final_score = round(
        skill_result["score"] * 0.40
        + experience_score * 0.20
        + role_score * 0.15
        + location_score * 0.10
        + education_score * 0.10
        + 100 * 0.05
    )

    if final_score >= 80:
        recommendation = "APPLY"
    elif final_score >= 60:
        recommendation = "REVIEW"
    else:
        recommendation = "SKIP"

    return {
        "match_score": final_score,
        "recommendation": recommendation,
        "skills": skill_result,
        "experience_score": experience_score,
        "role_score": role_score,
        "location_score": location_score,
        "education_score": education_score
    }
