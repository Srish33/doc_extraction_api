import re
from typing import Any, Dict, List, Optional

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b"
)

DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:Week|Month|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
    r"|(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December))"
    r"|(?:\d{1,2}[.]\d{1,2}[.]\d{2,4})",
    re.IGNORECASE
)
MONEY_PATTERN = re.compile(r"(?:Rs\.?|INR|USD|EUR|GBP|\$|€|£)\s?\d[\d,]*(?:\.\d{1,2})?", re.IGNORECASE)
PERCENT_PATTERN = re.compile(r"\b\d{1,3}(?:\.\d{1,2})?\s*%\b")

DOCUMENT_CLASSIFIER_MAP = {
    "Resume": ["EXPERIENCE", "EDUCATION", "SKILLS", "PROJECTS", "AWARDS", "CERTIFICATIONS", "PUBLICATIONS", "SUMMARY"],
    "Invoice": ["INVOICE #", "BILL TO", "SHIP TO", "INVOICE DATE", "DUE DATE", "TOTAL DUE", "SUBTOTAL", "BALANCE DUE",
                "DESCRIPTION", "QUANTITY", "UNIT PRICE"],
    "Receipt": ["CASHIER", "ITEMS", "SUBTOTAL", "TAX", "TOTAL", "CHANGE", "STORE #", "AUTH CODE", "VISA", "MASTERCARD"],
    "Calendar": ["SCHEDULE", "AGENDA", "MEETING", "TIMETABLE", "APPOINTMENT", "CALENDAR", "REMINDER", "EVENTS"],
    "Certificate": ["MARKSHEET", "TRANSCRIPT", "GRADE", "ROLL NO", "REGISTRATION NO", "PASSED",
                    "PROVISIONAL CERTIFICATE", "CONTROLLER OF EXAMINATIONS"]
}



def universal_de_space_text(text: str) -> str:
    """Scans strings to fix exploded capital lettering layouts (e.g.

    E X P E R I E N C E) without corrupting digit spaces.
    """

    def collapse_match(match):
        return match.group(0).replace(" ", "")

    return re.sub(r'\b[A-Z]\s+[A-Z]\s+[A-Z]\s+[A-Z](?:\s+[A-Z])*\b', collapse_match, text)


def universal_split_lines(text: str) -> List[str]:
    """Slices structural plain-text blocks into independent list array sentences

    using weighted classification anchor mapping points.
    """
    all_anchors = []
    for keywords in DOCUMENT_CLASSIFIER_MAP.values():
        all_anchors.extend(keywords)

    repaired = text
    for anchor in sorted(set(all_anchors), key=len, reverse=True):
        repaired = re.sub(rf'(?i)\b({re.escape(anchor)})\b', r'\n\1\n', repaired)

    return [line.strip() for line in repaired.split('\n') if line.strip()]


def _normalize_line(line: str) -> str:
    """Cleans up trailing plain-text punctuation layouts without deleting vital

    trailing digits or numerical data strings.
    """
    line = re.sub(r'[°•°.,\s\-—–]+$', '', line)
    return re.sub(r'\s+', ' ', line).strip()


def _unique(items: List[Any]) -> List[Any]:
    """Helper macro to safely drop duplicates while keeping layout order intact."""
    seen = set()
    return [x for x in items if not (x in seen or seen.add(x))]


def _remove_null_values(data: Any) -> Any:
    """Recursively walks downstream response JSON nodes to prune empty fields."""
    if isinstance(data, dict):
        return {k: _remove_null_values(v) for k, v in data.items() if v not in [None, "", [], {}]}
    elif isinstance(data, list):
        return [_remove_null_values(x) for x in data if x not in [None, "", [], {}]]
    return data



