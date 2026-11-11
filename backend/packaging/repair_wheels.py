"""Auditable downstream wheel repair; never modify installed package metadata.

Only WHEEL and RECORD may change. Pinned official archives, full original RECORD
verification and post-write payload verification are mandatory, not optional.
"""

import argparse
import base64
import csv
import hashlib
import http.client
import io
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

BUILD = "1cricksy"
RENAME = {
    "old": "mediapipe/tasks/c/libmediapipe_c_lib.cpython-39-x86_64-linux-gnu.so",
    "new": "mediapipe/tasks/c/libmediapipe.so",
    "sha256": "715145a5556c567f4603c7f329e2c7382aba0123ac76b90108f64f8843e20639",
    "size": 28638200,
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def record_hash(data):
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_name(name):
    path = PurePosixPath(name)
    require(
        bool(name)
        and not path.is_absolute()
        and "\\" not in name
        and ":" not in name
        and "\x00" not in name
        and all(part not in ("", ".", "..") for part in name.rstrip("/").split("/")),
        "Unsafe archive member: " + name,
    )


def read_archive(data):
    members = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            safe_name(info.filename)
            require(info.filename not in members, "Duplicate archive member")
            require(not info.flag_bits & 1, "Encrypted archive member")
            mode = info.external_attr >> 16
            require(not stat.S_ISLNK(mode), "Symlink archive member")
            require(info.file_size <= 400_000_000, "Oversized archive member")
            members[info.filename] = archive.read(info)
    require(sum(map(len, members.values())) <= 600_000_000, "Oversized archive")
    return members


def verify_record(members, record, rename=None):
    seen = set()
    renamed = False
    rows = csv.reader(io.StringIO(members[record].decode("utf-8"), newline=""))
    for row in rows:
        require(len(row) == 3, "Malformed RECORD row")
        name, digest, size = row
        safe_name(name)
        if rename and name == rename["old"]:
            require(name not in members and rename["new"] in members, "Unexpected rename state")
            name = rename["new"]
            payload = members[name]
            require(sha256(payload) == rename["sha256"], "Rename payload hash mismatch")
            require(len(payload) == rename["size"], "Rename payload size mismatch")
            renamed = True
        require(name not in seen, "Duplicate RECORD entry")
        seen.add(name)
        require(name in members, "Missing RECORD member: " + name)
        if name == record:
            require(digest == size == "", "RECORD must not hash itself")
        else:
            require(digest == record_hash(members[name]), "RECORD hash mismatch: " + name)
            require(size == str(len(members[name])), "RECORD size mismatch: " + name)
    files = {name for name in members if not name.endswith("/")}
    require(seen == files, "Incomplete RECORD")
    require(rename is None or renamed, "Expected exact MediaPipe RECORD defect absent")


def repair(data, spec):
    require(len(data) == spec["size"], "Original archive size mismatch")
    require(sha256(data) == spec["sha256"], "Original archive SHA256 mismatch")
    members = read_archive(data)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        original_info = {info.filename: info for info in archive.infolist()}
    dist = spec["distribution"] + "-" + spec["version"] + ".dist-info/"
    wheel, record = dist + "WHEEL", dist + "RECORD"
    require(
        wheel in members and record in members and dist + "METADATA" in members,
        "Missing mandatory metadata",
    )
    require(
        not any(name.endswith(("/RECORD.jws", "/RECORD.p7s")) for name in members),
        "Signed wheel requires independent handling",
    )
    require(
        {name.split("/", 1)[0] for name in members if ".dist-info/" in name} == {dist.rstrip("/")},
        "Unexpected dist-info directory",
    )
    require(
        members[wheel] == spec["original_wheel"].encode("utf-8"), "Unexpected WHEEL content or tags"
    )
    require("Root-Is-Purelib: false\n" in spec["original_wheel"], "Expected native wheel")
    rename = RENAME if spec["distribution"] == "mediapipe" else None
    verify_record(members, record, rename)
    original = members.copy()
    lines = [
        line
        for line in spec["original_wheel"].splitlines()
        if line and not line.startswith(("Tag:", "Build:"))
    ]
    lines += ["Build: " + BUILD] + ["Tag: " + tag for tag in spec["tags"]]
    members[wheel] = ("\n".join(lines) + "\n\n").encode("utf-8")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    for name in sorted(members):
        if not name.endswith("/"):
            writer.writerow(
                [
                    name,
                    "" if name == record else record_hash(members[name]),
                    "" if name == record else len(members[name]),
                ]
            )
    members[record] = buffer.getvalue().encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = original_info[name].create_system
            info.external_attr = original_info[name].external_attr
            info.internal_attr = original_info[name].internal_attr
            archive.writestr(
                info, members[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )
    derived = output.getvalue()
    checked = read_archive(derived)
    with zipfile.ZipFile(io.BytesIO(derived)) as archive:
        for info in archive.infolist():
            previous = original_info[info.filename]
            require(
                (info.create_system, info.external_attr, info.internal_attr)
                == (previous.create_system, previous.external_attr, previous.internal_attr),
                "Archive permission attributes changed: " + info.filename,
            )
    require(checked.keys() == original.keys(), "Derived member set changed")
    for name in original:
        if name not in (wheel, record):
            require(checked[name] == original[name], "Runtime payload changed: " + name)
    verify_record(checked, record)
    filename = (
        f'{spec["distribution"]}-{spec["version"]}-{BUILD}-' f'py3-none-{spec["platform"]}.whl'
    )
    require(
        spec["tags"] == ["py3-none-" + p for p in spec["platform"].split(".")],
        "Filename and internal tags disagree",
    )
    provenance = {
        "original_filename": spec["filename"],
        "original_sha256": sha256(data),
        "original_size": len(data),
        "official_url": spec["url"],
        "derived_filename": filename,
        "derived_sha256": sha256(derived),
        "derived_size": len(derived),
        "build": BUILD,
        "original_wheel_metadata": spec["original_wheel"],
        "derived_tags": spec["tags"],
        "changed_members": [wheel, record],
        "preserved_members": len(members) - 2,
        "original_record_exception": rename,
        "payloads_metadata_dependencies_licenses_byte_identical": True,
    }
    return filename, derived, provenance


def download(spec):
    require(
        spec["url"].startswith("https://files.pythonhosted.org/packages/"),
        "Only pinned official PyPI file URLs are allowed",
    )
    connection = http.client.HTTPSConnection("files.pythonhosted.org", timeout=600)
    try:
        connection.request("GET", spec["url"].removeprefix("https://files.pythonhosted.org"))
        response = connection.getresponse()
        require(response.status == 200, "Official download failed or redirected")
        data = response.read(spec["size"] + 1)
    finally:
        connection.close()
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--originals", type=Path)
    args = parser.parse_args()
    specs = json.loads(Path(__file__).with_name("wheel-pins.json").read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    provenance = []
    for spec in specs:
        data = (
            (args.originals / spec["filename"]).read_bytes() if args.originals else download(spec)
        )
        name, derived, evidence = repair(data, spec)
        target = args.output / name
        require(not target.exists(), "Refusing to overwrite derived wheel")
        with target.open("xb") as handle:
            handle.write(derived)
        provenance.append(evidence)
    evidence_path = args.output / "wheel-provenance.json"
    with evidence_path.open("x", encoding="utf-8") as handle:
        json.dump(provenance, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
