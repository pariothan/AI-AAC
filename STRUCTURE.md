# Project Structure

## Overview
The codebase has been reorganized with supporting Python modules in the `src/` directory while keeping the main entry point at the root level.

## Directory Structure

```
Oct-4-Hackathon-2025-/
│
├── app.py                   # Main Flask application (entry point)
├── requirements.txt         # Python dependencies
├── run_app.sh              # Shell script to run the app
│
├── src/                    # Source code modules
│   ├── __init__.py         # Package initialization
│   ├── rank_terms.py       # Term ranking and vocabulary generation
│   ├── img_generator.py    # Image description utilities
│   ├── vocab_generator.py  # Vocabulary generation utilities
│
├── templates/              # Flask HTML templates
│   └── index.html          # Main web interface
│
├── README.md               # Main documentation
├── SECURITY.md             # Security documentation
├── README_WEB_UI.md        # Web UI documentation
└── .env                    # Environment variables (optional)
```

## File Purposes

### Root Level Files

**app.py**
- Main Flask application
- Defines all API routes
- Handles rate limiting
- Manages API key validation
- Entry point: `python app.py`

**requirements.txt**
- Python package dependencies
- Install with: `pip install -r requirements.txt`

**run_app.sh**
- Convenience script to start the application
- Makes it easy to run with one command

### src/ Directory

**src/rank_terms.py**
- Core vocabulary generation logic
- Uses OpenAI embeddings and GPT-4
- Implements term ranking algorithms
- Handles semantic similarity calculations
- Categorizes terms (pronouns, verbs, nouns, etc.)

**src/img_generator.py**
- Image analysis utilities
- FastAPI-based image description service
- Handles image format conversions

**src/vocab_generator.py**
- Vocabulary generation utilities
- Helper functions for word processing

**src/__init__.py**
- Package initialization
- Makes src/ a proper Python package

### templates/ Directory

**templates/index.html**
- Complete web interface
- Includes all HTML, CSS, and JavaScript
- Drag-and-drop word interface
- API key management modal
- Responsive design

### Documentation Files

**README.md**
- Main project documentation
- Setup instructions
- Usage guide
- API documentation

**SECURITY.md**
- Security features documentation
- Rate limiting details
- Best practices
- Deployment checklist

**README_WEB_UI.md**
- Web UI specific documentation
- Frontend features

## Import Changes

### Before Restructuring
```python
from rank_terms import generate_terms
```

### After Restructuring
```python
from src.rank_terms import generate_terms
```

## Running the Application

### Development
```bash
python app.py
```

### With Environment Variables
```bash
export FLASK_ENV=development
python app.py
```

### Using the Shell Script
```bash
./run_app.sh
```

## Benefits of This Structure

1. **Clean Separation**: Main entry point separate from supporting modules
2. **Easy to Navigate**: Related code grouped in `src/`
3. **Standard Python Layout**: Follows common Python project patterns
4. **Scalable**: Easy to add new modules to `src/`
5. **Clear Entry Point**: `app.py` at root makes it obvious how to start

## Import Guidelines

When adding new modules to `src/`:
- Import using: `from src.module_name import function_name`
- All modules in `src/` can import each other using: `from src.other_module import ...`
- External packages import normally: `from flask import Flask`

## Adding New Files

### New Python Module
1. Create file in `src/` directory
2. Import in `app.py` using `from src.your_module import ...`
3. Update this documentation

### New Template
1. Create file in `templates/` directory
2. Reference in Flask routes: `render_template('your_template.html')`

### New Static Files
1. Create `static/` directory at root if needed
2. Configure Flask: `app = Flask(__name__, static_folder='static')`
3. Access at `/static/filename`

## Testing

The application has been tested and works correctly with the new structure:
- ✅ Flask server starts successfully
- ✅ Web interface loads properly
- ✅ All imports resolve correctly
- ✅ Templates render correctly
