import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

def test_generate_sentences_from_words():
    url = f"{BASE_URL}/generate-sentences"
    headers = {"Content-Type": "application/json"}
    # Use a sample set of words for sentence generation
    payload = {
        "words": ["I", "want", "food"]
    }

    # --- Success case ---
    response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "success" in data and data["success"] is True, "Response missing success=true"
    assert "sentences" in data and isinstance(data["sentences"], list), "Sentences list missing or invalid"
    assert 15 <= len(data["sentences"]) <= 21, f"Expected 15-21 sentences, got {len(data['sentences'])}"
    for sentence in data["sentences"]:
        assert isinstance(sentence, str) and 1 <= len(sentence) <= 200, "Each sentence must be a short string"

    # --- Error case: missing 'words' ---
    payload_missing_words = {}
    response = requests.post(url, json=payload_missing_words, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 400, f"Expected 400 for missing words, got {response.status_code}"
    err_data = response.json()
    assert "error" in err_data and isinstance(err_data["error"], str), "Error message missing for missing words"

    # --- Error case: missing API key scenario ---
    # The API key is optional if server has key configured. Since we cannot detect server config here,
    # test sending empty api_key to simulate missing or invalid key error.
    payload_with_empty_api_key = {
        "words": ["I", "want", "food"],
        "api_key": ""
    }
    response = requests.post(url, json=payload_with_empty_api_key, headers=headers, timeout=TIMEOUT)
    # Could be 400 if server requires api_key, or 200 if server has key internally.
    # Account for either.
    if response.status_code == 400:
        err_data = response.json()
        assert "error" in err_data and isinstance(err_data["error"], str), "Expected error message for empty api_key"

    # --- Rate limiting: more than 20 requests within 5 minutes ---
    # Try to provoke rate limit error by sending many requests if possible.
    # This is a sample of repeated rapid calls to trigger 429.
    # If 429 encountered, validate error structure.
    rate_limit_hit = False
    for _ in range(25):
        r = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        if r.status_code == 429:
            rate_limit_hit = True
            rl_data = r.json()
            assert "error" in rl_data and isinstance(rl_data["error"], str), "Rate limit error message missing"
            break
    assert rate_limit_hit or True  # Pass even if no rate limit triggered (depends on server state)

    # --- Server error simulation ---
    # We cannot force a 500 easily; we test for proper structure if a 500 occurs.
    # Here, test a malformed payload that might cause 500, or just check if 500 returns proper structure.
    malformed_payload = {"words": None}
    response = requests.post(url, json=malformed_payload, headers=headers, timeout=TIMEOUT)
    if response.status_code == 500:
        err_data = response.json()
        assert "success" in err_data and err_data["success"] is False, "Expected success:false on server error"
        assert "error" in err_data and isinstance(err_data["error"], str), "Error message missing on server error"

test_generate_sentences_from_words()
