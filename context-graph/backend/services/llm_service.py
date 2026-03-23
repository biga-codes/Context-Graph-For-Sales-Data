"""
llm_service.py — Gemini NL→SQL pipeline for the SAP dataset.
"""

import os
import json
import re
import google.generativeai as genai
from services.db import execute_query

genai.configure(api_key=os.environ["AIzaSyCEAcDTtlE0QB_aWj2omGHZ-Gw6d4G0fmE"])
_model = genai.GenerativeModel("gemini-1.5-flash")

SCHEMA_DESCRIPTION = """
SQLite database with the following tables (SAP-style business data):

billing_document_headers
  billingDocument (PK), billingDocumentType, creationDate, billingDocumentDate,
  billingDocumentIsCancelled, cancelledBillingDocument, totalNetAmount,
  transactionCurrency, companyCode, fiscalYear, accountingDocument, soldToParty

billing_document_items
  billingDocument, billingDocumentItem, material, billingQuantity,
  billingQuantityUnit, netAmount, transactionCurrency,
  referenceSdDocument (→ sales_order_headers.salesOrder),
  referenceSdDocumentItem

billing_document_cancellations
  billingDocument (PK), cancellationBillingDocument,
  cancellationBillingDocumentType, cancellationDate

sales_order_headers
  salesOrder (PK), salesOrderType, salesOrganization, soldToParty,
  creationDate, totalNetOrderAmount, transactionCurrency,
  overallDeliveryStatus, overallSDProcessStatus, overallBillingStatus

sales_order_items
  salesOrder, salesOrderItem, material, requestedQuantity,
  requestedQuantityUnit, netAmount, deliveryStatus,
  overallSDProcessStatus, billingStatus, plant, storageLocation

sales_order_schedule_lines
  salesOrder, salesOrderItem, scheduleLine,
  requestedDeliveryDate, confirmedDeliveryDate, scheduledQuantity

outbound_delivery_headers
  deliveryDocument (PK), deliveryDocumentType, shippingPoint, deliveryDate,
  actualGoodsMovementDate, overallDeliveryStatus, soldToParty, shipToParty

outbound_delivery_items
  deliveryDocument, deliveryDocumentItem, material, actualDeliveryQuantity,
  deliveryQuantityUnit, referenceSDDocument (→ sales_order_headers.salesOrder),
  referenceSDDocumentItem, plant, storageLocation

journal_entry_items_accounts_receivable
  accountingDocument, companyCode, fiscalYear, accountingDocumentItem,
  customer, amountInTransactionCurrency, transactionCurrency,
  documentItemText, assignmentReference

payments_accounts_receivable
  accountingDocument, companyCode, fiscalYear, customer,
  paymentAmount, transactionCurrency, paymentDate, paymentMethod,
  clearingDocument

business_partners
  businessPartner (PK), businessPartnerName, businessPartnerType,
  businessPartnerCategory, language, country, creationDate

business_partner_addresses
  businessPartner, addressID, streetName, cityName, region, country, postalCode

customer_company_assignments
  customer, companyCode, accountGroup, paymentTerms

customer_sales_area_assignments
  customer, salesOrganization, distributionChannel, division, salesGroup, salesOffice

products
  product (PK), productType, baseUnit, weightUnit, grossWeight, netWeight, creationDate

product_descriptions
  product, language, productDescription

product_plants
  product, plant, profileCode

product_storage_locations
  product, plant, storageLocation

plants
  plant (PK), plantName, country, region, cityName

Key relationships:
- billing_document_items.referenceSdDocument → sales_order_headers.salesOrder
- outbound_delivery_items.referenceSDDocument → sales_order_headers.salesOrder
- billing_document_headers.accountingDocument → journal_entry_items_accounts_receivable.accountingDocument
- billing_document_headers.soldToParty → business_partners.businessPartner
- sales_order_headers.soldToParty → business_partners.businessPartner
- billing_document_items.material / sales_order_items.material → products.product
"""

SYSTEM_PROMPT = f"""
You are a data assistant for a SAP-style business operations dataset.
You ONLY answer questions about the data in the database described below.
You do NOT answer general knowledge questions, creative requests, or anything
unrelated to this dataset.

{SCHEMA_DESCRIPTION}

Your job:
1. Determine if the user's question is relevant to this dataset.
2. If NOT relevant, respond with exactly:
   {{"relevant": false, "message": "This system is designed to answer questions related to the provided dataset only."}}
3. If relevant, generate a valid SQLite SELECT query:
   {{"relevant": true, "sql": "<your SQL here>", "explanation": "<one sentence>"}}

Rules:
- Only SELECT statements. Never INSERT, UPDATE, DELETE, DROP.
- Use proper JOINs. Column names are case-sensitive — use exact names from the schema.
- Limit to 100 rows unless user asks for more.
- For "trace the flow" queries, JOIN across:
  sales_order_headers → billing_document_items (on salesOrder = referenceSdDocument)
  → billing_document_headers → journal_entry_items_accounts_receivable (on accountingDocument)
  → payments_accounts_receivable (on accountingDocument)
  Also join outbound_delivery_items (on referenceSDDocument = salesOrder)
- Return ONLY valid JSON. No markdown, no code fences, no extra text.
"""

ANSWER_PROMPT = """
Question: "{question}"
Query results (JSON, up to 50 rows): {results}

Write a clear, concise, data-backed answer in 2-4 sentences.
Reference specific numbers, IDs, or entity names from the results.
Do not mention SQL, tables, or database internals.
"""


def classify_and_generate_sql(user_query: str) -> dict:
    response = _model.generate_content(
        [{"role": "user", "parts": [SYSTEM_PROMPT + "\n\nUser question: " + user_query]}]
    )
    raw = response.text.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"relevant": False, "message": "Could not parse model response. Please rephrase your question."}


def generate_answer(question: str, results: list[dict]) -> str:
    prompt = ANSWER_PROMPT.format(
        question=question,
        results=json.dumps(results[:50], default=str),
    )
    response = _model.generate_content(prompt)
    return response.text.strip()


def query_pipeline(user_query: str) -> dict:
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
        return {"relevant": True, "answer": f"Query execution error: {e}", "sql": sql, "rows": []}

    if not rows:
        answer = "The query returned no results for your question."
    else:
        answer = generate_answer(user_query, rows)

    return {"relevant": True, "answer": answer, "sql": sql, "rows": rows[:100]}
