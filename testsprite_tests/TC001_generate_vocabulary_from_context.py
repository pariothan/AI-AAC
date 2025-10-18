import requests
import time

BASE_URL = "http://localhost:5001"
GENERATE_ENDPOINT = "/generate"
TIMEOUT = 30

def test_generate_vocabulary_from_context():
    headers = {"Content-Type": "application/json"}
    context_text = "a day at the beach"
    
    # First, try success case with context only (assuming server has key configured)
    try:
        response = requests.post(
            BASE_URL + GENERATE_ENDPOINT,
            json={"context": context_text},
            headers=headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 200, f"Expected 200 for valid context, got {response.status_code}"
        json_data = response.json()
        assert json_data.get("success") is True, "Success flag should be True on success"
        assert "terms" in json_data, "Response must contain 'terms'"
        assert isinstance(json_data["terms"], list), "'terms' must be a list"
        terms = json_data["terms"]
        # Check approximately 100 terms (allow some tolerance)
        assert 80 <= len(terms) <= 120, f"Expected ~100 terms but got {len(terms)}"
        # Check emoji prefixes present (check first 5 terms have emoji prefix pattern)
        for term in terms[:5]:
            assert isinstance(term, str), "Each term must be string"
            first_char = term[0]
            assert ord(first_char) > 127, f"First character should be emoji (non-ASCII), got {first_char}"
        # Check returned context matches input
        assert json_data.get("context") == context_text, "Returned context must match input"
    except requests.RequestException as e:
        assert False, f"HTTP request failed in success case: {e}"
    except Exception as e:
        assert False, f"Unexpected error in success case: {e}"
        
    # Second, test success case with context and an example fake API key
    fake_api_key = "sk-fakeapikey1234567890"
    try:
        response = requests.post(
            BASE_URL + GENERATE_ENDPOINT,
            json={"context": context_text, "api_key": fake_api_key},
            headers=headers,
            timeout=TIMEOUT,
        )
        # We expect either 200 or 429 (if rate limited) or 400 (if fake key rejected)
        if response.status_code == 200:
            json_data = response.json()
            assert json_data.get("success") is True, "Success flag should be True with valid context and api_key"
            assert "terms" in json_data and isinstance(json_data["terms"], list)
        elif response.status_code == 429:
            json_data = response.json()
            assert "error" in json_data and "Rate limit" in json_data["error"], "Expected rate limit error message"
        elif response.status_code == 400:
            json_data = response.json()
            assert "error" in json_data, "400 response must have error message"
        else:
            assert False, f"Unexpected status code {response.status_code} for context with API key"
    except requests.RequestException as e:
        assert False, f"HTTP request failed in API key case: {e}"
    except Exception as e:
        assert False, f"Unexpected error in API key case: {e}"
        
    # Third, test error on missing context (empty body)
    try:
        response = requests.post(
            BASE_URL + GENERATE_ENDPOINT,
            json={},
            headers=headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400, f"Expected 400 for missing context, got {response.status_code}"
        json_data = response.json()
        assert "error" in json_data, "400 error response must contain error message"
    except requests.RequestException as e:
        assert False, f"HTTP request failed in missing context case: {e}"
    except Exception as e:
        assert False, f"Unexpected error in missing context case: {e}"
    
    # Fourth, test error on missing API key if server has no key configured
    # We first check if server has API key configured
    try:
        srv_key_response = requests.get(BASE_URL + "/api/check-server-key", timeout=TIMEOUT)
        srv_key_response.raise_for_status()
        srv_key_data = srv_key_response.json()
        server_has_key = srv_key_data.get("hasServerKey", False)
    except Exception:
        server_has_key = False
    
    if not server_has_key:
        # Send request without api_key, expect 400 error with appropriate message about missing API key
        try:
            response = requests.post(
                BASE_URL + GENERATE_ENDPOINT,
                json={"context": context_text},
                headers=headers,
                timeout=TIMEOUT,
            )
            assert response.status_code == 400, f"Expected 400 when server has no key and api_key missing, got {response.status_code}"
            json_data = response.json()
            assert "error" in json_data, "Expected error message when api_key missing and server key not configured"
        except Exception as e:
            assert False, f"Error testing missing API key when server key absent: {e}"
    
    # Fifth, simulate rate limiting by rapidly sending 21 requests with same api_key
    # Use the fake_api_key from above
    if server_has_key or fake_api_key:
        try:
            # Send 20 requests - expect success or 429 (on boundary)
            for i in range(20):
                r = requests.post(
                    BASE_URL + GENERATE_ENDPOINT,
                    json={"context": context_text, "api_key": fake_api_key},
                    headers=headers,
                    timeout=TIMEOUT,
                )
                assert r.status_code in (200, 429), f"Expected 200 or 429 during rate limit test, got {r.status_code}"
                if r.status_code == 429:
                    break
            # 21st request should definitely be rate limited (429) if not already hit
            r = requests.post(
                BASE_URL + GENERATE_ENDPOINT,
                json={"context": context_text, "api_key": fake_api_key},
                headers=headers,
                timeout=TIMEOUT,
            )
            assert r.status_code == 429, f"Expected 429 on rate limit exceed, got {r.status_code}"
            json_data = r.json()
            assert "error" in json_data and "Rate limit" in json_data["error"], "429 error message must indicate rate limit exceeded"
        except requests.RequestException as e:
            assert False, f"HTTP request failed during rate limit test: {e}"
        except Exception as e:
            assert False, f"Unexpected error during rate limit test: {e}"
    
    # Sixth, test server error handling: This is typically hard to forcibly trigger.
    # Instead, try to send invalid data to provoke server error.
    try:
        response = requests.post(
            BASE_URL + GENERATE_ENDPOINT,
            data="not a json", # Invalid content type and body
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        # Accept 400 or 500; if 500, check response content
        if response.status_code == 500:
            json_data = response.json()
            assert json_data.get("success") is False, "500 error response must have success False"
            assert "error" in json_data, "500 error response must contain error message"
        elif response.status_code == 400:
            # Acceptable, server might reject bad JSON as 400
            pass
        else:
            # Other status codes are unexpected here
            assert False, f"Unexpected status code when sending malformed data: {response.status_code}"
    except requests.RequestException:
        # Exception on bad server response acceptable
        pass
    except Exception as e:
        assert False, f"Unexpected error on server error simulation: {e}"

test_generate_vocabulary_from_context()
