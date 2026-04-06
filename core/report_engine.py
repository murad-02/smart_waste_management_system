import os
import io
from datetime import datetime, date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage,
    PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from config import REPORTS_DIR, APP_NAME
from database.db_setup import Session
from database.models import Detection, Report, User
from core.analytics_engine import AnalyticsEngine


class ReportEngine:
    """Generates PDF reports with charts, statistics, and detection details."""

    def __init__(self):
        self.analytics = AnalyticsEngine()

    def generate_report(self, report_type: str, start_date: date,
                        end_date: date, generated_by: int) -> str:
        """Generate a PDF report and return the file path."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_{start_date}_{end_date}_{timestamp}.pdf"
        file_path = os.path.join(REPORTS_DIR, filename)

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Gather data
        category_dist = self.analytics.get_category_distribution(start_dt, end_dt)
        fill_dist = self.analytics.get_fill_level_distribution(start_dt, end_dt)
        detections = self._get_detections_in_range(start_dt, end_dt)

        total_detections = len(detections)
        top_category = max(category_dist, key=category_dist.get) if category_dist else "N/A"

        # Build PDF
        doc = SimpleDocTemplate(
            file_path, pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm, bottomMargin=20 * mm
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle", parent=styles["Title"],
            fontSize=20, textColor=colors.HexColor("#00b894"),
            spaceAfter=12
        )
        heading_style = ParagraphStyle(
            "ReportHeading", parent=styles["Heading2"],
            fontSize=14, textColor=colors.HexColor("#0984e3"),
            spaceAfter=8, spaceBefore=16
        )
        normal_style = styles["Normal"]

        elements = []

        # --- Header ---
        elements.append(Paragraph(APP_NAME, title_style))
        elements.append(Paragraph(
            f"<b>{report_type.capitalize()} Report</b>", heading_style
        ))
        elements.append(Paragraph(
            f"Date Range: {start_date} to {end_date}", normal_style
        ))
        elements.append(Paragraph(
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            normal_style
        ))
        elements.append(Spacer(1, 20))

        # --- Summary Statistics ---
        elements.append(Paragraph("Summary Statistics", heading_style))
        summary_data = [
            ["Total Detections", str(total_detections)],
            ["Top Waste Category", top_category],
        ]
        for cat, count in category_dist.items():
            summary_data.append([f"  {cat}", str(count)])

        summary_table = Table(summary_data, colWidths=[250, 200])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#22223a")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # --- Category Distribution Chart ---
        if category_dist:
            elements.append(Paragraph("Waste Category Distribution", heading_style))
            chart_path = self._create_bar_chart(category_dist, "Category Distribution")
            if chart_path:
                elements.append(RLImage(chart_path, width=450, height=250))
                elements.append(Spacer(1, 20))

        # --- Fill Level Summary ---
        if fill_dist:
            elements.append(Paragraph("Bin Fill Level Summary", heading_style))
            fill_data = [["Fill Level", "Count"]]
            for level, count in fill_dist.items():
                fill_data.append([level.replace("_", " ").title(), str(count)])

            fill_table = Table(fill_data, colWidths=[250, 200])
            fill_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0984e3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(fill_table)
            elements.append(Spacer(1, 20))

        # --- Detection Details Table ---
        elements.append(Paragraph("Detection Details", heading_style))
        if detections:
            # Paginate: 25 rows per page
            detail_header = ["ID", "Date", "Category", "Confidence", "Operator", "Status"]
            page_size = 25

            for i in range(0, len(detections), page_size):
                page_detections = detections[i:i + page_size]
                detail_data = [detail_header]

                for d in page_detections:
                    operator_name = self._get_user_name(d.detected_by)
                    detail_data.append([
                        str(d.id),
                        d.detected_at.strftime("%Y-%m-%d %H:%M") if d.detected_at else "",
                        d.waste_category,
                        f"{d.confidence:.0%}",
                        operator_name,
                        d.status.capitalize()
                    ])

                detail_table = Table(
                    detail_data,
                    colWidths=[40, 100, 80, 70, 100, 70]
                )
                detail_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00b894")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#f5f5f5")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                elements.append(detail_table)

                if i + page_size < len(detections):
                    elements.append(PageBreak())
        else:
            elements.append(Paragraph("No detections found in the selected date range.",
                                      normal_style))

        # Build the PDF
        doc.build(elements)

        # Save report record to database
        self._save_report_record(report_type, file_path, generated_by,
                                 start_date, end_date)

        # Clean up temp chart image
        self._cleanup_temp_files()

        return file_path

    def _get_detections_in_range(self, start_dt, end_dt):
        """Get all detections within a date range."""
        session = Session()
        try:
            detections = session.query(Detection).filter(
                Detection.detected_at >= start_dt,
                Detection.detected_at <= end_dt
            ).order_by(Detection.detected_at.desc()).all()
            session.expunge_all()
            return detections
        except Exception:
            return []
        finally:
            session.close()

    def _get_user_name(self, user_id: int) -> str:
        """Get a user's full name by ID."""
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            return user.full_name if user else f"User #{user_id}"
        except Exception:
            return f"User #{user_id}"
        finally:
            session.close()

    def _create_bar_chart(self, data: dict, title: str) -> str:
        """Create a bar chart image and return its file path."""
        try:
            fig, ax = plt.subplots(figsize=(8, 4))
            categories = list(data.keys())
            values = list(data.values())

            bar_colors = ["#00b894", "#0984e3", "#fdcb6e", "#d63031",
                          "#6c5ce7", "#00cec9", "#fd79a8"]
            colors_to_use = bar_colors[:len(categories)]

            ax.bar(categories, values, color=colors_to_use)
            ax.set_title(title, fontsize=14, fontweight="bold")
            ax.set_ylabel("Count")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()

            chart_path = os.path.join(REPORTS_DIR, "_temp_chart.png")
            fig.savefig(chart_path, dpi=100, bbox_inches="tight")
            plt.close(fig)
            return chart_path
        except Exception:
            return None

    def _save_report_record(self, report_type, file_path, generated_by,
                            start_date, end_date):
        """Save report metadata to the database."""
        session = Session()
        try:
            report = Report(
                report_type=report_type,
                file_path=file_path,
                generated_by=generated_by,
                generated_at=datetime.utcnow(),
                date_range_start=start_date,
                date_range_end=end_date
            )
            session.add(report)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def _cleanup_temp_files(self):
        """Remove temporary chart images."""
        temp_chart = os.path.join(REPORTS_DIR, "_temp_chart.png")
        if os.path.exists(temp_chart):
            try:
                os.remove(temp_chart)
            except Exception:
                pass

    def get_all_reports(self):
        """Get all report records."""
        session = Session()
        try:
            reports = session.query(Report).order_by(Report.generated_at.desc()).all()
            session.expunge_all()
            return reports
        except Exception:
            return []
        finally:
            session.close()

    def delete_report(self, report_id: int) -> bool:
        """Delete a report record and its file."""
        session = Session()
        try:
            report = session.query(Report).filter_by(id=report_id).first()
            if not report:
                return False

            # Delete the file
            if os.path.exists(report.file_path):
                os.remove(report.file_path)

            session.delete(report)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
