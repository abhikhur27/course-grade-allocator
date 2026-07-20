# Course Grade Allocator

Practical Python CLI for figuring out what average you need on the remaining parts of a course to hit a target grade.

## Why this project exists

Syllabus math gets annoying when some categories are graded and others are still open. This tool gives a fast answer to questions like:

- What average do I need on the project + final to finish with an A?
- Is my target still reachable?
- If I average 88 on the remaining work, where do I land?
- Which remaining category actually matters the most?

## Input format

The CSV must contain exactly these columns:

```csv
category,weight,earned_pct
Homework,20,92
Final Exam,25,
```

- `weight`: percentage of the final course grade
- `earned_pct`: current score in that category, or blank if it is still pending

Weights must sum to `100`.

## Usage

Basic target table:

```bash
python grade_allocator.py --input sample_gradebook.csv
```

Custom targets:

```bash
python grade_allocator.py --input sample_gradebook.csv --targets 93,90,87,80
```

Project a likely finish:

```bash
python grade_allocator.py --input sample_gradebook.csv --pending-average 88
```

Compare several remaining-average what-if scenarios at once:

```bash
python grade_allocator.py --input sample_gradebook.csv --pending-grid 70,80,85,90,95
```

Lock in one known pending score and solve the rest around it:

```bash
python grade_allocator.py --input sample_gradebook.csv --known-score "Final Exam=91" --targets 93,90,87
```

Export the target table:

```bash
python grade_allocator.py --input sample_gradebook.csv --output reports/targets.csv
```

Write a Markdown planning brief you can drop into notes:

```bash
python grade_allocator.py --input sample_gradebook.csv --pending-grid 75,85,95 --markdown-output reports/grade-plan.md
```

## Sample output

```text
Course Grade Allocator
======================
Completed weight:          60.00%
Remaining weight:          40.00%
Locked course points:      51.10
Average on graded work:    85.17%
```

The report now also prints a remaining-leverage section so you can see how much each unfinished category moves the final grade.

## Verification

```bash
python -m py_compile grade_allocator.py
python grade_allocator.py --input sample_gradebook.csv --pending-average 88
python grade_allocator.py --input sample_gradebook.csv --known-score "Final Exam=91"
python grade_allocator.py --input sample_gradebook.csv --pending-grid 75,85,95
```

## Portfolio Positioning

- Project type: Python command-line student utility
- Best use: quick syllabus planning before finals and project-heavy weeks
- Direction fit: useful standalone software rather than another browser-only demo
