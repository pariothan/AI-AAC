import requests
import os

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

def test_api_key_management_endpoint():
    """
    Test the API key management endpoint for checking server-side key availability.
    """
    url = f"{BASE_URL}/api/check-server-key"

    try:
        print(f"Testing {url}")
        response = requests.get(url, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}"

        data = response.json()
        assert isinstance(data, dict), "Response should be a dictionary"
        assert "hasServerKey" in data, "Response should contain 'hasServerKey' field"
        assert isinstance(data["hasServerKey"], bool), "'hasServerKey' should be a boolean"

        print(f"✅ Test passed! Server key availability: {data['hasServerKey']}")

        # Test that endpoints accept user-provided API key
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            print("Testing user-provided API key on /generate endpoint")
            payload = {
                "context": "Simple test",
                "api_key": api_key
            }
            response2 = requests.post(f"{BASE_URL}/generate", json=payload, timeout=60)
            # Should work with user-provided key even if no server key
            assert response2.status_code == 200, f"User-provided API key should work, got {response2.status_code}"
            print("✅ User-provided API key works correctly")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        assert False, f"Request failed: {e}"
    except Exception as e:
        print(f"❌ Test failed: {e}")
        assert False, f"Test failed: {e}"

test_api_key_management_endpoint()
