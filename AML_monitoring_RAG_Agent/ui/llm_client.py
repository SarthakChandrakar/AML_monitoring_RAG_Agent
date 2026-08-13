"""Optional LLM layer. The app never depends on it — absence is a normal state."""

from __future__ import annotations

import os

try:  # optional convenience only
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # noqa: BLE001
    pass

PROVIDERS = [
    ("Groq", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    ("Gemini", "GEMINI_API_KEY", "gemini-1.5-flash"),
    ("OpenAI", "OPENAI_API_KEY", "gpt-4o-mini"),
]

SYSTEM_PROMPT = (
    "You are an expert AML compliance analyst. Answer only from the supplied evidence, "
    "cite it as [E1], [E2], and state plainly when the evidence does not cover the question."
)


def available_provider() -> tuple[str, str, str] | None:
    for name, env_key, model in PROVIDERS:
        if os.getenv(env_key):
            return name, env_key, model
    return None


def generate(prompt: str) -> tuple[str | None, str]:
    """Return (answer, source_label). answer is None when no LLM is usable."""
    provider = available_provider()
    if provider is None:
        return None, "no LLM key configured"

    name, env_key, model = provider
    key = os.getenv(env_key, "")

    try:
        if name == "Groq":
            from groq import Groq

            client = Groq(api_key=key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content, f"{name} · {model}"

        if name == "Gemini":
            import google.generativeai as genai

            genai.configure(api_key=key)
            response = genai.GenerativeModel(model).generate_content(
                f"{SYSTEM_PROMPT}\n\n{prompt}"
            )
            return response.text, f"{name} · {model}"

        from openai import OpenAI

        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content, f"{name} · {model}"

    except Exception as exc:  # noqa: BLE001
        return None, f"{name} call failed — {type(exc).__name__}: {exc}"
