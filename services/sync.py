import os
import json
from services.linear import get_projects, create_project_update, get_teams, create_project
from services.news import get_recent_news

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data.json')

def run_sync(target_company=None, days_back=0, dry_run=False, create_project_if_missing=False):
    if not os.path.exists(DATA_FILE):
        raise Exception('Data file not found, please connect Linear first')

    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    if not data.get('linearToken'):
        raise Exception('Linear not connected')

    # Initialize postedArticles as a dict mapping project_id -> list of URLs
    if 'postedArticles' not in data or isinstance(data['postedArticles'], list):
        data['postedArticles'] = {}

    projects = get_projects()
    research_projects = [p for p in projects if p.get('name', '').startswith('Research: ')]

    # If target_company is specified, check if it exists (case-insensitive)
    if target_company:
        matching_projects = [
            p for p in research_projects 
            if p['name'].replace('Research: ', '').strip().lower() == target_company.lower()
        ]
        if not matching_projects:
            if create_project_if_missing:
                print(f"Project 'Research: {target_company}' not found. Fetching teams to create it...")
                teams = get_teams()
                if not teams:
                    raise Exception("Cannot create project: No teams found in this Linear workspace.")
                
                first_team_id = teams[0]['id']
                project_name = f"Research: {target_company.strip()}"
                
                print(f"Creating project '{project_name}' under team '{teams[0]['name']}'...")
                if not dry_run:
                    create_result = create_project(project_name, [first_team_id])
                    if not create_result.get('success'):
                         raise Exception("Failed to create project in Linear.")
                    
                    new_project = create_result.get('project', {})
                    # Append the new project to research_projects list so we process it
                    research_projects.append({
                        'id': new_project['id'],
                        'name': new_project['name']
                    })
                    print(f"Created project '{new_project['name']}' with ID {new_project['id']}")
                else:
                    print(f"[Dry Run] Would create project '{project_name}' under team ID {first_team_id}")
                    # Mock project append for dry run sync
                    research_projects.append({
                        'id': 'mock-dry-run-project-id',
                        'name': project_name
                    })
            else:
                raise ValueError(f"No Linear project found for company: '{target_company}'")

    synced_projects_count = 0
    new_articles_posted = 0

    for project in research_projects:
        company_name = project['name'].replace('Research: ', '').strip()
        project_id = project['id']
        
        if target_company and company_name.lower() != target_company.lower():
            continue

        synced_projects_count += 1
        print(f"Syncing news for company: {company_name} (days_back={days_back}, dry_run={dry_run})")

        articles = get_recent_news(company_name, days_back=days_back)
        
        # Get already posted articles for this specific project
        project_posted_urls = data['postedArticles'].get(project_id, [])
        
        # Filter out articles we've already posted for this specific project
        new_articles = [a for a in articles if a.get('url') not in project_posted_urls]

        for article in new_articles:
            # Format published date cleanly
            published_at = article.get('publishedAt', '')
            published_date = published_at.split('T')[0] if 'T' in published_at else published_at
            source_name = article.get('source', {}).get('name', 'Unknown Source')
            description = article.get('description') or ''
            
            # Build a rich Markdown layout for Linear
            update_body = (
                f"### 📰 News: {article.get('title', 'No Title')}\n"
                f"**Source:** {source_name} | **Published:** {published_date}\n\n"
            )
            if description:
                # Truncate description if extremely long just in case
                short_desc = description[:500] + '...' if len(description) > 500 else description
                update_body += f"*{short_desc}*\n\n"
            update_body += f"🔗 [Read full article]({article.get('url', '#')})"

            if not dry_run:
                create_project_update(project_id, update_body)
                
                # Update the project's list of posted URLs
                if project_id not in data['postedArticles']:
                    data['postedArticles'][project_id] = []
                data['postedArticles'][project_id].append(article['url'])
                
            new_articles_posted += 1

    # Save the updated postedArticles dict if not a dry run
    if not dry_run and new_articles_posted > 0:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    return {
        'syncedProjectsCount': synced_projects_count,
        'newArticlesPosted': new_articles_posted,
        'dryRun': dry_run
    }
