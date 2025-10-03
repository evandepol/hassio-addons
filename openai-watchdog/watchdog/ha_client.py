"""
Home Assistant API client for state monitoring
"""

import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class HomeAssistantClient:
    """Client for interacting with Home Assistant API"""
    
    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token
        self.session = None
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    async def _get_session(self):
        """Get or create HTTP session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def get_current_state(self, scope: List[str] = None) -> Dict[str, Any]:
        """Get current state of all entities or filtered by scope"""
        try:
            session = await self._get_session()
            async with session.get(f'{self.url}/api/states', headers=self.headers) as response:
                if response.status == 200:
                    entities = await response.json()
                    
                    # Filter by monitoring scope if provided
                    if scope:
                        filtered = self._filter_entities_by_scope(entities, scope)
                        return {entity['entity_id']: entity for entity in filtered}
                    
                    return {entity['entity_id']: entity for entity in entities}
                else:
                    logger.error(f"Failed to get states: {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error getting current state: {e}")
            return {}
    
    async def get_recent_changes(self, since: Optional[datetime] = None, scope: List[str] = None) -> List[Dict]:
        """Get recent state changes from history"""
        if since is None:
            from datetime import timezone
            since = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        try:
            # Deterministic approach: always query with filter_entity_id in chunks
            session = await self._get_session()
            from datetime import timezone
            since_iso = since.astimezone(timezone.utc).replace(microsecond=0).isoformat()
            now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

            # Determine scoped entities
            states = await self.get_current_state(scope)
            entity_ids = list(states.keys())
            if not entity_ids:
                return []

            CHUNK_SIZE = 150
            aggregated_history: List[List[Dict]] = []
            for i in range(0, len(entity_ids), CHUNK_SIZE):
                chunk = entity_ids[i:i+CHUNK_SIZE]
                chunk_params = {
                    'start_time': since_iso,
                    'end_time': now_iso,
                    'minimal_response': '1',
                    'filter_entity_id': ','.join(chunk)
                }
                async with session.get(
                    f'{self.url}/api/history/period',
                    headers=self.headers,
                    params=chunk_params
                ) as chunk_resp:
                    if chunk_resp.status == 200:
                        chunk_hist = await chunk_resp.json()
                        aggregated_history.extend(chunk_hist)
                    else:
                        chunk_txt = await chunk_resp.text()
                        logger.warning(
                            f"History chunk failed: {chunk_resp.status} for {len(chunk)} entities; {chunk_txt[:120]}"
                        )

            if not aggregated_history:
                return []

            changes = self._extract_changes_from_history(aggregated_history, scope)
            logger.debug(
                f"History query: {len(changes)} changes from {len(entity_ids)} entities in {((len(entity_ids)-1)//CHUNK_SIZE)+1} calls"
            )
            return changes
        except Exception as e:
            logger.error(f"Error getting recent changes: {e}")
            return []
    
    def _filter_entities_by_scope(self, entities: List[Dict], scope: List[str]) -> List[Dict]:
        """Filter entities based on monitoring scope"""
        if not scope:
            return entities
        
        # If patterns analysis is requested, include all entities
        if 'patterns' in scope:
            return entities
        
        filtered = []
        for entity in entities:
            entity_id = entity.get('entity_id', '')
            domain = entity_id.split('.')[0] if '.' in entity_id else ''
            
            # Map scope to domains
            if 'climate' in scope and domain in ['climate', 'weather', 'sensor']:
                if any(keyword in entity_id.lower() for keyword in ['temperature', 'humidity', 'climate', 'thermostat']):
                    filtered.append(entity)
            
            if 'security' in scope and domain in ['binary_sensor', 'alarm_control_panel', 'lock', 'camera']:
                if any(keyword in entity_id.lower() for keyword in ['door', 'window', 'motion', 'alarm', 'lock', 'security']):
                    filtered.append(entity)
            
            if 'energy' in scope and domain in ['sensor', 'switch', 'light']:
                if any(keyword in entity_id.lower() for keyword in ['power', 'energy', 'consumption', 'watt']):
                    filtered.append(entity)
            
            if 'automation_performance' in scope and domain in ['automation', 'script']:
                filtered.append(entity)
            
            if 'device_health' in scope and domain in ['sensor', 'binary_sensor']:
                filtered.append(entity)
        
        # If filtering produced no entities, fall back to all to avoid empty baseline
        return filtered if filtered else entities
    
    def _extract_changes_from_history(self, history: List[List[Dict]], scope: List[str] = None) -> List[Dict]:
        """Extract meaningful changes from history data"""
        changes = []
        
        for entity_history in history:
            if not entity_history:
                continue
                
            entity_id = entity_history[0].get('entity_id', '')
            
            # Skip if not in monitoring scope
            if scope and not self._entity_in_scope(entity_id, scope):
                continue
            
            # Look for state changes
            for i in range(1, len(entity_history)):
                prev_state = entity_history[i-1]
                curr_state = entity_history[i]
                
                if prev_state.get('state') != curr_state.get('state'):
                    changes.append({
                        'entity_id': entity_id,
                        'old_state': prev_state.get('state'),
                        'new_state': curr_state.get('state'),
                        'last_changed': curr_state.get('last_changed'),
                        'attributes': curr_state.get('attributes', {}),
                        'domain': entity_id.split('.')[0] if '.' in entity_id else ''
                    })
        
        return changes
    
    def _entity_in_scope(self, entity_id: str, scope: List[str]) -> bool:
        """Check if entity is in monitoring scope"""
        domain = entity_id.split('.')[0] if '.' in entity_id else ''
        
        scope_domains = {
            'climate': ['climate', 'weather', 'sensor'],
            'security': ['binary_sensor', 'alarm_control_panel', 'lock', 'camera'],
            'energy': ['sensor', 'switch', 'light'],
            'automation_performance': ['automation', 'script'],
            'device_health': ['sensor', 'binary_sensor'],
            'patterns': ['*']  # All entities for pattern analysis
        }
        
        for scope_item in scope:
            if scope_item in scope_domains:
                if '*' in scope_domains[scope_item] or domain in scope_domains[scope_item]:
                    return True
        
        return False
    
    async def send_notification(self, service: str, message: str, title: str = "OpenAI Watchdog", **kwargs):
        """Send notification through Home Assistant"""
        try:
            session = await self._get_session()
            # Normalize service string into (domain, name)
            domain = None
            name = None
            svc = (service or '').strip()
            if not svc:
                logger.error("Notification service not provided")
                return False

            # Persistent notification is special: domain=persistent_notification, service=create
            if svc == 'persistent_notification':
                domain = 'persistent_notification'
                name = 'create'
                payload = {
                    'message': message,
                    'title': title
                }
                if 'notification_id' in kwargs and kwargs['notification_id']:
                    payload['notification_id'] = kwargs['notification_id']
            else:
                if '.' in svc:
                    domain, name = svc.split('.', 1)
                else:
                    # Assume notify domain if only a target name is provided
                    domain, name = 'notify', svc

                payload = {
                    'message': message,
                    'title': title,
                    **kwargs
                }

            endpoint = f'{self.url}/api/services/{domain}/{name}'

            async with session.post(
                endpoint,
                headers=self.headers,
                json=payload
            ) as response:
                if response.status == 200:
                    logger.info(f"Notification sent via {service}")
                    return True
                else:
                    body = await response.text()
                    logger.error(f"Failed to send notification via {service}: {response.status} - {body[:200]}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False