"""Paperwork Agent - Dynamic Workflow Generator and Synthesizer.

Automatically generates structured, authoritative workflow schemas on-the-fly
for any administrative paperwork goal (passports, driving licenses, visas,
KYC, university admissions, etc.) using LLM orchestration or intelligent fallback synthesis.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = Path(os.environ.get("WORKFLOWS_DIR", _BACKEND_ROOT / "data" / "workflows"))


def _slugify(text: str) -> str:
    """Convert human-readable title or goal to a clean workflow ID slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:40].strip("_") or "custom_workflow"


def _generate_with_llm(user_goal: str) -> dict[str, Any] | None:
    """Generate a structured workflow definition using the configured LLM provider."""
    provider = os.environ.get("MODEL_PROVIDER", "openai").lower()
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

    prompt = f"""You are an administrative paperwork and legal compliance expert.
Generate an authoritative, structured checklist schema for the following paperwork goal:
"{user_goal}"

Output ONLY a single valid JSON object with this exact structure:
{{
    "workflow_id": "short_unique_snake_case_id",
    "workflow_name": "Official Title of Application/Process",
    "description": "Clear explanation of the administrative procedure and required documentation.",
    "requirements": [
        {{
            "id": "req_unique_id",
            "name": "Name of Requirement (e.g. Proof of Address)",
            "description": "What specific document is needed and from where.",
            "required": true,
            "accepted_evidence_types": ["utility_bill", "bank_statement", "aadhaar_card"],
            "relevant_fields": ["full_name", "address", "date_of_birth"],
            "validation_hints": "Specific rules (e.g. dated within 3 months, names must match exactly)."
        }}
    ]
}}
Do not wrap in markdown quotes or add any conversational text. Return only raw JSON.
"""

    try:
        if provider == "groq" and groq_key and not groq_key.startswith("your-"):
            from openai import OpenAI
            client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            model_id = os.environ.get("MODEL_ID", "llama-3.3-70b-versatile")
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content or ""
            return json.loads(raw_content)

        elif provider == "ollama":
            from openai import OpenAI
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            client = OpenAI(api_key="ollama", base_url=base_url)
            model_id = os.environ.get("MODEL_ID", "llama3.2")
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            raw_content = response.choices[0].message.content or ""
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            return json.loads(json_match.group(0)) if json_match else json.loads(raw_content)

        elif provider == "openrouter" and openrouter_key and not openrouter_key.startswith("your-"):
            from openai import OpenAI
            client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
            model_id = os.environ.get("MODEL_ID", "meta-llama/llama-3.2-3b-instruct:free")
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            raw_content = response.choices[0].message.content or ""
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            return json.loads(json_match.group(0)) if json_match else json.loads(raw_content)

        elif provider == "openai" and openai_key and not openai_key.startswith("your-"):
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            model_id = os.environ.get("MODEL_ID", "gpt-4o")
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content or ""
            return json.loads(raw_content)

        elif provider == "anthropic" and anthropic_key and not anthropic_key.startswith("your-"):
            from anthropic import Anthropic
            client = Anthropic(api_key=anthropic_key)
            model_id = os.environ.get("MODEL_ID", "claude-sonnet-4-6")
            response = client.messages.create(
                model=model_id,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            raw_content = "".join(text_blocks).strip()
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

    except Exception as e:
        logger.warning(f"LLM workflow generation failed: {e}. Falling back to rule synthesizer.")

    return None


def _generate_with_heuristics(user_goal: str) -> dict[str, Any]:
    """Intelligently synthesize a realistic administrative workflow based on goal keywords."""
    goal_lower = user_goal.lower()
    
    # Base extracted topic
    clean_title = user_goal.strip()
    clean_title = re.sub(r"^(i want to|how do i|apply for|help me with|verify my documents for)\s+", "", clean_title, flags=re.IGNORECASE)
    clean_title = clean_title.strip(" .!?").title()
    if not clean_title:
        clean_title = "Administrative Application"

    wf_id = _slugify(clean_title)
    
    requirements = []

    # 1. Identity Proof
    requirements.append({
        "id": "req_identity",
        "name": "Proof of Identity",
        "description": "Government-issued photo identification (Aadhaar Card, Passport, Driver's License, Voter ID, or National ID Card).",
        "required": True,
        "accepted_evidence_types": ["aadhaar_card", "passport", "drivers_license", "voter_id", "national_id"],
        "relevant_fields": ["full_name", "id_number", "date_of_birth"],
        "validation_hints": "Must be a valid, unexpired government-issued document displaying full legal name."
    })

    # 2. Address Proof
    requirements.append({
        "id": "req_address",
        "name": "Proof of Current Address",
        "description": "Recent utility bill, bank account statement, rental agreement, or official residency proof.",
        "required": True,
        "accepted_evidence_types": ["utility_bill", "bank_statement", "aadhaar_card", "rent_agreement", "official_letter"],
        "relevant_fields": ["full_name", "address"],
        "validation_hints": "Must match the applicant's current residential address and be recently dated if a recurring utility bill."
    })

    # 3. DOB / Age Proof
    requirements.append({
        "id": "req_dob",
        "name": "Proof of Date of Birth",
        "description": "Birth Certificate, Aadhaar Card, Matriculation Certificate, or Passport.",
        "required": True,
        "accepted_evidence_types": ["birth_certificate", "aadhaar_card", "matriculation_certificate", "passport"],
        "relevant_fields": ["full_name", "date_of_birth"],
        "validation_hints": "Date of birth must be consistent across all submitted documents without discrepancy."
    })

    # 4. Domain-specific requirements
    if any(k in goal_lower for k in ["passport", "visa", "immigration", "travel"]):
        requirements.append({
            "id": "req_photograph",
            "name": "Recent Passport-Sized Photograph",
            "description": "Recent colored photograph meeting official biometric specifications (white background, taken within 6 months).",
            "required": True,
            "accepted_evidence_types": ["photograph", "passport_photo"],
            "relevant_fields": ["photograph"],
            "validation_hints": "Must be recent color photo with clear frontal view."
        })
        if "visa" in goal_lower:
            requirements.append({
                "id": "req_financial_means",
                "name": "Proof of Financial Means / Bank Statement",
                "description": "Bank account statements for the last 3 to 6 months showing sufficient funds.",
                "required": True,
                "accepted_evidence_types": ["bank_statement", "tax_return", "payslip"],
                "relevant_fields": ["full_name", "bank_name", "balance", "income"],
                "validation_hints": "Must show steady account activity and sufficient balance."
            })

    elif any(k in goal_lower for k in ["license", "licence", "driving", "rto", "vehicle"]):
        requirements.append({
            "id": "req_medical_declaration",
            "name": "Medical Fitness Certificate / Declaration",
            "description": "Medical fitness form or self-declaration for driving suitability.",
            "required": False,
            "accepted_evidence_types": ["medical_certificate", "fitness_declaration"],
            "relevant_fields": ["full_name", "doctor_signature", "fitness_status"],
            "validation_hints": "Required if applying for commercial category or if above designated age threshold."
        })

    elif any(k in goal_lower for k in ["education", "university", "college", "admission", "job", "employment"]):
        requirements.append({
            "id": "req_academic_records",
            "name": "Educational Qualifications / Certificates",
            "description": "Graduation degree certificate, transcript, or 10th/12th marksheets.",
            "required": True,
            "accepted_evidence_types": ["degree_certificate", "transcript", "diploma", "school_certificate"],
            "relevant_fields": ["full_name", "qualification", "institution", "grade"],
            "validation_hints": "Must include official institutional seal/signature and confirm qualification."
        })


    return {
        "workflow_id": wf_id,
        "workflow_name": f"{clean_title} Checklist",
        "description": f"Automated compliance checklist and verification schema for {clean_title}.",
        "requirements": requirements,
    }


def save_workflow_schema(workflow_data: dict[str, Any]) -> Path:
    """Save a validated workflow dictionary to data/workflows/ as a JSON file."""
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    wf_id = workflow_data.get("workflow_id", "custom_workflow")
    target_file = WORKFLOWS_DIR / f"{wf_id}.json"
    target_file.write_text(json.dumps(workflow_data, indent=4), encoding="utf-8")
    logger.info(f"Saved generated workflow '{wf_id}' to {target_file}")
    return target_file


def generate_and_register_workflow(user_goal: str) -> dict[str, Any]:
    """Generate a workflow for a user goal, persist it, and return the definition.

    1. Tries LLM-based structured generation if model credentials are active.
    2. Falls back to intelligent domain heuristic synthesis.
    3. Saves the workflow JSON to data/workflows/ for immediate reuse by all tools.
    """
    wf = _generate_with_llm(user_goal)
    if not wf or not isinstance(wf, dict) or "requirements" not in wf:
        wf = _generate_with_heuristics(user_goal)

    # Sanitize requirements structure
    if "workflow_id" not in wf or not wf["workflow_id"]:
        wf["workflow_id"] = _slugify(user_goal)
    if "workflow_name" not in wf or not wf["workflow_name"]:
        wf["workflow_name"] = user_goal.title()
    if "description" not in wf:
        wf["description"] = f"Workflow requirements for {user_goal}"
    if "requirements" not in wf or not isinstance(wf["requirements"], list):
        wf["requirements"] = []

    # Ensure each requirement has essential keys
    for i, req in enumerate(wf["requirements"]):
        if not isinstance(req, dict):
            continue
        req.setdefault("id", f"req_{i+1}")
        req.setdefault("name", f"Requirement {i+1}")
        req.setdefault("description", "")
        req.setdefault("required", True)
        req.setdefault("accepted_evidence_types", ["national_id", "official_document"])
        req.setdefault("relevant_fields", ["full_name", "date_of_birth", "address"])
        req.setdefault("validation_hints", "Document must be valid and legible.")

    save_workflow_schema(wf)
    return wf
