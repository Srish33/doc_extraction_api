import re


MONEY_PATTERN = re.compile(
    r"(?:Rs\.?|INR|USD|EUR|GBP|\$|€|£)\s?\d[\d,]*(?:\.\d{1,2})?",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(r"(?:\+?[ \t]?\(?\d[\d \t().-]{7,}\d)")
DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
    r"\s+\d{1,2},?\s+\d{4}|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
    r"\s+\d{4})\b",
    re.IGNORECASE,
)

DOCUMENT_KEYWORDS = {
    "Receipt": ["receipt", "amount paid", "payment method", "date paid"],
    "Invoice": ["invoice", "invoice number", "bill to", "due date", "balance due"],
    "Resume": ["resume", "curriculum vitae", "experience", "education", "skills"],
    "Bank Statement": ["statement", "account number", "opening balance", "closing balance"],
    "Report": ["report", "abstract", "introduction", "conclusion", "findings"],
    "Agreement": ["agreement", "contract", "terms and conditions", "party", "signature"],
    "Certificate": ["certificate", "certifies", "awarded", "issued"],
    "Letter": ["dear", "subject", "sincerely", "regards"],
}

SECTION_HEADERS = {
    "abstract",
    "account details",
    "agreement",
    "amount",
    "bill from",
    "bill to",
    "certificate",
    "conclusion",
    "contact",
    "customer",
    "date",
    "description",
    "education",
    "experience",
    "findings",
    "invoice",
    "item",
    "payment",
    "receipt",
    "report",
    "seller",
    "ship to",
    "skills",
    "summary",
    "sub total",
    "subtotal",
    "tax",
    "terms",
    "total",
}

