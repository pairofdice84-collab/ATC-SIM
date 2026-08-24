"""Local dev server for the radar sim.

Plain http.server answers repeat requests with 304 Not Modified, so an edited
page keeps rendering from cache until a manual hard-reload. This sends
no-store on everything, which matters while iterating on the sim and the
voice clips.

    python serve.py [port]
"""
import functools
import http.server
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_head(self):
        # Drop conditional headers so a stale copy is never revalidated to 304
        # - the base handler answers If-Modified-Since before we get a say.
        for h in ("If-Modified-Since", "If-None-Match"):
            while h in self.headers:
                del self.headers[h]
        return super().send_head()

    def log_message(self, fmt, *args):
        # Quieter log - clip fetches would otherwise drown out everything else.
        msg = fmt % args
        if "/voice/clips/" not in msg:
            sys.stderr.write("%s %s\n" % (self.log_date_time_string(), msg))


socketserver.TCPServer.allow_reuse_address = True
handler = functools.partial(NoCacheHandler)
with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
    print(f"serving radar-sim on http://localhost:{PORT}  (no-cache)")
    httpd.serve_forever()
