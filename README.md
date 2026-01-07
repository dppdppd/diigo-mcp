# Diigo MCP Server

Model Context Protocol (MCP) server for the Diigo bookmarking service API v2.

## Features

- **List & Search Bookmarks** - Browse all bookmarks with filters (tags, visibility, sort order)
- **Create Bookmarks** - Add new bookmarks with tags, descriptions, and privacy settings
- **Update Bookmarks** - Modify existing bookmarks with smart merging
- **Delete Bookmarks** - Remove bookmarks by URL
- **Get Annotations** - Access highlights and comments on bookmarks
- **Bulk Operations** - Create multiple bookmarks with rate limiting
- **Auto-pagination** - Automatically fetch all bookmarks beyond API's 100-item limit
- **Rate Limit Handling** - Automatic retry with exponential backoff

## Installation

### 1. Get Diigo API Credentials

Visit https://www.diigo.com/api_keys/new/ to create an API key.

### 2. Clone and Install

```bash
# Clone repository
git clone https://github.com/dppdppd/diigo-mcp.git
cd diigo-mcp

# Create virtual environment and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Configure Credentials

Copy `.env.example` to `.env` and add your credentials:

```bash
cp .env.example .env
# Edit .env with your actual Diigo credentials:
# DIIGO_USERNAME=your_username
# DIIGO_PASSWORD=your_password
# DIIGO_API_KEY=your_api_key
```

### 4. Add to OpenCode Configuration

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "diigo": {
      "type": "local",
      "command": ["/path/to/diigo-mcp/.venv/bin/python", "/path/to/diigo-mcp/main.py"],
      "enabled": true,
      "timeout": 30000,
      "environment": {
        "DIIGO_USERNAME": "{env:DIIGO_USERNAME}",
        "DIIGO_PASSWORD": "{env:DIIGO_PASSWORD}",
        "DIIGO_API_KEY": "{env:DIIGO_API_KEY}"
      }
    }
  }
}
```

**Note:** Replace `/path/to/diigo-mcp/` with the actual path where you cloned the repository.

### 5. Restart OpenCode

After updating the configuration, restart OpenCode to load the MCP server.

## Available Tools

### Bookmark Management

#### `diigo_list_bookmarks`
List bookmarks with optional filters.
- **Parameters:**
  - `user` (optional): Username to fetch bookmarks for (defaults to authenticated user)
  - `count` (optional): Number to fetch. Omit for auto-pagination (fetches all bookmarks)
  - `start` (optional): Start offset (default: 0)
  - `sort` (optional): Sort order - 0=created, 1=updated, 2=popularity, 3=hot (default: 1)
  - `tags` (optional): Comma-separated tags to filter
  - `filter` (optional): "all" or "public" (default: "all")
  - `list_name` (optional): Filter by list name
- **Example:** `diigo_list_bookmarks(tags="python,programming", count=50)`

#### `diigo_search_bookmarks`
Search bookmarks by query string (matches title/description).
- **Parameters:**
  - `query` (required): Search query
  - `tags` (optional): Comma-separated tags to filter
  - `filter` (optional): "all" or "public"
  - `user` (optional): Username
- **Example:** `diigo_search_bookmarks(query="machine learning", tags="ai")`

#### `diigo_get_bookmark`
Get a single bookmark by URL with full details including annotations.
- **Parameters:**
  - `url` (required): Bookmark URL to find
  - `user` (optional): Username
- **Example:** `diigo_get_bookmark(url="https://example.com")`

#### `diigo_create_bookmark`
Create a new bookmark.
- **Parameters:**
  - `url` (required): Bookmark URL
  - `title` (required): Bookmark title
  - `desc` (optional): Description (default: "")
  - `tags` (optional): Comma-separated tags (default: "")
  - `shared` (optional): Public (true) or private (false) (default: false)
  - `read_later` (optional): Mark as unread (default: false)
- **Example:** `diigo_create_bookmark(url="https://example.com", title="Example Site", tags="examples,web", shared=true)`

#### `diigo_update_bookmark`
Update an existing bookmark (preserves unmodified fields).
- **Parameters:**
  - `url` (required): Bookmark URL (identifier)
  - `title` (optional): New title
  - `desc` (optional): New description
  - `tags` (optional): New tags (comma-separated)
  - `shared` (optional): New sharing status
  - `read_later` (optional): New read_later status
- **Example:** `diigo_update_bookmark(url="https://example.com", tags="updated,tags")`

#### `diigo_delete_bookmark`
Delete a bookmark by URL.
- **Parameters:**
  - `url` (required): Bookmark URL
  - `title` (optional): Bookmark title (auto-fetched if not provided)
- **Example:** `diigo_delete_bookmark(url="https://example.com")`

#### `diigo_get_recent_bookmarks`
Get recently updated bookmarks.
- **Parameters:**
  - `count` (optional): Number to fetch (default: 50)
  - `user` (optional): Username
- **Example:** `diigo_get_recent_bookmarks(count=20)`

