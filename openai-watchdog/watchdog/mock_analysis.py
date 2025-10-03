"""
Mock analysis utilities for OpenAI Watchdog
"""

from typing import Dict, List, Any


async def mock_openai_analysis(model: str, changes: List[Dict]) -> Dict[str, Any]:
    """Generate a deterministic mock analysis for development/testing.

    Args:
        model: Model name to echo in cost_info for transparency.
        changes: Recent Home Assistant state changes to examine.

    Returns:
        A structured analysis result similar to the real analyzer, but with
        zero cost and simple heuristic insights.
    """
    insights: List[Dict[str, Any]] = []
    requires_attention = False
    confidence = 0.7

    # Heuristic: treat door/lock entities as security-relevant
    security_changes = [
        c for c in changes if 'door' in c.get('entity_id', '') or 'lock' in c.get('entity_id', '')
    ]
    if security_changes:
        insights.append({
            'type': 'security',
            'message': f'Security activity detected: {len(security_changes)} security-related changes',
            'confidence': 0.8,
            'entities': [c.get('entity_id') for c in security_changes[:3]],
        })
        requires_attention = True

    # Heuristic: treat power/energy entities as energy-relevant
    energy_changes = [
        c for c in changes if 'power' in c.get('entity_id', '') or 'energy' in c.get('entity_id', '')
    ]
    if energy_changes:
        insights.append({
            'type': 'energy',
            'message': f'Energy monitoring: {len(energy_changes)} power-related changes',
            'confidence': 0.6,
            'entities': [c.get('entity_id') for c in energy_changes[:3]],
        })

    # Mock cost info (no cost in mock mode)
    cost_info = {
        'model': model,
        'estimated_tokens': 0,
        'estimated_cost': 0.0,
        'input_tokens': 0,
        'output_tokens': 0,
        'input_cost': 0.0,
        'output_cost': 0.0,
    }

    return {
        'requires_attention': requires_attention,
        'insights': insights,
        'confidence': confidence,
        'processed_changes': len(changes),
        'cost_info': cost_info,
    }
