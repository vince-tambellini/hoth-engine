# CLAUDE.md

## Project: Hoth Industries Supplier Recommendation Engine

### What this is
A sourcing decision tool for an industrial equipment manufacturer (Hoth Industries). The user describes what they need to source, and the system gives them a supplier recommendation with reasoning — not a dashboard, not a chatbot, the actual decision.

This is a demo prototype for a solutions architecture interview at CADDi. It needs to work, look clean, and be walkable in a 30-60 minute demo.

### Read SPEC.md first
The full specification is in SPEC.md. Read it entirely before writing any code. It contains the data pipeline logic, architecture, scoring algorithms, entity resolution rules, and the demo script.

### Data files
All source data is in `/data/`. There are 4 files:
- `supplier_orders.csv` — 500 rows of purchase orders (messy supplier names, some missing dates)
- `quality_inspections.csv` — 200 rows of quality inspections (NO supplier field — must join to orders)
- `rfq_responses.csv` — 92 rows of supplier quotes
- `supplier_notes.txt` — unstructured procurement team notes about each supplier

### Critical data issues to handle
1. **Supplier name normalization**: "APEX MFG", "Apex Mfg", "APEX Manufacturing Inc", "Apex Manufacturing Inc" are ALL the same company → normalize to "Apex Manufacturing"
2. **Inspection-to-supplier join**: quality_inspections has no supplier_name. Join to supplier_orders by matching order_id AND parts_inspected == quantity. This works because quantities are unique within each PO.
3. **8 orders have missing actual_delivery_date** — exclude from on-time calculations, don't crash on them.
4. **Part categories**: extract from part_number prefix (e.g., HX-5520 → "HX", MOTOR-6634 → "MOTOR"). Use these for category-level supplier scoring.

### Architecture
```
Backend (Python/FastAPI):
  /api/recommend    POST  {part_type, quantity?, deadline?} → recommendation JSON
  /api/chat         POST  {message, history} → Anthropic API response
  /api/suppliers    GET   → all supplier scorecards
  /api/health       GET   → status

Frontend (React or plain HTML):
  Single page. Input box at top. Recommendation cards below. Chat below that.
```

### Backend requirements
- Python. FastAPI preferred, Flask acceptable.
- Data processing with pandas.
- No database needed — load CSVs into memory at startup, compute all scores.
- Anthropic API key will be set as env var ANTHROPIC_API_KEY.
- Use claude-sonnet-4-20250514 for the chat endpoint.

### Scoring logic
Per supplier, per part category:
- `on_time_pct` = on-time deliveries / total deliveries with dates
- `rejection_pct` = parts_rejected / parts_inspected
- `avg_delay_days` = mean of (actual_delivery_date - promised_date).days
- `tco_multiplier` = 1 + (rejection_pct * 0.5) + (max(0, avg_delay_days) * 0.02)
  - This approximates: a 10% reject rate adds 5% to effective cost, each day late adds 2%
- `composite_score` = (on_time_pct * 0.35) + ((100 - rejection_pct) * 0.40) + (reliability * 0.25)
  - where reliability = max(0, 95 - max(0, avg_delay_days) * 5)

### Recommendation endpoint logic
Input: part description or part category (user types natural language, map to category)
Output:
```json
{
  "recommended": {
    "supplier": "Apex Manufacturing",
    "reason": "Most experienced with HX parts. 40 orders, 85% on-time, 2.5% rejection.",
    "unit_price_avg": 1120.50,
    "on_time_pct": 85.0,
    "rejection_pct": 2.5
  },
  "alternative": {
    "supplier": "AeroFlow Systems", 
    "reason": "Higher price but lower quality risk. 2.6% rejection, reliable lead times.",
    ...
  },
  "avoid": {
    "supplier": "QuickFab Industries",
    "reason": "15.6% rejection rate on HX. 60% late delivery. Team notes: weld quality consistently poor.",
    ...
  },
  "context": {
    "total_historical_orders": 67,
    "suppliers_evaluated": 4,
    "data_range": "Oct 2021 - Sep 2025"
  }
}
```

### Chat endpoint
System prompt should include:
- All computed supplier scores as JSON
- The full supplier_notes.txt content
- Part-category breakdowns
- Instruction: "You are a procurement decision assistant for Hoth Industries. Answer with specific numbers from their data. Be direct. Make recommendations. Don't hedge."
- The user's most recent recommendation result as context

### Frontend requirements
- Clean and simple. White background. No gradients, no fancy animations.
- One page. Three sections vertically:
  1. **Input**: large text field with placeholder "What do you need to source?" and 3-4 example prompts as clickable chips below
  2. **Recommendation**: three cards (recommended/green, alternative/blue, avoid/red) that appear after submission
  3. **Follow-up**: chat interface for drill-down questions. Only appears after recommendation is shown.
- Use a good sans-serif font. System font stack is fine.
- Mobile-responsive is not required.

### Part-type mapping
The user will type natural language. Map to part categories:
- "heat exchanger", "HX", "coil" → HX
- "motor", "fan motor" → MOTOR  
- "bracket", "mount" → BRKT
- "fan", "cooling fan", "axial fan" → FAN
- "controller", "PLC", "VFD", "control" → CTRL
- "sensor", "temperature sensor", "flow sensor" → SENSOR
- "filter", "HEPA" → FILTER
- "panel", "control panel", "enclosure" → PANEL
- "shaft", "drive shaft" → SHAFT
- "bearing" → BEARING
- "damper" → DAMPER
- "louver" → LOUVER
- "fins", "fin" → FINS

If the user's input doesn't clearly map, use the Anthropic API to extract the part type.

### Supplier notes integration
Parse supplier_notes.txt and attach qualitative flags to each supplier:
- QuickFab: "Team warns: weld quality poor on pressure vessels. OK for brackets and fins only."
- Stellar: "Highest quality but capacity-limited. Use for critical deliveries with zero error margin."
- TitanForge: "Best for motors. Do not use for other part types."
- AeroFlow: "Air handling specialist. Most accurate lead times. Cleanroom-certified HEPA."
- Precision Thermal: "Electronics and controls expert. Excellent technical support."
- Apex: "General purpose default. Reliable but not exceptional. DATA ISSUE: 4 name variants in SAP."

These should appear in recommendations and be available to the chat model.

### Running the project
```bash
# Install dependencies
pip install fastapi uvicorn pandas anthropic

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Run
python main.py
# or
uvicorn main:app --reload --port 8000
```

Frontend should be served from the same server (static files) or a simple dev server.

### What NOT to do
- Don't build a dashboard with charts and tabs
- Don't build user auth or database migrations
- Don't over-engineer — this is a demo, 500 rows of data, keep it simple
- Don't use TypeScript — plain JS is fine for the frontend
- Don't add PDF export, email integration, or anything not in the spec
- Don't make the chat the primary interface — the recommendation comes first, chat is for follow-ups

### File structure
```
/
├── CLAUDE.md          (this file)
├── SPEC.md            (full specification)
├── main.py            (FastAPI app — data pipeline, scoring, API endpoints)
├── data/
│   ├── supplier_orders.csv
│   ├── quality_inspections.csv
│   ├── rfq_responses.csv
│   └── supplier_notes.txt
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── requirements.txt
```

Keep it flat. No src/ directory, no nested packages, no build tools. One Python file for the backend, one HTML file, one CSS file, one JS file.
