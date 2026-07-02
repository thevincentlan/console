import os
import json
import requests
DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data.json')

def get_linear_token():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        active_id = data.get('activeConnectionId')
        connections = data.get('linearConnections', [])
        for conn in connections:
            if conn.get('id') == active_id:
                return conn.get('token')
        
        # Fallback to single token if exists
        return data.get('linearToken')
    except Exception:
        return None

def get_organization_info(token):
    query = """
    query {
      organization {
        id
        name
      }
    }
    """
    response = requests.post(
        'https://api.linear.app/graphql',
        json={'query': query},
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
    )
    
    response_data = response.json()
    if 'errors' in response_data:
        error_msgs = ", ".join([e.get('message', 'Unknown error') for e in response_data['errors']])
        raise Exception(f"Linear API Error during OAuth callback: {error_msgs}")
        
    return response_data.get('data', {}).get('organization', {})

def linear_graphql(query, variables=None):
    if variables is None:
        variables = {}
        
    token = get_linear_token()
    if not token:
        raise Exception('Linear not authenticated')

    response = requests.post(
        'https://api.linear.app/graphql',
        json={'query': query, 'variables': variables},
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
    )
    
    response_data = response.json()
    if 'errors' in response_data:
        error_msgs = ", ".join([e.get('message', 'Unknown error') for e in response_data['errors']])
        raise Exception(f"Linear API Error: {error_msgs}")

    return response_data.get('data', {})

def get_projects():
    query = """
    query {
      projects {
        nodes {
          id
          name
        }
      }
    }
    """
    data = linear_graphql(query)
    return data.get('projects', {}).get('nodes', [])

def create_project_update(project_id, body):
    query = """
    mutation ProjectUpdateCreate($projectId: String!, $body: String!) {
      projectUpdateCreate(input: { projectId: $projectId, body: $body }) {
        success
        projectUpdate {
          id
        }
      }
    }
    """
    data = linear_graphql(query, {'projectId': project_id, 'body': body})
    return data.get('projectUpdateCreate', {})

def get_teams():
    query = """
    query {
      teams {
        nodes {
          id
          name
        }
      }
    }
    """
    data = linear_graphql(query)
    return data.get('teams', {}).get('nodes', [])

def create_project(name, team_ids):
    query = """
    mutation ProjectCreate($name: String!, $teamIds: [String!]!) {
      projectCreate(input: { name: $name, teamIds: $teamIds }) {
        success
        project {
          id
          name
        }
      }
    }
    """
    data = linear_graphql(query, {'name': name, 'teamIds': team_ids})
    return data.get('projectCreate', {})
