# Supplier Recommendation Engine — Specification

## What This Is

A tool for Hoth Industries procurement team that takes a sourcing need as input and outputs a supplier recommendation with reasoning. Not a dashboard. Not a report generator. The answer.

## The Problem It Solves

Hoth keeps ordering from bad suppliers because quality and delivery data never reaches procurement at decision time. Their procurement manager said: "I keep hearing 'we used them before and they had problems' AFTER we've already placed an order."

This tool assembles the full picture from three disconnected data sources and makes the recommendation before the PO is placed.

## Data Sources (included in /data)

### supplier_orders.csv (500 rows)
- Fields: order_id, supplier_name, part_number, part_description, order_date, promised_date, actual_delivery_date, quantity, unit_price, po_amount
- Date range: Oct 2021 – Sep 2025
- Known issues:
  - Supplier "Apex Manufacturing" appears as 4 variants: "APEX MFG", "Apex Mfg", "APEX Manufacturing Inc", "Apex Manufacturing Inc"
  - 8 orders have missing actual_delivery_date
  - Part numbers use prefix convention: HX (heat exchangers), MOTOR, CTRL (controllers), BRKT (brackets), FAN, FINS, SENSOR, FILTER, PANEL, SHAFT, BEARING, DAMPER, LOUVER

### quality_inspections.csv (200 rows)
- Fields: inspection_id, order_id, inspection_date, parts_inspected, parts_rejected, rejection_reason, rework_required
- Known issues:
  - NO supplier name field — must join to supplier_orders via order_id + quantity match (parts_inspected == quantity on the order line)
  - This join works reliably because quantities are unique within each PO

### rfq_responses.csv (92 rows)
- Fields: rfq_id, supplier_name, part_description, quote_date, quoted_price, lead_time_weeks, notes
- Same supplier name inconsistencies as orders

### supplier_notes.txt (qualitative data)
- Unstructured text: emails, meeting notes, team feedback
- Contains critical context the numbers don't capture:
  - QuickFab: weld quality poor on pressure vessels, fine for brackets/fins
  - TitanForge: excellent for motors, don't use for anything else
  - AeroFlow: air handling specialist, most accurate lead times
  - Precision Thermal: electronics/controls expert
  - Stellar: highest quality but capacity-limited
  - Apex: reliable B+ default, 40% of fan business

## Architecture

```
┌─────────────────────────────────────────────┐
│                  Frontend                    │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Input: "I need 200 aluminum heat      │  │
│  │  exchangers, 4-week deadline"          │  │
│  └────────────────────────────────────────┘  │
│                     │                        │
│                     ▼                        │
│  ┌────────────────────────────────────────┐  │
│  │  RECOMMENDATION (primary output)       │  │
│  │                                        │  │
│  │  ✅ Use: Apex Manufacturing            │  │
│  │  $1,120/unit | 85% on-time | 2.5% rej │  │
│  │                                        │  │
│  │  ⚠️ Alternative: AeroFlow Systems     │  │
│  │  $1,195/unit | higher but zero fails   │  │
│  │                                        │  │
│  │  🚫 Avoid: QuickFab Industries        │  │
│  │  Cheapest but 15.6% rejection on HX   │  │
│  └────────────────────────────────────────┘  │
│                     │                        │
│                     ▼                        │
│  ┌────────────────────────────────────────┐  │
│  │  FOLLOW-UP (conversational drill-down) │  │
│  │                                        │  │
│  │  User: "Why not QuickFab?"             │  │
│  │  → Specific data: 9 HX orders,        │  │
│  │    8 late, 15.6% reject, team notes    │  │
│  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│               Backend (Python)               │
│                                              │
│  1. Data Ingestion & Entity Resolution       │
│     - Normalize supplier names               │
│     - Join inspections to orders             │
│     - Parse supplier_notes.txt               │
│                                              │
│  2. Scoring Engine                           │
│     - Per-supplier, per-part-category        │
│     - On-time %, rejection %, avg delay      │
│     - TCO = direct cost + rework + delays    │
│                                              │
│  3. Recommendation API                       │
│     - Input: part type, quantity, deadline    │
│     - Output: ranked suppliers + reasoning   │
│                                              │
│  4. Anthropic API (conversational layer)     │
│     - System prompt with full Hoth context   │
│     - Supplier scores as structured data     │
│     - supplier_notes.txt as qualitative ctx  │
│     - User asks follow-ups, gets data-backed │
│       answers                                │
└─────────────────────────────────────────────┘
```

## Data Pipeline Detail

