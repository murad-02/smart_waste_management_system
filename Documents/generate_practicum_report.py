from __future__ import annotations

import copy
import os
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("w", W_NS)


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _set_attr(elem, name: str, value: str):
    elem.set(w(name), value)


def paragraph(
    text: str = "",
    *,
    style: str | None = None,
    align: str | None = None,
    bold: bool = False,
    page_break_before: bool = False,
) -> ET.Element:
    p = ET.Element(w("p"))
    p_pr = ET.SubElement(p, w("pPr"))
    if style:
        p_style = ET.SubElement(p_pr, w("pStyle"))
        _set_attr(p_style, "val", style)
    if align:
        jc = ET.SubElement(p_pr, w("jc"))
        _set_attr(jc, "val", align)
    if page_break_before:
        pb = ET.SubElement(p_pr, w("pageBreakBefore"))
        _set_attr(pb, "val", "1")

    if text:
        for i, line in enumerate(text.split("\n")):
            r = ET.SubElement(p, w("r"))
            if bold:
                r_pr = ET.SubElement(r, w("rPr"))
                ET.SubElement(r_pr, w("b"))
            t = ET.SubElement(r, w("t"))
            if line.startswith(" ") or line.endswith(" "):
                t.set(f"{{{XML_NS}}}space", "preserve")
            t.text = line
            if i < len(text.split("\n")) - 1:
                ET.SubElement(r, w("br"))
    return p


def page_break() -> ET.Element:
    p = ET.Element(w("p"))
    r = ET.SubElement(p, w("r"))
    br = ET.SubElement(r, w("br"))
    _set_attr(br, "type", "page")
    return p


def table(rows: list[list[str]], widths: list[int] | None = None) -> ET.Element:
    tbl = ET.Element(w("tbl"))

    tbl_pr = ET.SubElement(tbl, w("tblPr"))
    tbl_style = ET.SubElement(tbl_pr, w("tblStyle"))
    _set_attr(tbl_style, "val", "TableGrid")
    tbl_w = ET.SubElement(tbl_pr, w("tblW"))
    _set_attr(tbl_w, "w", "0")
    _set_attr(tbl_w, "type", "auto")

    if widths is None:
        widths = [2500] * len(rows[0])

    tbl_grid = ET.SubElement(tbl, w("tblGrid"))
    for width in widths:
        grid_col = ET.SubElement(tbl_grid, w("gridCol"))
        _set_attr(grid_col, "w", str(width))

    for ridx, row in enumerate(rows):
        tr = ET.SubElement(tbl, w("tr"))
        for cell_text in row:
            tc = ET.SubElement(tr, w("tc"))
            tc_pr = ET.SubElement(tc, w("tcPr"))
            tc_w = ET.SubElement(tc_pr, w("tcW"))
            _set_attr(tc_w, "w", "0")
            _set_attr(tc_w, "type", "auto")
            tc_p = paragraph(cell_text, bold=(ridx == 0))
            tc.append(tc_p)
    return tbl


def get_base_sectpr(base_docx: Path) -> ET.Element:
    with zipfile.ZipFile(base_docx, "r") as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    body = root.find(w("body"))
    sect_pr = body.find(w("sectPr"))
    if sect_pr is None:
        raise RuntimeError("Base DOCX does not contain sectPr")
    return copy.deepcopy(sect_pr)


