"""
ai-gateway/server.py

helix AI gateway — internal model inference service.
wraps the llama.cpp inference backend
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone

from flask import Flask, jsonify, request

class _JsonFormatter(logging.Formatter):
    def format(self, record):
        e = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "service": "ai-gateway",
            "version": "1.0.14",
            "msg":     record.getMessage(),
        }
        if hasattr(record, "extra"):
            e.update(record.extra)
        return json.dumps(e)

_h = logging.StreamHandler()
_h.setFormatter(_JsonFormatter())
log = logging.getLogger("ai-gateway")
log.setLevel(logging.INFO)
log.addHandler(_h)
log.propagate = False

app = Flask(__name__)
app.logger.handlers = []

_models = {
    "ai/smollm2": {
        "id": "ai/smollm2", "object": "model",
        "created": 1744000000, "context_length": 4096,
        "quantization": "Q4_K_M", "backend": "llama.cpp",
    }
}
_engine_flags: list[str] = ["--threads", "4", "--ctx-size", "4096", "--log-disable"]


@app.route("/healthz")
def health():
    return jsonify({
        "status": "ok", "version": "1.0.14", "uptime_s": 14832,
        "engines": {"llama.cpp": "running"},
    })

@app.route("/models")
def models():
    return jsonify({"object": "list", "data": list(_models.values())})

@app.route("/models/create", methods=["POST"])
def models_create():
    body = request.get_json(force=True, silent=True) or {}
    src = body.get("from", "")
    _models[src] = {"id": src, "object": "model",
                    "created": int(datetime.now().timestamp()),
                    "context_length": 4096, "quantization": "Q4_K_M", "backend": "llama.cpp"}
    log.info("model pulled", extra={"extra": {"model": src}})
    return jsonify({"status": "ok", "model": src}), 201

@app.route("/metrics")
def metrics():
    return (
        "# HELP gateway_requests_total\n# TYPE gateway_requests_total counter\n"
        'gateway_requests_total{engine="llama.cpp",model="ai/smollm2"} 312\n'
        "# HELP gateway_tokens_total\n# TYPE gateway_tokens_total counter\n"
        'gateway_tokens_total{model="ai/smollm2"} 84291\n'
        "# HELP gateway_active_slots\n# TYPE gateway_active_slots gauge\n"
        "gateway_active_slots 0\n"
    ), 200, {"Content-Type": "text/plain; version=0.0.4"}

@app.route("/engines/llama.cpp/v1/chat/completions", methods=["POST"])
@app.route("/engines/v1/chat/completions", methods=["POST"])
@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    body  = request.get_json(force=True, silent=True) or {}
    model = body.get("model", "ai/smollm2")
    msgs  = body.get("messages", [])
    last  = next((m["content"] for m in reversed(msgs) if m.get("role") == "user"), "")
    log.info("inference", extra={"extra": {"model": model, "n_messages": len(msgs)}})
    return jsonify({
        "id": "chatcmpl-hxgw0001", "object": "chat.completion",
        "created": int(datetime.now().timestamp()), "model": model,
        "choices": [{"index": 0,
                     "message": {"role": "assistant",
                                 "content": f"[gateway response to: '{last[:50]}']"},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 14, "completion_tokens": 22, "total_tokens": 36},
    })

@app.route("/engines/_configure", methods=["POST"])
def engine_configure():
    global _engine_flags
    body  = request.get_json(force=True, silent=True) or {}
    flags = body.get("flags", [])

    log.info("engine configuration updated", extra={"extra": {
        "endpoint":    "/engines/_configure",
        "flags_count": len(flags),
        "remote_addr": request.remote_addr,
        "method":      request.method,
    }})

    _engine_flags = list(flags)
    _apply_flags(flags)
    return jsonify({
        "status": "ok", "engine": "llama.cpp",
        "flags": _engine_flags,
        "note": "configuration applied; will persist until next restart",
    })


def _apply_flags(flags: list[str]):
    log_path = _flag_val(flags, "--log-file")
    if not log_path:
        return
    try:
        parent = os.path.dirname(log_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with open(log_path, "a") as f:
            f.write(
                f"llama_model_load: version=3 vocab_type=1 n_vocab=32768\n"
                f"llama_init_from_model: n_ctx={_flag_val(flags,'--ctx-size','4096')}"
                f" n_batch=2048 n_threads={_flag_val(flags,'--threads','4')}\n"
                f"llm_load_tensors: ggml_backend_buffer_type_alloc_buffer: backend=0\n"
                f"srv  log started ts={ts} path={log_path}\n"
            )
        subprocess.run(["echo", f"[{ts}] llama.cpp log init → {log_path}"], check=False)
        log.warning("llama.cpp log-file flag applied", extra={"extra": {"log_path": log_path}})
    except Exception as exc:
        log.error("flag apply error", extra={"extra": {"error": str(exc)}})


def _flag_val(flags, name, default=""):
    for i, f in enumerate(flags):
        if f == name and i + 1 < len(flags):
            return flags[i + 1]
    return default


if __name__ == "__main__":
    log.info("ai-gateway starting", extra={"extra": {"listen": "0.0.0.0:12434"}})
    app.run(host="0.0.0.0", port=12434, debug=False)
