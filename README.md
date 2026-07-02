# Linear & News Integration Gateway

A lightweight Flask application that acts as an integration gateway between your Linear workspace and various news/event sources. It identifies company research projects on Linear (e.g., `Research: Google`) and automatically posts formatted updates with recent headlines.

It supports both automated crawling/syncing with the **News API** and a generic ingestion gateway endpoint for receiving updates from any external third-party service (Zapier, custom scripts, RSS readers, etc.).

---

## What It Does

1. **OAuth 2.0 Flow**: Dynamic, multi-workspace authorization with Linear via an in-product consent flow.
2. **Dynamic Configuration**: Connect, switch active workspaces, set News API keys, and update sync frequencies at runtime via the UI—no redeployment or static config changes required.
3. **Smart Ingestion & Deduplication**: Tracks previously posted articles per-project to prevent duplicates.
4. **Custom Update Ingestion (Gateway)**: A generic API endpoint allows any third-party tool to post articles directly to Linear projects.
5. **Background Sync Scheduler**: An integrated background worker checks for news updates automatically at configurable intervals (hourly, daily, etc.).
6. **Automatic Project Provisioning**: Can automatically create the corresponding Linear project under an active team if a company board is missing.

---

## How to Run It

### Prerequisites
* Python 3.8+
* A Linear workspace where you have admin settings access (to register an OAuth application)
* A News API key from [newsapi.org](https://newsapi.org/) (optional if only using custom manual updates)

### Configuration

1. **Initialize a virtual environment and install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Register a Linear OAuth Application**:
   * Go to **Linear Settings** -> **Workspace** -> **API**.
   * Under **OAuth Applications**, click **New application**.
   * Name: `Research News Sync`
   * Callback URL: `http://localhost:3000/oauth/callback`
   * Scopes: `read`, `write`
   * Click **Create** and copy the generated **Client ID** and **Client Secret**.

3. **Populate your `.env` file in the project root**:
   ```env
   LINEAR_CLIENT_ID=your_client_id
   LINEAR_CLIENT_SECRET=your_client_secret
   PORT=3000
   ```

### Running the Server
```bash
python app.py
```
Visit `http://localhost:3000` in your browser. Click **Connect Linear** to initiate authorization.

### Public Web Exposure (via ngrok)
To allow Linear to send redirect callbacks to your local machine and test the webhook endpoints over the internet:
1. Start ngrok pointing to port 3000:
   ```bash
   ngrok http 3000
   ```
2. Copy the public HTTPS forwarding URL (e.g., `https://your-subdomain.ngrok-free.dev`).
3. Update your `.env` file with this URL:
   ```env
   BASE_URL=https://your-subdomain.ngrok-free.dev
   ```
4. Update the Callback URL of your OAuth Application in Linear's settings to match:
   ```
   https://your-subdomain.ngrok-free.dev/oauth/callback
   ```

---

## Web Exposure & Verification Guide

To expose the application to the web for external webhook triggers and OAuth redirect callbacks, you can use **ngrok**.

* **Live Public URL**: `https://your-subdomain.ngrok-free.dev` *(obtained from your active ngrok terminal)*
* **Callback OAuth URL**: `https://your-subdomain.ngrok-free.dev/oauth/callback`

### 1. Triggering Automated Sync

This endpoint crawls the News API for headlines and posts matching projects on Linear.

**Hit Locally:**
```bash
curl -X POST http://localhost:3000/api/webhook/sync \
  -H "Content-Type: application/json" \
  -d '{"companyName": "Apple", "daysBack": 0, "dryRun": true}'
```

**Hit Over the Web (via ngrok):**
```bash
curl -X POST https://your-subdomain.ngrok-free.dev/api/webhook/sync \
  -H "Content-Type: application/json" \
  -d '{"companyName": "Apple", "daysBack": 0, "dryRun": true}'
```

### 2. Ingesting Custom Updates (Gateway)

This endpoint posts a single, manually structured update directly to your Linear boards.

**Hit Locally:**
```bash
curl -X POST http://localhost:3000/api/webhook/post_article \
  -H "Content-Type: application/json" \
  -d '{
    "companyName": "Google",
    "title": "Gemini 1.5 Pro Release",
    "url": "https://deepmind.google/technologies/gemini/",
    "source": "Google DeepMind",
    "dryRun": true
  }'
```

**Hit Over the Web (via ngrok):**
```bash
curl -X POST https://your-subdomain.ngrok-free.dev/api/webhook/post_article \
  -H "Content-Type: application/json" \
  -d '{
    "companyName": "Google",
    "title": "Gemini 1.5 Pro Release",
    "url": "https://deepmind.google/technologies/gemini/",
    "source": "Google DeepMind",
    "dryRun": true
  }'
```

---

## API Guide / Reference

### 1. Trigger Automated News API Sync
Triggers the News API crawler to fetch articles for matching `Research: {Company}` projects and post them.

* **Endpoint**: `POST /api/webhook/sync`
* **Content-Type**: `application/json`
* **Request Fields**:
  * `companyName` *(string, optional)*: If provided, syncs only this specific company (case-insensitive). Defaults to syncing all projects starting with `Research: `.
  * `daysBack` *(int, optional)*: Lookback window in days for news search (0 is today only, max 30). Defaults to `0`.
  * `dryRun` *(bool, optional)*: Simulates the process and reports metrics without writing updates to Linear. Defaults to `false`.
  * `createProjectIfMissing` *(bool, optional)*: If `companyName` is specified and no matching project is found, creates a new project titled `Research: {Company}` under the first available team. Defaults to `false`.

* **Example Request Payload**:
  ```json
  {
    "companyName": "Apple",
    "daysBack": 3,
    "dryRun": false,
    "createProjectIfMissing": true
  }
  ```

* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "result": {
      "syncedProjectsCount": 1,
      "newArticlesPosted": 3,
      "dryRun": false
    }
  }
  ```

* **Error Response (500 Internal Server Error)**:
  ```json
  {
    "success": false,
    "error": "Error message description"
  }
  ```

---

### 2. Ingest Custom Article Update (Gateway)
Ingests a single formatted article from a custom or third-party source and creates a corresponding update in Linear.

* **Endpoint**: `POST /api/webhook/post_article`
* **Content-Type**: `application/json`
* **Request Fields**:
  * `companyName` *(string, required)*: Target company name.
  * `title` *(string, required)*: Article title.
  * `url` *(string, required)*: Link to the article. Also used for deduplication.
  * `source` *(string, optional)*: Source name (e.g., "Bloomberg"). Defaults to `"Unknown Source"`.
  * `description` *(string, optional)*: Brief summary. Truncated to 500 characters in the update.
  * `publishedAt` *(string, optional)*: Publication date (ISO format). Defaults to current date.
  * `dryRun` *(bool, optional)*: Simulates posting. Defaults to `false`.
  * `createProjectIfMissing` *(bool, optional)*: Creates the project in Linear if it doesn't exist. Defaults to `false`.

* **Example Request Payload**:
  ```json
  {
    "companyName": "Google",
    "title": "Gemini Code Assistant Upgrades",
    "url": "https://deepmind.google/gemini",
    "source": "Google Blog",
    "createProjectIfMissing": true
  }
  ```

* **Success Response - New Post (200 OK)**:
  ```json
  {
    "success": true,
    "result": {
      "status": "posted",
      "message": "Article successfully posted to project update",
      "url": "https://deepmind.google/gemini",
      "dryRun": false
    }
  }
  ```

* **Success Response - Duplicate Caught (200 OK)**:
  ```json
  {
    "success": true,
    "result": {
      "status": "duplicate",
      "message": "Article already posted to this project",
      "url": "https://deepmind.google/gemini",
      "dryRun": false
    }
  }
  ```

* **Bad Request Response (400 Bad Request)**:
  ```json
  {
    "success": false,
    "error": "Missing required fields: companyName, title, and url are required"
  }
  ```

---

## Assumptions & Design Decisions

* **Lightweight Local State (`data.json`)**: To fulfill the requirement of dynamic configurations without the overhead of a full relational database, the app stores active workspace connections, credentials, and article sync history in a local, gitignored `data.json` file.
* **In-Memory Background Scheduler**: We chose APScheduler to run task intervals. This avoids requiring a heavy asynchronous task queue runner like Celery or a message broker like Redis, keeping the application lightweight and single-process.
* **Project Provisioning Convention**: The application targets Linear projects starting with `Research: `. Anything following the colon is parsed as the target keyword for the News query.
* **Secure Tokens**: Dynamic tokens are stored on disk but are explicitly sanitized (removed) from status API payloads sent back to the browser.
