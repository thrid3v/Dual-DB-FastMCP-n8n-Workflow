import json
import os
import re
import pymysql
import psycopg2
from psycopg2 import sql
from fastmcp import FastMCP

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Initialize FastMCP Server
mcp = FastMCP('Dual-DB-Manager')


def validate_identifier(name: str) -> bool:
    return bool(re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name))


def validate_column_type(column_type: str) -> bool:
    return bool(re.match(r'^[A-Za-z0-9_()\s,]+$', column_type))


def parse_json_input(value, name: str) -> dict:
    if isinstance(value, dict):
        parsed = value
    else:
        try:
            parsed = json.loads(value)
        except Exception as exc:
            raise ValueError(f'Invalid JSON for {name}: {exc}')
    if not isinstance(parsed, dict):
        raise ValueError(f'{name} must be a JSON object.')
    return parsed


def get_db_connection(db_type: str, database: str | None = None):
    '''Routes the connection to the correct database driver.'''
    if db_type == 'postgres':
        return psycopg2.connect(
            host=os.getenv('PG_HOST', 'localhost'),
            database=database or os.getenv('PG_DATABASE', 'analytics'),
            user=os.getenv('PG_USER', 'admin'),
            password=os.getenv('PG_PASSWORD', os.getenv('POSTGRES_PASSWORD')),
            port=os.getenv('PG_PORT', '5432')
        )
    elif db_type == 'mysql':
        return pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            database=database or os.getenv('MYSQL_DATABASE', 'inventory'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD')),
            port=int(os.getenv('MYSQL_PORT', '3306'))
        )
    else:
        raise ValueError(f'Unsupported database type: {db_type}')


@mcp.tool()
def create_database(db_type: str, database_name: str) -> str:
    '''Creates a new database in either MySQL or PostgreSQL.'''
    if not validate_identifier(database_name):
        return 'Error: Invalid database name. Use letters, numbers, and underscores only.'

    try:
        if db_type == 'postgres':
            conn = get_db_connection('postgres', os.getenv('PG_CREATE_DB', 'postgres'))
            # CREATE DATABASE cannot run inside a transaction block; psycopg2
            # opens one implicitly unless the connection is in autocommit mode.
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(sql.SQL('CREATE DATABASE {};').format(sql.Identifier(database_name)))
        elif db_type == 'mysql':
            conn = get_db_connection('mysql', os.getenv('MYSQL_CREATE_DB', 'mysql'))
            cursor = conn.cursor()
            cursor.execute(f'CREATE DATABASE `{database_name}`;')
        else:
            return f'Error: Unsupported database type: {db_type}'

        conn.commit()
        cursor.close()
        conn.close()
        return f"Database '{database_name}' created successfully for {db_type}."
    except Exception as e:
        return f'Database Error encountered: {str(e)}'


@mcp.tool()
def create_table(
    db_type: str,
    table_name: str,
    columns: dict,
    primary_key: str = '',
    if_not_exists: bool = True,
) -> str:
    '''Creates a table using a JSON object for column definitions.'''
    if not validate_identifier(table_name):
        return 'Error: Invalid table name. Use letters, numbers, and underscores only.'

    if isinstance(columns, dict):
        columns_data = columns
    else:
        try:
            columns_data = parse_json_input(columns, 'columns')
        except ValueError as exc:
            return str(exc)

    if not columns_data:
        return 'Error: columns must be a non-empty object mapping names to types.'
    if primary_key and not validate_identifier(primary_key):
        return 'Error: Invalid primary key column name. Use letters, numbers, and underscores only.'

    for name, col_type in columns_data.items():
        if not validate_identifier(name):
            return f"Error: Invalid column name '{name}'. Use letters, numbers, and underscores only."
        if not isinstance(col_type, str) or not validate_column_type(col_type):
            return f"Error: Invalid column type for '{name}'."

    try:
        if db_type == 'postgres':
            conn = get_db_connection('postgres')
            cursor = conn.cursor()
            if_clause = 'IF NOT EXISTS ' if if_not_exists else ''
            column_defs = [
                sql.SQL('{} {}').format(sql.Identifier(name), sql.SQL(col_type))
                for name, col_type in columns_data.items()
            ]
            if primary_key:
                column_defs.append(sql.SQL('PRIMARY KEY ({})').format(sql.Identifier(primary_key)))
            query = sql.SQL('CREATE TABLE {if_not_exists}{table} ({columns});').format(
                if_not_exists=sql.SQL(if_clause),
                table=sql.Identifier(table_name),
                columns=sql.SQL(', ').join(column_defs),
            )
            cursor.execute(query)
        elif db_type == 'mysql':
            conn = get_db_connection('mysql')
            cursor = conn.cursor()
            if_clause = 'IF NOT EXISTS ' if if_not_exists else ''
            column_defs = [f'`{name}` {col_type}' for name, col_type in columns_data.items()]
            if primary_key:
                column_defs.append(f'PRIMARY KEY (`{primary_key}`)')
            query = f'CREATE TABLE {if_clause}`{table_name}` ({', '.join(column_defs)});'
            cursor.execute(query)
        else:
            return f'Error: Unsupported database type: {db_type}'

        conn.commit()
        cursor.close()
        conn.close()
        return f"Table '{table_name}' created successfully for {db_type}."
    except Exception as e:
        return f'Database Error encountered: {str(e)}'


