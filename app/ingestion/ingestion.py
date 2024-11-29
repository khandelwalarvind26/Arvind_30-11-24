import psycopg2, os
from urllib.parse import urlparse
from app.core.config import settings

# Database URL
db_url = settings.DATABASE_URL

# Parse the URL
result = urlparse(db_url)

# Extract the connection parameters
username = result.username
password = result.password
hostname = result.hostname
port = result.port
dbname = result.path[1:]  # Removing the leading '/' in the path


def get_connection():
    try:
        return psycopg2.connect(
            dbname=dbname,
            user=username,
            password=password,
            host=hostname,
            port=port
        )

    except Exception as error:
        print(f"Error: {error}")
        return False
    
conn = get_connection()

if conn:
    print("Connection to the PostgreSQL established successfully.")
else:
    print("Connection to the PostgreSQL encountered an error.")


curr = conn.cursor()
print("Cursor created.")

# Determine the root of the project (two levels up from 'app' folder)
current_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "/store-monitoring-data/"))

set_timezone_query = """SET TIMEZONE = 'UTC';"""

create_store_hours_table_query = """
    CREATE TABLE IF NOT EXISTS store_hours (
        id SERIAL PRIMARY KEY,
        store_id VARCHAR(36),
        day_of_week INT CHECK (day_of_week BETWEEN 0 AND 6), 
        start_time_local TIME,
        end_time_local TIME
    );
"""

create_timezones_table_query = """
    CREATE TABLE IF NOT EXISTS stores (
        store_id VARCHAR(36) PRIMARY KEY,
        timezone_str VARCHAR(50)
    );
"""

create_store_status_query = """
    CREATE TYPE status AS ENUM ('active', 'inactive');
    CREATE TABLE IF NOT EXISTS store_status (
        id SERIAL PRIMARY KEY,
        store_id VARCHAR(36),
        status status,
        timestamp TIMESTAMP WITH TIME ZONE
    );
"""

curr.execute(create_store_hours_table_query)
curr.execute(create_timezones_table_query)
curr.execute(create_store_status_query)
print("Table created.")

timezones_file_path = os.path.join(current_path, "timezones.csv")
with open(timezones_file_path, 'r') as f:
    curr.copy_expert(
        "COPY stores (store_id, timezone_str) FROM stdin WITH CSV HEADER", f
    )

store_hours_file_path = os.path.join(current_path, "menu_hours.csv")
with open(store_hours_file_path, 'r') as f:
    curr.copy_expert(
        "COPY store_hours (store_id, day_of_week, start_time_local, end_time_local) FROM stdin WITH CSV HEADER", f
    )

store_status_file_path = os.path.join(current_path, "store_status.csv")
with open(store_status_file_path, 'r') as f:
    curr.copy_expert(
        "COPY store_status (store_id, status, timestamp) FROM stdin WITH CSV HEADER", f
    )

# curr.execute(add_missing_store_ids_query)
print("Inserted values, starting commit.")
conn.commit()
print("Finished commit.")

curr.close()
conn.close()

