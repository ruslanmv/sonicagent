import json
import re
from pathlib import Path
from sonicagent_rt.protocol import constants as pyc


def _ts_array(name: str) -> tuple[str, ...]:
    text = Path("clients/web/src/protocol/constants.ts").read_text()
    match = re.search(rf"export const {name} = \[(.*?)\] as const;", text, re.S)
    assert match, name
    return tuple(json.loads(f"[{match.group(1).rstrip().rstrip(',')} ]"))


def test_protocol_constants_match_typescript() -> None:
    ts = Path("clients/web/src/protocol/constants.ts").read_text()
    assert f"PROTOCOL_VERSION = {pyc.PROTOCOL_VERSION}" in ts
    assert f"HEADER_SIZE = {pyc.HEADER_SIZE}" in ts
    assert list(pyc.MAGIC) == [0x53, 0x41]
    assert _ts_array("CONTROL_EVENTS") == pyc.CONTROL_EVENTS
    assert _ts_array("SERVER_EVENTS") == pyc.SERVER_EVENTS
