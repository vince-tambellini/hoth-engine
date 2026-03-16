import os
import json
import numpy as np
import pandas as pd
import faiss
from flask import Flask, request, jsonify, send_from_directory
from sentence_transformers import SentenceTransformer
import anthropic
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder="static")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ---------------------------------------------------------------------------
# 1. Entity resolution
# ---------------------------------------------------------------------------

def normalize_supplier(name: str) -> str:
    n = name.strip().lower()
    if "apex" in n:
        return "Apex Manufacturing"
    return name.strip()


# ---------------------------------------------------------------------------
# 2. Load & clean data
# ---------------------------------------------------------------------------

def load_data():
    # Orders
    orders = pd.read_csv(os.path.join(DATA_DIR, "supplier_orders.csv"))
    orders["supplier_name"] = orders["supplier_name"].apply(normalize_supplier)
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders["promised_date"] = pd.to_datetime(orders["promised_date"])
    orders["actual_delivery_date"] = pd.to_datetime(
        orders["actual_delivery_date"], errors="coerce"
    )
    orders["part_category"] = orders["part_number"].str.extract(r"^([A-Z]+)")

    # Inspections — join to orders by order_id + quantity match
    inspections = pd.read_csv(os.path.join(DATA_DIR, "quality_inspections.csv"))
    inspections = inspections.merge(
        orders[["order_id", "quantity", "supplier_name", "part_category"]],
        left_on=["order_id", "parts_inspected"],
        right_on=["order_id", "quantity"],
        how="left",
    )

    # RFQ responses
    rfq = pd.read_csv(os.path.join(DATA_DIR, "rfq_responses.csv"))
    rfq["supplier_name"] = rfq["supplier_name"].apply(normalize_supplier)

    # Supplier notes
    with open(os.path.join(DATA_DIR, "supplier_notes.txt"), encoding="utf-8") as f:
        supplier_notes_raw = f.read()

    return orders, inspections, rfq, supplier_notes_raw


# ---------------------------------------------------------------------------
# 3. Scoring engine — TCO (Total Cost of Ownership)
#
# effective_cost = unit_price × (1 + rejection_rate × 0.5 + late_rate × 0.2)
#
# Why these factors:
#   - Each rejected part costs ~50% of unit price to rework or reorder
#   - Each late delivery adds ~20% in expediting, idle lines, missed deadlines
#
# Rank by lowest effective cost = best supplier.
# ---------------------------------------------------------------------------

REWORK_COST_FACTOR = 0.5   # rejected parts cost 50% of unit price to fix
DELAY_COST_FACTOR = 0.2    # late deliveries add 20% in hidden costs

def compute_scores(orders: pd.DataFrame, inspections: pd.DataFrame):
    """Return a dict keyed by (supplier, category) with TCO metrics."""
    scores = {}

    # --- delivery metrics per supplier per category ---
    has_delivery = orders.dropna(subset=["actual_delivery_date"]).copy()
    has_delivery["delay_days"] = (
        has_delivery["actual_delivery_date"] - has_delivery["promised_date"]
    ).dt.days
    has_delivery["on_time"] = has_delivery["delay_days"] <= 0

    delivery_stats = (
        has_delivery.groupby(["supplier_name", "part_category"])
        .agg(
            total_orders=("order_id", "count"),
            on_time_count=("on_time", "sum"),
            avg_delay_days=("delay_days", "mean"),
            avg_unit_price=("unit_price", "mean"),
        )
        .reset_index()
    )

    # --- quality metrics per supplier per category ---
    quality_stats = (
        inspections.dropna(subset=["supplier_name"])
        .groupby(["supplier_name", "part_category"])
        .agg(
            total_inspected=("parts_inspected", "sum"),
            total_rejected=("parts_rejected", "sum"),
        )
        .reset_index()
    )

    # Merge delivery + quality
    merged = delivery_stats.merge(
        quality_stats,
        on=["supplier_name", "part_category"],
        how="left",
    )
    merged["total_inspected"] = merged["total_inspected"].fillna(0)
    merged["total_rejected"] = merged["total_rejected"].fillna(0)

    for _, row in merged.iterrows():
        key = (row["supplier_name"], row["part_category"])

        on_time_pct = (
            round(row["on_time_count"] / row["total_orders"] * 100, 1)
            if row["total_orders"] > 0
            else 0
        )
        late_rate = 1 - (row["on_time_count"] / row["total_orders"]) if row["total_orders"] > 0 else 0
        rejection_rate = (
            row["total_rejected"] / row["total_inspected"]
            if row["total_inspected"] > 0
            else 0
        )
        rejection_pct = round(rejection_rate * 100, 1)
        avg_delay = round(row["avg_delay_days"], 1)
        avg_price = round(row["avg_unit_price"], 2)

        # TCO: what you actually pay per unit after accounting for rework and delays
        effective_cost = avg_price * (
            1 + rejection_rate * REWORK_COST_FACTOR + late_rate * DELAY_COST_FACTOR
        )

        scores[key] = {
            "supplier": row["supplier_name"],
            "part_category": row["part_category"],
            "total_orders": int(row["total_orders"]),
            "on_time_pct": on_time_pct,
            "late_rate_pct": round(late_rate * 100, 1),
            "rejection_pct": rejection_pct,
            "avg_delay_days": avg_delay,
            "avg_unit_price": avg_price,
            "effective_cost": round(effective_cost, 2),
            "total_inspected": int(row["total_inspected"]),
            "total_rejected": int(row["total_rejected"]),
        }

    return scores


