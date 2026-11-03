from __future__ import annotations

import io
import os
import random
import secrets
from html import escape
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from flask import Flask, abort, flash, redirect, render_template, request, send_file, session, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "Book.xlsx"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

REQUIRED_COLUMNS = {
    "class", "subject", "topic", "concept_text",
    "key_points", "example", "misconception"
}


def load_dataset() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError("Book.xlsx is missing. Place it beside app.py.")
    data = pd.read_excel(DATA_FILE)
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Book.xlsx is missing columns: {', '.join(sorted(missing))}")
    data["class"] = pd.to_numeric(data["class"], errors="coerce")
    data = data.dropna(subset=["class", "subject", "topic", "concept_text"])
    data["class"] = data["class"].astype(int)
    for col in REQUIRED_COLUMNS - {"class"}:
        data[col] = data[col].fillna("").astype(str).str.strip()
    return data


df = load_dataset()


def get_subjects(class_no: int) -> list[str]:
    return sorted(df.loc[df["class"] == class_no, "subject"].dropna().unique().tolist())


def get_topic_row(class_no: int, subject: str):
    matches = df[(df["class"] == class_no) & (df["subject"] == subject)]
    if matches.empty:
        return None
    return matches.iloc[0]


def build_questions(row, difficulty: str) -> list[dict]:
    """Builds template-based questions from the supplied concept data (not an ML model)."""
    concept = str(row["concept_text"])
    sentences = [part.strip() for part in concept.replace("\n", " ").split(".") if len(part.strip()) > 25]
    if not sentences:
        sentences = [concept.strip() or f"{row['topic']} is an important topic."]
    random.shuffle(sentences)

    templates = [
        f"What is {row['topic']}?",
        f"Which statement best explains {row['topic']}?",
        f"Why is {row['topic']} useful?",
        f"Which idea is most closely related to {row['topic']}?",
        f"Which statement about {row['topic']} is correct?",
    ]
    if difficulty == "easy":
        templates = [
            f"Choose the correct explanation of {row['topic']}.",
            f"What is the main idea of {row['topic']}?",
            f"Which statement describes {row['topic']}?",
            f"Select the correct fact about {row['topic']}.",
            f"What should you remember about {row['topic']}?",
        ]
    elif difficulty == "fun":
        templates = [
            f"Quick challenge: which option describes {row['topic']}?",
            f"Imagine explaining {row['topic']} to a friend. Which is correct?",
            f"Pick the true fact about {row['topic']}!",
            f"Knowledge check: what does {row['topic']} involve?",
            f"Which clue points to {row['topic']}?",
        ]

    misconception = str(row["misconception"]).strip()
    example = str(row["example"]).strip()
    key_points = str(row["key_points"]).strip()
    distractors = [x for x in [misconception, example, key_points] if x and x not in sentences]
    questions = []
    used_answers = set()
    for i, prompt in enumerate(templates):
        candidates = [s for s in sentences if s not in used_answers] or sentences
        answer = candidates[i % len(candidates)]
        used_answers.add(answer)
        options = [answer]
        for candidate in distractors:
            if candidate not in options:
                options.append(candidate)
            if len(options) == 4:
                break
        generic = [
            f"{row['topic']} is unrelated to the subject.",
            "It is only useful for memorising examination answers.",
            "It has no practical applications.",
        ]
        for candidate in generic:
            if len(options) == 4:
                break
            if candidate not in options:
                options.append(candidate)
        random.shuffle(options)
        questions.append({"question": prompt, "options": options, "answer": answer})
    return questions


