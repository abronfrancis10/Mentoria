import json
import re
import ollama

def generate_questions_with_answers(role, resume_text, count=15):
    prompt = f"""
You are a professional technical interviewer.

Role: {role}
Candidate Resume:
{resume_text}

Generate {count} interview questions with optimal answers.

Return ONLY valid JSON:
[
  {{
    "question": "string",
    "optimal_answer": "string"
  }}
]

Rules:
- No markdown
- No bullet points
- No newlines inside values
"""

    response = ollama.chat(
        model="mistral",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response["message"]["content"]

    match = re.search(r"\[\s*{.*?}\s*\]", raw, re.S)
    if not match:
        raise ValueError("Invalid LLM output")

    return json.loads(match.group())
