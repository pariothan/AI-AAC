# Infinite Craft-Style Context Wordlist Generator

A beautiful web UI inspired by Infinite Craft that generates contextual wordlists using AI.

## Setup

All dependencies are already installed in the `myenv` conda environment!

**To run the app:**
```bash
./run_app.sh
```

Or manually activate the conda environment:
```bash
conda activate myenv
python app.py
```

**Open your browser:**
Navigate to http://localhost:5000

> Note: API keys are already configured in the code

## Usage

1. Enter any context in the input field (e.g., "software development team meeting", "cooking in a professional kitchen", "underwater marine biology")
2. Click "Generate Words"
3. Wait a moment while AI generates ~100 relevant vocabulary terms
4. Terms appear as draggable cards in the Infinite Craft style
5. Use the search box to filter terms
6. Click the download button to export the wordlist as a text file
7. Click the trash icon to clear all terms

## Features

- 🎨 **Infinite Craft-style UI** with animated particle background
- 📝 **Context-based generation** using Claude and OpenAI embeddings
- 🔍 **Real-time search** to filter displayed terms
- 📥 **Export functionality** to download wordlists
- 🎯 **Draggable cards** for visual organization
- ⚡ **Fast and efficient** vocabulary generation

## How It Works

The app uses:
- **Claude (Sonnet 4.5)** to generate candidate terms
- **OpenAI embeddings** for semantic similarity
- **spaCy** for linguistic analysis
- **MMR algorithm** for diversity
- **Category-based quotas** for balanced results
