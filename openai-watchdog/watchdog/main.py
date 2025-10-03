#!/usr/bin/env python3
"""
OpenAI Watchdog - Intelligent Home Assistant Monitoring
Main monitoring service that runs continuously
"""

import asyncio
import os
import sys
import signal
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from watchdog_monitor import WatchdogMonitor
from ha_client import HomeAssistantClient
from openai_analyzer import OpenAIAnalyzer
from cost_tracker import CostTracker
from insight_manager import InsightManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class OpenAIWatchdogService:
    """Main service class for OpenAI Watchdog"""
    
    def __init__(self):
        self.running = False
        self.monitor = None
        self.ha_client = None
        self.openai_analyzer = None
        self.cost_tracker = None
        self.insight_manager = None
        
        # Load configuration from environment
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            'check_interval': int(os.getenv('WATCHDOG_CHECK_INTERVAL', '30')),
            'insight_threshold': float(os.getenv('WATCHDOG_INSIGHT_THRESHOLD', '0.8')),
            'max_daily_calls': int(os.getenv('WATCHDOG_MAX_DAILY_CALLS', '1000')),
            'cost_limit': float(os.getenv('WATCHDOG_COST_LIMIT', '1.00')),
            'enable_learning': os.getenv('WATCHDOG_ENABLE_LEARNING', 'true').lower() == 'true',
            'notify_on_any_insight': os.getenv('WATCHDOG_NOTIFY_ON_ANY_INSIGHT', 'false').lower() == 'true',
            'monitoring_scope': self._parse_monitoring_scope(),
            'notification_service': os.getenv('WATCHDOG_NOTIFICATION_SERVICE', 'persistent_notification'),
            'data_dir': os.getenv('OPENAI_WATCHDOG_DATA', '/config/openai-watchdog'),
            'ha_url': os.getenv('HA_URL', 'http://supervisor/core'),
            'ha_token': os.getenv('HASSIO_TOKEN', '')
        }
    
    def _parse_monitoring_scope(self) -> List[str]:
        """Parse monitoring scope. Accepts single string like 'all' or a list-json string."""
        raw = os.getenv('WATCHDOG_MONITORING_SCOPE', 'all').strip().lower()
        if raw == 'all' or raw == '' or raw == 'true':
            return [
                'climate', 'security', 'energy',
                'automation_performance', 'device_health', 'patterns'
            ]
        # Try JSON list
        try:
            import json
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                parsed_lower = [str(x).lower() for x in parsed]
                if 'all' in parsed_lower:
                    return [
                        'climate', 'security', 'energy',
                        'automation_performance', 'device_health', 'patterns'
                    ]
                return parsed_lower
        except Exception:
            pass
        # Try comma-separated list from UI edge cases
        if ',' in raw:
            return [x.strip() for x in raw.split(',') if x.strip()]
        # Otherwise treat as single category
        return [raw]
    
    async def initialize(self):
        """Initialize all service components"""
        logger.info("Initializing OpenAI Watchdog components...")
        
        try:
            # Initialize Home Assistant client
            self.ha_client = HomeAssistantClient(
                url=self.config['ha_url'],
                token=self.config['ha_token']
            )
            
            # Initialize OpenAI analyzer
            self.openai_analyzer = OpenAIAnalyzer(
                model=self.config['model'],
                insight_threshold=self.config['insight_threshold']
            )
            
            # Initialize cost tracker
            self.cost_tracker = CostTracker(
                data_dir=self.config['data_dir'],
                daily_limit=self.config['cost_limit'],
                max_calls=self.config['max_daily_calls']
            )
            
            # Initialize insight manager
            self.insight_manager = InsightManager(
                data_dir=self.config['data_dir'],
                ha_client=self.ha_client,
                notification_service=self.config['notification_service']
            )
            
            # Initialize main monitor
            self.monitor = WatchdogMonitor(
                ha_client=self.ha_client,
                openai_analyzer=self.openai_analyzer,
                cost_tracker=self.cost_tracker,
                insight_manager=self.insight_manager,
                config=self.config
            )
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def start(self):
        """Start the monitoring service"""
        logger.info("Starting OpenAI Watchdog monitoring service...")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.running = True
        
        try:
            await self.initialize()
            await self.monitor.start_monitoring()
            
        except Exception as e:
            logger.error(f"Service error: {e}")
            self.running = False
            raise
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def stop(self):
        """Stop the monitoring service"""
        logger.info("Stopping OpenAI Watchdog service...")
        self.running = False
        
        if self.monitor:
            await self.monitor.stop_monitoring()

# Service entry point
async def main():
    """Main entry point for the service"""
    service = OpenAIWatchdogService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)
    finally:
        await service.stop()

if __name__ == "__main__":
    asyncio.run(main())