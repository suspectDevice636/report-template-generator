import httpx
import json
import logging
from typing import Dict, Any
from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)


async def check_ollama_health() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return False


async def generate_finding_content(
    finding_description: str,
) -> Dict[str, Any]:
    """
    Generate finding report content from a brief description.

    Input: "SQLI in /api/users, POST method, authenticated, can extract user data"
    Output: {
        "title": "SQL Injection in User API Endpoint",
        "description_impact": "...",
        "remediation": "...",
        "wstg_reference": "..."
    }
    """

    prompt = f"""You are a professional security report writer for penetration testing.

A tester has identified the following vulnerability during testing:
"{finding_description}"

Generate a professional finding report section with these exact fields:

1. FINDING_TITLE: A clear, professional title for this vulnerability
2. DESCRIPTION_IMPACT: 2-3 paragraphs explaining what the vulnerability is, how it was found, and its business/technical impact
3. REMEDIATION: Step-by-step remediation guidance with code examples if applicable
4. WSTG_REFERENCE: Provide the OWASP WSTG reference URL(s) most relevant to this vulnerability

Format your response as JSON with these exact keys:
{{
    "title": "...",
    "description_impact": "...",
    "remediation": "...",
    "wstg_reference": "..."
}}

Important:
- Be specific and technical but also understandable to non-technical stakeholders
- Include actual code examples in remediation where applicable
- WSTG references should be actual URLs from https://owasp.org/www-project-web-security-testing-guide/"""

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
            )

            if response.status_code != 200:
                logger.error(f"Ollama error: {response.text}")
                return {
                    "error": "Ollama generation failed",
                    "status_code": response.status_code,
                }

            result = response.json()
            response_text = result.get("response", "")

            # Try to parse JSON response
            try:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    content = json.loads(json_str)
                    return {
                        "status": "success",
                        "content": content,
                    }
                else:
                    logger.warning("No JSON found in response, returning raw text")
                    return {
                        "status": "partial",
                        "content": {
                            "raw_response": response_text,
                        },
                    }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return {
                    "status": "error",
                    "error": "Failed to parse LLM response as JSON",
                    "raw_response": response_text,
                }

    except httpx.TimeoutException:
        logger.error("Ollama request timed out")
        return {"error": "Analysis timeout", "status": "timeout"}
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return {"error": str(e), "status": "error"}


async def generate_wstg_reference(vulnerability_type: str) -> str:
    """
    Generate WSTG reference URL(s) for a vulnerability type.
    """
    wstg_mappings = {
        "sql_injection": "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection",
        "xss": "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/01-Testing_for_Reflected_Cross_Site_Scripting",
        "authentication": "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/",
        "authorization": "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/",
        "csrf": "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/05-Testing_for_Cross_Site_Request_Forgery",
        "business_logic": "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/",
        "api": "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/12-API_Testing/",
    }

    # Try to find a match
    vuln_lower = vulnerability_type.lower()
    for key, url in wstg_mappings.items():
        if key in vuln_lower:
            return url

    # Default to main testing guide
    return "https://owasp.org/www-project-web-security-testing-guide/"
