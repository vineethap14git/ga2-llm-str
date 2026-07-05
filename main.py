from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import re

app = FastAPI()

# -----------------------------
# Request schema
# -----------------------------
class InvoiceInput(BaseModel):
    text: str

# -----------------------------
# Response schema (IMPORTANT)
# -----------------------------
class InvoiceOutput(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str

# -----------------------------
# Call local LLM (Ollama example)
# -----------------------------
def call_llm(prompt: str) -> str:
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        return res.json()["response"]
    except Exception:
        return ""

# -----------------------------
# Extraction prompt
# -----------------------------
def build_prompt(text: str):
    return f"""
Extract invoice data from the text below.

Return ONLY valid JSON:
{{
  "vendor": "...",
  "amount": 0.0,
  "currency": "USD",
  "date": "YYYY-MM-DD"
}}

Rules:
- vendor: company name
- amount: numeric only
- currency: 3-letter uppercase code
- date: format YYYY-MM-DD

TEXT:
{text}
"""

# -----------------------------
# POST /extract endpoint
# -----------------------------
@app.post("/extract", response_model=InvoiceOutput)
def extract_invoice(data: InvoiceInput):

    # ---- Handle empty / bad input safely ----
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=422, detail="Empty invoice text")

    # ---- Call LLM ----
    prompt = build_prompt(data.text)
    raw_output = call_llm(prompt)

    if not raw_output:
        raise HTTPException(status_code=422, detail="LLM failed to respond")

    # ---- Extract JSON safely ----
    try:
        json_str = re.search(r"\{.*\}", raw_output, re.S).group()
        parsed = eval(json_str.replace("true", "True").replace("false", "False"))
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid LLM output")

    # ---- Final validation via Pydantic ----
    try:
        return InvoiceOutput(
            vendor=str(parsed["vendor"]),
            amount=float(parsed["amount"]),
            currency=str(parsed["currency"]).upper(),
            date=str(parsed["date"])
        )
    except Exception:
        raise HTTPException(status_code=422, detail="Schema validation failed")
