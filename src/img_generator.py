from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
import anthropic
import os
from dotenv import load_dotenv
import base64
from typing import Dict
from PIL import Image
import pillow_heif
from io import BytesIO

# Load environment variables from the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

app = FastAPI()

def get_image_description(image_bytes: bytes, mime_type: str) -> Dict[str, str]:
    """
    Generate a detailed description of an image using Claude's vision capabilities.

    Args:
        image_bytes: The image file as bytes
        mime_type: The MIME type of the image (e.g., 'image/jpeg', 'image/png')

    Returns:
        A dictionary containing the image description and details
    """
    # Get API key - try IMG_GENERATOR specific key first, then fall back to general key
    api_key = os.getenv("IMG_GENERATOR_ANTHRPIC_API_KEY")

    if not api_key:
        raise ValueError("No API key found. Please set ANTHROPIC_API_KEY or IMG_GENERATOR_ANTHRPIC_API_KEY in .env file")

    # Initialize the Anthropic client
    client = anthropic.Anthropic(api_key=api_key)

    # Encode image to base64
    image_base64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    # Create the prompt for Claude
    prompt = """Please provide a comprehensive description of this image. Include:

1. Overall Description: What the image shows at a high level
2. Key Elements: Main objects, people, or subjects in the image
3. Details: Colors, composition, setting, and any notable features
4. Context: What the image appears to be about or its purpose
5. Mood/Atmosphere: The feeling or tone conveyed by the image

Be specific and descriptive."""

    # Call the Claude API with vision
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ],
    )

    # Extract the response
    description = message.content[0].text

    return {
        "description": description,
        "model": "claude-sonnet-4-5-20250929"
    }


def resize_image_if_needed(image_bytes: bytes, mime_type: str, max_size_mb: float = 5.0, max_dimension: int = 1568) -> tuple[bytes, str]:
    """
    Resize image if it's too large in file size or dimensions.
    Claude API has limits: max 5MB per image, recommended max dimension 1568px.

    Args:
        image_bytes: The image as bytes
        mime_type: The MIME type of the image
        max_size_mb: Maximum file size in MB (default 5.0)
        max_dimension: Maximum width or height in pixels (default 1568)

    Returns:
        Tuple of (resized_bytes, mime_type)
    """
    # Check file size
    size_mb = len(image_bytes) / (1024 * 1024)

    # Open the image
    img = Image.open(BytesIO(image_bytes))

    # Get current dimensions
    width, height = img.size
    needs_resize = False

    # Check if dimensions are too large
    if width > max_dimension or height > max_dimension:
        needs_resize = True
        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))
    elif size_mb > max_size_mb:
        # If file is too large but dimensions are ok, reduce dimensions by 20%
        needs_resize = True
        new_width = int(width * 0.8)
        new_height = int(height * 0.8)

    if needs_resize:
        # Resize the image
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Convert to RGB if necessary
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')

    # Determine output format and quality
    output_format = 'JPEG'
    if mime_type == 'image/png':
        output_format = 'PNG'
    elif mime_type == 'image/webp':
        output_format = 'WEBP'
    elif mime_type == 'image/gif':
        output_format = 'GIF'
    else:
        # Default to JPEG for all other formats
        output_format = 'JPEG'
        mime_type = 'image/jpeg'

    # Save with compression
    output = BytesIO()
    if output_format == 'JPEG':
        img.save(output, format=output_format, quality=85, optimize=True)
    elif output_format == 'PNG':
        img.save(output, format=output_format, optimize=True)
    elif output_format == 'WEBP':
        img.save(output, format=output_format, quality=85)
    else:
        img.save(output, format=output_format)

    output.seek(0)
    return output.read(), mime_type


def convert_heic_to_jpeg(image_bytes: bytes) -> tuple[bytes, str]:
    """
    Convert HEIC image to JPEG format.

    Args:
        image_bytes: The HEIC image as bytes

    Returns:
        Tuple of (converted_bytes, mime_type)
    """
    # Open the HEIC image
    img = Image.open(BytesIO(image_bytes))

    # Convert to RGB if necessary (HEIC might be in different color mode)
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')

    # Save as JPEG
    output = BytesIO()
    img.save(output, format='JPEG', quality=85, optimize=True)
    output.seek(0)

    return output.read(), "image/jpeg"


