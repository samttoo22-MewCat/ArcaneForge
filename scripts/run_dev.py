"""Development server launcher."""
import uvicorn
from server.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
        log_level=settings.log_level,
    )
