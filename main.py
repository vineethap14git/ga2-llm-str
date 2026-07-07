from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import re
from datetime import datetime

app = FastAPI()

class ExtractRequest(BaseModel):
    text: str

class ExtractResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str

def parse_invoice_text(text: str):

    prompt = f"""
Extract the following fields from this invoice.

Return ONLY valid JSON.

Schema:

{{
    "vendor": "",
    "amount": 0,
    "currency": "",
    "date": ""
}}

Rules:

- vendor = company/vendor name
- amount = total amount due as a number
- currency = 3-letter uppercase currency code
- date = payment due date in YYYY-MM-DD format

Invoice:

{text}
"""

    response = chat(
        model="llama3.2:3b",
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ]
    )

    return json.loads(response.message.content)


@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    try:
        result = parse_invoice_text(req.text)
        return ExtractResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid input")