#!/bin/bash

# Variables
experiment_name="debate"
model_name="gpt-4.1-mini-2025-04-14"
exp_dir="./exp/gpt4_1_mini_4debaters_sandbag_v5"

# gpt-5-mini-2025-08-07

sandbag=true
num_debaters=4

for arg in "$@"; do
  if [ "$arg" == "--sandbag" ]; then
    sandbag=true
  elif [[ "$arg" == --num_debaters=* ]]; then
    num_debaters="${arg#*=}"
  fi
done

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
  sandbag=$sandbag \
  num_debaters=$num_debaters

# Judge run
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
