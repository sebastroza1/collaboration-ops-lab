"""Offline-only identity and messaging reconciliation. Read-only and deterministic."""
from collections import Counter
from typing import Any


def _canonical(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip().casefold()


def _records(snapshot: dict[str, Any], key: str, name: str) -> list[dict[str, Any]]:
    items = snapshot.get(key, [])
    if not isinstance(items, list):
        raise ValueError(f"{name} must be a list")
    if not all(isinstance(item, dict) for item in items):
        raise ValueError(f"Every {name} entry must be an object")
    return items


def _index(items: list[dict[str, Any]], key: str, name: str) -> dict[str, dict[str, Any]]:
    values = [_canonical(item.get(key), f"{name} {key}") for item in items]
    duplicates = sorted(item for item, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate {name} {key}: {', '.join(duplicates)}")
    return dict(zip(values, items, strict=True))


def _members(group: dict[str, Any], label: str) -> set[str]:
    raw_members = group.get("members", [])
    if not isinstance(raw_members, list):
        raise ValueError(f"{label} members must be a list")
    members = [_canonical(member, f"{label} member") for member in raw_members]
    duplicates = sorted(item for item, count in Counter(members).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate {label} members: {', '.join(duplicates)}")
    return set(members)


def _validate_snapshots(directory: Any, messaging: Any) -> None:
    if not isinstance(directory, dict) or not isinstance(messaging, dict):
        raise ValueError("Directory and messaging snapshots must be JSON objects")

    users = _records(directory, "users", "directory users")
    groups = _records(directory, "groups", "directory groups")
    mailboxes = _records(messaging, "mailboxes", "mailboxes")
    messaging_groups = _records(messaging, "groups", "messaging groups")

    for user in users:
        _canonical(user.get("id"), "directory user id")
        _canonical(user.get("upn"), "directory user upn")
        if "enabled" in user and not isinstance(user["enabled"], bool):
            raise ValueError("directory user enabled must be a boolean")
    for mailbox in mailboxes:
        _canonical(mailbox.get("directory_id"), "mailbox directory_id")
        _canonical(mailbox.get("address"), "mailbox address")
    for group in groups:
        _canonical(group.get("id"), "directory group id")
        _members(group, "directory group")
    for group in messaging_groups:
        _canonical(group.get("directory_id"), "messaging group directory_id")
        _members(group, "messaging group")


def reconcile(directory: dict[str, Any], messaging: dict[str, Any]) -> dict[str, Any]:
    """Compare two synthetic snapshots; return *proposals* without mutations."""
    _validate_snapshots(directory, messaging)
    directory_users = _index(_records(directory, "users", "directory users"), "id", "directory user")
    directory_groups = _index(_records(directory, "groups", "directory groups"), "id", "directory group")
    mailboxes = _index(_records(messaging, "mailboxes", "mailboxes"), "directory_id", "mailbox")
    message_groups = _index(_records(messaging, "groups", "messaging groups"), "directory_id", "messaging group")
    findings: list[dict[str, str]] = []

    def add(kind: str, entity: str, action: str, explanation: str) -> None:
        findings.append({"type": kind, "entity": entity, "action": action, "reason": explanation})

    for uid, user in directory_users.items():
        mailbox = mailboxes.get(uid)
        if mailbox is None and user.get("enabled", True):
            add("missing_mailbox", uid, "review_provisioning", "Enabled directory user has no messaging mailbox")
        elif mailbox and _canonical(mailbox["address"], "mailbox address") != _canonical(user["upn"], "directory user upn"):
            add("address_mismatch", uid, "review_identity_mapping", "UPN and mailbox address differ")

    for uid in mailboxes:
        if uid not in directory_users:
            add("orphan_mailbox", uid, "manual_review", "Mailbox directory ID not found; do not delete automatically")

    for gid, group in directory_groups.items():
        target = message_groups.get(gid)
        if target is None:
            add("missing_group", gid, "review_provisioning", "Directory group missing from messaging platform")
            continue
        expected = _members(group, "directory group")
        actual = _members(target, "messaging group")
        for uid in sorted(expected - actual):
            add("missing_membership", f"{gid}/{uid}", "review_membership_add", "Group member absent from messaging snapshot")
        for uid in sorted(actual - expected):
            add("unexpected_membership", f"{gid}/{uid}", "manual_review", "Member unexpected; never remove automatically")

    for gid in message_groups:
        if gid not in directory_groups:
            add("orphan_group", gid, "manual_review", "Messaging group not found in directory")

    findings.sort(key=lambda item: (item["type"], item["entity"], item["action"]))
    counts = Counter(row["type"] for row in findings)
    return {
        "schema_version": 1,
        "source": "synthetic_offline_fixtures",
        "dry_run": True,
        "safe_to_apply": False,
        "write_operations": 0,
        "summary": {
            "directory_users": len(directory_users),
            "mailboxes": len(mailboxes),
            "directory_groups": len(directory_groups),
            "messaging_groups": len(message_groups),
            "findings": len(findings),
            "by_type": dict(sorted(counts.items())),
        },
        "findings": findings,
    }