def make_chart(score: int, total: int) -> io.BytesIO:
    chart = io.BytesIO()
    fig, ax = plt.subplots(figsize=(5, 4))
    values = [score, max(total - score, 0)]
    if total == 0:
        values = [0, 1]
    ax.pie(values, labels=["Correct", "Incorrect"], autopct="%1.1f%%",
           startangle=90, colors=["#16a085", "#f39c12"])
    ax.set_title("Performance Analysis")
    fig.tight_layout()
    fig.savefig(chart, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    chart.seek(0)
    return chart


def create_pdf(result: dict) -> io.BytesIO:
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=18*mm,
                            leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("BodyCustom", parent=styles["BodyText"], leading=15, spaceAfter=6)
    story = [
        Paragraph("AI Study Pal — Student Report", styles["Title"]),
        Spacer(1, 8*mm),
        Paragraph(f"<b>Name:</b> {escape(result['name'])}", body),
        Paragraph(f"<b>Class:</b> {result['class_no']}", body),
        Paragraph(f"<b>Subject:</b> {escape(result['subject'])}", body),
        Paragraph(f"<b>Topic:</b> {escape(result['topic'])}", body),
        Paragraph(f"<b>Difficulty:</b> {escape(result['difficulty'].title())}", body),
        Paragraph(f"<b>Score:</b> {result['score']}/{result['total']}", body),
        Spacer(1, 4*mm),
        Paragraph("<b>Overall feedback</b>", styles["Heading2"]),
        Paragraph(escape(result["feedback"]), body),
    ]
    chart = make_chart(result["score"], result["total"])
    story += [Spacer(1, 3*mm), Image(chart, width=105*mm, height=80*mm)]
    if result["wrong_questions"]:
        story += [Spacer(1, 4*mm), Paragraph("Areas to Improve", styles["Heading2"])]
        for item in result["wrong_questions"]:
            story.append(Paragraph(f"<b>Question:</b> {escape(item['question'])}", body))
            story.append(Paragraph(f"<b>Your answer:</b> {escape(item['your_answer'])}", body))
            story.append(Paragraph(f"<b>Correct answer:</b> {escape(item['correct_answer'])}", body))
            story.append(Spacer(1, 2*mm))
    doc.build(story)
    output.seek(0)
    return output


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return render_template("index.html", step="welcome")

    step = request.form.get("step", "welcome")
    if step == "details":
        return render_template("index.html", step="details", classes=[10, 11, 12])

    if step == "study":
        name = request.form.get("name", "").strip()
        class_raw = request.form.get("class", "")
        subject = request.form.get("subject", "").strip()
        if not name or not class_raw.isdigit():
            flash("Please enter your name and select a valid class.", "error")
            return redirect(url_for("home"))
        class_no = int(class_raw)
        if class_no not in [10, 11, 12] or subject not in get_subjects(class_no):
            flash("That class and subject combination is not available in the dataset.", "error")
            return render_template("index.html", step="details", classes=[10, 11, 12])
        row = get_topic_row(class_no, subject)
        session["student"] = {"name": name, "class_no": class_no, "subject": subject,
                              "topic": row["topic"]}
        return render_template("index.html", step="study", student=session["student"],
                               concept=row["concept_text"], key_points=row["key_points"],
                               example=row["example"])

    if step == "quiz":
        student = session.get("student")
        if not student:
            flash("Please enter your details first.", "error")
            return redirect(url_for("home"))
        difficulty = request.form.get("difficulty", "easy")
        if difficulty not in {"easy", "medium", "fun"}:
            difficulty = "easy"
        row = get_topic_row(student["class_no"], student["subject"])
        if row is None:
            abort(400)
        quiz = build_questions(row, difficulty)
        quiz_id = secrets.token_urlsafe(12)
        session["active_quiz"] = {"id": quiz_id, "difficulty": difficulty, "questions": quiz}
        return render_template("index.html", step="quiz", student=student,
                               quiz=quiz, quiz_id=quiz_id, difficulty=difficulty)

    if step == "result":
        student = session.get("student")
        active = session.get("active_quiz")
        if not student or not active or request.form.get("quiz_id") != active["id"]:
            flash("Your quiz session expired. Please start again.", "error")
            return redirect(url_for("home"))
        score = 0
        wrong = []
        for i, question in enumerate(active["questions"]):
            user_answer = request.form.get(f"q{i}", "")
            if user_answer == question["answer"]:
                score += 1
            else:
                wrong.append({"question": question["question"],
                              "your_answer": user_answer or "Not answered",
                              "correct_answer": question["answer"]})
        total = len(active["questions"])
        if score == total:
            feedback = "Excellent! You answered every question correctly."
        elif score >= total / 2:
            feedback = "Good effort! Review the areas below and practise again."
        else:
            feedback = "Keep practising. Revisit the concept and focus on the corrections below."
        result = {"name": student["name"], "class_no": student["class_no"],
                  "subject": student["subject"], "topic": student["topic"],
                  "difficulty": active["difficulty"], "score": score, "total": total,
                  "feedback": feedback, "wrong_questions": wrong}
        session["last_result"] = result
        session.pop("active_quiz", None)
        return render_template("index.html", step="result", result=result,
                               chart_url=url_for("chart"))

    flash("Please start from the welcome page.", "error")
    return redirect(url_for("home"))


@app.route("/chart")
def chart():
    result = session.get("last_result")
    if not result:
        abort(404)
    chart_file = make_chart(result["score"], result["total"])
    return send_file(chart_file, mimetype="image/png")


@app.route("/download")
def download():
    result = session.get("last_result")
    if not result:
        abort(404)
    pdf = create_pdf(result)
    safe_name = "".join(c for c in result["name"] if c.isalnum() or c in "-_")[:40] or "student"
    return send_file(pdf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"AI_Study_Pal_{safe_name}_report.pdf")


@app.route("/health")
def health():
    return {"status": "ok", "dataset_rows": int(len(df))}


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
