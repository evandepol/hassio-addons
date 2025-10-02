"""
OpenAI analysis engine for interpreting Home Assistant state changes
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

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
        if not api_key:
            logger.error("No OpenAI API key found")
            return
            
        try:
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
    
    async def analyze_changes(self, changes: List[Dict], context: Dict, monitoring_scope: List[str]) -> Dict[str, Any]:
        """Analyze state changes and return insights"""
        if not changes:
            return {'requires_attention': False, 'insights': []}
        
        if not self.client:
            logger.warning("OpenAI client not initialized, using mock analysis")
            return await self._mock_openai_analysis(changes)
        
        try:
            # Build analysis prompt based on scope and changes
            prompt = self._build_analysis_prompt(changes, context, monitoring_scope)
            
            # Make OpenAI API call
            response = await self.client.chat.completions.create(
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
            usage = response.usage
            
            # Calculate cost
            cost_info = self._calculate_cost(usage)
            
            # Process and structure the response
            structured_result = self._structure_analysis(analysis_text, changes)
            structured_result['cost_info'] = cost_info
            
            return structured_result
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Fallback to mock analysis
            return await self._mock_openai_analysis(changes)
    
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
    
    async def _mock_openai_analysis(self, changes: List[Dict]) -> Dict[str, Any]:
        """Mock OpenAI analysis for development/testing"""
        # TODO: Replace with actual OpenAI API call
        
        # Simple mock analysis based on change patterns
        insights = []
        requires_attention = False
        confidence = 0.7
        
        # Check for concerning patterns
        security_changes = [c for c in changes if 'door' in c.get('entity_id', '') or 'lock' in c.get('entity_id', '')]
        if security_changes:
            insights.append({
                'type': 'security',
                'message': f'Security activity detected: {len(security_changes)} security-related changes',
                'confidence': 0.8,
                'entities': [c.get('entity_id') for c in security_changes[:3]]
            })
            requires_attention = True
        
        energy_changes = [c for c in changes if 'power' in c.get('entity_id', '') or 'energy' in c.get('entity_id', '')]
        if energy_changes:
            insights.append({
                'type': 'energy',
                'message': f'Energy monitoring: {len(energy_changes)} power-related changes',
                'confidence': 0.6,
                'entities': [c.get('entity_id') for c in energy_changes[:3]]
            })
        
        # Mock cost info
        cost_info = {
            'model': self.model,
            'estimated_tokens': len(str(changes)) // 4,  # Rough token estimate
            'estimated_cost': 0.001,  # Mock cost
            'input_tokens': 100,
            'output_tokens': 50,
            'input_cost': 0.0007,
            'output_cost': 0.0003
        }
        
        return {
            'requires_attention': requires_attention,
            'insights': insights,
            'confidence': confidence,
            'processed_changes': len(changes),
            'cost_info': cost_info
        }
    
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