@mcp.tool()
def insert_data(db_type: str, table_name: str, row_data: dict) -> str:
    '''Inserts a single row into the specified table for MySQL or PostgreSQL.'''
    if not validate_identifier(table_name):
        return 'Error: Invalid table name. Use letters, numbers, and underscores only.'

    if isinstance(row_data, dict):
        row = row_data
    else:
        try:
            row = parse_json_input(row_data, 'row_data')
        except ValueError as exc:
            return str(exc)

    if not row:
        return 'Error: row_data must be a non-empty object.'
    if not all(validate_identifier(col) for col in row.keys()):
        return 'Error: Invalid column names. Use letters, numbers, and underscores only.'

    columns = list(row.keys())
    values = list(row.values())

    try:
        if db_type == 'postgres':
            conn = get_db_connection('postgres')
            cursor = conn.cursor()
            query = sql.SQL('INSERT INTO {} ({}) VALUES ({});').format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(sql.Placeholder() for _ in columns),
            )
            cursor.execute(query, values)
        elif db_type == 'mysql':
            conn = get_db_connection('mysql')
            cursor = conn.cursor()
            placeholders = ', '.join(['%s'] * len(columns))
            columns_sql = ', '.join(f'`{col}`' for col in columns)
            query = f'INSERT INTO `{table_name}` ({columns_sql}) VALUES ({placeholders});'
            cursor.execute(query, values)
        else:
            return f'Error: Unsupported database type: {db_type}'

        conn.commit()
        cursor.close()
        conn.close()
        return f'Inserted row into {table_name} successfully.'
    except Exception as e:
        return f'Database Error encountered: {str(e)}'


@mcp.tool()
def read_data(db_type: str, table_name: str = '', sql_query: str = '', limit: int = 10) -> str:
    '''Reads data from a database. Either provide table_name for simple fetch, or sql_query for custom SELECT.
    
    Examples:
    - Simple: table_name="products", limit=3
    - Custom: sql_query="SELECT * FROM products WHERE price > 100"
    '''
    if table_name and sql_query:
        return 'Error: Provide either table_name or sql_query, not both.'
    
    if not table_name and not sql_query:
        return 'Error: Provide either table_name or sql_query.'
    
    try:
        conn = get_db_connection(db_type)
        cursor = conn.cursor()
        
        if sql_query:
            if not sql_query.lower().strip().startswith('select'):
                return 'Error: Only SELECT queries are permitted via this tool.'
            cursor.execute(sql_query)
        else:
            if not validate_identifier(table_name):
                return 'Error: Invalid table name. Use letters, numbers, and underscores only.'
            if limit <= 0:
                return 'Error: limit must be a positive integer.'
            if db_type == 'postgres':
                query = sql.SQL('SELECT * FROM {} LIMIT %s;').format(sql.Identifier(table_name))
                cursor.execute(query, (limit,))
            elif db_type == 'mysql':
                query = f'SELECT * FROM `{table_name}` LIMIT %s;'
                cursor.execute(query, (limit,))
            else:
                return f'Error: Unsupported database type: {db_type}'
        
        column_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        results = [dict(zip(column_names, row)) for row in rows]
        
        cursor.close()
        conn.close()
        
        return json.dumps(results, default=str)
    except Exception as e:
        return f'Database Error encountered: {str(e)}'


@mcp.tool()
def get_database_schema(db_type: str) -> str:
    '''Retrieves the table names and structures for the specified db_type ('mysql' or 'postgres').'''
    if db_type == 'postgres':
        query = '''
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public';
        '''
    else: # mysql
        query = '''
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = DATABASE();
        '''

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
        return f'Database Error encountered: {str(e)}'


if __name__ == '__main__':
    mcp.run(transport='http')
