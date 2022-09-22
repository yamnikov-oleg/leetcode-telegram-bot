import enum
import time
from dataclasses import dataclass

import requests


def leetcode_query(query: str, variables: dict) -> dict:
    resp = requests.post(
        "https://leetcode.com/graphql/",
        json={
            "query": query,
            "variables": variables,
        },
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.content}")

    # Rate limiting
    time.sleep(1)

    return resp.json()


class Difficulty(enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


@dataclass
class Question:
    title: str
    title_slug: str
    difficulty: Difficulty
    is_paid_only: bool

    @classmethod
    def from_json(cls, data: dict) -> "Question":
        return Question(
            title=data["title"],
            title_slug=data["titleSlug"],
            difficulty=Difficulty(data["difficulty"].upper()),
            is_paid_only=data["isPaidOnly"],
        )

    @property
    def url(self) -> str:
        return f"https://leetcode.com/problems/{self.title_slug}/"


def get_random_question(difficulty: Difficulty) -> Question:
    resp_json = leetcode_query(
        query="""
            query randomQuestion($filters: QuestionListFilterInput) {
                randomQuestion(categorySlug: "", filters: $filters) {
                    title
                    titleSlug
                    difficulty
                    isPaidOnly
                }
            }
        """,
        variables={
            "filters": {"difficulty": difficulty.value},
        },
    )

    question = Question.from_json(resp_json["data"]["randomQuestion"])
    if question.is_paid_only:
        # Trying again
        return get_random_question(difficulty)
    else:
        return question
