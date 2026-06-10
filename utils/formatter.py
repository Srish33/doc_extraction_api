import re

# Module-level patterns used across the formatter to detect common entities.
MONEY_PATTERN = re.compile(
    r"(?:Rs\.?|INR|USD|EUR|GBP|\$|€|£)\s?\d[\d,]*(?:\.\d{1,2})?",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

# OPTIMIZED: Captures standard grouped formats, spaced layouts, and prefix numbers (+91) smoothly
PHONE_PATTERN = re.compile(
    r"(?:\+91[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b|"
    r"(?:\+91[\s.-]?)?[6-9]\d{4}[\s.-]?\d{5}\b|"
    r"(?:\+91[\s.-]?)?[6-9]\d{9}\b"
)

DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
    r"\s+\d{1,2},?\s+\d{4}|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
    r"\s+\d{4})\b",
    re.IGNORECASE,
)

PERCENT_PATTERN = re.compile(r"\b\d{1,3}(?:\.\d{1,2})?\s*%\b")

DOCUMENT_KEYWORDS = {
    "Receipt": ["receipt", "amount paid", "payment method", "date paid"],
    "Invoice": ["invoice number", "tax invoice", "bill to", "due date", "balance due", "total amount"],
    "Resume": ["resume", "curriculum vitae", "experience", "education", "skills", "extracurriculars"],
    "Bank Statement": ["statement", "account number", "opening balance", "closing balance"],
    "Report": ["report", "abstract", "introduction", "conclusion", "findings"],
    "Agreement": ["agreement", "contract", "terms and conditions", "party", "signature"],
    "Certificate": ["certificate of", "certifies that", "awarded", "issued", "examination", "marksheet", "grade points",
                    "sgpa", "cgpa", "identity card", "roll no"],
    "Letter": ["dear", "subject", "sincerely", "regards"],
    "MSDS": ["material safety data sheet", "msds", "hazards identification", "first-aid measures", "chemical product"],
    "Assay Certificate": ["assay certificate", "chemical analysis", "spectro", "grade", "al2o3", "fe2o3", "sio2",
                          "moisture %"],
    "Purchase Order": ["purchase order", "po number", "delivery terms", "vendor code", "indentor"],
}

SECTION_HEADERS = {
    "abstract", "account details", "agreement", "amount", "bill from", "bill to",
    "certificate", "conclusion", "contact", "customer", "date", "description",
    "education", "experience", "findings", "invoice", "item", "payment",
    "receipt", "report", "seller", "ship to", "skills", "summary", "sub total",
    "subtotal", "tax", "terms", "total", "projects", "certificates", "extracurriculars",
    "composition", "hazards identification", "first-aid measures", "fire fighting",
    "handling and storage", "physical and chemical properties", "stability and reactivity",
    "chemical analysis", "test results", "specifications", "delivery terms"
}

TABLE_HEADER_LABELS = {
    "amount", "balance", "credit", "date", "debit", "description", "discount",
    "item", "particulars", "price", "qty", "quantity", "rate", "total",
    "unit cost", "unit price"
}


def _lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def _unique(values):
    seen = set()
    result = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _remove_null_values(value):
    if value is None:
        return "Not found"
    if isinstance(value, dict):
        return {key: _remove_null_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_remove_null_values(item) for item in value]
    return value


def _find_label_index(lines, labels):
    lowered_labels = {label.lower() for label in labels}
    for index, line in enumerate(lines):
        normalized = line.rstrip(":").lower()
        if normalized in lowered_labels:
            return index
    return -1


def _value_after_label(lines, labels):
    label_index = _find_label_index(lines, labels)
    if label_index == -1:
        return None

    current_line = lines[label_index]
    if ":" in current_line:
        _, value = current_line.split(":", 1)
        value = value.strip()
        if value:
            return value

    if label_index + 1 < len(lines):
        return lines[label_index + 1]
    return None


