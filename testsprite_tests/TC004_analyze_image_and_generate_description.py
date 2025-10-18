import requests
from io import BytesIO
from PIL import Image
import time

BASE_URL = "http://localhost:5001"
ANALYZE_IMAGE_ENDPOINT = f"{BASE_URL}/analyze-image"
TIMEOUT = 30

def test_analyze_image_generate_description():
    headers = {}
    # A dummy valid API key for testing, replace with real key if needed
    valid_api_key = "test-api-key-123"

    # Helper to create a simple RGB image in memory
    def create_image(format="PNG", size=(100, 100), color=(255, 0, 0)):
        img = Image.new("RGB", size, color=color)
        img_bytes = BytesIO()
        img.save(img_bytes, format=format)
        img_bytes.seek(0)
        return img_bytes

    # 1. Test successful image upload and description generation with PNG image
    img_file = create_image("PNG")
    files = {"image": ("test_image.png", img_file, "image/png")}
    data = {"api_key": valid_api_key}
    try:
        resp = requests.post(ANALYZE_IMAGE_ENDPOINT, files=files, data=data, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
        json_resp = resp.json()
        assert json_resp.get("success") is True, "Response success flag is not True"
        desc = json_resp.get("description")
        assert isinstance(desc, str) and 10 <= len(desc) <= 1000, "Description should be a string of reasonable length"
    except Exception as e:
        raise AssertionError(f"Failed successful image upload test: {e}")

    # 2. Test successful upload with JPEG image (check processing correctness - server handles)
    img_file_jpeg = create_image("JPEG")
    files = {"image": ("test_image.jpeg", img_file_jpeg, "image/jpeg")}
    data = {"api_key": valid_api_key}
    try:
        resp = requests.post(ANALYZE_IMAGE_ENDPOINT, files=files, data=data, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Expected 200 OK for JPEG, got {resp.status_code}"
        json_resp = resp.json()
        assert json_resp.get("success") is True, "Success flag should be True for JPEG image"
        desc = json_resp.get("description")
        assert isinstance(desc, str) and 10 <= len(desc) <= 1000, "JPEG description length invalid"
    except Exception as e:
        raise AssertionError(f"Failed JPEG image upload test: {e}")

    # 3. Test missing image file (no 'image' in files)
    data = {"api_key": valid_api_key}
    try:
        resp = requests.post(ANALYZE_IMAGE_ENDPOINT, data=data, timeout=TIMEOUT)
        assert resp.status_code == 400, f"Expected 400 for missing file, got {resp.status_code}"
        json_resp = resp.json()
        assert "error" in json_resp, "Missing 'error' in response body for missing image"
    except Exception as e:
        raise AssertionError(f"Failed missing image file test: {e}")

    # 4. Test empty filename for image file
    img_file_empty_name = create_image("PNG")
    files = {"image": ("", img_file_empty_name, "image/png")}
    data = {"api_key": valid_api_key}
    try:
        resp = requests.post(ANALYZE_IMAGE_ENDPOINT, files=files, data=data, timeout=TIMEOUT)
        assert resp.status_code == 400, f"Expected 400 for empty filename, got {resp.status_code}"
        json_resp = resp.json()
        assert "error" in json_resp, "Missing 'error' in response for empty filename"
    except Exception as e:
        raise AssertionError(f"Failed empty filename test: {e}")

    # 5. Test missing API key (no api_key field)
    img_file = create_image("PNG")
    files = {"image": ("test_image.png", img_file, "image/png")}
    try:
        resp = requests.post(ANALYZE_IMAGE_ENDPOINT, files=files, timeout=TIMEOUT)
        # Could be 400 due to missing api_key (as per spec)
        assert resp.status_code == 400, f"Expected 400 for missing api_key, got {resp.status_code}"
        json_resp = resp.json()
        assert "error" in json_resp, "Missing 'error' in response for missing api_key"
    except Exception as e:
        raise AssertionError(f"Failed missing API key test: {e}")

    # 6. Test rate limiting - simulate by sending 21 requests quickly
    # Only if the API key is valid and rate limit is enforced
    img_file = create_image("PNG")
    files_template = {"image": ("test_image.png", img_file, "image/png")}
    data = {"api_key": valid_api_key}
    limit_exceeded = False
    # We must reopen the file in each iteration because requests closes it after the call
    try:
        for i in range(21):
            img_file = create_image("PNG")
            files = {"image": ("test_image.png", img_file, "image/png")}
            resp = requests.post(ANALYZE_IMAGE_ENDPOINT, files=files, data=data, timeout=TIMEOUT)
            if resp.status_code == 429:
                json_resp = resp.json()
                assert "error" in json_resp, "Missing 'error' message on rate limit exceeded"
                limit_exceeded = True
                break
            elif resp.status_code not in (200, 429):
                raise AssertionError(f"Unexpected status code: {resp.status_code} on request {i+1}")
        assert limit_exceeded, "Rate limit (429) was not triggered after 21 requests"
    except Exception as e:
        raise AssertionError(f"Failed rate limiting test: {e}")

    # 7. Test server error handling by sending bad data (simulate by sending non-image file as image)
    fake_file = BytesIO(b"this is not an image")
    files = {"image": ("fake.txt", fake_file, "text/plain")}
    data = {"api_key": valid_api_key}
    try:
        resp = requests.post(ANALYZE_IMAGE_ENDPOINT, files=files, data=data, timeout=TIMEOUT)
        # Server error 500 or validation error 400 possible; check for 500 or 400 with error message
        assert resp.status_code in (400, 500), f"Expected 400 or 500 for bad file, got {resp.status_code}"
        json_resp = resp.json()
        assert "error" in json_resp or ("success" in json_resp and json_resp.get("success") is False), "Expected error info in response"
    except Exception as e:
        raise AssertionError(f"Failed server error response test: {e}")

test_analyze_image_generate_description()