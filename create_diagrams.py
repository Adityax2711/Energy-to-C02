"""
Script to generate clean, easy-to-understand visual architecture diagrams
for the Energy-to-CO2 Translation Engine PDF report.
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

os.makedirs("pdf_assets", exist_ok=True)

# -------------------------------------------------------------------------
# 1. End-to-End System Architecture Diagram (Simple Flowchart)
# -------------------------------------------------------------------------
def create_architecture_diagram():
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")

    # Title
    ax.text(5, 3.9, "HOW THE SYSTEM WORKS (END-TO-END DATA FLOW)", 
            ha="center", va="center", fontsize=13, fontweight="bold", color="#0F172A")

    # 6 Steps definitions: (x, y, title, subtitle, color, text_color)
    steps = [
        (0.2, 1.2, 1.4, 2.2, "1. SENSORS", "Measures computer\npower (Watts)\nevery second\n(psutil / AWS)", "#38BDF8", "#0C4A6E"),
        (1.8, 1.2, 1.4, 2.2, "2. SECURITY", "Shield blocks\nhackers, DDoS\n& bad inputs\n(OWASP A+)", "#F43F5E", "#881337"),
        (3.4, 1.2, 1.4, 2.2, "3. MATH", "Converts Watts\ninto energy\n(Watt-hours & kWh)\nTrapezoidal rule", "#F59E0B", "#78350F"),
        (5.0, 1.2, 1.4, 2.2, "4. CO2 ENGINE", "Calculates smoke\n& carbon based on\ncity power grid\n(gCO2e)", "#10B981", "#064E3B"),
        (6.6, 1.2, 1.4, 2.2, "5. AI BRAIN", "Predicts future load,\ndetects spikes &\nright-sizes chips\n(4 AI Engines)", "#8B5CF6", "#4C1D95"),
        (8.2, 1.2, 1.4, 2.2, "6. DASHBOARD", "Live web graphs,\nPrometheus metrics\n& verified audit\nledger for users", "#0EA5E9", "#0369A1"),
    ]

    for x, y, w, h, title, desc, col, text_col in steps:
        # Card shadow / background
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", 
                                     edgecolor=col, facecolor="#F8FAFC", linewidth=2)
        ax.add_patch(box)
        
        # Header banner inside box
        header = patches.FancyBboxPatch((x, y + h - 0.5), w, 0.5, boxstyle="round,pad=0.04",
                                        edgecolor=col, facecolor=col, linewidth=1)
        ax.add_patch(header)
        ax.text(x + w/2, y + h - 0.25, title, ha="center", va="center", 
                fontsize=8.5, fontweight="bold", color="white")
        
        # Body text
        ax.text(x + w/2, y + (h - 0.5)/2, desc, ha="center", va="center", 
                fontsize=7.5, color="#1E293B", linespacing=1.2)

    # Connecting Arrows
    for i in range(len(steps) - 1):
        x_start = steps[i][0] + steps[i][2] + 0.02
        x_end = steps[i+1][0] - 0.02
        y_mid = 2.0
        ax.annotate("", xy=(x_end, y_mid), xytext=(x_start, y_mid),
                    arrowprops=dict(arrowstyle="-|>", color="#64748B", lw=2, mutation_scale=12))

    # Bottom summary explanation
    summary_box = patches.FancyBboxPatch((0.2, 0.2), 9.6, 0.65, boxstyle="round,pad=0.05",
                                        edgecolor="#CBD5E1", facecolor="#F1F5F9", linewidth=1)
    ax.add_patch(summary_box)
    ax.text(5, 0.52, "SIMPLE SUMMARY: Raw Watts from servers enter on the left -> get filtered and converted -> AI optimizes -> User sees exact carbon & cost on the right.",
            ha="center", va="center", fontsize=8, fontweight="bold", color="#334155")

    plt.tight_layout()
    plt.savefig("pdf_assets/diagram_system_architecture.png", dpi=300)
    plt.close()
    print("Created pdf_assets/diagram_system_architecture.png")


# -------------------------------------------------------------------------
# 2. Regional Grid Comparison (Why City / Country Matters)
# -------------------------------------------------------------------------
def create_grid_comparison_diagram():
    fig, ax = plt.subplots(figsize=(9, 3.6), dpi=300)

    regions = [
        "Mumbai, India (Coal Heavy Grid)",
        "N. Virginia, USA (US-East Gas/Coal Mix)",
        "Frankfurt, Germany (European Mix)",
        "Oregon, USA (US-West Hydro River)",
        "Stockholm, Sweden (Hydro & Nuclear)"
    ]
    emissions = [708.2, 380.5, 330.0, 110.0, 45.0]
    colors_list = ["#EF4444", "#F97316", "#EAB308", "#3B82F6", "#10B981"]

    y_pos = np.arange(len(regions))
    bars = ax.barh(y_pos, emissions, color=colors_list, height=0.55, edgecolor="#334155", linewidth=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(regions, fontsize=8.5, fontweight="bold", color="#1E293B")
    ax.invert_yaxis()  # Top to bottom
    ax.set_xlabel("Carbon Pollution (Grams of CO2 emitted per 1 kWh of electricity)", fontsize=9, fontweight="bold", color="#0F172A")
    ax.set_title("WHY LOCATION MATTERS: The Same Server Burns Drastically Different Carbon in Each Region", fontsize=10.5, fontweight="bold", color="#0F172A", pad=12)

    # Add data values at the end of each bar
    for bar, val in zip(bars, emissions):
        pct = ""
        if val == 45.0:
            pct = " (88.2% LESS CARBON!)"
        ax.text(val + 12, bar.get_y() + bar.get_height()/2, f"{val:.1f} g/kWh{pct}", 
                va="center", fontsize=8, fontweight="bold", color="#1E293B")

    ax.set_xlim(0, 950)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig("pdf_assets/diagram_grid_emissions.png", dpi=300)
    plt.close()
    print("Created pdf_assets/diagram_grid_emissions.png")


# -------------------------------------------------------------------------
# 3. Hardware Comparison (Old Intel/AMD vs Green AWS Graviton3)
# -------------------------------------------------------------------------
def create_hardware_diagram():
    fig, ax = plt.subplots(figsize=(9, 3.5), dpi=300)

    instances = ["Legacy Intel (c6i.4xlarge)", "AMD EPYC (m6a.4xlarge)", "AWS Graviton3 ARM (c7g.4xlarge)"]
    idle_watts = [45.0, 48.0, 24.0]
    peak_watts = [220.0, 240.0, 115.0]

    x = np.arange(len(instances))
    width = 0.32

    rects1 = ax.bar(x - width/2, idle_watts, width, label="Idle Power (Watts)", color="#94A3B8", edgecolor="#334155")
    rects2 = ax.bar(x + width/2, peak_watts, width, label="Maximum Peak Power (Watts)", color="#0284C7", edgecolor="#0F172A")

    # Highlight Graviton3
    rects2[2].set_color("#10B981")
    rects1[2].set_color("#6EE7B7")

    ax.set_ylabel("Power Consumption (Watts)", fontsize=9, fontweight="bold", color="#0F172A")
    ax.set_title("HARDWARE EFFICIENCY: Older Intel/AMD vs Modern Green AWS Graviton3 ARM", fontsize=10.5, fontweight="bold", color="#0F172A", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(instances, fontsize=8.5, fontweight="bold", color="#1E293B")
    ax.legend(frameon=True, facecolor="#F8FAFC", edgecolor="#CBD5E1", fontsize=8)
    ax.set_ylim(0, 280)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Values on top of bars
    for rect in rects1:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2, h + 5, f"{h:.0f}W", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    for rect in rects2:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2, h + 5, f"{h:.0f}W", ha="center", va="bottom", fontsize=7.5, fontweight="bold")

    # Big highlight arrow
    ax.annotate("48% Less Electricity!", xy=(2.16, 125), xytext=(2.16, 185),
                arrowprops=dict(arrowstyle="->", color="#059669", lw=2),
                ha="center", fontsize=8.5, fontweight="bold", color="#059669",
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="#10B981", facecolor="#ECFDF5"))

    plt.tight_layout()
    plt.savefig("pdf_assets/diagram_hardware_comparison.png", dpi=300)
    plt.close()
    print("Created pdf_assets/diagram_hardware_comparison.png")


# -------------------------------------------------------------------------
# 4. The 4 AI Engines Diagram (AI Suite)
# -------------------------------------------------------------------------
def create_ai_suite_diagram():
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.8)
    ax.axis("off")

    ax.text(5, 3.5, "THE 4 AI ENGINES (SMART AUTOMATION SUITE)", 
            ha="center", va="center", fontsize=12, fontweight="bold", color="#0F172A")

    ai_engines = [
        (0.2, 0.4, 2.2, 2.7, "P1: FORECASTER", "Predicts future 24h power\n& finds 'Green Windows'\n(best times to run jobs\nwhen solar/wind is high)", "#0284C7"),
        (2.65, 0.4, 2.2, 2.7, "P2: ANOMALY ALARM", "Catches rogue CPU spikes,\nmemory leaks & mining\ninstantly using Z-score\n& gradient math", "#EF4444"),
        (5.1, 0.4, 2.2, 2.7, "P3: RIGHT-SIZER", "Shows how much money\n& carbon you save by\nmoving to AWS Graviton3\nARM microprocessors", "#10B981"),
        (7.55, 0.4, 2.2, 2.7, "P4: AI COPILOT", "A smart chatbot you can\nask questions in plain\nEnglish like 'Show me our\ncarbon report for today'", "#8B5CF6")
    ]

    for x, y, w, h, title, desc, col in ai_engines:
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", 
                                     edgecolor=col, facecolor="#F8FAFC", linewidth=2)
        ax.add_patch(box)
        
        header = patches.FancyBboxPatch((x, y + h - 0.5), w, 0.5, boxstyle="round,pad=0.04",
                                        edgecolor=col, facecolor=col, linewidth=1)
        ax.add_patch(header)
        ax.text(x + w/2, y + h - 0.25, title, ha="center", va="center", 
                fontsize=8.5, fontweight="bold", color="white")
        
        ax.text(x + w/2, y + (h - 0.5)/2, desc, ha="center", va="center", 
                fontsize=7.8, color="#1E293B", linespacing=1.3)

    plt.tight_layout()
    plt.savefig("pdf_assets/diagram_ai_suite.png", dpi=300)
    plt.close()
    print("Created pdf_assets/diagram_ai_suite.png")


if __name__ == "__main__":
    create_architecture_diagram()
    create_grid_comparison_diagram()
    create_hardware_diagram()
    create_ai_suite_diagram()
    print("All diagrams generated successfully!")
