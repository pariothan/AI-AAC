import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from src.rank_terms import generate_terms
import base64
from PIL import Image
import io
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
from typing import Tuple
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Support mounting the app behind a reverse proxy on a subpath (e.g., /aac-demo)
raw_base_path = os.environ.get("APP_BASE_PATH", "").strip()
if raw_base_path in {"", "/"}:
    BASE_PATH = ""
else:
    BASE_PATH = "/" + raw_base_path.strip("/")

# Rate limiting: Track requests per API key hash
rate_limit_store = defaultdict(list)
RATE_LIMIT_REQUESTS = 20  # Max requests per window
RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds

def get_openai_client(api_key: str):
    """Create OpenAI client with provided API key"""
    if not api_key:
        raise ValueError("API key is required")
    return OpenAI(api_key=api_key)

def check_rate_limit(api_key: str) -> Tuple[bool, str]:
    """
    Check if request is within rate limits.
    Returns (is_allowed, error_message)
    """
    # Hash the API key for privacy (don't store actual keys)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]

    now = datetime.now()
    cutoff_time = now - timedelta(seconds=RATE_LIMIT_WINDOW)

    # Clean old requests
    rate_limit_store[key_hash] = [
        req_time for req_time in rate_limit_store[key_hash]
        if req_time > cutoff_time
    ]

    # Check if limit exceeded
    if len(rate_limit_store[key_hash]) >= RATE_LIMIT_REQUESTS:
        wait_time = int((rate_limit_store[key_hash][0] - cutoff_time).total_seconds())
        return False, f"Rate limit exceeded. Please wait {wait_time} seconds."

    # Add current request
    rate_limit_store[key_hash].append(now)
    return True, ""

@app.route('/')
def index():
    return render_template('index.html', base_path=BASE_PATH)

def add_emojis_to_terms(terms, openai_client):
    """
    Add emojis to a list of terms using a single API call.
    Returns a list of terms with emojis prepended.
    """
    # Format terms as a comma-separated list
    terms_str = ", ".join(terms)

    prompt = f"""For each of these words/phrases, add a single relevant emoji that best represents it.

Words: {terms_str}

Return ONLY a comma-separated list with each word prefixed by its emoji and a space.
Format: "emoji word, emoji word, emoji word"

Example input: "run, think, water"
Example output: "🏃 run, 💭 think, 💧 water"

Be concise. Use the most appropriate single emoji for each term. Output the list on one line."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.choices[0].message.content.strip()

        # Parse the response - split by comma and clean up
        emoji_terms = [term.strip() for term in response_text.split(',')]

        # Fallback: if parsing fails, return terms with default emoji
        if len(emoji_terms) != len(terms):
            return [f"✨ {term}" for term in terms]

        return emoji_terms

    except Exception as e:
        print(f"Error adding emojis: {e}")
        # Fallback: return terms with default emoji
        return [f"✨ {term}" for term in terms]

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        context = data.get('context', '')
        api_key = data.get('api_key', '')

        if not context:
            return jsonify({'error': 'Context is required'}), 400

        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        # Check rate limit
        is_allowed, error_msg = check_rate_limit(api_key)
        if not is_allowed:
            return jsonify({'error': error_msg}), 429

        # Create client with user's API key
        openai_client = get_openai_client(api_key)

        # Generate terms using the rank_terms module
        result = generate_terms(
            context,
            n=100,
            openai_client=openai_client
        )

        # Extract just the terms
        terms = [item['term'] for item in result['terms']]

        # Add emojis with a single API call
        print("Adding emojis to terms...")
        emoji_terms = add_emojis_to_terms(terms, openai_client)

        return jsonify({
            'success': True,
            'terms': emoji_terms,
            'context': context
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/generate-sentences', methods=['POST'])
def generate_sentences():
    try:
        data = request.json
        words = data.get('words', [])
        api_key = data.get('api_key', '')

        if not words:
            return jsonify({'error': 'Words are required'}), 400

        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        # Check rate limit
        is_allowed, error_msg = check_rate_limit(api_key)
        if not is_allowed:
            return jsonify({'error': error_msg}), 429

        # Create client with user's API key
        openai_client = get_openai_client(api_key)

        # Remove emojis from words for cleaner sentence generation
        clean_words = [word.split(' ', 1)[-1] if ' ' in word else word for word in words]
        words_str = ", ".join(clean_words)

        prompt = f"""Create 15-20 different short, simple sentences using ONLY these words IN THIS EXACT ORDER: {words_str}

CRITICAL RULES:
- Use ONLY the words provided - DO NOT add any other content words
- You may ONLY add function words (the, a, an, is, are, was, were, to, at, in, on, etc.)
- You may conjugate verbs as necessary (add -s, -ed, -ing)
- You may add plural markers (-s, -es)
- Keep the exact order of the content words given
- Make the sentences grammatically correct
- Be natural and simple
- Vary the sentence structures and function words used
- Show different ways to express the same idea with the given words

Return ONLY the sentences, one per line. No numbering, no extra text."""

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.choices[0].message.content.strip()
        sentences = [s.strip() for s in response_text.split('\n') if s.strip()]

        return jsonify({
            'success': True,
            'sentences': sentences
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        api_key = request.form.get('api_key', '')
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        # Check rate limit
        is_allowed, error_msg = check_rate_limit(api_key)
        if not is_allowed:
            return jsonify({'error': error_msg}), 400

        # Create client with user's API key
        openai_client = get_openai_client(api_key)

        # Read and process the image
        image_bytes = file.read()

        # Resize if needed (max 5MB, max dimension 1568px)
        image = Image.open(io.BytesIO(image_bytes))

        # Convert RGBA to RGB if needed
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize if too large
        max_dimension = 1568
        if max(image.size) > max_dimension:
            ratio = max_dimension / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Convert back to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr.seek(0)
        image_bytes = img_byte_arr.read()

        # Encode to base64
        image_base64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        # Generate description using OpenAI's vision
        prompt = """Describe this image in a way that would help generate vocabulary words for someone learning to communicate.
Focus on:
- Main objects and subjects
- Actions taking place
- Setting and environment
- Important details
- Overall context

Provide a clear, concise description (2-3 sentences)."""

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        description = response.choices[0].message.content.strip()

        return jsonify({
            'success': True,
            'description': description
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port)
