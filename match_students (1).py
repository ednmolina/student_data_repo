import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict

# ─────────────────────────────────────────────
# CONFIGURATION — update these if your CSV
# column names are different
# ─────────────────────────────────────────────

KEIKO_FILE        = "keiko_export.csv"
CONTACTLIST_FILE  = "contactlist_export.csv"
MATCHED_OUT       = "matched_students.csv"
REVIEW_OUT        = "review_needed.csv"

# Keiko column names (must match your CSV headers exactly)
K_ID        = "StudentID"
K_FIRST     = "FirstName"
K_LAST      = "LastName"
K_DATE      = "ClassDate"

# ContactList column names (must match your CSV headers exactly)
C_ID        = "StudentID"
C_FIRST     = "FirstName"
C_LAST      = "LastName"
C_STARTDATE = "start_date"

# How many days apart the dates can be and still be considered a match
# 60 days = 2 months
DATE_TOLERANCE_DAYS = 60

# ─────────────────────────────────────────────
# DATE PARSING
# Try multiple common date formats FileMaker
# might export
# ─────────────────────────────────────────────

DATE_FORMATS = [
    "%m/%d/%Y",   # 01/15/2020
    "%m-%d-%Y",   # 01-15-2020
    "%Y-%m-%d",   # 2020-01-15
    "%m/%d/%y",   # 01/15/20
    "%d/%m/%Y",   # 15/01/2020
    "%B %d, %Y",  # January 15, 2020
]

def parse_date(date_str):
    """Try to parse a date string using multiple formats."""
    if not date_str or date_str.strip() == "":
        return None
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None  # Could not parse

def normalize_name(first, last):
    """Lowercase and strip whitespace for reliable matching."""
    return (first.strip().lower(), last.strip().lower())

def dates_within_tolerance(date1, date2, tolerance_days=DATE_TOLERANCE_DAYS):
    """Return True if two dates are within tolerance_days of each other."""
    if date1 is None or date2 is None:
        return None  # Cannot determine - flag for review
    diff = abs((date1 - date2).days)
    return diff <= tolerance_days

# ─────────────────────────────────────────────
# STEP 1: LOAD KEIKO DATA
# Get one row per student: their ID, name,
# and earliest class date
# ─────────────────────────────────────────────

print("Loading Keiko data...")

keiko_students = {}  # keiko_id -> {first, last, earliest_date}

if not os.path.exists(KEIKO_FILE):
    print(f"ERROR: Could not find {KEIKO_FILE}")
    print("Make sure the file is in the same folder as this script.")
    exit(1)

