"""
Example: Web Integration
Demonstrates WebSocket client for real-time communication.
"""

import asyncio
import json
import websockets


class ShadowClaudeWebSocketClient:
    """WebSocket client for ShadowClaude."""
    
    def __init__(self, uri: str, token: str):
        self.uri = uri
        self.token = token
        self.websocket = None
        self.session_id = None
    
    async def connect(self):
        """Connect to WebSocket server."""
        self.websocket = await websockets.connect(self.uri)
        
        # Authenticate
        await self.send({
            "type": "auth",
            "token": self.token
        })
        
        response = await self.receive()
        if response.get("type") == "auth_response" and response.get("success"):
            self.session_id = response.get("session_id")
            print(f"Authenticated. Session: {self.session_id}")
            return True
        return False
    
    async def send(self, message: dict):
        """Send message to server."""
        await self.websocket.send(json.dumps(message))
    
    async def receive(self) -> dict:
        """Receive message from server."""
        message = await self.websocket.recv()
        return json.loads(message)
    
    async def query(self, message: str, stream: bool = True) -> str:
        """Send query and get response."""
        request_id = f"req_{asyncio.get_event_loop().time()}"
        
        await self.send({
            "type": "query",
            "id": request_id,
            "payload": {
                "message": message,
                "stream": stream
            }
        })
        
        if stream:
            chunks = []
            async for message in self.websocket:
                data = json.loads(message)
                if data.get("type") == "query_chunk":
                    chunk = data["payload"]["content"]
                    chunks.append(chunk)
                    print(chunk, end="", flush=True)
                    
                    if data["payload"].get("done"):
                        break
            print()  # New line after stream
            return "".join(chunks)
        else:
            response = await self.receive()
            return response["payload"]["content"]
    
    async def close(self):
        """Close connection."""
        if self.websocket:
            await self.websocket.close()


async def main():
    client = ShadowClaudeWebSocketClient(
        uri="ws://localhost:8080/ws",
        token="your_api_token_here"
    )
    
    try:
        if await client.connect():
            print("=== WebSocket Query ===\n")
            
            response = await client.query(
                "What are the benefits of WebSocket over HTTP polling?",
                stream=True
            )
            
            print(f"\nFull response received: {len(response)} chars")
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
