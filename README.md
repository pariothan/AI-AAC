# Image Description Generator

A FastAPI web application that generates detailed descriptions of images using Claude's vision capabilities.


Slides link: https://docs.google.com/presentation/d/1YGiIkGLCvR31djQOlJv5BNP7Qfjj2e1R3gXzgQje9W4/edit?usp=sharing

Github Profile: https://github.com/meetapandit/Oct-4-Hackathon-2025-
## Features

- 🖼️ **Image Upload UI**: Drag-and-drop or browse to upload images
- 🔄 **HEIC Support**: Automatically converts HEIC images to JPEG
- 📏 **Smart Resizing**: Automatically optimizes large images (max 5MB, 1568px)
- 🎨 **Multiple Formats**: Supports JPEG, PNG, WebP, GIF, and HEIC
- 🤖 **AI-Powered**: Uses Claude Sonnet 4.5 for detailed image descriptions
- ⚡ **Real-time Processing**: Fast image analysis with loading indicators

## Project Structure

```
Oct-4-Hackathon-2025-/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── img_generator.py     # Main FastAPI application
│   ├── vocab_generator.py   # Vocabulary generation utilities
│   ├── text_to_speek.py     # Text-to-speech functionality
│   └── .env                 # Environment variables
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the `src/` directory:

```env
ANTHROPIC_API_KEY=your_api_key_here
IMG_GENERATOR_ANTHRPIC_API_KEY=your_api_key_here
```

### 4. Run the Application

```bash
python src/img_generator.py
```

The application will be available at `http://localhost:8000`

## Usage

1. Open your browser and navigate to `http://localhost:8000`
2. Upload an image by:
   - Dragging and dropping it into the upload area
   - Clicking "Browse Files" to select an image
3. Click "Analyze Image" to generate a description
4. View the AI-generated description below

## API Endpoints

### `GET /`
Returns the web UI for image upload

### `POST /describe-image`
Upload an image and receive a detailed description

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (image file)

**Response:**
```json
{
  "success": true,
  "filename": "example.jpg",
  "description": "Detailed image description...",
  "model": "claude-sonnet-4-5-20250929"
}
```

## Supported Image Formats

- JPEG/JPG
- PNG
- WebP
- GIF
- HEIC (automatically converted to JPEG)

## Image Processing Features

- **Automatic HEIC Conversion**: HEIC images are converted to JPEG for API compatibility
- **Smart Resizing**: Images larger than 5MB or exceeding 1568px in any dimension are automatically resized
- **Quality Optimization**: Uses LANCZOS resampling and compression for optimal quality/size balance

## Technologies Used

- **FastAPI**: Web framework
- **Anthropic Claude API**: AI image description
- **Pillow**: Image processing
- **pillow-heif**: HEIC format support

## License

MIT License
