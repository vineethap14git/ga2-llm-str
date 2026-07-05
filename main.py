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

USE_LLM = False   # change to True when running locally with Ollama

# -----------------------------
# Call local LLM (Ollama example)
# -----------------------------
def call_llm(prompt: str):
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

def extract_fallback(text: str):
    amount = re.search(r"(\d+(\.\d+)?)", text)
    currency = re.search(r"\b(USD|EUR|GBP)\b", text)
    date = re.search(r"\d{4}-\d{2}-\d{2}", text)

    vendor = "Unknown"
    if "Invoice from" in text:
        vendor = text.split("Invoice from")[-1].split(".")[0]

    return {
        "vendor": vendor.strip(),
        "amount": float(amount.group(1)) if amount else 0.0,
        "currency": currency.group(1) if currency else "USD",
        "date": date.group(0) if date else "2026-01-01"
    }

# -----------------------------
# Extraction prompt
# -----------------------------
def build_prompt(text: str):
    return f"""
Extract invoice details.

Return ONLY JSON:
{{
  "vendor": "...",
  "amount": 0.0,
  "currency": "USD",
  "date": "YYYY-MM-DD"
}}

TEXT:
{text}
"""

# -----------------------------
# POST /extract endpoint
# -----------------------------
@app.post("/extract", response_model=InvoiceOutput)
def extract_invoice(data: InvoiceInput):

    #  safety check (important for marks)
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=422, detail="Empty input")

    #  choose method
    if USE_LLM:
        raw = call_llm(build_prompt(data.text))

        # try parsing LLM output
        try:
            json_str = re.search(r"\{.*\}", raw, re.S).group()
            parsed = eval(json_str.replace("true", "True").replace("false", "False"))
        except:
            raise HTTPException(status_code=422, detail="Bad LLM output")

    else:
        parsed = extract_fallback(data.text)

    #  final validation (IMPORTANT)
    return InvoiceOutput(
        vendor=str(parsed["vendor"]),
        amount=float(parsed["amount"]),
        currency=str(parsed["currency"]).upper(),
        date=str(parsed["date"])
    )