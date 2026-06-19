import re
import pandas as pd
from django.db import transaction
from django.utils import timezone
from .models import ReferenceCounter


# =====================================================
# REFERENCE NUMBER GENERATOR
# =====================================================

def get_next_reference(prefix):
    """
    Atomically increment the counter for the given prefix and return
    a formatted reference string.

    e.g. SLR → "SLR00000001", "SLR00000002", ...
         SUP → "SUP00000001", "SUP00000002", ...  (independent)
    """
    with transaction.atomic():
        counter, _ = ReferenceCounter.objects.select_for_update().get_or_create(
            prefix=prefix,
            defaults={"last_number": 0}
        )
        counter.last_number += 1
        counter.save()
        return f"{prefix}{str(counter.last_number).zfill(8)}"


# =====================================================
# OBDX FILENAME BUILDER
#
# Required pattern (per CRWB/OBDX naming spec):
#   {PREFIX}_{PARTYID}_{DDMMYYYY}.txt
#
# PARTYID = first 9 digits of the originating (debit) account number
#           used for that file's transactions.
# Max length is 50 characters (incl. underscores/dots, excl. extension) —
# enforced by truncation below.
# =====================================================

def build_party_id(account_number):
    """Extract the OBDX Party ID: the first 9 digits of an account number."""
    digits_only = re.sub(r"\D", "", str(account_number))
    return digits_only[:9]


def build_export_filename(prefix, debit_account_num, extension="txt"):
    party_id = build_party_id(debit_account_num)
    now = timezone.now()
    date_part = now.strftime("%d.%m.%Y")
    time_suffix = now.strftime("%H%M%S")
    base_name = f"{prefix}_{party_id}_{date_part}{time_suffix}"
    base_name = base_name[:50]  # enforce 50-character cap from the spec
    return f"{base_name}.{extension}"


# =====================================================
# HELPERS
# =====================================================

def format_amount(value):
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "0.00"


def format_date(value):
    """
    Parse any date value and return DD.MM.YYYY string per OBDX spec.
    Returns empty string if value is null/unparseable.
    """
    if pd.isna(value) or str(value).strip() == "":
        return ""
    try:
        return pd.to_datetime(value, errors="raise").strftime("%d.%m.%Y")
    except Exception:
        return str(value).strip()


def build_header(prefix, currency, total_amount, count):
    return f"0;{prefix};{currency};{total_amount:.2f};{str(count).zfill(4)}"


def clean_columns(df):
    df = df.fillna("")
    df.columns = (
        df.columns
        .str.replace("\t", "", regex=True)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )
    return df


def safe_numeric(df, col):
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    else:
        df[col] = 0
    return df


def safe(row, field):
    val = row.get(field, "")
    if pd.isna(val):
        return ""
    return str(val)


# =====================================================
# VALIDATION
# Checks that required columns exist AND are non-empty.
# Reference columns are intentionally excluded from
# required_fields in every converter below — they are
# always auto-generated.
# =====================================================

def validate_required_fields(df, required_fields):
    df_cols = set(df.columns)

    missing_columns = [c for c in required_fields if c not in df_cols]
    if missing_columns:
        raise ValueError(f"VALIDATION_ERROR: Missing columns {missing_columns}")

    for field in required_fields:
        empty_rows = (
            df[field]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
        )
        if empty_rows.any():
            raise ValueError(f"VALIDATION_ERROR: Empty values in column '{field}'")


# =====================================================
# SALARY PAYMENT
# Template columns: Trans Serial, Vote Num, Currency, Debit Account Num,
#   Bank Name, Funding TRF Num, Credit Account Num, Reference Num,
#   Credit Account Name, Payee BIC, Cost Center, Description, Amount, Value Date
# Note: "Reference Num" column exists in template but is auto-generated — excluded.
# =====================================================

def convert_salary(df):
    df = clean_columns(df)

    required_fields = [
        "Trans Serial",
        "Vote Num",
        "Currency",
        "Debit Account Num",
        "Bank Name",
        "Funding TRF Num",
        "Credit Account Num",
        "Credit Account Name",
        "Payee BIC",
        "Cost Center",
        "Description",
        "Amount",
        "Value Date",
        # "Reference Num" intentionally omitted — auto-generated below
    ]

    validate_required_fields(df, required_fields)

    df["Amount"] = pd.to_numeric(df["Amount"], errors="raise")
    if (df["Amount"] <= 0).any():
        raise ValueError("Invalid Amount values — all amounts must be greater than zero")

    # Format Value Date to DD.MM.YYYY per spec
    df["Value Date"] = df["Value Date"].apply(format_date)

    total_amount = df["Amount"].sum()
    first = df.iloc[0]

    header = [
        "0",
        first["Vote Num"],
        f"{total_amount:.2f}",
        first["Currency"],
        first["Debit Account Num"],
        first["Funding TRF Num"],
        first["Description"],
        first["Value Date"],
        str(len(df)).zfill(4),
    ]

    lines = [";".join(map(str, header))]
    references = []

    for _, r in df.iterrows():
        reference = get_next_reference("SLR")
        references.append(reference)
        line = [
            "1",
            r["Payee BIC"],
            r["Credit Account Num"],
            reference,
            r["Credit Account Name"],
            r["Bank Name"],
            r["Cost Center"],
            r["Description"],
            f"{float(r['Amount']):.1f}",
        ]
        lines.append(";".join(map(str, line)))

    return "\n".join(lines), references


