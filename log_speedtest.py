#!/usr/bin/env python3
#
# version 1.1 - 20240124-2200                    
#
# This Python program performs a speedtest and then logs the results into a MariaDB database. 
import subprocess
import configparser
from datetime import datetime
import json
import pymysql
import sys
import os
import socket

# Configuration Variables
config = configparser.ConfigParser()
config.read('config.ini')
DB_HOST = config['database']['host']
DB_PORT = int(config['database']['port'])
DB_USER = config['database']['user']
DB_PASS = config['database']['password'] 

# Automatically obtain the server's hostname
SERVER_HOSTNAME = socket.gethostname()

# Using the hostname in the database name
DB_NAME = f'{SERVER_HOSTNAME}_speedtest'

def create_database(cursor):
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

def create_table(cursor):
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS speedtest_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        download DOUBLE,
        upload DOUBLE,
        ping DOUBLE,
        server_url VARCHAR(255),
        server_lat VARCHAR(20),
        server_lon VARCHAR(20),
        server_name VARCHAR(255),
        server_country VARCHAR(255),
        server_cc VARCHAR(10),
        server_sponsor VARCHAR(255),
        server_id VARCHAR(20),
        server_host VARCHAR(255),
        server_d DOUBLE,
        server_latency DOUBLE,
        timestamp DATETIME,
        bytes_sent BIGINT,
        bytes_received BIGINT,
        client_ip VARCHAR(20),
        client_lat VARCHAR(20),
        client_lon VARCHAR(20),
        client_isp VARCHAR(255),
        client_isprating VARCHAR(20),
        client_rating VARCHAR(20),
        client_ispdlavg VARCHAR(20),
        client_ispulavg VARCHAR(20),
        client_loggedin VARCHAR(20),
        client_country VARCHAR(20)
    )
    """
    create_archive_table_sql = """
    CREATE TABLE IF NOT EXISTS speedtest_results_archive LIKE speedtest_results;
    """
    try:
        cursor.execute(create_table_sql)

        # Create the archive table with the same structure as speedtest_results
        cursor.execute(create_archive_table_sql)
    except Exception as e:
        print(f"Error creating table: {e}")
        sys.exit(1)

def procedure_exists(cursor, proc_name):
    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.ROUTINES
        WHERE ROUTINE_SCHEMA = %s
        AND ROUTINE_TYPE = 'PROCEDURE'
        AND ROUTINE_NAME = %s
    """, (DB_NAME, proc_name))
    return cursor.fetchone()[0] > 0

def create_stored_procedures(cursor):
    # Procedure to get the size of the database
    if not procedure_exists(cursor, 'GetDatabaseSize'):
        create_proc_db_size = """
        CREATE PROCEDURE GetDatabaseSize()
        BEGIN
            SELECT table_schema "Database", SUM(data_length + index_length) / 1024 / 1024 "Size in MB"
            FROM information_schema.TABLES
            WHERE table_schema = DATABASE()
            GROUP BY table_schema;
        END
        """
        cursor.execute(create_proc_db_size)

    # Procedure to get stats from speedtest_results
    if not procedure_exists(cursor, 'GetSpeedtestStats'):
        create_proc_speedtest_stats = """
        CREATE PROCEDURE GetSpeedtestStats()
        BEGIN
            SELECT
                MIN(timestamp) AS start_date,
                MAX(timestamp) AS end_date,
                AVG(download / 1024 / 1024) AS avg_download_mbps,
                AVG(upload / 1024 / 1024) AS avg_upload_mbps
            FROM speedtest_results;
        END
        """
        cursor.execute(create_proc_speedtest_stats)

    # Procedure to archive old entries
    if not procedure_exists(cursor, 'ArchiveOldEntries'):
        create_proc_archive_old_entries = """
        CREATE PROCEDURE ArchiveOldEntries()
        BEGIN
            -- Inserts entries older than 48 hours into the archive table
            INSERT INTO speedtest_results_archive
            SELECT * FROM speedtest_results
            WHERE timestamp < NOW() - INTERVAL 48 HOUR;

            -- Deletes those entries from the original table
            DELETE FROM speedtest_results
            WHERE timestamp < NOW() - INTERVAL 48 HOUR;
        END
        """
        cursor.execute(create_proc_archive_old_entries)

def run_speedtest():
    try:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        speedtest_cli_path = os.path.join(script_dir, 'bin', 'speedtest-cli')
        output = subprocess.check_output([speedtest_cli_path, '--json'])
        return json.loads(output)
    except Exception as e:
        print(f"Error running speedtest-cli: {e}")
        return None

def insert_result(cursor, data):
    insert_sql = """
    INSERT INTO speedtest_results (
        download, upload, ping, server_url, server_lat, server_lon, server_name,
        server_country, server_cc, server_sponsor, server_id, server_host, server_d,
        server_latency, timestamp, bytes_sent, bytes_received, client_ip, client_lat,
        client_lon, client_isp, client_isprating, client_rating, client_ispdlavg,
        client_ispulavg, client_loggedin, client_country
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s
    )
    """
    # Convert ISO 8601 timestamp to MariaDB DATETIME format
    timestamp = datetime.fromisoformat(data['timestamp'].rstrip('Z')).strftime('%Y-%m-%d %H:%M:%S')

    try:
        cursor.execute(insert_sql, (
            data['download'], data['upload'], data['ping'],
            data['server']['url'], data['server']['lat'], data['server']['lon'],
            data['server']['name'], data['server']['country'], data['server']['cc'],
            data['server']['sponsor'], data['server']['id'], data['server']['host'],
            data['server']['d'], data['server']['latency'], timestamp, # Updated timestamp
            data['bytes_sent'], data['bytes_received'], data['client']['ip'],
            data['client']['lat'], data['client']['lon'], data['client']['isp'],
            data['client']['isprating'], data['client']['rating'], data['client']['ispdlavg'],
            data['client']['ispulavg'], data['client']['loggedin'], data['client']['country']
        ))
    except Exception as e:
        print(f"Error inserting data into database: {e}")

def main():
    conn = None
    try:
        # Connect to MariaDB
        conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, passwd=DB_PASS)
        cursor = conn.cursor()

        # Create database and table
        create_database(cursor)
        conn.select_db(DB_NAME)
        create_table(cursor)

        # create stored procedures
        create_stored_procedures(cursor)
        # Run Speedtest and get results
        data = run_speedtest()
        if data:
            insert_result(cursor, data)
            conn.commit()
            print("Speedtest data inserted successfully.")
        else:
            print("No data to insert.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    main()
