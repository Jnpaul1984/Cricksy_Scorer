"""Standard-library tests; no downloaded wheel code is imported or executed."""

import copy
import csv
import io
import unittest
import zipfile

from backend.packaging import repair_wheels as rw


class WheelRepairTests(unittest.TestCase):
    def setUp(self):
        self.dist = "example-1.0.dist-info/"
        self.spec = {
            "distribution": "example",
            "version": "1.0",
            "filename": "original.whl",
            "url": "https://files.pythonhosted.org/packages/test/original.whl",
            "original_wheel": "Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: cp39-cp39-linux_x86_64\n\n",
            "tags": ["py3-none-linux_x86_64"],
            "platform": "linux_x86_64",
        }
        self.members = {
            "example/__init__.py": b"# Unchanged runtime payload\n",
            "example/lib.so": b"\x7fELF\x00test",
            self.dist + "WHEEL": self.spec["original_wheel"].encode(),
            self.dist + "METADATA": b"Name: example\nVersion: 1.0\nRequires-Dist: numpy<2\n",
            self.dist + "LICENSE": b"Original license\n",
        }

    def pack(self, members=None, record_override=None):
        members = dict(self.members if members is None else members)
        record = self.dist + "RECORD"
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\n")
        for name, data in sorted(members.items()):
            writer.writerow([name, rw.record_hash(data), len(data)])
        writer.writerow([record, "", ""])
        members[record] = buffer.getvalue().encode() if record_override is None else record_override
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        data = stream.getvalue()
        spec = dict(self.spec, size=len(data), sha256=rw.sha256(data))
        return data, spec

    def test_valid_repair_payload_and_dependency_metadata_unchanged(self):
        data, spec = self.pack()
        name, derived, provenance = rw.repair(data, spec)
        self.assertEqual(name, "example-1.0-1cricksy-py3-none-linux_x86_64.whl")
        result = rw.read_archive(derived)
        for member, payload in self.members.items():
            if not member.endswith("/WHEEL"):
                self.assertEqual(result[member], payload)
        self.assertIn(b"Build: 1cricksy\n", result[self.dist + "WHEEL"])
        self.assertIn(b"Root-Is-Purelib: false\n", result[self.dist + "WHEEL"])
        self.assertIn(b"Tag: py3-none-linux_x86_64\n", result[self.dist + "WHEEL"])
        self.assertEqual(provenance["original_sha256"], rw.sha256(data))
        self.assertEqual(provenance["derived_sha256"], rw.sha256(derived))
        rw.verify_record(result, self.dist + "RECORD")

    def test_permissions_preserved(self):
        data, spec = self.pack()
        _, derived, _ = rw.repair(data, spec)
        with zipfile.ZipFile(io.BytesIO(data)) as old, zipfile.ZipFile(io.BytesIO(derived)) as new:
            for before in old.infolist():
                after = new.getinfo(before.filename)
                self.assertEqual(before.external_attr, after.external_attr)
                self.assertEqual(before.internal_attr, after.internal_attr)
                self.assertEqual(before.create_system, after.create_system)

    def test_reproducible(self):
        data, spec = self.pack()
        self.assertEqual(rw.repair(data, spec), rw.repair(data, spec))

    def test_wrong_archive_hash(self):
        data, spec = self.pack()
        spec["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA256"):
            rw.repair(data, spec)

    def test_wrong_size(self):
        data, spec = self.pack()
        spec["size"] += 1
        with self.assertRaisesRegex(ValueError, "size"):
            rw.repair(data, spec)

    def test_invalid_record(self):
        data, spec = self.pack(record_override=b"missing,sha256=bad,123\n")
        with self.assertRaisesRegex(ValueError, "Missing RECORD"):
            rw.repair(data, spec)

    def test_incomplete_record(self):
        data, spec = self.pack(record_override=(self.dist + "RECORD,,\n").encode())
        with self.assertRaisesRegex(ValueError, "Incomplete RECORD"):
            rw.repair(data, spec)

    def test_unexpected_tag(self):
        members = copy.deepcopy(self.members)
        members[self.dist + "WHEEL"] += b"Tag: cp312-cp312-any\n"
        data, spec = self.pack(members)
        with self.assertRaisesRegex(ValueError, "Unexpected WHEEL"):
            rw.repair(data, spec)

    def test_unsafe_member(self):
        members = dict(self.members, **{"../outside": b"invalid"})
        data, spec = self.pack(members)
        with self.assertRaisesRegex(ValueError, "Unsafe archive"):
            rw.repair(data, spec)

    def test_added_member_fails_pinned_hash(self):
        original, spec = self.pack()
        stream = io.BytesIO(original)
        with zipfile.ZipFile(stream, "a") as archive:
            archive.writestr("unexpected.py", b"unexpected")
        with self.assertRaises(ValueError):
            rw.repair(stream.getvalue(), spec)

    def test_duplicate_member(self):
        data, spec = self.pack()
        stream = io.BytesIO(data)
        with zipfile.ZipFile(stream, "a") as archive, self.assertWarns(UserWarning):
            archive.writestr("example/lib.so", b"duplicate")
        data = stream.getvalue()
        spec.update(size=len(data), sha256=rw.sha256(data))
        with self.assertRaisesRegex(ValueError, "Duplicate archive"):
            rw.repair(data, spec)

    def test_multiple_manylinux_tags(self):
        data, spec = self.pack()
        spec["platform"] = "manylinux_2_17_x86_64.manylinux2014_x86_64"
        spec["tags"] = ["py3-none-manylinux_2_17_x86_64", "py3-none-manylinux2014_x86_64"]
        name, derived, _ = rw.repair(data, spec)
        self.assertTrue(name.endswith(spec["platform"] + ".whl"))
        for tag in spec["tags"]:
            self.assertIn(("Tag: " + tag).encode(), rw.read_archive(derived)[self.dist + "WHEEL"])

    def test_filename_tag_disagreement(self):
        data, spec = self.pack()
        spec["tags"] = ["py3-none-any"]
        with self.assertRaisesRegex(ValueError, "disagree"):
            rw.repair(data, spec)

    def test_rename_is_exact_and_requires_hash_size_and_missing_old(self):
        payload = b"test fixture, not the official MediaPipe binary"
        rename = dict(rw.RENAME, sha256=rw.sha256(payload), size=len(payload))
        record = "mediapipe-0.10.31.dist-info/RECORD"
        rows = f'{rename["old"]},{rw.record_hash(payload)},{len(payload)}\n{record},,\n'
        members = {rename["new"]: payload, record: rows.encode()}
        rw.verify_record(members, record, rename)
        # The actual hardcoded exception must reject this synthetic native payload.
        with self.assertRaisesRegex(ValueError, "Rename payload"):
            rw.verify_record(members, record, rw.RENAME)
        for bad in [dict(rename, sha256="0" * 64), dict(rename, size=len(payload) + 1)]:
            with self.assertRaises(ValueError):
                rw.verify_record(members, record, bad)
        with self.assertRaises(ValueError):
            rw.verify_record(dict(members, **{rename["old"]: payload}), record, rename)
        with self.assertRaises(ValueError):
            rw.verify_record(members, record)
        wrong = dict(members, **{record: rows.replace(rename["old"], "other/missing.so").encode()})
        with self.assertRaises(ValueError):
            rw.verify_record(wrong, record, rename)


if __name__ == "__main__":
    unittest.main()
