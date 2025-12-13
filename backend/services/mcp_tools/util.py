import time
from fastapi import Request
from datetime import datetime

# Dummy audit log function (replace with DB or log sink as needed)
async def audit_log(tool: str, user, body):
    # user: user object or id
    # body: request body
    # Log: {tool, userId, timestamp, durationMs, status}
    # For now, just print (replace with DB insert or logger)
    print({
        "tool": tool,
        "userId": getattr(user, "id", str(user)),
        "timestamp": datetime.utcnow().isoformat(),
        "status": "ok"
    })
