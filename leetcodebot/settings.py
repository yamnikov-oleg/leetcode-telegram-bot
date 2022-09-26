import logging
from datetime import timedelta
from pathlib import Path

logging.basicConfig(format="%(asctime)s [%(name)s : %(levelname)s] %(message)s", level=logging.INFO)

BASE_DIR = Path(__name__).resolve().parent
DB_URL = f"sqlite:///{BASE_DIR / 'data' / 'db.sqlite3'}"

BOT_TOKEN = ""
CHAT_ID = ""

LEETCODE_CSRF = ""
LEETCODE_SESSION = ""
LEETCODE_USER_AGENT = ""

SCORE_DELTA = timedelta(days=90)

MESSAGES = [
    "Are you up for the today's challenge?",
    "Finished your morning coffee? How about a leetcode problem?",
]

MESSAGE_SUBMISSION_LOAD_ERROR = "⚠️ Could not load submission <b>{id}</b>."
MESSAGE_SUBMISSION_WRONG_QUESTION = "⚠️ Submission <b>{id}</b> belongs to a different problem."
MESSAGE_SUBMISSION_ALREADY_SOLVED = "⚠️ Submission <b>{id}</b> refused as you have already solved that problem."
MESSAGE_SUBMISSION_TAKEN = (
    '⚠️ Submission <b>{id}</b> was already submitted by <a href="tg://user?id={by_id}">{by_name}</a>.'
)
MESSAGE_SUBMISSION_ACCEPTED = "✅ Submission <b>{id}</b> accepted."
MESSAGE_YOUR_SCORE_HEADER = "<b>Your score for the past 3 months:</b>"
MESSAGE_YOUR_SCORE = "{score} solution(s)!"
MESSAGE_TOP_SCORES_HEADER = "<b>Top scores for the past 3 months:</b>"
MESSAGE_TOP_SCORE = '{place}. <a href="tg://user?id={user_id}">{user_name}</a>: {score}'


def SCHEDULE(scheduler, task):
    scheduler.every().monday.at("7:00").do(task)
    scheduler.every().thursday.at("7:00").do(task)


try:
    from .local_settings import *  # noqa: F401, F403
except ImportError:
    pass
