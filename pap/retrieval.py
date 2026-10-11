"""Local candidate-retrieval primitives for specification v0.6.

The module intentionally has no model or vector-store dependency.  It provides
the deterministic part of the retrieval contract and accepts optional semantic
scores supplied by a future local embedding index.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

NOISE = {"the", "and", "for", "with", "from", "this", "that", "note", "notes", "project", "日报", "周报", "总结", "记录", "内容", "标题"}
REASONS = {"TITLE_ONLY", "STRUCTURE_ONLY", "TEMPLATE_ONLY", "INSUFFICIENT_BODY", "STOPWORD_ONLY_COLLISION", "DUPLICATE_CONTENT", "SAME_FAMILY_TRIVIAL", "SAME_TOPIC_NO_MECHANISM_DELTA", "UNVERIFIED_SOURCE", "COOLDOWN"}


def as_mapping(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return row if hasattr(row, "get") else dict(row)


def stable_int(seed: str, *parts: str) -> int:
    return int.from_bytes(hashlib.sha256("|".join((seed, *parts)).encode()).digest()[:8], "big")


def terms(text: str) -> set[str]:
    latin = re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{2,}", text.lower())
    han = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return set(latin + [s[i:i + 2] for s in han for i in range(len(s) - 1)])


def local_embedding(text: str, *, dimensions: int = 256) -> list[float]:
    """Build a deterministic multilingual local embedding without network I/O.

    This hashing-vector fallback is deliberately modest, but it keeps indexing
    functional when the optional local transformer cannot be loaded.
    """
    vector = [0.0] * dimensions
    features = list(terms(text))
    # Include character trigrams for Chinese and morphology for English.
    normalized = re.sub(r"\s+", " ", text.lower())
    features.extend(normalized[i:i + 3] for i in range(max(0, len(normalized) - 2)))
    for feature in features:
        h = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(h[:4], "big") % dimensions
        vector[index] += -1.0 if h[4] & 1 else 1.0
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


_TRANSFORMER = None
_TRANSFORMER_FAILED = False
TRANSFORMER_MODEL_ID = "intfloat/multilingual-e5-small"


def transformer_embedding(text: str, *, model_id: str = TRANSFORMER_MODEL_ID) -> list[float] | None:
    """Encode with the installed local SentenceTransformers model lazily."""
    global _TRANSFORMER, _TRANSFORMER_FAILED
    if _TRANSFORMER_FAILED:
        return None
    try:
        if _TRANSFORMER is None:
            from sentence_transformers import SentenceTransformer
            _TRANSFORMER = SentenceTransformer(model_id, device="cpu")
        vector = _TRANSFORMER.encode(["passage: " + text], normalize_embeddings=True, show_progress_bar=False)[0]
        return [float(value) for value in vector]
    except Exception:
        _TRANSFORMER_FAILED = True
        return None


def embedding(text: str) -> tuple[str, list[float]]:
    """Return ``(model_id, vector)`` using transformer-first local retrieval."""
    vector = transformer_embedding(text)
    if vector is not None:
        return TRANSFORMER_MODEL_ID, vector
    return "pap-local-hash-v1", local_embedding(text)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b: return 0.0
    # Vectors from different embedding models (e.g. the 256-d hash fallback vs
    # the 384-d transformer) are not comparable; zip() would silently score a
    # truncated dot product. Mixed dimensions score neutral instead.
    if len(a) != len(b): return 0.0
    return max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))


def effective_body(row: Mapping[str, Any]) -> str:
    row = as_mapping(row)
    text = str(row.get("text") or "")
    heading = str(row.get("heading_path") or "").strip()
    # Remove common shell; retain quoted prose and code because they are still
    # evidence, while excluding headings/frontmatter-only fragments.
    body = re.sub(r"^\s*---.*?---\s*", " ", text, flags=re.S)
    body = re.sub(r"^\s*#{1,6}\s+[^\n]+", " ", body)
    body = re.sub(r"`{3}.*?`{3}", " ", body, flags=re.S)
    body = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    if not body and heading:
        return ""
    return body


def time_bucket(row: Mapping[str, Any], now: datetime | None = None) -> str:
    row = as_mapping(row)
    now = now or datetime.now(timezone.utc)
    raw = row.get("timestamps_json") or row.get("timestamps") or "{}"
    if isinstance(raw, str):
        import json
        try: raw = json.loads(raw)
        except Exception: raw = {}
    value = next((v.get("value") for v in raw.values() if isinstance(v, dict) and v.get("value")), None)
    try:
        then = datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
        if then and then.tzinfo is None: then = then.replace(tzinfo=timezone.utc)
        days = (now - then).days if then else 366
    except (TypeError, ValueError):
        days = 366
    return "recent" if days <= 14 else "medium" if days <= 90 else "long" if days <= 365 else "archive"


def domain(row: Mapping[str, Any]) -> str:
    row = as_mapping(row)
    path = str(row.get("source_path") or "")
    return path.split("/", 1)[0] or str(row.get("source_type") or "unknown")


def _event_datetime(row: Mapping[str, Any]) -> datetime | None:
    row = as_mapping(row)
    raw = row.get("timestamps_json") or row.get("timestamps") or {}
    if isinstance(raw, str):
        import json
        try: raw = json.loads(raw)
        except Exception: raw = {}
    for value in raw.values() if isinstance(raw, dict) else ():
        if isinstance(value, dict) and value.get("value"):
            try:
                parsed = datetime.fromisoformat(str(value["value"]).replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


@dataclass
class PairFeatures:
    semantic_similarity: float = 0.0
    lexical_overlap: float = 0.0
    entity_jaccard: float = 0.0
    shared_entity_count: int = 0
    temporal_distance_days: int = 0
    temporal_distance_norm: float = 0.0
    domain_same: bool = False
    domain_distance: float = 0.0
    source_type_same: bool = False
    topic_same: bool = False
    mechanism_delta: float = 0.0
    evidence_quality: float = 0.0
    verification_quality: float = 0.0
    exploration_bonus: float = 0.0
    prior_rejection_penalty: float = 0.0
    prior_delivery_penalty: float = 0.0
    recall_channels: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]: return self.__dict__.copy()


@dataclass
class Rejection:
    candidate_id: str
    reason_code: str
    feature_snapshot: dict[str, Any]


def pair_features(a: Mapping[str, Any], b: Mapping[str, Any], *, channels: Iterable[str] = (), semantic_similarity: float = 0.0, exploration_bonus: float = 0.0) -> PairFeatures:
    a, b = as_mapping(a), as_mapping(b)
    at, bt = terms(str(a.get("heading_path", "")) + " " + str(a.get("text", ""))), terms(str(b.get("heading_path", "")) + " " + str(b.get("text", "")))
    shared = at & bt
    union = at | bt
    same_domain = domain(a) == domain(b)
    ad, bd = _event_datetime(a), _event_datetime(b)
    temporal_days = abs((ad - bd).days) if ad and bd else 0
    # The local fallback uses lexical overlap only as a feature.  A future
    # embedding provider can pass semantic_similarity without changing filters.
    lexical = len(shared) / max(1, len(union))
    return PairFeatures(semantic_similarity=semantic_similarity, lexical_overlap=lexical, entity_jaccard=lexical,
        shared_entity_count=len(shared), temporal_distance_days=temporal_days, temporal_distance_norm=min(1.0, temporal_days / 365.0), domain_same=same_domain, domain_distance=0.0 if same_domain else 1.0,
        source_type_same=a.get("source_type") == b.get("source_type"), topic_same=semantic_similarity >= .90 and lexical >= .50,
        mechanism_delta=0.0 if semantic_similarity >= .90 and lexical >= .50 else min(1.0, abs(len(at)-len(bt))/max(1, len(union))),
        evidence_quality=min(1.0, (len(effective_body(a)) + len(effective_body(b))) / 1000),
        verification_quality=0.0 if (a.get("requires_source_verification") and a.get("verification_state") not in ("verified", "independently_supported")) or (b.get("requires_source_verification") and b.get("verification_state") not in ("verified", "independently_supported")) else 1.0,
        exploration_bonus=exploration_bonus, recall_channels=list(dict.fromkeys(channels)))


def hard_filter(a: Mapping[str, Any], b: Mapping[str, Any], f: PairFeatures, *, min_chars: int = 80, min_tokens: int = 24) -> str | None:
    a, b = as_mapping(a), as_mapping(b)
    for row in (a, b):
        body = effective_body(row)
        if not body:
            return "TITLE_ONLY"
        if len(body) < min_chars and len(terms(body)) < min_tokens:
            return "INSUFFICIENT_BODY"
        shell = str(row.get("text") or "").strip().lower()
        if shell.startswith(("#", "- [ ]", "template:", "status:")) and len(body) < min_chars:
            return "STRUCTURE_ONLY"
        if row.get("template_fingerprint") and len(body) < min_chars:
            return "TEMPLATE_ONLY"
        trusted_derived = row.get("voice") == "system" and row.get("source_type") in {"world_historian_thread", "world_event"}
        if row.get("requires_source_verification") and row.get("verification_state") not in ("verified", "independently_supported") and not trusted_derived:
            return "UNVERIFIED_SOURCE"
    shared = terms(str(a.get("text", ""))) & terms(str(b.get("text", "")))
    if shared and all(x in NOISE for x in shared) and set(f.recall_channels) <= {"lexical", "bm25"}:
        return "STOPWORD_ONLY_COLLISION"
    if (a.get("content_hash") and a.get("content_hash") == b.get("content_hash")) or (a.get("normalized_hash") and a.get("normalized_hash") == b.get("normalized_hash")) or a.get("evidence_id") == b.get("evidence_id"):
        return "DUPLICATE_CONTENT"
    if a.get("evidence_family_id") == b.get("evidence_family_id"):
        return "SAME_FAMILY_TRIVIAL"
    if f.topic_same and f.mechanism_delta <= .10 and f.semantic_similarity >= .90 and f.entity_jaccard >= .50:
        return "SAME_TOPIC_NO_MECHANISM_DELTA"
    return None


def rrf(rank: int, k: int = 60) -> float: return 1.0 / (k + max(1, rank))


def rank_score(f: PairFeatures, *, profile: str = "serendipity") -> float:
    channels = set(f.recall_channels)
    score = sum(rrf(i + 1) for i, _ in enumerate(channels))
    score += .18 * f.domain_distance + .14 * f.temporal_distance_norm + .14 * f.mechanism_delta + .10 * f.evidence_quality + .10 * f.exploration_bonus
    if profile == "serendipity": score -= .20 * int(f.topic_same)
    else: score += .25 * f.verification_quality
    return score - .25 * f.prior_rejection_penalty - .20 * f.prior_delivery_penalty


def decaying_penalty(base: float, age_days: float, half_life_days: float = 14.0) -> float:
    return base * math.exp(-max(0.0, age_days) / half_life_days)


def pair_family_key(a: str, b: str, channel: str = "") -> str:
    return hashlib.sha256("|".join(sorted((a, b)) + [channel]).encode()).hexdigest()


def cooldown_duration_hours(reject_count: int, *, scope_kind: str) -> int:
    if scope_kind == "anchor":
        return (24, 72, 168, 336)[min(max(reject_count, 1) - 1, 3)]
    if scope_kind == "template":
        return 168 if reject_count < 5 else 720
    return (72, 168, 336)[min(max(reject_count, 1) - 1, 2)]


def cooldown_active(cooldown_until: str | None, *, now: datetime | None = None) -> bool:
    if not cooldown_until:
        return False
    now = now or datetime.now(timezone.utc)
    try:
        until = datetime.fromisoformat(cooldown_until.replace("Z", "+00:00"))
        if until.tzinfo is None: until = until.replace(tzinfo=timezone.utc)
        return until > now
    except ValueError:
        return False


def update_cooldown(reject_count: int, *, scope_kind: str, base_penalty: float = 1.0, at: datetime | None = None) -> dict[str, Any]:
    at = at or datetime.now(timezone.utc)
    from datetime import timedelta
    hours = cooldown_duration_hours(reject_count, scope_kind=scope_kind)
    return {"reject_count": reject_count, "cooldown_until": (at + timedelta(hours=hours)).isoformat(timespec="seconds"), "penalty": base_penalty}


def select_stratified(rows: list[Mapping[str, Any]], *, seed: str, limit: int, state: Mapping[str, Mapping[str, Any]] | None = None, max_per_family: int = 1) -> list[Mapping[str, Any]]:
    rows = [as_mapping(r) for r in rows]
    state = state or {}
    weights = {"recent": .30, "medium": .25, "long": .25, "archive": .20}
    groups: dict[str, list[Mapping[str, Any]]] = {k: [] for k in weights}
    for row in rows: groups[time_bucket(row)].append(row)
    selected: list[Mapping[str, Any]] = []; families: dict[str, int] = {}
    ordered = [(k, groups[k]) for k in weights]
    for bucket, group in ordered:
        group.sort(key=lambda r: (state.get(str(r.get("evidence_family_id")), {}).get("explore_count", 0), state.get(str(r.get("evidence_family_id")), {}).get("last_explored_at") or "", stable_int(seed, str(r.get("evidence_family_id")), str(r.get("evidence_id")))))
        quota = max(1, round(limit * weights[bucket])) if group else 0
        for row in group[:quota]:
            fam = str(row.get("evidence_family_id"))
            if families.get(fam, 0) >= max_per_family: continue
            selected.append(row); families[fam] = families.get(fam, 0) + 1
    remaining = sorted((r for r in rows if r not in selected), key=lambda r: stable_int(seed, str(r.get("evidence_id"))))
    for row in remaining:
        if len(selected) >= limit: break
        fam = str(row.get("evidence_family_id"))
        if families.get(fam, 0) < max_per_family: selected.append(row); families[fam] = families.get(fam, 0) + 1
    return selected[:limit]
