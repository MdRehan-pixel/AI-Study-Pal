# Restoration notes

This folder is a cleaned-up, modernized restoration based on the uploaded original `app.py`, `index.html`, and `Book.xlsx`, plus the project reports.

Preserved core workflow: student details → concept study → quiz → evaluation → feedback/chart → PDF report.

Changes made for this restoration:
- Modern responsive interface and separated CSS.
- Server-side quiz answer storage and evaluation (answers are no longer embedded in hidden form fields).
- Dataset validation and safe handling of missing class/subject combinations.
- Per-session quiz identifiers and PDF generation in memory.
- Removed unreachable duplicated code from the original backend.
- Honest documentation of the rule-based quiz generation; no unsupported claim of trained ML.

The uploaded original files should be retained separately as archival copies.
