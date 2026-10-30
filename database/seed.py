"""Reproducibly seed fictional demo identities."""
from .db import connect, init_db

STUDENTS = [
    ("STU1001", "Asha Rao", "PGDM Big Data Analytics", 2, 250000, 180000, "partially_paid", "under_review", "Merit scholarship application is under review; final award not recorded."),
    ("STU1002", "Kabir Mehta", "PGDM AI & Data Science", 1, 240000, 240000, "paid", "approved", "Merit scholarship approved for the current academic year."),
    ("STU1003", "Mira Sen", "PGDM Big Data Analytics", 3, 260000, 0, "unpaid", "not_applied", "No scholarship application is on record."),
]

def seed(path=None):
    init_db(path)
    with connect(path) as db:
        db.executemany("INSERT OR IGNORE INTO students(student_id,display_name,programme,semester,fee_amount,amount_paid,payment_status,scholarship_status,scholarship_eligibility) VALUES(?,?,?,?,?,?,?,?,?)", STUDENTS)

if __name__ == "__main__":
    seed()
