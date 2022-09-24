from functools import wraps
from typing import List, Optional, Tuple

import telegram
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, declarative_base, relationship

from . import settings
from .questions import Difficulty
from .utils import now

Base = declarative_base()
engine = create_engine(settings.DB_URL, echo=True, future=True)


class Post(Base):
    __tablename__ = "post"

    id = Column(Integer, primary_key=True)
    message_id = Column(String, nullable=False)
    posted = Column(DateTime(timezone=True), nullable=False, default=now)

    questions = relationship("PostQuestion", back_populates="post", cascade="all, delete-orphan")


class PostQuestion(Base):
    __tablename__ = "post_question"

    DIFFICULTY_EASY = 1
    DIFFICULTY_MEDIUM = 2
    DIFFICULTY_HARD = 3

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)
    post = relationship("Post", back_populates="questions")
    leetcode_title_slug = Column(String, nullable=False)
    difficulty = Column(Integer, nullable=False)

    @property
    def difficulty_enum(self) -> Optional[Difficulty]:
        if self.difficulty == self.DIFFICULTY_EASY:
            return Difficulty.EASY
        elif self.difficulty == self.DIFFICULTY_MEDIUM:
            return Difficulty.MEDIUM
        elif self.difficulty == self.DIFFICULTY_HARD:
            return Difficulty.HARD
        else:
            return None

    @difficulty_enum.setter
    def difficulty_enum(self, value: Difficulty) -> None:
        if value == Difficulty.EASY:
            self.difficulty = self.DIFFICULTY_EASY
        elif value == Difficulty.MEDIUM:
            self.difficulty = self.DIFFICULTY_MEDIUM
        elif value == Difficulty.HARD:
            self.difficulty = self.DIFFICULTY_HARD
        else:
            raise TypeError(f"Expected Difficulty, got {type(value)}")


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, nullable=False)
    name = Column(String, nullable=False)

    solutions = relationship("Solution", back_populates="user", cascade="all, delete-orphan")


class Solution(Base):
    __tablename__ = "solution"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = relationship("User", back_populates="solutions")
    leetcode_id = Column(String, nullable=False, index=True)
    post_question_id = Column(Integer, ForeignKey("post_question.id"), nullable=False)
    post_question = relationship("PostQuestion")
    posted = Column(DateTime(timezone=True), nullable=False, default=now)


def ensure_user(session: Session, telegram_user: telegram.User) -> User:
    """
    Commit after calling this function.
    """
    user = session.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
    if user:
        if user.name != telegram_user.full_name:
            user.name = telegram_user.full_name

        return user

    user = User(telegram_id=telegram_user.id, name=telegram_user.full_name)
    session.add(user)
    return user


def get_top_solvers(session: Session) -> List[Tuple[User, int]]:
    return (
        session.query(User, func.count(Solution.leetcode_id))
        .select_from(Solution)
        .join(User)
        .filter(Solution.posted > (now() - settings.SCORE_DELTA))
        .group_by(Solution.user_id)
        .having(func.count(Solution.leetcode_id) > 0)
        .order_by(func.count(Solution.leetcode_id).desc())[:10]
    )


def create_tables():
    Base.metadata.create_all(engine)


def with_session(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with Session(engine) as session:
            f(*args, session=session, **kwargs)

    return wrapper
