"""Build Meridian Bank demo database (synthetic data only).

Creates banking.db with: customers, accounts, transactions, loans, payments.
Run:  python src/build_db.py
"""
import os
import random
import sqlite3
from datetime import date, timedelta

DB_PATH = os.getenv("DB_PATH", "banking.db")
random.seed(42)

SCHEMA = """
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    city          TEXT NOT NULL,
    state         TEXT NOT NULL,
    join_date     DATE NOT NULL,
    credit_score  INTEGER NOT NULL
);

CREATE TABLE accounts (
    account_id    INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    account_type  TEXT NOT NULL,
    branch        TEXT NOT NULL,
    balance       REAL NOT NULL,
    opened_date   DATE NOT NULL
);

CREATE TABLE transactions (
    txn_id        INTEGER PRIMARY KEY,
    account_id    INTEGER NOT NULL REFERENCES accounts(account_id),
    txn_date      DATE NOT NULL,
    amount        REAL NOT NULL,
    category      TEXT NOT NULL
);

CREATE TABLE loans (
    loan_id       INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    loan_type     TEXT NOT NULL,
    principal     REAL NOT NULL,
    interest_rate REAL NOT NULL,
    start_date    DATE NOT NULL,
    status        TEXT NOT NULL
);

CREATE TABLE payments (
    payment_id    INTEGER PRIMARY KEY,
    loan_id       INTEGER NOT NULL REFERENCES loans(loan_id),
    due_date      DATE NOT NULL,
    paid_date     DATE,
    amount        REAL NOT NULL
);
"""

NAMES = ["James Carter", "Maria Lopez", "Wei Chen", "Aisha Khan", "John Smith",
         "Priya Patel", "David Kim", "Sarah Jones", "Omar Hassan", "Emily Davis",
         "Luis Garcia", "Nina Rossi", "Tom Walker", "Fatima Ali", "Raj Mehta"]
CITIES = [("Boston", "MA"), ("Austin", "TX"), ("Denver", "CO"), ("Seattle", "WA"),
          ("Miami", "FL"), ("Chicago", "IL")]
BRANCHES = ["Downtown", "Westside", "North Hills", "Lakeview"]
TXN_CATS = ["groceries", "salary", "utilities", "transfer", "atm", "dining"]
LOAN_TYPES = ["mortgage", "auto", "personal"]


def build():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    for cid in range(1, 16):
        city, st = random.choice(CITIES)
        join = date(2020, 1, 1) + timedelta(days=random.randint(0, 1500))
        cur.execute("INSERT INTO customers VALUES (?,?,?,?,?,?)",
                    (cid, NAMES[cid - 1], city, st, join.isoformat(),
                     random.randint(580, 820)))

    aid = 1
    for cid in range(1, 16):
        for _ in range(random.randint(1, 2)):
            opened = date(2021, 1, 1) + timedelta(days=random.randint(0, 1200))
            cur.execute("INSERT INTO accounts VALUES (?,?,?,?,?,?)",
                        (aid, cid, random.choice(["checking", "savings"]),
                         random.choice(BRANCHES), round(random.uniform(200, 95000), 2),
                         opened.isoformat()))
            aid += 1
    n_accounts = aid - 1

    tid = 1
    for acc in range(1, n_accounts + 1):
        for _ in range(20):
            d = date(2025, 1, 1) + timedelta(days=random.randint(0, 530))
            amt = round(random.uniform(-2000, 4000), 2)
            cur.execute("INSERT INTO transactions VALUES (?,?,?,?,?)",
                        (tid, acc, d.isoformat(), amt, random.choice(TXN_CATS)))
            tid += 1

    lid = 1
    for cid in range(1, 16):
        if random.random() < 0.6:
            lt = random.choice(LOAN_TYPES)
            principal = {"mortgage": random.uniform(150000, 600000),
                         "auto": random.uniform(8000, 60000),
                         "personal": random.uniform(2000, 40000)}[lt]
            start = date(2022, 1, 1) + timedelta(days=random.randint(0, 900))
            status = random.choice(["active", "active", "active", "paid_off", "default"])
            cur.execute("INSERT INTO loans VALUES (?,?,?,?,?,?,?)",
                        (lid, cid, lt, round(principal, 2),
                         round(random.uniform(3.5, 9.5), 2), start.isoformat(), status))
            for m in range(12):
                due = start + timedelta(days=30 * m)
                missed = random.random() < 0.15
                paid = None if missed else (due + timedelta(days=random.randint(0, 5))).isoformat()
                cur.execute("INSERT INTO payments (loan_id, due_date, paid_date, amount) "
                            "VALUES (?,?,?,?)",
                            (lid, due.isoformat(), paid, round(principal / 120, 2)))
            lid += 1

    con.commit()
    con.close()
    print(f"Built {DB_PATH}: 15 customers, {n_accounts} accounts, {lid-1} loans")


if __name__ == "__main__":
    build()