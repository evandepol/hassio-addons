"""
Lightweight ingress web UI server for OpenAI Watchdog
"""

import os
from aiohttp import web


class StatusWebServer:
    """Tiny aiohttp server to expose status and insights via ingress"""

    def __init__(self, config, cost_tracker, insight_manager):
        self.config = config
        self.cost_tracker = cost_tracker
        self.insight_manager = insight_manager
        self.web_app = None
        self.web_runner = None

    async def start(self):
        self.web_app = web.Application()

        html_str = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>OpenAI Watchdog</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 16px; color: #222; }
      h1 { font-size: 20px; margin-bottom: 8px; }
      .card { border: 1px solid #ddd; border-radius: 8px; padding: 12px 16px; margin: 12px 0; background: #fff; }
      .row { display: flex; gap: 16px; flex-wrap: wrap; }
      .muted { color: #666; font-size: 12px; }
      pre { white-space: pre-wrap; }
      table { border-collapse: collapse; width: 100%; }
      th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #eee; }
      code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    </style>
  </head>
  <body>
    <h1>OpenAI Watchdog</h1>
    <div class="card" id="summary">
      <div><strong>Model:</strong> <span id="model">-</span></div>
      <div><strong>Scope:</strong> <span id="scope">-</span></div>
      <div class="row">
        <div>
          <div class="muted">Check interval</div>
          <div><span id="interval">-</span> s</div>
        </div>
        <div>
          <div class="muted">Notify on any insight</div>
          <div id="notify_any">-</div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>Usage (today)</h3>
      <div id="usage">-</div>
    </div>

    <div class="card">
      <h3>Recent insights (24h)</h3>
      <div id="insights">Loading…</div>
    </div>

    <script>
      async function load() {
        try {
          const res = await fetch('api/status');
          const data = await res.json();
          document.getElementById('model').textContent = data.model;
          document.getElementById('scope').textContent = (data.monitoring_scope || []).join(', ');
          document.getElementById('interval').textContent = data.check_interval;
          document.getElementById('notify_any').textContent = data.notify_on_any_insight ? 'Yes' : 'No';

          const u = data.usage || {}; const t = u.today || {};
          document.getElementById('usage').innerHTML = `
            <table>
              <tr><th>Cost</th><td>$${(t.cost || 0).toFixed(4)} of $${(t.limit_cost || 0).toFixed(2)}</td></tr>
              <tr><th>Requests</th><td>${t.requests || 0} of ${t.limit_requests || 0}</td></tr>
              <tr><th>Remaining</th><td>$${(t.remaining_cost || 0).toFixed(4)} / ${t.remaining_requests || 0} requests</td></tr>
            </table>`;

          const insights = data.recent_insights || [];
          const cont = document.getElementById('insights');
          if (!insights.length) {
            cont.textContent = 'No insights in the last 24h.';
          } else {
            cont.innerHTML = insights.map(i => `
              <div class="card" style="margin:8px 0;background:#fafafa">
                <div><strong>${(i.type || 'general').toString().toUpperCase()}</strong> · ${(i.confidence*100).toFixed(0)}%</div>
                <div>${i.summary || ''}</div>
                <div class="muted">${i.timestamp || ''}</div>
              </div>`).join('');
          }
        } catch (e) {
          document.getElementById('insights').textContent = 'Failed to load status.';
        }
      }
      load();
    </script>
  </body>
</html>
        """

        async def status_handler(request):
            return web.json_response({
                'model': self.config['model'],
                'check_interval': self.config['check_interval'],
                'monitoring_scope': self.config['monitoring_scope'],
                'notify_on_any_insight': self.config.get('notify_on_any_insight', False),
                'usage': self.cost_tracker.get_usage_summary() if self.cost_tracker else {},
                'recent_insights': self.insight_manager.get_recent_insights(24) if self.insight_manager else []
            })

        async def insights_handler(request):
            return web.json_response({
                'insights': self.insight_manager.get_recent_insights(168) if self.insight_manager else []
            })

        async def index_handler(request):
            return web.Response(text=html_str, content_type='text/html')

        self.web_app.add_routes([
            web.get('/', index_handler),
            web.get('/index.html', index_handler),
            web.get('/api/status', status_handler),
            web.get('/api/insights', insights_handler),
        ])

        self.web_runner = web.AppRunner(self.web_app)
        await self.web_runner.setup()
        port = int(os.getenv('WATCHDOG_HTTP_PORT', '8099'))
        site = web.TCPSite(self.web_runner, '0.0.0.0', port)
        await site.start()

    async def stop(self):
        if self.web_runner:
            await self.web_runner.cleanup()
