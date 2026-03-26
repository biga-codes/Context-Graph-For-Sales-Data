"""
graph_builder.py — Builds nodes + edges from the SAP-style SQLite database.
"""

import os
import time
from threading import Lock

from services.db import get_connection

NODE_COLORS = {
    "BillingDocument":  "#f97316",
    "SalesOrder":       "#3b82f6",
    "Delivery":         "#10b981",
    "JournalEntry":     "#a78bfa",
    "Payment":          "#f43f5e",
    "BusinessPartner":  "#fbbf24",
    "Product":          "#34d399",
    "Plant":            "#94a3b8",
}

_GRAPH_CACHE = {"data": None, "built_at": 0.0}
_GRAPH_CACHE_LOCK = Lock()
_GRAPH_CACHE_TTL_SECONDS = int(os.getenv("GRAPH_CACHE_TTL_SECONDS", "120"))


def _node(id, label, type_, data):
    return {
        "id": id,
        "type": "entityNode",
        "data": {
            "label": label,
            "entityType": type_,
            "color": NODE_COLORS.get(type_, "#ccc"),
            "properties": data,
        },
        "position": {"x": 0, "y": 0},
    }


def _edge(source, target, label):
    return {
        "id": f"{source}__{target}__{label}",
        "source": source,
        "target": target,
        "label": label,
        "type": "smoothstep",
        "animated": False,
    }