def _money_after_label(lines, labels):
    label_index = _find_label_index(lines, labels)
    if label_index == -1:
        return None

    for line in lines[label_index + 1: label_index + 4]:
        match = MONEY_PATTERN.search(line)
        if match:
            return match.group(0)
    return None


def _section(lines, start_labels, end_labels):
    start_index = _find_label_index(lines, start_labels)
    if start_index == -1:
        return []

    lowered_end_labels = {label.lower() for label in end_labels}
    end_index = len(lines)
    for index in range(start_index + 1, len(lines)):
        if lines[index].rstrip(":").lower() in lowered_end_labels:
            end_index = index
            break

    return lines[start_index + 1: end_index]


def _contact_details(section_lines):
    if not section_lines:
        return {
            "name": None,
            "address": [],
            "phone": None,
            "email": None,
            "other_details": [],
        }

    email = None
    phone = None
    address = []
    other_details = []

    metadata_blacklist = {"date:", "ship mode:", "balance due:", "order id:", "invoice", "notes:", "thanks",
                          "po number:"}

    for line in section_lines[1:]:
        cleaned_line = line.replace('"', '').strip()
        lowered_line = cleaned_line.lower()

        if any(term in lowered_line for term in metadata_blacklist):
            continue

        email_match = EMAIL_PATTERN.search(cleaned_line)
        phone_match = PHONE_PATTERN.search(cleaned_line)

        if email_match and not email:
            email = email_match.group(0)
        elif phone_match and not phone:
            phone = phone_match.group(0)
        elif cleaned_line.replace(" ", "").isdigit():
            other_details.append(cleaned_line)
        elif not MONEY_PATTERN.search(cleaned_line):
            if cleaned_line.lower() not in {"ship to:", "bill to:", "vendor:"}:
                address.append(cleaned_line)
        else:
            other_details.append(cleaned_line)

    return {
        "name": section_lines[0].replace('"', '').strip(),
        "address": address,
        "phone": phone,
        "email": email,
        "other_details": other_details,
    }


def _detect_document_type(text):
    lowered_text = text.lower()

    # Priority check for Resumes to lock down type matching accuracy
    if any(kw in lowered_text for kw in ["github.com", "linkedin.com", "bloc", "riverpod", "coursework", "b.tech"]):
        return "Resume"
    if any(kw in lowered_text for kw in ["marksheet", "semester", "identity card", "roll no", "grade points"]):
        return "Certificate"

    scores = {}
    for document_type, keywords in DOCUMENT_KEYWORDS.items():
        scores[document_type] = sum(1 for keyword in keywords if keyword in lowered_text)

    best_type = max(scores, key=scores.get)
    if scores[best_type] == 0:
        return "General Document"
    return best_type


def _extract_title(lines):
    for line in lines[:8]:
        if len(line) <= 120 and not EMAIL_PATTERN.search(line) and not PHONE_PATTERN.search(line):
            return line
    return lines[0] if lines else None


def _extract_key_value_fields(lines):
    fields = {}
    for index, line in enumerate(lines):
        key = None
        value = None

        if len([column for column in re.split(r"\s{2,}|\t+|\s+\|\s+", line) if column.strip()]) >= 2:
            continue

        if ":" in line:
            key, value = line.split(":", 1)
        elif index + 1 < len(lines):
            normalized = line.rstrip(":").lower()
            next_line = lines[index + 1]
            is_label = re.search(r"(number|no|date|name|method|total|amount|id|code)$", normalized)
            is_table_header = normalized in {"amount", "price", "quantity", "qty", "unit cost", "unit price"}
            if is_label and not is_table_header:
                key = line
                value = next_line

        if not key or not value:
            continue

        key = re.sub(r"\s+", " ", key).strip(" :-")
        value = value.strip()
        if 1 <= len(key) <= 60 and value:
            fields[key] = value

    return fields