# =====================================================
# SUPPLIER PAYMENT
# Template columns: Trans Serial, Currency, Debit Account Num,
#   Debit Account Name, Payment Amount, Payee Details, Vendor Code,
#   Emp Num, National ID, Invoice Num, Payee BIC, Credit Account Num,
#   Cost Center, Date, Reference Num, Description
# Note: "Reference Num" column exists in template but is auto-generated — excluded.
# =====================================================

def convert_supplier(df):
    df = clean_columns(df)
    df = safe_numeric(df, "Payment Amount")

    required_fields = [
        "Currency",
        "Debit Account Num",
        "Debit Account Name",
        "Payment Amount",
        "Payee Details",
        "Invoice Num",
        "Payee BIC",
        "Credit Account Num",
        "Cost Center",
        "Description",
        # "Reference Num" intentionally omitted — auto-generated below
    ]

    validate_required_fields(df, required_fields)

    currency   = str(df.iloc[0].get("Currency", "MWK"))
    file_total = df["Payment Amount"].sum()

    lines = [build_header("OBDXSP", currency, file_total, len(df))]
    references = []

    for i, r in df.iterrows():
        reference = get_next_reference("SUP")
        references.append(reference)
        serial = str(i + 1).zfill(4)
        line = [
            "1",
            serial,
            r.get("Currency", ""),
            r.get("Debit Account Num", ""),
            r.get("Debit Account Name", ""),
            format_amount(r.get("Payment Amount", 0)),
            r.get("Payee Details", ""),
            r.get("Vendor Code", ""),
            r.get("Emp Num", ""),
            r.get("National ID", ""),
            r.get("Invoice Num", ""),
            r.get("Payee BIC", ""),
            r.get("Credit Account Num", ""),
            r.get("Cost Center", ""),
            format_date(r.get("Date", "")),   # ← DD.MM.YYYY
            reference,
            r.get("Description", ""),
        ]
        lines.append(";".join(map(str, line)))

    return "\n".join(lines), references


# =====================================================
# REMITTANCE PRN
# Template columns: Trans Serial, Debit Account Num, Debit Account Name,
#   Currency, Credit Account Num, Currency.1, Payment Amount, Creditor Name,
#   Payment Date, Date Created, Reference Num, Cost Centre, PRN
# Note: "Reference Num" column exists in template but is auto-generated — excluded.
# =====================================================

def convert_remittancePRN(df):
    df = clean_columns(df)
    df = safe_numeric(df, "Payment Amount")

    required_fields = [
        "Debit Account Num",
        "Debit Account Name",
        "Currency",
        "Credit Account Num",
        "Payment Amount",
        "Creditor Name",
        "Payment Date",
        "Date Created",
        "Cost Centre",
        "PRN",
        # "Reference Num" intentionally omitted — auto-generated below
    ]

    validate_required_fields(df, required_fields)

    file_total = df["Payment Amount"].sum()
    lines = [f"0;OBDXPRN;{file_total:.2f};{str(len(df)).zfill(4)}"]
    references = []

    for i, r in df.iterrows():
        reference = get_next_reference("PRN")
        references.append(reference)
        serial = str(i + 1).zfill(4)
        line = [
            "2",
            serial,
            r.get("Debit Account Num", ""),
            r.get("Debit Account Name", ""),
            r.get("Currency", ""),
            r.get("Credit Account Num", ""),
            r.get("Currency", ""),
            format_amount(r.get("Payment Amount", 0)),
            r.get("Creditor Name", ""),
            format_date(r.get("Payment Date", "")),   # ← DD.MM.YYYY
            format_date(r.get("Date Created", "")),   # ← DD.MM.YYYY
            reference,
            r.get("Cost Centre", ""),
            r.get("PRN", ""),
        ]
        lines.append(";".join(map(str, line)))

    return "\n".join(lines), references


# =====================================================
# REMITTANCE TR
# Template columns: Trans Serial, Debit Account Num, Debit Account Name,
#   Debit Currency, Credit Account Num, Credit Currency, Payment Amount,
#   Creditor Name, Payment Date, Date created, Reference Num, Cost Centre
# Note: "Reference Num" column exists in template but is auto-generated — excluded.
# Debit Currency and Credit Currency are separate to support cross-currency
# transactions (e.g. MWK debit, USD credit).
# =====================================================

