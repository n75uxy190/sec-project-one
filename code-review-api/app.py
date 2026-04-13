"""
code-review-api/app.py

Helix Code Review API — automated PR review via AI gateway.
"""

import logging
import os
import requests
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [code-review-api] %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

app   = Flask(__name__)
GW    = os.environ.get("GATEWAY_URL", "http://ai-gateway:12434")
MODEL = "ai/smollm2"


@app.route("/")
def index():
    return jsonify({"service": "helix-code-review", "version": "3.4.1", "status": "ok"})


@app.route("/review", methods=["POST"])
def review():
    body = request.get_json(force=True, silent=True) or {}
    diff = body.get("diff", "")
    pr   = body.get("pr_id", "unknown")
    if not diff:
        return jsonify({"error": "diff required"}), 400
    log.info(f"Reviewing PR #{pr} ({len(diff)} chars)")
    try:
        r = requests.post(f"{GW}/engines/llama.cpp/v1/chat/completions", json={
            "model": MODEL,
            "messages": [
                {"role": "system",  "content": "You are a senior engineer reviewing a PR. Be concise."},
                {"role": "user",    "content": f"Review this diff:\n\n{diff}"},
            ],
        }, timeout=30)
        comment = r.json()["choices"][0]["message"]["content"]
        log.info(f"Review done for PR #{pr}")
        return jsonify({"pr_id": pr, "comment": comment, "model": MODEL})
    except Exception as e:
        log.error(f"Gateway error: {e}")
        return jsonify({"error": str(e)}), 502


if __name__ == "__main__":
    log.info("code-review-api starting on :5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
