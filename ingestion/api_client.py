"""HTTP client with retry, backoff, timeout, and local file caching."""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from config import settings

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class OpenF1Client:
    """Robust client for fetching Formula 1 data from OpenF1 API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = settings.REQUEST_TIMEOUT_SECONDS,
        max_retries: int = settings.MAX_RETRIES,
        backoff_factor: float = settings.BACKOFF_FACTOR,
        cache_dir: Optional[Path] = None,
    ):
        self.base_url = (base_url or settings.OPENF1_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.cache_dir = cache_dir or settings.RAW_DATA_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Setup requests session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        cache_filename: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch records from OpenF1 endpoint.

        Args:
            endpoint: API endpoint path (e.g. 'sessions', 'laps', 'car_data')
            params: Query parameters dictionary
            use_cache: If True, read/write from local cache file
            cache_filename: Custom cache filename; if None, derived automatically

        Returns:
            List of dictionary records returned by the API.
        """
        endpoint_clean = endpoint.strip("/")
        params = params or {}

        # Resolve cache file path if caching enabled
        cache_path = None
        if use_cache:
            if cache_filename:
                cache_path = self.cache_dir / cache_filename
            else:
                # Build deterministic filename from endpoint and sorted params
                param_str = "_".join(f"{k}-{v}" for k, v in sorted(params.items()))
                cache_name = f"{endpoint_clean}_{param_str}.json" if param_str else f"{endpoint_clean}.json"
                # Clean invalid filename characters
                safe_cache_name = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in cache_name)
                cache_path = self.cache_dir / safe_cache_name

            if cache_path.exists():
                logger.info(f"Loading cached response from {cache_path}")
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return data
                except Exception as err:
                    logger.warning(f"Failed to read cache file {cache_path}: {err}. Refetching from API.")

        url = f"{self.base_url}/{endpoint_clean}"
        logger.info(f"Fetching from OpenF1 API: {url} with params={params}")

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                if isinstance(data, dict):
                    data = [data]
                else:
                    data = []

            # Save to disk cache if enabled
            if use_cache and cache_path:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Saved {len(data)} records to cache at {cache_path}")

            return data

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred while querying {url}: {http_err}")
            raise
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred while querying {url}: {conn_err}")
            raise
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout occurred while querying {url}: {timeout_err}")
            raise
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to parse JSON response from {url}: {json_err}")
            raise
        except Exception as err:
            logger.error(f"Unexpected error querying {url}: {err}")
            raise