def convert_remittanceTR(df):
    df = clean_columns(df)
    df = safe_numeric(df, "Payment Amount")

    required_fields = [
        "Debit Account Num",
        "Debit Account Name",
        "Currency",    # ← split from single "Currency"
        "Credit Account Num",
        "Currency",   # ← split from single "Currency"
        "Payment Amount",
        "Creditor Name",
        "Payment Date",
        "Date Created",      # ← uppercase 'C' matches template exactly
        "Cost Centre",
        # "Reference Num" intentionally omitted — auto-generated below
    ]

    validate_required_fields(df, required_fields)

    file_total = df["Payment Amount"].sum()
    lines = [f"0;CRWB;{file_total:.2f};{str(len(df)).zfill(4)}"]
    references = []

    for i, r in df.iterrows():
        reference = get_next_reference("TRN")
        references.append(reference)
        serial = str(i + 1).zfill(4)
        line = [
            "2",
            serial,
            r.get("Debit Account Num", ""),
            r.get("Debit Account Name", ""),
            r.get("Debit Currency", ""),            # ← debit currency
            r.get("Credit Account Num", ""),
            r.get("Credit Currency", ""),           # ← credit currency (can differ)
            format_amount(r.get("Payment Amount", 0)),
            r.get("Creditor Name", ""),
            format_date(r.get("Payment Date", "")),  # ← DD.MM.YYYY
            format_date(r.get("Date created", "")),  # ← DD.MM.YYYY
            reference,
            r.get("Cost Centre", ""),
        ]
        lines.append(";".join(map(str, line)))

    return "\n".join(lines), references


# =====================================================
# FOREIGN PAYMENT
# Template columns: Trans Serial, Currency, Debit Account, Account Name,
#   Amount, Amount in words, Payee Details1, Payee Details2, Invoice Number,
#   Bank Branch Code, Payee BIC, Credit Account, Cost Center, Approval Date,
#   Reference Number, Surname, First Name, Sector Code, Industrial Class, BOP Category
# Note: "Reference Number" column exists in template but is auto-generated — excluded.
# Optional cols (not in template, safe() returns "" if absent):
#   Corresponding Bank, Corresponding Country, Non-Resident, Subject,
#   Description, Individua Surname, Individual Name, Individual Gender,
#   CostOfGoods, Freight
# =====================================================

def convert_foreign(df):
    df = clean_columns(df)
    df = safe_numeric(df, "Amount")

    if df.empty:
        raise ValueError("File is empty")

    required_fields = [
        "Trans Serial",
        "Currency",
        "Debit Account",
        "Account Name",
        "Amount",
        "Amount in words",
        "Payee Details1",
        "Payee Details2",
        "Invoice Number",
        "Bank Branch Code",
        "Payee BIC",
        "Credit Account",
        "Cost Center",
        "Approval Date",
        "Surname",
        "First Name",
        "Sector Code",
        "Industrial Class",
        "BOP Category",
        # "Reference Number" intentionally omitted — auto-generated below
    ]

    validate_required_fields(df, required_fields)

    currency     = str(df.iloc[0].get("Currency", "MWK"))
    total_amount = df["Amount"].sum()

    lines = [build_header("CRWB", currency, total_amount, len(df))]
    references = []

    for i, r in df.iterrows():
        reference = get_next_reference("FRX")
        references.append(reference)
        serial = str(i + 1).zfill(4)
        line = [
            "1",
            serial,
            safe(r, "Currency"),
            safe(r, "Debit Account"),
            safe(r, "Account Name"),
            format_amount(r.get("Amount", 0)),
            safe(r, "Amount in words"),
            safe(r, "Payee Details1"),
            safe(r, "Payee Details2"),
            safe(r, "Invoice Number"),
            safe(r, "Bank Branch Code"),
            safe(r, "Payee BIC"),
            safe(r, "Credit Account"),
            safe(r, "Cost Center"),
            format_date(r.get("Approval Date", "")),  # ← DD.MM.YYYY
            reference,
            safe(r, "Corresponding Bank"),
            safe(r, "Corresponding Country"),
            safe(r, "Non-Resident"),
            safe(r, "Surname"),
            safe(r, "First Name"),
            safe(r, "Sector Code"),
            safe(r, "Industrial Class"),
            safe(r, "BOP Category"),
            safe(r, "Subject"),
            safe(r, "Description"),
            safe(r, "Individua Surname"),
            safe(r, "Individual Name"),
            safe(r, "Individual Gender"),
            safe(r, "CostOfGoods"),
            safe(r, "Freight"),
        ]
        lines.append(";".join(line))

    return "\n".join(lines), references