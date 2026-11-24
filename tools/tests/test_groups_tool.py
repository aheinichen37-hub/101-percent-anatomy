"""tools/groups.py: report runs on the real app; --apply only touches the /*GO*/ block."""
import json, os, shutil, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(REPO, "tools", "groups.py")


def run(*args):
    return subprocess.run([sys.executable, "-I", TOOL, *args], capture_output=True, text=True, cwd=REPO)


def test_report_runs_and_names_decks():
    r = run(os.path.join(REPO, "index.html"), "--all")
    assert r.returncode == 0, r.stderr
    assert "ch8-arm" in r.stdout and "decks have groups" in r.stdout


def test_apply_changes_only_the_override_block_and_flags_stale(tmp_path):
    page = tmp_path / "index.html"
    shutil.copy(os.path.join(REPO, "index.html"), page)
    for f in ("manifest.webmanifest", "sw.js"):
        shutil.copy(os.path.join(REPO, f), tmp_path / f)
    ov = tmp_path / "ov.json"
    ov.write_text(json.dumps({"ch8-arm|Interosseous membrane": "forearm", "ch8-arm|No such card": "x"}))
    before = page.read_text()
    r = run(str(page), "--apply", "--overrides", str(ov))
    assert r.returncode == 0, r.stderr
    after = page.read_text()
    assert '"ch8-arm|Interosseous membrane": "forearm"' in after
    assert after.replace(after[after.index("/*GO*/"):after.index("/*END GO*/")], "") == \
        before.replace(before[before.index("/*GO*/"):before.index("/*END GO*/")], "")
    assert "Stale overrides" in r.stdout and "No such card" in r.stdout
