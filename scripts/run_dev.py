"""Development server launcher. Ctrl+C stops uvicorn and shuts down Docker compose."""
import signal
import subprocess
import sys
from pathlib import Path

# Ensure project root is on sys.path regardless of cwd
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn
from server.config import settings

DOCKER_COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker/docker-compose.yml")]


def stop_docker() -> None:
    print("\n[shutdown] Stopping Docker containers...")
    subprocess.run(DOCKER_COMPOSE + ["down"], check=False)
    print("[shutdown] Docker stopped.")


def main() -> None:
    original_sigint = signal.getsignal(signal.SIGINT)

    def handle_sigint(sig, frame):
        stop_docker()
        signal.signal(signal.SIGINT, original_sigint)
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        uvicorn.run(
            "server.main:app",
            host=settings.server_host,
            port=settings.server_port,
            reload=True,
            reload_dirs=[str(ROOT / "server")],
            log_level=settings.log_level,
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
