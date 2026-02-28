# FileMaker Student Matching — Complete Guide

> Print this. You do not need internet access once you have it.

This guide covers:
- **Part 1** — Export from FileMaker (Keiko + ContactList)
- **Part 2** — Run the Python matching script
- **Part 3** — Review and fix flagged students
- **Part 4** — Import results back into ContactList
- **Part 5** — New student workflow going forward
- **Part 6** — Troubleshooting

**Legend:**
- Lines starting with `>>` are exact values to type.
- Lines starting with `!!` are critical warnings.
- Lines starting with `[CHECK]` are things to verify.

---

## Part 1: Export from FileMaker

You need to export two CSV files — one from Keiko and one from ContactList. These become the input files for the Python script.

### 1.1 Export from Keiko

Keiko is a transaction table. Each row is one class session. You need to export ALL rows. Python will find the earliest date per student automatically.

1. Open the Keiko file in FileMaker Pro.
2. Make sure you are showing ALL records: **Records → Show All Records**
3. From the top menu: **File → Export Records**
4. A Save dialog opens. Navigate to the folder where you saved `match_students.py`.
5. Name the file exactly:
```
   keiko_export.csv
```
6. Set the file type dropdown to **Comma-Separated Values (CSV)** and click **Save**.
7. A field export dialog opens. Add exactly these fields **in this order** to the export list on the right side:
```
   StudentID
   FirstName
   LastName
   ClassDate
   DeductionAmount
```
   To add a field: click it on the left list, then click **Move** or double-click it.  
   To remove a field: click it on the right list and click **Clear**.  
   To reorder: drag fields in the right list.

   > **!!** Make sure ONLY these fields are in the export list. Extra fields will not break anything but keep it clean.

8. Make sure the checkbox says **"Use field names as column names in first row"** (or similar). This must be checked.
9. Click **Export**.

> **[CHECK]** Navigate to your folder and confirm `keiko_export.csv` exists. Open it in any text editor and confirm the first line (header) reads:
> ```
> StudentID,FirstName,LastName,ClassDate,DeductionAmount
> ```
> (order may vary but all must be present)

---

### 1.2 Export from ContactList

1. Open the ContactList file in FileMaker Pro.
2. **Records → Show All Records**
3. **File → Export Records**
4. Navigate to the **same folder** as before.
5. Name the file exactly:
```
   contactlist_export.csv
```
6. Set file type to **Comma-Separated Values (CSV)** and click **Save**.
7. Add exactly these fields to the export list:
```
   StudentID
   FirstName
   LastName
   start_date
   Email
   Address
```
8. Make sure **"Use field names as column names"** is checked.
9. Click **Export**.

> **[CHECK]** Open `contactlist_export.csv` in a text editor. First line should read:
> ```
> StudentID,FirstName,LastName,start_date,Email,Address
> ```

> **!!** If your field names in FileMaker are spelled differently (e.g. `First_Name` instead of `FirstName`), open `match_students.py` in a text editor, find the **CONFIGURATION** section near the top, and update the variable names to match exactly what your CSV headers say.

---

## Part 2: Run the Python Script

### 2.1 Check Python is Installed

1. Open Terminal on your Mac: press `Cmd+Space`, type `Terminal`, press `Enter`.  
   On Windows: press the Windows key, type `cmd`, press `Enter`.
