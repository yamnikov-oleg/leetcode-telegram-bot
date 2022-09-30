import logging
import random
import re
from typing import List, Tuple

from schedule import Scheduler
from sqlalchemy.orm import Session
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, Filters, MessageHandler, Updater

from . import settings
from .db import (
    Post,
    PostQuestion,
    Solution,
    User,
    ensure_user,
    get_top_solvers,
    with_session,
)
from .questions import (
    Difficulty,
    Question,
    get_random_question,
    get_submission_question_slug,
)
from .utils import escape_html, now

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


@with_session
def post_questions(bot: Bot, session: Session) -> None:
    logger.info("Requesting questions...")

    top_scores = get_top_solvers(session)
    text_lines = [
        random.choice(settings.MESSAGES),
        "",
        *format_top_scores(top_scores),
    ]

    easy_question = get_random_question(Difficulty.EASY)
    medium_question = get_random_question(Difficulty.MEDIUM)
    hard_question = get_random_question(Difficulty.HARD)

    message = bot.send_message(
        chat_id=settings.CHAT_ID,
        text="\n".join(text_lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [
                [question_to_button(easy_question)],
                [question_to_button(medium_question)],
                [question_to_button(hard_question)],
            ],
        ),
        disable_notification=True,
    )

    post = Post(message_id=str(message.message_id))
    for question in [easy_question, medium_question, hard_question]:
        post_question = PostQuestion(leetcode_title_slug=question.title_slug)
        post_question.difficulty_enum = question.difficulty
        post.questions.append(post_question)

    session.add(post)
    session.commit()


def format_top_scores(top_scores: List[Tuple[User, int]]) -> List[str]:
    lines = []
    if top_scores:
        lines.append(settings.MESSAGE_TOP_SCORES_HEADER)
        for ix, (top_user, top_score) in enumerate(top_scores):
            lines.append(
                settings.MESSAGE_TOP_SCORE.format(
                    place=ix + 1,
                    user_id=top_user.telegram_id,
                    user_name=escape_html(top_user.name),
                    score=top_score,
                )
            )
    return lines


@with_session
def on_reply(update: Update, context: CallbackContext, session: Session) -> None:
    if not update.message or str(update.message.chat_id) != str(settings.CHAT_ID):
        return

    reply_to_id = update.message.reply_to_message.message_id
    post = session.query(Post).filter(Post.message_id == reply_to_id).first()
    if not post:
        return

    user = ensure_user(session, update.message.from_user)

    logger.info("Reply from %s (tg id %s) to post (tg id %s)", user.name, user.telegram_id, post.message_id)

    submission_url_re = re.compile(r"https:\/\/leetcode\.com\/submissions\/detail\/(\d+)\/")
    submission_url_matches = list(submission_url_re.finditer(update.message.text))
    # Process only the first 3 urls at max to prevent DOS attacks
    submission_url_matches = submission_url_matches[:3]

    if not submission_url_matches:
        return

    loaded_solutions = []
    error_messages = []

    for match in submission_url_matches:
        submission_id = match.group(1)

        try:
            question_slug = get_submission_question_slug(submission_id)
        except Exception:
            logger.exception("Loading submission failed")
            error_messages.append(settings.MESSAGE_SUBMISSION_LOAD_ERROR.format(id=submission_id))
            continue

        post_question = None
        for pq in post.questions:
            if pq.leetcode_title_slug == question_slug:
                post_question = pq
                break

        if not post_question:
            error_messages.append(settings.MESSAGE_SUBMISSION_WRONG_QUESTION.format(id=submission_id))
            continue

        solved_before = (
            session.query(Solution)
            .join(Solution.post_question)
            .filter(Solution.user_id == user.id)
            .filter(PostQuestion.leetcode_title_slug == question_slug)
            .first()
            is not None
        )
        if solved_before:
            error_messages.append(settings.MESSAGE_SUBMISSION_ALREADY_SOLVED.format(id=submission_id))
            continue

        old_solution = session.query(Solution).filter(Solution.leetcode_id == submission_id).first()
        if old_solution:
            error_messages.append(
                settings.MESSAGE_SUBMISSION_TAKEN.format(
                    id=submission_id,
                    by_id=old_solution.user.telegram_id,
                    by_name=escape_html(old_solution.user.name),
                )
            )
            continue

        loaded_solutions.append(
            Solution(
                user=user,
                leetcode_id=submission_id,
                post_question=post_question,
            )
        )

    response_text_lines = []

    for solution in loaded_solutions:
        response_text_lines.append(settings.MESSAGE_SUBMISSION_ACCEPTED.format(id=solution.leetcode_id))

    if loaded_solutions:
        response_text_lines.append("")

    response_text_lines.extend(error_messages)

    if error_messages:
        response_text_lines.append("")

    response_text_lines.append(settings.MESSAGE_YOUR_SCORE_HEADER)

    user_score = (
        session.query(Solution)
        .filter(
            Solution.user_id == user.id,
            Solution.posted > (now() - settings.SCORE_DELTA),
        )
        .count()
    )
    response_text_lines.append(settings.MESSAGE_YOUR_SCORE.format(score=user_score))
    response_text_lines.append("")

    top_scores = get_top_solvers(session)
    top_score_lines = format_top_scores(top_scores)
    response_text_lines.extend(top_score_lines)

    context.bot.send_message(
        chat_id=settings.CHAT_ID,
        text="\n".join(response_text_lines),
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id,
        disable_notification=True,
    )

    session.commit()


def run():
    updater = Updater(settings.BOT_TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.reply & ~Filters.command, on_reply))

    bot = Bot(settings.BOT_TOKEN)
    scheduler = Scheduler()

    def task():
        try:
            post_questions(bot)
        except Exception:
            logger.exception("Task failed")

    settings.SCHEDULE(scheduler, task)
    updater.job_queue.run_repeating(lambda context: scheduler.run_pending(), interval=60)

    updater.start_polling()
    updater.idle()
