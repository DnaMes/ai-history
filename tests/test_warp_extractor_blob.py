from datetime import datetime

from ai_history.core.models import Role, UnifiedMessage
from ai_history.extractors.warp import WarpExtractor


def test_extract_assistant_text_from_blob_picks_human_text():
    extractor = WarpExtractor()
    blob = (
        b"$123e4567-e89b-12d3-a456-426614174000 "
        b"CiQ2M2FkOWRhYi1jNDZiLTQ5NGItYTgwOC0wMjNiNGVjMTJhYjgq "
        b"I will check your installed packages and then verify the fingerprint sensor detection. "
        b"After that I can suggest the exact Fedora fix steps."
    )

    text = extractor._extract_assistant_text_from_blob(blob)

    assert "fingerprint sensor detection" in text


def test_extract_assistant_text_from_blob_drops_skill_instruction_noise():
    extractor = WarpExtractor()
    blob = (
        b"This file provides guidance to WARP when working with code in this repository. "
        b"Use for: debug and troubleshoot production issues. "
        b"I can help you fix your Fedora shutdown timer now."
    )

    text = extractor._extract_assistant_text_from_blob(blob)

    assert "guidance to WARP" not in text
    assert "Use for:" not in text


def test_extract_assistant_text_from_blob_handles_binary_wrapped_response():
    extractor = WarpExtractor()
    blob = (
        b"\n$7a48c26d-06a9-4d9e-a0fd-1e85ca4cd03b"
        b"\x00The user confirmed to run the shutdown command."
        b"\x00Das folgende Kommando plant das Herunterfahren des Systems in 60 Minuten:\n"
        b"```bash\nsudo shutdown -h +60\n```\n\n"
        b"Zum Abbrechen des geplanten Shutdowns:\n"
        b"```bash\nsudo shutdown -c\n```\n\n"
        b"Soll ich den Befehl ausfuhren?:HCiQwZjV"
        b'\x00=sudo shutdown -h +60 "Geplantes Herunterfahren in 60 Minuten"'
    )

    text = extractor._extract_assistant_text_from_blob(blob)

    assert "Das folgende Kommando plant das Herunterfahren" in text
    assert "sudo shutdown -h +60" in text
    assert "The user confirmed" not in text


def test_extract_assistant_candidates_preserve_turn_like_order():
    extractor = WarpExtractor()
    blob = (
        b"noise use for: azure deployments"
        b"\x00Das folgende Kommando plant das Herunterfahren des Systems in 60 Minuten:\n"
        b"```bash\nsudo shutdown -h +60\n```\n\n"
        b"Soll ich den Befehl ausfuhren?"
        b"\x00Das System wird um 01:13 Uhr heruntergefahren. Mit sudo shutdown -c kannst du es jederzeit abbrechen."
    )

    candidates = extractor._extract_assistant_text_candidates_from_blob(blob)

    assert len(candidates) == 2
    assert "Soll ich den Befehl" in candidates[0]
    assert "Das System wird um 01:13 Uhr" in candidates[1]


def test_build_session_distributes_assistant_messages_across_turns():
    extractor = WarpExtractor()
    queries = []
    for idx in range(6):
        queries.append(
            {
                "input": {"Query": {"text": f"backup task {idx}"}},
                "working_directory": "/repo",
                "start_ts": f"2026-03-05T10:00:0{idx}",
                "model_id": "warp-model",
            }
        )

    same_ts = datetime.fromisoformat("2026-03-05T10:05:00")
    assistant_messages = [
        UnifiedMessage(
            role=Role.ASSISTANT,
            content=f"Progress update for backup task {idx}",
            timestamp=same_ts,
        )
        for idx in range(3)
    ]

    session = extractor._build_session("conv-test", queries, assistant_messages)
    roles = [msg.role.value for msg in session.messages]

    assert roles.count("user") == 6
    assert roles.count("assistant") == 3
    assert roles.index("assistant") < len(roles) - roles.count("assistant")
    assert roles != [
        "user",
        "user",
        "user",
        "user",
        "user",
        "user",
        "assistant",
        "assistant",
        "assistant",
    ]
