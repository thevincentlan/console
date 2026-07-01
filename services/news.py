import os
import json
import requests
from datetime import datetime, timedelta

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data.json')

def get_news_api_key():
    # 1. Try to read from data.json first (dynamic configuration)
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            if data.get('newsApiKey'):
                return data['newsApiKey']
        except Exception:
            pass
    # 2. Fall back to environment variable
    return os.environ.get('NEWS_API_KEY')

def get_recent_news(company_name, days_back=0):
    api_key = get_news_api_key()
    if not api_key:
        raise Exception('News API key not configured')

    # Get date range based on days_back
    today = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

    try:
        response = requests.get(
            'https://newsapi.org/v2/everything',
            params={
                'q': company_name,
                'from': from_date,
                'to': today,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': api_key
            }
        )
        response.raise_for_status()
        return response.json().get('articles', [])
    except requests.exceptions.RequestException as e:
        print('News API Error:', e.response.text if e.response else str(e))
        raise Exception('Failed to fetch news')
