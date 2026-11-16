import getpass
import sqlite3
from pathlib import Path

from pwdlib import PasswordHash

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_DIR / "database" / "data.db"

if not DATABASE_PATH.is_file():
    raise SystemExit("Khong tim thay database/data.db. Hay chay setup.bat truoc.")

connection = sqlite3.connect(DATABASE_PATH)
try:
    if connection.execute(
        "SELECT 1 FROM users WHERE role = 'admin' LIMIT 1"
    ).fetchone():
        print("Database da co tai khoan admin; bo qua buoc tao moi.")
        raise SystemExit(0)
finally:
    connection.close()

while True:
    username = input("Ten dang nhap admin: ").strip()
    if not 3 <= len(username) <= 50:
        print("Ten dang nhap can dai tu 3 den 50 ky tu.")
        continue

    connection = sqlite3.connect(DATABASE_PATH)
    try:
        exists = connection.execute(
            "SELECT 1 FROM users WHERE username = ?", (username,)
        ).fetchone()
    finally:
        connection.close()
    if exists:
        print("Ten dang nhap da duoc su dung; hay chon ten khac.")
        continue
    break

full_name = input("Ho va ten admin: ").strip()
if not full_name or len(full_name) > 100:
    raise SystemExit("Ho ten khong duoc de trong va toi da 100 ky tu.")

while True:
    password = getpass.getpass("Mat khau admin (8-128 ky tu): ")
    if not 8 <= len(password) <= 128:
        print("Mat khau can dai tu 8 den 128 ky tu.")
        continue
    confirmation = getpass.getpass("Nhap lai mat khau: ")
    if password != confirmation:
        print("Hai mat khau khong khop; thu lai.")
        continue
    break

password_hash = PasswordHash.recommended().hash(password)
connection = sqlite3.connect(DATABASE_PATH)
try:
    connection.execute(
        "INSERT INTO users (username, password_hash, full_name, role, is_active) "
        "VALUES (?, ?, ?, 'admin', 1)",
        (username, password_hash, full_name),
    )
    connection.commit()
finally:
    connection.close()

print("Tao tai khoan admin thanh cong.")
