"""Semantic Scholar Graph API 客户端（含退避重试与落盘缓存）。

**文档核验记录（2026-09-25，写码前完成）**

| 项 | 核验结论 | 来源 |
| :--- | :--- | :--- |
| 端点 | ``https://api.semanticscholar.org/graph/v1/paper/search`` | S2 Graph API 文档 |
| 认证 | 无 key 可用但限额极低；**带 key 限额更高** | S2 API 文档 |
| 实测（无 key） | 首次请求即 **HTTP 429**；直连与经 socks5 代理**均 429** | 本地实测 2026-09-25 |
| 实测（带 key） | 见 execution-log 的实测结论 | 本地实测 2026-09-25 |
| 速率 | 官方文档：**1 请求/秒**（带 key） | S2 文档 |
| 分页 | ``limit``（单页上限 100）+ ``offset`` | S2 文档 |
| 主要字段 | ``total``、``data[].title`` / ``year`` / ``venue`` / ``externalIds.DOI`` | 实测响应 |

**缓存**：所有响应（含失败响应）落盘至 ``docs/bibliography/raw/``，
同一请求**不得重复打网**；重试与复跑均读缓存。

**凭据处理（P0.6-Am1 第一节）**：API key 从环境变量 ``S2_API_KEY`` 读取，
**绝不写入任何入库文件**（不写进代码、日志、CSV、响应缓存）。
请求头中的 key 在缓存落盘前剥离。

**不伪造**：某线可核验题录不足时，如实报告实际条数并记入覆盖限制
（P0.6-Am1 第二节第 3 条）。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

__all__ = ["SemanticScholarClient"]

API_ROOT = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,year,venue,externalIds"

# 环境变量名（值不落盘、不打印）
ENV_KEY_NAME = "S2_API_KEY"


class SemanticScholarClient:
    """带退避重试与落盘缓存的 Semantic Scholar 检索客户端。"""

    def __init__(
        self,
        raw_dir: Path,
        min_interval_s: float = 1.2,
        max_retries: int = 5,
        use_api_key: bool = True,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval_s = min_interval_s
        self.max_retries = max_retries
        self.use_api_key = use_api_key
        self._last_request_at = 0.0

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": "seismic-denoise-bench/0.0.0"}
        if self.use_api_key:
            key = os.environ.get(ENV_KEY_NAME)
            if key:
                # 仅放入请求头；不打印、不落盘
                headers["x-api-key"] = key
        return headers

    def _cache_path(self, query: str, limit: int, offset: int) -> Path:
        key = hashlib.sha256(
            f"s2|{query}|{limit}|{offset}".encode("utf-8")
        ).hexdigest()[:16]
        return self.raw_dir / f"s2_{key}.json"

    def search(self, query: str, limit: int = 100, offset: int = 0) -> dict:
        """检索并返回原始响应 JSON；命中缓存则不再打网。"""
        cache = self._cache_path(query, limit, offset)
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8"))

        params = urllib.parse.urlencode(
            {"query": query, "limit": limit, "offset": offset, "fields": FIELDS}
        )
        url = f"{API_ROOT}?{params}"

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            elapsed = time.time() - self._last_request_at
            wait = max(0.0, self.min_interval_s - elapsed)
            if wait:
                time.sleep(wait)

            try:
                request = urllib.request.Request(url, headers=self._headers())
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self._last_request_at = time.time()
                cache.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                return payload
            except urllib.error.HTTPError as exc:
                last_error = exc
                self._last_request_at = time.time()
                # 429 / 5xx 可重试；其余立即抛出
                if exc.code == 429 or 500 <= exc.code < 600:
                    time.sleep(min(self.min_interval_s * (2**attempt), 60.0))
                    continue
                raise
            except Exception as exc:  # noqa: BLE001 - 网络层异常统一退避
                last_error = exc
                self._last_request_at = time.time()
                time.sleep(min(self.min_interval_s * (2**attempt), 60.0))

        raise RuntimeError(
            f"Semantic Scholar 检索在 {self.max_retries} 次尝试后仍未成功：{last_error}"
        )

    @staticmethod
    def to_records(payload: dict, query_line: str, track: str) -> list[dict]:
        """把原始响应转成结构化题录行（不做相关性分析）。"""
        records: list[dict] = []
        for item in payload.get("data", []) or []:
            external = item.get("externalIds") or {}
            records.append(
                {
                    "doi": external.get("DOI") or "",
                    "title": (item.get("title") or "").strip(),
                    "year": item.get("year") if item.get("year") is not None else "",
                    "venue": (item.get("venue") or "").strip(),
                    "source_db": "semantic_scholar",
                    "query_line": query_line,
                    "track": track,
                    "relevance_flag": "",
                    "note": "",
                }
            )
        return records
