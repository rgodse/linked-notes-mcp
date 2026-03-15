"""Seed context ingestion helpers for linked-notes-mcp.

This module implements a staged ingestion flow:

1. sources are registered into an ingestion run
2. candidate memory nodes are extracted deterministically
3. candidates are reviewed before promotion into the graph
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .common import (
    candidate_recommendation_label,
    infer_entity_type,
    infer_summary,
    load_json_file,
    normalize_space,
    save_json_file,
)
from .graph import KnowledgeGraph, Note
from .parser import (
    extract_aliases,
    extract_relationships,
    extract_tags,
    extract_title,
    normalize_id,
    parse_frontmatter,
)


@dataclass
class IngestionArtifact:
    id: str
    run_id: str
    source_type: str
    source_ref: str
    checksum: str
    project: str | None
    created_at: str


@dataclass
class IngestionRun:
    id: str
    project: str | None
    mode: str
    created_at: str
    artifacts: int
    candidates_created: int
    pending_review: int


@dataclass
class IngestionCandidate:
    id: str
    run_id: str
    artifact_id: str
    review_state: str
    candidate_type: str
    entity_type: str
    title: str
    aliases: list[str]
    summary: str
    project: str | None
    status: str | None
    tags: list[str]
    relationships: list[dict[str, str]]
    body: str
    evidence: list[dict[str, str]]
    confidence: float
    dedupe: dict[str, Any]
    created_at: str
    review_reason: str | None = None
    promoted_note_id: str | None = None


@dataclass
class IngestionReview:
    candidate_id: str
    action: str
    reason: str | None
    target_note_id: str | None
    created_at: str


def _ingestion_runs_path(vault_path: Path) -> Path:
    return vault_path / ".linked_notes_ingestion_runs.json"


def _ingestion_candidates_path(vault_path: Path) -> Path:
    return vault_path / ".linked_notes_ingestion_candidates.json"


def _ingestion_reviews_path(vault_path: Path) -> Path:
    return vault_path / ".linked_notes_ingestion_reviews.json"


def _load_json(path: Path, default: Any) -> Any:
    return load_json_file(path, default)


def _save_json(path: Path, data: Any) -> None:
    save_json_file(path, data, sort_keys=True)


def _load_runs(vault_path: Path) -> list[dict[str, Any]]:
    return _load_json(_ingestion_runs_path(vault_path), [])


def _save_runs(vault_path: Path, runs: list[dict[str, Any]]) -> None:
    _save_json(_ingestion_runs_path(vault_path), runs)


def _load_candidates(vault_path: Path) -> list[dict[str, Any]]:
    return _load_json(_ingestion_candidates_path(vault_path), [])


def _save_candidates(vault_path: Path, candidates: list[dict[str, Any]]) -> None:
    _save_json(_ingestion_candidates_path(vault_path), candidates)


def _load_reviews(vault_path: Path) -> list[dict[str, Any]]:
    return _load_json(_ingestion_reviews_path(vault_path), [])


def _save_reviews(vault_path: Path, reviews: list[dict[str, Any]]) -> None:
    _save_json(_ingestion_reviews_path(vault_path), reviews)


def list_ingestion_runs(vault_path: Path, limit: int = 20) -> list[dict[str, Any]]:
    runs = _load_runs(vault_path)
    runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return runs[:limit]


def review_extracted_nodes(
    vault_path: Path,
    run_id: str | None = None,
    state: str = "pending",
    recommendation: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    candidates = _load_candidates(vault_path)
    result = []
    for candidate in candidates:
        if run_id and candidate.get("run_id") != run_id:
            continue
        if state != "all" and candidate.get("review_state", "pending") != state:
            continue
        if recommendation and _recommendation_label(candidate) != recommendation:
            continue
        result.append(candidate)
    result.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return result[:limit]


def ingest_sources(
    graph: KnowledgeGraph,
    sources: list[dict[str, Any]],
    project: str | None = None,
    mode: str = "stage",
) -> dict[str, Any]:
    """Create an ingestion run and stage extracted candidates."""

    if graph.vault_path is None:
        raise ValueError("Graph has no vault path configured")
    if mode != "stage":
        raise ValueError("Only 'stage' mode is supported in v1")
    if not sources:
        raise ValueError("At least one source is required")

    vault_path = Path(graph.vault_path)
    run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    created_at = datetime.now().isoformat()

    artifacts: list[dict[str, Any]] = []
    candidates = _load_candidates(vault_path)
    created_candidates = 0

    expanded_sources = _expand_sources(sources)
    for source in expanded_sources:
        artifact, extracted = _extract_source(graph, run_id, source, project, created_at)
        artifacts.append(asdict(artifact))
        candidates.extend(asdict(candidate) for candidate in extracted)
        created_candidates += len(extracted)

    _save_candidates(vault_path, candidates)

    runs = _load_runs(vault_path)
    run = IngestionRun(
        id=run_id,
        project=project,
        mode=mode,
        created_at=created_at,
        artifacts=len(artifacts),
        candidates_created=created_candidates,
        pending_review=created_candidates,
    )
    runs.append(asdict(run))
    _save_runs(vault_path, runs)

    return {
        "run_id": run_id,
        "project": project,
        "artifacts": len(artifacts),
        "candidates_created": created_candidates,
        "pending_review": created_candidates,
    }


def accept_extracted_node(graph: KnowledgeGraph, candidate_id: str) -> dict[str, Any]:
    """Promote a staged candidate into the graph."""

    candidate, candidates = _find_candidate(graph, candidate_id)
    if candidate.get("review_state") != "pending":
        raise ValueError(f"Candidate is not pending: {candidate_id}")

    dedupe = candidate.get("dedupe", {})
    target_identifier = dedupe.get("matched_note_id")
    if dedupe.get("strategy") in {"merge_into_existing", "duplicate"} and target_identifier:
        note = merge_extracted_node(graph, candidate_id, target_identifier)["note"]
        return {"action": "merged", "note": note, "candidate_id": candidate_id}

    note = graph.upsert_memory_node(
        title=candidate["title"],
        summary=candidate["summary"],
        entity_type=candidate["entity_type"],
        project=candidate.get("project"),
        status=candidate.get("status"),
        aliases=candidate.get("aliases") or [],
        tags=candidate.get("tags") or [],
        relationships=candidate.get("relationships") or [],
        body=_candidate_body(candidate),
        filename=normalize_id(candidate["title"]),
    )

    candidate["review_state"] = "accepted"
    candidate["promoted_note_id"] = note.id
    _replace_candidate(graph, candidates, candidate)
    _append_review(
        Path(graph.vault_path),
        IngestionReview(
            candidate_id=candidate_id,
            action="accepted",
            reason=None,
            target_note_id=note.id,
            created_at=datetime.now().isoformat(),
        ),
    )
    _update_run_pending_count(Path(graph.vault_path), candidate["run_id"])
    return {"action": "accepted", "note": note, "candidate_id": candidate_id}


def reject_extracted_node(
    graph: KnowledgeGraph,
    candidate_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Reject a staged candidate."""

    candidate, candidates = _find_candidate(graph, candidate_id)
    if candidate.get("review_state") != "pending":
        raise ValueError(f"Candidate is not pending: {candidate_id}")

    candidate["review_state"] = "rejected"
    candidate["review_reason"] = reason
    _replace_candidate(graph, candidates, candidate)
    _append_review(
        Path(graph.vault_path),
        IngestionReview(
            candidate_id=candidate_id,
            action="rejected",
            reason=reason,
            target_note_id=None,
            created_at=datetime.now().isoformat(),
        ),
    )
    _update_run_pending_count(Path(graph.vault_path), candidate["run_id"])
    return {"status": "rejected", "candidate_id": candidate_id, "reason": reason}