@app.post("/describe-image")
async def describe_image(file: UploadFile = File(...)):
    """
    Endpoint to upload an image and receive a detailed description.

    Args:
        file: The uploaded image file

    Returns:
        JSON response with image description and details
    """
    # All supported formats including HEIC
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif", "image/heic", "image/heif"]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: JPEG, PNG, WebP, GIF, HEIC"
        )

    try:
        # Read the image file
        image_bytes = await file.read()
        mime_type = file.content_type

        # Convert HEIC to JPEG if needed
        if mime_type in ["image/heic", "image/heif"]:
            image_bytes, mime_type = convert_heic_to_jpeg(image_bytes)

        # Resize image if it's too large (max 5MB, max dimension 1568px)
        image_bytes, mime_type = resize_image_if_needed(image_bytes, mime_type)

        # Generate description
        result = get_image_description(image_bytes, mime_type)

        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "description": result["description"],
            "model": result["model"]
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.get("/")
async def root():
    """UI endpoint for image upload"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Image Description Generator</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 800px;
                width: 100%;
                padding: 40px;
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 10px;
                font-size: 2em;
            }
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
            }
            .upload-area {
                border: 3px dashed #667eea;
                border-radius: 15px;
                padding: 40px;
                text-align: center;
                background: #f8f9ff;
                transition: all 0.3s ease;
                cursor: pointer;
                margin-bottom: 20px;
            }
            .upload-area:hover {
                background: #f0f2ff;
                border-color: #764ba2;
            }
            .upload-area.dragover {
                background: #e8ebff;
                border-color: #764ba2;
            }
            .upload-icon {
                font-size: 3em;
                margin-bottom: 15px;
            }
            #fileInput {
                display: none;
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                font-size: 1em;
                cursor: pointer;
                transition: transform 0.2s;
                display: inline-block;
                margin-top: 10px;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            #preview {
                margin-top: 20px;
                text-align: center;
                display: none;
            }
            #previewImage {
                max-width: 100%;
                max-height: 300px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            }
            #result {
                margin-top: 20px;
                padding: 20px;
                background: #f8f9ff;
                border-radius: 10px;
                display: none;
            }
            #result h2 {
                color: #667eea;
                margin-bottom: 15px;
            }
            #description {
                color: #333;
                line-height: 1.6;
                white-space: pre-wrap;
            }
            .loading {
                display: none;
                text-align: center;
                margin-top: 20px;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🖼️ Image Description Generator</h1>
            <p class="subtitle">Upload an image to get a detailed AI-powered description</p>

            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <p style="font-size: 1.2em; color: #333; margin-bottom: 10px;">
                    <strong>Drop your image here</strong>
                </p>
                <p style="color: #666;">or</p>
                <button class="btn" onclick="document.getElementById('fileInput').click()">
                    Browse Files
                </button>
                <p style="margin-top: 15px; font-size: 0.9em; color: #999;">
                    Supported formats: JPEG, PNG, WebP, GIF, HEIC
                </p>
            </div>

            <input type="file" id="fileInput" accept="image/jpeg,image/jpg,image/png,image/webp,image/gif,image/heic,image/heif,.heic">

            <div id="preview">
                <img id="previewImage" alt="Preview" style="display: block; margin: 0 auto;">
                <button class="btn" id="analyzeBtn" onclick="analyzeImage()" style="margin-top: 20px;">
                    Analyze Image
                </button>
            </div>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p style="margin-top: 15px; color: #667eea;">Analyzing your image...</p>
            </div>

            <div id="result">
                <h2>📝 Description</h2>
                <div id="description"></div>
            </div>
        </div>

        <script>
            let selectedFile = null;

            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const preview = document.getElementById('preview');
            const previewImage = document.getElementById('previewImage');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            const analyzeBtn = document.getElementById('analyzeBtn');

            // Prevent default drag behaviors
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, preventDefaults, false);
            });

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            // Highlight drop area when item is dragged over it
            ['dragenter', 'dragover'].forEach(eventName => {
                uploadArea.addEventListener(eventName, () => {
                    uploadArea.classList.add('dragover');
                }, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, () => {
                    uploadArea.classList.remove('dragover');
                }, false);
            });

            // Handle dropped files
            uploadArea.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                handleFile(files[0]);
            }, false);

            // Handle file input change
            fileInput.addEventListener('change', (e) => {
                handleFile(e.target.files[0]);
            });

            function handleFile(file) {
                if (!file) return;

                selectedFile = file;

                // Show preview
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                    preview.style.display = 'block';
                    result.style.display = 'none';
                };
                reader.readAsDataURL(file);
            }

            async function analyzeImage() {
                if (!selectedFile) return;

                // Show loading
                loading.style.display = 'block';
                result.style.display = 'none';
                analyzeBtn.disabled = true;

                // Create form data
                const formData = new FormData();
                formData.append('file', selectedFile);

                try {
                    const response = await fetch('/describe-image', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    if (data.success) {
                        document.getElementById('description').textContent = data.description;
                        result.style.display = 'block';
                    } else {
                        alert('Error: ' + (data.detail || 'Failed to analyze image'));
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                } finally {
                    loading.style.display = 'none';
                    analyzeBtn.disabled = false;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