def build_full_graph() -> dict:
    conn = get_connection()
    nodes, edges = [], []

    # ── Billing Documents ─────────────────────────────────────────────────
    for row in conn.execute("SELECT * FROM billing_document_headers LIMIT 200"):
        r = dict(row)
        bid = r["billingDocument"]
        nodes.append(_node(f"bd_{bid}", f"Billing {bid}", "BillingDocument", r))

    # ── Sales Orders ──────────────────────────────────────────────────────
    for row in conn.execute("SELECT * FROM sales_order_headers LIMIT 200"):
        r = dict(row)
        so = r["salesOrder"]
        nodes.append(_node(f"so_{so}", f"SO {so}", "SalesOrder", r))
        if r.get("soldToParty"):
            edges.append(_edge(f"bp_{r['soldToParty']}", f"so_{so}", "placed"))

    # ── Link Deliveries → Billing Documents via billing items ──────────────
    for row in conn.execute("""
        SELECT DISTINCT bdi.billingDocument, bdi.referenceSdDocument
        FROM billing_document_items bdi
        WHERE bdi.referenceSdDocument IS NOT NULL AND bdi.referenceSdDocument != ''
        LIMIT 500
    """):
        r = dict(row)
        edges.append(_edge(f"del_{r['referenceSdDocument']}", f"bd_{r['billingDocument']}", "billed_as"))

    # ── Outbound Deliveries ───────────────────────────────────────────────
    for row in conn.execute("SELECT * FROM outbound_delivery_headers LIMIT 200"):
        r = dict(row)
        dd = r["deliveryDocument"]
        nodes.append(_node(f"del_{dd}", f"Delivery {dd}", "Delivery", r))
        if r.get("soldToParty"):
            edges.append(_edge(f"bp_{r['soldToParty']}", f"del_{dd}", "delivered_to"))

    # ── Link Deliveries → Sales Orders via delivery items ─────────────────
    for row in conn.execute("""
        SELECT DISTINCT deliveryDocument, referenceSdDocument
        FROM outbound_delivery_items
        WHERE referenceSdDocument IS NOT NULL AND referenceSdDocument != ''
        LIMIT 500
    """):
        r = dict(row)
        edges.append(_edge(f"so_{r['referenceSdDocument']}", f"del_{r['deliveryDocument']}", "fulfilled_by"))

    # ── Link Sales Orders → Products via order items ──────────────────────
    for row in conn.execute("""
        SELECT DISTINCT salesOrder, material
        FROM sales_order_items
        WHERE material IS NOT NULL AND material != ''
        LIMIT 1000
    """):
        r = dict(row)
        edges.append(_edge(f"so_{r['salesOrder']}", f"prod_{r['material']}", "contains_product"))

    # ── Link Deliveries → Products via delivery items ─────────────────────
    for row in conn.execute("""
        SELECT DISTINCT deliveryDocument, material
        FROM outbound_delivery_items
        WHERE material IS NOT NULL AND material != ''
        LIMIT 1000
    """):
        r = dict(row)
        edges.append(_edge(f"del_{r['deliveryDocument']}", f"prod_{r['material']}", "ships_product"))

    # ── Link Billing Documents → Products via billing items ───────────────
    for row in conn.execute("""
        SELECT DISTINCT billingDocument, material
        FROM billing_document_items
        WHERE material IS NOT NULL AND material != ''
        LIMIT 1000
    """):
        r = dict(row)
        edges.append(_edge(f"bd_{r['billingDocument']}", f"prod_{r['material']}", "bills_product"))

    # ── Journal Entries ───────────────────────────────────────────────────
    for row in conn.execute("""
        SELECT DISTINCT accountingDocument, companyCode, fiscalYear, customer
        FROM journal_entry_items_accounts_receivable LIMIT 200
    """):
        r = dict(row)
        jid = f"{r['accountingDocument']}_{r['companyCode']}"
        nodes.append(_node(f"je_{jid}", f"JE {r['accountingDocument']}", "JournalEntry", r))

    # ── Link Billing → Journal via accountingDocument ─────────────────────
    for row in conn.execute("""
        SELECT billingDocument, accountingDocument, companyCode
        FROM billing_document_headers
        WHERE accountingDocument IS NOT NULL AND accountingDocument != ''
        LIMIT 300
    """):
        r = dict(row)
        jid = f"{r['accountingDocument']}_{r['companyCode']}"
        edges.append(_edge(f"bd_{r['billingDocument']}", f"je_{jid}", "posted_to"))

    # ── Payments ──────────────────────────────────────────────────────────
    for row in conn.execute("SELECT * FROM payments_accounts_receivable LIMIT 200"):
        r = dict(row)
        pid = f"{r['accountingDocument']}_{r['companyCode']}_{r.get('accountingDocumentItem', '1')}"
        nodes.append(_node(f"pay_{pid}", f"Payment {r['accountingDocument']}", "Payment", r))
        jid = f"{r['accountingDocument']}_{r['companyCode']}"
        edges.append(_edge(f"je_{jid}", f"pay_{pid}", "cleared_by"))

    # ── Business Partners ─────────────────────────────────────────────────
    for row in conn.execute("SELECT * FROM business_partners LIMIT 200"):
        r = dict(row)
        bp = r["businessPartner"]
        nodes.append(_node(f"bp_{bp}", r.get("businessPartnerName") or f"BP {bp}", "BusinessPartner", r))

    # ── Products ──────────────────────────────────────────────────────────
    for row in conn.execute("""
        SELECT p.product, pd.productDescription, p.baseUnit
        FROM products p
        LEFT JOIN product_descriptions pd ON p.product = pd.product AND pd.language = 'EN'
        LIMIT 200
    """):
        r = dict(row)
        prod = r["product"]
        label = r.get("productDescription") or prod
        nodes.append(_node(f"prod_{prod}", label[:30], "Product", r))

    # ── Link products → plants from product-plant assignments ─────────────
    for row in conn.execute("""
        SELECT DISTINCT product, plant
        FROM product_plants
        WHERE plant IS NOT NULL AND plant != ''
        LIMIT 1000
    """):
        r = dict(row)
        edges.append(_edge(f"prod_{r['product']}", f"pl_{r['plant']}", "available_at"))

    # ── Link deliveries → plants via delivery items ───────────────────────
    for row in conn.execute("""
        SELECT DISTINCT deliveryDocument, plant
        FROM outbound_delivery_items
        WHERE plant IS NOT NULL AND plant != ''
        LIMIT 1000
    """):
        r = dict(row)
        edges.append(_edge(f"del_{r['deliveryDocument']}", f"pl_{r['plant']}", "dispatched_from"))

    # ── Link sales order items' production plant ──────────────────────────
    for row in conn.execute("""
        SELECT DISTINCT salesOrder, productionPlant
        FROM sales_order_items
        WHERE productionPlant IS NOT NULL AND productionPlant != ''
        LIMIT 1000
    """):
        r = dict(row)
        edges.append(_edge(f"so_{r['salesOrder']}", f"pl_{r['productionPlant']}", "planned_from"))

    # ── Plants ────────────────────────────────────────────────────────────
    for row in conn.execute("SELECT * FROM plants LIMIT 50"):
        r = dict(row)
        nodes.append(_node(f"pl_{r['plant']}", r.get("plantName") or r["plant"], "Plant", r))

    conn.close()

    # Deduplicate nodes
    seen = set()
    unique_nodes = [n for n in nodes if not (n["id"] in seen or seen.add(n["id"]))]

    return {"nodes": unique_nodes, "edges": edges}


def _get_cached_full_graph() -> dict:
    now = time.time()
    with _GRAPH_CACHE_LOCK:
        if (
            _GRAPH_CACHE["data"] is not None
            and now - _GRAPH_CACHE["built_at"] < _GRAPH_CACHE_TTL_SECONDS
        ):
            return _GRAPH_CACHE["data"]

    data = build_full_graph()

    with _GRAPH_CACHE_LOCK:
        _GRAPH_CACHE["data"] = data
        _GRAPH_CACHE["built_at"] = time.time()

    return data


def get_full_graph_cached() -> dict:
    return _get_cached_full_graph()


def get_node_neighbors(node_id: str) -> dict:
    full = _get_cached_full_graph()
    neighbor_ids = set()
    filtered_edges = []
    for e in full["edges"]:
        if e["source"] == node_id or e["target"] == node_id:
            filtered_edges.append(e)
            neighbor_ids.update([e["source"], e["target"]])
    neighbor_ids.add(node_id)
    filtered_nodes = [n for n in full["nodes"] if n["id"] in neighbor_ids]
    return {"nodes": filtered_nodes, "edges": filtered_edges}
