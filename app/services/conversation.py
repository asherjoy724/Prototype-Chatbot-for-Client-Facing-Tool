from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List


@dataclass
class ConversationTurn:
    role: str
    text: str


_memory: Dict[str, Deque[ConversationTurn]] = defaultdict(lambda: deque(maxlen=8))


def append_turn(session_id: str, role: str, text: str) -> None:
    if not session_id:
        return

    _memory[session_id].append(ConversationTurn(role=role, text=text))


def get_recent_turns(session_id: str, limit: int = 6) -> List[ConversationTurn]:
    if not session_id or session_id not in _memory:
        return []

    turns = list(_memory[session_id])
    return turns[-limit:]


def render_recent_turns(session_id: str, limit: int = 6) -> str:
    turns = get_recent_turns(session_id, limit=limit)
    if not turns:
        return "No prior conversation."

    return "\n".join(f"{turn.role.upper()}: {turn.text}" for turn in turns)