def _extract_identifiers(lines):
    identifiers = {}
    patterns = {
        "invoice_number": ["Invoice Number", "Invoice No", "Invoice #"],
        "receipt_number": ["Receipt Number", "Receipt No", "Receipt #"],
        "reference_number": ["Reference Number", "Reference No", "Ref No", "Ref #"],
        "account_number": ["Account Number", "Account No", "A/C No"],
        "order_number": ["Order Number", "Order No", "Order #", "Purchase Order", "PO Number", "PO No"],
        "customer_id": ["Customer ID", "Customer No", "Client ID", "Vendor Code"],
    }
    for name, labels in patterns.items():
        identifiers[name] = _value_after_label(lines, labels)
    return identifiers


def _extract_contact_blocks(lines):
    contacts = []
    labels = ["Bill To", "Billed To", "Ship To", "From", "To", "Customer", "Seller", "Vendor"]
    end_labels = list(SECTION_HEADERS)

    for label in labels:
        section_lines = _section(lines, [label], end_labels)
        if section_lines:
            contacts.append({"label": label, "details": _contact_details(section_lines)})

    return contacts


def _extract_sections(lines):
    sections = []
    current = None

    table_noise_words = {"secured", "subject", "full", "marks", "code", "sl", "no"}
    protected_resume_headers = {"summary", "education", "experience", "projects", "skills", "certificates",
                                "extracurriculars"}

    for index, line in enumerate(lines):
        normalized = line.rstrip(":").lower().strip()

        is_header = (
                normalized in SECTION_HEADERS
                or normalized in protected_resume_headers
                or (
                        line.isupper()
                        and 4 <= len(line) <= 40
                        and len(line.split()) <= 4
                        and not any(char.isdigit() for char in line)
                )
        )

        if is_header and normalized not in protected_resume_headers:
            if normalized in table_noise_words or any(w in table_noise_words for w in normalized.split()):
                lookahead_lines = lines[index + 1: index + 4] if index + 1 < len(lines) else []
                if any(re.search(r"\b\d{2,3}\b", l) for l in lookahead_lines):
                    is_header = False

            if index > 0 and re.search(r"\b\d{2,3}\b", lines[index - 1]):
                is_header = False

        if is_header:
            if current:
                sections.append(current)
            current = {"heading": line.rstrip(":").strip(), "content": []}
        elif current:
            current["content"].append(line)

    if current:
        sections.append(current)

    return [s for s in sections if s["content"]]


def _extract_table_like_rows(lines):
    rows = []
    for line in lines:
        columns = re.split(r"\s{2,}|\t+|\s+\|\s+", line)
        columns = [column.strip() for column in columns if column.strip()]
        if len(columns) >= 2:
            rows.append(columns)
    return rows


def _extract_phone_numbers(text):
    phones = []
    for match in PHONE_PATTERN.finditer(text):
        phone = match.group(0).strip()
        digit_count = len(re.findall(r"\d", phone))
        if digit_count >= 8:
            phones.append(phone)
    return _unique(phones)


def _build_table_description(headers, rows):
    if not headers or not rows:
        return "No data found in table."

    descriptions = []
    clean_headers = [h.strip().replace("_", " ").title() for h in headers]
    is_standard_financial_table = all(h in clean_headers for h in ["Description", "Unit Cost", "Quantity", "Amount"])

    for idx, row in enumerate(rows, start=1):
        working_row = list(row)

        if is_standard_financial_table and len(working_row) >= 4:
            uc_idx = clean_headers.index("Unit Cost")
            qty_idx = clean_headers.index("Quantity")

            unit_cost_val = working_row[uc_idx]
            quantity_val = working_row[qty_idx]

            has_currency_in_qty = bool(MONEY_PATTERN.search(quantity_val))

            if has_currency_in_qty:
                working_row[uc_idx], working_row[qty_idx] = working_row[qty_idx], working_row[uc_idx]

        row_parts = []
        for i, header in enumerate(clean_headers):
            val = working_row[i] if i < len(working_row) else "Not Specified"
            row_parts.append(f"{header}: '{val}'")

        descriptions.append(f"Row {idx} -> {', '.join(row_parts)}")

    return " | ".join(descriptions)


