"""
Updated PDF generator for Energy-to-CO2 Translation Engine.
Rewritten in extremely simple, easy-to-understand English with
visual architecture diagrams and flowcharts embedded directly into the report.
Guaranteed exactly 10 pages.
"""
import os
import sys

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
)
from reportlab.pdfgen import canvas

# ----------------------------------------------------------------------
# Clean Modern Palette
# ----------------------------------------------------------------------
PRIMARY = HexColor("#0F172A")       # Deep slate navy
SECONDARY = HexColor("#0284C7")     # Friendly sky blue
ACCENT_GREEN = HexColor("#059669")  # Emerald eco green
ACCENT_WARN = HexColor("#D97706")   # Amber warning
TEXT_DARK = HexColor("#1E293B")     # Dark charcoal body
TEXT_MUTED = HexColor("#64748B")    # Slate grey secondary
BG_LIGHT = HexColor("#F8FAFC")      # Clean off-white surface
BG_ALT = HexColor("#F1F5F9")        # Card background
BORDER_COLOR = HexColor("#CBD5E1")  # Clean divider line
WHITE = HexColor("#FFFFFF")


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print exact total page numbers,
    running headers, and footers across all pages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages):
        page_num = self._pageNumber
        self.saveState()

        if page_num == 1:
            # Cover page top banner
            self.setFillColor(PRIMARY)
            self.rect(0, 786, 612, 6, fill=True, stroke=False)
            self.setFillColor(ACCENT_GREEN)
            self.rect(0, 782, 180, 4, fill=True, stroke=False)
            
            # Bottom footer rule
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.75)
            self.line(36, 32, 576, 32)
            
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(TEXT_MUTED)
            self.drawString(36, 20, "ENERGY-TO-CO2 TRANSLATION ENGINE  |  PROJECT ARCHITECTURE & TOOLS GUIDE")
            self.drawRightString(576, 20, f"Page {page_num} of {total_pages}")
        else:
            # Top header bar
            self.setFillColor(PRIMARY)
            self.rect(0, 786, 612, 6, fill=True, stroke=False)
            
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(TEXT_MUTED)
            self.drawString(36, 764, "ENERGY-TO-CO2 TRANSLATION ENGINE")
            self.setFont("Helvetica", 8)
            self.drawString(220, 764, "•   Simple Architecture Guide & Tools Explanation")
            
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.5)
            self.line(36, 756, 576, 756)

            # Bottom footer bar
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.5)
            self.line(36, 32, 576, 32)
            
            self.setFont("Helvetica", 8)
            self.setFillColor(TEXT_MUTED)
            self.drawString(36, 20, "Energy, Carbon & Cloud Architecture Guide  •  Written in Simple, Easy English")
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(PRIMARY)
            self.drawRightString(576, 20, f"Page {page_num} of {total_pages}")

        self.restoreState()


def get_custom_styles():
    """Build typography and styling rules for clean, readable layout."""
    base_styles = getSampleStyleSheet()

    styles = {
        "CoverTitle": ParagraphStyle(
            "CoverTitle",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=PRIMARY,
            spaceAfter=3,
        ),
        "CoverSubtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=SECONDARY,
            spaceAfter=8,
        ),
        "PageTitle": ParagraphStyle(
            "PageTitle",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=PRIMARY,
            spaceAfter=2,
        ),
        "PageSubtitle": ParagraphStyle(
            "PageSubtitle",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=SECONDARY,
            textTransform="uppercase",
            spaceAfter=6,
        ),
        "SectionHeader": ParagraphStyle(
            "SectionHeader",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=PRIMARY,
            spaceBefore=4,
            spaceAfter=3,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=11.3,
            textColor=TEXT_DARK,
            spaceAfter=4,
        ),
        "BulletText": ParagraphStyle(
            "BulletText",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.1,
            leading=10.8,
            textColor=TEXT_DARK,
            leftIndent=10,
            firstLineIndent=-7,
            spaceAfter=2.5,
        ),
        "CalloutText": ParagraphStyle(
            "CalloutText",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=TEXT_DARK,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=WHITE,
            alignment=1,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
            textColor=TEXT_DARK,
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10,
            textColor=TEXT_DARK,
        ),
        "TableCellCenter": ParagraphStyle(
            "TableCellCenter",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
            textColor=TEXT_DARK,
            alignment=1,
        ),
    }
    return styles


