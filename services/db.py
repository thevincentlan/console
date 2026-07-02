import os
import shutil
import json

# Determine the template path (packaged read-only data.json)
TEMPLATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data.json'))

# Resolve target writeable data path
if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    # Vercel Serverless environment (read-only root, writeable /tmp)
    DATA_FILE = '/tmp/data.json'
    
    # Initialize /tmp/data.json if not present
    if not os.path.exists(DATA_FILE):
        try:
            if os.path.exists(TEMPLATE_PATH):
                shutil.copy(TEMPLATE_PATH, DATA_FILE)
                print(f"Copied template database to writeable {DATA_FILE}")
            else:
                with open(DATA_FILE, 'w') as f:
                    json.dump({
                        'linearToken': None,
                        'linearConnections': [],
                        'activeConnectionId': None,
                        'postedArticles': {}
                    }, f, indent=2)
                print(f"Initialized new database at writeable {DATA_FILE}")
        except Exception as e:
            print(f"Failed to initialize serverless database: {e}")
else:
    # Local development
    DATA_FILE = TEMPLATE_PATH
