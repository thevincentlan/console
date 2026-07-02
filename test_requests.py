import os
import requests
from dotenv import load_dotenv

# Load environment variables (to read BASE_URL if set)
load_dotenv()

# Resolve base URL from env, stripping any trailing slashes
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:3000').rstrip('/')

print(f"Targeting Integration Gateway at: {BASE_URL}\n")

def test_trigger_sync():
    """
    Simulates triggering an automated sync for NVIDIA headlines
    """
    print("--- 1. Testing POST /api/webhook/sync (Dry Run) ---")
    url = f"{BASE_URL}/api/webhook/sync"
    payload = {
        "companyName": "NVIDIA",
        "daysBack": 1,
        "dryRun": True,
        "createProjectIfMissing": False
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(response.json())
    except Exception as e:
        print(f"Request failed: {e}")
    print("\n")

def test_post_custom_article():
    """
    Simulates posting a single custom formatted update to NVIDIA project
    """
    print("--- 2. Testing POST /api/webhook/post_article (Dry Run) ---")
    url = f"{BASE_URL}/api/webhook/post_article"
    payload = {
        "companyName": "NVIDIA",
        "title": "Agentic AI Integration gateway demo",
        "url": "https://example.com/sandbox-test-url-999",
        "source": "Sandbox CLI Test",
        "description": "This is a dry-run test update posted from test_requests.py.",
        "dryRun": True,
        "createProjectIfMissing": True
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(response.json())
    except Exception as e:
        print(f"Request failed: {e}")
    print("\n")

def test_trigger_sync_all():
    """
    Simulates triggering an automated sync for ALL existing research projects in Linear
    """
    print("--- 3. Testing POST /api/webhook/sync for ALL projects (Dry Run) ---")
    url = f"{BASE_URL}/api/webhook/sync"
    payload = {
        "daysBack": 1,
        "dryRun": True
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(response.json())
    except Exception as e:
        print(f"Request failed: {e}")
    print("\n")

if __name__ == '__main__':
    test_trigger_sync()
    test_trigger_sync_all()
    test_post_custom_article()
