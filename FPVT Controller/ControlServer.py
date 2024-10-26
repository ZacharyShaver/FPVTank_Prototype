from http.server import SimpleHTTPRequestHandler, HTTPServer

# Server settings
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 80         # Port to listen on (HTTP uses port 80)

class MyRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Respond to a GET request
        self.send_response(200)  # Send HTTP status code 200 (OK)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        # Send a simple HTML response
        self.wfile.write(b"<html><body><h1>Hello from Python Web Server!</h1></body></html>")

if __name__ == "__main__":
    # Create and configure the server
    server = HTTPServer((HOST, PORT), MyRequestHandler)
    print(f"Server started. Listening on {HOST}:{PORT}")
    
    # Start the server
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()