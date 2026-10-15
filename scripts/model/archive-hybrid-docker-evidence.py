#!/usr/bin/env python3
"""Archive all 17 pinned, stopped Hybrid research Docker logs. Never delete Docker."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "scripts/model/hybrid-docker-inventory.py"
EXPECTED_IDS = {
    "10f8645adee052bd7506f1237e4064bcbbfb189caaeacbb9759981eaa33b32a5",
    "2ea2a61cb2e07df79044280ac1c65ffa5bda8fb3084501ea87853b7d6fbf20e1",
    "3b7e6badbd653f38f18e884c287b96c3c37cf005822cbc9ccb03f741d7421254",
    "43afd5055614c273181bd8f91d251ab19ac88d49080f3362cf7bcc31143c5c65",
    "569f2720593f4d0f768342c1417a9d2363fba894fd7f83a8de8a5df0dd2a9d51",
    "586fb729f12cfb8971ba5ed21ef4fdff4845505d132511cfcacb269c77e045a0",
    "6484fdf56ffbec15d76333bda1a36f05ca50b9f17841b37e41e0781343a8b2e0",
    "7a871dfd8c7dbc63f7e3943a7261003e9564442a28c486b6cd6b3b8bf672cc45",
    "ba4029544a1ef39ffc2ab316da9ceb4cb975e845344c6be9bf683fc50db2ca5a",
    "bd6886aa4499f14e12e8ce3e49c2400ec2a0d940bf4e0d03a0d8fe3d1d5ba14c",
    "c14af278cc738258a8fda1d686595864f845ff11cf4b223e8c1f48d92be06ca1",
    "df2787a3fab4ef0d6d953e62ba4f7af380eebc46bf220734804b993cec5ac21b",
    "e029767f2882aa50636bcabf55a55d4adda0c3b25c4d41c2b58d8d0b0f915a1c",
    "e2b000b28d5e71922e20d59f9725c8ebe54c5794349a20515343302f8d608e2a",
    "e526189f1093e95d81568d82eb10b8beaeb6227adca49029f241634769e6cbc7",
    "e937e0f23e45ba4ee8851e79e60eaefc509367b74a021e67a74fea098ad17f62",
    "efa06c76207540a3ffa034e1e8d21156565a458be91486b5bac1208bbe9a1aec",
}
LIMIT = 16 * 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def docker(*args):
    return subprocess.run(["docker", *args], capture_output=True, text=True,
                          check=True, timeout=90).stdout


def capture(cid, destination):
    with destination.open("xb") as fp:
        os.fchmod(fp.fileno(), 0o600)
        with subprocess.Popen(["docker", "logs", "--timestamps", cid],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
            n = 0
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                n += len(chunk)
                if n > LIMIT:
                    proc.kill()
                    proc.wait()
                    raise RuntimeError("log exceeded 16MiB: " + cid)
                fp.write(chunk)
            if proc.wait(timeout=30) != 0:
                raise RuntimeError("docker logs failed: " + cid)
        fp.flush()
        os.fsync(fp.fileno())


def main():
    if len(sys.argv) != 1:
        print("Usage: python3 scripts/model/archive-hybrid-docker-evidence.py", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("hybrid_docker_inventory", INVENTORY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ids = docker("ps", "-aq", "--no-trunc")
    entries = module.inventory(ids, docker("inspect", *ids.splitlines()))
    by_id = {e["id"]: e for e in entries}
    if set(by_id) != EXPECTED_IDS or any(e["status"] != "exited" or e["protected"] for e in entries):
        print("ARCHIVE=BLOCKED_INVENTORY_MISMATCH")
        return 3
    base = Path.home() / ".local/state/qwen38-spark/retirement-archives"
    if not base.is_dir() or base.is_symlink() or base.stat().st_mode & 0o077:
        print("ARCHIVE=BLOCKED_UNSAFE_PARENT")
        return 3
    with tempfile.TemporaryDirectory(prefix=".pending-hybrid-17-", dir=base) as temporary:
        folder = Path(temporary)
        folder.chmod(0o700)
        manifest = []
        for cid, entry in sorted(by_id.items()):
            log = folder / (cid + ".log")
            meta = folder / (cid + ".json")
            capture(cid, log)
            with meta.open("x", encoding="utf-8") as fp:
                os.fchmod(fp.fileno(), 0o600)
                json.dump(entry, fp, indent=2, sort_keys=True)
                fp.write("\n")
                fp.flush()
                os.fsync(fp.fileno())
            for file in (log, meta):
                manifest.append(f"{digest(file)}  {file.name}\n")
        sha = folder / "SHA256SUMS"
        with sha.open("x") as fp:
            os.fchmod(fp.fileno(), 0o600)
            fp.writelines(manifest)
        for line in manifest:
            checksum, name = line.strip().split("  ", 1)
            if digest(folder / name) != checksum:
                raise RuntimeError("archive checksum failure")
        # Re-check live inventory before publication. Never archive stale Docker identities.
        latest_ids = docker("ps", "-aq", "--no-trunc")
        latest = module.inventory(latest_ids, docker("inspect", *latest_ids.splitlines()))
        if latest_ids.splitlines() != ids.splitlines() or latest != entries:
            raise RuntimeError("Docker inventory changed during archive")
        final = base / "hybrid-docker-17-20261015"
        if final.exists() or final.is_symlink():
            raise RuntimeError("archive destination exists: " + str(final))
        folder.rename(final)
        print("HYBRID_ARCHIVE=" + str(final))
        print("HYBRID_ARCHIVE_SHA256=PASS_34_FILES")
        print("HYBRID_DOCKER_DELETE=NOT_PERFORMED")
        # Prevent TemporaryDirectory cleanup from touching renamed final directory.
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("HYBRID_ARCHIVE=BLOCKED " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        raise SystemExit(3)
