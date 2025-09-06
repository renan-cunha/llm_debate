python -m core.debate \
  exp_dir='./exp/test3' \
  +experiment='debate'\
  ++correct_debater.language_model.model='gpt-5-nano-2025-08-07' \
  ++incorrect_debater.language_model.model='gpt-5-nano-2025-08-07' \
  ++correct_debater.BoN=1 \
  ++incorrect_debater.BoN=1 \
  ++max_num_from_same_story=1 \
  ++split=train