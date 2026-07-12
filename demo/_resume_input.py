"""
Shared "resume as pasted text vs uploaded file" resolution logic, used by
both demo/webapp.py (plain test form) and demo/site.py (public landing
page). Mirrors the same rule the deployed MCP tool would apply.
"""
import base64

from core.file_extract import SUPPORTED_FILE_TYPES, FileExtractionError, extract_text_from_file


def resolve_resume_text(resume_text: str, uploaded_file):
    """uploaded_file is (filename, bytes) or None/empty.

    Returns (resolved_resume_text, rejection_dict). Exactly one is None.
    """
    if not uploaded_file or not uploaded_file[1]:
        return resume_text, None

    filename, file_bytes = uploaded_file
    file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if resume_text.strip():
        return None, {
            "rejected": True,
            "reason": "Provide the resume as either pasted text or an uploaded file, not both.",
        }
    if file_type not in SUPPORTED_FILE_TYPES:
        return None, {
            "rejected": True,
            "reason": f"Unsupported file type '{file_type}'. Supported: "
            f"{', '.join(sorted(SUPPORTED_FILE_TYPES))}.",
        }
    try:
        extracted = extract_text_from_file(base64.b64encode(file_bytes).decode("ascii"), file_type)
        return extracted, None
    except FileExtractionError as e:
        return None, {"rejected": True, "reason": str(e)}
