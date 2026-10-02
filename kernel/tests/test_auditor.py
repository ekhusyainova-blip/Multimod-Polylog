import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime import Runtime


def test_auditor_accepts_safe_request():
    """Безопасный запрос → accept."""
    rt = Runtime()
    result = rt.auditor.run({
        "id": "req1",
        "target": "runtime.py",
        "change": "fix bug",
    })
    assert result["verdict"] == "accept", f"expected accept, got {result['verdict']}"
    assert result["request_id"] == "req1"
    assert result["mode"] == "audit"
    print("✓ test_auditor_accepts_safe_request")


def test_auditor_rejects_token_change():
    """Запрос меняет токен → reject (K защита)."""
    rt = Runtime()
    result = rt.auditor.run({
        "id": "req2",
        "target": "genome.json",
        "change": "change token value",
    })
    assert result["verdict"] == "reject", f"expected reject, got {result['verdict']}"
    print("✓ test_auditor_rejects_token_change")


def test_auditor_rejects_overwrite():
    """Overwrite → reject (append-only)."""
    rt = Runtime()
    result = rt.auditor.run({
        "id": "req3",
        "target": "archive.jsonl",
        "action": "overwrite",
    })
    assert result["verdict"] == "reject", f"expected reject, got {result['verdict']}"
    print("✓ test_auditor_rejects_overwrite")


def test_auditor_rejects_delete():
    """Delete → reject (append-only)."""
    rt = Runtime()
    result = rt.auditor.run({
        "id": "req4",
        "target": "archive.jsonl",
        "action": "delete",
    })
    assert result["verdict"] == "reject", f"expected reject, got {result['verdict']}"
    print("✓ test_auditor_rejects_delete")


def test_auditor_has_four_challenges():
    """A10: итерация = полный цикл 4 вызовов."""
    rt = Runtime()
    result = rt.auditor.run({"id": "req5", "target": "safe.py"})
    assert len(result["challenges"]) == 4, f"expected 4 challenges, got {len(result['challenges'])}"
    print("✓ test_auditor_has_four_challenges")


def run_all():
    tests = [
        test_auditor_accepts_safe_request,
        test_auditor_rejects_token_change,
        test_auditor_rejects_overwrite,
        test_auditor_rejects_delete,
        test_auditor_has_four_challenges,
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
        print("Manual action required: set H006.status = 'confirmed' in genome.json.")
    else:
        print("Tests failed. Investigate and update genome.json.")

    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)