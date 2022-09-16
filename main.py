import enum
import logging
import random
import time
from dataclasses import dataclass

import requests
from schedule import Scheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

import settings

logging.basicConfig(format="%(asctime)s [%(name)s : %(levelname)s] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


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


difficulty_marker = {
    Difficulty.EASY: "🥉",
    Difficulty.MEDIUM: "🥈",
    Difficulty.HARD: "🥇",
}


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


def question_to_button(question: Question) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"{difficulty_marker[question.difficulty]} {question.title.strip()}",
        url=question.url,
    )


def post_question(bot: Bot) -> None:
    logger.info("Requesting questions...")

    text = random.choice(settings.MESSAGES)

    easy_question = get_random_question(Difficulty.EASY)
    medium_question = get_random_question(Difficulty.MEDIUM)
    hard_question = get_random_question(Difficulty.HARD)

    bot.send_message(
        chat_id=settings.CHAT_ID,
        text=text,
        reply_markup=InlineKeyboardMarkup(
            [
                [question_to_button(easy_question)],
                [question_to_button(medium_question)],
                [question_to_button(hard_question)],
            ],
        ),
    )


def main():
    bot = Bot(settings.BOT_TOKEN)
    scheduler = Scheduler()

    def task():
        try:
            post_question(bot)
        except Exception:
            logger.exception("Task failed")

    settings.SCHEDULE(scheduler, task)

    while True:
        scheduler.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
