"""
Local heuristic "model" for offline analysis when no external local LLM is configured.
Produces structured insights similar to the online path, zero-cost.
"""

from datetime import datetime
from typing import Dict, List, Any


def _score(conf: float) -> float:
    try:
        c = float(conf)
        if 0.0 <= c <= 1.0:
            return c
    except Exception:
        pass
    return 0.7


async def local_analyze(changes: List[Dict], context: Dict, scope: List[str], threshold: float = 0.8) -> Dict[str, Any]:
    """Heuristic analysis for local tier.
    - Looks for simple patterns across changes to produce insights.
    - Zero token/cost; designed to be deterministic and fast.
    """
    insights: List[Dict[str, Any]] = []

    # Simple detectors
    now = datetime.now().isoformat()
    for ch in changes[-20:]:
        entity = ch.get('entity_id', '')
        domain = (ch.get('domain') or '').lower()
        old_s = str(ch.get('old_state'))
        new_s = str(ch.get('new_state'))
        ts = ch.get('last_changed', now)

        # Security heuristics
        if 'security' in scope or 'all' in scope:
            # Door/lock opened/unlocked
            if any(k in entity for k in ['door', 'lock']) or domain in ['lock', 'binary_sensor']:
                if 'unlock' in new_s.lower() or new_s.lower() in ['on', 'open', 'unlocked']:
                    insights.append({
                        'type': 'security',
                        'message': f"{entity} changed to {new_s} at {ts}",
                        'confidence': _score(0.85),
                        'entities': [entity],
                        'recommended_action': 'Verify if this is expected.'
                    })

        # Energy heuristics
        if 'energy' in scope or 'all' in scope:
            if domain in ['sensor'] and ('power' in entity or 'energy' in entity):
                try:
                    old_v = float(''.join([c for c in old_s if c.isdigit() or c == '.'])) if old_s else 0.0
                    new_v = float(''.join([c for c in new_s if c.isdigit() or c == '.'])) if new_s else 0.0
                    if new_v > 0 and old_v >= 0 and (new_v - old_v) / max(old_v, 1.0) > 0.5:
                        insights.append({
                            'type': 'energy',
                            'message': f"Power increased significantly for {entity}: {old_v} → {new_v}",
                            'confidence': _score(0.8),
                            'entities': [entity],
                            'recommended_action': 'Investigate unusual consumption.'
                        })
                except Exception:
                    pass

        # Device health heuristics
        if 'device_health' in scope or 'all' in scope:
            if 'battery' in entity:
                try:
                    lvl = float(''.join([c for c in new_s if c.isdigit() or c == '.'])) if new_s else 100.0
                    if lvl < 20:
                        insights.append({
                            'type': 'device_health',
                            'message': f"Low battery for {entity}: {lvl}%",
                            'confidence': _score(0.9),
                            'entities': [entity],
                            'recommended_action': 'Replace or recharge battery soon.'
                        })
                except Exception:
                    pass

    # Basic consolidation
    requires_attention = any(i.get('confidence', 0.0) >= threshold for i in insights)
    overall_conf = max([i.get('confidence', 0.0) for i in insights], default=0.7)
    summary = (
        f"{len(insights)} observation(s). " + \
        ("Attention required." if requires_attention else "No urgent issues.")
    )

    return {
        'requires_attention': requires_attention,
        'confidence': overall_conf,
        'overall_assessment': 'urgent' if requires_attention and overall_conf >= 0.9 else ('concerning' if requires_attention else 'normal'),
        'insights': insights,
        'summary': summary,
        'analysis_timestamp': now,
        'changes_analyzed': len(changes),
        'provider': 'local',
        'cost_info': {
            'model': 'local-heuristic',
            'estimated_tokens': 0,
            'estimated_cost': 0.0,
            'input_tokens': 0,
            'output_tokens': 0,
            'input_cost': 0.0,
            'output_cost': 0.0,
            'note': 'local-rulebased',
            'provider': 'local',
            'success': True,
        }
    }
