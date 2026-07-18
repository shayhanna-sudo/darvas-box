"""Darvas-Bot entrypoint (scaffold). Engine: src/darvas_engine.py"""
import config
from src import db


def init():
    db.init_db(config.DB_PATH)
    print("[Darvas-Bot] DB ready.")
    print("[Darvas-Bot] KILL_SWITCH =", config.KILL_SWITCH)


if __name__ == "__main__":
    init()
