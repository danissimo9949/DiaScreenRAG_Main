"""
Utilities for RAG API communication with retry logic
"""
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def create_retry_session(
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: Optional[list] = None,
    timeout: int = 60
) -> requests.Session:
    """
    Create a requests session with retry logic and exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff delay
        status_forcelist: HTTP status codes that should trigger a retry
        timeout: Request timeout in seconds
    
    Returns:
        Configured requests.Session with retry adapter
    """
    if status_forcelist is None:
        status_forcelist = [500, 502, 503, 504, 429]
    
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST"],
        raise_on_status=False
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def call_rag_api_with_retry(
    url: str,
    method: str = "GET",
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    timeout: int = 60,
    **kwargs
) -> Tuple[Optional[requests.Response], Optional[Exception]]:
    """
    Call RAG API with retry logic and exponential backoff.
    
    Args:
        url: API endpoint URL
        method: HTTP method ('GET' or 'POST')
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff delay
        timeout: Request timeout in seconds
        **kwargs: Additional arguments to pass to requests (params, json, etc.)
    
    Returns:
        Tuple of (Response object or None, Exception or None)
    """
    session = create_retry_session(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        timeout=timeout
    )
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if method.upper() == "POST":
                response = session.post(url, timeout=timeout, **kwargs)
            else:
                response = session.get(url, timeout=timeout, **kwargs)
            
            if response.status_code < 500 or attempt == max_retries:
                return response, None
            
            logger.warning(
                f"RAG API request failed with status {response.status_code} "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )
            
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            
        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                logger.warning(
                    f"RAG API request timeout (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {delay:.2f} seconds..."
                )
                time.sleep(delay)
            else:
                logger.error(f"RAG API request failed after {max_retries + 1} attempts: {e}")
                
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                logger.warning(
                    f"RAG API connection error (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {delay:.2f} seconds..."
                )
                time.sleep(delay)
            else:
                logger.error(f"RAG API connection failed after {max_retries + 1} attempts: {e}")
                
        except requests.exceptions.RequestException as e:
            last_exception = e
            logger.error(f"RAG API request error (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                time.sleep(delay)
    
    return None, last_exception