def build_document() -> ET.Element:
    doc = ET.Element(w("document"))
    body = ET.SubElement(doc, w("body"))

    def add(*elements: ET.Element):
        for element in elements:
            body.append(element)

    title = (
        "Smart Waste Management System:\n"
        "A Desktop Application with YOLO-Based Bin Monitoring,\n"
        "Alerts, Reporting, and Fleet Operations"
    )

    add(
        paragraph("Md. Muradul Islam", align="center"),
        paragraph("ID# 22203234", align="center"),
        paragraph("", align="center"),
        paragraph(
            "A Practicum in the Partial Fulfillment of the Requirements\n"
            "for the Award of Bachelor of Computer Science and Engineering (BCSE)",
            align="center",
        ),
        paragraph("Department of Computer Science and Engineering", align="center"),
        paragraph("College of Engineering and Technology", align="center"),
        paragraph(
            "IUBAT-International University of Business Agriculture and Technology",
            align="center",
        ),
        paragraph("Spring 2026", align="center"),
        paragraph("", align="center"),
        paragraph(title, style="Title", align="center"),
        page_break(),
        paragraph(title, style="Title", align="center"),
        paragraph("Md. Muradul Islam", align="center"),
        paragraph("ID# 22203234", align="center"),
        paragraph(
            "A Practicum in the Partial Fulfillment of the Requirements for the Award of Bachelor of Computer Science and Engineering (BCSE)",
            align="center",
        ),
        paragraph("The practicum has been examined and approved,", align="center"),
        paragraph("", align="center"),
        paragraph("_____________________________", align="center"),
        paragraph("Prof. Dr. Utpal Kanti Das", align="center"),
        paragraph("Chairman", align="center"),
        paragraph("Department of Computer Science and Engineering", align="center"),
        paragraph("", align="center"),
        paragraph("_____________________________", align="center"),
        paragraph("Shahinur Alam", align="center"),
        paragraph("Co-supervisor, Coordinator and Assistant Professor", align="center"),
        paragraph("Department of Computer Science and Engineering", align="center"),
        paragraph("", align="center"),
        paragraph("_____________________________", align="center"),
        paragraph("Md. Khairul Islam", align="center"),
        paragraph("Supervisor and Lecturer", align="center"),
        paragraph("Department of Computer Science and Engineering", align="center"),
        paragraph("College of Engineering and Technology", align="center"),
        paragraph(
            "IUBAT-International University of Business Agriculture and Technology",
            align="center",
        ),
        paragraph("Spring 2026", align="center"),
        page_break(),
        paragraph("Letter of Transmittal", style="Heading1"),
        paragraph("26 May 2026"),
        paragraph("The Chair"),
        paragraph("Practicum Defense Committee"),
        paragraph("Department of Computer Science and Engineering"),
        paragraph("IUBAT-International University of Business Agriculture and Technology"),
        paragraph("4 Embankment Drive Road, Sector 10, Uttara Model Town"),
        paragraph("Dhaka 1230, Bangladesh."),
        paragraph("Subject: Submission of practicum report on the Smart Waste Management System."),
        paragraph("Dear Sir,"),
        paragraph(
            "With due respect, I am submitting my practicum report titled "
            "\"Smart Waste Management System: A Desktop Application with YOLO-Based Bin "
            "Monitoring, Alerts, Reporting, and Fleet Operations\" as a partial "
            "requirement for the Bachelor of Computer Science and Engineering degree "
            "at IUBAT. The report has been prepared from the actual repository state "
            "of this project. It documents the implemented modules, database design, "
            "role-based workflows, YOLO-based detection pipeline, alerting, reporting, "
            "and fleet operations subsystem without relying on fabricated functionality."
        ),
        paragraph(
            "This version intentionally corrects earlier draft material that described "
            "the system as a mock-only detector. The current implementation contains "
            "real model-loading paths for `models/best.pt` and `models/best_bin_level.pt`, "
            "video and webcam handling in the detection UI, and six fleet-management "
            "screens in addition to the original waste-management workflow. I respectfully "
            "submit this report for evaluation."
        ),
        paragraph("Yours sincerely,"),
        paragraph("_____________"),
        paragraph("Md. Muradul Islam"),
        paragraph("ID# 22203234"),
        page_break(),
        paragraph("Organization's Certificate", style="Heading1"),
        paragraph(
            "A scanned organization certificate is not included in the repository. "
            "This page is intentionally left as a placeholder so the official certificate "
            "can be inserted without altering the rest of the report."
        ),
        page_break(),
        paragraph("Student's Declaration", style="Heading1"),
        paragraph(
            "I, Md. Muradul Islam, declare that this practicum report titled "
            "\"Smart Waste Management System: A Desktop Application with YOLO-Based Bin "
            "Monitoring, Alerts, Reporting, and Fleet Operations\" has been prepared "
            "from my own work and from the actual project artifacts available in the "
            "repository. The analysis, code inspection, screenshots, diagrams, and "
            "written explanations presented here were prepared for academic submission "
            "under the guidance of my supervisor."
        ),
        paragraph(
            "Where external documentation or software manuals informed implementation "
            "choices, those sources are acknowledged in the reference section. No part "
            "of this report intentionally contains plagiarized material, fabricated "
            "experimental results, or invented project features. I take responsibility "
            "for the accuracy of the submitted content."
        ),
        paragraph("_____________"),
        paragraph("Md. Muradul Islam"),
        paragraph("ID# 22203234"),
        page_break(),
        paragraph("Supervisor's Certification", style="Heading1"),
        paragraph(
            "This is to certify that the practicum report titled "
            "\"Smart Waste Management System: A Desktop Application with YOLO-Based Bin "
            "Monitoring, Alerts, Reporting, and Fleet Operations\" submitted by "
            "Md. Muradul Islam, bearing ID# 22203234, has been prepared as part of the "
            "requirements for the award of Bachelor of Computer Science and Engineering "
            "(BCSE) at IUBAT-International University of Business Agriculture and Technology."
        ),
        paragraph(
            "The current draft has been written to align with the implemented project "
            "artifacts and with the supplied practicum report template."
        ),
        paragraph("_____________________________"),
        paragraph("Md. Khairul Islam"),
        paragraph("Supervisor and Lecturer"),
        paragraph("Department of Computer Science and Engineering"),
        paragraph("IUBAT-International University of Business Agriculture and Technology"),
        page_break(),
        paragraph("Abstract", style="Heading1"),
        paragraph(
            "The Smart Waste Management System (SWMS) is a PyQt5 desktop application "
            "for monitoring waste bins, recording detection events, managing alerts, "
            "generating reports, and handling supporting fleet operations. The current "
            "repository state shows that the system is no longer limited to a mock-only "
            "prototype. The detection engine loads two Ultralytics YOLO models from the "
            "`models` directory: one model for bin detection and one model for fill-level "
            "classification. The engine supports image inference, video-stream processing, "
            "and webcam-based monitoring, and it persists detection events into an SQLite "
            "database through SQLAlchemy."
        ),
        paragraph(
            "Beyond the original waste-management workflow, the application now includes "
            "a fleet subsystem covering trucks, drivers, routes, collection trips, "
            "maintenance logs, and fleet analytics. The repository defines twelve "
            "database tables in total: seven for the original waste-management module "
            "and five for fleet operations. The user interface contains role-aware "
            "navigation for operators, supervisors, and administrators. Operators can "
            "run detections and work with assigned trips, supervisors can manage alerts, "
            "drivers, and maintenance records, and administrators can manage users, "
            "settings, and the full system configuration."
        ),
        paragraph(
            "This report follows the official practicum template and is grounded in "
            "the code, models, diagrams, and database snapshot available on 26 May 2026. "
            "The testing chapter therefore reports verifiable repository facts such as "
            "existing model files, implemented screens, table counts, and persisted sample "
            "records, while explicitly avoiding unsupported claims. The result is an "
            "accurate technical report of the project in its present form."
        ),
        page_break(),
        paragraph("Acknowledgments", style="Heading1"),
        paragraph(
            "All praise to Almighty Allah for granting me the strength and patience "
            "required to complete this practicum project and the final report."
        ),
        paragraph(
            "I sincerely thank my supervisor, Md. Khairul Islam, for his guidance, "
            "review, and continuous support throughout the practicum work. I also thank "
            "Shahinur Alam for coordination and administrative support, and Prof. Dr. "
            "Utpal Kanti Das for departmental leadership during the practicum process."
        ),
        paragraph(
            "I am grateful to my family, classmates, and everyone who supported the "
            "development and documentation of this project."
        ),
        page_break(),
        paragraph("Table of Contents", style="Heading1"),
        paragraph("Letter of Transmittal"),
        paragraph("Organization's Certificate"),
        paragraph("Student's Declaration"),
        paragraph("Supervisor's Certification"),
        paragraph("Abstract"),
        paragraph("Acknowledgments"),
        paragraph("Chapter 1. Introduction"),
        paragraph("Chapter 2. Organizational Overview"),
        paragraph("Chapter 3. Requirement Engineering"),
        paragraph("Chapter 4. Analysis Modeling"),
        paragraph("Chapter 5. Risk Management"),
        paragraph("Chapter 6. Project Planning and Scheduling"),
        paragraph("Chapter 7. Project Cost Estimation"),
        paragraph("Chapter 8. Designing"),
        paragraph("Chapter 9. Testing"),
        paragraph("Chapter 10. Ethical Consideration and Sustainability"),
        paragraph("Chapter 11. Conclusion"),
        paragraph("References"),
        paragraph("List of Figures", style="Heading1"),
        paragraph("Figure 4.1 Use Case Diagram (Documents/Diagrams/SMWS_UseCase.drawio.png)"),
        paragraph("Figure 4.2-4.5 Activity Diagrams (Documents/Diagrams/SWMS_Activity_Diagram*.png)"),
        paragraph("Figure 4.6-4.8 Swimlane Diagrams (Documents/Diagrams/SWMS_Swimlane_Diagram*.png)"),
        paragraph("Figure 4.9-4.10 Sequence Diagrams (Documents/Diagrams/SWMS_Sequence_Diagram*.png)"),
        paragraph("Figure 4.11 Class Diagram (Documents/Diagrams/SWMS_Class_Diagram.drawio.png)"),
        paragraph("Figure 6.1 Gantt Chart (Documents/Diagrams/SWM_GanttChart.png)"),
        paragraph("Figure 8.1-8.4 DFDs (Documents/Diagrams/SWMS_DFD_*.png)"),
        paragraph("Figure 8.5 ER Diagram (Documents/Diagrams/SWMS_ERD.drawio.png)"),
        paragraph("List of Tables", style="Heading1"),
        paragraph("Table 3.1 Major Functional Areas"),
        paragraph("Table 3.2 Non-Functional Requirements"),
        paragraph("Table 8.1 Database Tables"),
        paragraph("Table 9.1 Repository Verification Summary"),
        page_break(),
        paragraph("Chapter 1. Introduction", style="Heading1"),
        paragraph("1.1 Background of the Study", style="Heading2"),
        paragraph(
            "Manual waste-recording processes create three practical problems for a "
            "small waste-management operation. First, paper or spreadsheet-based logging "
            "delays visibility into current bin conditions. Second, the absence of a "
            "structured digital history makes verification and auditing difficult. Third, "
            "manual monitoring cannot react quickly when bins become full or when a route "
            "or collection trip needs operational attention."
        ),
        paragraph(
            "The Smart Waste Management System addresses those gaps with a Windows desktop "
            "application that combines computer-vision-based bin monitoring, alert rules, "
            "historical records, PDF reporting, and an integrated fleet module. The project "
            "is suitable for environments where a local database and a desktop-first workflow "
            "are more practical than a cloud-only deployment."
        ),
        paragraph("1.2 Methodology", style="Heading2"),
        paragraph(
            "This report was prepared primarily through repository inspection. The codebase, "
            "database schema, local model files, current SQLite data, and existing diagrams "
            "were examined to establish factual project details. Existing practicum draft "
            "documents in the repository were used only for academic metadata such as student, "
            "supervisor, and organization names where those details were already recorded."
        ),
        paragraph(
            "Because the user explicitly requested an accurate report with no hallucination, "
            "unsupported claims from older drafts were removed. In particular, sections that "
            "described the detection engine as purely mock-based were corrected to reflect "
            "the present YOLO-based implementation."
        ),
        paragraph("1.3 Objectives", style="Heading2"),
        paragraph(
            "The broad objective of the practicum is to build a usable desktop system that "
            "records waste-bin monitoring events, supports staff through role-based access, "
            "raises actionable alerts, and provides traceable operational records."
        ),
        paragraph(
            "Specific objectives are to implement user authentication; persist detections and "
            "reports in SQLite; provide analytics dashboards; support image, video, and webcam "
            "detection workflows; generate PDF reports; manage SMTP-backed notifications; and "
            "extend the platform with fleet dashboards, trucks, drivers, routes, trips, and "
            "maintenance records."
        ),
        paragraph("1.4 Process Model", style="Heading2"),
        paragraph(
            "The repository structure indicates an incremental development pattern. The "
            "application first establishes core desktop infrastructure such as authentication, "
            "database initialization, and general waste-management screens. It then layers "
            "analytics, reporting, and finally a distinct fleet subsystem. This staged growth "
            "matches an iterative-incremental process better than a single-pass waterfall approach."
        ),
        paragraph("1.5 Feasibility Study", style="Heading2"),
        paragraph(
            "Technical feasibility is strong because the stack uses mature Python libraries: "
            "PyQt5 for the interface, SQLAlchemy for persistence, SQLite for local storage, "
            "Ultralytics YOLO and OpenCV for vision workflows, ReportLab for PDF generation, "
            "and bcrypt for password hashing. Operational feasibility is also strong because "
            "the application runs locally and does not require continuous internet access."
        ),
        paragraph(
            "Economic feasibility cannot be expressed here as a verified currency budget because "
            "the repository does not include audited cost records. To remain accurate, the cost "
            "discussion in this report is limited to identifiable cost drivers rather than invented "
            "monetary values."
        ),
        paragraph("1.6 Structure of the Report", style="Heading2"),
        paragraph(
            "The remaining chapters cover the organizational setting, requirements, analysis "
            "artifacts, risk considerations, planning, cost drivers, design, testing evidence, "
            "ethics, sustainability, and conclusion."
        ),
        page_break(),
        paragraph("Chapter 2. Organizational Overview", style="Heading1"),
        paragraph("2.1 Organization Vision", style="Heading2"),
        paragraph(
            "Existing practicum documents in the repository identify the host organization as "
            "AIQNIC, a Dhaka-based organization working in AI-enabled software and data solutions. "
            "Its documented vision emphasizes the practical use of intelligent systems to solve "
            "real operational problems."
        ),
        paragraph("2.2 Organization Mission", style="Heading2"),
        paragraph(
            "The organization context recorded in the existing draft materials describes a mission "
            "centered on delivering applied AI, data, and software engineering solutions for real "
            "business workflows."
        ),
        paragraph("2.3 Organization Services", style="Heading2"),
        paragraph(
            "The same repository documents mention services including software engineering, "
            "predictive analytics, natural language processing, computer vision, MLOps, and data "
            "science consulting. The present practicum project aligns most closely with the "
            "computer vision and software engineering categories."
        ),
        paragraph("2.4 Organizational Structure", style="Heading2"),
        paragraph(
            "The repository already contains an organizational overview and figure references in "
            "earlier report drafts. For this final technical report, the key point is that the "
            "practicum context involved academic supervision and an applied project environment "
            "suitable for a desktop operational system."
        ),
        paragraph("2.5 My Position in this Organization", style="Heading2"),
        paragraph(
            "Within the practicum context, the student's role was that of a software developer and "
            "system integrator responsible for requirements interpretation, UI implementation, "
            "database design, service-layer development, and final reporting."
        ),
        paragraph("2.6 Address of the Organization", style="Heading2"),
        paragraph(
            "The formal university address appears in the letter of transmittal. The host "
            "organization address is not separately verifiable from the codebase and is therefore "
            "not restated here without documentary confirmation."
        ),
        page_break(),
        paragraph("Chapter 3. Requirement Engineering", style="Heading1"),
        paragraph("3.1 Requirement Engineering Process", style="Heading2"),
        paragraph(
            "The implemented system suggests a straightforward requirement flow: identify user roles, "
            "define their actions, map those actions to UI screens, and persist each workflow through "
            "database tables and service methods. This can be observed directly in `ui/main_window.py`, "
            "`ui/widgets/sidebar.py`, the SQLAlchemy models, and the service classes under `core`."
        ),
        paragraph("3.2 Requirement Elicitation", style="Heading2"),
        paragraph(
            "The current requirements are visible through the interface composition itself. The sidebar "
            "exposes the primary modules: Dashboard, Detection, Waste History, Fleet Dashboard, Trucks, "
            "Drivers, Routes, Trips, Maintenance, Users, Alerts, Reports, and Settings. Permission rules "
            "in `core/fleet/fleet_permissions.py` and the general role hierarchy in `core/auth_manager.py` "
            "show how those requirements were translated into access rules."
        ),
        paragraph("3.3 Requirement Analysis", style="Heading2"),
        paragraph(
            "Three actors exist in the current implementation: administrator, supervisor, and operator. "
            "Administrators manage users and application settings. Supervisors manage alerts, drivers, "
            "maintenance, and full trip editing. Operators can run detections, inspect history, view the "
            "fleet dashboard, and work with trips and routes within their permitted scope."
        ),
        paragraph("3.4 Requirement Specifications", style="Heading2"),
        paragraph("Table 3.1 Major Functional Areas"),
        table(
            [
                ["Area", "Implemented capability"],
                ["Authentication", "Login, bcrypt password verification, default admin seeding"],
                ["Detection", "Image, video, and webcam workflows backed by YOLO models"],
                ["History", "Filtering, status updates, notes, CSV export, Excel export"],
                ["Alerts", "Rule CRUD, fill-level thresholds, email notification, acknowledgement"],
                ["Reports", "PDF generation, history of generated reports, deletion and opening"],
                ["Settings", "SMTP, company name, alert toggle, confidence threshold, backup, logs"],
                ["Fleet", "Dashboard, trucks, drivers, routes, trips, maintenance, analytics"],
            ],
            widths=[2200, 6900],
        ),
        paragraph("3.4.1 User Requirements", style="Heading2"),
        paragraph(
            "Users require a desktop interface that supports their role without exposing unrelated "
            "administrative functions. They also require visual feedback, persisted history, and the "
            "ability to continue working on a local machine."
        ),
        paragraph("3.4.2 System Requirements", style="Heading2"),
        paragraph(
            "The system requires Python dependencies listed in `requirements.txt`, accessible YOLO model "
            "files in the `models` directory, write access to the local `data` and `database` folders, "
            "and a Windows environment capable of running a PyQt5 desktop application."
        ),
        paragraph("3.4.3 Functional Requirements", style="Heading2"),
        paragraph(
            "The codebase implements model loading, detection persistence, alert evaluation, report "
            "generation, fleet CRUD operations, maintenance scheduling, activity logging, and settings "
            "persistence. It also enforces role-aware access at both UI and service levels."
        ),
        paragraph("3.4.4 Non-Functional Requirements", style="Heading2"),
        paragraph("Table 3.2 Non-Functional Requirements"),
        table(
            [
                ["Quality attribute", "Current evidence"],
                ["Security", "Passwords hashed with bcrypt; role-aware UI and service checks"],
                ["Maintainability", "Separated `ui`, `core`, and `database` packages"],
                ["Portability", "Desktop Python stack with local SQLite storage"],
                ["Traceability", "Activity logs, generated report records, persisted detections"],
                ["Scalability", "Adequate for local deployment; SQLite bounds enterprise scale"],
            ],
            widths=[2600, 6500],
        ),
        paragraph("3.5 Use Case Diagram", style="Heading2"),
        paragraph(
            "The repository includes `Documents/Diagrams/SMWS_UseCase.drawio.png`, which corresponds "
            "to the core actor interactions described above."
        ),
        page_break(),
        paragraph("Chapter 4. Analysis Modeling", style="Heading1"),
        paragraph("4.1 Activity Diagrams", style="Heading2"),
        paragraph(
            "The repository contains four activity diagrams for the major workflows: authentication, "
            "waste detection, detection verification, and report generation. These files are stored as "
            "`SWMS_Activity_Diagram1.drawio.png` through `SWMS_Activity_Diagram4.drawio.png`."
        ),
        paragraph("4.2 Swimlane Diagrams", style="Heading2"),
        paragraph(
            "Three swimlane diagrams are present for end-to-end detection workflow, alert-rule lifecycle, "
            "and user-management behavior. These artifacts are useful because responsibility in the system "
            "is split among operators, supervisors, administrators, services, and the database."
        ),
        paragraph("4.3 Sequence Diagrams", style="Heading2"),
        paragraph(
            "Two sequence diagrams are available: one for the detection process and one for alert triggering. "
            "They align with the actual call flow from UI workers to `DetectionEngine`, `AlertManager`, and "
            "database persistence."
        ),
        paragraph("4.4 CRC Cards", style="Heading2"),
        paragraph(
            "The implemented domain objects that most clearly map to CRC-style analysis are User, Detection, "
            "AlertRule, Alert, Report, ActivityLog, AppSetting, Truck, Driver, Route, CollectionTrip, and "
            "MaintenanceRecord."
        ),
        paragraph("4.5 Class Diagram", style="Heading2"),
        paragraph(
            "The class diagram file `Documents/Diagrams/SWMS_Class_Diagram.drawio.png` corresponds closely "
            "to the SQLAlchemy models defined in `database/models.py` and `database/fleet_models.py`."
        ),
        page_break(),
        paragraph("Chapter 5. Risk Management", style="Heading1"),
        paragraph("5.1 Risk Management Overview", style="Heading2"),
        paragraph(
            "The main project risks visible from the repository are model availability, local data integrity, "
            "SMTP configuration failure, permission mistakes, and long-term maintainability."
        ),
        paragraph("5.2 Risk Identification", style="Heading2"),
        paragraph(
            "If either YOLO model file is missing, detection fails. If the SQLite database is corrupted or "
            "deleted, history and configuration are lost unless a backup exists. If SMTP settings are invalid, "
            "email alerts fail. If role checks are incomplete, users may see or modify actions outside their "
            "authority."
        ),
        paragraph("5.3 Risk Analysis", style="Heading2"),
        paragraph(
            "Model-file availability is a medium-to-high operational risk because the detection engine directly "
            "depends on `models/best.pt` and optionally `models/best_bin_level.pt`. Data-loss risk is medium "
            "because the system uses a local SQLite database; however, the Settings screen provides a database "
            "backup feature. SMTP risk is medium because alert recording still works even if email sending fails."
        ),
        paragraph("5.4 Risk Planning", style="Heading2"),
        paragraph(
            "Mitigation is already visible in the implementation. The detection engine checks for missing model "
            "files and returns structured error messages. The alert manager commits alert rows before attempting "
            "email delivery so SMTP failure cannot erase triggered alerts. The settings module allows the operator "
            "to export a database backup. Service-level permission checks provide defense beyond the UI."
        ),
        page_break(),
        paragraph("Chapter 6. Project Planning and Scheduling", style="Heading1"),
        paragraph("6.1 Overview", style="Heading2"),
        paragraph(
            "The repository includes a Gantt chart image at `Documents/Diagrams/SWM_GanttChart.png`, indicating "
            "that scheduling was documented as a formal project artifact. The implemented system also shows a "
            "logical delivery order: database and auth foundation first, core waste-management workflow next, "
            "analytics and reporting after that, and the fleet subsystem as a later major increment."
        ),
        paragraph("6.2 Function Point Estimation", style="Heading2"),
        paragraph(
            "A strict function-point recalculation is omitted here because the repository does not contain an "
            "auditable estimation worksheet. Still, the present application clearly spans multiple external inputs "
            "(login, CRUD forms, filters, settings), outputs (dashboards, alerts, reports, exports), internal files "
            "(twelve database tables), and inquiries (history views, report history, fleet analytics)."
        ),
        paragraph("6.3 Project Scheduling", style="Heading2"),
        paragraph(
            "A practical schedule for this repository state can be read in four major blocks: foundation and schema, "
            "core waste-management workflows, analytics and reporting, and fleet operations. This matches the actual "
            "code organization better than an unverified day-by-day schedule."
        ),
        page_break(),
        paragraph("Chapter 7. Project Cost Estimation", style="Heading1"),
        paragraph("7.1 Overview", style="Heading2"),
        paragraph(
            "The repository does not provide verified expense ledgers or signed cost sheets. To preserve accuracy, "
            "this chapter identifies cost drivers only."
        ),
        paragraph("7.2 Personnel Cost", style="Heading2"),
        paragraph(
            "The primary cost driver is development time for analysis, UI implementation, service-layer coding, "
            "database design, diagram preparation, debugging, and documentation."
        ),
        paragraph("7.3 Hardware Cost", style="Heading2"),
        paragraph(
            "The system is intended for a standard Windows workstation with sufficient storage for the local database, "
            "model files, result images, and generated reports."
        ),
        paragraph("7.4 Software Cost", style="Heading2"),
        paragraph(
            "The software stack is primarily open source: Python, PyQt5, SQLAlchemy, bcrypt, matplotlib, ReportLab, "
            "OpenCV, Ultralytics, Pillow, NumPy, and openpyxl. This keeps direct licensing cost low in an educational "
            "or internal deployment context."
        ),
        paragraph("7.5 Other Cost", style="Heading2"),
        paragraph(
            "Additional costs may include email service administration, data collection for model improvement, user "
            "training, and ongoing maintenance. No verified monetary figures are stated here because they are not "
            "available in the repository."
        ),
        page_break(),
        paragraph("Chapter 8. Designing", style="Heading1"),
        paragraph("8.1 Data Flow Diagrams", style="Heading2"),
        paragraph(
            "The repository contains a context diagram (`SWMS_DFD_0.drawio.png`), a level-1 DFD (`SWMS_DFD_1.drawio.png`), "
            "and two deeper level-2 diagrams (`SWMS_DFD_2.1.drawio.png`, `SWMS_DFD_2.2.drawio.png`). These diagrams reflect "
            "the application's separation between user actions, service logic, database persistence, and generated outputs."
        ),
        paragraph("8.2 ER Diagram", style="Heading2"),
        paragraph(
            "The entity-relationship diagram file `SWMS_ERD.drawio.png` is consistent with the current SQLAlchemy schema."
        ),
        paragraph("8.3 Database Field Design", style="Heading2"),
        paragraph("Table 8.1 Database Tables"),
        table(
            [
                ["Table", "Purpose"],
                ["users", "Credentials, profile data, roles, activation state"],
                ["detections", "Persisted detection records and fill-level results"],
                ["alert_rules", "Configured fill-level thresholds and notification targets"],
                ["alerts", "Triggered alerts and acknowledgement state"],
                ["activity_logs", "Recorded user and system activities"],
                ["reports", "Generated report metadata"],
                ["app_settings", "SMTP, company, and confidence settings"],
                ["fleet_trucks", "Truck master data and lifecycle state"],
                ["fleet_drivers", "Driver records and optional truck assignments"],
                ["fleet_routes", "Route definitions and zone data"],
                ["fleet_trips", "Trip execution data linking truck, driver, and route"],
                ["fleet_maintenance", "Service history and next-service tracking"],
            ],
            widths=[2500, 6800],
        ),
        paragraph("8.4 Interface Design", style="Heading2"),
        paragraph(
            "The interface uses a stacked-window desktop layout with a role-sensitive sidebar. The waste-management "
            "portion includes Dashboard, Detection, History, Alerts, Reports, Users, and Settings. The fleet section "
            "adds Fleet Dashboard, Trucks, Drivers, Routes, Trips, and Maintenance. This structure is directly visible "
            "in `ui/main_window.py` and `ui/widgets/sidebar.py`."
        ),
        paragraph(
            "The Detection screen is the most technically dense interface. It supports image, video, and webcam input, "
            "runs background workers, presents annotated frames, and aggregates unique detections in streaming mode using "
            "YOLO tracking identifiers where available."
        ),
        page_break(),
        paragraph("Chapter 9. Testing", style="Heading1"),
        paragraph("9.1 Repository Verification Summary", style="Heading2"),
        paragraph(
            "No automated test suite is implemented under the `tests` package, so this chapter reports verifiable "
            "evidence gathered from the current repository and database snapshot on 26 May 2026."
        ),
        paragraph("Table 9.1 Repository Verification Summary"),
        table(
            [
                ["Item", "Verified evidence"],
                ["Database schema", "12 SQLAlchemy tables registered across waste and fleet modules"],
                ["Model assets", "4 model-related files present; `best.pt` and `best_bin_level.pt` available"],
                ["User roles", "3 roles present in DB snapshot: admin, supervisor, operator"],
                ["Detection records", "62 persisted detections in SQLite snapshot"],
                ["Alert workflow", "1 alert rule and 7 alerts present in snapshot; alert manager supports email and acknowledgement"],
                ["Report workflow", "Report engine implemented; 2 report records present in snapshot"],
                ["Fleet workflow", "Fleet tables populated with trucks, driver, route, trip, and maintenance sample data"],
                ["Diagrams", "17 diagram assets present under `Documents/Diagrams`"],
            ],
            widths=[2500, 6800],
        ),
        paragraph(
            "In addition to the database snapshot, the code confirms that detections can be exported to CSV and Excel, "
            "generated reports can be opened or deleted from the UI, and database backups can be exported from Settings."
        ),
        page_break(),
        paragraph("Chapter 10. Ethical Consideration and Sustainability", style="Heading1"),
        paragraph("10.1 Ethical Considerations", style="Heading2"),
        paragraph(
            "The system stores user credentials, operational history, and generated alerts. Ethical handling of that data "
            "requires password hashing, controlled access, and careful use of backups. The current implementation hashes "
            "passwords with bcrypt and separates privileges by role."
        ),
        paragraph(
            "A second ethical issue is representational accuracy in computer vision. Because this repository uses trained "
            "model files for bin and fill-level analysis, future deployment should evaluate those models with real local "
            "data before operational dependence is increased. This is especially important if the system is later extended "
            "beyond bin monitoring into broader waste categorization."
        ),
        paragraph("10.2 Sustainability Through Software Engineering", style="Heading2"),
        paragraph(
            "From a software-engineering perspective, the project supports sustainability through modular separation of UI, "
            "business logic, and persistence. It also uses predominantly open-source dependencies and a local database, which "
            "reduces infrastructure overhead for small deployments. The fleet subsystem further supports operational sustainability "
            "by tracking maintenance deadlines and trip records."
        ),
        page_break(),
        paragraph("Chapter 11. Conclusion", style="Heading1"),
        paragraph("11.1 Conclusion", style="Heading2"),
        paragraph(
            "The Smart Waste Management System in its current repository state is a substantial desktop application rather than "
            "a shell. It combines waste-bin monitoring, historical recordkeeping, alerting, PDF reporting, activity logging, "
            "settings management, and a separate fleet-operations module. The database schema, UI structure, and local model "
            "assets confirm that the project has advanced beyond the earlier mock-only description found in previous drafts."
        ),
        paragraph("11.2 Limitation", style="Heading2"),
        paragraph(
            "The current report deliberately avoids unsupported cost figures, page-numbered tables of contents, and external "
            "organizational claims that cannot be verified from the repository. The project also lacks an automated test suite, "
            "and long-term production readiness would benefit from broader model evaluation, migration handling, and documented "
            "deployment procedures."
        ),
        paragraph("11.3 Future Plan", style="Heading2"),
        paragraph(
            "Recommended next steps are to add automated tests, formalize migrations for schema evolution, expand reporting to "
            "cover fleet analytics, evaluate model performance on a documented validation set, and embed the existing diagram "
            "assets directly into the final academic submission if required."
        ),
        page_break(),
        paragraph("References", style="Heading1"),
        paragraph("PyQt5 documentation."),
        paragraph("SQLAlchemy documentation."),
        paragraph("Ultralytics YOLO documentation."),
        paragraph("OpenCV documentation."),
        paragraph("ReportLab documentation."),
        paragraph("bcrypt documentation."),
        paragraph("Local repository artifacts: source code, diagrams, SQLite database, and existing practicum draft documents."),
    )

    return doc


def write_docx(base_docx: Path, output_docx: Path):
    document = build_document()
    body = document.find(w("body"))
    body.append(get_base_sectpr(base_docx))
    xml_bytes = ET.tostring(document, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(base_docx, "r") as zin, zipfile.ZipFile(output_docx, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == "word/document.xml":
                zout.writestr(item, xml_bytes)
            else:
                zout.writestr(item, zin.read(item.filename))


def main():
    repo_root = Path(__file__).resolve().parents[1]
    base_docx = repo_root / "Documents" / "Report.docx"
    output_docx = repo_root / "Documents" / "SWMS_Practicum_Final_Report_Accurate.docx"
    if not base_docx.exists():
        raise FileNotFoundError(base_docx)
    write_docx(base_docx, output_docx)
    print(output_docx)


if __name__ == "__main__":
    main()
