
import os
import json
import re
import requests
from services.db import execute_query

_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()

_API_KEY = os.getenv("GEMINI_API_KEY")
_MODEL_CANDIDATES = [
    os.getenv("GEMINI_MODEL", "").strip(),
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]
_model = None



def _get_model():
    global _model
    if _model is not None:
        return _model

    try:
        import google.generativeai as genai  # pyright: ignore[reportMissingImports]
        from google.api_core.exceptions import GoogleAPICallError, NotFound
    except Exception:
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    genai.configure(api_key=api_key)
    tried = set()
    candidates = [m for m in _MODEL_CANDIDATES if m]

    # Prefer models that are explicitly listed for this key/project.
    available = set()
    try:
        for m in genai.list_models():
            name = m.name.replace("models/", "")
            if "generateContent" in getattr(m, "supported_generation_methods", []):
                available.add(name)
    except Exception:
        available = set()

    ordered = []
    if available:
        ordered.extend([m for m in candidates if m.replace("models/", "") in available])
    ordered.extend(candidates)

    for model_name in ordered:
        normalized = model_name.replace("models/", "")
        if not normalized or normalized in tried:
            continue
        tried.add(normalized)
        try:
            _model = genai.GenerativeModel(normalized)
            return _model
        except NotFound:
            continue
        except GoogleAPICallError:
            continue
        except Exception:
            continue

    return None


def _llm_generate(system_prompt: str, user_prompt: str) -> str:
    if _LLM_PROVIDER == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("LLM is unavailable. Set GROQ_API_KEY in backend/.env.")

        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip() or "llama-3.1-8b-instant"
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return (payload["choices"][0]["message"]["content"] or "").strip()

    model = _get_model()
    if model is None:
        raise RuntimeError("LLM is unavailable. Check GEMINI_API_KEY and GEMINI_MODEL in backend/.env.")

    response = model.generate_content(
        [{"role": "user", "parts": [system_prompt + "\n\n" + user_prompt]}]
    )
    return (response.text or "").strip()

# ── Schema context injected into every system prompt ─────────────────────────
SCHEMA_DESCRIPTION = """
You have access to a SQLite database with the following tables:

billing_document_headers (billingDocument, billingDocumentType, creationDate, billingDocumentDate,
    billingDocumentIsCancelled, cancelledBillingDocument, totalNetAmount, transactionCurrency,
    companyCode, fiscalYear, accountingDocument, soldToParty)
billing_document_items (billingDocument, billingDocumentItem, material, billingQuantity,
    billingQuantityUnit, netAmount, transactionCurrency, referenceSdDocument, referenceSdDocumentItem)
sales_order_headers (salesOrder, salesOrderType, salesOrganization, distributionChannel,
    organizationDivision, soldToParty, creationDate, totalNetAmount, transactionCurrency,
    overallDeliveryStatus, overallOrdReltdBillgStatus)
sales_order_items (salesOrder, salesOrderItem, material, requestedQuantity, requestedQuantityUnit,
    netAmount, productionPlant, storageLocation)
outbound_delivery_headers (deliveryDocument, shippingPoint, creationDate, actualGoodsMovementDate,
    overallGoodsMovementStatus, overallPickingStatus)
outbound_delivery_items (deliveryDocument, deliveryDocumentItem, material, actualDeliveryQuantity,
    deliveryQuantityUnit, referenceSdDocument, referenceSdDocumentItem, plant, storageLocation)
journal_entry_items_accounts_receivable (accountingDocument, companyCode, fiscalYear,
    accountingDocumentItem, customer, amountInTransactionCurrency, transactionCurrency,
    referenceDocument, clearingDate, clearingAccountingDocument)
payments_accounts_receivable (accountingDocument, companyCode, fiscalYear, accountingDocumentItem,
    customer, amountInTransactionCurrency, transactionCurrency, postingDate, documentDate,
    clearingDate, clearingAccountingDocument, referenceDocument)
business_partners (businessPartner, customer, businessPartnerName, businessPartnerFullName,
    businessPartnerCategory, creationDate, lastChangeDate)
products (product, productType, baseUnit, weightUnit, grossWeight, netWeight, creationDate)
product_descriptions (product, language, productDescription)
product_plants (product, plant, mrpType, profitCenter)
plants (plant, plantName, salesOrganization, distributionChannel, division)

Relationships:
- sales_order_headers.salesOrder = sales_order_items.salesOrder
- outbound_delivery_items.referenceSdDocument = sales_order_headers.salesOrder
- outbound_delivery_items.deliveryDocument = outbound_delivery_headers.deliveryDocument
- billing_document_items.referenceSdDocument = outbound_delivery_headers.deliveryDocument
- billing_document_items.billingDocument = billing_document_headers.billingDocument
- billing_document_headers.accountingDocument + companyCode can link to journal entries on same fields
- journal_entry_items_accounts_receivable.accountingDocument + companyCode can link to payments_accounts_receivable
- sales_order_headers.soldToParty and billing_document_headers.soldToParty can map to business_partners.businessPartner/customer
- *_items.material can join to products.product

Important: column names are case-sensitive as written above (for example: referenceSdDocument).
"""

