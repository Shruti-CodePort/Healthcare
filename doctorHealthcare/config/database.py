import mysql.connector
from mysql.connector import pooling

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Devansh@0127",
    "database": "healthcare",
    "auth_plugin": "mysql_native_password",
    "pool_name": "mypool",
    "pool_size": 5
}

connection_pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)

def get_db_connection():
    return connection_pool.get_connection()