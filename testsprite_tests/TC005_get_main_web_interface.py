import requests

def test_get_main_web_interface():
    base_url = "http://localhost:5001"
    url = f"{base_url}/"
    headers = {
        "Accept": "text/html"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to main web interface failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    content_type = response.headers.get("Content-Type", "")
    assert "text/html" in content_type, f"Expected 'text/html' in Content-Type header, got '{content_type}'"
    assert len(response.text) > 100, "HTML content too short, likely failed to load main web interface"

test_get_main_web_interface()