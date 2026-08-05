from fpdf import FPDF
from datetime import datetime
import json

class ascendReport(FPDF):
    def header(self):
        self.set_fill_color(30, 20, 60)
        self.rect(0, 0, 210, 22, 'F')
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(200, 180, 255)
        self.set_y(6)
        self.cell(0, 10, "ascend - AI Code Review Report", align="C")
        self.set_draw_color(100, 100, 200)
        self.set_line_width(0.5)
        self.line(10, 22, 200, 22)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"ascend Report  |  {datetime.now().strftime('%d %B %Y, %I:%M %p')}  |  Page {self.page_no()}", align="C")

    def section_title(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(40, 30, 80)
        self.set_text_color(180, 160, 255)
        self.cell(0, 9, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def divider(self):
        self.set_draw_color(200, 200, 220)
        self.set_line_width(0.2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)


def generate_pdf_report(review_data, code_snippet, language, overall_score, issue_counts, output_path):
    pdf = ascendReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_left_margin(12)
    pdf.set_right_margin(12)

    issues = review_data.get("issues", [])
    strengths = review_data.get("strengths", [])
    summary = review_data.get("summary", "")
    top_learning = review_data.get("top_learning", "")

    # ── SCORE OVERVIEW ──
    pdf.section_title("SCORE OVERVIEW")

    score_color = (16, 140, 80) if overall_score >= 70 else (180, 120, 0) if overall_score >= 50 else (180, 40, 40)
    verdict = "Excellent" if overall_score >= 85 else "Good" if overall_score >= 70 else "Needs Work" if overall_score >= 50 else "Major Issues" if overall_score >= 30 else "Critical Issues"

    # score row
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(*score_color)
    pdf.set_x(12)
    pdf.cell(0, 14, str(overall_score), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(40, 40, 40)
    pdf.set_x(12)
    pdf.cell(0, 7, f"Verdict: {verdict}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.cell(0, 7, f"Language: {language}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.cell(0, 7, f"Total Issues: {len(issues)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # issue breakdown row
    pdf.set_font("Helvetica", "B", 10)
    categories = [
        ("Bugs", issue_counts.get("bug", 0), (180, 40, 60)),
        ("Security", issue_counts.get("security", 0), (160, 100, 0)),
        ("Performance", issue_counts.get("performance", 0), (60, 60, 180)),
        ("Style", issue_counts.get("style", 0), (20, 120, 80)),
    ]

    for label, count, color in categories:
        pdf.set_fill_color(245, 245, 250)
        pdf.set_draw_color(200, 200, 220)
        pdf.set_line_width(0.3)
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.rect(x, y, 43, 16, 'DF')
        pdf.set_text_color(*color)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_xy(x, y + 1)
        pdf.cell(43, 8, str(count), align="C")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.set_xy(x, y + 9)
        pdf.cell(43, 5, label, align="C")
        pdf.set_xy(x + 44, y)

    pdf.ln(20)

    # ── SUMMARY ──
    if summary:
        pdf.section_title("AI SUMMARY")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.set_fill_color(248, 248, 255)
        pdf.set_x(12)
        pdf.multi_cell(186, 6, summary, fill=True)
        pdf.ln(2)

    # ── ISSUES ──
    if issues:
        pdf.section_title(f"ISSUES FOUND ({len(issues)})")

        type_colors = {
            "bug": (180, 40, 60),
            "security": (160, 100, 0),
            "performance": (60, 60, 180),
            "style": (20, 120, 80)
        }

        sev_labels = {
            "high": "HIGH",
            "medium": "MEDIUM",
            "low": "LOW"
        }

        sev_colors = {
            "high": (180, 40, 60),
            "medium": (160, 100, 0),
            "low": (20, 120, 80)
        }

        for i, issue in enumerate(issues, 1):
            issue_type = issue.get("type", "style").lower()
            severity = issue.get("severity", "medium").lower()
            title = issue.get("title", "Issue detected")
            description = issue.get("description", "")
            fix = issue.get("fix", "")
            lesson = issue.get("lesson", "")
            line_num = issue.get("line", "")

            type_color = type_colors.get(issue_type, (100, 100, 100))
            sev_color = sev_colors.get(severity, (100, 100, 100))

            # issue number and title
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(30, 30, 30)
            pdf.set_x(12)
            title_text = f"{i}. {title}"
            if line_num:
                title_text += f"  (Line {line_num})"
            pdf.cell(0, 7, title_text, new_x="LMARGIN", new_y="NEXT")

            # type and severity badges
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*type_color)
            pdf.set_x(12)
            pdf.cell(25, 5, f"[{issue_type.upper()}]")
            pdf.set_text_color(*sev_color)
            pdf.cell(25, 5, f"[{sev_labels.get(severity, severity.upper())}]")
            pdf.ln(6)

            # description
            if description:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(60, 60, 60)
                pdf.set_x(14)
                pdf.multi_cell(182, 5, description)
                pdf.ln(1)

            # fix
            if fix:
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(20, 120, 80)
                pdf.set_x(14)
                pdf.cell(0, 5, "Fix:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Courier", "", 8)
                pdf.set_text_color(30, 30, 30)
                pdf.set_fill_color(240, 248, 240)
                pdf.set_x(14)
                fix_clean = fix[:400].encode('ascii', 'replace').decode('ascii')
                pdf.multi_cell(182, 4.5, fix_clean, fill=True)
                pdf.ln(1)

            # lesson
            if lesson:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(80, 80, 160)
                pdf.set_x(14)
                lesson_clean = lesson.encode('ascii', 'replace').decode('ascii')
                pdf.multi_cell(182, 5, f"Learn: {lesson_clean}")
                pdf.ln(1)

            pdf.divider()

    # ── STRENGTHS ──
    if strengths:
        pdf.section_title("STRENGTHS")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 100, 60)
        for s in strengths:
            pdf.set_x(14)
            s_clean = s.encode('ascii', 'replace').decode('ascii')
            pdf.multi_cell(182, 6, f"+ {s_clean}")
        pdf.ln(2)

    # ── TOP LEARNING ──
    if top_learning:
        pdf.section_title("TOP THING TO LEARN NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.set_fill_color(255, 252, 230)
        pdf.set_x(12)
        tl_clean = top_learning.encode('ascii', 'replace').decode('ascii')
        pdf.multi_cell(186, 6, tl_clean, fill=True)
        pdf.ln(4)

    # ── CODE SUBMITTED ──
    pdf.section_title("CODE SUBMITTED")
    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(40, 40, 40)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_x(12)
    code_clean = code_snippet[:2000].encode('ascii', 'replace').decode('ascii')
    if len(code_snippet) > 2000:
        code_clean += "\n... (truncated)"
    pdf.multi_cell(186, 4, code_clean, fill=True)

    pdf.output(output_path)
    return output_path