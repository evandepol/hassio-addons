"""
OpenAI analysis engine for interpreting Home Assistant state changes
"""

import os
import json
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
try:
    # Local mock utilities
    from .mock_analysis import mock_openai_analysis
except Exception:
    mock_openai_analysis = None

logger = logging.getLogger(__name__)

# OpenAI model pricing per 1k tokens (input/output)
OPENAI_PRICING = {
    'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
    'gpt-4o': {'input': 0.0025, 'output': 0.01},
    'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015}
}

class OpenAIAnalyzer:
    """OpenAI-powered analysis engine for Home Assistant monitoring"""
    
    def __init__(self, model: str = "gpt-4o-mini", insight_threshold: float = 0.8):
        self.model = model
        self.insight_threshold = insight_threshold
        self.client = None
        self.api_key: Optional[str] = None
        self._client_cache: Dict[str, Any] = {}
        # API audit log path
        self.data_dir = os.getenv('OPENAI_WATCHDOG_DATA', '/config/openai-watchdog')
        self.api_log_path = os.path.join(self.data_dir, 'logs', 'openai_api.log')
        self.log_api_stdout = (os.getenv('WATCHDOG_LOG_API_STDOUT', 'false').lower() == 'true')
        # Backoff state for rate limits/errors
        self.backoff_until: Optional[datetime] = None
        self.backoff_seconds: int = int(os.getenv('WATCHDOG_BACKOFF_INITIAL_SECONDS', '60'))
        self.backoff_max_seconds: int = int(os.getenv('WATCHDOG_BACKOFF_MAX_SECONDS', '7200'))
        try:
            os.makedirs(os.path.dirname(self.api_log_path), exist_ok=True)
        except Exception:
            pass
        self._initialize_client()
        
        
        # Analysis templates for different monitoring types
        self.analysis_templates = {
            'climate': self._get_climate_template(),
            'security': self._get_security_template(),
            'energy': self._get_energy_template(),
            'automation_performance': self._get_automation_template(),
            'device_health': self._get_device_health_template(),
            'patterns': self._get_pattern_template()
        }
    
    def _initialize_client(self):
        """Initialize OpenAI client with API key"""
        if AsyncOpenAI is None:
            logger.error("OpenAI package not installed")
            return
            
        # Try to get API key from various sources
        api_key = self._get_api_key()
        self.api_key = api_key
        if not api_key:
            logger.error("No OpenAI API key found")
            return
            
        try:
            base_url = os.getenv('OPENAI_BASE_URL')
            if base_url:
                self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                logger.info(f"Initialized OpenAI client with model: {self.model} (base_url={base_url})")
            else:
                self.client = AsyncOpenAI(api_key=api_key)
            logger.info(f"Initialized OpenAI client with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    
    def _get_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment variable (set by Home Assistant configuration)"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("No OpenAI API key found in configuration")
            logger.warning("Please set 'openai_api_key' in the Home Assistant add-on configuration")
        return api_key
    
    async def analyze_changes(self, changes: List[Dict], context: Dict, monitoring_scope: List[str], provider: Optional[str] = None, local_base_url: Optional[str] = None) -> Dict[str, Any]:
        """Analyze state changes and return insights"""
        if not changes:
            return {'requires_attention': False, 'insights': []}

        # Provider override: explicit mock
        if provider == 'mock':
            if mock_openai_analysis is not None:
                mock_result = await mock_openai_analysis(self.model, changes)
            else:
                mock_result = {'requires_attention': False, 'insights': [], 'confidence': 0.7, 'processed_changes': len(changes), 'cost_info': {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}}
            # annotate provider tier
            try:
                mock_result['provider'] = 'mock'
            except Exception:
                pass
            self._log_api_call(
                prompt="[TIER=mock] Using mock analysis",
                response_text=json.dumps(mock_result) if isinstance(mock_result, dict) else str(mock_result),
                usage=None,
                cost_info={'model': self.model, 'estimated_cost': 0.0, 'note': 'tier-mock', 'provider': 'mock', 'success': True}
            )
            try:
                mock_result['cost_info'] = {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0, 'note': 'tier-mock', 'provider': 'mock', 'success': True}
            except Exception:
                pass
            return mock_result
        
        # If we're in a backoff window, skip real API calls and use mock
        if provider != 'local' and self._is_in_backoff():
            remaining = int((self.backoff_until - datetime.utcnow()).total_seconds()) if self.backoff_until else 0
            if mock_openai_analysis is not None:
                mock_result = await mock_openai_analysis(self.model, changes)
            else:
                mock_result = {'requires_attention': False, 'insights': [], 'confidence': 0.7, 'processed_changes': len(changes), 'cost_info': {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}}
            # Insert a rate limit/backoff informational insight
            try:
                mock_result.setdefault('insights', []).insert(0, {
                    'type': 'rate_limit',
                    'message': f'OpenAI calls paused due to backoff. Resuming in ~{remaining}s.',
                    'confidence': 0.95
                })
            except Exception:
                pass
            mock_result['requires_attention'] = mock_result.get('requires_attention', False)
            self._log_api_call(
                prompt="[BACKOFF] Skipping OpenAI call; using mock analysis",
                response_text=json.dumps(mock_result) if isinstance(mock_result, dict) else str(mock_result),
                usage=None,
                cost_info={'model': self.model, 'estimated_cost': 0.0, 'note': 'backoff-mock', 'provider': 'mock', 'success': True}
            )
            try:
                mock_result['cost_info'] = {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0, 'note': 'backoff-mock', 'provider': 'mock', 'success': True}
            except Exception:
                pass
            return mock_result

        if not self.client and provider != 'local':
            logger.warning("OpenAI client not initialized, using mock analysis")
            if mock_openai_analysis is not None:
                mock_result = await mock_openai_analysis(self.model, changes)
            else:
                mock_result = {'requires_attention': False, 'insights': [], 'confidence': 0.7, 'processed_changes': len(changes), 'cost_info': {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}}
            # Log mock call for visibility
            self._log_api_call(
                prompt="[MOCK] No API key/client; generated mock analysis based on changes",
                response_text=json.dumps(mock_result) if isinstance(mock_result, dict) else str(mock_result),
                usage=None,
                cost_info={'model': self.model, 'estimated_cost': 0.0, 'note': 'mock', 'provider': 'mock', 'success': True}
            )
            try:
                mock_result['cost_info'] = {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0, 'note': 'mock', 'provider': 'mock', 'success': True}
            except Exception:
                pass
            return mock_result
        
        try:
            # Build analysis prompt based on scope and changes
            prompt = self._build_analysis_prompt(changes, context, monitoring_scope)
            logger.debug("OpenAI prompt (model=%s): %s", self.model, prompt)
            
            # Select client based on provider
            client = self.client
            provider_used = 'online'
            if provider == 'local':
                if local_base_url:
                    client = self._get_or_create_client(local_base_url)
                    provider_used = 'local'
                else:
                    logger.warning("Provider 'local' selected but no local_base_url provided; falling back to mock")
                    if mock_openai_analysis is not None:
                        mock_result = await mock_openai_analysis(self.model, changes)
                    else:
                        mock_result = {'requires_attention': False, 'insights': [], 'confidence': 0.7, 'processed_changes': len(changes), 'cost_info': {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}}
                    try:
                        mock_result['provider'] = 'mock'
                    except Exception:
                        pass
                    self._log_api_call(
                        prompt="[TIER=local] Missing local_base_url; using mock",
                        response_text=json.dumps(mock_result) if isinstance(mock_result, dict) else str(mock_result),
                        usage=None,
                        cost_info={'model': self.model, 'estimated_cost': 0.0, 'note': 'tier-local-missing-url', 'provider': 'mock', 'success': True}
                    )
                    try:
                        mock_result['cost_info'] = {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0, 'note': 'tier-local-missing-url', 'provider': 'mock', 'success': True}
                    except Exception:
                        pass
                    return mock_result

            # Make OpenAI API call
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intelligent Home Assistant monitoring system. Analyze state changes and provide structured insights in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # Extract response and usage info
            analysis_text = response.choices[0].message.content
            usage = getattr(response, 'usage', None)
            # Calculate cost
            if usage is not None and hasattr(usage, 'prompt_tokens'):
                cost_info = self._calculate_cost(usage)
                cost_info['success'] = True
            else:
                note = 'tier-local' if provider == 'local' else 'tier-online'
                cost_info = {
                    'model': self.model,
                    'estimated_tokens': 0,
                    'estimated_cost': 0.0,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'input_cost': 0.0,
                    'output_cost': 0.0,
                    'note': note,
                    'provider': provider_used,
                    'success': True
                }
            
            # Process and structure the response
            structured_result = self._structure_analysis(analysis_text, changes)
            try:
                structured_result['provider'] = provider_used
            except Exception:
                pass
            structured_result['cost_info'] = cost_info
            
            # Log API call (prompt + response + usage/cost)
            self._log_api_call(
                prompt=prompt,
                response_text=analysis_text,
                usage=usage,
                cost_info={**cost_info, 'provider': provider_used}
            )
            
            return structured_result
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Fallback to mock analysis
            if mock_openai_analysis is not None:
                mock_result = await mock_openai_analysis(self.model, changes)
            else:
                mock_result = {'requires_attention': False, 'insights': [], 'confidence': 0.7, 'processed_changes': len(changes), 'cost_info': {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}}
            try:
                mock_result['provider'] = 'mock'
            except Exception:
                pass
            # If unauthorized, attach a clear insight message
            try:
                msg = str(e)
                if '401' in msg or 'invalid_api_key' in msg or 'Incorrect API key' in msg:
                    mock_result.setdefault('insights', []).insert(0, {
                        'type': 'configuration',
                        'message': 'OpenAI authorization failed (401). Please verify your API key in the add-on configuration.',
                        'confidence': 0.99
                    })
                    mock_result['requires_attention'] = True
                # Rate limit handling (429 / rate_limit_exceeded): apply backoff
                if provider != 'local' and ('429' in msg or 'rate_limit_exceeded' in msg or 'Rate limit' in msg):
                    wait_s = self._parse_wait_seconds(msg) or self.backoff_seconds
                    self._apply_backoff(wait_s)
                    resume_in = int((self.backoff_until - datetime.utcnow()).total_seconds()) if self.backoff_until else wait_s
                    mock_result.setdefault('insights', []).insert(0, {
                        'type': 'rate_limit',
                        'message': f'OpenAI rate limit reached. Pausing real analysis for ~{resume_in}s.',
                        'confidence': 0.9
                    })
            except Exception:
                pass
            self._log_api_call(
                prompt="[MOCK-FALLBACK] OpenAI API error; generated mock analysis",
                response_text=json.dumps(mock_result) if isinstance(mock_result, dict) else str(mock_result),
                usage=None,
                cost_info={'model': self.model, 'estimated_cost': 0.0, 'note': 'mock-fallback', 'provider': 'mock', 'success': False}
            )
            try:
                mock_result['cost_info'] = {'model': self.model, 'estimated_tokens': 0, 'estimated_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0, 'note': 'mock-fallback', 'provider': 'mock', 'success': False}
            except Exception:
                pass
            return mock_result

    def _get_or_create_client(self, base_url: str):
        if AsyncOpenAI is None:
            return None
        key = base_url.strip()
        if key in self._client_cache:
            return self._client_cache[key]
        # Use configured API key if present; local servers typically ignore it
        api_key = self.api_key or os.getenv('OPENAI_API_KEY') or 'local'
        try:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            self._client_cache[key] = client
            return client
        except Exception as e:
            logger.error(f"Failed to create local client for {base_url}: {e}")
            return self.client

    def _is_in_backoff(self) -> bool:
        try:
            return self.backoff_until is not None and datetime.utcnow() < self.backoff_until
        except Exception:
            return False

    def _apply_backoff(self, seconds: int):
        try:
            seconds = max(1, int(seconds))
        except Exception:
            seconds = self.backoff_seconds
        self.backoff_until = datetime.utcnow() + timedelta(seconds=seconds)
        # Exponential backoff for next time, up to cap
        self.backoff_seconds = min(self.backoff_seconds * 2, self.backoff_max_seconds)
        logger.warning(f"Applying backoff for {seconds}s (next backoff step {self.backoff_seconds}s, until {self.backoff_until} UTC)")

    def _parse_wait_seconds(self, message: str) -> Optional[int]:
        """Parse 'try again in 3h20m0.959s' style hints from error text to seconds."""
        try:
            # Look for patterns like 'in 3h20m0.959s' or 'in 15m30s' or 'in 45s'
            m = re.search(r"in\s+((?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?)", message, re.IGNORECASE)
            if not m:
                return None
            hours = int(m.group(2)) if m.group(2) else 0
            minutes = int(m.group(3)) if m.group(3) else 0
            seconds = float(m.group(4)) if m.group(4) else 0.0
            total = int(hours * 3600 + minutes * 60 + seconds)
            return max(total, 1)
        except Exception:
            return None
    
    def _calculate_cost(self, usage) -> Dict[str, Any]:
        """Calculate API cost based on token usage"""
        if self.model not in OPENAI_PRICING:
            # Use gpt-4o-mini pricing as fallback
            pricing = OPENAI_PRICING['gpt-4o-mini']
        else:
            pricing = OPENAI_PRICING[self.model]
        
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens
        
        # Calculate cost (pricing is per 1k tokens)
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        total_cost = input_cost + output_cost
        
        return {
            'model': self.model,
            'estimated_tokens': total_tokens,
            'estimated_cost': total_cost,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost
        }
    
    def _build_analysis_prompt(self, changes: List[Dict], context: Dict, scope: List[str]) -> str:
        """Build analysis prompt for OpenAI"""
        
        # Base prompt
        prompt = f"""You are OpenAI Watchdog, an intelligent Home Assistant monitoring system. 
Analyze the following state changes and provide insights.

Current scope: {', '.join(scope)}
Time: {datetime.now().isoformat()}
Recent changes: {len(changes)}
Context buffer: {context.get('change_count', 0)} recent changes

State Changes:
"""
        
        # Add change details
        for change in changes[-10:]:  # Last 10 changes
            prompt += f"""
Entity: {change.get('entity_id')}
Domain: {change.get('domain')}
Change: {change.get('old_state')} → {change.get('new_state')}
Time: {change.get('last_changed')}
"""
        
        # Add scope-specific analysis instructions
        for scope_item in scope:
            if scope_item in self.analysis_templates:
                prompt += f"\n{self.analysis_templates[scope_item]}"
        
        prompt += f"""

Please analyze these changes and respond with a JSON object in this exact format:
{{
  "requires_attention": boolean,
  "confidence": number (0.0-1.0),
  "overall_assessment": "normal|concerning|urgent",
  "insights": [
    {{
      "type": "security|energy|climate|automation|device_health|pattern",
      "message": "description of the insight",
      "confidence": number (0.0-1.0),
      "entities": ["entity_id1", "entity_id2"],
      "recommended_action": "suggested action if any"
    }}
  ],
  "summary": "brief overall summary"
}}

Focus on:
- Unusual patterns or anomalies
- Energy optimization opportunities  
- Security concerns
- Device health issues
- Performance problems

Only set requires_attention to true if confidence > {self.insight_threshold} and there are genuine concerns.
Be concise but thorough in your analysis.
"""
        
        return prompt
    
    
    def _structure_analysis(self, analysis_result, changes: List[Dict]) -> Dict[str, Any]:
        """Structure the analysis result into a standard format"""
        
        # If analysis_result is already a dict (from mock), return it with timestamp
        if isinstance(analysis_result, dict):
            analysis_result['analysis_timestamp'] = datetime.now().isoformat()
            return analysis_result
        
        # Handle string response from OpenAI API
        requires_attention = False
        confidence = 0.7
        insights = []
        
        try:
            # Try to parse as JSON first
            if analysis_result.strip().startswith('{'):
                parsed = json.loads(analysis_result)
                return {
                    'requires_attention': parsed.get('requires_attention', False),
                    'confidence': parsed.get('confidence', 0.7),
                    'insights': parsed.get('insights', []),
                    'analysis_timestamp': datetime.now().isoformat(),
                    'changes_analyzed': len(changes)
                }
        except json.JSONDecodeError:
            pass
        
        # Fallback: Parse as text
        lines = analysis_result.split('\n')
        
        for line in lines:
            if 'Attention Required: True' in line or 'attention_required": true' in line.lower():
                requires_attention = True
            elif 'Confidence:' in line or 'confidence' in line.lower():
                try:
                    # Extract number from line
                    import re
                    match = re.search(r'(\d+\.?\d*)', line)
                    if match:
                        confidence = float(match.group(1))
                        if confidence > 1:  # If it's a percentage
                            confidence = confidence / 100
                except:
                    confidence = 0.7
            elif line.strip() and not any(skip in line.lower() for skip in ['analysis status:', 'processed', 'time:']):
                insights.append(line.strip())
        
        return {
            'requires_attention': requires_attention and confidence > self.insight_threshold,
            'confidence': confidence,
            'insights': insights,
            'analysis_timestamp': datetime.now().isoformat(),
            'changes_analyzed': len(changes)
        }

    def _log_api_call(self, prompt: str, response_text: str, usage: Optional[Any], cost_info: Dict[str, Any]):
        """Write a structured log entry for the API call (prompt + response)."""
        try:
            # Truncate very large strings to keep logs manageable
            def trunc(s, max_len=12000):
                try:
                    return s if len(s) <= max_len else s[:max_len] + "... [truncated]"
                except Exception:
                    return str(s)
            entry = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'model': self.model,
                'prompt': trunc(prompt or ''),
                'response': trunc(response_text or ''),
                'usage': None if usage is None else {
                    'prompt_tokens': getattr(usage, 'prompt_tokens', None),
                    'completion_tokens': getattr(usage, 'completion_tokens', None),
                    'total_tokens': getattr(usage, 'total_tokens', None),
                },
                'cost': cost_info,
            }
            # Write JSONL entry
            with open(self.api_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
            # Also emit a concise debug log
            logger.debug("OpenAI response (model=%s, tokens=%s): %s", self.model, entry.get('usage'), trunc(response_text, 2000))
            # Optionally emit prompt/response to stdout for quick debugging
            if self.log_api_stdout:
                logger.info("OpenAI prompt: %s", trunc(prompt, 4000))
                logger.info("OpenAI response: %s", trunc(response_text, 4000))
        except Exception as e:
            logger.warning(f"Failed to write OpenAI API log: {e}")
    
    def _get_climate_template(self) -> str:
        return """
For climate monitoring, focus on:
- Temperature fluctuations outside normal ranges
- HVAC efficiency patterns  
- Unusual heating/cooling cycles
- Energy optimization opportunities
"""
    
    def _get_security_template(self) -> str:
        return """
For security monitoring, focus on:
- Unusual access patterns (doors, locks)
- Motion detection anomalies
- Security system state changes
- Potential security threats or concerns
"""
    
    def _get_energy_template(self) -> str:
        return """
For energy monitoring, focus on:
- Power consumption spikes or anomalies
- Device efficiency patterns
- Opportunities for energy savings
- Unusual usage patterns
"""
    
    def _get_automation_template(self) -> str:
        return """
For automation performance, focus on:
- Failed automation executions
- Slow response times
- Automation conflicts or loops
- Optimization opportunities
"""
    
    def _get_device_health_template(self) -> str:
        return """
For device health monitoring, focus on:
- Device connectivity issues
- Battery level warnings
- Sensor accuracy problems
- Device failure predictions
"""
    
    def _get_pattern_template(self) -> str:
        return """
For pattern analysis, focus on:
- Recurring behavioral patterns
- Seasonal adjustments needed
- Usage optimization opportunities
- Predictive maintenance indicators
"""