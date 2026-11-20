import importlib.util
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("secret_scan", ROOT / "scripts" / "secret_scan.py")
assert _spec and _spec.loader
secret_scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(secret_scan)

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _fake_seed(prefix: str, n: int) -> str:
    # Built at runtime so no seed-shaped literal ever lands in the repo.
    return prefix + "".join(secrets.choice(B58) for _ in range(n))


def test_detects_seeds_and_key_headers(tmp_path: Path) -> None:
    f = tmp_path / "leak.py"
    header = "-----BEGIN " + "EC PRIVATE KEY-----"
    f.write_text(f"a = '{_fake_seed('s', 28)}'\nb = '{_fake_seed('sEd', 28)}'\n{header}\n")
    kinds = {name for _, _, name in secret_scan.scan([f])}
    assert kinds == {"xrpl-seed-secp256k1", "xrpl-seed-ed25519", "private-key-header"}


def test_clean_file_and_addresses_pass(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("addr = 'rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh'\nsome_ordinary_identifier = 1\n")
    assert secret_scan.scan([f]) == []


def test_repo_is_clean() -> None:
    import os

    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        assert secret_scan.scan(secret_scan.candidate_files()) == []
    finally:
        os.chdir(cwd)