def _table_from_rows(rows):
    if len(rows) < 2:
        return None

    headers = rows[0]
    data_rows = rows[1:]

    return {
        "table_summary": _build_table_description(headers, data_rows)
    }


def _extract_vertical_tables(lines):
    tables = []
    index = 0

    while index < len(lines):
        headers = []
        start_index = index
        while index < len(lines):
            normalized = lines[index].rstrip(":").lower()
            if normalized not in TABLE_HEADER_LABELS:
                break
            headers.append(lines[index].rstrip(":"))
            index += 1

        if len(headers) < 2:
            index = start_index + 1
            continue

        values = []
        while index < len(lines):
            normalized = lines[index].rstrip(":").lower()
            if normalized in SECTION_HEADERS or normalized in TABLE_HEADER_LABELS:
                break
            values.append(lines[index])
            index += 1

        rows = []
        for value_index in range(0, len(values), len(headers)):
            row = values[value_index: value_index + len(headers)]
            if len(row) == len(headers):
                rows.append(row)

        if rows:
            tables.append(
                {
                    "table_summary": _build_table_description(headers, rows)
                }
            )

    return tables


def _extract_tables(lines):
    tables = []
    row_table = _table_from_rows(_extract_table_like_rows(lines))
    if row_table:
        tables.append(row_table)
    tables.extend(_extract_vertical_tables(lines))
    return tables


def _extract_general_details(text):
    lines = _lines(text)
    emails = _unique(EMAIL_PATTERN.findall(text))
    phones = _extract_phone_numbers(text)
    dates = _unique(match.group(0) for match in DATE_PATTERN.finditer(text))
    money_values = _unique(match.group(0) for match in MONEY_PATTERN.finditer(text))

    # Capture structural academic percentages safely
    percentages = _unique(match.group(0) for match in PERCENT_PATTERN.finditer(text))

    doc_type = _detect_document_type(text)

    has_tables = doc_type in {"Receipt", "Invoice", "Purchase Order"}
    table_rows = _extract_table_like_rows(lines) if has_tables else []
    extracted_tables = _extract_tables(lines) if has_tables else []

    return {
        "document_type": doc_type,
        "title": _extract_title(lines),
        "key_value_fields": _extract_key_value_fields(lines),
        "identifiers": _extract_identifiers(lines),
        "contacts": _extract_contact_blocks(lines),
        "emails": emails,
        "phone_numbers": phones,
        "dates": dates,
        "monetary_values": money_values,
        "percentages": percentages,  # Assigned safely to dataset maps
        "sections": _extract_sections(lines),
        "table_like_rows": table_rows,
        "tables": extracted_tables,
    }


def _company_section(lines):
    payment_index = _find_label_index(lines, ["Payment method", "Payment mode", "Vendor", "Vendor Code"])
    bill_to_index = _find_label_index(lines, ["Bill To", "Billed To", "Customer", "Ship To"])
    if payment_index == -1 or bill_to_index == -1 or payment_index >= bill_to_index:
        return []

    return lines[payment_index + 2: bill_to_index]


