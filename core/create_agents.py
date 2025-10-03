import logging
from pathlib import Path
from typing import List, Optional

from omegaconf import DictConfig

from core.agents.debater_base import DebaterBase, DebaterConfig
from core.agents.debater_quality import DebaterQuality
from core.agents.judge_base import JudgeBase, JudgeConfig
from core.agents.judge_quality import JudgeQuality
from core.file_handler import Method
from core.llm_api.llm import ModelAPI
from core.rollouts.quality_seq import QualitySeqRollout
from core.rollouts.quality_sim import QualitySimRollout
from core.rollouts.rollout_base import RolloutBase, RolloutConfig

DEBATER_CLASSES = {
    "quality": DebaterQuality,
}
LOGGER = logging.getLogger(__name__)


def create_debater(
    method: Method,
    config: DebaterConfig,
    correct: bool,
    api_handler: ModelAPI,
) -> DebaterBase:
    debater_class = DEBATER_CLASSES.get(config.debater_type)
    if not debater_class:
        raise ValueError(f"Unknown debater type: {config.debater_type}")
    return debater_class(method, config, correct, api_handler)


JUDGE_CLASSES = {
    "quality": JudgeQuality,
}


def create_judge(
    method: Method,
    config: JudgeConfig,
    rollout_config: RolloutConfig,
    api_handler: ModelAPI,
) -> JudgeBase:
    judge_class = JUDGE_CLASSES.get(config.judge_type)
    if not judge_class:
        raise ValueError(f"Unknown judge type: {config.judge_type}")
    return judge_class(method, config, rollout_config, api_handler)


# setup rollout
ROLLOUT_CLASSES = {
    "quality_sim": QualitySimRollout,
    "quality_seq": QualitySeqRollout,
}


def create_rollout(
    method: Method,
    config: RolloutConfig,
    cache_dir: Path,
    correct_debaters: List[DebaterBase] | DebaterBase | None,
    incorrect_debaters: List[DebaterBase] | DebaterBase | None,
    cross_examiner: Optional[JudgeBase],
    correct_judge_BoN: Optional[JudgeBase],
    incorrect_judge_BoN: Optional[JudgeBase],
    correct_judge_critic: Optional[JudgeBase],
    incorrect_judge_critic: Optional[JudgeBase],
    correct_judge_critique_pm: Optional[JudgeBase],
    incorrect_judge_critique_pm: Optional[JudgeBase],
) -> RolloutBase:
    rollout_class = ROLLOUT_CLASSES.get(config.rollout_type)
    if not rollout_class:
        raise ValueError(f"Unknown rollout type: {config.rollout_type}")

    if correct_debaters is None:
        correct_list: List[DebaterBase] = []
    elif isinstance(correct_debaters, list):
        correct_list = correct_debaters
    else:
        correct_list = [correct_debaters]

    if incorrect_debaters is None:
        incorrect_list: List[DebaterBase] = []
    elif isinstance(incorrect_debaters, list):
        incorrect_list = incorrect_debaters
    else:
        incorrect_list = [incorrect_debaters]

    return rollout_class(
        method,
        config,
        cache_dir,
        correct_list,
        incorrect_list,
        cross_examiner,
        correct_judge_BoN,
        incorrect_judge_BoN,
        correct_judge_critic,
        incorrect_judge_critic,
        correct_judge_critique_pm,
        incorrect_judge_critique_pm,
    )


