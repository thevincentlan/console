import os
import json
import random
import string
from flask import Flask, request, jsonify, redirect, send_from_directory
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# Load environment variables
load_dotenv()

from services.sync import run_sync, post_single_article
from services.linear import get_organization_info

app = Flask(__name__, static_folder='public')
PORT = int(os.environ.get('PORT', 3000))
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

# Ensure data file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({
            'linearToken': None,
            'linearConnections': [],
            'activeConnectionId': None,
            'postedArticles': {}
        }, f, indent=2)

def get_linear_auth_url():
    client_id = os.environ.get('LINEAR_CLIENT_ID')
    base_url = os.environ.get('BASE_URL', f'http://localhost:{PORT}')
    redirect_uri = f"{base_url}/oauth/callback"
    state = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    # Linear requires read,write scopes to fetch projects and create updates, prompt=consent forces workspace selector
    return f"https://linear.app/oauth/authorize?client_id={client_id}&redirect_uri={requests.utils.quote(redirect_uri)}&response_type=code&state={state}&scope=read,write&prompt=consent"

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/oauth/linear')
def oauth_linear():
    if not os.environ.get('LINEAR_CLIENT_ID'):
        return "Linear Client ID not configured in .env", 500
    return redirect(get_linear_auth_url())

# used to set up oauth
@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return "Authorization code missing", 400

    base_url = os.environ.get('BASE_URL', f'http://localhost:{PORT}')
    
    try:
        response = requests.post(
            'https://api.linear.app/oauth/token',
            data={
                'client_id': os.environ.get('LINEAR_CLIENT_ID'),
                'client_secret': os.environ.get('LINEAR_CLIENT_SECRET'),
                'code': code,
                'redirect_uri': f"{base_url}/oauth/callback",
                'grant_type': 'authorization_code'
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        # Fetch organization info to identify workspace
        org_info = get_organization_info(access_token)
        org_id = org_info.get('id')
        org_name = org_info.get('name', 'Unknown Workspace')
        
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            
        if 'linearConnections' not in data:
            data['linearConnections'] = []
            
        # Check if this workspace organization is already connected
        existing_conn = None
        for conn in data['linearConnections']:
            if conn.get('id') == org_id:
                existing_conn = conn
                break
                
        if existing_conn:
            existing_conn['token'] = access_token
            existing_conn['name'] = org_name
        else:
            data['linearConnections'].append({
                'id': org_id,
                'name': org_name,
                'token': access_token
            })
            
        data['activeConnectionId'] = org_id
        data['linearToken'] = access_token # backwards compatibility
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        return redirect('/?success=true')
    except Exception as e:
        print('OAuth Error:', str(e))
        return "Error authenticating with Linear", 500

# used to get connection status
@app.route('/api/status')
def api_status():
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
        
    has_news_api_key = bool(data.get('newsApiKey') or os.environ.get('NEWS_API_KEY'))
    
    # Return connections list but sanitize raw tokens for security
    connections = []
    for conn in data.get('linearConnections', []):
        connections.append({
            'id': conn.get('id'),
            'name': conn.get('name')
        })
            
    return jsonify({
        'linearConnections': connections,
        'activeConnectionId': data.get('activeConnectionId'),
        'newsApiConnected': has_news_api_key,
        'syncIntervalHours': int(data.get('syncIntervalHours', 1)),
        'syncDaysBack': int(data.get('syncDaysBack', 0))
    })

@app.route('/api/config/select_linear', methods=['POST'])
def api_config_select_linear():
    req_data = request.json or {}
    conn_id = req_data.get('connectionId')
    if not conn_id:
        return jsonify({'success': False, 'error': 'Connection ID is required'}), 400
        
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            
        # Verify connection exists
        connections = data.get('linearConnections', [])
        selected_conn = None
        for conn in connections:
            if conn.get('id') == conn_id:
                selected_conn = conn
                break
                
        if not selected_conn:
            return jsonify({'success': False, 'error': 'Workspace connection not found'}), 404
            
        data['activeConnectionId'] = conn_id
        data['linearToken'] = selected_conn.get('token') # sync fallback
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/newsapi', methods=['POST'])
def api_config_newsapi():
    req_data = request.json or {}
    key = req_data.get('newsApiKey', '').strip()
    if not key:
        return jsonify({'success': False, 'error': 'News API Key cannot be empty'}), 400
        
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        data['newsApiKey'] = key
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects')
def api_projects():
    try:
        from services.linear import get_projects
        projects = get_projects()
        return jsonify({'success': True, 'projects': projects})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/sync_settings', methods=['POST'])
def api_config_sync_settings():
    req_data = request.json or {}
    try:
        days_back = int(req_data.get('syncDaysBack', 0))
        interval_hours = int(req_data.get('syncIntervalHours', 1))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid parameter format'}), 400
        
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            
        data['syncDaysBack'] = days_back
        data['syncIntervalHours'] = interval_hours
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        # Reschedule background job
        job = scheduler.get_job('scheduled_sync_job')
        if job:
            if interval_hours <= 0:
                scheduler.pause_job('scheduled_sync_job')
                print("Background sync task paused.")
            else:
                scheduler.resume_job('scheduled_sync_job')
                scheduler.reschedule_job('scheduled_sync_job', trigger='interval', hours=interval_hours)
                print(f"Background sync task rescheduled to run every {interval_hours} hour(s).")
                
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/disconnect', methods=['POST'])
def api_disconnect():
    req_data = request.json or {}
    integration = req_data.get('integration')
    conn_id = req_data.get('connectionId')
    
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            
        if integration == 'linear':
            connections = data.get('linearConnections', [])
            if conn_id:
                data['linearConnections'] = [c for c in connections if c.get('id') != conn_id]
            else:
                data['linearConnections'] = []
                
            # Update active connections
            if data['linearConnections']:
                data['activeConnectionId'] = data['linearConnections'][0]['id']
                data['linearToken'] = data['linearConnections'][0]['token']
            else:
                data['activeConnectionId'] = None
                data['linearToken'] = None
        elif integration == 'newsapi':
            data['newsApiKey'] = None
        else:
            return jsonify({'success': False, 'error': 'Invalid integration'}), 400
            
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/webhook/sync', methods=['POST'])
def api_webhook_sync():
    req_data = request.json or {}
    company_name = req_data.get('companyName')
    
    # Safely convert parameters
    try:
        days_back = int(req_data.get('daysBack', 0))
    except (ValueError, TypeError):
        days_back = 0
        
    dry_run = bool(req_data.get('dryRun', False))
    create_project_if_missing = bool(req_data.get('createProjectIfMissing', False))
    
    try:
        result = run_sync(
            company_name, 
            days_back=days_back, 
            dry_run=dry_run, 
            create_project_if_missing=create_project_if_missing
        )
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        print('Sync error:', e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/webhook/post_article', methods=['POST'])
def api_webhook_post_article():
    req_data = request.json or {}
    company_name = req_data.get('companyName')
    title = req_data.get('title')
    url = req_data.get('url')
    
    if not company_name or not title or not url:
        return jsonify({'success': False, 'error': 'Missing required fields: companyName, title, and url are required'}), 400
        
    description = req_data.get('description')
    source = req_data.get('source')
    published_at = req_data.get('publishedAt')
    dry_run = bool(req_data.get('dryRun', False))
    create_project_if_missing = bool(req_data.get('createProjectIfMissing', False))
    
    try:
        result = post_single_article(
            company_name=company_name,
            article_data={
                'title': title,
                'url': url,
                'description': description,
                'source': source,
                'publishedAt': published_at
            },
            dry_run=dry_run,
            create_project_if_missing=create_project_if_missing
        )
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        print('Post custom article error:', e)
        return jsonify({'success': False, 'error': str(e)}), 500

# Set up background scheduler
def scheduled_sync():
    print("Running scheduled sync...")
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        days_back = int(data.get('syncDaysBack', 0))
        run_sync(days_back=days_back)
    except Exception as e:
        print(f"Scheduled sync failed: {e}")

def get_initial_sync_interval():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            return int(data.get('syncIntervalHours', 1))
        except Exception:
            pass
    return 1

initial_interval = get_initial_sync_interval()

scheduler = BackgroundScheduler()
# Add job, if initial_interval is 0 (disabled), start paused
scheduler.add_job(
    func=scheduled_sync, 
    trigger="interval", 
    hours=max(1, initial_interval), 
    id="scheduled_sync_job"
)
if initial_interval <= 0:
    scheduler.pause_job("scheduled_sync_job")
scheduler.start()

if __name__ == '__main__':
    # When running in production/ngrok, we still bind to 0.0.0.0 or localhost on PORT
    app.run(host='0.0.0.0', port=PORT, debug=False)
