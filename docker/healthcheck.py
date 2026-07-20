#!/usr/bin/env python3
"""Docker 容器健康检查"""
import httpx
import sys

try:
    resp = httpx.get("http://localhost:8765/api/health", timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("status") == "ok":
            sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