# ---------------------------------------------------------------------------
# 4. Supplier notes
# ---------------------------------------------------------------------------

SUPPLIER_NOTES = {
    "QuickFab Industries": (
        "Team warns: weld quality poor on pressure vessels. "
        "OK for brackets and fins only. Chronic late delivery."
    ),
    "Stellar Metalworks": (
        "Highest quality but capacity-limited. "
        "Use for critical deliveries with zero error margin."
    ),
    "TitanForge LLC": (
        "Best for motors. Do not use for other part types."
    ),
    "AeroFlow Systems": (
        "Air handling specialist. Most accurate lead times. "
        "Cleanroom-certified HEPA."
    ),
    "Precision Thermal Co": (
        "Electronics and controls expert. Excellent technical support."
    ),
    "Apex Manufacturing": (
        "General purpose default. Reliable but not exceptional. "
        "DATA ISSUE: 4 name variants in SAP."
    ),
}

# Supplier specializations — which categories each supplier is known for
SUPPLIER_SPECIALIZATIONS = {
    "TitanForge LLC": ["MOTOR"],
    "AeroFlow Systems": ["DAMPER", "LOUVER", "FILTER", "FAN"],
    "Precision Thermal Co": ["CTRL", "SENSOR"],
    "Stellar Metalworks": ["SHAFT", "BRKT"],
}


# ---------------------------------------------------------------------------
# 5. FAISS part-category index
# ---------------------------------------------------------------------------

CATEGORY_DOCS = {
    "HX": "heat exchanger, HX, coil, aluminum heat exchanger, heavy duty heat exchanger, brazed plate heat exchanger",
    "MOTOR": "motor, fan motor, electric motor, 3HP motor, 5HP motor, 7.5HP motor, 10HP motor",
    "BRKT": "bracket, mount, heavy duty mount, vibration mount, aluminum bracket",
    "FAN": "fan, cooling fan, axial fan, high CFM fan, ventilation fan",
    "CTRL": "controller, PLC, VFD, control, PLC control module, touch screen controller, temperature controller",
    "SENSOR": "sensor, temperature sensor, flow sensor, pressure sensor",
    "FILTER": "filter, HEPA, HEPA filter, air filter, cleanroom filter",
    "PANEL": "panel, control panel, enclosure, stainless control panel",
    "SHAFT": "shaft, drive shaft, motor shaft",
    "BEARING": "bearing, sealed bearing, heavy duty bearing, bearing assembly",
    "DAMPER": "damper, pneumatic damper",
    "LOUVER": "louver, air louver",
    "FINS": "fins, fin, aluminum fins, cooling fins",
}


def build_faiss_index(model: SentenceTransformer):
    categories = list(CATEGORY_DOCS.keys())
    texts = [CATEGORY_DOCS[c] for c in categories]
    embeddings = model.encode(texts, normalize_embeddings=True).astype("float32")
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index, categories


def query_category(text: str, model: SentenceTransformer, index, categories, k=1):
    vec = model.encode([text], normalize_embeddings=True).astype("float32")
    distances, indices = index.search(vec, k)
    best_idx = indices[0][0]
    return categories[best_idx], float(distances[0][0])


# ---------------------------------------------------------------------------
# 6. Recommendation logic — rank by lowest effective cost (TCO)
# ---------------------------------------------------------------------------

