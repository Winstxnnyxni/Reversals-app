from database import get_connection, init_db

# 🔥 Ensure tables exist
init_db()

username = input("Enter username: ")
password = input("Enter password: ")

conn = get_connection()
c = conn.cursor()

c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))

conn.commit()
conn.close()

print("User created successfully")