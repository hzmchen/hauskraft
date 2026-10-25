# SPDX-License-Identifier: MIT
"""A fake OpenAI-compatible Chat Completions server for Hauskraft's assistant tests (ADR 0022, M2S-E01-01).

Spec-owned test fixture, standard library only. It answers ``POST /v1/chat/completions`` from the scripted scenarios
in ``scenarios.json`` and records every request so tests can check what the harness sent. See README.md.

Run: ``python server.py [--port 8090]`` (or ``FAKE_LLM_PORT``).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

SCENARIOS: list[dict[str, Any]] = json.loads((Path(__file__).with_name("scenarios.json")).read_text("utf-8"))[
    "scenarios"
]
MODELS = ["fake-tools", "fake-no-tools", "fake-broken", "fake-loop", "fake-no-usage"]
WRONG_KEY = "wrong-key"
TODAY = re.compile(r"^Today: (\d{4}-\d{2}-\d{2})", re.M)
TEMPLATE = re.compile(r"\{\{(\w+)(?::([^{}]*))?\}\}")

_records: list[dict[str, Any]] = []
_lock = threading.Lock()


# ---------------------------------------------------------------- message helpers
def text_of(content: Any) -> str:
    """Message content as text: a string, or a list of parts with ``text``."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
    return ""


def system_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(text_of(m.get("content")) for m in messages if m.get("role") in ("system", "developer"))


def last_user_index(messages: list[dict[str, Any]]) -> int:
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            return i
    return -1


def tool_payloads(messages: list[dict[str, Any]]) -> list[Any]:
    """Parsed contents of tool messages, oldest first (unparseable content stays a string)."""
    out: list[Any] = []
    for m in messages:
        if m.get("role") == "tool":
            raw = text_of(m.get("content"))
            try:
                out.append(json.loads(raw))
            except (TypeError, ValueError):
                out.append(raw)
    return out


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def titled(payload: Any) -> list[dict[str, Any]]:
    return [d for d in walk(payload) if isinstance(d.get("title"), str)]


# ---------------------------------------------------------------- templates
class Context:
    def __init__(self, messages: list[dict[str, Any]], groups: dict[str, str], user: str) -> None:
        self.messages = messages
        self.groups = groups
        self.user = user
        self.system = system_text(messages)
        self.tools = tool_payloads(messages)

    def today(self) -> dt.date | None:
        m = TODAY.search(self.system)
        return dt.date.fromisoformat(m.group(1)) if m else None

    def render(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._render_str(value)
        if isinstance(value, list):
            return [self.render(v) for v in value]
        if isinstance(value, dict):
            return {k: self.render(v) for k, v in value.items()}
        return value

    def _render_str(self, text: str) -> Any:
        # Groups first, so they can feed {{find:...}}.
        text = re.sub(r"\{\{g:(\w+)\}\}", lambda m: self.groups.get(m.group(1), ""), text)
        whole = TEMPLATE.fullmatch(text)
        if whole and whole.group(1) == "null":
            return None
        return TEMPLATE.sub(lambda m: self._expand(m.group(1), m.group(2) or ""), text)

    def _expand(self, name: str, arg: str) -> str:
        if name == "date":
            today = self.today()
            return (today + dt.timedelta(days=int(arg or 0))).isoformat() if today else "NO-DATE-IN-CONTEXT"
        if name == "find":
            for payload in reversed(self.tools):
                for item in titled(payload):
                    if item["title"].casefold() == arg.casefold() and "id" in item:
                        return str(item["id"])
            return "NOT-FOUND"
        if name == "titles":
            titles = [d["title"] for d in titled(self.tools[-1])] if self.tools else []
            return ", ".join(titles) if titles else "nothing"
        if name == "user":
            return self.user
        return "{{" + name + "}}"


# ---------------------------------------------------------------- the model
def offered(body: dict[str, Any]) -> list[str]:
    return [t.get("function", {}).get("name", "") for t in body.get("tools") or []]


def choose(messages: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, str], str]:
    idx = last_user_index(messages)
    user = text_of(messages[idx].get("content")).strip() if idx >= 0 else ""
    system = system_text(messages)
    for scenario in SCENARIOS:
        if "system" in scenario and not re.search(scenario["system"], system):
            continue
        if "match" in scenario:
            m = re.fullmatch(scenario["match"], user, re.I | re.S)
            if not m:
                continue
            return scenario, {k: v or "" for k, v in m.groupdict().items()}, user
        return scenario, {}, user
    return None, {}, user


def rounds_since_user(messages: list[dict[str, Any]]) -> int:
    idx = last_user_index(messages)
    return sum(1 for m in messages[idx + 1:] if m.get("role") == "assistant")


def last_tool_text(messages: list[dict[str, Any]]) -> str:
    """The newest tool message since the latest user message, or ""."""
    for m in reversed(messages):
        if m.get("role") == "user":
            break
        if m.get("role") == "tool":
            return text_of(m.get("content"))
    return ""


