#!/usr/bin/env python3
#
# Created by RejectH0 - 20 JAN 2024 - 2300 MST
#
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
        # Create the database if it does not exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.execute(f"USE {DB_NAME}")

        # Procedure to get the size of the database
        create_proc_db_size = """
        CREATE PROCEDURE IF NOT EXISTS GetDatabaseSize()
        BEGIN
            SELECT table_schema "Database", SUM(data_length + index_length) / 1024 / 1024 "Size in MB" 
            FROM information_schema.TABLES 
            WHERE table_schema = DATABASE()
            GROUP BY table_schema;
        END
        """
        cursor.execute(create_proc_db_size)

        # Procedure to get stats from speedtest_results
        create_proc_speedtest_stats = """
        CREATE PROCEDURE IF NOT EXISTS GetSpeedtestStats()
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

    except Exception as e:
        print(f"Error creating database or stored procedures: {e}")
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
    try:
        cursor.execute(create_table_sql)
    except Exception as e:
        print(f"Error creating table: {e}")
        sys.exit(1)

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
