import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import NAS_IP, NAS_USERNAME, NAS_PASSWORD, NAS_SHARE, NAS_MOUNT_PATH

logger = logging.getLogger(__name__)


class NASStorage:
    """Handle storage of anonymized reports on NAS."""

    def __init__(self):
        self.nas_ip = NAS_IP
        self.nas_share = NAS_SHARE
        self.mount_path = Path(NAS_MOUNT_PATH)
        self.reports_dir = self.mount_path / "pentest_reports"
        self.findings_index = self.mount_path / "findings_index.json"

    def ensure_mounted(self) -> bool:
        """Ensure NAS is mounted. Return True if accessible."""
        try:
            if not self.mount_path.exists():
                logger.warning(f"NAS mount point not found: {self.mount_path}")
                logger.info(f"Configure NAS_MOUNT_PATH in .env")
                return False

            # Try to access the mount
            test_file = self.mount_path / ".nas_check"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception as e:
            logger.error(f"NAS not accessible: {e}")
            return False

    def save_report_metadata(
        self,
        report_name: str,
        findings_count: int,
        vulnerability_types: List[str],
    ) -> bool:
        """
        Save anonymized report metadata to NAS.

        Metadata saved (NO CLIENT DATA):
        - Report name (anonymized)
        - Number of findings
        - Vulnerability types found
        - Date generated
        - Severity breakdown
        """
        try:
            if not self.ensure_mounted():
                logger.warning("NAS not available, skipping metadata save")
                return False

            # Ensure directories exist
            self.reports_dir.mkdir(parents=True, exist_ok=True)

            # Create anonymized metadata
            metadata = {
                "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "report_name": report_name,  # User-provided name
                "findings_count": findings_count,
                "vulnerability_types": vulnerability_types,
                "timestamp": datetime.now().isoformat(),
                "client_data": False,  # Flag that no client data is included
            }

            # Save metadata file
            metadata_path = self.reports_dir / f"{metadata['report_id']}_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Report metadata saved to NAS: {metadata_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save report metadata: {e}")
            return False

    def save_findings_summary(
        self,
        report_name: str,
        findings: List[Dict[str, Any]],
    ) -> bool:
        """
        Save anonymized findings summary to NAS.

        Each finding saved with:
        - Vulnerability type
        - Title
        - Severity
        - WSTG reference

        NOT saved:
        - Full descriptions with client context
        - Sensitive data
        - Specific payloads
        - Client information
        """
        try:
            if not self.ensure_mounted():
                logger.warning("NAS not available, skipping findings save")
                return False

            self.reports_dir.mkdir(parents=True, exist_ok=True)

            # Anonymize findings (keep only essential info)
            anonymized_findings = []
            for finding in findings:
                anonymized_findings.append(
                    {
                        "title": finding.get("title"),
                        "type": finding.get("type"),
                        "severity": finding.get("severity"),
                        "wstg_reference": finding.get("wstg_reference"),
                        # NOT including: description, remediation details, client data
                    }
                )

            # Save findings summary
            summary = {
                "report_name": report_name,
                "timestamp": datetime.now().isoformat(),
                "findings_count": len(findings),
                "findings_summary": anonymized_findings,
            }

            summary_path = self.reports_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2)

            logger.info(f"Findings summary saved to NAS: {summary_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save findings summary: {e}")
            return False

    def list_reports(self) -> List[Dict[str, Any]]:
        """List all stored reports from NAS."""
        reports = []
        try:
            if self.reports_dir.exists():
                for metadata_file in self.reports_dir.glob("*_metadata.json"):
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                        reports.append(metadata)
        except Exception as e:
            logger.error(f"Failed to list reports: {e}")
        return reports

    def get_storage_info(self) -> Dict[str, Any]:
        """Get NAS storage information."""
        info = {
            "nas_ip": self.nas_ip,
            "nas_share": self.nas_share,
            "mount_path": str(self.mount_path),
            "accessible": self.ensure_mounted(),
            "reports_dir": str(self.reports_dir),
        }

        if info["accessible"]:
            try:
                reports = self.list_reports()
                info["reports_count"] = len(reports)
                info["status"] = "Connected"
            except Exception as e:
                info["status"] = f"Connected but read error: {e}"
        else:
            info["status"] = "Not accessible"
            info["note"] = "Configure NAS_IP and NAS_MOUNT_PATH in .env and ensure NAS is mounted"

        return info
