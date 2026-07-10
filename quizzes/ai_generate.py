"""AI-assisted quiz question generation (Claude / Anthropic Messages API).

No SDK dependency -- `requests` (already a project dependency) is enough
for a single JSON POST, so this avoids pulling in the `anthropic` package
for one call site.

Nothing here ever touches the Questions table directly: generate_questions()
only returns plain dicts. The admin always reviews/edits the draft on the
review screen before anything is saved (GenerateQuestionsView /
ReviewGeneratedQuestionsView in views.py) -- that's the one hard
requirement this module exists to serve, so don't add a "save directly"
shortcut here later without re-checking that decision.
"""
import json
import os
import re

import requests
from django.conf import settings

from .question_import import normalize_correct_option

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-5"
MAX_QUESTIONS_PER_BATCH = 25


class AIGenerationError(Exception):
    """Raised for anything that stops a usable question list from coming
    back -- missing key, network failure, or output that doesn't parse
    into the expected shape. The message is shown to the admin as-is, so
    keep it in the same plain, direct tone as question_import.py's errors."""


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    key_file = settings.BASE_DIR / ".secrets" / "anthropic_api_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return ""


def _build_prompt(topic, count):
    return f"""Generate exactly {count} multiple-choice quiz questions about: {topic}

Write in clear, professional English suitable for a general adult audience taking an online awareness quiz. Avoid slang, avoid overly technical jargon unless the topic requires it, and keep each question self-contained (no "as mentioned above" references).

Rules for every question:
- Exactly 4 answer options, all plausible, none duplicated, none identical to the question text.
- Exactly one option is correct.
- Include a 2-3 sentence explanation that both confirms why the correct option is right AND briefly notes why the other options are wrong/less accurate. This explanation is shown to the learner after they answer, whether they got it right or wrong, so it must teach the full picture, not just restate the correct option.
- Questions should vary in difficulty and cover different aspects of the topic, not near-duplicates of each other.

Return ONLY a JSON array (no markdown fences, no commentary before or after), where each element has exactly this shape:
{{"question": "...", "option_1": "...", "option_2": "...", "option_3": "...", "option_4": "...", "correct_option": 1, "explanation": "..."}}

"correct_option" must be an integer 1-4 indicating which option_N is correct. Return exactly {count} elements."""


def _extract_json_array(text):
    text = text.strip()
    # Claude sometimes wraps output in ```json ... ``` even when told not to.
    fence_match = re.search(r"```(?:json)?\s*(\[.*\])\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AIGenerationError(f"AI ne jo output diya wo valid JSON nahi tha: {e}")


def generate_questions(topic, count):
    """Returns a list of clean dicts (question, option_1..4, correct_option
    int, explanation), ready to prefill the review/edit screen. Never
    writes to the database."""
    topic = (topic or "").strip()
    if not topic:
        raise AIGenerationError("Topic khaali hai.")
    count = max(1, min(int(count), MAX_QUESTIONS_PER_BATCH))

    api_key = get_api_key()
    if not api_key:
        raise AIGenerationError(
            "ANTHROPIC_API_KEY set nahi hai server par -- pehle API key configure karo."
        )

    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": _build_prompt(topic, count)}],
            },
            timeout=90,
        )
    except requests.RequestException as e:
        raise AIGenerationError(f"Anthropic API tak pahunch nahi paaye: {e}")

    if resp.status_code != 200:
        raise AIGenerationError(
            f"Anthropic API ne error diya (HTTP {resp.status_code}): {resp.text[:300]}"
        )

    try:
        data = resp.json()
        text = data["content"][0]["text"]
    except (KeyError, IndexError, ValueError) as e:
        raise AIGenerationError(f"API response ka format samajh nahi aaya: {e}")

    parsed = _extract_json_array(text)
    if not isinstance(parsed, list) or not parsed:
        raise AIGenerationError("AI ne koi question list nahi di.")

    clean_rows = []
    for idx, row in enumerate(parsed, start=1):
        if not isinstance(row, dict):
            continue
        q_text = str(row.get("question", "")).strip()
        opts = [str(row.get(f"option_{n}", "")).strip() for n in (1, 2, 3, 4)]
        explanation = str(row.get("explanation", "")).strip()
        correct_int = normalize_correct_option(row.get("correct_option"))

        if not q_text or any(not o for o in opts) or correct_int is None:
            continue  # skip malformed entries rather than failing the whole batch

        clean_rows.append({
            "question": q_text,
            "option_1": opts[0], "option_2": opts[1], "option_3": opts[2], "option_4": opts[3],
            "correct_option": correct_int,
            "explanation": explanation,
        })

    if not clean_rows:
        raise AIGenerationError("AI ke output se ek bhi valid question nahi ban paya -- dobara try karo.")

    return clean_rows
