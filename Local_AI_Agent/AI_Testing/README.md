# Flask Calculator App

A modern, responsive, and secure Web Calculator application built with Flask.

## Features

- **Standard & Scientific Operations:**
  - Basic arithmetic: addition, subtraction, multiplication, division, modulo.
  - Scientific functions: power (`xʸ`), square root (`√`), trigonometric functions (`sin`, `cos`, `tan`), logarithms (`log10`, natural log `ln`), factorial (`n!`), and constants ($\pi$, $e$).
- **Safe Expression Evaluator:**
  - Uses Python's Abstract Syntax Tree (`ast`) to safely parse and evaluate expressions without dangerous `eval()` calls.
  - Protection against syntax exploits, code execution, division-by-zero, and exponent overflow attacks.
- **Calculation History:**
  - Calculation history drawer with the ability to review past results.
  - Click on any previous result to quickly load it back into the display.
  - History clear button.
- **Full Keyboard Support:**
  - Type numbers `0`-`9`, operators (`+`, `-`, `*`, `/`, `%`, `^`), parentheses, `Enter` or `=` to calculate, `Backspace` to delete, and `Esc` to clear.
- **Modern Dark UI:**
  - Clean glassmorphism styling, responsive layout for desktop and mobile screens.

## Project Structure

```text
├── app.py                 # Flask server and safe AST-based calculation engine
├── requirements.txt       # Dependencies (including Flask)
├── templates/
│   └── index.html         # Frontend interface
└── static/
    ├── css/
    │   └── style.css      # Modern dark-mode styling
    └── js/
        └── script.js      # Interactive keypad, API calls, and keyboard bindings
```

## Getting Started

### 1. Set Up Environment & Install Dependencies

Ensure Python 3.10+ is installed:

```bash
# If using a virtual environment:
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements:
pip install -r requirements.txt
```

### 2. Run the Application

```bash
cd AI_Testing
python app.py
```

### 3. Open in Browser

Open your browser and navigate to:
```
http://127.0.0.1:5000
```
