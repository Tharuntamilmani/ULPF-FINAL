"""Fix admin password hash using bcrypt directly."""
import os, psycopg2, bcrypt

host = os.environ.get("POSTGRES_HOST", "postgres")
pwd  = os.environ.get("POSTGRES_PASSWORD", "")
admin_pass = os.environ.get("ADMIN_PASSWORD", "Admin@SIH2026!")

new_hash = bcrypt.hashpw(admin_pass.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
print(f"New hash generated for password: {admin_pass}")

conn = psycopg2.connect(host=host, port=5432, dbname="m6_control_plane", user="m6user", password=pwd)
conn.autocommit = True
cur = conn.cursor()
cur.execute("UPDATE users SET hashed_password = %s WHERE username = 'admin'", (new_hash,))
print(f"Updated {cur.rowcount} row(s).")
conn.close()
print("Admin password hash updated successfully.")
