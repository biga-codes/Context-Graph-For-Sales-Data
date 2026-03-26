import sqlite3
import os
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "context_graph.db"
DB_PATH = Path(os.getenv("CONTEXT_GRAPH_DB_PATH", str(DEFAULT_DB_PATH)))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(force_recreate: bool = False):
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()
    if force_recreate:
        cursor.executescript("""
            DROP TABLE IF EXISTS billing_document_headers;
            DROP TABLE IF EXISTS billing_document_items;
            DROP TABLE IF EXISTS billing_document_cancellations;
            DROP TABLE IF EXISTS sales_order_headers;
            DROP TABLE IF EXISTS sales_order_items;
            DROP TABLE IF EXISTS sales_order_schedule_lines;
            DROP TABLE IF EXISTS outbound_delivery_headers;
            DROP TABLE IF EXISTS outbound_delivery_items;
            DROP TABLE IF EXISTS journal_entry_items_accounts_receivable;
            DROP TABLE IF EXISTS payments_accounts_receivable;
            DROP TABLE IF EXISTS business_partners;
            DROP TABLE IF EXISTS business_partner_addresses;
            DROP TABLE IF EXISTS customer_company_assignments;
            DROP TABLE IF EXISTS customer_sales_area_assignments;
            DROP TABLE IF EXISTS products;
            DROP TABLE IF EXISTS product_descriptions;
            DROP TABLE IF EXISTS product_plants;
            DROP TABLE IF EXISTS product_storage_locations;
            DROP TABLE IF EXISTS plants;
            DROP TABLE IF EXISTS customers;
            DROP TABLE IF EXISTS addresses;
            DROP TABLE IF EXISTS orders;
            DROP TABLE IF EXISTS order_items;
            DROP TABLE IF EXISTS deliveries;
            DROP TABLE IF EXISTS invoices;
            DROP TABLE IF EXISTS payments;
        """)
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
            distributionChannel TEXT,
            organizationDivision TEXT,
            salesGroup TEXT,
            salesOffice TEXT,
            soldToParty TEXT,
            creationDate TEXT,
            totalNetAmount REAL,
            transactionCurrency TEXT,
            overallDeliveryStatus TEXT,
            overallOrdReltdBillgStatus TEXT,
            overallSdDocReferenceStatus TEXT,
            requestedDeliveryDate TEXT,
            customerPaymentTerms TEXT
        );
        CREATE TABLE IF NOT EXISTS sales_order_items (
            salesOrder TEXT,
            salesOrderItem TEXT,
            material TEXT,
            requestedQuantity REAL,
            requestedQuantityUnit TEXT,
            netAmount REAL,
            productionPlant TEXT,
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
            shippingPoint TEXT,
            creationDate TEXT,
            actualGoodsMovementDate TEXT,
            deliveryBlockReason TEXT,
            headerBillingBlockReason TEXT,
            overallGoodsMovementStatus TEXT,
            overallPickingStatus TEXT,
            hdrGeneralIncompletionStatus TEXT,
            soldToParty TEXT,
            shipToParty TEXT
        );
        CREATE TABLE IF NOT EXISTS outbound_delivery_items (
            deliveryDocument TEXT,
            deliveryDocumentItem TEXT,
            material TEXT,
            actualDeliveryQuantity REAL,
            deliveryQuantityUnit TEXT,
            referenceSdDocument TEXT,
            referenceSdDocumentItem TEXT,
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
            referenceDocument TEXT,
            clearingDate TEXT,
            clearingAccountingDocument TEXT,
            clearingDocFiscalYear TEXT,
            postingDate TEXT,
            documentDate TEXT,
            assignmentReference TEXT,
            PRIMARY KEY (accountingDocument, companyCode, fiscalYear, accountingDocumentItem)
        );
        CREATE TABLE IF NOT EXISTS payments_accounts_receivable (
            accountingDocument TEXT,
            companyCode TEXT,
            fiscalYear TEXT,
            accountingDocumentItem TEXT,
            customer TEXT,
            amountInTransactionCurrency REAL,
            transactionCurrency TEXT,
            postingDate TEXT,
            documentDate TEXT,
            clearingDate TEXT,
            clearingAccountingDocument TEXT,
            clearingDocFiscalYear TEXT,
            referenceDocument TEXT,
            paymentAmount REAL,
            paymentDate TEXT,
            paymentMethod TEXT,
            clearingDocument TEXT,
            PRIMARY KEY (accountingDocument, companyCode, fiscalYear, accountingDocumentItem)
        );
        CREATE TABLE IF NOT EXISTS business_partners (
            businessPartner TEXT PRIMARY KEY,
            customer TEXT,
            businessPartnerName TEXT,
            businessPartnerFullName TEXT,
            businessPartnerCategory TEXT,
            creationDate TEXT
            ,lastChangeDate TEXT,
            businessPartnerIsBlocked INTEGER,
            isMarkedForArchiving INTEGER
        );
        CREATE TABLE IF NOT EXISTS business_partner_addresses (
            businessPartner TEXT,
            addressId TEXT,
            streetName TEXT,
            cityName TEXT,
            region TEXT,
            country TEXT,
            postalCode TEXT,
            PRIMARY KEY (businessPartner, addressId)
        );
        CREATE TABLE IF NOT EXISTS customer_company_assignments (
            customer TEXT,
            companyCode TEXT,
            customerAccountGroup TEXT,
            reconciliationAccount TEXT,
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
            mrpType TEXT,
            profitCenter TEXT,
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
            salesOrganization TEXT,
            distributionChannel TEXT,
            division TEXT,
            addressId TEXT,
            language TEXT
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
