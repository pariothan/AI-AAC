import requests

def test_check_if_server_has_api_key():
    base_url = "http://localhost:5001"
    endpoint = "/api/check-server-key"
    url = base_url + endpoint
    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    try:
        json_data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"
    assert "hasServerKey" in json_data, "Response JSON missing 'hasServerKey' property"
    assert isinstance(json_data["hasServerKey"], bool), "'hasServerKey' should be a boolean"

test_check_if_server_has_api_key()