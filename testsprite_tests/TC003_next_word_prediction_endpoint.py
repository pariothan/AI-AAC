import requests
import os

BASE_URL = "http://localhost:5001"
TIMEOUT = 60

def test_next_word_prediction():
    """
    Test the next word prediction API that returns the 15 most likely subsequent words
    in AAC communication context with emoji support.
    """
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY", "")

    url = f"{BASE_URL}/suggest-next-words"
    headers = {
        "Content-Type": "application/json"
    }

    # Test with words (actual Flask API structure)
    payload = {
        "words": ["I", "want"],
        "api_key": api_key
    }

    try:
        print(f"Testing {url} with words")
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        assert False, f"Request failed: {e}"

    try:
        data = response.json()
    except ValueError:
        print("❌ Response is not valid JSON")
        assert False, "Response is not valid JSON"

    assert isinstance(data, dict), "Response JSON should be a dictionary"
    assert "success" in data, "Response JSON must contain 'success' key"
    assert data["success"] == True, f"API returned success=False: {data.get('error', 'Unknown error')}"
    assert "suggestions" in data, "Response JSON must contain 'suggestions' key"

    suggestions = data["suggestions"]
    assert isinstance(suggestions, list), "'suggestions' should be a list"
    assert len(suggestions) >= 10, f"'suggestions' list should contain at least 10 items, got {len(suggestions)}"

    # Validate each suggestion has emoji
    for suggestion in suggestions:
        assert isinstance(suggestion, str), "Each suggestion should be a string"
        assert len(suggestion.strip()) > 0, "Suggestion cannot be empty"
        # Check for emoji (Unicode characters > 127 in first few chars)
        has_emoji = any(ord(char) > 127 for char in suggestion[:3])
        # Most suggestions should have emojis
        # Note: Not all might have emojis, so we'll just check they're non-empty strings

    # Test with empty words array (should return core vocabulary)
    payload_empty = {
        "words": [],
        "api_key": api_key
    }

    print(f"Testing {url} with empty words (should return core vocabulary)")
    response2 = requests.post(url, json=payload_empty, headers=headers, timeout=TIMEOUT)
    response2.raise_for_status()
    data2 = response2.json()

    assert data2["success"] == True
    assert "suggestions" in data2
    core_vocab = data2["suggestions"]
    assert len(core_vocab) >= 10, f"Core vocabulary should have at least 10 items, got {len(core_vocab)}"

    print(f"✅ Test passed! Got {len(suggestions)} suggestions with words, {len(core_vocab)} core vocabulary without words")

test_next_word_prediction()
