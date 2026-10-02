import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime import Runtime


def test_select_returns_latest_match_first():
    rt = Runtime()
    rt.append_history({"id": "e1", "type": "principle", "text": "P1"})
    rt.append_history({"id": "e2", "type": "deepening", "text": "R1"})
    rt.append_history({"id": "e3", "type": "principle", "text": "P2"})

    result = rt.k.select(rt.history, lambda e: e.get("type") == "principle")
    assert result == "e3", f"expected e3, got {result}"
    print("✓ test_select_returns_latest_match_first")


def test_select_finds_unique_match():
    rt = Runtime()
    rt.append_history({"id": "e1", "type": "principle"})
    rt.append_history({"id": "e2", "type": "deepening"})
    rt.append_history({"id": "e3", "type": "principle"})

    result = rt.k.select(rt.history, lambda e: e.get("type") == "deepening")
    assert result == "e2", f"expected e2, got {result}"
    print("✓ test_select_finds_unique_match")


def test_select_returns_none_when_not_found():
    rt = Runtime()
    rt.append_history({"id": "e1", "type": "principle"})
    rt.append_history({"id": "e2", "type": "deepening"})

    result = rt.k.select(rt.history, lambda e: e.get("type") == "unknown")
    assert result is None, f"expected None, got {result}"
    print("✓ test_select_returns_none_when_not_found")


def test_select_does_not_modify_history():
    rt = Runtime()
    rt.append_history({"id": "e1", "type": "principle"})

    before = list(rt.history)
    rt.k.select(rt.history, lambda e: e.get("type") == "nonexistent")
    after = list(rt.history)

    assert before == after, f"history modified: {before} → {after}"
    assert len(before) == len(after), f"size changed: {len(before)} → {len(after)}"
    print("✓ test_select_does_not_modify_history")


def run_all():
    tests = [
        test_select_returns_latest_match_first,
        test_select_finds_unique_match,
        test_select_returns_none_when_not_found,
        test_select_does_not_modify_history,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"✗ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed")
    print()
    if failed == 0:
        print("All tests passed.")
        print("Manual action required: set H001.status = 'confirmed' in genome.json.")
    else:
        print("Tests failed. H001 may be refuted.")
        print("Manual action required: investigate and update genome.json.")

    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)