def accept_all_candidates(
    graph: KnowledgeGraph,
    run_id: str,
    recommendation: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Bulk-accept pending candidates for a run."""

    candidates = review_extracted_nodes(
        Path(graph.vault_path),
        run_id=run_id,
        state="pending",
        recommendation=recommendation,
        limit=limit or 10_000,
    )
    results = []
    for candidate in candidates:
        outcome = accept_extracted_node(graph, candidate["id"])
        results.append(
            {
                "candidate_id": candidate["id"],
                "action": outcome["action"],
                "note_id": outcome["note"].id,
                "title": outcome["note"].title,
            }
        )
    return {"run_id": run_id, "accepted": len(results), "results": results}


def reject_all_candidates(
    graph: KnowledgeGraph,
    run_id: str,
    recommendation: str | None = None,
    reason: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Bulk-reject pending candidates for a run."""

    candidates = review_extracted_nodes(
        Path(graph.vault_path),
        run_id=run_id,
        state="pending",
        recommendation=recommendation,
        limit=limit or 10_000,
    )
    results = []
    for candidate in candidates:
        outcome = reject_extracted_node(graph, candidate["id"], reason)
        results.append(
            {
                "candidate_id": candidate["id"],
                "review_state": outcome["status"],
            }
        )
    return {"run_id": run_id, "rejected": len(results), "results": results}


def merge_extracted_node(
    graph: KnowledgeGraph,
    candidate_id: str,
    target_identifier: str,
) -> dict[str, Any]:
    """Merge a staged candidate into an existing memory node."""

    candidate, candidates = _find_candidate(graph, candidate_id)
    if candidate.get("review_state") != "pending":
        raise ValueError(f"Candidate is not pending: {candidate_id}")

    target = graph.get_note(target_identifier)
    if target is None:
        raise ValueError(f"Target note not found: {target_identifier}")

    relationships = _merge_relationships(target, candidate.get("relationships") or [])
    aliases = list(dict.fromkeys(target.aliases + candidate.get("aliases", [])))
    tags = list(dict.fromkeys(target.tags + candidate.get("tags", [])))
    summary = target.frontmatter.get("summary") or candidate["summary"]
    entity_type = target.frontmatter.get("entity_type") or candidate["entity_type"]
    project = target.frontmatter.get("project") or candidate.get("project")
    status = target.frontmatter.get("status") or candidate.get("status")

    updated = graph.upsert_memory_node(
        title=target.title,
        summary=summary,
        entity_type=entity_type,
        project=project,
        status=status,
        aliases=aliases,
        tags=tags,
        relationships=relationships,
        body=_merged_body(target, candidate),
        filename=target.id,
    )

    candidate["review_state"] = "merged"
    candidate["promoted_note_id"] = updated.id
    candidate["review_reason"] = f"merged into {updated.id}"
    _replace_candidate(graph, candidates, candidate)
    _append_review(
        Path(graph.vault_path),
        IngestionReview(
            candidate_id=candidate_id,
            action="merged",
            reason=None,
            target_note_id=updated.id,
            created_at=datetime.now().isoformat(),
        ),
    )
    _update_run_pending_count(Path(graph.vault_path), candidate["run_id"])
    return {"action": "merged", "note": updated, "candidate_id": candidate_id}


def _find_candidate(
    graph: KnowledgeGraph,
    candidate_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if graph.vault_path is None:
        raise ValueError("Graph has no vault path configured")
    candidates = _load_candidates(Path(graph.vault_path))
    for candidate in candidates:
        if candidate.get("id") == candidate_id:
            return candidate, candidates
    raise ValueError(f"Candidate not found: {candidate_id}")


def _replace_candidate(
    graph: KnowledgeGraph,
    candidates: list[dict[str, Any]],
    updated_candidate: dict[str, Any],
) -> None:
    if graph.vault_path is None:
        raise ValueError("Graph has no vault path configured")
    for index, candidate in enumerate(candidates):
        if candidate.get("id") == updated_candidate["id"]:
            candidates[index] = updated_candidate
            break
    _save_candidates(Path(graph.vault_path), candidates)


def _append_review(vault_path: Path, review: IngestionReview) -> None:
    reviews = _load_reviews(vault_path)
    reviews.append(asdict(review))
    _save_reviews(vault_path, reviews)


def _update_run_pending_count(vault_path: Path, run_id: str) -> None:
    runs = _load_runs(vault_path)
    candidates = _load_candidates(vault_path)
    pending = sum(
        1
        for candidate in candidates
        if candidate.get("run_id") == run_id and candidate.get("review_state") == "pending"
    )
    for run in runs:
        if run.get("id") == run_id:
            run["pending_review"] = pending
            break
    _save_runs(vault_path, runs)


def _extract_source(
    graph: KnowledgeGraph,
    run_id: str,
    source: dict[str, Any],
    project: str | None,
    created_at: str,
) -> tuple[IngestionArtifact, list[IngestionCandidate]]:
    source_type = source.get("type")
    if source_type == "file":
        path = Path(source["path"])
        if not path.exists():
            raise ValueError(f"Source file not found: {path}")
        content = path.read_text(encoding="utf-8")
        source_ref = str(path)
        display_name = path.stem
    elif source_type == "text":
        content = source["content"]
        source_ref = source.get("name", "inline-text")
        display_name = source.get("name", "inline-text")
    else:
        raise ValueError(f"Unsupported source type: {source_type}")

    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    artifact = IngestionArtifact(
        id=f"artifact-{uuid.uuid4().hex[:8]}",
        run_id=run_id,
        source_type=source_type,
        source_ref=source_ref,
        checksum=checksum,
        project=project,
        created_at=created_at,
    )
    candidate = _candidate_from_content(
        graph=graph,
        artifact=artifact,
        content=content,
        display_name=display_name,
        project=project,
        created_at=created_at,
    )
    return artifact, [candidate]


def _candidate_from_content(
    graph: KnowledgeGraph,
    artifact: IngestionArtifact,
    content: str,
    display_name: str,
    project: str | None,
    created_at: str,
) -> IngestionCandidate:
    frontmatter, body = parse_frontmatter(content)
    title = extract_title(content, frontmatter, display_name)
    summary = infer_summary(body or content, explicit_summary=frontmatter.get("summary"))
    entity_type = infer_entity_type(
        body or content,
        explicit_entity_type=frontmatter.get("entity_type"),
    )
    status = frontmatter.get("status")
    aliases = extract_aliases(frontmatter)
    tags = extract_tags(frontmatter)
    if project and not frontmatter.get("project"):
        inferred_project = project
    else:
        inferred_project = frontmatter.get("project")
    relationships = [
        {"type": rel.relation_type, "target": rel.raw_target}
        for rel in extract_relationships(frontmatter)
    ]
    confidence = 0.85 if frontmatter else 0.65
    evidence_text = normalize_space((body or content).strip())
    evidence = [
        {
            "artifact_id": artifact.id,
            "snippet": evidence_text[:200] + ("..." if len(evidence_text) > 200 else ""),
            "loc": artifact.source_ref,
        }
    ]
    dedupe = _dedupe_candidate(
        graph=graph,
        title=title,
        aliases=aliases,
        project=inferred_project,
        summary=summary,
        tags=tags,
    )
    return IngestionCandidate(
        id=f"candidate-{uuid.uuid4().hex[:8]}",
        run_id=artifact.run_id,
        artifact_id=artifact.id,
        review_state="pending",
        candidate_type="node",
        entity_type=entity_type,
        title=title,
        aliases=aliases,
        summary=summary,
        project=inferred_project,
        status=str(status) if status is not None else None,
        tags=tags,
        relationships=relationships,
        body=(body or content).strip(),
        evidence=evidence,
        confidence=confidence,
        dedupe=dedupe,
        created_at=created_at,
    )


def _expand_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand directory and glob sources into file sources."""

    expanded: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sources:
        source_type = source.get("type")
        if source_type in {"file", "text"}:
            key = str(sorted(source.items()))
            if key not in seen:
                seen.add(key)
                expanded.append(source)
            continue

        if source_type == "directory":
            directory = Path(source["path"])
            if not directory.exists() or not directory.is_dir():
                raise ValueError(f"Source directory not found: {directory}")
            recursive = bool(source.get("recursive", True))
            include_extensions = {
                ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                for ext in source.get("extensions", [".md", ".markdown", ".txt"])
            }
            include_patterns = source.get("include", [])
            exclude_patterns = source.get("exclude", [])
            iterator = directory.rglob("*") if recursive else directory.glob("*")
            for path in sorted(iterator):
                if not path.is_file():
                    continue
                if include_extensions and path.suffix.lower() not in include_extensions:
                    continue
                relative = str(path.relative_to(directory))
                if include_patterns and not any(
                    path.match(pattern) or relative_match(relative, pattern)
                    for pattern in include_patterns
                ):
                    continue
                if exclude_patterns and any(
                    path.match(pattern) or relative_match(relative, pattern)
                    for pattern in exclude_patterns
                ):
                    continue
                file_source = {"type": "file", "path": str(path)}
                key = str(sorted(file_source.items()))
                if key not in seen:
                    seen.add(key)
                    expanded.append(file_source)
            continue

        if source_type == "glob":
            pattern = source["pattern"]
            for path in sorted(Path().glob(pattern)):
                if not path.is_file():
                    continue
                file_source = {"type": "file", "path": str(path.resolve())}
                key = str(sorted(file_source.items()))
                if key not in seen:
                    seen.add(key)
                    expanded.append(file_source)
            continue

        raise ValueError(f"Unsupported source type: {source_type}")

    return expanded


def relative_match(relative_path: str, pattern: str) -> bool:
    """Match a relative path against a glob-like pattern."""

    return Path(relative_path).match(pattern)


def _dedupe_candidate(
    graph: KnowledgeGraph,
    title: str,
    aliases: list[str],
    project: str | None,
    summary: str,
    tags: list[str],
) -> dict[str, Any]:
    best_score = 0
    best_note: Note | None = None
    best_reasons: list[str] = []
    candidate_norm = normalize_id(title)
    candidate_aliases = {alias.lower() for alias in aliases}
    summary_lower = summary.lower()

    for note in graph.list_all_notes():
        score = 0
        reasons: list[str] = []
        if normalize_id(note.title) == candidate_norm:
            score += 8
            reasons.append("title match")
        if candidate_aliases.intersection({alias.lower() for alias in note.aliases}):
            score += 7
            reasons.append("alias match")
        if project and note.frontmatter.get("project") == project:
            score += 3
            reasons.append(f"same project: {project}")
        if (
            note.title.lower() in summary_lower
            or title.lower() in str(note.frontmatter.get("summary", "")).lower()
        ):
            score += 2
            reasons.append("title mentioned in summary")
        shared_tags = sorted(set(tags).intersection(note.tags))
        if shared_tags:
            score += len(shared_tags)
            reasons.append(f"shared tags: {', '.join(shared_tags)}")
        if score > best_score:
            best_score = score
            best_note = note
            best_reasons = reasons

    if best_note is None or best_score < 4:
        return {"strategy": "new", "matched_note_id": None, "score": best_score, "reasons": []}

    strategy = "merge_into_existing"
    if best_score >= 8 and normalize_id(best_note.title) == candidate_norm:
        strategy = "duplicate"
    return {
        "strategy": strategy,
        "matched_note_id": best_note.id,
        "score": best_score,
        "reasons": best_reasons,
    }


def _recommendation_label(candidate: dict[str, Any]) -> str:
    """Return the compact recommendation label used in review filters."""

    return candidate_recommendation_label(candidate)


def _merge_relationships(
    note: Note,
    candidate_relationships: list[dict[str, str]],
) -> list[dict[str, str]]:
    relationships = [
        {"type": relationship.relation_type, "target": relationship.raw_target}
        for relationship in note.explicit_relationships
    ]
    relationships.extend(candidate_relationships)
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for relationship in relationships:
        key = (relationship["type"], relationship["target"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(relationship)
    return unique


def _merged_body(target: Note, candidate: dict[str, Any]) -> str:
    body = target.body.rstrip()
    incoming = _candidate_body(candidate)
    if incoming and incoming not in body:
        if body:
            body += "\n\n"
        body += "## Ingested Context\n" + incoming
    return body


def _candidate_body(candidate: dict[str, Any]) -> str:
    body = (candidate.get("body") or "").strip()
    evidence_lines = []
    for item in candidate.get("evidence", []):
        snippet = item.get("snippet", "").strip()
        loc = item.get("loc", "").strip()
        if snippet:
            evidence_lines.append(f"- {snippet} ({loc})" if loc else f"- {snippet}")
    if evidence_lines:
        evidence_block = "## Evidence\n" + "\n".join(evidence_lines)
        if body:
            return body + "\n\n" + evidence_block
        return evidence_block
    return body