def setup_debate(
    cfg: dict,
    cache_dir: Path,
    api_handler: ModelAPI,
) -> RolloutBase:
    assert cfg.rollout.name1 != cfg.rollout.name2

    num_debaters = getattr(cfg, "num_debaters", 2)
    assert num_debaters % 2 == 0, "num_debaters must be even"
    num_per_side = num_debaters // 2

    import copy

    correct_configs = [copy.deepcopy(cfg.correct_debater) for _ in range(num_per_side)]
    incorrect_configs = [
        copy.deepcopy(cfg.incorrect_debater) for _ in range(num_per_side)
    ]

    if getattr(cfg, "sandbag", False):
        sandbag_path = Path(__file__).resolve().parents[1] / "sandbag_prompt.txt"
        with open(sandbag_path, "r", encoding="utf-8") as f:
            sandbag_text = f.read().strip()
        for i, conf in enumerate(correct_configs):
            if i == 0:
                continue
            sys_prompt = conf.prompts.messages[0].content
            correct_configs[i].prompts.messages[0].content = (
                sandbag_text + "\n" + sys_prompt
            )
    for i, conf in enumerate(correct_configs):
        print(correct_configs[i].prompts.messages[0].content[:500])
        print("=" * 80)
    import sys

    correct_judge_BoN = (
        create_judge(cfg.method, cfg.correct_preference, cfg.rollout, api_handler)
        if cfg.correct_debater.BoN > 1
        else None
    )
    incorrect_judge_BoN = (
        create_judge(cfg.method, cfg.incorrect_preference, cfg.rollout, api_handler)
        if cfg.incorrect_debater.BoN > 1
        else None
    )
    correct_judge_critic = (
        create_judge(cfg.method, cfg.correct_critic, cfg.rollout, api_handler)
        if cfg.correct_debater.cBoN > 0
        else None
    )
    incorrect_judge_critic = (
        create_judge(cfg.method, cfg.incorrect_critic, cfg.rollout, api_handler)
        if cfg.incorrect_debater.cBoN > 0
        else None
    )
    correct_judge_critique_pm = (
        create_judge(cfg.method, cfg.correct_critique_pm, cfg.rollout, api_handler)
        if cfg.correct_debater.cBoN > 0
        else None
    )
    incorrect_judge_critique_pm = (
        create_judge(cfg.method, cfg.incorrect_critique_pm, cfg.rollout, api_handler)
        if cfg.incorrect_debater.cBoN > 0
        else None
    )

    if cfg.method == "debate" or cfg.method == "baseline":
        correct_debaters = [
            create_debater(cfg.method, conf, correct=True, api_handler=api_handler)
            for conf in correct_configs
        ]
        incorrect_debaters = [
            create_debater(cfg.method, conf, correct=False, api_handler=api_handler)
            for conf in incorrect_configs
        ]

    if cfg.method == "consultancy":
        if cfg.method_type == "correct":
            correct_debaters = [
                create_debater(cfg.method, conf, correct=True, api_handler=api_handler)
                for conf in correct_configs
            ]
            incorrect_debaters = []

        elif cfg.method_type == "incorrect":
            correct_debaters = []
            incorrect_debaters = [
                create_debater(cfg.method, conf, correct=False, api_handler=api_handler)
                for conf in incorrect_configs
            ]
        else:
            raise ValueError(f"Unknown method type: {cfg.method_type}")

    if cfg.use_intermediary:
        cross_examiner = create_judge(
            cfg.method,
            cfg.cross_examiner,
            cfg.rollout,
            api_handler,
        )
    else:
        cross_examiner = None

    rollout = create_rollout(
        cfg.method,
        cfg.rollout,
        cache_dir,
        correct_debaters,
        incorrect_debaters,
        cross_examiner,
        correct_judge_BoN,
        incorrect_judge_BoN,
        correct_judge_critic,
        incorrect_judge_critic,
        correct_judge_critique_pm,
        incorrect_judge_critique_pm,
    )
    if correct_debaters:
        LOGGER.info(cfg.correct_debater.language_model)
    if incorrect_debaters:
        LOGGER.info(cfg.incorrect_debater.language_model)
    if cross_examiner:
        LOGGER.info(cfg.cross_examiner.language_model)
    return rollout


def setup_judge(
    cfg: DictConfig,
    judge_cfg: DictConfig,
    api_handler: ModelAPI,
):
    judge = create_judge(cfg.method, judge_cfg, cfg.rollout, api_handler)
    return judge
