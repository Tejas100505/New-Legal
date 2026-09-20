"""
Report Generation Agent for the E-Discovery platform.

Exports reports in PDF (real via reportlab), DOCX (real via python-docx), Markdown, CSV, and JSON.
"""

import base64
import csv
import io
import json
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, AgentException
from loguru import logger

# Try imports for reportlab and docx
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class ReportInput(BaseModel):
    document_id: str
    format: str = "markdown"  # markdown, json, csv, pdf, docx
    review_data: Dict[str, Any] = Field(default_factory=dict)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ReportOutput(BaseModel):
    document_id: str
    format: str
    content: str  # Raw text for MD/CSV/JSON, Base64-encoded for PDF/DOCX
    confidence_score: float


class ReportAgent(BaseAgent[ReportInput, ReportOutput]):
    """
    Generates exportable reports in multiple formats.
    """

    def __init__(self):
        super().__init__(
            name="ReportAgent",
            prompt_version="1.1.0",
            input_model=ReportInput,
            output_model=ReportOutput,
        )

    def _to_markdown(self, inp: ReportInput) -> str:
        lines = [
            f"# E-Discovery Review Report",
            f"**Document ID:** {inp.document_id}",
            "",
            "## Timeline",
        ]
        if inp.timeline:
            for event in inp.timeline:
                lines.append(f"- **{event.get('date', 'N/A')}**: {event.get('description', '')}")
        else:
            lines.append("_No timeline events._")

        lines.extend(["", "## Risk Assessment"])
        if inp.risks:
            for risk in inp.risks:
                lines.append(f"- **{risk.get('category', 'Unknown')}**: {risk.get('risk_level', 'N/A')} — {risk.get('reason', '')}")
        else:
            lines.append("_No risk assessments._")

        lines.extend(["", "## Evidence & Review Data"])
        if inp.review_data:
            lines.append(f"Total documents reviewed: {inp.review_data.get('total_documents', 0)}")
            for k, v in inp.review_data.items():
                if k != "total_documents":
                    lines.append(f"- **{k}**: {v}")
        else:
            lines.append("_No review data available._")

        lines.extend(["", "## Recommendations"])
        if inp.recommendations:
            for rec in inp.recommendations:
                lines.append(f"- {rec}")
        else:
            lines.append("_No recommendations._")

        return "\n".join(lines)

    def _to_json(self, inp: ReportInput) -> str:
        report = {
            "document_id": inp.document_id,
            "timeline": inp.timeline,
            "risks": inp.risks,
            "review_data": inp.review_data,
            "recommendations": inp.recommendations,
        }
        return json.dumps(report, indent=2, default=str)

    def _to_csv(self, inp: ReportInput) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Section", "Key", "Value"])

        for event in inp.timeline:
            writer.writerow(["Timeline", event.get("date", ""), event.get("description", "")])
        for risk in inp.risks:
            writer.writerow(["Risk", risk.get("category", ""), f"{risk.get('risk_level', '')}: {risk.get('reason', '')}"])
        for rec in inp.recommendations:
            writer.writerow(["Recommendation", "", rec])

        return output.getvalue()

    def _to_pdf(self, inp: ReportInput) -> str:
        """Generates a real PDF file and returns its Base64 encoded string."""
        if not REPORTLAB_AVAILABLE:
            raise AgentException("ReportLab is not installed or available.")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()
        
        # Add custom styles safely
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor='#1e293b',
            alignment=TA_CENTER,
            spaceAfter=20
        )
        section_style = ParagraphStyle(
            'ReportSection',
            parent=styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor='#4f46e5',
            spaceBefore=15,
            spaceAfter=8
        )
        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor='#334155',
            spaceAfter=6
        )

        story = []
        story.append(Paragraph("E-Discovery Review Report", title_style))
        story.append(Paragraph(f"<b>Document ID:</b> {inp.document_id}", body_style))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Timeline Events", section_style))
        if inp.timeline:
            for event in inp.timeline:
                date = event.get('date', 'N/A')
                desc = event.get('description', '')
                story.append(Paragraph(f"• <b>{date}</b>: {desc}", body_style))
        else:
            story.append(Paragraph("<i>No timeline events extracted.</i>", body_style))

        story.append(Spacer(1, 10))
        story.append(Paragraph("Risk Assessment", section_style))
        if inp.risks:
            for risk in inp.risks:
                cat = risk.get('category', 'Unknown')
                level = risk.get('risk_level', 'N/A')
                reason = risk.get('reason', '')
                story.append(Paragraph(f"• <b>[{level}] {cat}</b>: {reason}", body_style))
        else:
            story.append(Paragraph("<i>No risks flagged.</i>", body_style))

        story.append(Spacer(1, 10))
        story.append(Paragraph("Recommendations", section_style))
        if inp.recommendations:
            for rec in inp.recommendations:
                story.append(Paragraph(f"• {rec}", body_style))
        else:
            story.append(Paragraph("<i>No recommendations.</i>", body_style))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return base64.b64encode(pdf_bytes).decode('utf-8')

    def _to_docx(self, inp: ReportInput) -> str:
        """Generates a real Word DOCX file and returns its Base64 encoded string."""
        if not DOCX_AVAILABLE:
            raise AgentException("python-docx is not installed or available.")

        doc = docx.Document()
        doc.add_heading('E-Discovery Review Report', level=0)
        doc.add_paragraph(f'Document ID: {inp.document_id}')

        doc.add_heading('Timeline Events', level=1)
        if inp.timeline:
            for event in inp.timeline:
                date = event.get('date', 'N/A')
                desc = event.get('description', '')
                doc.add_paragraph(f'{date}: {desc}', style='List Bullet')
        else:
            doc.add_paragraph('No timeline events extracted.')

        doc.add_heading('Risk Assessment', level=1)
        if inp.risks:
            for risk in inp.risks:
                cat = risk.get('category', 'Unknown')
                level = risk.get('risk_level', 'N/A')
                reason = risk.get('reason', '')
                doc.add_paragraph(f'[{level}] {cat}: {reason}', style='List Bullet')
        else:
            doc.add_paragraph('No risks flagged.')

        doc.add_heading('Recommendations', level=1)
        if inp.recommendations:
            for rec in inp.recommendations:
                doc.add_paragraph(rec, style='List Bullet')
        else:
            doc.add_paragraph('No recommendations.')

        buffer = io.BytesIO()
        doc.save(buffer)
        docx_bytes = buffer.getvalue()
        buffer.close()

        return base64.b64encode(docx_bytes).decode('utf-8')

    async def _execute(self, validated_input: ReportInput) -> dict:
        logger.info(f"[{self.name}] Generating {validated_input.format} report for {validated_input.document_id}")

        fmt = validated_input.format.lower()
        generators = {
            "markdown": self._to_markdown,
            "json": self._to_json,
            "csv": self._to_csv,
            "pdf": self._to_pdf,
            "docx": self._to_docx,
        }

        generator = generators.get(fmt)
        if not generator:
            raise AgentException(f"Unsupported report format: {fmt}")

        content = generator(validated_input)

        return {
            "document_id": validated_input.document_id,
            "format": fmt,
            "content": content,
            "confidence_score": 1.0,
        }
