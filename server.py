import os
import json
import pymysql
import psycopg2
from mcp.server.fastmcp import FastMCP

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Initialize FastMCP Server
mcp = FastMCP("Dual-DB-Manager")

def get_db_connection(db_type: str):
    """Routes the connection to the correct database driver."""
    if db_type == "postgres":
        return psycopg2.connect(
            host=os.getenv("PG_HOST", "localhost"),
            database=os.getenv("PG_DATABASE", "analytics"),
            user=os.getenv("PG_USER", "admin"),
            password=os.getenv("PG_PASSWORD"),
            port=os.getenv("PG_PORT", "5432")
        )
    elif db_type == "mysql":
        return pymysql.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            database=os.getenv("MYSQL_DATABASE", "inventory"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD"),
            port=int(os.getenv("MYSQL_PORT", "3306"))
        )
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

@mcp.tool()
def execute_read_query(db_type: str, sql_query: str) -> str:
    """Executes a read-only (SELECT) query on either a 'mysql' or 'postgres' database.
    Returns the results stringified in JSON format.
    """
    # Safeguard validation rule
    if not sql_query.lower().strip().startswith("select"):
        return "Error: Only SELECT queries are permitted via this tool."
    
    try:
        conn = get_db_connection(db_type)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        
        # Fetch column names dynamically from the cursor description
        column_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        # Convert raw tuples to dictionary output mapping column -> value
        results = [dict(zip(column_names, row)) for row in rows]
        
        cursor.close()
        conn.close()
        
        return json.dumps(results, default=str)
    except Exception as e:
        return f"Database Error encountered: {str(e)}"

@mcp.tool()
def get_database_schema(db_type: str) -> str:
    """Retrieves the table names and structures for the specified db_type ('mysql' or 'postgres')."""
    if db_type == "postgres":
        query = """
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public';
        """
    else: # mysql
        query = """
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = DATABASE();
        """
    
    try:
        conn = get_db_connection(db_type)
        cursor = conn.cursor()
        cursor.execute(query)
        
        column_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        results = [dict(zip(column_names, row)) for row in rows]
        
        cursor.close()
        conn.close()
        
        return json.dumps(results, default=str)
    except Exception as e:
        return f"Database Error encountered: {str(e)}"

# 4. Start the Server
if __name__ == "__main__":
    mcp.run(transport='sse')