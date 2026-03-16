# Architecture Diagram

Paste the diagram below into [mermaid.live](https://mermaid.live) to get a shareable image (PNG/SVG).

## System Overview

```mermaid
graph TB
    subgraph User
        Browser["Browser (localhost:8000)"]
    end

    subgraph Frontend["Frontend — Static HTML/CSS/JS"]
        Input["Search Input<br/>'I need 200 heat exchangers'"]
        Cards["Recommendation Cards<br/>Recommended | Alternative | Avoid"]
        Chat["Follow-up Chat"]
    end

    subgraph Backend["Backend — Flask (Python)"]

        subgraph DataPipeline["Data Pipeline (runs at startup)"]
            Load["Load CSVs"]
            Normalize["Entity Resolution<br/>4 Apex name variants → 1"]
            Join["Inspection Join<br/>order_id + quantity match"]
            Score["TCO Scoring Engine<br/>effective_cost = price × (1 + rej×0.5 + late×0.2)"]
        end

        subgraph APIs["API Endpoints"]
            Recommend["POST /api/recommend"]
            ChatAPI["POST /api/chat"]
            Suppliers["GET /api/suppliers"]
            Health["GET /api/health"]
        end

        FAISS["FAISS Vector Index<br/>all-MiniLM-L6-v2<br/>13 part categories"]
    end

    subgraph DataSources["Data Sources (/data)"]
        Orders["supplier_orders.csv<br/>500 purchase orders"]
        Inspections["quality_inspections.csv<br/>200 inspections"]
        RFQ["rfq_responses.csv<br/>92 quotes"]
        Notes["supplier_notes.txt<br/>Team feedback"]
    end

    subgraph External["External Services"]
        Claude["Anthropic Claude API<br/>claude-sonnet-4-20250514"]
    end

    %% Data flow
    Orders --> Load
    Inspections --> Load
    RFQ --> Load
    Notes --> Load
    Load --> Normalize --> Join --> Score

    %% User flow
    Browser --> Input
    Input -->|"POST {part_type}"| Recommend
    Recommend -->|"vector search"| FAISS
    FAISS -->|"matched category"| Recommend
    Recommend -->|"lookup scores"| Score
    Recommend -->|"JSON response"| Cards

    Chat -->|"POST {message}"| ChatAPI
    ChatAPI -->|"system prompt + scores"| Claude
    Claude -->|"response"| ChatAPI
    ChatAPI -->|"JSON reply"| Chat

    %% Styling
    classDef data fill:#f9f9f9,stroke:#ccc
    classDef api fill:#e8f4e8,stroke:#4a4
    classDef external fill:#e8e8f4,stroke:#44a
    class Orders,Inspections,RFQ,Notes data
    class Recommend,ChatAPI,Suppliers,Health api
    class Claude external
```

## Recommendation Flow (Detail)

```mermaid
flowchart LR
    A["User types:<br/>'200 aluminum heat exchangers'"] --> B["FAISS vector search<br/>sentence-transformers"]
    B --> C["Matched category: HX"]
    C --> D["Lookup all suppliers<br/>with HX history"]
    D --> E["Rank by TCO<br/>effective_cost = price ×<br/>(1 + rej×0.5 + late×0.2)"]
    E --> F["Specialist tiebreaker"]
    F --> G["Return top 3:<br/>✅ Recommended<br/>🔵 Alternative<br/>🔴 Avoid"]
```

## TCO Formula

```mermaid
graph LR
    A["Unit Price<br/>$1,473"] --> D
    B["Rejection Rate<br/>16.3% × 0.5"] --> D
    C["Late Rate<br/>62.5% × 0.2"] --> D
    D["Effective Cost<br/>$1,473 × (1 + 0.082 + 0.125)<br/>= $1,777"]

    style A fill:#e8f4e8
    style B fill:#fde8e8
    style C fill:#fde8e8
    style D fill:#f4e8e8,stroke:#c44,stroke-width:2px
```
