# Linear & News API Integrator

A lightweight Flask application that connects your Linear workspace with the News API. It automatically searches for new articles related to companies you are researching and posts them as updates to the corresponding Linear projects.

## What it does

1. Connects to Linear via an in-product OAuth flow.
2. Scans your Linear workspace for projects titled `Research: {Company}`.
3. For each company, it queries the News API for articles published today.
4. Prevents duplicate postings by tracking processed article URLs.
5. Posts a new project update on Linear for each newly found article with the headline and link.
6. Runs automatically every hour, or can be triggered manually via a webhook or the UI.

## How to run it

### Prerequisites

1. Python 3.8+
2. A Linear workspace where you are an admin (to create an OAuth application)
3. A News API key from [newsapi.org](https://newsapi.org/)

### Configuration

1. Initialize a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create a Linear OAuth application:
   - Go to Linear Settings -> Workspace -> API.
   - Under "OAuth Applications", click "New application".
   - Set the name to "Research News Sync".
   - Set the Callback URL to `http://localhost:3000/oauth/callback`.
   - Add scopes: `read`, `write`.
   - Save the application to get your Client ID and Client Secret.

3. Populate the `.env` file with your credentials:
   ```env
   LINEAR_CLIENT_ID=your_linear_client_id
   LINEAR_CLIENT_SECRET=your_linear_client_secret
   NEWS_API_KEY=your_news_api_key
   PORT=3000
   ```

### Running the server

Start the server using python:
```bash
source venv/bin/activate
python app.py
```

Then, visit `http://localhost:3000` in your browser. Click "Connect Linear" to authenticate.

### Exposing the server over the Web (via ngrok)

For the app to receive OAuth redirect callbacks from Linear and to expose a live webhook endpoint that can be triggered over the web, you can use `ngrok`.

1. **Install & authenticate ngrok**:
   Follow instructions on [ngrok.com](https://ngrok.com/) to install and set up your auth token.

2. **Expose the Flask server**:
   Start ngrok pointing to the server port (default 3000):
   ```bash
   ngrok http 3000
   ```

3. **Update configurations with your ngrok URL**:
   * Copy the public HTTPS forwarding URL from the ngrok terminal output (e.g. `https://your-subdomain.ngrok-free.dev`).
   * Update the `BASE_URL` key in your `.env` file:
     ```env
     BASE_URL=https://your-subdomain.ngrok-free.dev
     ```
   * Update your redirect URI in your Linear OAuth Application settings to match:
     ```
     https://your-subdomain.ngrok-free.dev/oauth/callback
     ```

### Triggering the Webhook

You can trigger a sync manually by sending a `POST` request to the webhook endpoint.

**Locally:**
```bash
curl -X POST http://localhost:3000/api/webhook/sync \
  -H "Content-Type: application/json" \
  -d '{"companyName": "Apple"}'
```

**Over the Web (via ngrok):**
```bash
curl -X POST https://your-subdomain.ngrok-free.dev/api/webhook/sync \
  -H "Content-Type: application/json" \
  -d '{"companyName": "Apple", "daysBack": 7, "dryRun": false}'
```

*Note: The `companyName` parameter is optional (default: syncs all projects starting with `Research: `). `daysBack` (default: 0) and `dryRun` (default: false) can be set to customize the timeframe or simulate the sync without writing updates.*

## Assumptions & Design Decisions

- **Token Storage**: The application stores the OAuth token and sync history in a local `data.json` file. This is to fulfill the "dynamic authentication" requirement without the overhead of a full database since the app does not need multi-tenancy.
- **Timeframe**: News queries are scoped to the current day (`from: today, to: today`) to ensure we are only getting the most recent news.
- **Deduplication**: We store the URLs of articles we have already posted to prevent spamming the Linear project with duplicates on subsequent syncs.
- **Project Convention**: The app specifically looks for projects whose name starts with `Research: `. Anything after the colon is treated as the company name.
