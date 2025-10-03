import csv
import random
import sys
from pathlib import Path


def main(csv_path):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"Error: File {csv_path} not found")
        return

    output_path = csv_path.with_suffix(".md")

    with open(csv_path, newline="",
              encoding="utf-8") as csvfile, open(output_path,
                                                 "w",
                                                 encoding="utf-8") as mdfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            story_title = row.get("story_title", "").strip()
            question = row.get("question", "").strip()
            correct_answer = row.get("correct answer", "").strip()
            negative_answer = row.get("negative answer", "").strip()

            # Randomize order
            if random.random() < 0.5:
                answers = [correct_answer, negative_answer]
                correct_index = 1
            else:
                answers = [negative_answer, correct_answer]
                correct_index = 2

            # Write Markdown
            mdfile.write(f"# {story_title}\n\n")
            mdfile.write(f"## {question}\n\n")
            mdfile.write(f"1. {answers[0]}\n")
            mdfile.write(f"2. {answers[1]}\n\n")
            mdfile.write(f"Correct_answer: {correct_index}\n\n")
            mdfile.write("-----\n\n")

    print(f"Markdown file created: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py input.csv")
    else:
        main(sys.argv[1])
