from flask import Flask, render_template, request, jsonify
from pathlib import Path
import PyPDF2
import docx
import re
import os
import language_tool_python

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

# Initialize LanguageTool
tool = language_tool_python.LanguageTool('en-US')


def analyze_resume(text):
    suggestions = []

    # Basic analysis rules
    word_count = len(text.split())
    if word_count < 200:
        suggestions.append("Your resume is quite short. Aim for at least 200 words.")

    if not re.search(r'\b\d{4}\b', text):  # Checking if there are any dates
        suggestions.append("Include dates for your education and experience.")

    skills = ['python', 'java', 'javascript', 'react', 'sql', 'aws', 'docker', 'machine learning', 'data science',
              'html', 'css']
    found_skills = [skill for skill in skills if skill.lower() in text.lower()]
    if len(found_skills) < 3:
        suggestions.append("Consider adding more technical skills that are relevant to your field.")

    sections = ['education', 'experience', 'skills', 'projects', 'certifications', 'achievements', 'languages']
    missing = [s for s in sections if s.lower() not in text.lower()]
    if missing:
        suggestions.append(f"Add these missing sections: {', '.join(missing)}.")

    # Look for specific section content (e.g., project descriptions, quantifiable achievements)
    if 'projects' in text.lower() and len(
            [word for word in text.split() if word.lower() in ['project', 'worked', 'led']]) < 10:
        suggestions.append(
            "Add more details to your projects section. Employers love seeing quantifiable achievements.")

    # Suggest action for typos or grammatical issues (very basic rule)
    if len(re.findall(r'\bthe\b', text)) > 15:  # Random check for repetitive words
        suggestions.append("Be cautious of repetitive words like 'the'. Try to avoid unnecessary repetition.")

    # Check for grammar errors
    grammar_errors = check_grammar(text)
    if grammar_errors:
        suggestions.append("Grammar issues found:\n" + "\n".join(grammar_errors))

    return "\n".join(
        suggestions) if suggestions else "Your resume looks good! But consider adding more quantifiable achievements."


def check_grammar(text):
    """Check for grammar issues using LanguageTool and return the issues with line numbers"""
    matches = tool.check(text)
    errors = []

    for match in matches:
        error_msg = f"Line {match.context.splitlines().index(match.context)}: {match.message}"
        errors.append(error_msg)

    return errors


def extract_text(filepath):
    """Extracts text from a given file (pdf, docx, txt)"""
    filepath_str = str(filepath)
    text = ''

    if filepath_str.endswith('.pdf'):
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ' '.join([page.extract_text() for page in reader.pages if page.extract_text()])

    elif filepath_str.endswith('.docx'):
        doc = docx.Document(filepath)
        text = ' '.join([para.text for para in doc.paragraphs])

    elif filepath_str.endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8') as file:
            text = file.read()

    # Basic validation to ensure text extraction was successful
    if not text.strip():
        raise ValueError("No text found in the file. Please check the file format or content.")

    return text


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/enhance', methods=['POST'])
def enhance():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['resume']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    filepath = Path(app.config['UPLOAD_FOLDER']) / file.filename
    try:
        file.save(filepath)

        # Extract text from the uploaded file
        text = extract_text(filepath)

        # Analyze the resume and get suggestions
        suggestions = analyze_resume(text)

        return jsonify({"suggestions": suggestions})

    except ValueError as ve:
        # Handle specific errors (e.g., empty or non-readable file)
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        # Generic error handler
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        # Clean up by deleting the uploaded file after processing
        if filepath.exists():
            os.remove(filepath)


if __name__ == '__main__':
    app.run(debug=True)
