import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Server Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8000))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Ollama Configuration (local on same machine)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 90))

# NAS Configuration - PLACEHOLDER for IP address
NAS_IP = os.getenv("NAS_IP", "192.168.50.50")  # Change this to your NAS IP
NAS_USERNAME = os.getenv("NAS_USERNAME", "admin")
NAS_PASSWORD = os.getenv("NAS_PASSWORD", "")
NAS_SHARE = os.getenv("NAS_SHARE", "findings")
NAS_MOUNT_PATH = os.getenv("NAS_MOUNT_PATH", "/mnt/pentest-reports")

# Local file storage (for templates and working files)
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates" / "uploads"
REPORTS_DIR = BASE_DIR / "reports" / "generated"
STATIC_DIR = BASE_DIR / "static"

# Ensure directories exist
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# App Info
APP_NAME = "Report Template Generator"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Offline pentest report generator with LLM-assisted content"
