import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


class Config:
    """Configuration for Diigo MCP Server"""

    # Required credentials
    DIIGO_USERNAME = os.getenv("DIIGO_USERNAME")
    DIIGO_PASSWORD = os.getenv("DIIGO_PASSWORD")
    DIIGO_API_KEY = os.getenv("DIIGO_API_KEY")

    # API configuration
    DIIGO_BASE_URL = os.getenv("DIIGO_BASE_URL", "https://secure.diigo.com/api/v2")

    # Request configuration
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
    MAX_BOOKMARKS_PER_REQUEST = int(os.getenv("MAX_BOOKMARKS_PER_REQUEST", "100"))

    # Retry configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "2"))

    # Cache configuration
    CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))

    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        required = [
            ("DIIGO_USERNAME", cls.DIIGO_USERNAME),
            ("DIIGO_PASSWORD", cls.DIIGO_PASSWORD),
            ("DIIGO_API_KEY", cls.DIIGO_API_KEY),
        ]

        missing = [name for name, value in required if not value]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please set them in your environment or .env file.\n"
                f"Get your API key at: https://www.diigo.com/api_keys/new/"
            )

    @classmethod
    def get_default_user(cls):
        """Get the configured username (default user for operations)"""
        return cls.DIIGO_USERNAME
