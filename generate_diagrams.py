"""Generate architecture diagrams as PDFs."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def rounded_box(ax, x, y, w, h, text, facecolor="#f8f9fa", edgecolor="#dee2e6",
                fontsize=9, fontweight="normal", textcolor="#1a1a1a", lw=1.5, alpha=1.0):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                         facecolor=facecolor, edgecolor=edgecolor, lw=lw, alpha=alpha)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, fontweight=fontweight, color=textcolor,
            linespacing=1.5, family="sans-serif")

def arrow(ax, x1, y1, x2, y2, color="#888888"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5,
                                connectionstyle="arc3,rad=0"))

def section_box(ax, x, y, w, h, label, facecolor="#f8f9fa", edgecolor="#ccc"):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2",
                         facecolor=facecolor, edgecolor=edgecolor, lw=1.2, alpha=0.4)
    ax.add_patch(box)
    ax.text(x + 0.15, y + h - 0.15, label, ha="left", va="top",
            fontsize=8, fontweight="bold", color="#666", family="sans-serif")


# ---------------------------------------------------------------------------
# Diagram 1: System Architecture
# ---------------------------------------------------------------------------

def draw_system_architecture():
    fig, ax = plt.subplots(1, 1, figsize=(11, 14))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-0.5, 15.5)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Title
    ax.text(5, 15, "System Architecture", ha="center", va="center",
            fontsize=18, fontweight="bold", family="sans-serif", color="#1a1a1a")
    ax.text(5, 14.5, "Hoth Industries Supplier Recommendation Engine",
            ha="center", va="center", fontsize=11, color="#666", family="sans-serif")

    # --- User ---
    rounded_box(ax, 3, 13.2, 4, 0.7, "User Browser\nhttp://127.0.0.1:8000",
                facecolor="#e8eaf6", edgecolor="#7986cb", fontsize=9, fontweight="bold")

    arrow(ax, 5, 13.2, 5, 12.6)

    # --- Frontend section ---
    section_box(ax, 0.5, 10.3, 9, 2.5, "FRONTEND — HTML / CSS / JS",
                facecolor="#f3e5f5", edgecolor="#ce93d8")

    rounded_box(ax, 1.2, 11.6, 3, 0.7, "Text Input\n'I need 200 heat exchangers'",
                facecolor="#f3e5f5", edgecolor="#ba68c8", fontsize=8)
    rounded_box(ax, 5.5, 11.6, 3.5, 0.7, "Recommendation Cards\nRecommended | Alt | Avoid",
                facecolor="#f3e5f5", edgecolor="#ba68c8", fontsize=8)
    rounded_box(ax, 3, 10.6, 4, 0.6, "Follow-up Chat Interface",
                facecolor="#f3e5f5", edgecolor="#ba68c8", fontsize=8)

    arrow(ax, 4.2, 11.6, 5.5, 11.95)
    arrow(ax, 7.25, 11.6, 5, 11.1)

    # --- API arrows ---
    ax.text(2.2, 10.15, "POST /api/recommend", fontsize=7, color="#888", ha="center", family="sans-serif")
    arrow(ax, 2.7, 10.6, 2.7, 9.6)

    ax.text(7.8, 10.15, "POST /api/chat", fontsize=7, color="#888", ha="center", family="sans-serif")
    arrow(ax, 7.3, 10.6, 7.3, 9.6)

    # --- Backend section ---
    section_box(ax, 0.5, 3.5, 9, 6.3, "BACKEND — Flask (Python)",
                facecolor="#e8f5e9", edgecolor="#a5d6a7")

    # API endpoints
    rounded_box(ax, 1, 8.7, 3.5, 0.7, "Recommendation API\nPOST /api/recommend",
                facecolor="#c8e6c9", edgecolor="#66bb6a", fontsize=8, fontweight="bold")
    rounded_box(ax, 5.5, 8.7, 3.5, 0.7, "Chat API\nPOST /api/chat",
                facecolor="#c8e6c9", edgecolor="#66bb6a", fontsize=8, fontweight="bold")

    # FAISS
    rounded_box(ax, 1, 7.3, 3.5, 0.9, "FAISS Vector Index\nall-MiniLM-L6-v2\n13 part categories embedded",
                facecolor="#e3f2fd", edgecolor="#64b5f6", fontsize=8, fontweight="bold")

    arrow(ax, 2.75, 8.7, 2.75, 8.2)
    ax.text(3.4, 8.4, "vector\nsearch", fontsize=7, color="#666", family="sans-serif")

    # Score store
    rounded_box(ax, 5.5, 7.3, 3.5, 0.9, "TCO Score Store\nPer supplier, per category\neffective_cost = price ×\n(1 + rej×0.5 + late×0.2)",
                facecolor="#fff8e1", edgecolor="#ffd54f", fontsize=7.5)

    arrow(ax, 4.5, 7.75, 5.5, 7.75)
    ax.text(5, 7.95, "matched\ncategory", fontsize=7, color="#666", ha="center", family="sans-serif")

    # Startup pipeline
    section_box(ax, 1, 3.8, 8, 3.0, "DATA PIPELINE — Runs at Startup",
                facecolor="#e3f2fd", edgecolor="#90caf9")

    rounded_box(ax, 1.5, 5.6, 2.8, 0.6, "1. Load 4 CSVs",
                facecolor="#bbdefb", edgecolor="#64b5f6", fontsize=8)
    rounded_box(ax, 5, 5.6, 3.5, 0.6, "2. Entity Resolution\n4 Apex variants → 1",
                facecolor="#bbdefb", edgecolor="#64b5f6", fontsize=8)
    rounded_box(ax, 1.5, 4.5, 3.2, 0.6, "3. Join Inspections\norder_id + quantity",
                facecolor="#bbdefb", edgecolor="#64b5f6", fontsize=8)
    rounded_box(ax, 5.5, 4.5, 3, 0.6, "4. Compute TCO\nScore all suppliers",
                facecolor="#bbdefb", edgecolor="#64b5f6", fontsize=8)

    arrow(ax, 4.3, 5.9, 5, 5.9)
    arrow(ax, 2.9, 5.6, 2.9, 5.1)
    arrow(ax, 4.7, 4.8, 5.5, 4.8)
    arrow(ax, 7, 5.1, 7, 7.3)

    # --- Data sources ---
    section_box(ax, 0.5, 0.2, 4.5, 2.8, "DATA FILES",
                facecolor="#fff8e1", edgecolor="#ffe082")

    rounded_box(ax, 0.8, 2.0, 3.8, 0.5, "supplier_orders.csv — 500 orders",
                facecolor="#fff9c4", edgecolor="#ffd54f", fontsize=7.5)
    rounded_box(ax, 0.8, 1.4, 3.8, 0.5, "quality_inspections.csv — 200 rows",
                facecolor="#fff9c4", edgecolor="#ffd54f", fontsize=7.5)
    rounded_box(ax, 0.8, 0.8, 3.8, 0.5, "rfq_responses.csv — 92 quotes",
                facecolor="#fff9c4", edgecolor="#ffd54f", fontsize=7.5)
    rounded_box(ax, 0.8, 0.3, 3.8, 0.4, "supplier_notes.txt — Team feedback",
                facecolor="#fff9c4", edgecolor="#ffd54f", fontsize=7.5)

    arrow(ax, 2.9, 3.0, 2.9, 3.8)

    # --- Claude ---
    rounded_box(ax, 5.5, 1.0, 3.5, 1.2, "Anthropic Claude API\nclaude-sonnet-4-20250514\n\nScores + notes in\nsystem prompt",
                facecolor="#ede7f6", edgecolor="#9575cd", fontsize=8, fontweight="bold")

    arrow(ax, 7.3, 8.7, 7.3, 2.2)
    arrow(ax, 7.5, 2.2, 7.5, 8.7)
    ax.text(7.9, 5.5, "request ↓  response ↑", fontsize=7, color="#7e57c2",
            rotation=90, ha="center", va="center", family="sans-serif")

    plt.tight_layout()
    fig.savefig("diagrams/system_architecture.pdf", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    print("  OK system_architecture.pdf")


# ---------------------------------------------------------------------------
# Diagram 2: Recommendation Flow
# ---------------------------------------------------------------------------

def draw_recommendation_flow():
    fig, ax = plt.subplots(1, 1, figsize=(8, 14))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 15)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(4, 14.5, "Recommendation Flow", ha="center", va="center",
            fontsize=18, fontweight="bold", family="sans-serif", color="#1a1a1a")

    y = 13.2
    gap = 1.8

    # Step 1
    rounded_box(ax, 1.5, y, 5, 0.8, "User Input\n'200 aluminum heat exchangers, 4 weeks'",
                facecolor="#e8eaf6", edgecolor="#7986cb", fontsize=9, fontweight="bold")
    arrow(ax, 4, y, 4, y - 0.6)
    y -= gap

    # Step 2
    rounded_box(ax, 1.5, y, 5, 0.8, "FAISS Vector Search\nEmbed query → find nearest part category",
                facecolor="#e3f2fd", edgecolor="#64b5f6", fontsize=9)
    arrow(ax, 4, y, 4, y - 0.6)
    y -= gap

    # Step 3
    rounded_box(ax, 2, y, 4, 0.7, "Matched Category: HX\n(Heat Exchangers)",
                facecolor="#e8f5e9", edgecolor="#66bb6a", fontsize=9, fontweight="bold")
    arrow(ax, 4, y, 4, y - 0.6)
    y -= gap

    # Step 4
    rounded_box(ax, 1.5, y, 5, 0.8, "Find All Suppliers\nwith HX order history in the data",
                facecolor="#f3e5f5", edgecolor="#ba68c8", fontsize=9)
    arrow(ax, 4, y, 4, y - 0.6)
    y -= gap

    # Step 5
    rounded_box(ax, 1, y, 6, 1.0,
                "Rank by Total Cost of Ownership\n\neffective_cost = unit_price × (1 + rejection_rate × 0.5 + late_rate × 0.2)",
                facecolor="#fff3e0", edgecolor="#ff9800", fontsize=9, fontweight="bold")
    arrow(ax, 4, y, 4, y - 0.7)
    y -= gap + 0.2

    # Step 6
    rounded_box(ax, 1.5, y, 5, 0.7, "Apply Specialist Tiebreaker\nDomain expertise from team notes",
                facecolor="#fce4ec", edgecolor="#ef9a9a", fontsize=9)
    arrow(ax, 4, y, 4, y - 0.6)
    y -= gap

    # Results
    rounded_box(ax, 0.5, y + 0.05, 2, 0.7, "Recommended\nLowest true cost",
                facecolor="#e8f5e9", edgecolor="#2e7d32", fontsize=8.5, fontweight="bold", lw=2)
    rounded_box(ax, 3, y + 0.05, 2, 0.7, "Alternative\nSecond best",
                facecolor="#e3f2fd", edgecolor="#1565c0", fontsize=8.5, fontweight="bold", lw=2)
    rounded_box(ax, 5.5, y + 0.05, 2, 0.7, "Avoid\nHighest true cost",
                facecolor="#ffebee", edgecolor="#c62828", fontsize=8.5, fontweight="bold", lw=2)

    plt.tight_layout()
    fig.savefig("diagrams/recommendation_flow.pdf", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    print("  OK recommendation_flow.pdf")


# ---------------------------------------------------------------------------
# Diagram 3: TCO Formula
# ---------------------------------------------------------------------------

def draw_tco_formula():
    fig, ax = plt.subplots(1, 1, figsize=(9, 11))
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 12)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(4.5, 11.3, "TCO: Total Cost of Ownership", ha="center", va="center",
            fontsize=18, fontweight="bold", family="sans-serif", color="#1a1a1a")
    ax.text(4.5, 10.7, "Why the cheapest quote isn't always the cheapest supplier",
            ha="center", va="center", fontsize=10, color="#888", family="sans-serif")

    # Formula
    rounded_box(ax, 0.8, 9.2, 7.4, 0.9,
                "effective_cost  =  unit_price  ×  ( 1  +  rejection_rate × 0.5  +  late_rate × 0.2 )",
                facecolor="#fff3e0", edgecolor="#ff9800", fontsize=10, fontweight="bold", lw=2)

    # Factor explanations
    ax.text(4.5, 8.5, "What each factor means:", fontsize=10, fontweight="bold",
            ha="center", color="#444", family="sans-serif")

    rounded_box(ax, 0.5, 7.4, 3.5, 0.7,
                "Rejection × 0.5\nEach rejected part costs ~50%\nof unit price to rework/reorder",
                facecolor="#ffebee", edgecolor="#ef5350", fontsize=8)

    rounded_box(ax, 5, 7.4, 3.5, 0.7,
                "Late Rate × 0.2\nLate deliveries add ~20% in\nexpediting & missed deadlines",
                facecolor="#ffebee", edgecolor="#ef5350", fontsize=8)

    # Example header
    ax.text(4.5, 6.5, "Example: Heat Exchangers (HX)", fontsize=12, fontweight="bold",
            ha="center", color="#1a1a1a", family="sans-serif")

    # QuickFab example
    section_box(ax, 0.3, 3.8, 8.4, 2.3, "", facecolor="#ffebee", edgecolor="#ef5350")
    ax.text(4.5, 5.7, "QuickFab Industries — looks cheap, actually most expensive",
            fontsize=10, fontweight="bold", ha="center", color="#c62828", family="sans-serif")

    rounded_box(ax, 0.5, 4.6, 2.2, 0.6, "Unit Price\n$1,473",
                facecolor="#fff9c4", edgecolor="#ffd54f", fontsize=9, fontweight="bold")
    ax.text(2.9, 4.85, "+", fontsize=14, fontweight="bold", ha="center", color="#c62828")
    rounded_box(ax, 3.2, 4.6, 2.2, 0.6, "Rejection Penalty\n16.3% × 0.5 = +$120",
                facecolor="#ffcdd2", edgecolor="#ef5350", fontsize=8)
    ax.text(5.6, 4.85, "+", fontsize=14, fontweight="bold", ha="center", color="#c62828")
    rounded_box(ax, 5.9, 4.6, 2.5, 0.6, "Late Penalty\n62.5% × 0.2 = +$184",
                facecolor="#ffcdd2", edgecolor="#ef5350", fontsize=8)

    rounded_box(ax, 2.5, 3.9, 4, 0.5, "True Cost:  $1,777 / unit",
                facecolor="#ffcdd2", edgecolor="#c62828", fontsize=11, fontweight="bold", lw=2.5)

    # Apex example
    section_box(ax, 0.3, 1.3, 8.4, 2.1, "", facecolor="#e8f5e9", edgecolor="#66bb6a")
    ax.text(4.5, 3.1, "Apex Manufacturing — looks pricier, actually cheaper",
            fontsize=10, fontweight="bold", ha="center", color="#2e7d32", family="sans-serif")

    rounded_box(ax, 0.5, 2.1, 2.2, 0.6, "Unit Price\n$1,627",
                facecolor="#fff9c4", edgecolor="#ffd54f", fontsize=9, fontweight="bold")
    ax.text(2.9, 2.35, "+", fontsize=14, fontweight="bold", ha="center", color="#2e7d32")
    rounded_box(ax, 3.2, 2.1, 2.2, 0.6, "Rejection Penalty\n2.6% × 0.5 = +$21",
                facecolor="#c8e6c9", edgecolor="#66bb6a", fontsize=8)
    ax.text(5.6, 2.35, "+", fontsize=14, fontweight="bold", ha="center", color="#2e7d32")
    rounded_box(ax, 5.9, 2.1, 2.5, 0.6, "Late Penalty\n17.5% × 0.2 = +$57",
                facecolor="#c8e6c9", edgecolor="#66bb6a", fontsize=8)

    rounded_box(ax, 2.5, 1.4, 4, 0.5, "True Cost:  $1,705 / unit",
                facecolor="#c8e6c9", edgecolor="#2e7d32", fontsize=11, fontweight="bold", lw=2.5)

    # Savings callout
    rounded_box(ax, 2, 0.3, 5, 0.6,
                "Apex saves $72/unit vs QuickFab\ndespite $154 higher sticker price",
                facecolor="#e8eaf6", edgecolor="#5c6bc0", fontsize=9, fontweight="bold", lw=2)

    plt.tight_layout()
    fig.savefig("diagrams/tco_formula.pdf", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    print("  OK tco_formula.pdf")


# ---------------------------------------------------------------------------
# Generate all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    os.makedirs("diagrams", exist_ok=True)
    print("Generating diagrams...")
    draw_system_architecture()
    draw_recommendation_flow()
    draw_tco_formula()
    print("Done! PDFs saved to diagrams/")
