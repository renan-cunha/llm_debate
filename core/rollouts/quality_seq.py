import json

import pandas as pd

from core.agents.debater_quality import DebaterQuality
from core.file_handler import Method
from core.rollouts.rollout_base import RolloutBase
from core.rollouts.utils import (
    Answers,
    CacheManager,
    DebaterNames,
    Round,
    TranscriptConfig,
)


class QualitySeqRollout(RolloutBase):
    def __init__(self, *args):
        super().__init__(*args)
        assert (
            self.correct_debaters and self.incorrect_debaters
        ), "Both debaters must be specified"
        assert (
            self.correct_judge_critic is None and self.incorrect_judge_critic is None
        ), "Critique refinement not supported for sequential debate"

    async def debate_turn(
        self,
        transcript: TranscriptConfig,
        current_step: int,
        cache_manager: CacheManager,
        pair_index: int,
        swap: bool = False,
    ):
        order_name = ["correct", "incorrect"] if not swap else ["incorrect", "correct"]
        order_debater = (
            [
                self.correct_debaters[pair_index],
                self.incorrect_debaters[pair_index],
            ]
            if not swap
            else [
                self.incorrect_debaters[pair_index],
                self.correct_debaters[pair_index],
            ]
        )
        order_BoN = (
            [self.correct_judge_BoN, self.incorrect_judge_BoN]
            if not swap
            else [self.incorrect_judge_BoN, self.correct_judge_BoN]
        )

        round_type = "sim" if current_step == 0 else "seq"
        new_round = {
            "type": round_type,
        }
        new_responses = {"type": round_type}
        transcript.rounds.append(Round(**new_round))
        transcript.responses.append(Round(**new_round))
        if self.cross_examiner and current_step != 0:
            question, response = await self.cross_examiner.take_turn(
                transcript,
                current_step,
                cache_manager,
            )
            new_round["cross_examiner"] = question
            new_responses["cross_examiner"] = response
            transcript.rounds[-1] = Round(**new_round)
            transcript.responses[-1] = Round(**new_responses)

        argument0, response0 = await order_debater[0].take_turn(
            transcript, current_step, cache_manager, order_BoN[0]
        )
        new_round[order_name[0]] = argument0
        new_responses[order_name[0]] = response0
        if current_step != 0:
            transcript.responses[-1] = Round(**new_responses)
            transcript.rounds[-1] = Round(**new_round)

        argument1, response1 = await order_debater[1].take_turn(
            transcript, current_step, cache_manager, order_BoN[1]
        )

        new_responses[order_name[1]] = response1
        new_round[order_name[1]] = argument1
        transcript.responses[-1] = Round(**new_responses)
        transcript.rounds[-1] = Round(**new_round)
        cache_manager.save_item(current_step, "transcript", transcript.json())

        return transcript

    # No need for swap, it will be judge-time
    async def run(self, index: int, row: pd.Series, swap=False):
        names = {}
        if self.method == Method.debate:
            names["correct"] = self.config.name1 if not swap else self.config.name2
            names["incorrect"] = self.config.name2 if not swap else self.config.name1
            names["cross_examiner"] = (
                self.config.cross_examiner_name if self.cross_examiner else None
            )
        else:
            names["correct"] = (
                self.config.consultant_name if self.correct_debaters else None
            )
            names["incorrect"] = (
                self.config.consultant_name if self.incorrect_debaters else None
            )
            names["cross_examiner"] = (
                self.config.cross_examiner_name if self.cross_examiner else None
            )

        transcript = TranscriptConfig(
            index=index,
            story=row["story"],
            story_title=row["story_title"],
            question=row["question"],
            question_set_id=row["question_set_id"],
            answers=Answers(
                correct=row["correct answer"], incorrect=row["negative answer"]
            ),
            names=DebaterNames(**names),
            swap=swap,
            rollout_type=self.config.rollout_type,
        )
        # Load cached results if they exist
        cache_manager = CacheManager(self.cache_dir, transcript.index)
        current_step, transcript_cache, _ = cache_manager.unpack_results()
        if transcript_cache is not None:
            transcript = TranscriptConfig(**json.loads(transcript_cache))
        transcript_string = transcript.json()

        num_pairs = max(len(self.correct_debaters), len(self.incorrect_debaters))
        total_steps = self.config.num_steps * num_pairs

        # Run the debate
        while current_step < total_steps:
            try:
                pair_idx = current_step % num_pairs
                transcript = await self.debate_turn(
                    transcript, current_step, cache_manager, pair_idx, swap
                )
                current_step += 1
                transcript_string = transcript.json()
            except (RuntimeError, IndexError, ValueError) as e:
                transcript_string = f"Error occurred on debate {transcript.index}, step {current_step}. Error message: {e}."
                current_step = -1
                print(transcript_string)
                break
        complete = current_step >= total_steps
        if complete:
            debaters = (
                self.correct_debaters
                if self.correct_debaters
                else self.incorrect_debaters
            )
            print(f"Completed: {transcript.index}")
            total_cost = sum(d.api_handler.running_cost for d in debaters)
            print(f"Total cost: {total_cost:.3f}")
        return {
            "transcript": transcript_string,
            "complete": complete,
        }
