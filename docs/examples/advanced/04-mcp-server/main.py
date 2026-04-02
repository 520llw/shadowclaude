"""
Example: MCP Server
Demonstrates creating a Model Context Protocol server.
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler


class MCPServer(BaseHTTPRequestHandler):
    """Simple MCP server implementation."""
    
    tools = {
        "calculator": {
            "description": "Perform calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        },
        "weather": {
            "description": "Get weather information",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                },
                "required": ["city"]
            }
        }
    }
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = json.loads(body)
        
        method = request.get("method")
        
        if method == "tools/discover":
            self.handle_discover()
        elif method == "tools/call":
            self.handle_call(request)
        else:
            self.send_error(404)
    
    def handle_discover(self):
        """Return available tools."""
        response = {
            "tools": [
                {
                    "name": name,
                    "description": info["description"],
                    "parameters": info["parameters"]
                }
                for name, info in self.tools.items()
            ]
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def handle_call(self, request):
        """Handle tool call."""
        params = request.get("params", {})
        tool_name = params.get("tool")
        arguments = params.get("arguments", {})
        
        if tool_name == "calculator":
            try:
                result = eval(arguments.get("expression", ""))
                response = {"result": result}
            except Exception as e:
                response = {"error": str(e)}
        
        elif tool_name == "weather":
            city = arguments.get("city", "Unknown")
            response = {
                "city": city,
                "temperature": 22,
                "condition": "Sunny"
            }
        
        else:
            response = {"error": f"Unknown tool: {tool_name}"}
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def main():
    print("=== MCP Server Example ===\n")
    
    server = HTTPServer(('localhost', 8081), MCPServer)
    print("MCP Server running on http://localhost:8081")
    print("Available tools:")
    for name, info in MCPServer.tools.items():
        print(f"  - {name}: {info['description']}")
    
    print("\nPress Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