def _extract_items(lines):
    item_index = _find_label_index(lines, ["Item", "Description", "Particulars"])
    subtotal_index = _find_label_index(lines, ["Subtotal", "Sub Total", "Total"])
    if item_index == -1:
        return []

    end_index = subtotal_index if subtotal_index != -1 else len(lines)
    item_lines = lines[item_index + 1: end_index]

    header_words = {"unit cost", "unit price", "quantity", "qty", "amount", "price", "rate", "item"}

    cleaned_values = []
    for line in item_lines:
        cleaned = line.replace('"', '').replace('\\$', '$').strip()
        cleaned = re.sub(r'^,+|,+$', '', cleaned).strip()

        if not cleaned or cleaned == "$" or cleaned.lower() in header_words:
            continue
        cleaned_values.append(cleaned)

    if len(cleaned_values) >= 5 and not cleaned_values[1].isdigit():
        cleaned_values[0] = f"{cleaned_values[0]}, {cleaned_values[1]}"
        del cleaned_values[1]

    items = []
    for index in range(0, len(cleaned_values), 4):
        row = cleaned_values[index: index + 4]
        if len(row) < 4:
            continue
        items.append(
            {
                "description": row[0] if len(row) > 0 else "Unknown Item",
                "quantity": row[1] if len(row) > 1 else "0",
                "unit_cost": row[2] if len(row) > 2 else "0.00",
                "amount": row[3] if len(row) > 3 else "0.00",
            }
        )

    return items


def _extract_financial_details(text):
    lines = _lines(text)
    bill_to_section = _section(
        lines,
        ["Bill To", "Billed To", "Customer", "Vendor"],
        ["Item", "Description", "Particulars", "Subtotal", "Sub Total", "Total"],
    )

    refunded_date = None
    refunded_amount = None
    for index, line in enumerate(lines):
        if "refunded" in line.lower():
            refunded_date = line
            if index + 1 < len(lines):
                refunded_amount = MONEY_PATTERN.search(lines[index + 1])
                refunded_amount = refunded_amount.group(0) if refunded_amount else None
            break

    date_paid = _value_after_label(lines, ["Date paid", "Payment date"])
    if not date_paid:
        date_paid = _value_after_label(lines, ["Date:"])

    return {
        "company": _contact_details(_company_section(lines)),
        "customer": _contact_details(bill_to_section),
        "receipt_number": _value_after_label(lines, ["Receipt Number", "Receipt No", "Receipt #"]),
        "invoice_number": _value_after_label(lines,
                                             ["Invoice Number", "Invoice No", "Invoice #", "PO Number", "PO No"]),
        "date_paid": date_paid,
        "due_date": _value_after_label(lines, ["Due Date", "Payment Due", "Delivery Date"]),
        "payment_method": _value_after_label(lines, ["Payment method", "Payment mode", "Terms of Delivery"]),
        "items": _extract_items(lines),
        "subtotal": _money_after_label(lines, ["Subtotal", "Sub Total"]),
        "tax": _money_after_label(lines, ["Tax", "GST", "VAT"]),
        "total": _money_after_label(lines, ["Total", "Grand Total", "Total Amount"]),
        "amount_paid": _money_after_label(lines, ["Amount paid", "Paid Amount"]),
        "balance_due": _money_after_label(lines, ["Balance Due", "Amount Due"]),
        "refund": {
            "date_or_note": refunded_date,
            "amount": refunded_amount,
        },
    }


def _has_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value != "Not found"
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _add_if_present(target, key, value):
    if _has_value(value):
        target[key] = value


def _important_contact(contact):
    important = {}
    _add_if_present(important, "name", contact.get("name"))
    _add_if_present(important, "address", contact.get("address"))
    _add_if_present(important, "phone", contact.get("phone"))
    _add_if_present(important, "email", contact.get("email"))
    _add_if_present(important, "other_details", contact.get("other_details"))
    return important


def _important_financial_details(financial):
    important = {}
    _add_if_present(important, "company", _important_contact(financial["company"]))
    _add_if_present(important, "customer", _important_contact(financial["customer"]))

    for key in [
        "receipt_number", "invoice_number", "date_paid", "due_date",
        "payment_method", "subtotal", "tax", "total", "amount_paid", "balance_due",
    ]:
        _add_if_present(important, key, financial.get(key))

    refund = financial.get("refund", {})
    important_refund = {}
    _add_if_present(important_refund, "date_or_note", refund.get("date_or_note"))
    _add_if_present(important_refund, "amount", refund.get("amount"))
    _add_if_present(important, "refund", important_refund)
    _add_if_present(important, "items", financial.get("items"))
    return important


