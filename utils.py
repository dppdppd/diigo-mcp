import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse


def generate_bookmark_id(created_at: str, url: str) -> str:
    """
    Generate deterministic ID from timestamp + URL
    Format: YYMMDD + first 4 chars of UUID5
    Example: "241026abc1"

    Args:
        created_at: Diigo timestamp format "2008/04/30 06:28:54 +0800"
        url: Bookmark URL

    Returns:
        Short human-readable ID
    """
    try:
        # Parse Diigo timestamp: "2008/04/30 06:28:54 +0800"
        dt = datetime.strptime(created_at.split(" +")[0], "%Y/%m/%d %H:%M:%S")
        timestamp = dt.timestamp()

        # Generate UUID5 from timestamp + URL
        full_id = uuid.uuid5(uuid.NAMESPACE_URL, str(timestamp) + url)

        # Create short ID: date + first 4 chars of UUID
        short_id = dt.strftime("%y%m%d") + str(full_id)[:4]
        return short_id
    except Exception as e:
        # Fallback to simple UUID if parsing fails
        return str(uuid.uuid4())[:8]


def parse_diigo_date(date_str: str) -> Optional[datetime]:
    """
    Parse Diigo timestamp format: '2008/04/30 06:28:54 +0800'

    Args:
        date_str: Diigo formatted timestamp

    Returns:
        datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(date_str.split(" +")[0], "%Y/%m/%d %H:%M:%S")
    except Exception:
        return None


def parse_tags(tags_string: str) -> List[str]:
    """
    Parse comma-separated tags string

    Args:
        tags_string: Comma-separated tags like "tag1,tag2,tag3"

    Returns:
        List of tag strings
    """
    if not tags_string or not tags_string.strip():
        return []
    return [t.strip() for t in tags_string.split(",") if t.strip()]


def tags_to_string(tags: List[str]) -> str:
    """
    Convert list of tags to comma-separated string

    Args:
        tags: List of tag strings

    Returns:
        Comma-separated string
    """
    return ",".join(tags)


def sanitize_tag(tag: str) -> str:
    """
    Sanitize tag for compatibility with other systems
    Replaces non-alphanumeric characters (except @ _ -) with underscore

    Args:
        tag: Original tag string

    Returns:
        Sanitized tag string
    """
    return re.sub("[^A-Za-z0-9@_-]+", "_", tag)


def validate_url(url: str) -> bool:
    """
    Validate URL format

    Args:
        url: URL string to validate

    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks of specified size

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunked lists
    """
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def format_bookmark_json(bookmark: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format bookmark for consistent JSON output
    Adds generated ID and parses tags into list

    Args:
        bookmark: Raw bookmark dict from API

    Returns:
        Formatted bookmark dict
    """
    formatted = bookmark.copy()

    # Add generated ID
    if "created_at" in bookmark and "url" in bookmark:
        formatted["generated_id"] = generate_bookmark_id(
            bookmark["created_at"], bookmark["url"]
        )

    # Parse tags into list
    if "tags" in bookmark:
        formatted["tags_list"] = parse_tags(bookmark["tags"])

    return formatted


def parse_filter_param(filter_value: str) -> str:
    """
    Normalize filter parameter for API
    Accepts: all, public, private, read_later
    API expects: all, public

    Args:
        filter_value: Filter string

    Returns:
        API-compatible filter string
    """
    filter_map = {
        "all": "all",
        "public": "public",
        "private": "all",  # API doesn't have separate private filter
    }
    return filter_map.get(filter_value.lower(), "all")


def parse_sort_param(sort_value: str) -> int:
    """
    Convert sort parameter to API integer
    created/created_at -> 0
    updated/updated_at -> 1
    popularity -> 2
    hot -> 3

    Args:
        sort_value: Sort parameter string or int

    Returns:
        API sort integer (0-3)
    """
    if isinstance(sort_value, int):
        return max(0, min(3, sort_value))

    sort_map = {
        "created": 0,
        "created_at": 0,
        "updated": 1,
        "updated_at": 1,
        "popularity": 2,
        "hot": 3,
    }
    return sort_map.get(sort_value.lower(), 1)  # Default to updated_at


def parse_bool_param(value: Any) -> str:
    """
    Convert boolean or string to Diigo API yes/no format

    Args:
        value: Boolean, string, or None

    Returns:
        "yes" or "no"
    """
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        return "yes" if value.lower() in ["yes", "true", "1", "y"] else "no"
    return "no"