def get_recommendation(category: str, scores: dict):
    """Return recommended, alternative, avoid for a given part category."""
    candidates = [v for k, v in scores.items() if k[1] == category]
    if not candidates:
        return None

    # Sort by lowest effective cost (TCO). Specialist bonus breaks ties.
    def sort_key(x):
        specialist = -1 if category in SUPPLIER_SPECIALIZATIONS.get(x["supplier"], []) else 0
        return (x["effective_cost"], specialist)
    candidates.sort(key=sort_key)

    recommended = candidates[0]
    alternative = candidates[1] if len(candidates) > 1 else None
    avoid = candidates[-1] if len(candidates) > 1 else None
    if avoid and avoid["supplier"] == recommended["supplier"]:
        avoid = None

    def build_entry(s):
        if s is None:
            return None
        note = SUPPLIER_NOTES.get(s["supplier"], "")
        return {
            "supplier": s["supplier"],
            "reason": "",
            "unit_price_avg": s["avg_unit_price"],
            "effective_cost": s["effective_cost"],
            "on_time_pct": s["on_time_pct"],
            "rejection_pct": s["rejection_pct"],
            "avg_delay_days": s["avg_delay_days"],
            "total_orders": s["total_orders"],
            "team_notes": note,
        }

    rec = build_entry(recommended)
    rec["reason"] = (
        f"Lowest total cost for {category} parts. "
        f"${rec['unit_price_avg']}/unit, effectively ${rec['effective_cost']}/unit "
        f"after factoring in {rec['rejection_pct']}% rejection and "
        f"{100 - rec['on_time_pct']}% late rate."
    )

    alt = build_entry(alternative)
    if alt:
        alt["reason"] = (
            f"Next best TCO for {category}. "
            f"${alt['effective_cost']}/unit effective cost. "
            f"{alt['total_orders']} orders, {alt['on_time_pct']}% on-time."
        )

    avd = build_entry(avoid)
    if avd:
        avd["reason"] = (
            f"Highest true cost for {category}. "
            f"Looks like ${avd['unit_price_avg']}/unit but actually "
            f"${avd['effective_cost']}/unit after {avd['rejection_pct']}% rejection "
            f"and {100 - avd['on_time_pct']}% late rate. {avd['team_notes']}"
        )

    total_orders_cat = sum(c["total_orders"] for c in candidates)
    context = {
        "total_historical_orders": total_orders_cat,
        "suppliers_evaluated": len(candidates),
        "part_category": category,
    }

    return {
        "recommended": rec,
        "alternative": alt,
        "avoid": avd,
        "context": context,
    }


# ---------------------------------------------------------------------------
# 7. Startup — load everything
# ---------------------------------------------------------------------------

print("Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading data...")
orders_df, inspections_df, rfq_df, supplier_notes_raw = load_data()

print("Computing supplier scores...")
supplier_scores = compute_scores(orders_df, inspections_df)

print("Building FAISS index...")
faiss_index, faiss_categories = build_faiss_index(embed_model)

# Build summary for chat system prompt
scores_summary = json.dumps(list(supplier_scores.values()), indent=2)

# All unique suppliers
all_suppliers = list({v["supplier"] for v in supplier_scores.values()})

print(f"Ready. {len(orders_df)} orders, {len(inspections_df)} inspections, "
      f"{len(supplier_scores)} supplier-category scores.")


# ---------------------------------------------------------------------------
# 8. API endpoints
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "orders": len(orders_df),
                    "suppliers": len(all_suppliers)})


@app.route("/api/suppliers", methods=["GET"])
def suppliers():
    return jsonify(list(supplier_scores.values()))


@app.route("/api/recommend", methods=["POST"])
def recommend():
    body = request.get_json(force=True)
    user_input = body.get("part_type", "").strip()
    if not user_input:
        return jsonify({"error": "part_type is required"}), 400

    category, confidence = query_category(
        user_input, embed_model, faiss_index, faiss_categories
    )

    result = get_recommendation(category, supplier_scores)
    if result is None:
        return jsonify({"error": f"No data for category {category}"}), 404

    result["matched_category"] = category
    result["match_confidence"] = round(confidence, 3)
    return jsonify(result)


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    message = body.get("message", "").strip()
    history = body.get("history", [])
    recommendation_context = body.get("recommendation", None)

    if not message:
        return jsonify({"error": "message is required"}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not set"}), 500

    rec_section = ""
    if recommendation_context:
        rec_section = (
            "\n\nThe user's most recent recommendation result:\n"
            + json.dumps(recommendation_context, indent=2)
        )

    system_prompt = f"""You are a procurement decision assistant for Hoth Industries. You help the sourcing team make supplier decisions based on real performance data.

HOW WE RANK SUPPLIERS:
We use Total Cost of Ownership (TCO). The formula:
  effective_cost = unit_price × (1 + rejection_rate × 0.5 + late_rate × 0.2)
- Each rejected part costs ~50% of unit price to rework or reorder
- Each late delivery adds ~20% in expediting costs, idle production lines, and missed customer deadlines
- Lowest effective cost = best supplier

SUPPLIER PERFORMANCE DATA:
{scores_summary}

SUPPLIER NOTES (qualitative feedback from the procurement team):
{supplier_notes_raw}

SUPPLIER SUMMARIES:
{json.dumps(SUPPLIER_NOTES, indent=2)}
{rec_section}

INSTRUCTIONS:
- Answer with specific numbers from Hoth's data. Cite order counts, on-time percentages, rejection rates, and effective costs.
- Be direct. Make recommendations. Don't hedge.
- When comparing suppliers, show both the sticker price AND the effective cost.
- If a supplier has team notes/warnings, mention them.
- Keep answers concise — procurement people are busy.
"""

    messages = []
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )

    reply = response.content[0].text
    return jsonify({"reply": reply})


# ---------------------------------------------------------------------------
# 9. Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
