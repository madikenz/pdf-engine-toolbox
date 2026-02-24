"""Service for downloading PDFs from presigned S3 URLs."""

import structlog
import httpx

from app.config import settings
from app.utils.errors import DownloadFailedError

log = structlog.get_logger()


async def download_pdf(url: str) -> bytes:
    """Download a PDF from a presigned S3 URL.

    Args:
        url: Presigned S3 GET URL

    Returns:
        PDF file content as bytes

    Raises:
        DownloadFailedError: If download fails
    """
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            content = response.content
            log.info("pdf_downloaded", size_bytes=len(content))
            return content

    except httpx.TimeoutException:
        raise DownloadFailedError("Timeout downloading PDF from source URL")
    except httpx.HTTPStatusError as e:
        raise DownloadFailedError(f"HTTP {e.response.status_code} downloading PDF")
    except httpx.RequestError as e:
        raise DownloadFailedError(f"Network error downloading PDF: {e}")
