#!/usr/bin/env python3
"""
Small static server that serves `home.html` for `/` and `index.html`,
and falls back to normal static file serving for other paths.

Run: python3 serve.py 3000
Then open: http://localhost:3000/
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
import os


class RootToHomeHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Map root and /index.html to home.html in the working directory
        if path in ('/', '') or path == '/index.html':
            return os.path.join(os.getcwd(), 'home.html')
        return super().translate_path(path)


def run(host='0.0.0.0', port=3000):
    addr = (host, port)
    with ThreadingHTTPServer(addr, RootToHomeHandler) as httpd:
        print(f"Serving {os.getcwd()} on http://{host}:{port}/ — '/' -> home.html")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nServer stopped')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Serve static files, map / to home.html')
    p.add_argument('port', nargs='?', type=int, default=3000, help='port to listen on')
    args = p.parse_args()
    run(port=args.port)
