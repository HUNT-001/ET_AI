"""
Generates a synthetic-but-realistic sample PDF for pipeline testing.
Content is entirely original (written for this scaffold) but structured
like a real industrial maintenance/inspection report, referencing real
regulatory designations (OISD-STD-118, Factory Act Sec. 21) by name only
-- not reproducing their text -- so the ingestion pipeline has something
realistic to extract entities from before real documents are sourced.
"""

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm

styles = getSampleStyleSheet()

doc = SimpleDocTemplate("/home/claude/edgeai-os/datasets/samples/sample_maintenance_report.pdf", pagesize=A4)
story = []

story.append(Paragraph("Equipment Inspection & Maintenance Report", styles["Title"]))
story.append(Spacer(1, 0.5 * cm))

story.append(Paragraph("Report No: MNT-2026-0142", styles["Normal"]))
story.append(Paragraph("Plant: North Sector Process Unit 3", styles["Normal"]))
story.append(Paragraph("Inspection Date: 14 March 2026", styles["Normal"]))
story.append(Paragraph("Inspector: R. Menon, Senior Process Safety Engineer", styles["Normal"]))
story.append(Spacer(1, 0.5 * cm))

story.append(Paragraph("1. Summary", styles["Heading2"]))
story.append(Paragraph(
    "Routine inspection of pump P-101A and associated pressure relief valve "
    "V-204 was carried out on 14 March 2026 following a reported pressure "
    "fluctuation logged on 09 March 2026. Vibration readings on P-101A "
    "exceeded the baseline threshold by 18%%, consistent with early-stage "
    "bearing wear. No gas leakage was detected during the inspection window.",
    styles["Normal"]))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("2. Findings", styles["Heading2"]))
story.append(Paragraph(
    "Operating pressure on line PL-22 was recorded at 8.7 bar against a "
    "rated maximum of 10.2 bar. Bearing housing temperature on P-101A "
    "reached 71 degrees Celsius, above the 65 degree Celsius normal "
    "operating range specified in the OEM manual for this pump model. "
    "Relief valve V-204 set pressure was verified at 9.8 bar, within "
    "tolerance.",
    styles["Normal"]))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("3. Regulatory Cross-Reference", styles["Heading2"]))
story.append(Paragraph(
    "This inspection was conducted in accordance with OISD-STD-118 "
    "(Layouts for Oil and Gas Installations) safe-distance provisions and "
    "Factory Act Sec. 21 (Safety of Building and Machinery) periodic "
    "inspection requirements. No deviations from mandated inspection "
    "intervals were identified.",
    styles["Normal"]))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("4. Prior Related Incidents", styles["Heading2"]))
story.append(Paragraph(
    "Maintenance log MNT-2025-0871 (dated 22 August 2025) recorded a "
    "similar vibration anomaly on pump P-101A, attributed at the time to "
    "a loose foundation bolt and resolved by re-torquing to OEM "
    "specification. Given the recurrence pattern, bearing replacement is "
    "recommended rather than a further torque adjustment.",
    styles["Normal"]))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("5. Recommended Actions", styles["Heading2"]))
data = [
    ["Action", "Equipment", "Priority", "Due Date"],
    ["Replace bearing assembly", "P-101A", "High", "28 March 2026"],
    ["Re-verify relief set pressure post-repair", "V-204", "Medium", "30 March 2026"],
    ["Update OEM service interval log", "P-101A", "Low", "31 March 2026"],
]
table = Table(data, colWidths=[6.5*cm, 3*cm, 2.5*cm, 3.5*cm])
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
]))
story.append(table)

doc.build(story)
print("Sample PDF generated.")
