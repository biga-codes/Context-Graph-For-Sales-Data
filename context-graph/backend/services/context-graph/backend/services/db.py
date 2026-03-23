import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "context_graph.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS billing_document_headers (
            billingDocument TEXT PRIMARY KEY,
            billingDocumentType TEXT,
            creationDate TEXT,
            billingDocumentDate TEXT,
            billingDocumentIsCancelled INTEGER,
            cancelledBillingDocument TEXT,
            totalNetAmount REAL,
            transactionCurrency TEXT,
            companyCode TEXT,
            fiscalYear TEXT,
            accountingDocument TEXT,
            soldToParty TEXT
        );
        CREATE TABLE IF NOT EXISTS billing_document_items (
            billingDocument TEXT,
            billingDocumentItem TEXT,
            material TEXT,
            billingQuantity REAL,
            billingQuantityUnit TEXT,
            netAmount REAL,
            transactionCurrency TEXT,
            referenceSdDocument TEXT,
            referenceSdDocumentItem TEXT,
            PRIMARY KEY (billingDocument, billingDocumentItem)
        );
        CREATE TABLE IF NOT EXISTS billing_document_cancellations (
            billingDocument TEXT PRIMARY KEY,
            cancellationBillingDocument TEXT,
            cancellationBillingDocumentType TEXT,
            cancellationDate TEXT
        );
        CREATE TABLE IF NOT EXISTS sales_order_headers (
            salesOrder TEXT PRIMARY KEY,
            salesOrderType TEXT,
            salesOrganization TEXT,
            soldToParty TEXT,
            creationDate TEXT,
            totalNetOrderAmount REAL,
            transactionCurrency TEXT,
            overallDeliveryStatus TEXT,
            overallSDProcessStatus TEXT,
            overallBillingStatus TEXT
        );
        CREATE TABLE IF NOT EXISTS sales_order_items (
            salesOrder TEXT,
            salesOrderItem TEXT,
            material TEXT,
            requestedQuantity REAL,
            requestedQuantityUnit TEXT,
            netAmount REAL,
            deliveryStatus TEXT,
            overallSDProcessStatus TEXT,
            billingStatus TEXT,
            plant TEXT,
            storageLocation TEXT,
            PRIMARY KEY (salesOrder, salesOrderItem)
        );
        CREATE TABLE IF NOT EXISTS sales_order_schedule_lines (
            salesOrder TEXT,
            salesOrderItem TEXT,
            scheduleLine TEXT,
            requestedDeliveryDate TEXT,
            confirmedDeliveryDate TEXT,
            scheduledQuantity REAL,
            PRIMARY KEY (salesOrder, salesOrderItem, scheduleLine)
        );
        CREATE TABLE IF NOT EXISTS outbound_delivery_headers (
            deliveryDocument TEXT PRIMARY KEY,
            deliveryDocumentType TEXT,
            shippingPoint TEXT,
            deliveryDate TEXT,
            actualGoodsMovementDate TEXT,
            overallDeliveryStatus TEXT,
            soldToParty TEXT,
            shipToParty TEXT
        );
        CREATE TABLE IF NOT EXISTS outbound_delivery_items (
            deliveryDocument TEXT,
            deliveryDocumentItem TEXT,
            material TEXT,
            actualDeliveryQuantity REAL,
            deliveryQuantityUnit TEXT,
            referenceSDDocument TEXT,
            referenceSDDocumentItem TEXT,
            plant TEXT,
            storageLocation TEXT,
            PRIMARY KEY (deliveryDocument, deliveryDocumentItem)
        );
        CREATE TABLE IF NOT EXISTS journal_entry_items_accounts_receivable (
            accountingDocument TEXT,
            companyCode TEXT,
            fiscalYear TEXT,
            accountingDocumentItem TEXT,
            customer TEXT,
            amountInTransactionCurrency REAL,
            transactionCurrency TEXT,
            documentItemText TEXT,
            assignmentReference TEXT,
            PRIMARY KEY (accountingDocument, companyCode, fiscalYear, accountingDocumentItem)
        );
        CREATE TABLE IF NOT EXISTS payments_accounts_receivable (
            accountingDocument TEXT,
            companyCode TEXT,
            fiscalYear TEXT,
            customer TEXT,
            paymentAmount REAL,
            transactionCurrency TEXT,
            paymentDate TEXT,
            paymentMethod TEXT,
            clearingDocument TEXT,
            PRIMARY KEY (accountingDocument, companyCode, fiscalYear)
        );
        CREATE TABLE IF NOT EXISTS business_partners (
            businessPartner TEXT PRIMARY KEY,
            businessPartnerName TEXT,
            businessPartnerType TEXT,
            businessPartnerCategory TEXT,
            language TEXT,
            country TEXT,
            creationDate TEXT
        );
        CREATE TABLE IF NOT EXISTS business_partner_addresses (
            businessPartner TEXT,
            addressID TEXT,
            streetName TEXT,
            cityName TEXT,
            region TEXT,
            country TEXT,
            postalCode TEXT,
            PRIMARY KEY (businessPartner, addressID)
        );
        CREATE TABLE IF NOT EXISTS customer_company_assignments (
            customer TEXT,
            companyCode TEXT,
            accountGroup TEXT,
            paymentTerms TEXT,
            PRIMARY KEY (customer, companyCode)
        );
        CREATE TABLE IF NOT EXISTS customer_sales_area_assignments (
            customer TEXT,
            salesOrganization TEXT,
            distributionChannel TEXT,
            division TEXT,
            salesGroup TEXT,
            salesOffice TEXT,
            PRIMARY KEY (customer, salesOrganization, distributionChannel, division)
        );
        CREATE TABLE IF NOT EXISTS products (
            product TEXT PRIMARY KEY,
            productType TEXT,
            baseUnit TEXT,
            weightUnit TEXT,
            grossWeight REAL,
            netWeight REAL,
            creationDate TEXT
        );
        CREATE TABLE IF NOT EXISTS product_descriptions (
            product TEXT,
            language TEXT,
            productDescription TEXT,
            PRIMARY KEY (product, language)
        );
        CREATE TABLE IF NOT EXISTS product_plants (
            product TEXT,
            plant TEXT,
            profileCode TEXT,
            PRIMARY KEY (product, plant)
        );
        CREATE TABLE IF NOT EXISTS product_storage_locations (
            product TEXT,
            plant TEXT,
            storageLocation TEXT,
            PRIMARY KEY (product, plant, storageLocation)
        );
        CREATE TABLE IF NOT EXISTS plants (
            plant TEXT PRIMARY KEY,
            plantName TEXT,
            country TEXT,
            region TEXT,
            cityName TEXT
        );
    """)
    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


def execute_query(sql: str, params: tuple = ()) -> list[dict]:
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT"):
        raise ValueError("Only SELECT queries are permitted.")
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