### Annotations

#### `diigo_get_annotations`
Get highlights and comments for a specific bookmark.
- **Parameters:**
  - `url` (required): Bookmark URL
  - `user` (optional): Username
- **Example:** `diigo_get_annotations(url="https://example.com")`

### Bulk Operations

#### `diigo_bulk_create_bookmarks`
Create multiple bookmarks with rate limiting.
- **Parameters:**
  - `bookmarks` (required): Array of bookmark objects (each with url, title, desc, tags, shared, read_later)
  - `delay` (optional): Delay between requests in seconds (default: 0.5)
- **Example:**
```json
diigo_bulk_create_bookmarks(bookmarks=[
  {"url": "https://site1.com", "title": "Site 1", "tags": "tag1"},
  {"url": "https://site2.com", "title": "Site 2", "tags": "tag2"}
], delay=1.0)
```

## API Limitations

The Diigo API v2 is limited:
- Max 100 bookmarks per request (use auto-pagination)
- Comments/annotations are read-only
- No list management endpoints
- No standalone tag operations
- Rate limits enforced (automatic retry with backoff)

## Response Format

All tools return raw JSON from the Diigo API:

**Bookmark Object:**
```json
{
  "title": "Example",
  "url": "https://example.com",
  "user": "username",
  "desc": "Description",
  "tags": "tag1,tag2",
  "shared": "yes",
  "readlater": "no",
  "created_at": "2024/01/06 12:00:00 +0000",
  "updated_at": "2024/01/06 12:00:00 +0000",
  "comments": [],
  "annotations": []
}
```

**Error Response:**
```json
{
  "error": "error message"
}
```

## Development

### Project Structure

```
diigo-mcp/
├── main.py           # MCP server entry point
├── config.py         # Configuration & validation
├── diigo_client.py   # API client with retry logic
├── tools.py          # Tool implementations
├── utils.py          # Helper functions
├── requirements.txt  # Python dependencies
├── .env.example      # Environment template
├── .gitignore        # Git ignore rules
├── LICENSE           # MIT License
└── README.md         # This file
```

### Testing

Test authentication and basic functionality:

```bash
# Ensure environment variables are set
export DIIGO_USERNAME=your_username
export DIIGO_PASSWORD=your_password
export DIIGO_API_KEY=your_api_key

# Run the server (it will wait for JSON-RPC input via stdio)
.venv/bin/python main.py
```

The server will start and log:
```
INFO - Diigo MCP Server starting...
INFO - Configuration validated successfully
```

Press Ctrl+C to stop.

### Troubleshooting

#### Server Won't Start
- **Check credentials:** Verify `.env` file exists and contains valid credentials
- **Check dependencies:** Run `.venv/bin/pip install -r requirements.txt`
- **Check Python version:** Requires Python 3.8 or higher

#### Authentication Errors
- **Invalid credentials:** Visit https://www.diigo.com/api_keys/new/ to verify API key
- **Username/password:** Ensure these match your Diigo account login

#### Rate Limiting
- The server automatically retries with exponential backoff (1s, 2s, 4s, 8s, 16s)
- If rate limited, wait a few minutes before retrying
- Use `delay` parameter in bulk operations to avoid rate limits

#### Bookmark Not Found
- **URL must match exactly:** Include protocol (https://) and full path
- **Check ownership:** Some operations only work on your own bookmarks
- **Public vs private:** Use `filter="all"` to see private bookmarks

#### OpenCode Integration Issues
- **Restart required:** After editing `opencode.json`, restart OpenCode
- **Check logs:** OpenCode logs will show MCP server startup errors
- **Path issues:** Ensure paths in `opencode.json` are absolute and correct
- **Environment variables:** Verify `{env:VAR_NAME}` variables are set in shell before starting OpenCode

### Common Use Cases

#### Import Bookmarks from Browser
```python
# Export bookmarks from browser as HTML, parse URLs and titles
bookmarks = [
    {"url": "https://example.com", "title": "Example", "tags": "imported"},
    # ... more bookmarks
]
diigo_bulk_create_bookmarks(bookmarks=bookmarks, delay=1.0)
```

#### Find All Bookmarks with Tag
```python
# List all bookmarks with specific tag
diigo_list_bookmarks(tags="python")
```

#### Backup All Bookmarks
```python
# Fetch all bookmarks (auto-pagination)
diigo_list_bookmarks()  # Omit count parameter to get all
```

#### Search for Keyword
```python
# Search bookmarks by title/description
diigo_search_bookmarks(query="machine learning")
```

#### Update Multiple Bookmarks
```python
# Get bookmarks, modify, and update
bookmarks = diigo_list_bookmarks(tags="old-tag")
for bookmark in bookmarks:
    diigo_update_bookmark(url=bookmark['url'], tags="new-tag")
```

## License

MIT

## Links

- Diigo API Documentation: https://www.diigo.com/api_dev
- Get API Key: https://www.diigo.com/api_keys/new/
- Diigo Service: https://www.diigo.com