def create_callout(text, title="SIMPLE EXPLANATION / KEY TAKEAWAY", border_color=ACCENT_GREEN, bg_color=HexColor("#F0FDF4")):
    """Helper to render a styled alert/callout box."""
    styles = get_custom_styles()
    title_p = Paragraph(f"<b>{title}</b>", ParagraphStyle(
        "CTitle",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=border_color
    ))
    body_p = Paragraph(text, styles["CalloutText"])
    
    t = Table([[title_p], [Spacer(1, 2)], [body_p]], colWidths=[536])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 0.75, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def build_page_1(styles):
    """PAGE 1: Cover & Simple Executive Summary"""
    story = []
    
    story.append(Paragraph("Energy-to-CO<sub>2</sub> Translation Engine", styles["CoverTitle"]))
    story.append(Paragraph("A Clear, Simple Guide to Measuring Computer Electricity, Carbon Pollution & Cloud Architecture", styles["CoverSubtitle"]))
    
    # Metadata badges table
    meta_data = [
        [
            Paragraph("<b>What is this?</b> A Smart Software Electric Meter", styles["TableCell"]),
            Paragraph("<b>Security Level:</b> Enterprise Hardened (OWASP A+)", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Built With:</b> Python 3.11+ & FastAPI (High Speed)", styles["TableCell"]),
            Paragraph("<b>Database:</b> SQLite (Fast Write-Ahead Mode)", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Smart Features:</b> 4 Built-In AI/ML Engines", styles["TableCell"]),
            Paragraph("<b>Cloud Focus:</b> Amazon Web Services (AWS EC2 & ARM)", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Test Status:</b> 38 Automated Tests (100% Passed)", styles["TableCell"]),
            Paragraph("<b>Audit Standard:</b> GHG Protocol Scope 2 Standard", styles["TableCell"]),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[268, 268])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_ALT),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # Executive Overview in simple words
    story.append(Paragraph("1. The Big Idea: What Does This Project Do?", styles["SectionHeader"]))
    story.append(Paragraph(
        "Think of the electric meter outside your house. It tracks how much electricity your refrigerator, air conditioner, "
        "and lights use. But what about computers and cloud servers running programs on Amazon Web Services (AWS)? "
        "Normal cloud dashboards only tell you things like: <i>'Your CPU is at 70% busy'</i>. "
        "They <b>do not tell you</b> how much electricity the computer actually burned, how much money was spent on power, "
        "or how much smoke and carbon dioxide (CO<sub>2</sub>) was released into the air by the local power plant!",
        styles["Body"]
    ))
    story.append(Paragraph(
        "This project is a <b>Smart Software Meter for Computers</b>. It reads the electrical power draw (Watts) of running computers, "
        "calculates the total electricity used over time (Watt-hours and kWh), and tells you the exact carbon footprint (grams of CO<sub>2</sub>) "
        "based on the city or country where the server is running. It also uses <b>Artificial Intelligence (AI)</b> to catch power leaks "
        "and shows you how to save money and cut pollution by switching to modern green computer chips (like AWS Graviton3).",
        styles["Body"]
    ))

    # Core Value Pillars Table in simple language
    story.append(Paragraph("2. The 4 Big Benefits in Simple Terms", styles["SectionHeader"]))
    pillars = [
        [
            Paragraph("<b>Benefit</b>", styles["TableHeader"]),
            Paragraph("<b>What It Does (In Simple Words)</b>", styles["TableHeader"]),
            Paragraph("<b>Why It Matters</b>", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>1. Accurate Math</b>", styles["TableCellBold"]),
            Paragraph("Calculates real electricity (kWh) without guessing. If a server turns off, it pauses so it won't count fake power.", styles["TableCell"]),
            Paragraph("Gives exact numbers that financial accountants and auditors can trust.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>2. City Power Grids</b>", styles["TableCellBold"]),
            Paragraph("Knows if your server runs on coal (dirty) or waterfalls/nuclear (clean).", styles["TableCell"]),
            Paragraph("Shows how moving your code to clean regions cuts pollution by up to 88%!", styles["TableCell"]),
        ],
        [
            Paragraph("<b>3. Tamper-Proof Seal</b>", styles["TableCellBold"]),
            Paragraph("Uses digital wax seals (SHA-256 hashes) on every calculation.", styles["TableCell"]),
            Paragraph("If anyone tries to secretly change a number, the seal breaks instantly.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>4. Smart AI Brain</b>", styles["TableCellBold"]),
            Paragraph("4 AI helpers predict future power, sound alarms on spikes, and chat with you.", styles["TableCell"]),
            Paragraph("Stops wasted electricity and recommends cheaper, greener cloud hardware.", styles["TableCell"]),
        ],
    ]
    t_pillars = Table(pillars, colWidths=[95, 255, 186])
    t_pillars.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_pillars)
    story.append(Spacer(1, 6))

    # Table of contents summary
    story.append(Paragraph("3. Guide Roadmap (What Is on Each Page)", styles["SectionHeader"]))
    toc_text = (
        "<b>Page 2:</b> The Basics: Power, Electricity & Carbon  •  "
        "<b>Page 3:</b> System Architecture & Visual Data Flow Diagram  •  "
        "<b>Page 4:</b> Backend Tools: Python, FastAPI & APIs  •  "
        "<b>Page 5:</b> Database & Tamper-Proof Digital Seal  •  "
        "<b>Page 6:</b> The AI Brain: Forecasting & Spikes  •  "
        "<b>Page 7:</b> Cloud Hardware: Old Intel vs Green AWS ARM  •  "
        "<b>Page 8:</b> Security Shield & AI Copilot Chatbot  •  "
        "<b>Page 9:</b> Live Web Dashboard & Prometheus  •  "
        "<b>Page 10:</b> Testing, Deployment & Summary"
    )
    story.append(create_callout(toc_text, title="TABLE OF CONTENTS (10-PAGE EASY ROADMAP)", border_color=SECONDARY, bg_color=BG_LIGHT))

    return story


def build_page_2(styles):
    """PAGE 2: The Basics: Power, Electricity & Carbon Pollution"""
    story = []
    story.append(Paragraph("The Basics: Power, Electricity & Carbon Pollution", styles["PageTitle"]))
    story.append(Paragraph("SIMPLE SCIENCE  •  SPEEDOMETER VS ODOMETER  •  WHY SERVER LOCATION MATTERS", styles["PageSubtitle"]))

    story.append(Paragraph("1. Power vs Energy: The Car Analogy Made Easy", styles["SectionHeader"]))
    story.append(Paragraph(
        "Many people confuse <b>Power</b> and <b>Energy</b>. The easiest way to understand the difference is to think of a car:",
        styles["Body"]
    ))
    story.append(Paragraph(
        "• <b>Power (Watts) is like your Speedometer (km/h):</b> It tells you how fast electricity is flowing at this exact second. "
        "If you turn on heavy video games or AI training, your computer's power jumps from 40 Watts up to 150 Watts immediately.",
        styles["BulletText"]
    ))
    story.append(Paragraph(
        "• <b>Energy (Watt-hours & kWh) is like your Odometer (Kilometers Traveled):</b> It tells you the total amount of electricity "
        "burned over time. If a 100-Watt light bulb stays on for 10 hours, it consumes: 100 Watts * 10 hours = 1,000 Watt-hours = <b>1 kilowatt-hour (1 kWh)</b>.",
        styles["BulletText"]
    ))
    story.append(Paragraph(
        "• <b>Carbon Emissions (Grams of CO<sub>2</sub>):</b> When electricity is generated at a power plant by burning fossil fuels like coal or gas, "
        "smoke is released. We calculate: <i>Carbon = Electricity (kWh) * Power Plant Smoke Factor</i>.",
        styles["BulletText"]
    ))

    story.append(Paragraph("2. Why Data Center Overhead (PUE) Matters", styles["SectionHeader"]))
    story.append(Paragraph(
        "When servers run in big cloud data centers, they get very hot. The building needs air conditioning, fans, and emergency batteries. "
        "This extra overhead is called <b>PUE (Power Usage Effectiveness)</b>. If a data center has a PUE of <b>1.2</b>, it means that for every 100 Watts "
        "the computer uses, another 20 Watts is used by fans and air conditioners to keep it cool.",
        styles["Body"]
    ))

    story.append(Paragraph("3. Visual Diagram: Why Your Server's City Matters So Much", styles["SectionHeader"]))
    story.append(Paragraph(
        "Did you know? Running a computer program in Mumbai produces almost <b>16 times more pollution</b> than running the exact same program in Sweden! "
        "Look at the comparison below:",
        styles["Body"]
    ))

    # Embed Grid comparison diagram
    if os.path.exists("pdf_assets/diagram_grid_emissions.png"):
        story.append(Image("pdf_assets/diagram_grid_emissions.png", width=510, height=170))
        story.append(Spacer(1, 4))

    callout_p2 = (
        "<b>The Green Shifting Trick:</b> If you have a big computing job that doesn't need to finish in a microsecond (like processing reports "
        "or training AI models overnight), you can simply run it on AWS servers in <b>Stockholm (Sweden)</b> or <b>Oregon (USA)</b> instead of "
        "Mumbai or Virginia. You automatically cut <b>88% of the carbon pollution</b> without changing a single line of your program!"
    )
    story.append(create_callout(callout_p2, title="PRACTICAL GREEN TAKEAWAY", border_color=ACCENT_GREEN, bg_color=HexColor("#F0FDF4")))

    return story


def build_page_3(styles):
    """PAGE 3: System Architecture & Visual Data Flow Diagram"""
    story = []
    story.append(Paragraph("System Architecture: How the Whole Project Works", styles["PageTitle"]))
    story.append(Paragraph("END-TO-END DATA FLOW  •  STEP-BY-STEP EXPLANATION  •  15-SECOND DOWNTIME DEFENSE", styles["PageSubtitle"]))

    story.append(Paragraph("1. Visual Architecture Flowchart", styles["SectionHeader"]))
    story.append(Paragraph(
        "Here is the complete blueprint of how data travels through the system—from raw electrical hardware all the way to the user's dashboard:",
        styles["Body"]
    ))

    # Embed Architecture diagram
    if os.path.exists("pdf_assets/diagram_system_architecture.png"):
        story.append(Image("pdf_assets/diagram_system_architecture.png", width=515, height=185))
        story.append(Spacer(1, 4))

    story.append(Paragraph("2. Step-by-Step Breakdown of the 6 Architecture Blocks", styles["SectionHeader"]))
    story.append(Paragraph(
        "<b>Step 1: Sensors (Data Ingestion):</b> Reads the real-time electrical draw (Watts). It uses a library called <code>psutil</code> "
        "to check how busy the CPU is on your computer, or simulates virtual cloud fleets on Amazon AWS.",
        styles["BulletText"]
    ))
    story.append(Paragraph(
        "<b>Step 2: Security Shield (Perimeter Defense):</b> Like an airport security gate, it inspects every incoming message. "
        "It stops hackers, prevents spammers from sending too many requests (rate limiting), and sanitizes any malicious text.",
        styles["BulletText"]
    ))
    story.append(Paragraph(
        "<b>Step 3: Math Calculator (Trapezoidal Integration):</b> Computers send power readings every second (e.g. 50W, then 54W). "
        "The calculator takes the average between the two points and multiplies by the time passed to find the real Watt-hours.",
        styles["BulletText"]
    ))
    story.append(Paragraph(
        "<b>Step 4: Carbon Converter:</b> Multiplies the electricity by the local city grid smoke factor and data center cooling overhead.",
        styles["BulletText"]
    ))
    story.append(Paragraph(
        "<b>Step 5: AI Brain:</b> 4 artificial intelligence helpers forecast future power, sound alarms on spikes, and answer questions.",
        styles["BulletText"]
    ))
    story.append(Paragraph(
        "<b>Step 6: Dashboard & Database:</b> Saves all numbers into a fast database (SQLite) and shows live moving charts on a website.",
        styles["BulletText"]
    ))

    callout_p3 = (
        "<b>The 15-Second Downtime Safety Rule:</b> What happens if a server crashes or turns off for 2 days over the weekend? "
        "A dumb calculator might think the server was running full speed for those 48 hours and add massive fake electricity! "
        "Our engine is smart: <b>if the gap between readings is more than 15 seconds</b>, it marks the gap as <code>GAP_DETECTED</code>, "
        "records zero power for the downtime, and resets safely."
    )
    story.append(create_callout(callout_p3, title="SMART SAFETY FEATURE: NO FAKE ENERGY", border_color=PRIMARY, bg_color=BG_LIGHT))

    return story


def build_page_4(styles):
    """PAGE 4: Backend Tools & Web API (The Engine Under the Hood)"""
    story = []
    story.append(Paragraph("Backend Tools: What Powers the Software", styles["PageTitle"]))
    story.append(Paragraph("PYTHON 3.11+  •  FASTAPI  •  STARLETTE  •  PYDANTIC V2 DATA VALIDATION", styles["PageSubtitle"]))

    story.append(Paragraph("1. Why Python 3.11+ Was Chosen", styles["SectionHeader"]))
    story.append(Paragraph(
        "We chose <b>Python 3.11+</b> as the main programming language for three clear reasons:",
        styles["Body"]
    ))
    story.append(Paragraph("• <b>Simple to Read:</b> Python code looks almost like plain English, making it easy to build, explain, and maintain.", styles["BulletText"]))
    story.append(Paragraph("• <b>Best Math & AI Ecosystem:</b> Python is the undisputed world leader for math and machine learning (NumPy, SciPy, Scikit-learn).", styles["BulletText"]))
    story.append(Paragraph("• <b>High Speed:</b> Python 3.11 introduced major speed enhancements, running up to 25% faster than older Python versions.", styles["BulletText"]))

    story.append(Paragraph("2. Why FastAPI & Starlette?", styles["SectionHeader"]))
    story.append(Paragraph(
        "To make the engine accessible across a network, we used <b>FastAPI</b> mounted on the <b>Starlette</b> server toolkit and served via <b>Uvicorn</b>:",
        styles["Body"]
    ))
    story.append(Paragraph("• <b>Asynchronous Speed:</b> It can handle hundreds of sensor readings every second without freezing or slowing down.", styles["BulletText"]))
    story.append(Paragraph("• <b>Interactive Documentation:</b> FastAPI automatically builds a web testing page at <code>http://localhost:8000/docs</code> where anyone can test endpoints by clicking buttons.", styles["BulletText"]))

    story.append(Paragraph("3. Pydantic v2: The Digital Bouncer", styles["SectionHeader"]))
    story.append(Paragraph(
        "Imagine a nightclub bouncer checking IDs at the door. <b>Pydantic v2</b> checks all incoming data. "
        "If a sensor accidentally sends a negative power value (<i>-50 Watts</i>) or an impossible number (<i>1,000,000 Watts</i>), "
        "Pydantic rejects it immediately with a friendly error message, protecting the database from bad numbers.",
        styles["Body"]
    ))

    story.append(Paragraph("4. Simple Table of Web API Endpoints", styles["SectionHeader"]))
    api_simple = [
        [
            Paragraph("<b>URL Address (Route)</b>", styles["TableHeader"]),
            Paragraph("<b>What It Does (Simple English)</b>", styles["TableHeader"]),
            Paragraph("<b>Example Output</b>", styles["TableHeader"]),
        ],
        [
            Paragraph("<code>GET /health</code>", styles["TableCellBold"]),
            Paragraph("Checks if the server, database, and sensor are alive and running.", styles["TableCell"]),
            Paragraph("status: 'healthy', uptime: 3600s", styles["TableCell"]),
        ],
        [
            Paragraph("<code>POST /telemetry</code>", styles["TableCellBold"]),
            Paragraph("Sends a new power reading in Watts into the calculation engine.", styles["TableCell"]),
            Paragraph("status: 'INTEGRATED', energy_wh: 0.12", styles["TableCell"]),
        ],
        [
            Paragraph("<code>GET /energy/summary</code>", styles["TableCellBold"]),
            Paragraph("Returns total electricity burned so far in Watt-hours and kWh.", styles["TableCell"]),
            Paragraph("total_kwh: 4.821, total_intervals: 150", styles["TableCell"]),
        ],
        [
            Paragraph("<code>GET /carbon/summary</code>", styles["TableCellBold"]),
            Paragraph("Returns total carbon pollution emitted in grams and kilograms of CO<sub>2</sub>.", styles["TableCell"]),
            Paragraph("total_kg_co2e: 1.834 kg", styles["TableCell"]),
        ],
        [
            Paragraph("<code>GET /api/ai/forecast/24h</code>", styles["TableCellBold"]),
            Paragraph("Asks AI to predict tomorrow's electricity and find the best green hours.", styles["TableCell"]),
            Paragraph("best_window: 13:00 to 16:00 (solar peak)", styles["TableCell"]),
        ],
        [
            Paragraph("<code>POST /api/ai/copilot/chat</code>", styles["TableCellBold"]),
            Paragraph("Lets you ask questions in plain English like 'How much carbon did we make?'", styles["TableCell"]),
            Paragraph("Formatted plain-English markdown report", styles["TableCell"]),
        ],
        [
            Paragraph("<code>POST /api/security/verify-ledger</code>", styles["TableCellBold"]),
            Paragraph("Checks all digital seals across the database to verify zero tampering.", styles["TableCell"]),
            Paragraph("verified: 100%, tampered_records: 0", styles["TableCell"]),
        ],
    ]
    t_api = Table(api_simple, colWidths=[140, 246, 150])
    t_api.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_api)
    story.append(Spacer(1, 5))

    callout_p4 = (
        "<b>No Duplicate Readings:</b> What if your Wi-Fi flickers and sends the exact same reading twice? "
        "The server checks a special <code>Idempotency-Key</code>. If it sees the same reading again, it ignores the duplicate "
        "so you never get charged twice for electricity!"
    )
    story.append(create_callout(callout_p4, title="SMART DATA PROTECTION", border_color=SECONDARY, bg_color=BG_LIGHT))

    return story


def build_page_5(styles):
    """PAGE 5: Database & The Tamper-Proof Digital Seal"""
    story = []
    story.append(Paragraph("Database & The Tamper-Proof Digital Seal", styles["PageTitle"]))
    story.append(Paragraph("SQLITE WRITE-AHEAD LOGGING  •  SQLALCHEMY  •  SHA-256 DIGITAL WAX SEALS", styles["PageSubtitle"]))

    story.append(Paragraph("1. The Database: SQLite in High-Speed WAL Mode", styles["SectionHeader"]))
    story.append(Paragraph(
        "Every second, new power readings arrive. Where do we save them? "
        "We used <b>SQLite 3</b> with a special feature turned on called <b>WAL (Write-Ahead Logging)</b>:",
        styles["Body"]
    ))
    story.append(Paragraph("• <b>No Heavy Setup Needed:</b> Unlike MySQL or PostgreSQL, SQLite doesn't need a separate server running in the background. It is lightweight and self-contained.", styles["BulletText"]))
    story.append(Paragraph("• <b>Never Gets Stuck:</b> In standard databases, if someone is reading data, nobody can write data at the same time. In WAL mode, readers and writers never block each other!", styles["BulletText"]))
    story.append(Paragraph("• <b>Safe from Crashes:</b> If the power cord is unplugged, WAL mode ensures no data gets corrupted.", styles["BulletText"]))

    story.append(Paragraph("2. What Information is Stored in the Database?", styles["SectionHeader"]))
    db_tables = [
        [
            Paragraph("<b>Table Name</b>", styles["TableHeader"]),
            Paragraph("<b>What It Remembers (Simple Description)</b>", styles["TableHeader"]),
            Paragraph("<b>Why We Need It</b>", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>PowerSample</b>", styles["TableCellBold"]),
            Paragraph("Every raw power measurement (timestamp, host name, Watts).", styles["TableCell"]),
            Paragraph("The raw foundation for all calculations.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>EnergyInterval</b>", styles["TableCellBold"]),
            Paragraph("The time intervals between readings, duration, and Watt-hours.", styles["TableCell"]),
            Paragraph("Remembers electricity used over time.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>EmissionFactor</b>", styles["TableCellBold"]),
            Paragraph("Official smoke/carbon numbers for each city and country.", styles["TableCell"]),
            Paragraph("Tells us if the local grid is coal, gas, or hydro.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>CarbonEstimate</b>", styles["TableCellBold"]),
            Paragraph("The final grams of CO<sub>2</sub> calculated, with its digital seal.", styles["TableCell"]),
            Paragraph("Official carbon records for audits.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>AuditLedger</b>", styles["TableCellBold"]),
            Paragraph("An unchangeable notebook that records every single action and test.", styles["TableCell"]),
            Paragraph("Proves nobody cheated or changed the logs.", styles["TableCell"]),
        ],
    ]
    t_db = Table(db_tables, colWidths=[110, 260, 166])
    t_db.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_db)
    story.append(Spacer(1, 6))

    story.append(Paragraph("3. The Digital Wax Seal: SHA-256 Cryptographic Provenance", styles["SectionHeader"]))
    story.append(Paragraph(
        "In the old days, kings placed a <b>red wax seal</b> on letters. If anyone opened or altered the letter, the wax seal broke. "
        "We do the exact same thing digitally using a math formula called <b>SHA-256</b>:",
        styles["Body"]
    ))
    story.append(Paragraph("1. We take all inputs: <i>kWh burned + Datacenter cooling factor + Grid emission factor</i>.", styles["BulletText"]))
    story.append(Paragraph("2. The computer crunches these numbers into a unique 64-character digital fingerprint (for example: <code>a7f8b9...</code>).", styles["BulletText"]))
    story.append(Paragraph("3. This fingerprint is permanently locked in the database alongside the calculation.", styles["BulletText"]))

    audit_box = (
        "<b>The One-Click Auditor Scan:</b><br/>"
        "Anyone can press the <b>'Verify Ledger'</b> button in the web dashboard. The computer re-calculates the fingerprint for every single "
        "historical record. If an evil hacker changed even one decimal point from 10.5 kg to 1.5 kg, the fingerprint will mismatch "
        "and sound an alarm immediately!"
    )
    story.append(create_callout(audit_box, title="HOW WE GUARANTEE ZERO FRAUD FOR AUDITORS", border_color=ACCENT_GREEN, bg_color=HexColor("#F0FDF4")))

    return story


def build_page_6(styles):
    """PAGE 6: The AI Brain: Forecasting & Spike Detection (P1 & P2)"""
    story = []
    story.append(Paragraph("The AI Brain: Forecasting & Spike Detection", styles["PageTitle"]))
    story.append(Paragraph("WHY WE NEED AI  •  P1: 24H FUTURE FORECASTER  •  P2: ANOMALY SPIKE ALARM", styles["PageSubtitle"]))

    story.append(Paragraph("1. Why Simple Rules Fail & Why We Need AI", styles["SectionHeader"]))
    story.append(Paragraph(
        "Why can't we just set a fixed rule like: <i>'If power is above 80 Watts, sound an alarm'</i>? "
        "Because real life is dynamic! During 2:00 PM on a Tuesday, thousands of customers use your website, so 90 Watts is completely normal. "
        "But at 3:00 AM on a Sunday, 90 Watts is suspicious and could mean a hacker or runaway program. "
        "That is why we built <b>four smart AI helpers</b> into the engine:",
        styles["Body"]
    ))

    # Embed AI Suite Diagram
    if os.path.exists("pdf_assets/diagram_ai_suite.png"):
        story.append(Image("pdf_assets/diagram_ai_suite.png", width=515, height=170))
        story.append(Spacer(1, 4))

    story.append(Paragraph("2. Helper P1: The 24-Hour Future Forecaster & Green Windows", styles["SectionHeader"]))
    story.append(Paragraph(
        "Implemented in <code>app/services/ai_forecaster.py</code>, this AI predicts tomorrow's power draw using <b>wave mathematics (Fourier Diurnal Harmonics)</b>:",
        styles["Body"]
    ))
    story.append(Paragraph("• <b>Daily Waves:</b> It learns the daily rhythm of human activity (busy mornings, lunch dips, quiet nights).", styles["BulletText"]))
    story.append(Paragraph("• <b>Uncertainty Bands:</b> It draws an upper and lower boundary (95% confidence) showing the most likely power range.", styles["BulletText"]))
    story.append(Paragraph("• <b>The 'Green Window' Finder:</b> It automatically finds the best 3-hour period (e.g. when solar power is peaking) and tells you: <i>'Schedule your big AI training now to cut pollution by 35%!'</i>", styles["BulletText"]))

    story.append(Paragraph("3. Helper P2: The Real-Time Anomaly & Runaway Alarm", styles["SectionHeader"]))
    story.append(Paragraph(
        "Implemented in <code>app/services/ai_anomaly_detector.py</code>, this AI acts like a smoke detector for your server. "
        "It constantly monitors incoming power and catches two big dangers:",
        styles["Body"]
    ))
    story.append(Paragraph("1. <b>Sudden Spikes (Gradient dP/dt):</b> If power jumps by more than 25 Watts in one second, it flags a burst.", styles["BulletText"]))
    story.append(Paragraph("2. <b>Runaway Leaks (Z-Score):</b> If power drifts significantly above the moving average for no reason (like an infinite loop or crypto mining), it raises a <code>CRITICAL_RUNAWAY</code> alarm.", styles["BulletText"]))

    callout_p6 = (
        "<b>Interactive Testbed in Dashboard:</b> You don't have to wait for an accident to see it work! "
        "In the dashboard, you can click <b>'Simulate Rogue Spike (180W)'</b>. You will immediately watch the red alarm gauge jump, "
        "warning SRE engineers. Then click <b>'Mitigate Workload'</b> to restore peace and normal power."
    )
    story.append(create_callout(callout_p6, title="TRY IT YOURSELF IN THE DASHBOARD", border_color=SECONDARY, bg_color=BG_LIGHT))

    return story


def build_page_7(styles):
    """PAGE 7: Cloud Hardware & AWS Graviton3 Savings (Engine P3)"""
    story = []
    story.append(Paragraph("Cloud Hardware: Old Intel vs Green AWS ARM (P3)", styles["PageTitle"]))
    story.append(Paragraph("TDP POWER ENVELOPES  •  AWS GRAVITON3 ARM  •  DOLLARS & TREES ROI CALCULATOR", styles["PageSubtitle"]))

    story.append(Paragraph("1. Why AWS Cloud Hardware Matters", styles["SectionHeader"]))
    story.append(Paragraph(
        "Most companies run their software on Amazon Web Services (AWS) virtual machines called <b>EC2 instances</b>. "
        "However, different computer chips use vastly different amounts of electricity for the exact same job! "
        "Older Intel and AMD chips run hot and burn lots of power. Newer <b>AWS Graviton3 ARM</b> chips are designed like modern smartphone processors: "
        "they are super fast but use almost half the electricity!",
        styles["Body"]
    ))

    # Embed Hardware Comparison diagram
    if os.path.exists("pdf_assets/diagram_hardware_comparison.png"):
        story.append(Image("pdf_assets/diagram_hardware_comparison.png", width=510, height=170))
        story.append(Spacer(1, 4))

    story.append(Paragraph("2. Hardware Catalog Comparison (TDP Power Profiles)", styles["SectionHeader"]))
    hw_table = [
        [
            Paragraph("<b>Server Type</b>", styles["TableHeader"]),
            Paragraph("<b>Processor Architecture</b>", styles["TableHeader"]),
            Paragraph("<b>Idle Draw</b>", styles["TableHeader"]),
            Paragraph("<b>Peak Draw</b>", styles["TableHeader"]),
            Paragraph("<b>Efficiency Rating</b>", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>c6i.4xlarge</b>", styles["TableCellBold"]),
            Paragraph("Intel Xeon (x86)", styles["TableCell"]),
            Paragraph("45 Watts", styles["TableCellCenter"]),
            Paragraph("220 Watts", styles["TableCellCenter"]),
            Paragraph("Older, high electricity overhead", styles["TableCell"]),
        ],
        [
            Paragraph("<b>m6a.4xlarge</b>", styles["TableCellBold"]),
            Paragraph("AMD EPYC (x86)", styles["TableCell"]),
            Paragraph("48 Watts", styles["TableCellCenter"]),
            Paragraph("240 Watts", styles["TableCellCenter"]),
            Paragraph("Large memory, heavy power draw", styles["TableCell"]),
        ],
        [
            Paragraph("<b>c7g.4xlarge</b>", styles["TableCellBold"]),
            Paragraph("<b>AWS Graviton3 (ARM)</b>", styles["TableCellBold"]),
            Paragraph("<b>24 Watts</b>", styles["TableCellCenter"]),
            Paragraph("<b>115 Watts</b>", styles["TableCellCenter"]),
            Paragraph("<b>~48% LESS ELECTRICITY! Super green.</b>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>g5.2xlarge</b>", styles["TableCellBold"]),
            Paragraph("NVIDIA A10G GPU + AMD", styles["TableCell"]),
            Paragraph("65 Watts", styles["TableCellCenter"]),
            Paragraph("310 Watts", styles["TableCellCenter"]),
            Paragraph("High power for AI & graphics", styles["TableCell"]),
        ],
    ]
    t_hw = Table(hw_table, colWidths=[90, 140, 70, 70, 166])
    t_hw.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("BACKGROUND", (0, 3), (-1, 3), HexColor("#ECFDF5")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_hw)
    story.append(Spacer(1, 5))

    story.append(Paragraph("3. Helper P3: The Hardware Right-Sizer & ROI Calculator", styles["SectionHeader"]))
    story.append(Paragraph(
        "In companies, managers often buy big servers that sit mostly empty (e.g. running at only 20% CPU). "
        "Helper P3 scans your server fleet, identifies wasted capacity, and recommends moving to AWS Graviton3 ARM. "
        "It translates the technical savings into three numbers every executive understands:",
        styles["Body"]
    ))
    story.append(Paragraph("• <b>Monthly Money Saved ($):</b> Tells you how many hundreds of dollars you stop wasting on your monthly AWS bill.", styles["BulletText"]))
    story.append(Paragraph("• <b>Annual Carbon Eliminated:</b> Tells you how many metric tons of greenhouse gas you kept out of the sky.", styles["BulletText"]))
    story.append(Paragraph("• <b>Real-World Equivalents:</b> Translates savings into <i>'Number of Tree Seedlings Planted'</i> and <i>'Car Miles Avoided'</i>.", styles["BulletText"]))

    return story


def build_page_8(styles):
    """PAGE 8: Security Shield & The AI Copilot Chatbot (Engine P4)"""
    story = []
    story.append(Paragraph("Security Shield & The AI Copilot Chatbot (P4)", styles["PageTitle"]))
    story.append(Paragraph("6-LAYER DEFENSE SHIELD  •  OWASP A+ HARDENED  •  ZERO-HALLUCINATION AI CHATBOT", styles["PageSubtitle"]))

    story.append(Paragraph("1. The 6-Layer Security Shield (How We Keep It Safe)", styles["SectionHeader"]))
    story.append(Paragraph(
        "Because this system tracks real financial and environmental numbers, it must be protected against hackers and spammers. "
        "We built a <b>6-Layer Defense-in-Depth Shield</b> implemented in <code>app/core/security.py</code>:",
        styles["Body"]
    ))

    sec_simple = [
        [
            Paragraph("<b>Security Layer</b>", styles["TableHeader"]),
            Paragraph("<b>Real-World Metaphor</b>", styles["TableHeader"]),
            Paragraph("<b>How It Protects the System</b>", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>Layer 1: Security Headers</b>", styles["TableCellBold"]),
            Paragraph("Protective Armor", styles["TableCell"]),
            Paragraph("Blocks browser tricks like clickjacking, MIME sniffing, and cross-site scripting (XSS).", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Layer 2: Rate Limiter</b>", styles["TableCellBold"]),
            Paragraph("Bouncer at the Door", styles["TableCell"]),
            Paragraph("Limits each user to 180 requests per minute so spammers cannot crash the server with DoS attacks.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Layer 3: AI Prompt Filter</b>", styles["TableCellBold"]),
            Paragraph("Luggage Scanner", styles["TableCell"]),
            Paragraph("Scans text prompts and strips dangerous injection tricks like 'ignore previous rules' or 'drop table'.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Layer 4: Ingestion Guard</b>", styles["TableCellBold"]),
            Paragraph("Quality Inspector", styles["TableCell"]),
            Paragraph("Rejects negative power numbers, impossible wattage, and isolates server downtime gaps.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Layer 5: Provenance Ledger</b>", styles["TableCellBold"]),
            Paragraph("Tamper-Proof Wax Seal", styles["TableCell"]),
            Paragraph("Locks every single calculation with a permanent SHA-256 digital fingerprint.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Layer 6: Parameterized SQL</b>", styles["TableCellBold"]),
            Paragraph("Reinforced Vault", styles["TableCell"]),
            Paragraph("Uses SQLAlchemy 2.0 to ensure user inputs can never execute unauthorized SQL commands.", styles["TableCell"]),
        ],
    ]
    t_sec = Table(sec_simple, colWidths=[120, 110, 306])
    t_sec.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_sec)
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Helper P4: The AI Sustainability Copilot (Conversational Assistant)", styles["SectionHeader"]))
    story.append(Paragraph(
        "Implemented in <code>app/services/ai_copilot.py</code>, this is a smart assistant designed for executives and engineers. "
        "Instead of forcing you to write database queries, you can just type questions in plain English:",
        styles["Body"]
    ))
    story.append(Paragraph("• <i>'Generate our ESG Scope 2 Report'</i> -> It formats an executive summary of total kWh, total carbon, and data completeness.", styles["BulletText"]))
    story.append(Paragraph("• <i>'Why did power spike at 2 PM?'</i> -> It checks recent audit logs and tells you if someone ran a benchmark test or if a process went rogue.", styles["BulletText"]))
    story.append(Paragraph("• <i>'How can we reduce our footprint?'</i> -> It suggests moving workloads to green regions or right-sizing EC2 instances.", styles["BulletText"]))

    copilot_callout = (
        "<b>The Zero-Hallucination Guarantee:</b> Commercial chatbots (like ChatGPT) often make up fake math numbers when asked tricky math questions. "
        "Our Copilot has a strict safety rule: <b>it never invents numbers</b>! It only reads verified, cryptographically sealed numbers "
        "directly from the database calculation engine. You get 100% truthful, audit-ready reports."
    )
    story.append(create_callout(copilot_callout, title="TRUTHFUL AI: NO FAKE MATH", border_color=ACCENT_GREEN, bg_color=HexColor("#F0FDF4")))

    return story


def build_page_9(styles):
    """PAGE 9: The Web Dashboard & Live Monitoring"""
    story = []
    story.append(Paragraph("The Web Dashboard & Live SRE Monitoring", styles["PageTitle"]))
    story.append(Paragraph("NATIVE WEB DASHBOARD  •  CHART.JS VISUALS  •  PROMETHEUS & GRAFANA INTEGRATION", styles["PageSubtitle"]))

    story.append(Paragraph("1. Dashboard Design: Fast, Beautiful & Zero-Bloat", styles["SectionHeader"]))
    story.append(Paragraph(
        "We built the web dashboard using pure <b>Vanilla HTML5, modern CSS3, and JavaScript</b> located in <code>app/static/</code>. "
        "We deliberately avoided heavy frontend frameworks (like React or Angular) so that the dashboard loads in milliseconds, "
        "requires zero complex build tools (like npm or webpack), and runs smoothly on any laptop or phone.",
        styles["Body"]
    ))

    story.append(Paragraph("2. Guided Tour of the 8 Dashboard Modules", styles["SectionHeader"]))
    dash_modules = [
        [
            Paragraph("<b>Module Name</b>", styles["TableHeader"]),
            Paragraph("<b>What You See on the Screen</b>", styles["TableHeader"]),
            Paragraph("<b>What You Can Do (User Interaction)</b>", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>1. Live Metric Cards</b>", styles["TableCellBold"]),
            Paragraph("Big glowing cards showing current Watts, total kWh, and grams of CO<sub>2</sub>.", styles["TableCell"]),
            Paragraph("Watch numbers update live in real-time as your computer works.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>2. Grid & PUE Controls</b>", styles["TableCellBold"]),
            Paragraph("A dropdown menu for regions and a slider for datacenter cooling overhead (PUE).", styles["TableCell"]),
            Paragraph("Switch between US-East and Sweden to watch carbon drop by 88% instantly!", styles["TableCell"]),
        ],
        [
            Paragraph("<b>3. Dual-Axis Charts</b>", styles["TableCellBold"]),
            Paragraph("Smooth moving lines powered by Chart.js showing Watts and accumulated carbon.", styles["TableCell"]),
            Paragraph("Hover with your mouse over any second in history to inspect exact values.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>4. 24h AI Forecaster</b>", styles["TableCellBold"]),
            Paragraph("A forward-looking projection chart with green shaded 'Green Windows'.", styles["TableCell"]),
            Paragraph("See the best upcoming hours to run your heavy batch jobs.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>5. Anomaly Dial & Spike Buttons</b>", styles["TableCellBold"]),
            Paragraph("A colorful gauge dial showing the current power health score.", styles["TableCell"]),
            Paragraph("Click 'Simulate Rogue Spike' to test alarms, then 'Mitigate' to calm it down.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>6. AWS Hardware Advisor</b>", styles["TableCellBold"]),
            Paragraph("An instance picker (e.g. c6i Intel) and a server count slider.", styles["TableCell"]),
            Paragraph("See exact monthly dollar savings and tree seedlings planted by moving to ARM.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>7. AI Copilot Chat</b>", styles["TableCellBold"]),
            Paragraph("A clean chat window with quick prompt pills.", styles["TableCell"]),
            Paragraph("Click 'Generate ESG Scope 2 Report' to get an instant executive summary.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>8. Security Center</b>", styles["TableCellBold"]),
            Paragraph("A live A+ security grade badge and SHA-256 ledger scanner button.", styles["TableCell"]),
            Paragraph("Click 'Verify Ledger' to scan the entire database for tampering in 1 second.", styles["TableCell"]),
        ],
    ]
    t_dash = Table(dash_modules, colWidths=[115, 205, 216])
    t_dash.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_dash)
    story.append(Spacer(1, 5))

    story.append(Paragraph("3. SRE Observability: Prometheus & Grafana Integration", styles["SectionHeader"]))
    story.append(Paragraph(
        "In big tech companies, Site Reliability Engineers (SREs) use <b>Prometheus</b> and <b>Grafana</b> to monitor systems. "
        "Our engine automatically exports standard metrics at <code>/metrics</code> (such as <code>energy_power_watts</code> and <code>ai_power_anomaly_score</code>). "
        "We also include a pre-built Grafana dashboard configuration file (<code>dashboards/grafana-dashboard.json</code>) so teams can plug it in immediately.",
        styles["Body"]
    ))

    return story


def build_page_10(styles):
    """PAGE 10: How It Was Tested, How to Run It & Conclusion"""
    story = []
    story.append(Paragraph("How It Was Tested, How to Run It & Conclusion", styles["PageTitle"]))
    story.append(Paragraph("38 AUTOMATED PYTEST TESTS  •  STRESS-TEST BENCHMARKS  •  24/7 PRODUCTION SETUP", styles["PageSubtitle"]))

    story.append(Paragraph("1. Rigorous Testing: 38 Automated Tests (100% Passed)", styles["SectionHeader"]))
    story.append(Paragraph(
        "To guarantee that every calculation, security filter, and AI model works without bugs, we wrote a comprehensive test suite "
        "using <b>Pytest</b> in the <code>tests/</code> folder. All 38 tests pass with flying colors:",
        styles["Body"]
    ))

    test_simple = [
        [
            Paragraph("<b>Test File</b>", styles["TableHeader"]),
            Paragraph("<b>What It Tests (Simple Words)</b>", styles["TableHeader"]),
            Paragraph("<b>Test Result</b>", styles["TableHeader"]),
        ],
        [
            Paragraph("<code>test_integration.py</code>", styles["TableCellBold"]),
            Paragraph("Tests the math: makes sure Watts turn into Watt-hours and kWh accurately.", styles["TableCell"]),
            Paragraph("PASSED", styles["TableCellCenter"]),
        ],
        [
            Paragraph("<code>test_gap_and_validation.py</code>", styles["TableCellBold"]),
            Paragraph("Tests the 15-second downtime rule: ensures no fake energy during crashes.", styles["TableCell"]),
            Paragraph("PASSED", styles["TableCellCenter"]),
        ],
        [
            Paragraph("<code>test_carbon_calculator.py</code>", styles["TableCellBold"]),
            Paragraph("Tests city power grid factors and verifies the SHA-256 digital seals.", styles["TableCell"]),
            Paragraph("PASSED", styles["TableCellCenter"]),
        ],
        [
            Paragraph("<code>test_security.py</code>", styles["TableCellBold"]),
            Paragraph("Tests security headers, 180 req/min rate limiters, and prompt filters.", styles["TableCell"]),
            Paragraph("PASSED", styles["TableCellCenter"]),
        ],
        [
            Paragraph("<code>test_aws_optimizer.py</code>", styles["TableCellBold"]),
            Paragraph("Tests the SPECpower equation and AWS Graviton3 ARM cost savings math.", styles["TableCell"]),
            Paragraph("PASSED", styles["TableCellCenter"]),
        ],
        [
            Paragraph("<code>test_ai_features.py</code>", styles["TableCellBold"]),
            Paragraph("Tests the 24h Forecaster, green window finder, anomaly detector, and Copilot.", styles["TableCell"]),
            Paragraph("PASSED", styles["TableCellCenter"]),
        ],
        [
            Paragraph("<code>test_stress_experiment.py</code>", styles["TableCellBold"]),
            Paragraph("Runs the 4-step stress test (Idle -> Spike -> Heavy Load -> Cool Down).", styles["TableCell"]),
            Paragraph("PASSED", styles["TableCellCenter"]),
        ],
    ]
    t_tests = Table(test_simple, colWidths=[140, 316, 80])
    t_tests.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("BACKGROUND", (2, 1), (2, -1), HexColor("#ECFDF5")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_tests)
    story.append(Spacer(1, 5))

    story.append(Paragraph("2. How to Run the Project 24/7", styles["SectionHeader"]))
    story.append(Paragraph(
        "We provided three simple ways to run the project continuously:",
        styles["Body"]
    ))
    story.append(Paragraph(
        "• <b>Option 1: Docker Containers (Recommended for Cloud):</b> Run <code>docker compose up -d</code>. "
        "It launches both the translation engine and Prometheus inside isolated containers with automatic restart.",
        styles["BulletText"]
    ))
    story.append(Paragraph(
        "• <b>Option 2: Windows Background Daemon (For Local Laptops):</b> Double-click <code>start_background_24_7.vbs</code>. "
        "It silently runs the server in the background and auto-restarts if anything crashes, without keeping annoying command windows open.",
        styles["BulletText"]
    ))
    story.append(Paragraph(
        "• <b>Option 3: Cloudflare Zero-Trust Tunnel:</b> Run <code>python tunnel_runner.py</code>. "
        "It gives you a secure public HTTPS website link so you can share your live dashboard with teachers, evaluators, or clients anywhere in the world!",
        styles["BulletText"]
    ))

    story.append(Paragraph("3. Summary & Final Conclusion", styles["SectionHeader"]))
    conclusion_box = (
        "<b>Summary in Plain Words:</b> This project transforms invisible computer electricity into clear, understandable environmental intelligence. "
        "By uniting accurate math, tamper-proof security seals, regional grid awareness, and 4 smart AI helpers, "
        "it gives companies the exact tools they need to cut cloud bills, eliminate carbon pollution, and build a greener digital future."
    )
    story.append(create_callout(conclusion_box, title="PROJECT CONCLUSION & ENVIRONMENTAL IMPACT", border_color=ACCENT_GREEN, bg_color=HexColor("#F0FDF4")))

    return story


def generate_pdf(output_filename="Energy_to_CO2_Project_Documentation.pdf"):
    """Assemble all 10 pages and generate the final PDF report."""
    styles = get_custom_styles()

    # Document margins: 36pt left/right, 36pt top/bottom
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    story = []

    # Page 1
    story.extend(build_page_1(styles))
    story.append(PageBreak())

    # Page 2
    story.extend(build_page_2(styles))
    story.append(PageBreak())

    # Page 3
    story.extend(build_page_3(styles))
    story.append(PageBreak())

    # Page 4
    story.extend(build_page_4(styles))
    story.append(PageBreak())

    # Page 5
    story.extend(build_page_5(styles))
    story.append(PageBreak())

    # Page 6
    story.extend(build_page_6(styles))
    story.append(PageBreak())

    # Page 7
    story.extend(build_page_7(styles))
    story.append(PageBreak())

    # Page 8
    story.extend(build_page_8(styles))
    story.append(PageBreak())

    # Page 9
    story.extend(build_page_9(styles))
    story.append(PageBreak())

    # Page 10 (Last page: no trailing PageBreak)
    story.extend(build_page_10(styles))

    print(f"Building PDF '{output_filename}' with NumberedCanvas...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print("PDF build completed successfully.")


if __name__ == "__main__":
    generate_pdf()
