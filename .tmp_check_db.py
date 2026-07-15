from __future__ import annotations

import sqlite3
from pathlib import Path

db = Path("data/database/quiz_app.db")
con = sqlite3.connect(str(db))
cur = con.cursor()
print("version", cur.execute("select version_num from alembic_version").fetchall())
print("question_types", cur.execute("select question_type, count(*) from questions group by question_type").fetchall())
print("questions_sql", cur.execute("select sql from sqlite_master where type='table' and name='questions'").fetchone()[0])
con.close()