SYSTEM_PROMPT = f"""
You are a data assistant for a business operations dataset. You ONLY answer questions
about the data in the database described below. You do NOT answer general knowledge
questions, creative requests, or anything unrelated to this dataset.

{SCHEMA_DESCRIPTION}

Your job:
1. Determine if the user's question is relevant to the dataset.
2. If NOT relevant, respond with exactly:
   {{"relevant": false, "message": "This system is designed to answer questions related to the provided dataset only."}}
3. If relevant, generate a valid SQLite SELECT query and respond with:
   {{"relevant": true, "sql": "<your SQL here>", "explanation": "<one sentence describing what the query does>"}}

Rules:
- Only generate SELECT statements. Never INSERT, UPDATE, DELETE, or DROP.
- Use only the tables listed in this schema.
- Use JOINs where necessary.
- Limit results to 100 rows unless the user asks for more.
- Return ONLY valid JSON. No markdown, no code fences, no extra text.
"""

ANSWER_PROMPT = """
Given this question: "{question}"
And these query results (JSON): {results}

Write a clear, concise, data-backed answer in 2–4 sentences.
Reference specific numbers or entities from the results.
Do not mention SQL or database internals.
"""


def classify_and_generate_sql(user_query: str) -> dict:
    """Ask configured LLM to classify query and produce SQL if relevant."""

    try:
        raw = _llm_generate(SYSTEM_PROMPT, "User question: " + user_query)
    except Exception as e:
        return {
            "relevant": False,
            "message": f"LLM request failed: {e}",
        }

    # Strip markdown fences if Gemini wraps output anyway
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"relevant": False, "message": "Could not parse model response. Please rephrase your question."}


def generate_answer(question: str, results: list[dict]) -> str:
    """Ask configured LLM to formulate a natural-language answer from query results."""

    prompt = ANSWER_PROMPT.format(
        question=question,
        results=json.dumps(results[:50], default=str),  # cap at 50 rows for context
    )
    try:
        return _llm_generate(
            "You are a business data analyst assistant. Follow the user instruction exactly.",
            prompt,
        )
    except Exception as e:
        return f"LLM answer generation failed: {e}"


def query_pipeline(user_query: str) -> dict:
    """
    Full pipeline:
    1. Classify + generate SQL
    2. Execute SQL
    3. Generate natural-language answer
    Returns a dict with keys: answer, sql, rows, relevant
    """
    classification = classify_and_generate_sql(user_query)

    if not classification.get("relevant", False):
        return {
            "relevant": False,
            "answer": classification.get("message", "Out of scope."),
            "sql": None,
            "rows": [],
        }

    sql = classification["sql"]

    try:
        rows = execute_query(sql)
    except ValueError as e:
        return {"relevant": True, "answer": str(e), "sql": sql, "rows": []}
    except Exception as e:
        return {
            "relevant": True,
            "answer": f"Query execution error: {e}",
            "sql": sql,
            "rows": [],
        }

    if not rows:
        answer = "The query returned no results for your question."
    else:
        answer = generate_answer(user_query, rows)

    return {
        "relevant": True,
        "answer": answer,
        "sql": sql,
        "rows": rows[:100],
    }
