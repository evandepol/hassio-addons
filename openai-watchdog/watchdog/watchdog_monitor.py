"""
Core monitoring loop and state management
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class WatchdogMonitor:
    """Main monitoring service that coordinates all watchdog activities"""
    
    def __init__(self, ha_client, openai_analyzer, cost_tracker, insight_manager, config, provider_policy=None):
        self.ha_client = ha_client
        self.openai_analyzer = openai_analyzer
        self.cost_tracker = cost_tracker
        self.insight_manager = insight_manager
        self.config = config
        self.provider_policy = provider_policy
        
        self.running = False
        self.state_buffer = StateBuffer(max_size=1000)
        self.last_check = None
        
    async def start_monitoring(self):
        """Start the main monitoring loop"""
        logger.info("Starting monitoring loop...")
        self.running = True
        
        # Initialize baseline state
        await self._establish_baseline()
        
        # Start monitoring loop
        while self.running:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(self.config['check_interval'])
                
            except Exception as e:
                logger.error(f"Monitoring cycle error: {e}")
                await asyncio.sleep(self.config['check_interval'])
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        logger.info("Stopping monitoring loop...")
        self.running = False
    
    async def _monitoring_cycle(self):
        """Execute one monitoring cycle"""
        cycle_start = datetime.now(timezone.utc)
        
        # Check if we're within cost/API limits
        if not self.cost_tracker.can_make_request():
            logger.warning("Daily cost/API limit reached, skipping cycle")
            return
        
        # Get recent state changes from Home Assistant
        changes = await self.ha_client.get_recent_changes(
            since=self.last_check,
            scope=self.config['monitoring_scope']
        )
        
        if not changes:
            logger.debug("No state changes detected")
            self.last_check = cycle_start
            return
        
        # Add changes to state buffer
        self.state_buffer.add_changes(changes)
        
        # Choose provider (mock/local/online) per cycle
        provider = None
        local_base_url = None
        try:
            if self.provider_policy is not None:
                provider, local_base_url = self.provider_policy.choose_provider(self.openai_analyzer, self.cost_tracker)
                logger.info(f"Provider selected (desired): {provider or 'online'}" + (f" (local_base_url={local_base_url})" if provider == 'local' else ""))
        except Exception as e:
            logger.warning(f"Provider selection failed: {e}")
            provider, local_base_url = None, None

        # Analyze changes with selected provider
        analysis = await self.openai_analyzer.analyze_changes(
            changes=changes,
            context=self.state_buffer.get_context(),
            monitoring_scope=self.config['monitoring_scope'],
            provider=provider,
            local_base_url=local_base_url
        )

        # Reflect the actual provider used (after possible fallback)
        try:
            actual_provider = analysis.get('provider', provider or 'online')
            self.config['last_provider'] = actual_provider
            if actual_provider == 'local':
                self.config['last_local_base_url'] = local_base_url
        except Exception:
            pass
        
        # Track API cost
        self.cost_tracker.record_request(analysis.get('cost_info', {}))
        
        # Process any insights or alerts
        if analysis.get('requires_attention', False):
            await self.insight_manager.process_insight(analysis)
        elif self.config.get('notify_on_any_insight', False) and analysis.get('insights'):
            # Lower-severity informational notification when opted-in
            safe_analysis = dict(analysis)
            safe_analysis['requires_attention'] = False
            await self.insight_manager.process_insight(safe_analysis)
        
        # Update learning patterns if enabled
        if self.config['enable_learning']:
            await self._update_patterns(changes, analysis)
        
        self.last_check = cycle_start
        logger.debug(f"Monitoring cycle completed in {datetime.now(timezone.utc) - cycle_start}")
    
    async def _establish_baseline(self):
        """Establish baseline state for monitoring"""
        logger.info("Establishing baseline state...")
        
        try:
            # Get current state of all monitored entities
            current_state = await self.ha_client.get_current_state(
                scope=self.config['monitoring_scope']
            )
            
            self.state_buffer.set_baseline(current_state)
            self.last_check = datetime.now(timezone.utc)
            
            logger.info(f"Baseline established with {len(current_state)} entities")
            
        except Exception as e:
            logger.error(f"Failed to establish baseline: {e}")
            raise
    
    async def _update_patterns(self, changes: List[Dict], analysis: Dict):
        """Update learned patterns based on analysis"""
        # TODO: Implement pattern learning
        # This would update stored patterns based on observed behavior
        pass

class StateBuffer:
    """Buffer to store recent state changes for context"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.changes = []
        self.baseline = {}
    
    def add_changes(self, changes: List[Dict]):
        """Add new state changes to buffer"""
        self.changes.extend(changes)
        
        # Trim buffer if it exceeds max size
        if len(self.changes) > self.max_size:
            self.changes = self.changes[-self.max_size:]
    
    def set_baseline(self, state: Dict):
        """Set baseline state"""
        self.baseline = state
    
    def get_context(self, lookback_minutes: int = 60) -> Dict:
        """Get recent context for analysis"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        recent_changes = []
        for change in self.changes:
            ts = change.get('last_changed', '')
            if not ts:
                continue
            try:
                # Normalize 'Z' suffix and parse
                ts_norm = ts.replace('Z', '+00:00')
                dt = datetime.fromisoformat(ts_norm)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if dt > cutoff:
                recent_changes.append(change)
        
        return {
            'baseline': self.baseline,
            'recent_changes': recent_changes,
            'change_count': len(recent_changes),
            'buffer_size': len(self.changes)
        }