import asyncio
import logging
from typing import Dict, List, Any, Optional
import aiohttp
from config import Config
from utils import parse_bool_param, chunk_list

logger = logging.getLogger(__name__)


class DiigoClient:
    """Async HTTP client for Diigo API v2 with Basic Auth"""

    def __init__(self):
        self.base_url = Config.DIIGO_BASE_URL
        self.api_key = Config.DIIGO_API_KEY
        self.username = Config.DIIGO_USERNAME
        self.password = Config.DIIGO_PASSWORD
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth = aiohttp.BasicAuth(self.username, self.password)

    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
        self.session = aiohttp.ClientSession(timeout=timeout, auth=self.auth)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Any:
        """
        Make HTTP request with automatic retry on rate limits

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data

        Returns:
            JSON response or dict with error
        """
        if params is None:
            params = {}

        # Add API key to all requests
        params["key"] = self.api_key

        url = f"{self.base_url}/{endpoint}"

        for attempt in range(Config.MAX_RETRIES):
            try:
                async with self.session.request(
                    method, url, params=params, data=data
                ) as resp:
                    # Success
                    if resp.status == 200:
                        try:
                            return await resp.json()
                        except aiohttp.ContentTypeError:
                            # Handle non-JSON responses
                            text = await resp.text()
                            logger.warning(f"Non-JSON response: {text}")
                            return {"message": text}

                    # Rate limit or bad request
                    elif resp.status == 400:
                        text = await resp.text()
                        logger.warning(
                            f"400 error (attempt {attempt + 1}/{Config.MAX_RETRIES}): {text}"
                        )

                        if attempt < Config.MAX_RETRIES - 1:
                            wait = Config.RETRY_BACKOFF**attempt
                            logger.info(f"Retrying in {wait}s...")
                            await asyncio.sleep(wait)
                            continue
                        else:
                            return {
                                "error": f"Request failed after {Config.MAX_RETRIES} attempts: {text}"
                            }

                    # Auth error
                    elif resp.status == 401:
                        text = await resp.text()
                        return {"error": f"Authentication failed: {text}"}

                    # Forbidden
                    elif resp.status == 403:
                        text = await resp.text()
                        return {"error": f"Access forbidden: {text}"}

                    # Not found
                    elif resp.status == 404:
                        text = await resp.text()
                        return {"error": f"Resource not found: {text}"}

                    # Server busy
                    elif resp.status == 503:
                        text = await resp.text()
                        logger.warning(
                            f"503 server busy (attempt {attempt + 1}/{Config.MAX_RETRIES})"
                        )

                        if attempt < Config.MAX_RETRIES - 1:
                            wait = Config.RETRY_BACKOFF**attempt
                            logger.info(f"Retrying in {wait}s...")
                            await asyncio.sleep(wait)
                            continue
                        else:
                            return {
                                "error": f"Server busy after {Config.MAX_RETRIES} attempts: {text}"
                            }

                    # Other errors
                    else:
                        text = await resp.text()
                        return {"error": f"HTTP {resp.status}: {text}"}

            except asyncio.TimeoutError:
                logger.error(
                    f"Request timeout (attempt {attempt + 1}/{Config.MAX_RETRIES})"
                )
                if attempt < Config.MAX_RETRIES - 1:
                    wait = Config.RETRY_BACKOFF**attempt
                    await asyncio.sleep(wait)
                    continue
                else:
                    return {
                        "error": f"Request timeout after {Config.MAX_RETRIES} attempts"
                    }

            except Exception as e:
                logger.error(f"Request error: {e}")
                return {"error": f"Request failed: {str(e)}"}

        return {"error": "Max retries exceeded"}

    async def get_bookmarks(
        self,
        user: Optional[str] = None,
        start: int = 0,
        count: int = 100,
        sort: int = 1,
        tags: Optional[str] = None,
        filter: str = "all",
        list_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve bookmarks from Diigo API

        Args:
            user: Username (defaults to configured user)
            start: Start offset
            count: Number to fetch (max 100)
            sort: Sort order (0=created, 1=updated, 2=popularity, 3=hot)
            tags: Comma-separated tags to filter
            filter: "all" or "public"
            list_name: Filter by list name

        Returns:
            List of bookmark dicts or dict with error
        """
        if user is None:
            user = Config.get_default_user()

        params = {
            "user": user,
            "start": start,
            "count": min(count, Config.MAX_BOOKMARKS_PER_REQUEST),
            "sort": sort,
            "filter": filter,
        }

        if tags:
            params["tags"] = tags

        if list_name:
            params["list"] = list_name

        result = await self._request_with_retry("GET", "bookmarks", params=params)

        # Handle error response
        if isinstance(result, dict) and "error" in result:
            return result

        # Return list of bookmarks
        return result if isinstance(result, list) else []

    async def get_all_bookmarks(
        self, user: Optional[str] = None, **filters
    ) -> List[Dict[str, Any]]:
        """
        Auto-paginate through all bookmarks

        Args:
            user: Username (defaults to configured user)
            **filters: Additional filters (tags, filter, sort, list_name)

        Returns:
            List of all bookmarks or dict with error
        """
        bookmarks = []
        start = 0

        while True:
            batch = await self.get_bookmarks(
                user=user, start=start, count=100, **filters
            )

            # Handle error response
            if isinstance(batch, dict) and "error" in batch:
                return batch

            if not batch:
                break

            bookmarks.extend(batch)

            # Last page
            if len(batch) < 100:
                break

            start += 100

        return bookmarks

    async def save_bookmark(
        self,
        url: str,
        title: str,
        desc: str = "",
        tags: str = "",
        shared: bool = False,
        read_later: bool = False,
        merge: bool = True,
    ) -> Dict[str, Any]:
        """
        Save (create or update) a bookmark

        Args:
            url: Bookmark URL (required)
            title: Bookmark title (required)
            desc: Description
            tags: Comma-separated tags
            shared: Public (True) or private (False)
            read_later: Mark as unread
            merge: Merge with existing (True) or replace (False)

        Returns:
            Response dict with message or error
        """
        data = {
            "url": url,
            "title": title,
            "desc": desc,
            "tags": tags,
            "shared": parse_bool_param(shared),
            "readLater": parse_bool_param(read_later),
            "merge": parse_bool_param(merge),
        }

        return await self._request_with_retry("POST", "bookmarks", data=data)

    async def delete_bookmark(self, url: str, title: str) -> Dict[str, Any]:
        """
        Delete a bookmark

        Args:
            url: Bookmark URL (required)
            title: Bookmark title (required)

        Returns:
            Response dict with message or error
        """
        data = {
            "url": url,
            "title": title,
        }

        return await self._request_with_retry("POST", "bookmarks", data=data)

    async def bulk_save_bookmarks(
        self, bookmarks: List[Dict[str, Any]], delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        Save multiple bookmarks with rate limiting

        Args:
            bookmarks: List of bookmark dicts (url, title, desc, tags, shared, read_later)
            delay: Delay between requests in seconds

        Returns:
            Summary dict with success/failure counts
        """
        success_count = 0
        failed = []

        for i, bookmark in enumerate(bookmarks):
            try:
                result = await self.save_bookmark(**bookmark)

                if isinstance(result, dict) and "error" not in result:
                    success_count += 1
                else:
                    failed.append(
                        {
                            "index": i,
                            "url": bookmark.get("url"),
                            "error": result.get("error", "Unknown error"),
                        }
                    )

                # Rate limiting delay
                if i < len(bookmarks) - 1:
                    await asyncio.sleep(delay)

            except Exception as e:
                failed.append({"index": i, "url": bookmark.get("url"), "error": str(e)})

        return {
            "total": len(bookmarks),
            "success": success_count,
            "failed": len(failed),
            "failures": failed,
        }