with open(KEIKO_FILE, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    # Check columns exist
    cols = reader.fieldnames
    for col in [K_ID, K_FIRST, K_LAST, K_DATE]:
        if col not in cols:
            print(f"ERROR: Column '{col}' not found in {KEIKO_FILE}")
            print(f"Columns found: {cols}")
            print("Update the CONFIGURATION section at the top of this script.")
            exit(1)

    for row in reader:
        kid = row[K_ID].strip()
        if not kid:
            continue

        first = row[K_FIRST].strip()
        last  = row[K_LAST].strip()
        date  = parse_date(row[K_DATE])

        if kid not in keiko_students:
            keiko_students[kid] = {
                "keiko_id":     kid,
                "first":        first,
                "last":         last,
                "earliest_date": date
            }
        else:
            # Keep the earliest date we have seen for this student
            if date and (keiko_students[kid]["earliest_date"] is None or
                         date < keiko_students[kid]["earliest_date"]):
                keiko_students[kid]["earliest_date"] = date

print(f"  Loaded {len(keiko_students)} unique students from Keiko.")

# ─────────────────────────────────────────────
# STEP 2: LOAD CONTACTLIST DATA
# ─────────────────────────────────────────────

print("Loading ContactList data...")

contact_students = {}  # contact_id -> {first, last, start_date}

if not os.path.exists(CONTACTLIST_FILE):
    print(f"ERROR: Could not find {CONTACTLIST_FILE}")
    print("Make sure the file is in the same folder as this script.")
    exit(1)

with open(CONTACTLIST_FILE, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    cols = reader.fieldnames
    for col in [C_ID, C_FIRST, C_LAST, C_STARTDATE]:
        if col not in cols:
            print(f"ERROR: Column '{col}' not found in {CONTACTLIST_FILE}")
            print(f"Columns found: {cols}")
            print("Update the CONFIGURATION section at the top of this script.")
            exit(1)

    for row in reader:
        cid = row[C_ID].strip()
        if not cid:
            continue
        contact_students[cid] = {
            "contact_id":  cid,
            "first":       row[C_FIRST].strip(),
            "last":        row[C_LAST].strip(),
            "start_date":  parse_date(row[C_STARTDATE])
        }

print(f"  Loaded {len(contact_students)} students from ContactList.")

# ─────────────────────────────────────────────
# STEP 3: BUILD NAME INDEX FOR CONTACTLIST
# Group ContactList students by normalized name
# so we can quickly find name matches
# ─────────────────────────────────────────────

contact_by_name = defaultdict(list)  # (first, last) -> list of contact records
for cid, crec in contact_students.items():
    name_key = normalize_name(crec["first"], crec["last"])
    contact_by_name[name_key].append(crec)

# ─────────────────────────────────────────────
# STEP 4: MATCH EACH KEIKO STUDENT
# ─────────────────────────────────────────────

print("Matching students...")

matched   = []  # High confidence matches
review    = []  # Need manual review

for kid, krec in keiko_students.items():
    name_key = normalize_name(krec["first"], krec["last"])
    candidates = contact_by_name.get(name_key, [])

    keiko_date = krec["earliest_date"]

    # ── No name match at all ──
    if len(candidates) == 0:
        review.append({
            "reason":           "NO NAME MATCH",
            "keiko_id":         krec["keiko_id"],
            "keiko_first":      krec["first"],
            "keiko_last":       krec["last"],
            "keiko_first_date": keiko_date.strftime("%m/%d/%Y") if keiko_date else "",
            "contact_id":       "",
            "contact_first":    "",
            "contact_last":     "",
            "contact_start":    "",
            "date_diff_days":   "",
            "action":           "Find this student manually in ContactList and fill in KeikoStudentID"
        })
        continue

    # ── Exactly one name match ──
    if len(candidates) == 1:
        crec = candidates[0]
        contact_date = crec["start_date"]
        within = dates_within_tolerance(keiko_date, contact_date)

        if within is True:
            # High confidence match
            diff = abs((keiko_date - contact_date).days) if keiko_date and contact_date else ""
            matched.append({
                "contact_id":       crec["contact_id"],
                "keiko_id":         krec["keiko_id"],
                "first":            krec["first"],
                "last":             krec["last"],
                "keiko_first_date": keiko_date.strftime("%m/%d/%Y") if keiko_date else "",
                "contact_start":    contact_date.strftime("%m/%d/%Y") if contact_date else "",
                "date_diff_days":   diff,
                "confidence":       "HIGH"
            })
        elif within is False:
            # Name matches but dates are too far apart - flag it
            diff = abs((keiko_date - contact_date).days) if keiko_date and contact_date else ""
            review.append({
                "reason":           "DATE MISMATCH - name matches but dates are far apart",
                "keiko_id":         krec["keiko_id"],
                "keiko_first":      krec["first"],
                "keiko_last":       krec["last"],
                "keiko_first_date": keiko_date.strftime("%m/%d/%Y") if keiko_date else "",
                "contact_id":       crec["contact_id"],
                "contact_first":    crec["first"],
                "contact_last":     crec["last"],
                "contact_start":    contact_date.strftime("%m/%d/%Y") if contact_date else "",
                "date_diff_days":   diff,
                "action":           "Verify this is the same person. If yes, add to matched_students.csv manually."
            })
        else:
            # One or both dates missing - match on name alone, flag as medium confidence
            review.append({
                "reason":           "MISSING DATE - matched by name only, no date to confirm",
                "keiko_id":         krec["keiko_id"],
                "keiko_first":      krec["first"],
                "keiko_last":       krec["last"],
                "keiko_first_date": keiko_date.strftime("%m/%d/%Y") if keiko_date else "NO DATE",
                "contact_id":       crec["contact_id"],
                "contact_first":    crec["first"],
                "contact_last":     crec["last"],
                "contact_start":    contact_date.strftime("%m/%d/%Y") if contact_date else "NO DATE",
                "date_diff_days":   "",
                "action":           "Likely correct. Verify and move to matched_students.csv if confirmed."
            })
        continue

    # ── Multiple name matches (duplicate names) ──
    # Try to narrow down using date
    date_matches = []
    for crec in candidates:
        within = dates_within_tolerance(keiko_date, crec["start_date"])
        if within is True:
            date_matches.append(crec)

    if len(date_matches) == 1:
        # Name duplicates but only one has a matching date - high confidence
        crec = date_matches[0]
        contact_date = crec["start_date"]
        diff = abs((keiko_date - contact_date).days) if keiko_date and contact_date else ""
        matched.append({
            "contact_id":       crec["contact_id"],
            "keiko_id":         krec["keiko_id"],
            "first":            krec["first"],
            "last":             krec["last"],
            "keiko_first_date": keiko_date.strftime("%m/%d/%Y") if keiko_date else "",
            "contact_start":    contact_date.strftime("%m/%d/%Y") if contact_date else "",
            "date_diff_days":   diff,
            "confidence":       "HIGH - duplicate name resolved by date"
        })
    else:
        # Cannot resolve automatically - flag all candidates
        for crec in candidates:
            contact_date = crec["start_date"]
            diff = abs((keiko_date - contact_date).days) if keiko_date and contact_date else ""
            review.append({
                "reason":           "DUPLICATE NAME - cannot auto-resolve",
                "keiko_id":         krec["keiko_id"],
                "keiko_first":      krec["first"],
                "keiko_last":       krec["last"],
                "keiko_first_date": keiko_date.strftime("%m/%d/%Y") if keiko_date else "",
                "contact_id":       crec["contact_id"],
                "contact_first":    crec["first"],
                "contact_last":     crec["last"],
                "contact_start":    contact_date.strftime("%m/%d/%Y") if contact_date else "",
                "date_diff_days":   diff,
                "action":           "Pick the correct ContactList record and add ONE row to matched_students.csv"
            })

# ─────────────────────────────────────────────
# STEP 5: WRITE OUTPUT FILES
# ─────────────────────────────────────────────

print("Writing output files...")

# matched_students.csv - import this into ContactList
with open(MATCHED_OUT, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["contact_id", "keiko_id", "first", "last",
                  "keiko_first_date", "contact_start", "date_diff_days", "confidence"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(matched)

# review_needed.csv - manually resolve these
with open(REVIEW_OUT, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["reason", "keiko_id", "keiko_first", "keiko_last", "keiko_first_date",
                  "contact_id", "contact_first", "contact_last", "contact_start",
                  "date_diff_days", "action"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(review)

# ─────────────────────────────────────────────
# STEP 6: PRINT SUMMARY
# ─────────────────────────────────────────────

total_keiko = len(keiko_students)
total_matched = len(matched)
total_review = len(review)

print("")
print("=" * 50)
print("MATCHING COMPLETE")
print("=" * 50)
print(f"Total Keiko students:     {total_keiko}")
print(f"Auto-matched (confident): {total_matched}  -> see {MATCHED_OUT}")
print(f"Need manual review:       {total_review}  -> see {REVIEW_OUT}")
print(f"Match rate:               {round(total_matched/total_keiko*100, 1)}%")
print("")
print("NEXT STEPS:")
print("1. Open review_needed.csv and resolve each flagged row.")
print("   For each one you confirm, add a row to matched_students.csv.")
print("2. When matched_students.csv is complete, import it into")
print("   ContactList following the import instructions in the guide.")
print("=" * 50)
