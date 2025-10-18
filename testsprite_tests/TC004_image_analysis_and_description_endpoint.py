import requests
import os
import io

BASE_URL = "http://localhost:5001"
TIMEOUT = 60

def test_image_analysis_and_description():
    """
    Validate the image upload and analysis endpoint that processes multiple image formats
    and generates contextual vocabulary descriptions using GPT-4o-mini vision API.
    """
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY", "")

    url = f"{BASE_URL}/analyze-image"

    # Create a simple test image (1x1 pixel PNG)
    # PNG header for a 1x1 red pixel
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf'
        b'\xc0\x00\x00\x00\x03\x00\x01\x9a{\x99\x8d\x00\x00\x00\x00IEND\xaeB`\x82'
    )

    try:
        print(f"Testing {url}")

        # Prepare multipart/form-data request
        files = {
            'image': ('test_image.png', io.BytesIO(png_data), 'image/png')
        }
        data = {
            'api_key': api_key
        }

        response = requests.post(url, files=files, data=data, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}. Response: {response.text[:200]}"

        json_data = response.json()

        # Validate response structure based on actual Flask API
        assert "success" in json_data, "Response missing 'success' key"
        assert json_data["success"] == True, f"API returned success=False: {json_data.get('error', 'Unknown error')}"
        assert "description" in json_data, "Response missing 'description' key"

        description = json_data["description"]
        assert isinstance(description, str), "Description should be a string"
        assert len(description) > 10, f"Description seems too short: '{description}'"

        print(f"✅ Test passed! Image analyzed successfully")
        print(f"Description: {description[:100]}...")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        assert False, f"Request failed: {e}"
    except Exception as e:
        print(f"❌ Test failed: {e}")
        assert False, f"Test failed: {e}"

test_image_analysis_and_description()
