"""Fix lowercase status values in sources table."""
import os, psycopg2
conn = psycopg2.connect(host='postgres', port=5432, dbname='m6_control_plane', user='m6user', password=os.environ.get('POSTGRES_PASSWORD','M6PostgresSIH2026'))
conn.autocommit = True
cur = conn.cursor()
# Fix sources status to uppercase
cur.execute("UPDATE sources SET status = UPPER(status) WHERE status != UPPER(status)")
print(f"Fixed {cur.rowcount} sources status values")
# Fix services last_status
cur.execute("UPDATE services SET last_status = UPPER(last_status) WHERE last_status != UPPER(last_status)")
print(f"Fixed {cur.rowcount} services last_status values")
# Show current values
cur.execute("SELECT source_id, status FROM sources")
for r in cur.fetchall():
    print(f"  source: {r[0]} -> {r[1]}")
conn.close()
print("Done.")
