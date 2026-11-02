"""Short-lived speech-only sessions. These sessions never call the language model."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import asdict, dataclass, field
from threading import Lock

from sonicagent_rt.stt.errors import InvalidRequest, RateLimited, Unauthenticated

MODES = ("stt_only", "tts_only", "duplex_speech")

#: Values each negotiable option accepts. The first value of each is the v1
#: behaviour, and a client that sends no ``stream_options`` gets exactly that.
OPTION_VALUES: dict[str, tuple[object, ...]] = {
    # ``all``: a JSON ``tts.audio.chunk`` before every binary frame (v1).
    # ``none``: binary frames only. The 24-byte header already carries the
    # sequence, rate and timestamp, and a session speaks one turn at a time,
    # so the frames between ``tts.audio.meta`` and ``tts.audio.done`` belong
    # to that turn. Halves the WebSocket messages per second of speech.
    "chunk_events": ("all", "none"),
    # Output frame length. 40 ms halves the per-frame overhead again.
    "output_frame_ms": (20, 40),
    # ``none``: the server paces output to real time once it is
    # ``SONIC_MAX_OUTBOUND_QUEUE_MS`` ahead. ``ack``: the client reports
    # ``playback.ack`` with the milliseconds it has actually played, and the
    # server keeps at most that limit of unplayed audio in flight.
    "flow_control": ("none", "ack"),
    # ``server``: the VAD endpointer cuts utterances (v1). ``client``: the
    # client owns the turn (push-to-talk, a mic button). Audio is held until
    # the end-of-utterance flag and transcribed once, so one commit gives
    # exactly one ``transcript.final`` (empty text when nothing was said),
    # tagged with the ``commit_seq`` of the frame that ended it.
    "endpointing": ("server", "client"),
    # ``false``: ``tts.speak`` while one is running is refused (v1).
    # ``true``: up to MAX_TTS_QUEUE phrases wait their turn in order, so a
    # client streaming a reply phrase by phrase never waits a round trip
    # between them.
    "tts_queue": (False, True),
}

MAX_TTS_QUEUE = 16


@dataclass(frozen=True)
class StreamOptions:
    chunk_events: str = "all"
    output_frame_ms: int = 20
    flow_control: str = "none"
    endpointing: str = "server"
    tts_queue: bool = False

    @classmethod
    def parse(cls, raw: object, *, default_frame_ms: int = 20) -> StreamOptions:
        """Validate a client's ``stream_options``. Unknown keys are refused, not ignored.

        A typo such as ``endpoint`` silently falling back to server endpointing
        would hand the client two finals for one push-to-talk hold, which is the
        very thing it asked to avoid.
        """
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise InvalidRequest("stream_options must be an object")
        unknown = sorted(set(raw) - set(OPTION_VALUES))
        if unknown:
            raise InvalidRequest(f"unknown stream option: {unknown[0]}")
        values: dict[str, object] = {}
        for key, allowed in OPTION_VALUES.items():
            if key not in raw:
                continue
            value = raw[key]
            if isinstance(value, str):
                value = value.strip().lower()
            if value not in allowed or isinstance(value, bool) != isinstance(allowed[0], bool):
                raise InvalidRequest(f"stream option {key} must be one of {list(allowed)}")
            values[key] = value
        if "output_frame_ms" not in values and default_frame_ms in OPTION_VALUES["output_frame_ms"]:
            values["output_frame_ms"] = default_frame_ms
        return cls(**values)  # type: ignore[arg-type]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class SpeechStreamSession:
    session_id: str
    resume_token: str
    mode: str
    language: str | None
    voice_id: str
    stt_provider: str
    expires_at: float
    held: bool = False
    options: StreamOptions = field(default_factory=StreamOptions)
    created_at: float = field(default_factory=time.monotonic)
    #: Connected once and since disconnected: only a resume can still want it.
    released: bool = False


#: How long a session that was connected and then dropped stays resumable.
#: A client that comes back later creates a new session, which is what the
#: Avatar's link does anyway after its idle close.
RESUME_GRACE_SEC = 60.0
#: How long a created session may wait for its first connect before it can be
#: evicted to make room. Clients connect within a second of creating one.
CONNECT_WINDOW_SEC = 30.0


class SpeechStreamStore:
    """Live and resumable speech sessions, bounded by ``max_sessions``.

    Production finding (2026-11-01): a session used to stay in the store for its
    whole TTL (``SONIC_SESSION_TTL_SEC``, 30 minutes) after its socket closed,
    and ``max_sessions`` (8) counted those too. The bound is per service, not
    per user, and behind OllaBridge Cloud every user shares this one service,
    so eight page loads or microphone tests in half an hour refused every new
    voice session for everyone with "too many speech sessions are open" while
    no socket was open at all. Now a dropped session keeps only a short resume
    grace, and when the store is full the sessions nobody is connected to —
    dropped ones, and created ones that never connected within a connect
    window — make room, oldest first. Only connected sessions, and ones just
    created and about to connect, can fill it.
    """

    def __init__(self, *, ttl_sec: int, max_sessions: int) -> None:
        self._ttl_sec = ttl_sec
        self._max_sessions = max_sessions
        self._items: dict[str, SpeechStreamSession] = {}
        self._lock = Lock()

    def put(self, session: SpeechStreamSession) -> None:
        with self._lock:
            now = time.monotonic()
            self._drop_expired(now)
            if session.session_id not in self._items and len(self._items) >= self._max_sessions:
                self._evict_idle(now)
            if session.session_id not in self._items and len(self._items) >= self._max_sessions:
                raise RateLimited("too many speech sessions are open")
            self._items[session.session_id] = session

    def acquire(self, session_id: str, resume_token: str) -> SpeechStreamSession:
        current_time = time.monotonic()
        with self._lock:
            self._drop_expired(current_time)
            current = self._items.get(session_id)
            if current is None or not _same(current.resume_token, resume_token):
                raise Unauthenticated("authentication is required")
            if current.expires_at <= current_time:
                self._items.pop(session_id, None)
                raise Unauthenticated("authentication is required")
            if current.held:
                raise RateLimited("session is already connected")
            current.held = True
            return current

    def release(self, session_id: str) -> None:
        with self._lock:
            current = self._items.get(session_id)
            if current is not None:
                current.held = False
                current.released = True
                current.expires_at = min(current.expires_at, time.monotonic() + RESUME_GRACE_SEC)

    def _evict_idle(self, now: float) -> None:
        """Drop sessions nobody is connected to, oldest first, until one fits."""
        idle = sorted(
            (
                value
                for value in self._items.values()
                if not value.held and (value.released or now - value.created_at >= CONNECT_WINDOW_SEC)
            ),
            key=lambda value: value.created_at,
        )
        for value in idle:
            if len(self._items) < self._max_sessions:
                break
            self._items.pop(value.session_id, None)

    def __len__(self) -> int:
        with self._lock:
            self._drop_expired(time.monotonic())
            return len(self._items)

    def _drop_expired(self, now: float) -> None:
        expired = [key for key, value in self._items.items() if value.expires_at <= now]
        for key in expired:
            self._items.pop(key, None)


def _same(expected: str, presented: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(expected.encode("utf-8")).digest(),
        hashlib.sha256(presented.encode("utf-8")).digest(),
    )
