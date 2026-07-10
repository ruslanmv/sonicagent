class SonicAgentClient:
    """Placeholder SDK client; implement REST session creation and WebSocket streaming."""
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
