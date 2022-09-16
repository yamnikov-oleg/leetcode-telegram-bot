BOT_TOKEN = ""
CHAT_ID = ""

MESSAGES = [
    "Are you up for the today's challenge?",
    "Finished your morning coffee? How about a leetcode problem?",
]


def SCHEDULE(scheduler, task):
    scheduler.every().monday.at("7:00").do(task)
    scheduler.every().thursday.at("7:00").do(task)


try:
    from local_settings import *  # noqa: F401, F403
except ImportError:
    pass
