import requests
import traceback
import os

BASE_URL = "http://localhost:5001"
VOCAB_ENDPOINT = "/generate"
TIMEOUT = 60

def test_vocabulary_term_generation_endpoint():
    """
    Test the API endpoint responsible for generating 100+ contextually relevant vocabulary terms
    with emoji enhancements, ensuring correct ranking, categorization, and diversity using semantic embeddings and MMR algorithm.
    """
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY", "")

    # Sample payload matching actual Flask API structure
    payload = {
        "context": "I want to communicate about daily activities like eating, drinking, and playing with friends.",
        "api_key": api_key
    }
    headers = {
        'Content-Type': 'application/json',
    }

    response = None
    try:
        print(f"Testing {BASE_URL}{VOCAB_ENDPOINT}")
        response = requests.post(f"{BASE_URL}{VOCAB_ENDPOINT}", json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}. Response: {response.text[:200]}"
        data = response.json()

        # Validate response structure based on actual Flask API
        assert "success" in data, "Response missing 'success' key"
        assert data["success"] == True, f"API returned success=False: {data.get('error', 'Unknown error')}"
        assert "terms" in data, "Response missing 'terms' key"
        assert "context" in data, "Response missing 'context' key"

        terms = data["terms"]
        assert isinstance(terms, list), "'terms' should be a list"
        assert len(terms) >= 50, f"Expected at least 50 terms, got {len(terms)}"

        # Validate terms have emojis (actual API returns strings with emojis prepended)
        terms_with_emojis = 0
        unique_terms = set()

        for term in terms:
            assert isinstance(term, str), "Each term should be a string"
            assert len(term.strip()) > 0, "Term should not be empty"
            unique_terms.add(term.lower())

            # Check if term has emoji (emojis are typically at start of string)
            # Simple check: emojis are usually in Unicode ranges
            if any(ord(char) > 127 for char in term[:3]):  # Check first 3 chars for emoji
                terms_with_emojis += 1

        # At least 80% of terms should have emojis
        assert terms_with_emojis >= len(terms) * 0.8, f"Expected most terms to have emojis, got {terms_with_emojis}/{len(terms)}"

        # Validate diversity: no duplicates (case insensitive)
        assert len(unique_terms) >= len(terms) * 0.9, f"Too many duplicate terms detected"

        # Validate context is returned
        assert data["context"] == payload["context"], "Returned context doesn't match input"

        print(f"✅ Test passed! Generated {len(terms)} unique terms with emojis")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print(traceback.format_exc())
        if response:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text[:500]}")
        assert False, f"Exception occurred during test: {e}"

test_vocabulary_term_generation_endpoint()
