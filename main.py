#!/usr/bin/env python3
"""
Report Template Generator - FastAPI Server

Offline pentest report generator with LLM-assisted finding content.
- Upload DOCX templates (client-specific, test-type specific)
- Chat findings to the app
- LLM generates professional report sections
- Export filled DOCX ready for delivery
- Store anonymized reports on NAS

Runs on Mac Mini #2 with local Ollama integration.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import uvicorn
import sys
from pathlib import Path
from typing import List, Optional

from config import (
    SERVER_HOST,
    SERVER_PORT,
    DEBUG,
    LOG_LEVEL,
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    STATIC_DIR,
    TEMPLATES_DIR,
    REPORTS_DIR,
)
from ollama_service import check_ollama_health, generate_finding_content
from docx_service import DocxTemplateHandler, validate_template
from storage_service import NASStorage

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize services
template_handler = DocxTemplateHandler()
nas_storage = NASStorage()

# Create FastAPI app
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ============ Models ============


class FindingInput(BaseModel):
    """User input for a finding during testing."""

    finding_description: str
    vulnerability_type: Optional[str] = None
    template_name: str


class ReportRequest(BaseModel):
    """Request to generate a report from findings."""

    template_name: str
    findings: List[FindingInput]
    report_name: str


# ============ Routes ============


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "status": "running",
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check - verify Ollama connectivity."""
    ollama_healthy = await check_ollama_health()
    nas_info = nas_storage.get_storage_info()

    if not ollama_healthy:
        raise HTTPException(status_code=503, detail="Ollama not available")

    return {
        "status": "healthy",
        "ollama": "connected" if ollama_healthy else "disconnected",
        "nas": nas_info["status"],
    }


@app.post("/upload-template")
async def upload_template(file: UploadFile):
    """Upload a DOCX template for reports."""
    try:
        if not file.filename.endswith(".docx"):
            raise HTTPException(status_code=400, detail="File must be .docx")

        # Save template
        template_path = TEMPLATES_DIR / file.filename
        with open(template_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Validate template
        if not validate_template(template_path):
            template_path.unlink()
            raise HTTPException(status_code=400, detail="Invalid DOCX file")

        logger.info(f"Template uploaded: {file.filename}")

        return {
            "status": "success",
            "message": "Template uploaded successfully",
            "template_name": file.filename.replace(".docx", ""),
            "filename": file.filename,
        }

    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates")
async def list_templates():
    """List available templates."""
    try:
        templates = template_handler.get_available_templates()
        return {
            "status": "success",
            "count": len(templates),
            "templates": templates,
        }
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-finding")
async def generate_finding(finding: FindingInput):
    """
    Generate finding content using LLM.

    Input: User description of a finding (e.g., "SQLI in /api/users, POST, authenticated")
    Output: Professional finding with title, description, remediation, WSTG reference
    """
    try:
        logger.info(f"Generating finding content for: {finding.finding_description}")

        # Call Ollama to generate content
        result = await generate_finding_content(finding.finding_description)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result.get("error"))

        content = result.get("content", {})

        return {
            "status": "success",
            "finding": {
                "title": content.get("title", "N/A"),
                "description_impact": content.get("description_impact", "N/A"),
                "remediation": content.get("remediation", "N/A"),
                "wstg_reference": content.get("wstg_reference", "N/A"),
                "type": finding.vulnerability_type,
            },
        }

    except Exception as e:
        logger.error(f"Error generating finding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-report")
async def generate_report(report_request: ReportRequest):
    """
    Generate a complete report from findings.

    Steps:
    1. Load template
    2. For each finding, generate content via LLM
    3. Fill in template
    4. Save to local reports directory
    5. Save anonymized metadata to NAS
    6. Return download link
    """
    try:
        logger.info(f"Generating report: {report_request.report_name}")

        # Load template
        try:
            doc = template_handler.load_template(report_request.template_name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Template not found")

        # Generate findings
        generated_findings = []
        finding_types = set()

        for idx, finding_input in enumerate(report_request.findings):
            logger.info(f"Processing finding {idx + 1}/{len(report_request.findings)}")

            # Generate content via LLM
            result = await generate_finding_content(finding_input.finding_description)

            if "error" not in result:
                content = result.get("content", {})
                generated_findings.append(
                    {
                        "title": content.get("title", "Finding"),
                        "description_impact": content.get("description_impact", ""),
                        "remediation": content.get("remediation", ""),
                        "wstg_reference": content.get("wstg_reference", ""),
                        "type": finding_input.vulnerability_type or "Unknown",
                    }
                )
                finding_types.add(finding_input.vulnerability_type or "Unknown")

        # Fill in findings
        for idx, finding in enumerate(generated_findings):
            # Try to replace placeholders first
            template_handler.fill_finding(doc, finding, idx + 1)

        # Save report locally
        report_filename = f"{report_request.report_name}_{len(generated_findings)}_findings.docx"
        report_path = template_handler.save_report(doc, report_filename)

        # Save metadata to NAS (anonymized)
        nas_storage.save_report_metadata(
            report_request.report_name,
            len(generated_findings),
            list(finding_types),
        )

        # Save findings summary to NAS (anonymized)
        nas_storage.save_findings_summary(
            report_request.report_name,
            generated_findings,
        )

        logger.info(f"Report generated: {report_filename}")

        return {
            "status": "success",
            "message": "Report generated successfully",
            "report_name": report_filename,
            "findings_count": len(generated_findings),
            "download_url": f"/download-report/{report_filename}",
            "nas_saved": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download-report/{filename}")
async def download_report(filename: str):
    """Download a generated report."""
    try:
        report_path = template_handler.get_report_path(filename)

        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")

        return FileResponse(
            report_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename,
        )

    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/storage-info")
async def storage_info():
    """Get NAS storage information."""
    try:
        info = nas_storage.get_storage_info()
        return {
            "status": "success",
            "storage": info,
        }
    except Exception as e:
        logger.error(f"Error getting storage info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports")
async def list_reports():
    """List stored reports on NAS."""
    try:
        reports = nas_storage.list_reports()
        return {
            "status": "success",
            "count": len(reports),
            "reports": reports,
        }
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "detail": exc.detail,
        },
    )


def main():
    """Run the server."""
    try:
        logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
        logger.info(f"Listening on {SERVER_HOST}:{SERVER_PORT}")
        logger.info(f"API docs available at http://localhost:{SERVER_PORT}/docs")

        uvicorn.run(
            "main:app",
            host=SERVER_HOST,
            port=SERVER_PORT,
            reload=DEBUG,
            log_level=LOG_LEVEL.lower(),
        )
    except KeyboardInterrupt:
        logger.info("Server interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
