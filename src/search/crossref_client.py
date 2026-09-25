"""Crossref REST API 客户端。

**文档核验记录（2026-09-25，写码前完成）**

| 项 | 核验结论 | 来源 |
| :--- | :--- | :--- |
| 端点 | ``https://api.crossref.org/works`` | Crossref REST API 文档 |
| 认证 | **无需认证**（公开端点） | 同上 |
| Polite pool | 在 URL 附 ``mailto=`` 参数即进入 polite pool，获得更稳定的服务质量 | Crossref "polite pool" 说明 |
| 分页 | ``rows``（单页条数，上限 1000）+ ``offset``（偏移） | 同上 |
| 速率 | polite pool 下无硬性限速，但**不得滥用**；本实现固定请求间隔 | 同上 |
| 主要响应字段 | ``message.total-results``、``message.items[].DOI`` / ``title`` / ``issued`` / ``container-title`` / ``type`` | 实测响应 |

**实测**：``query=seismic+denoising&rows=1`` 返回 ``total-results = 217403``（2026-09-25），
说明端点与参数均有效。

**缓存**：所有响应落盘至 ``docs/bibliography/raw/``，同一请求**不得重复打网**
（重试与复跑均读缓存）。
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

__all__ = ["CrossrefClient"]

API_ROOT = "https://api.crossref.org/works"
# Crossref polite pool：附 mailto 即获更稳服务。此处用项目联系邮箱占位，
# 不含任何凭据（凭据类信息一律不得入库，见 P0.6-Am1 第一节）。
POLITE_MAILTO = "seismic-denoise-bench@example.org"


class CrossrefClient:
    """带落盘缓存的 Crossref 检索客户端。"""

    def __init__(self, raw_dir: Path, min_interval_s: float = 1.0) -> None:
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval_s = min_interval_s
        self._last_request_at = 0.0

    # -- 缓存 ---------------------------------------------------------------
    def _cache_path(self, query: str, rows: int, offset: int) -> Path:
        key = hashlib.sha256(
            f"crossref|{query}|{rows}|{offset}".encode("utf-8")
        ).hexdigest()[:16]
        return self.raw_dir / f"crossref_{key}.json"

    # -- 请求 ---------------------------------------------------------------
    def search(self, query: str, rows: int = 100, offset: int = 0) -> dict:
        """检索并返回**原始响应 JSON**（原样保存，不得改写）。

        同一 ``(query, rows, offset)`` 组合命中缓存则直接读取，不再打网。
        """
        cache = self._cache_path(query, rows, offset)
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8"))

        elapsed = time.time() - self._last_request_at
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)

        params = urllib.parse.urlencode(
            {"query": query, "rows": rows, "offset": offset, "mailto": POLITE_MAILTO}
        )
        url = f"{API_ROOT}?{params}"

        request = urllib.request.Request(url, headers={"User-Agent": "seismic-denoise-bench/0.0.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self._last_request_at = time.time()
        cache.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    # -- 题录提取 -----------------------------------------------------------
    @staticmethod
    def to_records(payload: dict, query_line: str, track: str) -> list[dict]:
        """把原始响应转成结构化题录行（不做相关性分析）。"""
        records: list[dict] = []
        items = payload.get("message", {}).get("items", []) or []
        for item in items:
            titles = item.get("title") or []
            container = item.get("container-title") or []
            issued = (item.get("issued") or {}).get("date-parts") or [[None]]
            year = issued[0][0] if issued and issued[0] else None
            records.append(
                {
                    "doi": item.get("DOI") or "",
                    "title": (titles[0] if titles else "").strip(),
                    "year": year if year is not None else "",
                    "venue": (container[0] if container else "").strip(),
                    "source_db": "crossref",
                    "query_line": query_line,
                    "track": track,
                    "relevance_flag": "",
                    "note": "",
                }
            )
        return records
