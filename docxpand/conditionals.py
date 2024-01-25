import random
import typing as tp


class Conditional:
    def __init__(seed: tp.Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    @staticmethod
    def uniform(probability: float = 0.5) -> bool:
        return random.random() <= probability

    @staticmethod
    def maybe(**kwargs) -> bool:
        raise NotImplementedError("Must be implemented in child class")


class BirthNameConditional(Conditional):
    @staticmethod
    def maybe(**kwargs) -> bool:
        gender: str = kwargs.get("gender", "nonbinary")
        probability_by_gender = kwargs.get(
            "probability_by_gender",
            {"male": 0.05, "female": 0.2, "nonbinary": 0.2},
        )
        probability = probability_by_gender.get(gender, 0.2)
        return Conditional.uniform(probability)
