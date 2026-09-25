"""新颖性检索客户端包（协议第八节）。

* :mod:`src.search.crossref_client`        —— Crossref REST API
* :mod:`src.search.semantic_scholar_client` —— Semantic Scholar Graph API

Google Scholar 无稳定公开 API，以**人工/半自动**方式检索并在检索日志中
**如实标注为人工检索**。
"""

from .crossref_client import CrossrefClient
from .semantic_scholar_client import SemanticScholarClient

__all__ = ["CrossrefClient", "SemanticScholarClient"]
