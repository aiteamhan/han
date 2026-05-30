import sqlite3
import os

DB_PATH = os.environ.get('DATABASE_URL', 'wechat.db')
# If DATABASE_URL is a sqlite URI like sqlite:///wechat.db, extract path
if DB_PATH.startswith('sqlite:///'):
    DB_PATH = DB_PATH.replace('sqlite:///', '')

print('Using DB:', DB_PATH)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info('messages')")
cols = [r[1] for r in cur.fetchall()]
print('Existing columns:', cols)
changed = False
if 'is_edited' not in cols:
    print('Adding is_edited column...')
    try:
        cur.execute("ALTER TABLE messages ADD COLUMN is_edited BOOLEAN DEFAULT 0")
        changed = True
    except Exception as e:
        print('Failed to add is_edited:', e)
if 'edited_at' not in cols:
    print('Adding edited_at column...')
    try:
        cur.execute("ALTER TABLE messages ADD COLUMN edited_at DATETIME")
        changed = True
    except Exception as e:
        print('Failed to add edited_at:', e)

if changed:
    conn.commit()
    print('Migration applied.')
else:
    print('No changes needed.')

conn.close()
