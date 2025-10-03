"""
Local LLM server lifecycle management (placeholder minimal manager).

This module is responsible for ensuring a local OpenAI-compatible endpoint
is running when enabled. In this initial version, we only provide a health
check utility; process management can be added later.
"""

import asyncio
import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class LocalServerManager:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv('WATCHDOG_LOCAL_BASE_URL', '').strip()

    async def is_healthy(self) -> bool:
        url = (self.base_url or '').rstrip('/') + '/v1/models'
        if not self.base_url:
            return False
        try:
            timeout = aiohttp.ClientTimeout(total=1.5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    return resp.status == 200
        except Exception:
            return False
