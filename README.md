# Hoth Industries — Supplier Recommendation Engine

A sourcing decision tool that takes a procurement need as input and outputs a supplier recommendation with reasoning. Built from real (simulated) purchase order, quality inspection, and supplier feedback data.

## What It Does

A procurement person types "I need 200 heat exchangers" and gets back:
- **Recommended supplier** — lowest total cost of ownership
- **Alternative** — backup option
- **Supplier to avoid** — with specific reasons why

Then they can ask follow-up questions in a chat interface powered by Claude, which has full access to the supplier data.

## How It Works

### Data Pipeline

1. **Load 4 data sources** — 500 purchase orders, 200 quality inspections, 92 RFQ quotes, and unstructured team notes
2. **Entity resolution** — Normalize supplier names (e.g., "APEX MFG", "Apex Mfg", "APEX Manufacturing Inc" → "Apex Manufacturing")
3. **Inspection join** — Quality inspections have no supplier field. We join them to orders by matching `order_id` + `parts_inspected == quantity`
4. **Score every supplier per part category** — On-time %, rejection %, average delay, and TCO

### Scoring: Total Cost of Ownership (TCO)

We rank suppliers by what they actually cost, not just their sticker price:

```
effective_cost = unit_price × (1 + rejection_rate × 0.5 + late_rate × 0.2)
```

| Factor | Multiplier | Why |
|--------|-----------|-----|
| Rejection rate | × 0.5 | Each rejected part costs ~50% of unit price to rework or reorder |
| Late delivery rate | × 0.2 | Late deliveries add ~20% in expediting, idle production lines, missed customer deadlines |

**Example:** QuickFab quotes $1,473/unit for heat exchangers. But with 16.3% rejection and 62.5% late delivery rate, their true cost is **$1,712/unit** — the most expensive option despite having the lowest sticker price.

### Part Category Matching (FAISS)

Users type natural language. We use FAISS vector search with sentence-transformers (`all-MiniLM-L6-v2`) to map their input to one of 13 part categories (HX, MOTOR, BRKT, CTRL, etc.). This is scalable — in production with hundreds of categories, the same approach works without maintaining keyword maps.

### Chat (Claude API)

After seeing the recommendation, users can ask follow-up questions. Claude (`claude-sonnet-4-20250514`) has the full supplier scorecard data and team notes in its system prompt, so it answers with specific numbers.

## Tech Stack

- **Backend:** Python, Flask
- **Data:** pandas (in-memory, no database)
- **Vector search:** FAISS + sentence-transformers (all-MiniLM-L6-v2)
- **LLM:** Anthropic Claude API (claude-sonnet-4-20250514)
- **Frontend:** Plain HTML/CSS/JS (no build tools)

## Project Structure

```
hoth-engine/
├── main.py              # Flask app — data pipeline, scoring, API endpoints
├── requirements.txt     # Python dependencies
├── .env                 # ANTHROPIC_API_KEY (not committed)
├── data/
│   ├── supplier_orders.csv        # 500 purchase orders
│   ├── quality_inspections.csv    # 200 quality inspections
│   ├── rfq_responses.csv          # 92 supplier quotes
│   └── supplier_notes.txt         # Unstructured team feedback
└── static/
    ├── index.html       # Single-page frontend
    ├── style.css        # Styles
    └── app.js           # Frontend logic
```

## Setup & Run

### Prerequisites

- Python 3.10+
- An Anthropic API key (for the chat feature)

### Install

```bash
pip install -r requirements.txt
```

### Configure

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_key_here
```

### Run

```bash
python main.py
```

Open **http://127.0.0.1:8000** in your browser.

### Try These Queries

- "200 aluminum heat exchangers, need delivery in 4 weeks"
- "Brackets for the CoreWeave project"
- "Who should we use for 10HP motors?"
- "HEPA filters for data center cleanroom"

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Server status |
| `GET` | `/api/suppliers` | All supplier scorecards |
| `POST` | `/api/recommend` | `{part_type: "..."}` → recommendation |
| `POST` | `/api/chat` | `{message: "...", history: [...]}` → Claude response |