### Step 1: Entity Resolution
```python
def normalize_supplier(name):
    n = name.strip().lower()
    if 'apex' in n:
        return 'Apex Manufacturing'
    return name.strip()
```
This is intentionally simple for the demo. In production, Drawer's AI entity resolution would handle this. In the interview, explain: "I hardcoded the Apex mapping because we know it. Drawer would do this automatically across thousands of suppliers using fuzzy matching and drawing-based identity."

### Step 2: Inspection-to-Supplier Join
The inspections table has no supplier field. Join via:
- Match on order_id
- Within that order, match parts_inspected to quantity on the order line
- This works because quantities are unique within each PO

This is a great interview talking point: "Their quality data isn't linked to their supplier data. I had to reverse-engineer the join. This is exactly why they can't close the feedback loop."

### Step 3: Scoring
Per supplier, per part category (HX, MOTOR, CTRL, etc.):
- on_time_pct: deliveries on or before promised_date / total deliveries
- rejection_pct: parts_rejected / parts_inspected
- avg_delay_days: mean of (actual_delivery - promised_date)
- tco_per_unit: unit_price + (rejection_pct * rework_cost_estimate) + (late_probability * delay_cost_per_day * avg_delay)
- composite_score: weighted blend (35% delivery, 40% quality, 25% cost-adjusted)

### Step 4: Recommendation Logic
Given a part type + quantity + deadline:
1. Find all suppliers who have made this part category before
2. Score each by composite score for this category
3. Check deadline feasibility against actual lead time history
4. Apply qualitative flags from supplier_notes (e.g., "don't use QuickFab for pressure vessels")
5. Return: recommended supplier, alternative, suppliers to avoid, with specific reasoning

## Anthropic API Integration

The conversational layer uses Claude with a system prompt containing:
- The full computed supplier scorecards (structured JSON)
- The supplier_notes.txt content (qualitative context)
- Part-category-level performance breakdowns
- Instructions to answer with specific numbers from Hoth's data
- Instructions to be direct and opinionated (this is a decision tool, not a hedge-everything assistant)

Model: claude-sonnet-4-20250514
Use for: follow-up questions after the recommendation is shown

## Frontend Design

Keep it simple. Not a dashboard.

### Primary screen:
- Large text input: "What do you need to source?"
- Example prompts below the input:
  - "200 aluminum heat exchangers, need delivery in 4 weeks"
  - "Brackets for the CoreWeave project"
  - "Who should we use for 10HP motors?"

### After submission:
- Recommendation card: the answer (supplier name, key stats, one sentence why)
- Alternative card: backup option with one sentence
- Avoid card: who NOT to use and why
- Below: chat input for follow-up questions

### Visual style:
- Clean, white background, no gradients
- Recommendation = green left border
- Alternative = blue left border  
- Avoid = red left border
- Minimal — this is a procurement tool, not a marketing site

## Demo Script (for interview)

1. Open the app. "This is the Supplier Recommendation Engine I built from Hoth's data."

2. Type: "I need 200 aluminum heat exchangers for the data center project"
   → System shows recommendation (Apex), alternative (AeroFlow), avoid (QuickFab)

3. "Notice it's not just showing me data — it's making the recommendation. Mike asked for decisions based on data. This is that."

4. Ask follow-up: "Why not QuickFab? They're 20% cheaper."
   → System explains with specific numbers from their order history

5. Ask: "What about the CoreWeave deadline? Can Apex deliver in 3 weeks?"
   → System checks lead time history and flags risk

6. "Now let me show you what's underneath." Walk through:
   - Entity resolution: "Apex appeared as 4 names. I consolidated them."
   - Inspection join: "Quality data had no supplier field. I joined by quantity match."
   - TCO calculation: "QuickFab looks cheap but costs $367K in hidden rework and delays."

7. Tie to Part 1: "This tool does what Drawer should enable — quality outcomes feeding back into supplier selection. Today it works on part numbers. With Drawer, it would work on drawing similarity."

## Tech Stack

- Python (FastAPI or Flask) for backend
- SQLite or just pandas for data storage (it's only 500+200+92 rows)
- Anthropic API for conversational layer
- React or plain HTML/JS for frontend
- Keep it simple — this is a demo, not production code

## What NOT to Build

- No user authentication
- No database migrations
- No dashboard views or charts
- No admin panel
- No export/PDF features (mention as future in demo)
- No multi-tenant anything

## Files Included

```
/data/
  supplier_orders.csv
  quality_inspections.csv
  rfq_responses.csv
  supplier_notes.txt
```

Copy these into your project's /data directory.