def parse_generic_sections(lines: List[str]) -> List[Dict[str, Any]]:
    """Scans document lines, groups text cleanly under respective headings,

    isolates bullet points into arrays, and strips out multi-page text repetition loops.
    """
    sections = []
    current_heading = "GENERAL OVERVIEW"
    current_text_buffer = []

    # ✅ FIXED: Global (?i) flag positioned at the absolute start of the expression sequence
    pointer_pattern = re.compile(
        r'(?i)^\d+[\s.)-]|^\b[A-Za-z][.)]\s|^•|^\*|^-|'
        r'^(phone|tel|email|date|invoice\s?#|p\.o\.\s?number|total\s?due|terms|ship\s?to|to:)'
    )

    for line in lines:
        normalized_line = _normalize_line(line)
        if not normalized_line:
            continue

        upper_line = normalized_line.upper()
        is_dynamic_header = False

        for keywords in DOCUMENT_CLASSIFIER_MAP.values():
            if any(kw.upper() == upper_line for kw in keywords) and len(upper_line) < 40:
                is_dynamic_header = True
                break

        if not is_dynamic_header and line.isupper() and len(line.split()) <= 4 and len(line) < 30 and line.isalpha():
            is_dynamic_header = True

        if is_dynamic_header:
            if current_text_buffer:
                unique_buffer = []
                for item in current_text_buffer:
                    if item not in unique_buffer:
                        unique_buffer.append(item)

                sections.append({
                    "heading": current_heading,
                    "description": unique_buffer if len(unique_buffer) > 1 else (
                        unique_buffer[0] if unique_buffer else "No descriptive records found.")
                })
            current_heading = upper_line
            current_text_buffer = []
        else:
            if pointer_pattern.match(normalized_line):
                current_text_buffer.append(normalized_line)
            else:
                if current_text_buffer and not pointer_pattern.match(str(current_text_buffer[-1])):
                    current_text_buffer[-1] = f"{current_text_buffer[-1]} {normalized_line}"
                else:
                    current_text_buffer.append(normalized_line)

    if current_text_buffer or current_heading != "GENERAL OVERVIEW":
        unique_buffer = []
        for item in current_text_buffer:
            if item not in unique_buffer:
                unique_buffer.append(item)

        sections.append({
            "heading": current_heading,
            "description": unique_buffer if len(unique_buffer) > 1 else (
                unique_buffer[0] if unique_buffer else "No descriptive records found.")
        })

    return sections


def format_response(filename: str, text: str, search_keyword: Optional[str] = None) -> Dict[str, Any]:
    """Universal gatekeeper parsing extracted strings into organized JSON graphs,

    featuring inline global entity registries, a custom keyword proximity searcher,
    and fallback formatters protecting international phone signatures.
    """
    repaired_text = universal_de_space_text(text)
    flat_upper = repaired_text.upper()
    processed_lines = universal_split_lines(text)

    scores = {dtype: 0 for dtype in DOCUMENT_CLASSIFIER_MAP.keys()}
    for dtype, keywords in DOCUMENT_CLASSIFIER_MAP.items():
        scores[dtype] = sum(2 if kw.upper() in flat_upper else 0 for kw in keywords)

    lower_fn = filename.lower()
    if "resume" in lower_fn or "cv" in lower_fn:
        scores["Resume"] += 10
    elif "calendar" in lower_fn or "schedule" in lower_fn:
        scores["Calendar"] += 10
    elif "invoice" in lower_fn:
        scores["Invoice"] += 10
    elif "receipt" in lower_fn:
        scores["Receipt"] += 10
    elif any(x in lower_fn for x in ["marksheet", "certificate", "transcript"]):
        scores["Certificate"] += 10

    inferred_doc_type = max(scores, key=scores.get) if max(scores.values(), default=0) > 0 else "General Document"

    structured_sections = parse_generic_sections(processed_lines)

    emails = _unique(EMAIL_PATTERN.findall(repaired_text))
    percentages = _unique([m.group(0).strip() for m in PERCENT_PATTERN.finditer(repaired_text)])

    raw_phones = _unique([m.group(0).strip() for m in PHONE_PATTERN.finditer(repaired_text)])

    phones = []
    for p in raw_phones:
        if p.startswith("+"):
            phones.append(p)
        else:
            if re.match(r'^\d{1,3}(?:\s|[\s.-]?\()', p) or re.match(r'^\d{1,3}\s', p):
                phones.append(f"+{p}")
            else:
                if len(p.replace(" ", "").replace("-", "")) >= 11:
                    phones.append(f"+{p}")
                else:
                    phones.append(p)

    search_matches = []
    if search_keyword and search_keyword.strip():
        clean_keyword = search_keyword.strip()
        keyword_regex = re.compile(rf'(?i)\b{re.escape(clean_keyword)}\b')

        for line in processed_lines:
            if keyword_regex.search(line):
                search_matches.append(_normalize_line(line))

    return _remove_null_values({
        "filename": filename,
        "document_type": inferred_doc_type,
        "extracted_data": {
            "emails": emails if emails else "None Found",
            "phone_numbers": phones if phones else "None Found",
            "percentages_detected": percentages if percentages else "None Found",
            "keyword_search": {
                "query_term": search_keyword if search_keyword else "No query provided",
                "match_count": len(search_matches),
                "matches_found": search_matches if search_matches else "No keyword matches located inside document."
            },
            "sections": structured_sections
        }
    })