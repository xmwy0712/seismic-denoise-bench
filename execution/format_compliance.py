"""格式合规机器门（P5.5-Am2 起强制；不再依赖"自检清单"）。

用法::

    python execution/format_compliance.py --doc docs/paper/draft-v6.md

**核心新增门（第四次违规后机械堵死）**
--------------------------------------
`G-fig-order` / `G-tab-order`：**编号顺序必须等于文档首次提及顺序**。
判据不是"嵌入行递增"，而是：把全文按出现顺序扫一遍，记录每个编号**首次出现**的次序，
该次序必须恰为 `1, 2, …, N`。参考行、alt 文本、题注**任一处**先出现都算首提，
因此"把图插到了前文"立刻能被抓到。

退出码：全部门通过 0；任一 FAIL 非 0（可直接用作交付门禁）。

`G-reader`（P5.7 起常驻，每版必跑）：读者形态门 —— 正文（附录 B 登记表除外）不得出现
「留待 / 终稿决定 / 候选标题 / 标题说明 / 须记录 / 须报告 / 更正说明 / 本文早期版本 /
本文初稿 / 初稿 v / 上一版 / 本版 / 治理 / change log / cover letter / 盲评」；
结构门：第 1 行即标题、其下不得有引注块、首个二级标题为「摘要」、不得存在「## 0.」类小节。
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PATH_PAT = [r"configs/", r"docs/", r"results/", r"\.yaml", r"\.md", r"\.csv"]
META_WORDS = ["如实", "不得择优", "签发", "裁定", "不可下放", "并列给出", "不作调换",
              "主次关系", "用户", "盲评", "本单", "任务单", "归档件", "并列报告", "本阶段"]


def first_mention_order(text: str, kind: str) -> list[int]:
    """按**首次出现**位置返回编号次序（kind ∈ {'图','表'}）。"""
    seen, order = set(), []
    for m in re.finditer(rf"{kind} (\d+)", text):
        n = int(m.group(1))
        if n not in seen:
            seen.add(n)
            order.append(n)
    return order


def check(doc: Path) -> tuple[list[tuple[str, bool, str]], bool]:
    t = doc.read_text(encoding="utf-8")
    body = t.split("## 附录 B")[0]
    res: list[tuple[str, bool, str]] = []

    # ── G-fig-order：图号顺序 == 首提顺序
    fo = first_mention_order(t, "图")
    res.append(("G-fig-order", fo == list(range(1, len(fo) + 1)),
                f"首提顺序 = {fo}；应 = 1..{len(fo)}"))

    # ── G-tab-order：表号顺序 == 首提顺序（表 A.x / B.x 除外）
    to = [n for n in first_mention_order(t, "表")]
    res.append(("G-tab-order", to == list(range(1, len(to) + 1)),
                f"首提顺序 = {to}；应 = 1..{len(to)}"))

    # ── G-embed-order：嵌入行顺序递增
    eseq = [int(m.group(1)) for m in re.finditer(r"!\[图 (\d)", t)]
    res.append(("G-embed-order", eseq == list(range(1, len(eseq) + 1)),
                f"嵌入顺序 = {eseq}"))

    # ── G-caption-order：题注顺序递增
    cseq = [int(m.group(1)) for m in re.finditer(r"\*\*图 (\d)\*\*", t)]
    res.append(("G-caption-order", cseq == list(range(1, len(cseq) + 1)),
                f"题注顺序 = {cseq}"))

    # ── G-embed-caption-pair：每条嵌入的 alt 号 == 紧随其后的题注号
    lines = t.split("\n")
    pair_bad = []
    for i, ln in enumerate(lines):
        m = re.match(r"!\[图 (\d)", ln)
        if not m:
            continue
        nxt = next((lines[j] for j in range(i + 1, min(i + 3, len(lines)))
                    if lines[j].startswith("**图")), "")
        m2 = re.match(r"\*\*图 (\d)\*\*", nxt)
        if not m2 or m2.group(1) != m.group(1):
            pair_bad.append(i + 1)
    res.append(("G-embed-caption-pair", not pair_bad,
                f"不配对行 = {pair_bad if pair_bad else '无'}"))

    # ── G-embed-exists：嵌入路径实存
    paths = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", t)
    miss = [p for p in paths if not (doc.parent / p).exists()]
    res.append(("G-embed-exists", not miss, f"缺失 = {miss if miss else '无'}（共 {len(paths)} 条）"))

    # ── G-appendix-figmap：附录图目录编号与文件名一致
    tabel = re.findall(r"^\|\s*图 (\d+)\s*\|\s*`([^`]+)`", t, re.M)
    map_bad = []
    for n, fn in tabel:
        m = re.match(r"fig(\d+)_", fn)
        if not m or m.group(1) != n:
            map_bad.append((n, fn))
    res.append(("G-appendix-figmap", not map_bad, f"编号/文件名不符 = {map_bad if map_bad else '无'}（共 {len(tabel)} 行）"))

    # ── G-tag：无 \tag
    ntag = len(re.findall(r"\\tag\{", t))
    res.append(("G-tag", ntag == 0, f"\\tag{{ 出现 = {ntag}"))

    # ── G-eq-number：编号连续且各恰一次
    seq = re.findall(r"\\qquad \((\d+)\)", t)
    ok = seq == [str(i) for i in range(1, len(seq) + 1)] and len(set(seq)) == len(seq)
    res.append(("G-eq-number", ok, f"编号 = 1..{len(seq)}，唯一 = {len(set(seq)) == len(seq)}"))

    # ── G-block-count：$$ 块数 == 公式编号数
    blocks = t.count("$$") // 2
    res.append(("G-block-count", blocks == len(seq), f"$$ 块 = {blocks}；编号数 = {len(seq)}"))

    # ── G-no-path：正文无路径/文件名
    npath = sum(len([l for l in body.split("\n") if re.search(p, l)]) for p in PATH_PAT)
    res.append(("G-no-path", npath == 0, f"正文命中 = {npath}"))

    # ── G-no-meta：正文无元话语词
    nmeta = sum(t.count(w) for w in META_WORDS)
    res.append(("G-no-meta", nmeta == 0, f"命中 = {nmeta}"))

    # ── G-cite-ref：引用 ↔ 文献表一一对应
    cited = sorted({int(m) for m in re.findall(r"\[(\d)\]", t)})
    listed = sorted({int(m) for m in re.findall(r"^\[(\d)\] ", t, re.M)})
    res.append(("G-cite-ref", cited == listed, f"正文 {cited} / 文献表 {listed}"))

    # ── G-reader-terms：读者形态词表（正文；附录 B 登记表除外）
    lines_all = t.split("\n")
    try:
        b_start = next(i for i, l in enumerate(lines_all)
                       if l.startswith("## 附录 B") or l.startswith("## Appendix B"))
    except StopIteration:
        b_start = len(lines_all)
    # 附录 B 整节排除（其内容本身就是修订登记；门自述范围 =「正文（附录 B 登记表除外）」）
    scan_lines = lines_all[:b_start]
    reader_words = ["留待", "终稿决定", "候选标题", "标题说明", "须记录", "须报告", "更正说明",
                    "本文早期版本", "本文初稿", "初稿 v", "上一版", "本版", "治理",
                    "change log", "cover letter", "盲评",
                    # P5.9 扩充：过程语言与自我指令式标签
                    "须写明", "不夸大", "删循环论证", "表述升级", "排查",
                    "本批之前", "自本批起", "此处更正", "口径更正说明", "修订史"]
    rhits = [(w, i + 1) for i, l in enumerate(scan_lines) for w in reader_words if w in l]
    res.append(("G-reader-terms", not rhits,
                f"命中 = {rhits[:5] if rhits else '无'}（词表 {len(reader_words)} 项；附录 B 登记表已排除）"))

    # ── G-reader-structure：第 1 行标题 / 无引注块 / 首个二级标题为摘要 / 无 ## 0.
    l0 = lines_all[0]
    title_ok = l0.startswith("# ")
    h2 = [l for l in lines_all if l.startswith("## ")]
    first_h2_ok = bool(h2) and (h2[0].startswith("## 摘要") or h2[0].startswith("## Abstract"))
    no_zero = not any(l.startswith("## 0.") for l in lines_all)
    pre = "\n".join(lines_all[:max(1, next((i for i, l in enumerate(lines_all)
                                            if l.startswith("## ")), len(lines_all)))])
    no_quote = not any(l.startswith(">") for l in pre.split("\n"))
    struct_ok = title_ok and first_h2_ok and no_zero and no_quote
    res.append(("G-reader-structure", struct_ok,
                f"标题行={title_ok} 首个二级标题=摘要:{first_h2_ok} 无##0.:{no_zero} 标题块无引注:{no_quote}"))

    # ── G-table-continuity：表格块不得被空行或非表格行切断
    tlines = t.split("\n")
    runs, cur = [], []
    for _i, _l in enumerate(tlines):
        if _l.startswith("|"):
            cur.append(_i)
        else:
            if cur:
                runs.append(cur)
                cur = []
    if cur:
        runs.append(cur)
    split_at = []
    for _a, _b in zip(runs, runs[1:]):
        _ca = tlines[_a[0]].count("|")
        _cb = tlines[_b[0]].count("|")
        between = tlines[_a[-1] + 1:_b[0]]
        has_anchor = any(x.startswith("#") or x.startswith("**表 ") or x.startswith("**图 ")
                         for x in between)
        if _ca == _cb and not has_anchor:
            split_at.append((_a[-1] + 2, _b[0] + 1))
    bad_sep = [_a[1] + 1 for _a in runs
               if len(_a) >= 3 and not re.fullmatch(r"\|[\s:|-]+\|", tlines[_a[1]])]
    tcont_ok = (not split_at) and (not bad_sep)
    res.append(("G-table-continuity", tcont_ok,
                f"表格块 = {len(runs)}；疑似断裂 = {split_at[:3] if split_at else '无'}；"
                f"分隔行异常 = {bad_sep[:3] if bad_sep else '无'}"))

    # ── G-encoding：无 BOM、纯 LF
    b = doc.read_bytes()
    res.append(("G-encoding", (not b.startswith(b"\xef\xbb\xbf")) and b.count(bytes([13])) == 0,
                f"BOM={b[:3] == b'\xef\xbb\xbf'} CR={b.count(bytes([13]))}"))

    return res, all(ok for _n, ok, _d in res)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="格式合规机器门")
    ap.add_argument("--doc", default="docs/paper/draft-v6.md")
    a = ap.parse_args(argv)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    doc = REPO / a.doc
    res, ok = check(doc)
    print(f"=== 格式合规机器门 · {a.doc} ===")
    for n, good, d in res:
        print(f"  {'PASS' if good else 'FAIL'}  {n:24} {d}")
    print()
    print(f"  总判定 = {'PASS（全部门通过）' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
