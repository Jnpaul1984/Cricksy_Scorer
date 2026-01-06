"""PDF export service for video analysis results."""

import io
import logging
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

logger = logging.getLogger(__name__)


def generate_analysis_pdf(
    job_id: str,
    session_title: str,
    status: str,
    quick_findings: dict[str, Any] | None,
    deep_findings: dict[str, Any] | None,
    quick_results: dict[str, Any] | None,
    deep_results: dict[str, Any] | None,
    created_at: datetime,
    completed_at: datetime | None,
) -> bytes:
    """
    Generate a PDF report from video analysis results.

    Args:
        job_id: Analysis job ID
        session_title: Video session title
        status: Job status
        quick_findings: Quick analysis findings
        deep_findings: Deep analysis findings
        quick_results: Full quick analysis results
        deep_results: Full deep analysis results
        created_at: Job creation timestamp
        completed_at: Job completion timestamp

    Returns:
        PDF bytes
    """
    logger.info(f"Generating PDF for job {job_id}")
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=10,
        spaceBefore=12,
    )
    body_style = styles['BodyText']
    
    # Title
    elements.append(Paragraph("Video Analysis Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Session metadata
    metadata_data = [
        ['Session:', session_title],
        ['Job ID:', job_id],
        ['Status:', status.upper()],
        ['Created:', created_at.strftime('%Y-%m-%d %H:%M:%S UTC')],
    ]
    if completed_at:
        metadata_data.append(['Completed:', completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')])
    
    metadata_table = Table(metadata_data, colWidths=[1.5*inch, 5*inch])
    metadata_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONT', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2C3E50')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(metadata_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Quick Analysis Section
    if quick_findings or quick_results:
        elements.append(Paragraph("Quick Analysis", heading_style))
        
        if quick_findings:
            findings_text = _format_findings(quick_findings)
            elements.append(Paragraph(findings_text, body_style))
        elif quick_results:
            # Fallback: extract summary from results
            summary = _extract_summary_from_results(quick_results, "Quick")
            elements.append(Paragraph(summary, body_style))
        
        elements.append(Spacer(1, 0.2*inch))
    
    # Deep Analysis Section
    if deep_findings or deep_results:
        elements.append(Paragraph("Deep Analysis", heading_style))
        
        if deep_findings:
            findings_text = _format_findings(deep_findings)
            elements.append(Paragraph(findings_text, body_style))
        elif deep_results:
            # Fallback: extract summary from results
            summary = _extract_summary_from_results(deep_results, "Deep")
            elements.append(Paragraph(summary, body_style))
        
        elements.append(Spacer(1, 0.2*inch))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    pdf_size_kb = len(pdf_bytes) / 1024
    logger.info(f"Generated PDF for job {job_id}: {pdf_size_kb:.2f} KB")
    
    return pdf_bytes


def _format_findings(findings: dict[str, Any]) -> str:
    """Format findings dictionary as readable text."""
    lines = []
    
    for key, value in findings.items():
        # Convert snake_case to Title Case
        label = key.replace('_', ' ').title()
        
        if isinstance(value, dict):
            lines.append(f"<b>{label}:</b>")
            for sub_key, sub_value in value.items():
                sub_label = sub_key.replace('_', ' ').title()
                lines.append(f"  • {sub_label}: {sub_value}")
        elif isinstance(value, list):
            lines.append(f"<b>{label}:</b>")
            for item in value:
                lines.append(f"  • {item}")
        else:
            lines.append(f"<b>{label}:</b> {value}")
    
    return '<br/>'.join(lines) if lines else "No detailed findings available."


def _extract_summary_from_results(results: dict[str, Any], stage: str) -> str:
    """Extract a summary from raw results JSON."""
    lines = [f"<b>{stage} analysis completed.</b><br/><br/>"]
    
    # Try to extract pose summary
    pose_summary = results.get('pose_summary') or results.get('pose', {})
    if pose_summary:
        if isinstance(pose_summary, dict):
            detection_rate = pose_summary.get('detection_rate_percent', 'N/A')
            total_frames = pose_summary.get('total_frames', 'N/A')
            lines.append(f"<b>Pose Detection:</b> {detection_rate}% detection rate across {total_frames} frames")
    
    # Try to extract evidence
    evidence = results.get('evidence', {})
    if evidence:
        lines.append("<br/><b>Key Findings:</b>")
        for metric, data in evidence.items():
            metric_label = metric.replace('_', ' ').title()
            threshold = data.get('threshold', 'N/A')
            lines.append(f"  • {metric_label}: Threshold = {threshold}")
    
    return '<br/>'.join(lines) if len(lines) > 1 else f"{stage} analysis data available in full results JSON."
