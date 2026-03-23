"""
ingest.py — Loads all JSONL folders into SQLite.

Usage:
    python -m services.ingest --data-dir /path/to/dataset/root

The dataset root should contain folders like:
    billing_document_headers/
    billing_document_items/
    sales_order_headers/
    ... etc.

Each folder can contain multiple .jsonl part files.
"""

import json
import os
import argparse
from pathlib import Path
from services.db import get_connection, init_db

# Maps folder name → (table_name, [columns_to_extract])
# Only columns listed here are inserted; extras are silently ignored.
# Add/remove columns to match what actually appears in your files.

TABLE_CONFIG = {
    "billing_document_headers": {
        "table": "billing_document_headers",
        "pk": "billingDocument",
        "columns": [
            "billingDocument", "billingDocumentType", "creationDate",
            "billingDocumentDate", "billingDocumentIsCancelled",
            "cancelledBillingDocument", "totalNetAmount", "transactionCurrency",
            "companyCode", "fiscalYear", "accountingDocument", "soldToParty",
        ],
    },
    "billing_document_items": {
        "table": "billing_document_items",
        "pk": None,
        "columns": [
            "billingDocument", "billingDocumentItem", "material",
            "billingQuantity", "billingQuantityUnit", "netAmount",
            "transactionCurrency", "referenceSdDocument", "referenceSdDocumentItem",
        ],
    },
    "billing_document_cancellations": {
        "table": "billing_document_cancellations",
        "pk": "billingDocument",
        "columns": [
            "billingDocument", "cancellationBillingDocument",
            "cancellationBillingDocumentType", "cancellationDate",
        ],
    },
    "sales_order_headers": {
        "table": "sales_order_headers",
        "pk": "salesOrder",
        "columns": [
            "salesOrder", "salesOrderType", "salesOrganization", "soldToParty",
            "creationDate", "totalNetOrderAmount", "transactionCurrency",
            "overallDeliveryStatus", "overallSDProcessStatus", "overallBillingStatus",
        ],
    },
    "sales_order_items": {
        "table": "sales_order_items",
        "pk": None,
        "columns": [
            "salesOrder", "salesOrderItem", "material",
            "requestedQuantity", "requestedQuantityUnit", "netAmount",
            "deliveryStatus", "overallSDProcessStatus", "billingStatus",
            "plant", "storageLocation",
        ],
    },
    "sales_order_schedule_lines": {
        "table": "sales_order_schedule_lines",
        "pk": None,
        "columns": [
            "salesOrder", "salesOrderItem", "scheduleLine",
            "requestedDeliveryDate", "confirmedDeliveryDate", "scheduledQuantity",
        ],
    },
    "outbound_delivery_headers": {
        "table": "outbound_delivery_headers",
        "pk": "deliveryDocument",
        "columns": [
            "deliveryDocument", "deliveryDocumentType", "shippingPoint",
            "deliveryDate", "actualGoodsMovementDate", "overallDeliveryStatus",
            "soldToParty", "shipToParty",
        ],
    },
    "outbound_delivery_items": {
        "table": "outbound_delivery_items",
        "pk": None,
        "columns": [
            "deliveryDocument", "deliveryDocumentItem", "material",
            "actualDeliveryQuantity", "deliveryQuantityUnit",
            "referenceSDDocument", "referenceSDDocumentItem",
            "plant", "storageLocation",
        ],
    },
    "journal_entry_items_accounts_receivable": {
        "table": "journal_entry_items_accounts_receivable",
        "pk": None,
        "columns": [
            "accountingDocument", "companyCode", "fiscalYear",
            "accountingDocumentItem", "customer",
            "amountInTransactionCurrency", "transactionCurrency",
            "documentItemText", "assignmentReference",
        ],
    },
    "payments_accounts_receivable": {
        "table": "payments_accounts_receivable",
        "pk": None,
        "columns": [
            "accountingDocument", "companyCode", "fiscalYear", "customer",
            "paymentAmount", "transactionCurrency",
            "paymentDate", "paymentMethod", "clearingDocument",
        ],
    },
    "business_partners": {
        "table": "business_partners",
        "pk": "businessPartner",
        "columns": [
            "businessPartner", "businessPartnerName", "businessPartnerType",
            "businessPartnerCategory", "language", "country", "creationDate",
        ],
    },
    "business_partner_addresses": {
        "table": "business_partner_addresses",
        "pk": None,
        "columns": [
            "businessPartner", "addressID", "streetName", "cityName",
            "region", "country", "postalCode",
        ],
    },
    "customer_company_assignments": {
        "table": "customer_company_assignments",
        "pk": None,
        "columns": ["customer", "companyCode", "accountGroup", "paymentTerms"],
    },
    "customer_sales_area_assignments": {
        "table": "customer_sales_area_assignments",
        "pk": None,
        "columns": [
            "customer", "salesOrganization", "distributionChannel",
            "division", "salesGroup", "salesOffice",
        ],
    },
    "products": {
        "table": "products",
        "pk": "product",
        "columns": [
            "product", "productType", "baseUnit", "weightUnit",
            "grossWeight", "netWeight", "creationDate",
        ],
    },
    "product_descriptions": {
        "table": "product_descriptions",
        "pk": None,
        "columns": ["product", "language", "productDescription"],
    },
    "product_plants": {
        "table": "product_plants",
        "pk": None,
        "columns": ["product", "plant", "profileCode"],
    },
    "product_storage_locations": {
        "table": "product_storage_locations",
        "pk": None,
        "columns": ["product", "plant", "storageLocation"],
    },
    "plants": {
        "table": "plants",
        "pk": "plant",
        "columns": ["plant", "plantName", "country", "region", "cityName"],
    },
}


def flatten(obj, prefix=""):
    """Flatten one level of nested dicts (e.g. creationTime: {hours, minutes})."""
    result = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                result[f"{prefix}{k}_{sk}"] = sv
        else:
            result[f"{prefix}{k}"] = v
    return result


def load_folder(conn, folder_path: Path, config: dict):
    table = config["table"]
    columns = config["columns"]
    placeholders = ", ".join("?" for _ in columns)
    cols_str = ", ".join(f'"{c}"' for c in columns)
    sql = f'INSERT OR IGNORE INTO {table} ({cols_str}) VALUES ({placeholders})'

    jsonl_files = sorted(folder_path.glob("*.jsonl"))
    if not jsonl_files:
        print(f"  [SKIP] No .jsonl files in {folder_path.name}")
        return

    total = 0
    for jf in jsonl_files:
        count = 0
        with open(jf, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    row = flatten(raw)
                    values = [row.get(c, None) for c in columns]
                    conn.execute(sql, values)
                    count += 1
                except Exception as e:
                    print(f"  [WARN] {jf.name}: {e}")
        total += count

    conn.commit()
    print(f"  [OK] {table}: {total} rows")


def ingest(data_dir: str):
    init_db()
    conn = get_connection()
    root = Path(data_dir)

    if not root.exists():
        print(f"[ERROR] Data directory not found: {root}")
        return

    print(f"[INGEST] Loading from {root}\n")
    for folder_name, config in TABLE_CONFIG.items():
        folder_path = root / folder_name
        if not folder_path.exists():
            print(f"  [SKIP] Folder not found: {folder_name}")
            continue
        load_folder(conn, folder_path, config)

    conn.close()
    print("\n[DONE] Ingestion complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="Root folder containing entity subfolders")
    args = parser.parse_args()
    ingest(args.data_dir)
