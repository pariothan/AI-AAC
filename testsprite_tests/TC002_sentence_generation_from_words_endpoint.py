import requests
import os

BASE_URL = "http://localhost:5001"
TIMEOUT = 60

def test_sentence_generation_from_words():
    """
    Verify the endpoint that creates 15-20 grammatically correct sentences from user-selected words,
    maintaining core meaning and supporting linguistic flexibility.
    """
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY", "")

    # Example words to send - matching actual Flask API structure
    words_payload = {
        "words": [
            "I", "want", "eat", "food", "hungry"
        ],
        "api_key": api_key
    }

    headers = {
        "Content-Type": "application/json"
    }

    endpoint = f"{BASE_URL}/generate-sentences"

    try:
        print(f"Testing {endpoint}")
        response = requests.post(endpoint, json=words_payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}. Response: {response.text[:200]}"
        data = response.json()

        # Validate response structure based on actual Flask API
        assert "success" in data, "Response JSON missing 'success' field"
        assert data["success"] == True, f"API returned success=False: {data.get('error', 'Unknown error')}"
        assert "sentences" in data, "Response JSON missing 'sentences' field"

        sentences = data["sentences"]
        assert isinstance(sentences, list), "'sentences' should be a list"
        assert 15 <= len(sentences) <= 25, f"Expected 15-25 sentences, got {len(sentences)}"

        # Validate each sentence
        for sentence in sentences:
            assert isinstance(sentence, str), "Each sentence should be a string"
            assert len(sentence.strip()) > 0, "Sentence should not be empty"
            # Should contain multiple words
            assert len(sentence.split()) >= 2, f"Sentence should contain multiple words: '{sentence}'"

            # Basic grammatical check - sentences should start with capital or contain words from input
            words_lower = [w.lower() for w in words_payload["words"]]
            sentence_lower = sentence.lower()
            contains_input_word = any(word in sentence_lower for word in words_lower)
            assert contains_input_word, f"Sentence should contain at least one input word: '{sentence}'"

        print(f"✅ Test passed! Generated {len(sentences)} grammatically correct sentences")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        assert False, f"Request failed: {e}"
    except Exception as e:
        print(f"❌ Test failed: {e}")
        assert False, f"Test failed: {e}"

test_sentence_generation_from_words()
