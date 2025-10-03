#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def parse_args():
    p = argparse.ArgumentParser(
        description="Extract QA/debate JSON from a CSV and render to Markdown."
    )
    p.add_argument(
        "csv_path",
        help="Path to the CSV file containing 'transcript' and 'answer_judge'",
    )
    p.add_argument("row", type=int, help="Row index (0-based) to read from the CSV")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output .md path (default: <csvstem>_row<row>.md)",
    )
    return p.parse_args()


def get_row_values(
    csv_path: str, row_idx: int, cols=("transcript", "answer_judge")
) -> Dict[str, str]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in cols if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"Missing required columns {missing}. Available: {reader.fieldnames}"
            )
        for i, rec in enumerate(reader):
            if i == row_idx:
                return {c: (rec.get(c) or "") for c in cols}
    raise IndexError(f"Row {row_idx} out of range.")


def robust_json_load(s: str) -> Dict[str, Any]:
    """
    Parse the 'transcript' JSON which may be wrapped in single quotes
    or double-encoded with escaped characters.
    """
    s = (s or "").strip()
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        s = s[1:-1]
    obj = json.loads(s)
    if isinstance(obj, str):
        obj = json.loads(obj)
    if not isinstance(obj, dict):
        raise ValueError("Parsed 'transcript' JSON is not an object/dict.")
    return obj


def normalize_text_cell(s: str) -> str:
    """
    Best-effort to return readable text for 'answer_judge':
    - strip one pair of outer single quotes if present
    - if it's a JSON-encoded string, json.loads it
    - otherwise lightly unescape common sequences for readability
    """
    if s is None:
        return ""
    s = s.strip()
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        s = s[1:-1]
    try:
        maybe = json.loads(s)
        if isinstance(maybe, str):
            return maybe
    except Exception:
        pass
    s = s.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')
    return s


ARGUMENT_RE = re.compile(r"<argument>(.*?)</argument>", flags=re.DOTALL | re.IGNORECASE)
THINKING_RE = re.compile(r"</?thinking>", flags=re.IGNORECASE)


def extract_argument(text: str) -> str:
    """
    Prefer content inside <argument>...</argument>.
    If absent, strip <thinking> tags and return remaining text.
    """
    if not isinstance(text, str):
        return ""
    m = ARGUMENT_RE.search(text)
    if m:
        content = m.group(1).strip()
    else:
        content = THINKING_RE.sub("", text).strip()
    return content


def collect_debate_rounds(obj: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Return a list of (correct_text, incorrect_text) pairs across rounds.
    If 'rounds' missing/empty, fall back to 'responses'.
    """
    rounds = []
    if isinstance(obj.get("rounds"), list) and obj["rounds"]:
        for r in obj["rounds"]:
            c = extract_argument(r.get("correct", ""))
            i = extract_argument(r.get("incorrect", ""))
            if c or i:
                rounds.append((c, i))
    elif isinstance(obj.get("responses"), list) and obj["responses"]:
        for r in obj["responses"]:
            c = extract_argument(r.get("correct", ""))
            i = extract_argument(r.get("incorrect", ""))
            if c or i:
                rounds.append((c, i))
    return rounds


def determine_correct_is_A(obj: Dict[str, Any]) -> bool:
    """
    Use the transcript's 'names' mapping to decide whether 'correct' corresponds to Debater A.
    Fallback: A = correct if mapping is missing/unknown.
    """
    names = obj.get("names")
    if isinstance(names, dict):
        corr = names.get("correct")
        inc = names.get("incorrect")

        def to_side(s: Any):
            if not isinstance(s, str):
                return None
            t = s.strip().lower()
            if t in ("debater a", "a", "debater_a"):
                return "A"
            if t in ("debater b", "b", "debater_b"):
                return "B"
            return None

        side_corr = to_side(corr)
        side_inc = to_side(inc)
        if side_corr == "A":
            return True
        if side_corr == "B":
            return False
        if side_inc == "A":
            return False
        if side_inc == "B":
            return True
    return True  # default


def build_markdown(obj: Dict[str, Any], judge_blob: str) -> str:
    question = (obj.get("question") or "").strip()
    story = (obj.get("story") or "").rstrip()
    pairs = collect_debate_rounds(obj)

    correct_is_A = determine_correct_is_A(obj)

    lines = []
    # Question
    lines.append(f"# Question\n\n{question}\n")
    # Debate
    lines.append("# Debate\n")
    if not pairs:
        lines.append("_No debate rounds found in this sample._\n")
    else:
        for idx, (correct_txt, incorrect_txt) in enumerate(pairs, start=1):
            lines.append(f"## Round {idx}\n")
            if correct_is_A:
                a_txt, b_txt = correct_txt, incorrect_txt
            else:
                a_txt, b_txt = incorrect_txt, correct_txt
            lines.append(f"**Debater A:**\n\n{(a_txt or '_(no content)_')}\n")
            lines.append(f"**Debater B:**\n\n{(b_txt or '_(no content)_')}\n")

    # Judge block (verbatim)
    if judge_blob.strip():
        lines.append("\n# Judge (answer_judge)\n")
        lines.append(judge_blob.strip() + "\n")

    # Story
    lines.append("\n# Story\n")
    lines.append(story + "\n")

    # Answer (who is correct per transcript mapping)
    lines.append("\n# Answer\n")
    lines.append(f"**Correct debater: {'A' if correct_is_A else 'B'}**\n")

    return "\n".join(lines)


def main():
    args = parse_args()
    cells = get_row_values(args.csv_path, args.row, cols=("transcript", "answer_judge"))
    transcript_raw = cells["transcript"]
    judge_raw = cells.get("answer_judge", "")

    obj = robust_json_load(transcript_raw)
    judge_blob = normalize_text_cell(judge_raw)

    md = build_markdown(obj, judge_blob)
    out_path = args.out or Path(f"{Path(args.csv_path).stem}_row{args.row}.md")
    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
