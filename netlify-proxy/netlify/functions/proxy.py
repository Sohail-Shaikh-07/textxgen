# netlify/functions/proxy.py
import os
import requests
import json

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

def handler(event, context):
    if not OPENROUTER_API_KEY:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "API key not configured"})
        }

    # Parse incoming request body
    try:
        body = json.loads(event["body"]) if event["body"] else {}
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON body"})
        }

    # Default values if not provided
    payload = {
        "model": body.get("model", "llama3"),
        "messages": body.get("messages", []),
        "stream": body.get("stream", False),
        "temperature": body.get("temperature", 0.7),
        "max_tokens": body.get("max_tokens", 100),
    }

    # Validate messages
    if not payload["messages"] or not isinstance(payload["messages"], list):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Messages must be a non-empty list"})
        }

    # Handle streaming or non-streaming requests
    try:
        if payload["stream"]:
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                headers=HEADERS,
                json=payload,
                stream=True,
            )
            response.raise_for_status()

            def stream_response():
                for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                    if chunk:
                        yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
                "isBase64Encoded": False,
                "body": stream_response(),
            }
        else:
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                headers=HEADERS,
                json=payload,
            )
            response.raise_for_status()
            return {
                "statusCode": 200,
                "body": response.text
            }
    except requests.RequestException as e:
        return {
            "statusCode": getattr(e.response, "status_code", 500),
            "body": json.dumps({"error": str(e)})
        }

# Export the handler for Netlify
exports = {"handler": handler}
