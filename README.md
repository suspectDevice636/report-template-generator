# Report Template Generator

**Offline pentest report generation with LLM-assisted content creation**

Transform your findings into professional, client-ready pentest reports without sending sensitive data to the cloud.

## Features

✅ **Upload custom DOCX templates** for different clients and test types  
✅ **Chat findings to the app** - minimal input, LLM fills in details  
✅ **Ollama-powered content generation** - offline, on-machine LLM  
✅ **Professional report output** - ready-to-send DOCX files  
✅ **Anonymized NAS storage** - save reports without client data  
✅ **WSTG references** - automatically included remediation guidance  

## Workflow

```
┌─────────────────────────────────────┐
│ During Pentest on Your Laptop       │
│                                     │
│ 1. Find vulnerability               │
│ 2. Open Report Generator            │
│ 3. Type: "SQLI in /api/users, POST" │
│ 4. LLM generates professional text  │
│ 5. Review and add to report         │
│ 6. Export DOCX when done            │
└─────────────────────────────────────┘
         │
         ▼ (via WiFi)
┌──────────────────────────────────────┐
│ Mac Mini #2 (192.168.50.11:8000)     │
├──────────────────────────────────────┤
│ ├─ Web UI                            │
│ ├─ FastAPI Server                    │
│ ├─ Ollama (11434)                    │
│ └─ DOCX Generation                   │
└────────┬─────────────────────────────┘
         │ (via EdgeRouter)
         ▼
┌──────────────────────────────────────┐
│ Synology NAS (192.168.50.50)         │
│ Anonymized report storage            │
└──────────────────────────────────────┘
```

## Installation

### Prerequisites

- **Mac Mini #2** with 32GB RAM
- **Python 3.10+**
- **Ollama** running locally (port 11434)
- **NAS** accessible via network mount

### Setup

```bash
# Clone and setup
cd ~/projects
git clone <repo> report-template-generator
cd report-template-generator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env
# Set: NAS_IP, NAS_USERNAME, NAS_PASSWORD, NAS_MOUNT_PATH

# Create directories
mkdir -p templates/uploads reports/generated static

# Run
python main.py
```

Server available at: **`http://192.168.50.11:8000`**

## Configuration

### .env File

```bash
# Server
SERVER_PORT=8000
DEBUG=false

# Ollama (local)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral
OLLAMA_TIMEOUT=90

# NAS Storage - UPDATE THESE
NAS_IP=192.168.50.50              # Your NAS IP
NAS_USERNAME=admin
NAS_PASSWORD=your_password
NAS_MOUNT_PATH=/mnt/pentest-reports  # Ensure this exists and is mounted
```

### NAS Mount Setup

```bash
# Create mount directory
mkdir -p /mnt/pentest-reports

# Mount NAS (adjust credentials)
sudo mount -t cifs //192.168.50.50/findings /mnt/pentest-reports \
  -o username=admin,password=YOUR_PASSWORD,uid=501,gid=20

# Verify
ls -la /mnt/pentest-reports

# Make permanent (add to /etc/fstab or create auto-mount script)
```

## Usage

### 1. Upload DOCX Template

```
Web UI → Templates tab
Select file: MyTemplate.docx
Upload
```

**Template placeholders:**
```
[FINDING_TITLE]
[DESCRIPTION_IMPACT]
[REMEDIATION]
[WSTG_REFERENCE]
```

### 2. Generate Report

```
Web UI → Generate Report tab

1. Enter report name: "Acme Corp - Web App Pentest"
2. Select template
3. Type finding: "SQL injection in /api/search POST, authenticated, can extract user data"
4. Click "Add Finding"
5. Ollama generates: title, description, remediation, WSTG reference
6. Add more findings (repeat step 3-5)
7. Click "Generate Report"
8. Download DOCX
```

### 3. Access Stored Reports

```
Web UI → Storage tab
View NAS-stored reports (anonymized metadata)
```

