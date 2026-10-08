"""Small SQLite transactions; retain durable commits when power is interrupted."""
import sqlite3
import time

def connect(path,timeout=5):
    db=sqlite3.connect(str(path),timeout=timeout)
    db.execute('PRAGMA synchronous=FULL')
    return db

def retry_transaction(path,operation,attempts=3,timeout=5):
    for attempt in range(attempts):
        db=connect(path,timeout)
        try:
            with db:return operation(db)
        except sqlite3.OperationalError as error:
            code=getattr(error,'sqlite_errorcode',None)
            if code not in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED) or attempt+1==attempts:raise
            time.sleep(.2*(attempt+1))
        finally:db.close()
