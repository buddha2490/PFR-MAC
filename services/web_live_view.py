"""
Auto-refreshing live view page for the web server.

/latest serves a bare image, which a browser will not update on its own. This
module serves a small self-contained HTML page that polls /latest and /status
so a remote machine (e.g. another node on the Tailscale VPN) gets a live feed
plus capture state without any client-side setup.

Kept out of web_output.py so that module stays under the per-file size cap,
matching the web_library.py / api_docs.py split.
"""

from .logger import app_logger

# No external assets: the page must render on a tailnet-only machine with no
# internet route. Everything (CSS, JS) is inline.
_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PFR Sentinel &mdash; Live</title>
<style>
  :root {
    --bg: #0b0e14; --panel: #141924; --line: #232a39;
    --text: #e6e9ef; --dim: #8b94a7; --ok: #4ade80; --warn: #fbbf24; --bad: #f87171;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  header {
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
    padding: 10px 16px; background: var(--panel); border-bottom: 1px solid var(--line);
  }
  h1 { font-size: 15px; font-weight: 600; margin: 0; letter-spacing: .2px; }
  .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--dim); flex: none; }
  .dot.ok { background: var(--ok); } .dot.warn { background: var(--warn); }
  .dot.bad { background: var(--bad); }
  .spacer { flex: 1 1 auto; }
  .chip {
    font-size: 12px; color: var(--dim); background: var(--bg);
    border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px;
    white-space: nowrap;
  }
  #wrap { padding: 16px; max-width: 1600px; margin: 0 auto; }
  #frame {
    display: block; width: 100%; height: auto; border-radius: 8px;
    border: 1px solid var(--line); background: #000;
  }
  #meta {
    margin-top: 12px; display: grid; gap: 8px;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  }
  .cell { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; }
  .k { font-size: 11px; color: var(--dim); text-transform: uppercase; letter-spacing: .5px; }
  .v { font-size: 14px; margin-top: 2px; word-break: break-word; }
  #err { display: none; margin-top: 12px; padding: 10px 12px; border-radius: 6px;
         background: #2a1416; border: 1px solid #5b2327; color: #fca5a5; }
</style>
</head>
<body>
<header>
  <span class="dot" id="dot"></span>
  <h1>PFR Sentinel</h1>
  <span class="chip" id="state">connecting&hellip;</span>
  <span class="spacer"></span>
  <span class="chip" id="age">&mdash;</span>
  <span class="chip" id="next">&mdash;</span>
</header>

<div id="wrap">
  <img id="frame" alt="Latest capture">
  <div id="err"></div>
  <div id="meta"></div>
</div>

<script>
// Paths are injected server-side so a renamed /latest or /status still works.
var IMAGE_URL  = "__IMAGE_PATH__";
var STATUS_URL = "__STATUS_PATH__";

var lastImageKey = null;

function fmtAge(s) {
  if (s === null || s === undefined) return "\\u2014";
  s = Math.round(s);
  if (s < 60) return s + "s ago";
  if (s < 3600) return Math.floor(s / 60) + "m " + (s % 60) + "s ago";
  return Math.floor(s / 3600) + "h " + Math.floor((s % 3600) / 60) + "m ago";
}

function fmtIn(s) {
  if (s === null || s === undefined) return "\\u2014";
  s = Math.max(0, Math.round(s));
  if (s < 60) return "next in " + s + "s";
  return "next in " + Math.floor(s / 60) + "m " + (s % 60) + "s";
}

function cell(k, v) {
  return '<div class="cell"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
}

function esc(v) {
  return String(v).replace(/[&<>"]/g, function (c) {
    return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c];
  });
}

function refreshImage() {
  // Cache-bust so the browser re-fetches rather than reusing the ETag'd copy.
  document.getElementById("frame").src = IMAGE_URL + "?t=" + Date.now();
}

function tick() {
  fetch(STATUS_URL, { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById("err").style.display = "none";

      var health = (d.health && d.health.status) || "unknown";
      var dot = document.getElementById("dot");
      dot.className = "dot " + (health === "ok" ? "ok" : health === "idle" ? "warn" : "bad");

      var cap = d.capture || {};
      document.getElementById("state").textContent =
        (cap.state || health) + (cap.mode ? " \\u00b7 " + cap.mode : "");
      document.getElementById("age").textContent = fmtAge(d.image_age_seconds);
      document.getElementById("next").textContent = fmtIn(cap.next_capture_in_seconds);

      // Only re-download the frame when the server reports a newer one.
      var key = String(d.latest_image) + "|" + String(d.images_served);
      if (key !== lastImageKey) { lastImageKey = key; refreshImage(); }

      var m = d.metadata || {};
      var rows = "";
      var want = [
        ["Camera", "CAMERA"], ["Exposure", "EXPOSURE"], ["Gain", "GAIN"],
        ["Sensor temp", "TEMP_C"], ["Resolution", "RES"], ["Mean ADU", "MEAN"],
      ];
      for (var i = 0; i < want.length; i++) {
        if (m[want[i][1]] !== undefined) rows += cell(want[i][0], esc(m[want[i][1]]));
      }
      if (cap.effective_interval_seconds) {
        rows += cell("Interval", Math.round(cap.effective_interval_seconds) + "s");
      }
      if (d.latest_image) rows += cell("File", esc(d.latest_image));
      if (cap.last_error) rows += cell("Last error", esc(cap.last_error));
      document.getElementById("meta").innerHTML = rows;
    })
    .catch(function (e) {
      document.getElementById("dot").className = "dot bad";
      document.getElementById("state").textContent = "unreachable";
      var err = document.getElementById("err");
      err.textContent = "Cannot reach the Sentinel server: " + e;
      err.style.display = "block";
    });
}

refreshImage();
tick();
setInterval(tick, 3000);
</script>
</body>
</html>
"""


def serve_live_view(handler, image_path, status_path):
    """Serve the auto-refreshing live view page.

    Args:
        handler: the BaseHTTPRequestHandler serving this request
        image_path: configured image endpoint (e.g. '/latest')
        status_path: configured status endpoint (e.g. '/status')
    """
    try:
        html = (
            _PAGE
            .replace('__IMAGE_PATH__', image_path)
            .replace('__STATUS_PATH__', status_path)
        ).encode('utf-8')

        handler.send_response(200)
        handler.send_header('Content-Type', 'text/html; charset=utf-8')
        handler.send_header('Content-Length', str(len(html)))
        # The page reflects live capture state; never let a proxy pin it.
        handler.send_header('Cache-Control', 'no-store')
        handler.end_headers()
        handler.wfile.write(html)
    except Exception as e:
        app_logger.error(f"Error serving live view: {e}")
        try:
            handler.send_error(500, "Live view unavailable")
        except Exception:
            pass
