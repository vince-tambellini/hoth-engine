# Architecture Diagrams

Go to [mermaid.live](https://mermaid.live), paste any diagram below into the left editor, then click the PNG or SVG export button to download a shareable image.

---

## System Architecture

```mermaid
graph TD
    User["🖥️ User opens browser<br/>http://127.0.0.1:8000"]

    User --> Input

    subgraph Frontend["Frontend — Single Page App"]
        direction TB
        Input["Text Input<br/>'I need 200 heat exchangers'"]
        Input --> RecCards
        RecCards["Recommendation Cards<br/>✅ Recommended &nbsp; 🔵 Alternative &nbsp; 🔴 Avoid"]
        RecCards --> ChatUI
        ChatUI["Follow-up Chat<br/>'Why not QuickFab?'"]
    end

    Input -- "POST /api/recommend" --> RecommendAPI
    ChatUI -- "POST /api/chat" --> ChatAPI

    subgraph Backend["Backend — Flask + Python"]
        direction TB

        subgraph Startup["Runs Once at Startup"]
            direction TB
            CSV["Load 4 Data Files"]
            CSV --> Clean["Entity Resolution<br/>Merge 4 Apex name variants into 1"]
            Clean --> JoinStep["Join Inspections → Orders<br/>Match on order_id + quantity"]
            JoinStep --> ScoreStep["Compute TCO Scores<br/>Per supplier, per part category"]
            ScoreStep --> BuildIndex["Build FAISS Vector Index<br/>Embed 13 part categories"]
        end

        RecommendAPI["POST /api/recommend"]
        ChatAPI["POST /api/chat"]
    end

    RecommendAPI -- "query vector" --> FAISS["FAISS Index<br/>all-MiniLM-L6-v2"]
    FAISS -- "matched category" --> RecommendAPI
    RecommendAPI -- "lookup scores" --> ScoreStep
    RecommendAPI -- "JSON" --> RecCards

    ChatAPI -- "scores + notes<br/>in system prompt" --> Claude["Anthropic Claude API<br/>claude-sonnet-4-20250514"]
    Claude -- "response" --> ChatAPI
    ChatAPI -- "JSON" --> ChatUI

    subgraph Data["Data Files"]
        direction TB
        D1["supplier_orders.csv<br/>500 purchase orders"]
        D2["quality_inspections.csv<br/>200 inspections"]
        D3["rfq_responses.csv<br/>92 quotes"]
        D4["supplier_notes.txt<br/>Team feedback"]
    end

    D1 --> CSV
    D2 --> CSV
    D3 --> CSV
    D4 --> CSV

    style Frontend fill:#f8f9fa,stroke:#dee2e6,stroke-width:2px
    style Backend fill:#e8f5e9,stroke:#a5d6a7,stroke-width:2px
    style Startup fill:#e3f2fd,stroke:#90caf9,stroke-width:2px
    style Data fill:#fff8e1,stroke:#ffe082,stroke-width:2px
    style Claude fill:#ede7f6,stroke:#b39ddb,stroke-width:2px
    style FAISS fill:#e3f2fd,stroke:#64b5f6,stroke-width:2px
```

---

## Recommendation Flow

```mermaid
graph TD
    A["User types:<br/>'200 aluminum heat exchangers'"]
    A --> B

    B["FAISS Vector Search<br/>Embed query with sentence-transformers<br/>Find nearest part category"]
    B --> C

    C["Matched Category: HX<br/>Heat Exchangers"]
    C --> D

    D["Find All Suppliers<br/>with HX order history"]
    D --> E

    E["Rank by TCO<br/>effective_cost = price × 1 + rej×0.5 + late×0.2"]
    E --> F

    F["Apply Specialist Tiebreaker<br/>From team notes and domain knowledge"]
    F --> G

    G["Return 3 Results"]
    G --> H["✅ Recommended<br/>Lowest true cost"]
    G --> I["🔵 Alternative<br/>Second best option"]
    G --> J["🔴 Avoid<br/>Highest true cost + warnings"]

    style A fill:#f8f9fa,stroke:#dee2e6,stroke-width:2px
    style B fill:#e3f2fd,stroke:#64b5f6,stroke-width:2px
    style C fill:#e8f5e9,stroke:#a5d6a7,stroke-width:2px
    style E fill:#fff3e0,stroke:#ffb74d,stroke-width:2px
    style H fill:#e8f5e9,stroke:#66bb6a,stroke-width:2px
    style I fill:#e3f2fd,stroke:#42a5f5,stroke-width:2px
    style J fill:#ffebee,stroke:#ef5350,stroke-width:2px
```

---

## TCO Formula Example: QuickFab on Heat Exchangers

```mermaid
graph TD
    Price["Unit Price<br/><b>$1,473</b>"]
    Rej["Rejection Penalty<br/>16.3% reject × 0.5 rework cost<br/><b>+ $120</b>"]
    Late["Late Delivery Penalty<br/>62.5% late × 0.2 delay cost<br/><b>+ $184</b>"]

    Price --> Total
    Rej --> Total
    Late --> Total

    Total["Effective Cost per Unit<br/><b>$1,777</b><br/>$304 more than sticker price"]

    Compare["Compare to Apex Manufacturing<br/>Unit Price: $1,627<br/>Effective Cost: <b>$1,648</b><br/>Looks more expensive, actually cheaper"]

    Total --> Compare

    style Price fill:#e8f5e9,stroke:#66bb6a,stroke-width:2px
    style Rej fill:#ffebee,stroke:#ef5350,stroke-width:2px
    style Late fill:#ffebee,stroke:#ef5350,stroke-width:2px
    style Total fill:#fce4ec,stroke:#e53935,stroke-width:3px
    style Compare fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
```
