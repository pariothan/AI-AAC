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
RATE_LIMIT_ENABLED = False  # Disabled per request; set True to restore limiting

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
    if not RATE_LIMIT_ENABLED:
        return True, ""

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
            model="gpt-4o-mini",
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

@app.route('/api/check-server-key', methods=['GET'])
def check_server_key():
    """Check if server has an API key configured"""
    has_key = bool(os.environ.get('OPENAI_API_KEY', ''))
    return jsonify({'hasServerKey': has_key})

@app.route('/generate', methods=['POST'])
def generate():
    try:
        print("\n" + "="*80)
        print("📥 RECEIVED /generate REQUEST")
        print("="*80)

        data = request.json
        context = data.get('context', '')
        user_api_key = data.get('api_key', '')

        # Use server API key if available, otherwise fall back to user-provided key
        server_api_key = os.environ.get('OPENAI_API_KEY', '')
        api_key = server_api_key if server_api_key else user_api_key

        print(f"📝 Context: {context[:100]}{'...' if len(context) > 100 else ''}")
        if server_api_key:
            print(f"🔑 Using server API key")
        else:
            print(f"🔑 Using user-provided API key: {'*' * (len(api_key) - 4)}{api_key[-4:] if len(api_key) > 4 else '****'}")

        if not context:
            print("❌ ERROR: No context provided")
            return jsonify({'error': 'Context is required'}), 400

        if not api_key:
            print("❌ ERROR: No API key available")
            return jsonify({'error': 'API key is required. Please contact the administrator.'}), 400

        # Check rate limit (use a generic identifier for server key)
        rate_limit_key = 'SERVER_KEY' if server_api_key else api_key
        print("🔍 Checking rate limit...")
        is_allowed, error_msg = check_rate_limit(rate_limit_key)
        if not is_allowed:
            print(f"❌ Rate limit exceeded: {error_msg}")
            return jsonify({'error': error_msg}), 429
        print("✅ Rate limit check passed")

        # Create client with user's API key
        try:
            print("🔧 Initializing OpenAI client...")
            openai_client = get_openai_client(api_key)
            print("✅ OpenAI client created successfully")
        except Exception as e:
            print(f"❌ ERROR creating OpenAI client: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to initialize OpenAI client: {str(e)}'
            }), 500

        # Generate terms using the rank_terms module
        try:
            print("\n🚀 Starting term generation pipeline...")
            result = generate_terms(
                context,
                n=100,
                openai_client=openai_client
            )
            print("✅ Term generation pipeline completed successfully")
        except Exception as e:
            print(f"❌ ERROR in generate_terms: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Failed to generate terms: {str(e)}'
            }), 500

        # Extract just the terms
        print(f"\n📊 Extracting {len(result['terms'])} terms from result...")
        terms = [item['term'] for item in result['terms']]
        print(f"✅ Extracted terms successfully")

        # Add emojis with a single API call
        print("\n😊 Adding emojis to terms...")
        emoji_terms = add_emojis_to_terms(terms, openai_client)
        print(f"✅ Added emojis to {len(emoji_terms)} terms")

        print("\n" + "="*80)
        print("✅ /generate REQUEST COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")

        return jsonify({
            'success': True,
            'terms': emoji_terms,
            'context': context
        })

    except Exception as e:
        print(f"ERROR in /generate endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/generate-sentences', methods=['POST'])
def generate_sentences():
    try:
        data = request.json
        words = data.get('words', [])
        user_api_key = data.get('api_key', '')

        if not words:
            return jsonify({'error': 'Words are required'}), 400

        # Use server API key if available, otherwise fall back to user-provided key
        server_api_key = os.environ.get('OPENAI_API_KEY', '')
        api_key = server_api_key if server_api_key else user_api_key

        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        # Check rate limit (use a generic identifier for server key)
        rate_limit_key = 'SERVER_KEY' if server_api_key else api_key
        is_allowed, error_msg = check_rate_limit(rate_limit_key)
        if not is_allowed:
            return jsonify({'error': error_msg}), 429

        # Create client with API key
        openai_client = get_openai_client(api_key)

        # Remove emojis from words for cleaner sentence generation
        clean_words = [word.split(' ', 1)[-1] if ' ' in word else word for word in words]
        words_str = ", ".join(clean_words)

        prompt = f"""Create 15-20 different short, simple sentences using these words: {words_str}

CRITICAL RULES:
- Use the words provided - preserve the user's intended meaning
- KEEP THE CORE MESSAGE INTACT - the user chose these words to express something specific
- You may add function words (the, a, an, is, are, was, were, to, at, in, on, with, while, etc.)
- You may conjugate verbs as necessary (add -s, -ed, -ing)
- You may add plural markers (-s, -es)
- You may change pronoun case (I/me, he/him, she/her, they/them, etc.)
- You may CHANGE PARTS OF SPEECH to make sentences grammatical (noun→verb, adjective→adverb, etc.)
  * "bad" (adjective) → "badly" (adverb): "I bad want food" → "I badly want food"
  * "quick" (adjective) → "quickly" (adverb): "I quick run" → "I quickly run"
  * "happy" (adjective) → "happily" (adverb): "I happy dance" → "I happily dance"
  * "love" (noun) → "love" (verb): "I love food" (noun) → "I love food" (verb)
- You may add helping verbs for clarity (want→want to, need→need to)
- You may add derivational suffixes to change word forms (-ly, -ness, -tion, -er, etc.)
- Keep words in their original order when possible - only reorder for grammar/clarity
- Make the sentences grammatically correct and natural
- Be simple and clear
- Show different ways to express ideas while maintaining the core meaning

Examples showing part-of-speech flexibility:
- "I bad want food" → "I badly want food" / "I want food badly" / "I really want food"
- "I happy see friend" → "I happily see my friend" / "I'm happy to see my friend"
- "I quick need help" → "I quickly need help" / "I need help quickly" / "I urgently need help"
- "I feel bad" → "I feel bad" / "I feel badly" / "I'm feeling bad"

Return ONLY the sentences, one per line. No numbering, no extra text."""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
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

@app.route('/suggest-next-words', methods=['POST'])
def suggest_next_words():
    try:
        data = request.json
        words = data.get('words', [])
        user_api_key = data.get('api_key', '')

        # Use server API key if available, otherwise fall back to user-provided key
        server_api_key = os.environ.get('OPENAI_API_KEY', '')
        api_key = server_api_key if server_api_key else user_api_key

        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        # Check rate limit (use a generic identifier for server key)
        rate_limit_key = 'SERVER_KEY' if server_api_key else api_key
        is_allowed, error_msg = check_rate_limit(rate_limit_key)
        if not is_allowed:
            return jsonify({'error': error_msg}), 429

        # Create client with API key
        openai_client = get_openai_client(api_key)

        # If no words, return core vocabulary with emojis
        if not words:
            core_vocab = [
                "👤 I", "💝 want", "📍 need", "🤝 help", "✅ yes", "❌ no",
                "➕ more", "🚶 go", "⏹️ stop", "❤️ like", "💭 feel", "💪 can",
                "🙏 please", "💝 thank you", "👍 good", "👎 bad"
            ]
            return jsonify({
                'success': True,
                'suggestions': core_vocab
            })

        # Build prompt for next word prediction
        words_str = " ".join(words)
        prompt = f"""Given these AAC (Augmentative and Alternative Communication) words in sequence: "{words_str}"

Suggest 15 likely next words that would naturally continue this phrase for someone using AAC to communicate.

CRITICAL RULES:
- Focus on HIGH-FREQUENCY AAC vocabulary (basic verbs, nouns, function words)
- Consider natural grammar and conversational flow
- Prioritize words that help express needs, feelings, and actions
- Include a mix of: verbs, nouns, and adjectives, but do NOT use function words (to, a, the)
- Keep words SIMPLE and commonly used in everyday communication
- NO complex or technical words
- NO proper nouns

Return ONLY the 15 words as a comma-separated list, nothing else.

Example input: "I want"
Example output: drink, go, help, food, water, more, see, play, eat, sleep, see, break, you, my, some"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Faster and cheaper
            max_tokens=150,
            temperature=0.7,  # Some creativity but not too random
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.choices[0].message.content.strip()

        # Parse suggestions
        suggestions = [word.strip() for word in response_text.split(',') if word.strip()]

        # Limit to 15
        suggestions = suggestions[:15]

        # Add emojis to suggestions
        suggestions_with_emojis = add_emojis_to_terms(suggestions, openai_client)

        return jsonify({
            'success': True,
            'suggestions': suggestions_with_emojis
        })

    except Exception as e:
        print(f"ERROR in /suggest-next-words endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    try:
        print("\n" + "="*80)
        print("📷 RECEIVED /analyze-image REQUEST")
        print("="*80)

        if 'image' not in request.files:
            print("❌ ERROR: No image file in request")
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        print(f"📁 Received file: {file.filename}")
        print(f"📄 Content type: {file.content_type}")

        if file.filename == '':
            print("❌ ERROR: Empty filename")
            return jsonify({'error': 'No file selected'}), 400

        user_api_key = request.form.get('api_key', '')

        # Use server API key if available, otherwise fall back to user-provided key
        server_api_key = os.environ.get('OPENAI_API_KEY', '')
        api_key = server_api_key if server_api_key else user_api_key

        if not api_key:
            print("❌ ERROR: No API key available")
            return jsonify({'error': 'API key is required. Please contact the administrator.'}), 400

        if server_api_key:
            print(f"🔑 Using server API key")
        else:
            print(f"🔑 Using user-provided API key (length: {len(api_key)})")

        # Check rate limit (use a generic identifier for server key)
        rate_limit_key = 'SERVER_KEY' if server_api_key else api_key
        print("🔍 Checking rate limit...")
        is_allowed, error_msg = check_rate_limit(rate_limit_key)
        if not is_allowed:
            print(f"❌ Rate limit exceeded: {error_msg}")
            return jsonify({'error': error_msg}), 400
        print("✅ Rate limit OK")

        # Create client with user's API key
        print("🔧 Creating OpenAI client...")
        openai_client = get_openai_client(api_key)
        print("✅ OpenAI client created successfully")

        # Read and process the image
        print("\n📖 Reading image bytes...")
        image_bytes = file.read()
        print(f"✅ Image size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")

        # Resize if needed (max 5MB, max dimension 1568px)
        print("🖼️  Opening image with PIL...")
        image = Image.open(io.BytesIO(image_bytes))
        print(f"✅ Image opened: {image.size[0]}x{image.size[1]} pixels, mode: {image.mode}")

        # Convert RGBA to RGB if needed
        if image.mode in ('RGBA', 'LA', 'P'):
            print(f"🎨 Converting image from {image.mode} to RGB...")
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
            print("✅ Image converted to RGB")
        elif image.mode != 'RGB':
            print(f"🎨 Converting image from {image.mode} to RGB...")
            image = image.convert('RGB')
            print("✅ Image converted to RGB")

        # Resize if too large
        max_dimension = 1568
        if max(image.size) > max_dimension:
            print(f"📏 Image too large ({max(image.size)}px), resizing to {max_dimension}px...")
            ratio = max_dimension / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"✅ Image resized to {image.size[0]}x{image.size[1]}")
        else:
            print(f"✅ Image size OK, no resizing needed")

        # Convert back to bytes
        print("\n💾 Converting image to JPEG format...")
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr.seek(0)
        image_bytes = img_byte_arr.read()
        print(f"✅ JPEG size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")

        # Encode to base64
        print("🔐 Encoding image to base64...")
        image_base64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        print(f"✅ Base64 encoded (length: {len(image_base64):,} characters)")

        # Generate description using OpenAI's vision
        print("\n🤖 Calling OpenAI GPT-4o-mini vision API...")
        prompt = """Describe this image in a way that would help generate vocabulary words for someone learning to communicate.
Focus on:
- Main objects and subjects
- Actions taking place
- Setting and environment
- Important details
- Overall context

Provide a clear, concise description (2-3 sentences)."""

        print(f"⚙️  Using model: gpt-4o-mini")
        print(f"📤 Sending vision request...")
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
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
        print("✅ OpenAI vision API call successful")

        description = response.choices[0].message.content.strip()
        print(f"📝 Generated description ({len(description)} chars):")
        print(f"   \"{description}\"")

        print("\n" + "="*80)
        print("✅ /analyze-image REQUEST COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")

        return jsonify({
            'success': True,
            'description': description
        })

    except Exception as e:
        print(f"ERROR in /analyze-image endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port)
