import json
import logging
from typing import Dict, List, Any, Optional
from diigo_client import DiigoClient
from utils import (
    parse_sort_param,
    parse_filter_param,
    validate_url,
    format_bookmark_json,
)

logger = logging.getLogger(__name__)


async def list_bookmarks_tool(
    user: Optional[str] = None,
    count: Optional[int] = None,
    start: int = 0,
    sort: int = 1,
    tags: Optional[str] = None,
    filter: str = "all",
    list_name: Optional[str] = None,
) -> str:
    """
    List bookmarks with optional filters

    Args:
        user: Username (defaults to configured user)
        count: Number to fetch (omit for all with auto-pagination)
        start: Start offset
        sort: Sort order (0=created, 1=updated, 2=popularity, 3=hot)
        tags: Comma-separated tags to filter
        filter: "all" or "public"
        list_name: Filter by list name

    Returns:
        JSON array of bookmarks or error dict
    """
    try:
        async with DiigoClient() as client:
            if count is None:
                # Auto-paginate to get all
                bookmarks = await client.get_all_bookmarks(
                    user=user, sort=sort, tags=tags, filter=filter, list_name=list_name
                )
            else:
                bookmarks = await client.get_bookmarks(
                    user=user,
                    start=start,
                    count=count,
                    sort=sort,
                    tags=tags,
                    filter=filter,
                    list_name=list_name,
                )

            # Handle error response
            if isinstance(bookmarks, dict) and "error" in bookmarks:
                return json.dumps(bookmarks)

            return json.dumps(bookmarks)

    except Exception as e:
        logger.error(f"Error listing bookmarks: {e}")
        return json.dumps({"error": str(e)})


async def search_bookmarks_tool(
    query: str,
    tags: Optional[str] = None,
    filter: str = "all",
    user: Optional[str] = None,
) -> str:
    """
    Search bookmarks by title/description
    Note: Diigo API has limited search, this does client-side filtering

    Args:
        query: Search query (matches title/description)
        tags: Comma-separated tags to filter
        filter: "all" or "public"
        user: Username (defaults to configured user)

    Returns:
        JSON array of matching bookmarks or error dict
    """
    try:
        async with DiigoClient() as client:
            # Get all bookmarks with filters
            bookmarks = await client.get_all_bookmarks(
                user=user, tags=tags, filter=filter
            )

            # Handle error response
            if isinstance(bookmarks, dict) and "error" in bookmarks:
                return json.dumps(bookmarks)

            # Client-side search
            query_lower = query.lower()
            results = [
                b
                for b in bookmarks
                if query_lower in b.get("title", "").lower()
                or query_lower in b.get("desc", "").lower()
            ]

            return json.dumps(results)

    except Exception as e:
        logger.error(f"Error searching bookmarks: {e}")
        return json.dumps({"error": str(e)})


async def get_bookmark_tool(url: str, user: Optional[str] = None) -> str:
    """
    Get a single bookmark by URL

    Args:
        url: Bookmark URL to find
        user: Username (defaults to configured user)

    Returns:
        JSON bookmark object or error dict
    """
    try:
        async with DiigoClient() as client:
            # Get all bookmarks
            bookmarks = await client.get_all_bookmarks(user=user)

            # Handle error response
            if isinstance(bookmarks, dict) and "error" in bookmarks:
                return json.dumps(bookmarks)

            # Find matching bookmark
            for b in bookmarks:
                if b.get("url") == url:
                    return json.dumps(b)

            return json.dumps({"error": f"Bookmark not found: {url}"})

    except Exception as e:
        logger.error(f"Error getting bookmark: {e}")
        return json.dumps({"error": str(e)})


async def create_bookmark_tool(
    url: str,
    title: str,
    desc: str = "",
    tags: str = "",
    shared: bool = False,
    read_later: bool = False,
) -> str:
    """
    Create a new bookmark

    Args:
        url: Bookmark URL (required)
        title: Bookmark title (required)
        desc: Description
        tags: Comma-separated tags
        shared: Public (True) or private (False)
        read_later: Mark as unread

    Returns:
        JSON response with message or error
    """
    try:
        # Validate URL
        if not validate_url(url):
            return json.dumps({"error": f"Invalid URL: {url}"})

        async with DiigoClient() as client:
            result = await client.save_bookmark(
                url=url,
                title=title,
                desc=desc,
                tags=tags,
                shared=shared,
                read_later=read_later,
                merge=False,  # Create new, don't merge
            )

            return json.dumps(result)

    except Exception as e:
        logger.error(f"Error creating bookmark: {e}")
        return json.dumps({"error": str(e)})


