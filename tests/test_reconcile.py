import unittest
from collab.reconcile import reconcile


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.directory = {"users": [{"id": "A", "upn": "a@example.test", "enabled": True}],
                          "groups": [{"id": "G", "members": ["A"]}]}
        self.messaging = {"mailboxes": [{"directory_id": "a", "address": "A@example.test"}],
                          "groups": [{"directory_id": "g", "members": ["a"]}]}

    def test_identical_data_has_zero_findings(self):
        result = reconcile(self.directory, self.messaging)
        self.assertEqual(result["summary"]["findings"], 0)
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["safe_to_apply"])

    def test_missing_mailbox_is_proposal(self):
        self.messaging["mailboxes"] = []
        result = reconcile(self.directory, self.messaging)
        self.assertEqual(result["findings"][0]["type"], "missing_mailbox")
        self.assertEqual(result["findings"][0]["action"], "review_provisioning")

    def test_disabled_user_does_not_trigger_mailbox_provisioning(self):
        self.directory["users"][0]["enabled"] = False
        self.messaging["mailboxes"] = []
        self.assertEqual(reconcile(self.directory, self.messaging)["summary"]["findings"], 0)

    def test_mailbox_address_mismatch(self):
        self.messaging["mailboxes"][0]["address"] = "wrong@example.test"
        self.assertIn("address_mismatch", [f["type"] for f in reconcile(self.directory, self.messaging)["findings"]])

    def test_orphan_is_manual_review_never_delete(self):
        self.messaging["mailboxes"].append({"directory_id": "x", "address": "x@example.test"})
        findings = reconcile(self.directory, self.messaging)["findings"]
        self.assertIn({"type": "orphan_mailbox", "entity": "x", "action": "manual_review", "reason": "Mailbox directory ID not found; do not delete automatically"}, findings)

    def test_missing_and_unexpected_membership(self):
        self.messaging["groups"][0]["members"] = ["X"]
        types = {f["type"] for f in reconcile(self.directory, self.messaging)["findings"]}
        self.assertEqual(types, {"missing_membership", "unexpected_membership"})

    def test_missing_group(self):
        self.messaging["groups"] = []
        self.assertIn("missing_group", [f["type"] for f in reconcile(self.directory, self.messaging)["findings"]])

    def test_duplicate_directory_ids_rejected(self):
        self.directory["users"].append(self.directory["users"][0].copy())
        with self.assertRaisesRegex(ValueError, "Duplicate directory user"):
            reconcile(self.directory, self.messaging)

    def test_duplicate_mailboxes_rejected_case_insensitive(self):
        self.messaging["mailboxes"].append({"directory_id": "A", "address": "another@example.test"})
        with self.assertRaisesRegex(ValueError, "Duplicate mailbox"):
            reconcile(self.directory, self.messaging)

    def test_is_deterministic(self):
        self.assertEqual(reconcile(self.directory, self.messaging), reconcile(self.directory, self.messaging))

    def test_rejects_non_object_snapshots(self):
        with self.assertRaisesRegex(ValueError, "JSON objects"):
            reconcile([], self.messaging)

    def test_rejects_missing_or_blank_identity_fields(self):
        del self.directory["users"][0]["upn"]
        with self.assertRaisesRegex(ValueError, "upn"):
            reconcile(self.directory, self.messaging)

    def test_rejects_invalid_enabled_flag(self):
        self.directory["users"][0]["enabled"] = "yes"
        with self.assertRaisesRegex(ValueError, "boolean"):
            reconcile(self.directory, self.messaging)

    def test_rejects_duplicate_members_case_insensitive(self):
        self.directory["groups"][0]["members"] = ["A", "a"]
        with self.assertRaisesRegex(ValueError, "Duplicate directory group members"):
            reconcile(self.directory, self.messaging)

    def test_report_explicitly_has_no_write_operations(self):
        result = reconcile(self.directory, self.messaging)
        self.assertEqual(result["write_operations"], 0)
        self.assertEqual(result["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
