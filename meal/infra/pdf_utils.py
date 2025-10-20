import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf_for_week(plan):
    """Generate a simple PDF table: Day / Breakfast / Lunch / Dinner for the provided plan."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Meal Plan – Week {plan.week}, {plan.year}", styles["Title"]),
        Spacer(1, 16),
    ]

    data = [["Day", "Breakfast", "Lunch", "Dinner"]]
    for day, meals in plan.meals.items():
        data.append([
            f"{day} ({meals.get('date','')})",
            meals.get("breakfast", "-"),
            meals.get("lunch", "-"),
            meals.get("dinner", "-"),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4CAF50")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 12),
        ("BOTTOMPADDING", (0,0), (-1,0), 10),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ]))

    elements.append(table)
    doc.build(elements)
    return buf.getvalue()