async def update_bookmark_tool(
    url: str,
    title: Optional[str] = None,
    desc: Optional[str] = None,
    tags: Optional[str] = None,
    shared: Optional[bool] = None,
    read_later: Optional[bool] = None,
) -> str:
    """
    Update an existing bookmark
    Uses merge=yes to preserve fields not being updated

    Args:
        url: Bookmark URL (identifier, required)
        title: New title (optional)
        desc: New description (optional)
        tags: New tags (optional)
        shared: New sharing status (optional)
        read_later: New read_later status (optional)

    Returns:
        JSON response with message or error
    """
    try:
        # Validate URL
        if not validate_url(url):
            return json.dumps({"error": f"Invalid URL: {url}"})

        async with DiigoClient() as client:
            # Get current bookmark to preserve unmodified fields
            bookmarks = await client.get_all_bookmarks()

            # Handle error
            if isinstance(bookmarks, dict) and "error" in bookmarks:
                return json.dumps(bookmarks)

            # Find existing bookmark
            existing = None
            for b in bookmarks:
                if b.get("url") == url:
                    existing = b
                    break

            if not existing:
                return json.dumps({"error": f"Bookmark not found: {url}"})

            # Build update with merge
            result = await client.save_bookmark(
                url=url,
                title=title if title is not None else existing.get("title", ""),
                desc=desc if desc is not None else existing.get("desc", ""),
                tags=tags if tags is not None else existing.get("tags", ""),
                shared=shared
                if shared is not None
                else (existing.get("shared") == "yes"),
                read_later=read_later
                if read_later is not None
                else (existing.get("readlater") == "yes"),
                merge=True,  # Merge with existing
            )

            return json.dumps(result)

    except Exception as e:
        logger.error(f"Error updating bookmark: {e}")
        return json.dumps({"error": str(e)})


async def delete_bookmark_tool(url: str, title: Optional[str] = None) -> str:
    """
    Delete a bookmark

    Args:
        url: Bookmark URL (required)
        title: Bookmark title (will auto-fetch if not provided)

    Returns:
        JSON response with message or error
    """
    try:
        async with DiigoClient() as client:
            # If title not provided, fetch it
            if not title:
                bookmarks = await client.get_all_bookmarks()

                # Handle error
                if isinstance(bookmarks, dict) and "error" in bookmarks:
                    return json.dumps(bookmarks)

                # Find bookmark
                for b in bookmarks:
                    if b.get("url") == url:
                        title = b.get("title")
                        break

                if not title:
                    return json.dumps({"error": f"Bookmark not found: {url}"})

            result = await client.delete_bookmark(url=url, title=title)
            return json.dumps(result)

    except Exception as e:
        logger.error(f"Error deleting bookmark: {e}")
        return json.dumps({"error": str(e)})


async def get_recent_bookmarks_tool(count: int = 50, user: Optional[str] = None) -> str:
    """
    Get recently updated bookmarks

    Args:
        count: Number to fetch
        user: Username (defaults to configured user)

    Returns:
        JSON array of bookmarks sorted by updated_at
    """
    try:
        async with DiigoClient() as client:
            bookmarks = await client.get_bookmarks(
                user=user,
                count=count,
                sort=1,  # Sort by updated_at
            )

            # Handle error response
            if isinstance(bookmarks, dict) and "error" in bookmarks:
                return json.dumps(bookmarks)

            return json.dumps(bookmarks)

    except Exception as e:
        logger.error(f"Error getting recent bookmarks: {e}")
        return json.dumps({"error": str(e)})


async def get_annotations_tool(url: str, user: Optional[str] = None) -> str:
    """
    Get annotations for a specific bookmark

    Args:
        url: Bookmark URL
        user: Username (defaults to configured user)

    Returns:
        JSON array of annotations or error dict
    """
    try:
        async with DiigoClient() as client:
            # Get all bookmarks
            bookmarks = await client.get_all_bookmarks(user=user)

            # Handle error response
            if isinstance(bookmarks, dict) and "error" in bookmarks:
                return json.dumps(bookmarks)

            # Find bookmark with matching URL
            for b in bookmarks:
                if b.get("url") == url:
                    annotations = b.get("annotations", [])
                    return json.dumps(annotations)

            return json.dumps({"error": f"Bookmark not found: {url}"})

    except Exception as e:
        logger.error(f"Error getting annotations: {e}")
        return json.dumps({"error": str(e)})


async def bulk_create_bookmarks_tool(
    bookmarks: List[Dict[str, Any]], delay: float = 0.5
) -> str:
    """
    Create multiple bookmarks with rate limiting

    Args:
        bookmarks: List of bookmark dicts with url, title, desc, tags, shared, read_later
        delay: Delay between requests in seconds

    Returns:
        JSON summary with success/failure counts
    """
    try:
        async with DiigoClient() as client:
            result = await client.bulk_save_bookmarks(bookmarks=bookmarks, delay=delay)

            return json.dumps(result)

    except Exception as e:
        logger.error(f"Error bulk creating bookmarks: {e}")
        return json.dumps({"error": str(e)})
