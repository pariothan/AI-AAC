# AI-AAC

A Flask web application that helps generate contextual vocabulary words and sentences for AAC (Augmentative and Alternative Communication) users. Uses OpenAI's GPT-4 for intelligent vocabulary generation and image analysis.

## Team

Built at the Oct-4 Bellevue Hackathon 2025 by:
- **Samuel Lederer** - Linguist
- **[Elizabeth Weber](https://www.linkedin.com/in/liz-m-weber/)** - Bioengineer & Accessibility Specialist
- **[Meeta Pandit](https://www.linkedin.com/in/meetapandit/)** - Data Engineer


## Project Structure

```
Oct-4-Hackathon-2025-/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── rank_terms.py        # Term ranking and vocabulary generation
│   ├── img_generator.py     # Image description utilities
│   ├── vocab_generator.py   # Vocabulary generation utilities
├── templates/
│   └── index.html           # Main web interface
├── app.py                   # Flask application (main entry point)
├── requirements.txt         # Python dependencies
├── SECURITY.md             # Security documentation
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
python -m spacy download en_core_web_sm
```

### 3. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5001`

**Note**: Users provide their own OpenAI API key through the web interface. No `.env` file is needed for the web app.

## Usage

### First Time Setup
1. Open your browser and navigate to `http://localhost:5001`
2. Enter your OpenAI API key when prompted
   - Get one from [OpenAI Platform](https://platform.openai.com/api-keys)
   - Optionally check "Session only" for better security
3. Your key is stored locally in your browser only

### Generating Vocabulary
1. **From Text**: Enter a context (e.g., "going to the beach") and click "Generate Words"
2. **From Image**: Click 📷 to upload an image - vocabulary is auto-generated from the image description

### Building Sentences
1. Drag words from the Word Bank to the Workspace
2. Arrange them in order
3. Click "Create Sentences" to generate example sentences using your words

## API Endpoints

### `GET /`
Returns the main web interface

### `POST /generate`
Generate vocabulary words from text context

**Request:**
```json
{
  "context": "going to the beach",
  "api_key": "sk-..."
}
```

**Response:**
```json
{
  "success": true,
  "terms": ["🏖️ beach", "🌊 ocean", "☀️ sun", ...],
  "context": "going to the beach"
}
```

### `POST /generate-sentences`
Generate sentences using selected words

### `POST /analyze-image`
Analyze an image and generate vocabulary

## Security Features

✅ **HTTPS Warning**: Alerts users when not using secure connections
✅ **Rate Limiting**: 20 requests per 5 minutes per API key
✅ **Session Storage**: Option to clear keys when browser closes
✅ **API Key Hashing**: Server never stores actual API keys

See [SECURITY.md](SECURITY.md) for more details.

## Technologies Used

- **Flask**: Web framework
- **OpenAI GPT-4**: Vocabulary generation, image analysis, sentence generation
- **spaCy**: Natural language processing
- **scikit-learn**: Term ranking and clustering
- **Pillow**: Image processing

## Development

To run with auto-reload during development:

```bash
export FLASK_ENV=development
python app.py
```

## License

“Commons Clause” License Condition v1.0

The Software is provided to you by the Licensor under the License, as defined below, subject to the following condition.

Without limiting other conditions in the License, the grant of rights under the License will not include, and the License does not grant to you, the right to Sell the Software.

For purposes of the foregoing, “Sell” means practicing any or all of the rights granted to you under the License to provide to third parties, for a fee or other consideration (including without limitation fees for hosting or consulting/ support services related to the Software), a product or service whose value derives, entirely or substantially, from the functionality of the Software. Any license notice or attribution required by the License must also include this Commons Clause License Condition notice.


## Hosting Behind `/aac-demo`

- Set environment variables when starting the Flask process so it binds correctly in production: `HOST=0.0.0.0`, `PORT=<port>`, and `APP_BASE_PATH=/aac-demo` (omit the trailing slash). The app reads these values on startup.
- Reverse proxy `/aac-demo` from your main site to the Flask service. Example Nginx block:
  ```nginx
  location /aac-demo/ {
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_set_header X-Forwarded-Prefix /aac-demo;
      proxy_pass http://127.0.0.1:5001/;
  }
  ```
- Visitors still provide their own OpenAI API key on the landing modal; keys never transit your server. Inform users that they must supply a valid `sk-` key to enable AI features.
- If you terminate TLS at the proxy, leave Flask in production (non-debug) mode and rely on the built-in rate limiting. Consider persisting rate-limit state (Redis) if you horizontally scale.
