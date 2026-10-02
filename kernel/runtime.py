#!/usr/bin/env python3
"""
Multimod Polilog — runtime v0.5.
Токен: MONOMOD::MM5FFF681946L6G6A111
"""

import argparse
import json
import sys
import time
from collections import deque
from pathlib import Path

GENOME_PATH = Path(__file__).parent / "genome.json"

MODE_TO_LOG = {
    "solo":        "audit.jsonl",
    "hybrid-peer": "peer_dialog_localhost.jsonl",
    "hybrid-cell": "cell_dialog.jsonl",
    "remote":      "peer_dialog_remote.jsonl",
}


def load_decisions(path: Path = GENOME_PATH):
    if not path.exists():
        print(f"[FATAL] genome.json not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"[FATAL] genome.json invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    d = data.get("decisions", {})
    if not isinstance(d, dict):
        d = {}

    def safe(name):
        s = d.get(name, {})
        return s if isinstance(s, dict) else {}

    canon = safe("canon")
    accepted = safe("accepted")
    refuted = safe("refuted")

    h = data.get("hypotheses", {})
    if not isinstance(h, dict):
        h = {}

    return canon, accepted, refuted, h, data


def check_integrity(canon, accepted, refuted):
    problems = []
    seen = {}
    for name, section in (("canon", canon), ("accepted", accepted), ("refuted", refuted)):
        for key, val in section.items():
            if not isinstance(val, dict):
                problems.append(f"{name}.{key}: not a dict")
                continue
            for field in ("element", "source", "date"):
                if field not in val:
                    problems.append(f"{name}.{key}: missing '{field}'")
            elem = val.get("element", "")
            if elem and elem in seen:
                problems.append(f"duplicate: {seen[elem]} vs {name}.{key}")
            elif elem:
                seen[elem] = f"{name}.{key}"
    return problems


def check_provenance(canon, accepted, refuted, genome_data):
    problems = []
    known_sections = {"decisions", "hypotheses", "notes"}
    classified = set()
    for section in (canon, accepted, refuted):
        for val in section.values():
            if isinstance(val, dict) and val.get("classifies"):
                classified.add(val["classifies"].lower())

    for section_name in genome_data:
        if section_name in known_sections:
            continue
        if section_name.lower() not in classified:
            problems.append(f"PROVENANCE: section '{section_name}' not classified")

    for key, val in canon.items():
        if isinstance(val, dict) and val.get("source") != "user":
            problems.append(f"PROVENANCE: canon.{key} source != 'user'")

    for key, val in accepted.items():
        if isinstance(val, dict):
            if val.get("source") != "assistant":
                problems.append(f"PROVENANCE: accepted.{key} source != 'assistant'")
            if val.get("accepted_by") != "user":
                problems.append(f"PROVENANCE: accepted.{key} missing accepted_by")

    return problems


def warn_open_questions(canon):
    opens = [(k, v) for k, v in canon.items()
             if isinstance(v, dict) and v.get("status") == "open_question"]
    for k, v in opens:
        print(f"[OPEN] {k}: {v['element']}")
    return len(opens)


def warn_refuted(refuted):
    if not refuted:
        return
    from collections import defaultdict
    by_reason = defaultdict(list)
    for k, v in refuted.items():
        if isinstance(v, dict):
            by_reason[v.get("reason", "?")].append(k)
    print(f"[REFUTED] {len(refuted)} elements stored (not used):")
    for reason, keys in sorted(by_reason.items()):
        print(f"  [{reason}] {len(keys)}: {', '.join(keys)}")


class Hypotheses:
    def __init__(self, hypotheses: dict):
        self.h = hypotheses

    def open_list(self):
        return [k for k, v in self.h.items()
                if isinstance(v, dict) and v.get("status") == "open"]

    def warn(self):
        opens = self.open_list()
        if opens:
            print(f"[HYPOTHESES] {len(opens)} open: {', '.join(opens)}")
        return len(opens)


class K:
    """
    ACCEPTED A1: K = anchor (select / value / bind).
    ACCEPTED A2: K берёт точку, не создаёт.
    """

    def select(self, git_history, condition):
        """
        H001: K берёт точку из GIT, не создаёт.
        git_history: deque — поток событий в памяти.
        condition: callable(event) -> bool.
        Возвращает id или None.
        """
        for event in reversed(git_history):
            if condition(event):
                return event.get("id")
        return None

    def value(self):
        """H002: value() — контекст K + p1…p10. HYPOTHESIS."""
        return {"anchor": None, "components": []}

    def bind(self, *constants):
        """H003: bind() — контекст CORE. H003: M# не определён."""
        return {"constants": list(constants)}


class Auditor:
    """
    ACCEPTED A5: local = audit (симуляция, один процесс, две роли).
    ACCEPTED A10: итерация = полный цикл 4 вызовов.
    """

    def run(self, request: dict) -> dict:
        """
        Local-аудит: проверяет update_request по 4 вызовам.
        Роли old и new — внутри одного процесса.

        challenges возвращается как dict (не list):
        - имена вызовов видны в результате
        - failed перечисляет упавшие вызовы
        - порядок вызовов не влияет на чтение результата
        """
        challenges = {
            "k_touched": self._check_k_touched(request),
            "policies_compatible": self._check_policies_compatible(request),
            "append_only": self._check_append_only(request),
            "connections_intact": self._check_connections_intact(request),
        }

        verdict = "accept" if all(challenges.values()) else "reject"
        failed = [name for name, ok in challenges.items() if not ok]

        return {
            "verdict": verdict,
            "challenges": challenges,
            "failed": failed,
            "request_id": request.get("id"),
            "mode": "audit",
        }

    def _check_k_touched(self, request: dict) -> bool:
        """Затрагивает ли request K (токен, границы, 1:1:1)? True=безопасно."""
        target = str(request.get("target", ""))
        change = str(request.get("change", ""))
        if "genome.json" in target and "token" in change.lower():
            return False
        return True

    def _check_policies_compatible(self, request: dict) -> bool:
        """H009: совместимость политик. HYPOTHESIS: заглушка True."""
        return True

    def _check_append_only(self, request: dict) -> bool:
        """Не нарушает ли request append-only?"""
        action = str(request.get("action", ""))
        if action in ("overwrite", "delete"):
            return False
        return True

    def _check_connections_intact(self, request: dict) -> bool:
        """HYPOTHESIS: заглушка True."""
        return True


class Dialog:
    """ACCEPTED A5: peer/cell = dialog."""
    def __init__(self):
        self.role = None
        self.challenge_timeout = 10
        self.dialog_timeout = 60

    def open(self, peer, request):
        raise NotImplementedError("Dialog.open — not yet implemented")

    def compatible(self, k_old, k_new):
        raise NotImplementedError("Dialog.compatible — not yet implemented")

    def iterate(self):
        raise NotImplementedError("Dialog.iterate — not yet implemented")


class Runtime:
    def __init__(self, mode: str = "solo",
                 history_maxlen: int = 1000,
                 test_iterations: int | None = None):
        self.mode = mode
        self.history = deque(maxlen=history_maxlen)
        self.test_iterations = test_iterations

        self.canon, self.accepted, self.refuted, hypotheses, genome_data = load_decisions()
        self.hypotheses = Hypotheses(hypotheses)
        self.genome_data = genome_data

        self.active = {**self.accepted, **self.canon}

        self.k = K()
        self.auditor = Auditor()
        self.dialog = Dialog()
        self.booted = False
        self.running = False

    def append_history(self, event: dict):
        """A21: пишет в history (v0.5)."""
        self.history.append(event)

    def boot(self):
        print(f"🧬 Multimod Polilog — runtime v0.5")
        print(f"   token: MONOMOD::MM5FFF681946L6G6A111")
        print(f"   mode:  {self.mode}")
        print()

        problems = check_integrity(self.canon, self.accepted, self.refuted)
        problems += check_provenance(self.canon, self.accepted, self.refuted, self.genome_data)
        if problems:
            print(f"[INTEGRITY] {len(problems)} problems:")
            for p in problems:
                print(f"  - {p}")
        else:
            print("[INTEGRITY] ok")

        print(f"[CANON]    {len(self.canon)} elements")
        print(f"[ACCEPTED] {len(self.accepted)} elements")
        print(f"[REFUTED]  {len(self.refuted)} elements")
        print(f"[ACTIVE]   {len(self.active)} elements")
        print()

        n_open = warn_open_questions(self.canon)
        n_hyp = self.hypotheses.warn()
        warn_refuted(self.refuted)

        expected_log = MODE_TO_LOG.get(self.mode)
        present = Path(expected_log).exists() if expected_log else False
        print(f"[LOG] mode={self.mode} → {expected_log} ({'present' if present else 'absent'})")

        print()
        print(f"✓ boot complete. open_questions={n_open}, hypotheses={n_hyp}")
        self.booted = True

    def run(self):
        if not self.booted:
            self.boot()
        self.running = True
        print(f"[RUN] mode={self.mode} — press Ctrl+C to stop")
        try:
            iteration = 0
            while self.running:
                iteration += 1
                if self.test_iterations and iteration >= self.test_iterations:
                    print(f"[RUN] test mode — exit after {iteration} iterations")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            print()
            print("[RUN] KeyboardInterrupt — stopping cleanly")
        finally:
            self.running = False

    def shutdown(self):
        print(f"🧬 shutdown. history size={len(self.history)}")


def positive_int(value):
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError(f"must be > 0, got {n}")
    return n


def parse_args():
    p = argparse.ArgumentParser(prog="runtime.py",
                                description="Multimod Polilog runtime. Default mode=solo.")
    p.add_argument("--mode",
                   choices=["solo", "hybrid-peer", "hybrid-cell", "remote"],
                   default="solo")
    p.add_argument("--test-iterations", type=positive_int, default=None)
    p.add_argument("--daemon", action="store_true")
    p.add_argument("--no-ui", action="store_true")
    p.add_argument("--version", action="version",
                   version="runtime.py 0.5 — MONOMOD::MM5FFF681946L6G6A111")
    return p.parse_args()


def main():
    args = parse_args()
    rt = Runtime(mode=args.mode, test_iterations=args.test_iterations)
    exit_code = 0
    try:
        rt.boot()
        rt.run()
    except KeyboardInterrupt:
        print()
        print("[INTERRUPT] Ctrl+C at top level")
    except Exception as e:
        print(f"[FATAL] {type(e).__name__}: {e}", file=sys.stderr)
        exit_code = 1
    finally:
        rt.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()