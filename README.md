# AI Study Pal

A Flask-based educational study assistant for Classes 10–12. Students select a class and subject, review a topic from an Excel dataset, take a five-question quiz, receive feedback, view a performance chart, and download a PDF report.

## Features
- Student details and class/subject selection
- Concept, key-points and example display
- Template-based quiz generation from the supplied dataset
- Server-side answer checking
- Score feedback and incorrect-answer review
- Performance chart and downloadable PDF report

## Tech stack
Python, Flask, Pandas, Excel (`Book.xlsx`), Matplotlib, ReportLab, HTML and CSS.

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment:
   - Windows: `py -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the app: `python app.py`
6. Open `http://127.0.0.1:5000`.

## Dataset
`Book.xlsx` contains 18 topic records: six subjects across Classes 10, 11 and 12. The app reads the columns `class`, `subject`, `topic`, `concept_text`, `key_points`, `example`, and `misconception`.

## Important project-scope note
The quiz generator is rule/template-based. It uses the topic text and dataset fields to form questions and distractors. It is **not** a trained machine-learning model and does not currently learn an individual student's ability. The Easy, Medium and Fun options currently change question phrasing rather than implementing calibrated difficulty levels. This README describes the implementation honestly.

## Before public deployment
Set a strong `SECRET_KEY` environment variable, turn off debug mode, add CSRF protection and production hosting configuration, and review the educational content for correctness. This project is a learning prototype, not a production assessment platform.

## Credits
Capstone project by Mohammed Rehan. The original project materials acknowledge support from Launched Global.