def _tables_from_items(items):
    if not items:
        return []

    headers = ["description", "unit_cost", "quantity", "amount"]
    rows = []
    for item in items:
        rows.append([item.get(header, "") for header in headers])

    return [
        {
            "table_summary": _build_table_description(headers, rows)
        }
    ]


def _format_section_preview(content):
    if any(line.strip().startswith("•") or len(line) > 55 or "github.com" in line.lower() for line in content):
        return content

    if len(content) < 6:
        return content

    headers = []
    data_start = 0
    for index, line in enumerate(content):
        line = line.strip()
        if re.search(r"\d{4}", line) or "%" in line or "(" in line:
            data_start = index
            break
        headers.append(line)

    if len(headers) < 2:
        return content

    merged_headers = []
    skip = False
    for i in range(len(headers)):
        if skip:
            skip = False
            continue
        current = headers[i]
        if i + 1 < len(headers) and len(current) <= 15:
            merged_headers.append(current + " " + headers[i + 1])
            skip = True
        else:
            merged_headers.append(current)

    headers = merged_headers
    values = content[data_start:]
    row_size = len(headers)
    formatted = []

    for i in range(0, len(values), row_size):
        row = values[i: i + row_size]
        if len(row) != row_size:
            continue
        arrow_row = []
        for h, v in zip(headers, row):
            arrow_row.append(f"{h} -> {v}")
        formatted.append(" | ".join(arrow_row))

    return formatted if formatted else content


def _important_sections(sections):
    result = []
    for section in sections:
        content = [line.strip() for line in section.get("content", []) if line.strip()]
        if not content:
            continue
        result.append(
            {"heading": section["heading"], "content": _format_section_preview(content)}
        )
    return result


def _important_details(details):
    important = {}
    _add_if_present(important, "title", details.get("title"))

    if details.get("financial_details"):
        financial_details = _important_financial_details(details["financial_details"])
        for key, value in financial_details.items():
            _add_if_present(important, key, value)
        _add_if_present(important, "tables", _tables_from_items(details["financial_details"]["items"]))
        return important

    identifiers = {key: value for key, value in details["identifiers"].items() if _has_value(value)}
    _add_if_present(important, "identifiers", identifiers)
    _add_if_present(important, "dates", details["dates"])
    _add_if_present(important, "emails", details["emails"])
    _add_if_present(important, "phone_numbers", details["phone_numbers"])
    _add_if_present(important, "monetary_amounts", details["monetary_values"])
    _add_if_present(important, "percentages_detected", details["percentages"])  # Preserves percentage tracking cleanly
    _add_if_present(important, "contacts", details["contacts"])

    if details.get("tables") and len(details["tables"]) > 0:
        _add_if_present(important, "tables", details["tables"])

    _add_if_present(important, "sections", _important_sections(details["sections"]))

    return important


def _search_keyword_in_text(text, keyword):
    if not keyword:
        return []

    matches = []
    lowered_keyword = keyword.lower()

    for line in text.splitlines():
        if lowered_keyword in line.lower():
            matches.append(line.strip())

    return _unique(matches)


def format_response(filename, text, search_keyword=None):
    details = _extract_general_details(text)

    if details["document_type"] in {"Receipt", "Invoice", "Purchase Order"}:
        details["financial_details"] = _extract_financial_details(text)

    important_details = _important_details(details)
    keyword_matches = _search_keyword_in_text(text, search_keyword)

    # FIXED: Restored your exact target payload keys (`document_type`, `extracted_data`, etc.)
    return _remove_null_values({
        "filename": filename,
        "document_type": details["document_type"],
        "keyword_search_target": search_keyword if search_keyword else "None Provided",
        "keyword_search_matches": keyword_matches if keyword_matches else "No matches found",
        "extracted_data": important_details
    })