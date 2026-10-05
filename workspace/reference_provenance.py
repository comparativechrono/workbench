"""Offline reference receipts carried from local inputs into frozen runs.

Graph JSON never establishes reference provenance. Only a local library receipt
whose file identity agrees with the engine's freshly computed input hash does.
Completed methods consume that frozen evidence, not today's mutable library.
"""
from __future__ import annotations

import copy
from pathlib import Path


def collect_references(app_root, paths, evidence=None):
    """Read local metadata; with evidence, require the freshly hashed identity.

    Preview is deliberately a metadata lookup, not another multi-GB file hash.
    The engine performs the authoritative hash immediately before freezing.
    Ordinary local files need no library entry and continue to work unchanged.
    """
    paths = list(dict.fromkeys(str(Path(path).resolve()) for path in paths if path))
    if not paths or not (Path(app_root) / "user-data/references/library.json").is_file():
        return {}
    try:
        from .reference_manager import ReferenceManager
    except ImportError:
        from reference_manager import ReferenceManager
    manager = ReferenceManager(app_root)
    references = {}
    for path in paths:
        checksum = evidence[path]["sha256"] if evidence is not None else None
        record = manager.provenance_for_path(path, sha256=checksum)
        if record is not None:
            references[path] = copy.deepcopy(record)
    return references


def used_paths(graph, statuses=None):
    refs = {ref for node in graph.get("nodes", [])
            if statuses is None or statuses.get(node.get("id")) == "success"
            for values in node.get("inputs", {}).values() for ref in values}
    return {str(Path(path).resolve()) for source in graph.get("sources", [])
            if source.get("id") in refs
            for path in source.get("files", {}).values() if path}


def methods_text(references, paths, *, verified):
    lines = []
    for path in sorted(paths):
        record = references.get(path)
        if not record:
            continue
        species = record.get("species", {})
        name = species.get("name", species.get("id", "")) if isinstance(species, dict) else str(species)
        assembly = record.get("assembly") or (species.get("assembly", "") if isinstance(species, dict) else "")
        accession = record.get("assembly_accession") or (species.get("assembly_accession", "") if isinstance(species, dict) else "")
        item = record.get("file", {})
        provider = record.get("provider_name") or ("Ensembl archive" if record.get("provider") == "ensembl-archive" else record.get("provider", "Reference provider"))
        identity = f"{provider}, release {record.get('release', '')}; {name}; assembly {assembly}"
        if accession:
            identity += f" ({accession})"
        filename = item.get("filename") or Path(path).name
        line = f"Reference data: {item.get('label', item.get('kind', 'local reference'))}: {identity}; file {filename}."
        detail = item.get("detail")
        if isinstance(detail, str) and detail:
            line += " " + detail.rstrip(".") + "."
        retrieved = record.get("downloaded_at") or record.get("retrieved_at")
        if retrieved:
            line += " Retrieved " + str(retrieved).split("T", 1)[0] + "."
        source = item.get("source_url") or item.get("url")
        if source:
            line += " Source: " + source
        lines.append(line)
    if not lines:
        return ""
    if verified:
        lines.append("Reference input SHA-256 hashes were checked against local download receipts when this run was prepared. Exact identities and download evidence are retained in reference-provenance.json and plan.json.")
    else:
        lines.append("Reference identities above come from local download receipts. Input SHA-256 hashes will be checked against those receipts before execution.")
    return "\n\n".join(lines)