## API Endpoints

### Upload Template
```bash
POST /upload-template
Content-Type: multipart/form-data

curl -F "file=@template.docx" http://192.168.50.11:8000/upload-template
```

### List Templates
```bash
GET /templates

curl http://192.168.50.11:8000/templates
```

### Generate Finding Content
```bash
POST /generate-finding
{
  "finding_description": "SQLI in /api/users",
  "vulnerability_type": "sql_injection",
  "template_name": "MyTemplate"
}
```

### Generate Report
```bash
POST /generate-report
{
  "template_name": "MyTemplate",
  "findings": [
    {
      "finding_description": "SQLI in /api/users",
      "vulnerability_type": "sql_injection",
      "template_name": "MyTemplate"
    }
  ],
  "report_name": "Acme Corp - Web App Test"
}
```

### Download Report
```bash
GET /download-report/{filename}
```

### Storage Info
```bash
GET /storage-info
GET /reports
```

## What Gets Stored on NAS

**Stored (anonymized):**
- Report name
- Vulnerability types (SQL injection, XSS, etc.)
- Finding count
- Timestamp
- WSTG references
- Generic remediation guidance

**NOT stored:**
- Client names
- Target domains/IPs
- Actual HTTP responses
- Sensitive data
- Client-specific information

### NAS Directory Structure

```
/mnt/pentest-reports/
├── pentest_reports/
│   ├── report_20260411_120000_metadata.json
│   ├── summary_20260411_120000.json
│   └── ...
└── findings_index.json
```

## Troubleshooting

**Ollama not responding:**
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Start if needed
ollama serve
```

**NAS not accessible:**
```bash
# Check mount
mount | grep pentest-reports

# Verify credentials
ping 192.168.50.50

# Re-mount
sudo umount /mnt/pentest-reports
sudo mount -t cifs //192.168.50.50/findings /mnt/pentest-reports \
  -o username=admin,password=PASSWORD
```

**Timeout generating findings:**
```bash
# Increase timeout in .env
OLLAMA_TIMEOUT=120

# Or use faster model
OLLAMA_MODEL=neural-chat
```

## Development

### Project Structure

```
report-template-generator/
├── main.py                    # FastAPI server
├── config.py                  # Configuration
├── ollama_service.py          # LLM integration
├── docx_service.py            # DOCX handling
├── storage_service.py         # NAS storage
├── static/
│   └── index.html            # Web UI
├── templates/
│   └── uploads/              # User-uploaded templates
├── reports/
│   └── generated/            # Generated DOCX files
├── requirements.txt
├── .env.example
└── README.md
```

### Running with Debug

```bash
DEBUG=true python main.py
```

Open: `http://192.168.50.11:8000/docs` for interactive API docs

## Workflow Tips

**For Multiple Clients:**
- Create separate DOCX templates for each client
- Include their branding, format preferences
- App handles content generation consistently

**For Different Test Types:**
- Web app template (focus on HTTP, API, logic flaws)
- Network template (focus on network services, access control)
- Mobile template (focus on app-specific issues)

**During Report Generation:**
- You can add findings iteratively
- Generate report at any time
- LLM content is customizable if needed

## Next Steps

1. Create your DOCX templates with placeholders
2. Mount your NAS
3. Configure .env with your lab details
4. Start the server
5. Test with a simple finding
6. Customize templates as needed

## License

Private project.

---

**Version:** 1.0.0  
**Status:** Ready for use  
**Last Updated:** 2026-04-11

---

## Notes for Your Lab

- **Network:** Access via WiFi from pentest VM to Mac Mini #2
- **Ollama:** Runs locally on Mac Mini #2, no remote calls needed
- **NAS:** Reachable from Mac Mini #2 via EdgeRouter
- **Client data:** Never leaves your lab network or offline VM
- **Reports:** Stored anonymized on NAS for record-keeping

Ready to generate professional pentest reports offline! 🔒
