"""
Provider selection policy for three-tier analysis fidelity:
- mock (always available, zero cost)
- local (CPU local model via OpenAI-compatible endpoint)
- online (OpenAI API)
"""

import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ProviderPolicy:
    """Decides which provider to use for a given cycle.

    Inputs considered:
    - Mode (auto, online_only, local_first, mock_only)
    - Daily budget/request limit (from cost tracker)
    - Analyzer backoff state (online rate limiting)
    - Local enable flag and system load threshold
    - Local base URL availability
    """

    def __init__(self):
        # Read configuration from environment (single source via add-on UI)
        self.mode = os.getenv('WATCHDOG_MODE', 'auto').strip().lower()
        self.local_enabled = os.getenv('WATCHDOG_LOCAL_ENABLED', 'false').lower() == 'true'
        self.local_base_url = os.getenv('WATCHDOG_LOCAL_BASE_URL', '').strip()
        self.local_max_cpu_load = float(os.getenv('WATCHDOG_LOCAL_MAX_CPU_LOAD', '1.5'))

    def choose_provider(self, analyzer, cost_tracker) -> Tuple[str, Optional[str]]:
        """Return (provider, base_url) where provider in {'mock','local','online'}.

        base_url is only relevant when provider == 'local'.
        """
        mode = self.mode
        online_allowed = cost_tracker.can_make_request() and not analyzer._is_in_backoff()
        # Reload dynamic base URL if run.sh started an embedded server
        dyn_base = os.getenv('WATCHDOG_LOCAL_BASE_URL', '').strip()
        if dyn_base and dyn_base != self.local_base_url:
            self.local_base_url = dyn_base
        local_ok = self._local_available()

        # Mode overrides
        if mode == 'mock_only':
            return 'mock', None
        if mode == 'online_only':
            return ('online', None) if online_allowed else ('mock', None)
        if mode == 'local_first':
            if local_ok:
                return 'local', self.local_base_url or None
            return ('online', None) if online_allowed else ('mock', None)

        # Default: auto
        if online_allowed:
            return 'online', None
        if local_ok:
            return 'local', self.local_base_url or None
        return 'mock', None

    def _local_available(self) -> bool:
        if not self.local_enabled:
            return False
        if not self.local_base_url:
            # If embedded server was started, run.sh will set WATCHDOG_LOCAL_BASE_URL; otherwise, local is unavailable
            return False
        try:
            load1, _, _ = os.getloadavg()
            if load1 > self.local_max_cpu_load:
                logger.info(f"Skipping local model due to loadavg={load1:.2f} > threshold {self.local_max_cpu_load:.2f}")
                return False
        except Exception:
            # If load cannot be read, be conservative and allow
            pass
        return True
