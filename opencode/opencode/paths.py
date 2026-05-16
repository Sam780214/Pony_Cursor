import os


def opencode_data_dir() -> str:
    d = (os.environ.get("OPENCODE_DATA_DIR") or "").strip()
    if d:
        return os.path.expandvars(os.path.expanduser(d))
    return os.path.join(os.path.expanduser("~"), ".local", "share", "opencode")


def opencode_db_path() -> str:
    db = (os.environ.get("OPENCODE_DB") or "").strip()
    if db:
        return os.path.expandvars(os.path.expanduser(db))
    return os.path.join(opencode_data_dir(), "opencode.db")


def backups_dir() -> str:
    return os.path.join(opencode_data_dir(), "backups")


def record_dir() -> str:
    rd = (os.environ.get("OPENCODE_RECORD_DIR") or "").strip()
    if rd:
        return os.path.expandvars(os.path.expanduser(rd))
    return r"D:\Pony"
