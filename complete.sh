#!/bin/bash
set -euo pipefail

# Defaults
experiment_name="debate"
model_name="gpt-4.1-mini-2025-04-14"
exp_dir="./exp/gpt4_1_mini_4debaters_sandbag_v5"
sandbag=false
num_debaters=2

show_help() {
  cat <<EOF
Usage: $0 [--exp_dir=PATH] [--sandbag] [--num_debaters=N] [--model_name=MODEL] [--help]

Options:
  --exp_dir=PATH        Directory to store experiment artifacts (default: $exp_dir)
  --sandbag             Enable sandbagging (default: $sandbag)
  --num_debaters=N      Number of debaters (default: $num_debaters)
  --model_name=MODEL    Language model name (default: $model_name)
  --help                Show this help and exit
EOF
}

# Parse CLI args
for arg in "$@"; do
  case "$arg" in
    --sandbag) sandbag=true ;;
    --num_debaters=*) num_debaters="${arg#*=}" ;;
    --exp_dir=*) exp_dir="${arg#*=}" ;;
    --model_name=*) model_name="${arg#*=}" ;;
    --help|-h) show_help; exit 0 ;;
    *) echo "Unknown option: $arg"; show_help; exit 1 ;;
  esac
done

# Start timer
start_ts=$(date +%s)

echo "=== Running debate pipeline ==="
echo "experiment_name: $experiment_name"
echo "model_name:      $model_name"
echo "exp_dir:         $exp_dir"
echo "sandbag:         $sandbag"
echo "num_debaters:    $num_debaters"
echo "==============================="

# Debate run
python -m core.debate \
  exp_dir="$exp_dir" \
  +experiment="$experiment_name" \
  ++correct_debater.language_model.model="$model_name" \
  ++incorrect_debater.language_model.model="$model_name" \
  ++correct_debater.BoN=1 \
  ++incorrect_debater.BoN=1 \
  ++max_num_from_same_story=1 \
  ++split=train \
  sandbag="$sandbag" \
  num_debaters="$num_debaters"

# Judge run (fixed model for consistency)
python -m core.judge \
  exp_dir="$exp_dir" \
  +experiment="$experiment_name" \
  ++judge.language_model.model="gpt-4.1-mini-2025-04-14" \
  ++judge_name="gpt-4.1-mini-2025-04-14"

# Scoring run
python -m core.scoring.accuracy \
  exp_dir="$exp_dir" \
  +experiment="$experiment_name" \
  ++judge_name="gpt-4.1-mini-2025-04-14"

# End timer and report
end_ts=$(date +%s)
elapsed=$(( end_ts - start_ts ))
printf "\nTotal runtime: %02d:%02d:%02d (hh:mm:ss)\n" \
  $((elapsed/3600)) $(((elapsed%3600)/60)) $((elapsed%60))