TABLE_HEADER_LABELS = {
    "amount",
    "balance",
    "credit",
    "date",
    "debit",
    "description",
    "discount",
    "item",
    "particulars",
    "price",
    "qty",
    "quantity",
    "rate",
    "total",
    "unit cost",
    "unit price",
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
    """Replace JSON null values with API-friendly empty defaults."""
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

    for line in lines[label_index + 1 : label_index + 4]:
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

    return lines[start_index + 1 : end_index]


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

    for line in section_lines[1:]:
        email_match = EMAIL_PATTERN.search(line)
        phone_match = PHONE_PATTERN.search(line)
        if email_match and not email:
            email = email_match.group(0)
        elif phone_match and not phone:
            phone = phone_match.group(0)
        elif line.replace(" ", "").isdigit():
            other_details.append(line)
        elif not MONEY_PATTERN.search(line):
            address.append(line)
        else:
            other_details.append(line)

    return {
        "name": section_lines[0],
        "address": address,
        "phone": phone,
        "email": email,
        "other_details": other_details,
    }


def _detect_document_type(text):
    lowered_text = text.lower()
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
            is_label = re.search(r"(number|no|date|name|method|total|amount|id)$", normalized)
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
        "order_number": ["Order Number", "Order No", "Order #"],
        "customer_id": ["Customer ID", "Customer No", "Client ID"],
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

    for line in lines:

        normalized = line.rstrip(":").lower()

        is_header = (
            normalized in SECTION_HEADERS
            or (
                line.isupper()
                and len(line.split()) <= 4
                and len(line) <= 30
            )
        )

        if is_header:
            if current:
                sections.append(current)

            current = {
                "heading": line.rstrip(":"),
                "content": []
            }

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


def _arrow_rows(headers, rows):
    arrow_output = []
    for row in rows:
        pairs = []
        for index, header in enumerate(headers):
            value = row[index] if index < len(row) else ""
            pairs.append(f"{header} -> {value}")
        arrow_output.append(pairs)
    return arrow_output


def _table_from_rows(rows):
    if len(rows) < 2:
        return None

    headers = rows[0]
    data_rows = rows[1:]
    return {
        "headers": headers,
        "rows": data_rows,
        "arrow_rows": _arrow_rows(headers, data_rows),
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
            row = values[value_index : value_index + len(headers)]
            if len(row) == len(headers):
                rows.append(row)

        if rows:
            tables.append(
                {
                    "headers": headers,
                    "rows": rows,
                    "arrow_rows": _arrow_rows(headers, rows),
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
    words = re.findall(r"\b\w+\b", text)
    emails = _unique(EMAIL_PATTERN.findall(text))
    phones = _extract_phone_numbers(text)
    dates = _unique(match.group(0) for match in DATE_PATTERN.finditer(text))
    money_values = _unique(match.group(0) for match in MONEY_PATTERN.finditer(text))

    return {
        "document_type": _detect_document_type(text),
        "title": _extract_title(lines),
        "overview": {
            "total_lines": len(lines),
            "total_words": len(words),
            "total_characters": len(text),
        },
        "key_value_fields": _extract_key_value_fields(lines),
        "identifiers": _extract_identifiers(lines),
        "contacts": _extract_contact_blocks(lines),
        "emails": emails,
        "phone_numbers": phones,
        "dates": dates,
        "monetary_values": money_values,
        "sections": _extract_sections(lines),
        "table_like_rows": _extract_table_like_rows(lines),
        "tables": _extract_tables(lines),
    }


def _company_section(lines):
    payment_index = _find_label_index(lines, ["Payment method", "Payment mode"])
    bill_to_index = _find_label_index(lines, ["Bill To", "Billed To", "Customer"])
    if payment_index == -1 or bill_to_index == -1 or payment_index >= bill_to_index:
        return []

    return lines[payment_index + 2 : bill_to_index]


def _extract_items(lines):
    item_index = _find_label_index(lines, ["Item", "Description"])
    subtotal_index = _find_label_index(lines, ["Subtotal", "Sub Total"])
    if item_index == -1:
        return []

    end_index = subtotal_index if subtotal_index != -1 else len(lines)
    item_lines = lines[item_index + 1 : end_index]
    header_words = {"unit cost", "unit price", "quantity", "qty", "amount", "price"}
    values = [line for line in item_lines if line.lower() not in header_words]
    items = []

    for index in range(0, len(values), 4):
        row = values[index : index + 4]
        if len(row) < 4:
            continue
        items.append(
            {
                "description": row[0],
                "unit_cost": row[1],
                "quantity": row[2],
                "amount": row[3],
            }
        )

    return items


def _extract_financial_details(text):
    lines = _lines(text)
    bill_to_section = _section(
        lines,
        ["Bill To", "Billed To", "Customer"],
        ["Item", "Description", "Subtotal", "Sub Total", "Total"],
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

    return {
        "company": _contact_details(_company_section(lines)),
        "customer": _contact_details(bill_to_section),
        "receipt_number": _value_after_label(lines, ["Receipt Number", "Receipt No", "Receipt #"]),
        "invoice_number": _value_after_label(lines, ["Invoice Number", "Invoice No", "Invoice #"]),
        "date_paid": _value_after_label(lines, ["Date paid", "Payment date", "Date"]),
        "due_date": _value_after_label(lines, ["Due Date", "Payment Due"]),
        "payment_method": _value_after_label(lines, ["Payment method", "Payment mode"]),
        "items": _extract_items(lines),
        "subtotal": _money_after_label(lines, ["Subtotal", "Sub Total"]),
        "tax": _money_after_label(lines, ["Tax", "GST", "VAT"]),
        "total": _money_after_label(lines, ["Total", "Grand Total"]),
        "amount_paid": _money_after_label(lines, ["Amount paid", "Paid Amount"]),
        "balance_due": _money_after_label(lines, ["Balance Due", "Amount Due"]),
        "refund": {
            "date_or_note": refunded_date,
            "amount": refunded_amount,
        },
    }


def _detail_points(details):
    points = [
        f"Document Type: {details['document_type']}",
        f"Title: {details['title'] or 'Not found'}",
        f"Total Lines: {details['overview']['total_lines']}",
        f"Total Words: {details['overview']['total_words']}",
    ]

    for key, value in details["identifiers"].items():
        if value:
            label = key.replace("_", " ").title()
            points.append(f"{label}: {value}")

    if details["dates"]:
        points.append(f"Dates Found: {', '.join(details['dates'])}")
    if details["emails"]:
        points.append(f"Emails Found: {', '.join(details['emails'])}")
    if details["phone_numbers"]:
        points.append(f"Phone Numbers Found: {', '.join(details['phone_numbers'])}")
    if details["monetary_values"]:
        points.append(f"Monetary Values Found: {', '.join(details['monetary_values'])}")

    financial = details.get("financial_details")
    if financial:
        company = financial["company"]
        customer = financial["customer"]
        if company["name"]:
            points.append(f"Company Name: {company['name']}")
        if company["address"]:
            points.append(f"Company Address: {', '.join(company['address'])}")
        if customer["name"]:
            points.append(f"Customer Name: {customer['name']}")
        for label in ["payment_method", "subtotal", "tax", "total", "amount_paid", "balance_due"]:
            value = financial.get(label)
            if value:
                points.append(f"{label.replace('_', ' ').title()}: {value}")
        for index, item in enumerate(financial["items"], start=1):
            points.append(
                "Item "
                f"{index}: {item['description']} | Unit Cost: {item['unit_cost']} | "
                f"Quantity: {item['quantity']} | Amount: {item['amount']}"
            )

    for key, value in details["key_value_fields"].items():
        points.append(f"{key}: {value}")

    return _unique(points)


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
        "receipt_number",
        "invoice_number",
        "date_paid",
        "due_date",
        "payment_method",
        "subtotal",
        "tax",
        "total",
        "amount_paid",
        "balance_due",
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
            "headers": headers,
            "rows": rows,
            "arrow_rows": _arrow_rows(headers, rows),
        }
    ]

def _format_section_preview(content):
    """
    Detect resume/invoice style vertical tables and
    convert them into arrow-row format.
    """

    if len(content) < 6:
        return content

    # Step 1: Detect header block
    headers = []
    data_start = 0

    for index, line in enumerate(content):
        line = line.strip()

        # Stop header detection once actual data starts
        if (
            re.search(r"\d{4}", line)
            or "%" in line
            or "(" in line
        ):
            data_start = index
            break

        headers.append(line)

    # Need at least 2 headers
    if len(headers) < 2:
        return content

    # Step 2: Merge broken headers
    merged_headers = []
    skip = False

    for i in range(len(headers)):
        if skip:
            skip = False
            continue

        current = headers[i]

        if (
            i + 1 < len(headers)
            and len(current) <= 15
        ):
            merged_headers.append(current + " " + headers[i + 1])
            skip = True
        else:
            merged_headers.append(current)

    headers = merged_headers

    # Step 3: Extract rows
    values = content[data_start:]

    row_size = len(headers)

    formatted = []

    for i in range(0, len(values), row_size):
        row = values[i:i + row_size]

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

        content = [
            line.strip()
            for line in section.get("content", [])
            if line.strip()
        ]

        if not content:
            continue

        result.append(
            {
                "heading": section["heading"],
                "content": _format_section_preview(content)
            }
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

    identifiers = {
        key: value
        for key, value in details["identifiers"].items()
        if _has_value(value)
    }
    _add_if_present(important, "identifiers", identifiers)
    _add_if_present(important, "dates", details["dates"])
    _add_if_present(important, "emails", details["emails"])
    _add_if_present(important, "phone_numbers", details["phone_numbers"])
    _add_if_present(important, "amounts", details["monetary_values"])

    _add_if_present(important, "fields", details["key_value_fields"])
    _add_if_present(important, "contacts", details["contacts"])
    _add_if_present(important, "tables", details["tables"])
    _add_if_present(important, "sections", _important_sections(details["sections"]))

    return important


def _humanize_key(key):
    return key.replace("_", " ").title()


def _preview_value(value):
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if _has_value(item):
                parts.append(f"{_humanize_key(key)}: {_preview_value(item)}")
        return ", ".join(parts)
    if isinstance(value, list):
        parts = [_preview_value(item) for item in value if _has_value(item)]
        return "; ".join(part for part in parts if part)
    return str(value)


def _document_preview(important_details):
    preview_parts = []
    for key, value in important_details.items():
        if not _has_value(value):
            continue
        preview_parts.append(f"{_humanize_key(key)}: {_preview_value(value)}")
    return ". ".join(preview_parts)


def format_response(filename, text):
    """Build the final JSON-friendly response object."""
    details = _extract_general_details(text)
    if details["document_type"] in {"Receipt", "Invoice"}:
        details["financial_details"] = _extract_financial_details(text)
    important_details = _important_details(details)

    response = {
        "filename": filename,
        "document_type": details["document_type"],
        "important_details_heading": "Important Details",
        "important_details": important_details,
        "document_preview_heading": "Document Preview",
        "document_preview": _document_preview(important_details),
    }

    return _remove_null_values(response)
