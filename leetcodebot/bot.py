import logging
import random
import time

from schedule import Scheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from . import settings
from .questions import Difficulty, Question, get_random_question

logger = logging.getLogger(__name__)


difficulty_marker = {
    Difficulty.EASY: "🥉",
    Difficulty.MEDIUM: "🥈",
    Difficulty.HARD: "🥇",
}


def question_to_button(question: Question) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"{difficulty_marker[question.difficulty]} {question.title.strip()}",
        url=question.url,
    )


def post_questions(bot: Bot) -> None:
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


def run():
    bot = Bot(settings.BOT_TOKEN)
    scheduler = Scheduler()

    def task():
        try:
            post_questions(bot)
        except Exception:
            logger.exception("Task failed")

    settings.SCHEDULE(scheduler, task)

    while True:
        scheduler.run_pending()
        time.sleep(60)
