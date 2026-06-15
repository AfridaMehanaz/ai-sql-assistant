"""Meridian Bank SQL Agent.

Flow: question -> LLM writes SQL (knows schema) -> execute READ-ONLY ->
      if SQL errors, feed error back to LLM to self-correct (max 2 retries) ->
      LLM turns rows into a plain-English answer.

Safety: opens DB read-only; rejects any non-SELECT statement.

Run:  python src/agent.py "which customers have loans in default?"
"""
import os
import re
import sys
import json
import sqlite3

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "banking.db")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
API_KEY = os.getenv("LLM_API_KEY", "set-me")
MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
MAX_RETRIES = 2

_client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def get_schema() -> str:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    con.close()
    return "\n\n".join(r[0] for r in rows)


def is_safe(sql: str) -> bool:
    s = sql.strip().rstrip(";").lower()
    if ";" in s:
        return False
    if not s.startswith("select"):
        return False
    banned = ("insert", "update", "delete", "drop", "alter",
              "create", "replace", "attach", "pragma")
    return not any(re.search(rf"\b{b}\b", s) for b in banned)


def run_sql(sql: str):
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, cur.fetchall()
    finally:
        con.close()


def _llm(system: str, user: str) -> str:
    resp = _client.chat.completions.create(
        model=MODEL, temperature=0.0,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content.strip()


def write_sql(question: str, schema: str, error: str = "") -> str:
    fix = f"\n\nYour previous SQL failed with:\n{error}\nFix it." if error else ""
    system = (
        "You are a SQLite expert. Given the schema, write ONE read-only SELECT "
        "query that answers the question. Return ONLY the SQL, no markdown, no "
        "explanation, no semicolon."
    )
    raw = _llm(system, f"SCHEMA:\n{schema}\n\nQUESTION: {question}{fix}")
    return raw.replace("```sql", "").replace("```", "").strip().rstrip(";")


def explain(question: str, sql: str, cols, rows) -> str:
    system = "Answer the user's question in 1-3 sentences using the query result. Be specific."
    preview = json.dumps({"columns": cols, "rows": rows[:50]}, default=str)
    return _llm(system, f"QUESTION: {question}\nSQL: {sql}\nRESULT: {preview}")


def ask(question: str) -> dict:
    schema = get_schema()
    error = ""
    log = []
    for attempt in range(MAX_RETRIES + 1):
        sql = write_sql(question, schema, error)
        if not is_safe(sql):
            return {"answer": "Refused: generated query was not a safe read-only SELECT.",
                    "sql": sql, "log": log + ["[BLOCK] unsafe SQL rejected"]}
        try:
            cols, rows = run_sql(sql)
            answer = explain(question, sql, cols, rows)
            return {"answer": answer, "sql": sql, "rows": rows, "log": log}
        except Exception as e:
            error = str(e)
            log.append(f"[RETRY {attempt+1}] SQL error -> self-correcting: {error}")
    return {"answer": "Could not produce a working query after retries.",
            "sql": sql, "log": log}


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Which customers have loans in default?"
    out = ask(q)
    print("\n=== SQL ===\n" + out["sql"])
    print("\n=== ANSWER ===\n" + out["answer"])
    if out.get("log"):
        print("\n=== AGENT LOG ===")
        for line in out["log"]:
            print(" ", line)