def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {"id": f"call_{uuid.uuid4().hex[:12]}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def reply(body: dict[str, Any]) -> dict[str, Any]:
    """The assistant message for a request: content and/or tool_calls."""
    messages = body.get("messages") or []
    tools = offered(body)
    if body.get("model") == "fake-loop":
        return {"tool_calls": [call("tasks_list", {})]} if "tasks_list" in tools else {"content": "loop"}
    scenario, groups, user = choose(messages)
    if scenario is None:
        return {"content": f"FAKE: no scenario matches: {user[:80]}"}
    ctx = Context(messages, groups, user)
    steps = scenario["steps"]
    n = rounds_since_user(messages)
    if n >= len(steps):
        return {"content": "FAKE: scenario exhausted"}
    step = steps[n]
    if "call" in step:
        missing = [c["name"] for c in step["call"] if c["name"] not in tools]
        if missing:
            return {"content": f"I can't do that: the tool {missing[0]} is not available."}
        return {"tool_calls": [call(c["name"], ctx.render(c.get("args", {}))) for c in step["call"]]}
    if "output_from_lines" in step:
        lines = [ln.strip()[2:].strip() for ln in user.splitlines() if ln.strip()[:2] in ("- ", "* ")]
        return output(body, {"tasks": [{"title": t, "due_on": None} for t in lines if t]})
    if "output" in step:
        return output(body, ctx.render(step["output"]))
    tool_text = last_tool_text(messages).casefold()
    if "say_denied" in step and "denied" in tool_text:
        return {"content": ctx.render(step["say_denied"])}
    if "say_failed" in step and ("not_found" in tool_text or "error" in tool_text):
        return {"content": ctx.render(step["say_failed"])}
    return {"content": ctx.render(step["say"])}


def output(body: dict[str, Any], value: Any) -> dict[str, Any]:
    """Structured output the way the request asks for it: response_format, an output tool, or JSON text."""
    fmt = body.get("response_format") or {}
    if fmt.get("type") in ("json_schema", "json_object"):
        return {"content": json.dumps(value)}
    for name in offered(body):
        if name.startswith("final_result"):
            return {"tool_calls": [call(name, value)]}
    return {"content": json.dumps(value)}


def completion(body: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": message.get("content")}
    if message.get("tool_calls"):
        msg["tool_calls"] = message["tool_calls"]
    out: dict[str, Any] = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:16]}", "object": "chat.completion", "created": int(time.time()),
        "model": body.get("model"),
        "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if message.get("tool_calls") else "stop"}],
    }
    if body.get("model") != "fake-no-usage":
        prompt = math.ceil(len(json.dumps(body.get("messages", [])) + json.dumps(body.get("tools", []))) / 4)
        done = math.ceil(len(json.dumps(message)) / 4) + 1
        out["usage"] = {"prompt_tokens": prompt, "completion_tokens": done, "total_tokens": prompt + done}
    return out


# ---------------------------------------------------------------- HTTP
def error(status: int, message: str, code: str) -> tuple[int, dict[str, Any]]:
    return status, {"error": {"message": message, "type": "invalid_request_error", "code": code}}


def handle_completion(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    auth = headers.get("authorization", "")
    with _lock:
        _records.append({"at": dt.datetime.now(dt.UTC).isoformat(), "authorization": auth,
                         "model": body.get("model"), "tools": offered(body), "messages": body.get("messages", []),
                         "body": body})
    if not auth.startswith("Bearer ") or auth.removeprefix("Bearer ") in ("", WRONG_KEY):
        return error(401, "Incorrect API key provided.", "invalid_api_key")
    model = body.get("model")
    if model not in MODELS:
        return error(404, f"The model {model!r} does not exist.", "model_not_found")
    if body.get("stream"):
        return error(400, "The fake model does not stream.", "stream_unsupported")
    if model == "fake-broken":
        return error(500, "The fake model is broken on purpose.", "server_error")
    if model == "fake-no-tools" and body.get("tools"):
        return error(400, "This model does not support tools.", "tools_unsupported")
    return 200, completion(body, reply(body))


class Handler(BaseHTTPRequestHandler):
    server_version = "hauskraft-fake-llm/1"

    def log_message(self, fmt: str, *args: Any) -> None:  # quiet
        return

    def _send(self, status: int, payload: Any) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path in ("/healthz", "/v1/healthz"):
            return self._send(200, {"status": "ok"})
        if url.path == "/v1/models":
            return self._send(200, {"object": "list", "data": [{"id": m, "object": "model"} for m in MODELS]})
        if url.path == "/_requests":
            q = parse_qs(url.query)
            contains = q.get("contains", [""])[0]
            limit = int(q.get("limit", ["100"])[0])
            with _lock:
                hits = [r for r in _records if contains in json.dumps(r["messages"], ensure_ascii=False)]
            return self._send(200, hits[-limit:])
        return self._send(404, {"error": {"message": "not found"}})

    def do_POST(self) -> None:
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if url.path == "/_reset":
            with _lock:
                _records.clear()
            return self._send(200, {"status": "reset"})
        if url.path == "/v1/chat/completions":
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                return self._send(*error(400, "Body is not JSON.", "invalid_json"))
            headers = {k.lower(): v for k, v in self.headers.items()}
            return self._send(*handle_completion(headers, body))
        return self._send(404, {"error": {"message": "not found"}})


def serve(port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)  # noqa: S104 - test fixture inside a container


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=int(os.environ.get("FAKE_LLM_PORT", "8090")))
    serve(parser.parse_args().port).serve_forever()


if __name__ == "__main__":
    main()
