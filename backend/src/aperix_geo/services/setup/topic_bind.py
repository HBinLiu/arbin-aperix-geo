"""将 candidate_queries 绑定到已选定的业务主题（确定性分桶，不按 decision_type）。"""

from __future__ import annotations

from aperix_geo.services.competitor.topic_types import (
    MIN_SEED_QUERIES_PER_TOPIC,
    MAX_MONITORING_TOPICS,
    CandidateQuery,
    SeedQuery,
    TopicCluster,
)

_MAX_SEEDS_PER_TOPIC = 8


def _query_terms(query: CandidateQuery) -> list[str]:
    terms = [str(query.get("text") or "")]
    terms.extend(str(t) for t in (query.get("seed_terms") or []) if str(t).strip())
    return terms


def _score_query_for_topic(*, query: CandidateQuery, topic_name: str) -> int:
    name = topic_name.strip()
    if not name:
        return 0
    score = 0
    name_cf = name.casefold()
    for raw in _query_terms(query):
        text = raw.strip()
        if not text:
            continue
        text_cf = text.casefold()
        if name_cf in text_cf:
            score += len(name) * 2
        # 主题名片段（≥2 字）命中问句
        for length in range(min(len(name), 8), 1, -1):
            for start in range(0, len(name) - length + 1):
                fragment = name[start : start + length].casefold()
                if len(fragment) >= 2 and fragment in text_cf:
                    score += length
                    break
    return score


def bind_queries_to_topics(
    topic_names: list[str],
    candidate_queries: list[CandidateQuery],
) -> list[TopicCluster]:
    """按语义重叠将问句分配到业务主题；每簇保留 intent/funnel/decision_type 供 Prompt 阶段使用。"""
    names = [n.strip() for n in topic_names if n.strip()][:MAX_MONITORING_TOPICS]
    if len(names) != MAX_MONITORING_TOPICS:
        raise ValueError(f"监测主题必须恰好 {MAX_MONITORING_TOPICS} 条")

    buckets: list[list[CandidateQuery]] = [[] for _ in names]
    if not candidate_queries:
        raise ValueError("候选问句为空，无法绑定主题")

    ranked: list[tuple[int, int, CandidateQuery]] = []
    for query in candidate_queries:
        scores = [_score_query_for_topic(query=query, topic_name=name) for name in names]
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        ranked.append((scores[best_idx], best_idx, query))
    ranked.sort(key=lambda row: row[0], reverse=True)

    counts = [0] * len(names)
    for score, idx, query in ranked:
        if counts[idx] >= _MAX_SEEDS_PER_TOPIC:
            continue
        buckets[idx].append(query)
        counts[idx] += 1

    # 补足 MIN_SEED_QUERIES_PER_TOPIC
    for idx, bucket in enumerate(buckets):
        if len(bucket) >= MIN_SEED_QUERIES_PER_TOPIC:
            continue
        for _, other_idx, query in ranked:
            if other_idx == idx or query in bucket:
                continue
            if counts[idx] >= _MAX_SEEDS_PER_TOPIC:
                break
            if _score_query_for_topic(query=query, topic_name=names[idx]) <= 0:
                continue
            bucket.append(query)
            counts[idx] += 1
            if len(bucket) >= MIN_SEED_QUERIES_PER_TOPIC:
                break
        while len(bucket) < MIN_SEED_QUERIES_PER_TOPIC:
            for _, _, query in ranked:
                if query in bucket or counts[idx] >= _MAX_SEEDS_PER_TOPIC:
                    continue
                bucket.append(query)
                counts[idx] += 1
                if len(bucket) >= MIN_SEED_QUERIES_PER_TOPIC:
                    break
            else:
                raise ValueError(f"主题「{names[idx]}」种子问句不足 {MIN_SEED_QUERIES_PER_TOPIC} 条")

    clusters: list[TopicCluster] = []
    for name, bucket in zip(names, buckets, strict=True):
        seeds: list[SeedQuery] = []
        seen_text: set[str] = set()
        for query in bucket[:_MAX_SEEDS_PER_TOPIC]:
            text = str(query.get("text") or "").strip()
            if not text or text in seen_text:
                continue
            seen_text.add(text)
            seeds.append(
                SeedQuery(
                    text=text,
                    intent=str(query.get("intent") or "commercial").strip().lower(),
                    funnel=str(query.get("funnel") or "mofu").strip().lower(),
                    decision_type=str(query.get("decision_type") or "scenario_fit").strip().lower(),
                )
            )
        if len(seeds) < MIN_SEED_QUERIES_PER_TOPIC:
            raise ValueError(f"主题「{name}」种子问句不足 {MIN_SEED_QUERIES_PER_TOPIC} 条")
        clusters.append(TopicCluster(name=name, seed_queries=seeds))
    return clusters
