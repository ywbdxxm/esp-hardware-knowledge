"""Fail-closed evidence grading independent of retrieval rank."""

from __future__ import annotations

import re

from espdocs.models import EvidenceDecision

_HIGH_RISK_PATTERNS = (
    (
        re.compile(r"\b[A-Z][A-Z0-9_]*_REG\b|寄存器地址|复位值|位域|保留位", re.IGNORECASE),
        "register_detail",
    ),
    (
        re.compile(r"电压|电流|功耗|绝对最大|额定值|射频|阻抗", re.IGNORECASE),
        "electrical_parameter",
    ),
    (re.compile(r"时序|延时|频率|MHz|kHz|ns|us|μs", re.IGNORECASE), "timing_parameter"),
    (re.compile(r"引脚|管脚|pin|启动|boot|strap", re.IGNORECASE), "pin_or_boot_configuration"),
    (re.compile(r"efuse|安全|加密|烧录|flash", re.IGNORECASE), "security_or_flashing"),
)


def classify_evidence(
    *,
    query: str,
    content_type: str,
    warnings: tuple[str, ...],
    version: str,
    verified: bool,
) -> EvidenceDecision:
    reasons: list[str] = []
    if version == "unknown":
        reasons.append("unknown_document_version")
    if not verified:
        reasons.append("unverified_corpus_page")
    reasons.extend(warning for warning in warnings if warning not in reasons)
    if content_type in {"table", "picture"}:
        reasons.append(f"visual_content:{content_type}")
    for pattern, reason in _HIGH_RISK_PATTERNS:
        if pattern.search(query):
            reasons.append(reason)
    unique_reasons = tuple(dict.fromkeys(reasons))
    if unique_reasons:
        return EvidenceDecision("C", True, unique_reasons)
    return EvidenceDecision("B", False, ())