2. Type this and press Enter:
```
   python3 --version
```
   You should see something like: `Python 3.x.x`

   If you see "command not found" then Python is not installed. Go to [python.org](https://python.org), download Python 3, install it, then come back here.

---

### 2.2 Navigate to Your Folder

1. In Terminal, type `cd` followed by a space, then drag your folder from Finder into the Terminal window. This fills in the path. Press Enter.

   Example:
```
   cd /Users/yourname/Desktop/FileMaker
```

2. Type this and press Enter to confirm the right files are there:
```
   ls
```
   You should see:
   - `match_students.py`
   - `keiko_export.csv`
   - `contactlist_export.csv`

   If any are missing, go back to Part 1.

---

### 2.3 Run the Script

1. Type this exactly and press Enter:
```
   python3 match_students.py
```

2. The script runs and will print progress messages. When done you will see something like:
```
   ==================================================
   MATCHING COMPLETE
   ==================================================
   Total Keiko students:     1043
   Auto-matched (confident): 987  -> see matched_students.csv
   Need manual review:        56  -> see review_needed.csv
   Match rate:               94.6%
   ==================================================
```

3. Two new files now exist in your folder:
   - `matched_students.csv` — confident matches
   - `review_needed.csv` — needs your attention

> **[CHECK]** Both files exist in your folder.

> **[CHECK]** `matched_students.csv` has more rows than `review_needed.csv`. If the match rate is below 80%, something may be wrong with your exports — see Part 6: Troubleshooting.

---

## Part 3: Review Flagged Students

Open `review_needed.csv` in Excel or Numbers. Each row is a student that Python could not confidently match. The **REASON** column tells you why. The **ACTION** column tells you what to do.

### The Three Types of Flags

**Type 1: No Name Match**

Python could not find anyone in ContactList with this student's name.

Likely causes: name spelled differently in the two systems (e.g. "Jon" vs "John", "McDonald" vs "MacDonald").

What to do: Search ContactList for this student manually. Find their ContactList StudentID. Add a row to `matched_students.csv` with that `contact_id` and `keiko_id`.

---

**Type 2: Date Mismatch**

Name matched but the earliest Keiko date and ContactList `start_date` are more than 2 months apart.

Likely causes: student was in ContactList for a while before attending their first Keiko class, or `start_date` is not accurate.

What to do: Look at both records and decide if it is the same person. If yes, add to `matched_students.csv`. If no, treat as Type 1.

---

**Type 3: Duplicate Name**

Two or more students in ContactList share this name.

What to do: Look at the `date_diff_days` column. Pick the ContactList record with the smaller date difference. Add ONE row to `matched_students.csv` for this Keiko student using that `contact_id`.

---

### How to Add a Row to matched_students.csv

Open `matched_students.csv` in Excel or a text editor. The columns are:
```
contact_id, keiko_id, first, last, keiko_first_date, contact_start, date_diff_days, confidence
```

Add a new row with:
- `contact_id` — the ContactList StudentID
- `keiko_id` — the Keiko StudentID
- `first`, `last` — student's name
- `confidence` — `MANUAL`

Leave `keiko_first_date`, `contact_start`, `date_diff_days` blank if you don't know them. Save the file when done.

> **[CHECK]** When you have resolved all rows in `review_needed.csv`, `matched_students.csv` should have one row per Keiko student (approximately 1000+ rows).

> **[CHECK]** No `keiko_id` appears more than once.

> **[CHECK]** No `contact_id` appears more than once. (Each student should match to exactly one ContactList record.)

---

## Part 4: Import Results into ContactList

`matched_students.csv` now contains the mapping. You will import it into ContactList so that each ContactList record gets the `KeikoStudentID` field filled in.

> **!!** Before doing this, make sure Phase 1 from the main FileMaker guide is complete — the `KeikoStudentID` field must exist in ContactList before you can import into it.

### 4.1 Prepare ContactList for Import

1. Open ContactList in FileMaker Pro.
2. You are going to import `matched_students.csv` and use it to **update existing records**. FileMaker calls this an "Import with Update."

### 4.2 Run the Import

1. From the top menu: **File → Import Records → File**
2. Navigate to `matched_students.csv`. Select it and click **Open**.
3. An **Import Field Mapping** dialog opens. This is where you tell FileMaker which column in the CSV maps to which field.
4. At the top of the dialog, find the **Import Action** dropdown. Set it to:
```
   Update matching records in found set
```
5. Map the fields (left = CSV columns, right = FileMaker fields):
```
   CSV: contact_id  →  FM field: StudentID
   CSV: keiko_id    →  FM field: KeikoStudentID
```
   For all other CSV columns, set them to **"Do not import"** by clicking the arrow between them until it shows a dash or X.

6. Check the box next to `contact_id` / `StudentID` to tell FileMaker: *find the ContactList record where StudentID matches contact_id, then update KeikoStudentID on that record.*

7. Click **Import**.
8. FileMaker shows a summary: how many records were updated, skipped, etc.

> **[CHECK]** The number of updated records should match approximately the number of rows in `matched_students.csv`.

> **[CHECK]** Open a ContactList record for a student you know is in Keiko. The `KeikoStudentID` field should now be populated.

> **[CHECK]** Open another student and verify the `KeikoStudentID` is correct by cross-checking with Keiko manually.

> **!!** If the update count is 0, the StudentID field mapping is wrong. The `contact_id` in your CSV must match exactly the format of `StudentID` in ContactList (same number format, no leading zeros, etc).

---

## Part 5: New Student Workflow Going Forward

For every new student who joins after this one-time matching is done, follow these steps:

1. Add the new student to ContactList. Their ContactList StudentID is assigned automatically by FileMaker.
2. The new student attends their first class and gets a row added in Keiko. Their Keiko StudentID is assigned by Keiko.
3. Go to ContactList, find the new student, and type their Keiko StudentID into the `KeikoStudentID` field. This is one field, one student, one time — it takes 30 seconds.
4. From that point on, when you enter a deduction in Keiko for that student, the sync script finds them in Urasenke automatically using the `KeikoStudentID` bridge.

> **!!** You must do step 3 before the sync script will work for a new student. If you forget, the script will show an error when you try to submit points for that student.

### Why Not Automate New Student Matching?

For new students, there is only one student to match at a time. Typing one ID number takes less time than any automated solution. Automation is only worth building when you have hundreds of students to match at once, which only happens once — the initial bulk job you just completed.

---

## Part 6: Troubleshooting

**Match rate is below 80%**

Something is likely wrong with your exports. Check:
- Do both CSV files have the right columns?
- Are the column names in the CSV exactly what the CONFIGURATION section in the script expects?
- Open both CSVs and check for encoding issues (strange characters instead of letters). If you see this, re-export from FileMaker and choose UTF-8 encoding if prompted.

---

**Script says "column not found"**

Open `match_students.py` in a text editor. Find the CONFIGURATION section near the top. Update the variable values to match exactly what your CSV headers say. Field names are case sensitive.

---

**Script says "command not found" for python3**

Try `python --version` (without the 3). If that works, use `python` instead of `python3` throughout this guide. If neither works, install Python from [python.org](https://python.org).

---

**Import updated 0 records**

The `contact_id` values in your CSV do not match the `StudentID` values in ContactList. Open both files and compare the format. Common issues:
- ContactList uses text StudentIDs, CSV has numbers (or vice versa)
- Leading zeros: `"0123"` vs `"123"`
- Extra spaces in the CSV

---

**A student was matched to the wrong person**

Find their row in ContactList. Clear the `KeikoStudentID` field and type in the correct Keiko StudentID manually. Then re-run the sync script for that student.

---

**review_needed.csv has hundreds of rows**

This usually means names are spelled very differently between Keiko and ContactList. Check a few rows and see if there is a pattern. Common issues:
- One system uses nicknames (Bob vs Robert)
- One system has middle names included
- Accented characters handled differently

If the pattern is consistent you can fix it in the CSV before re-running the script.

---

*End of Document*
