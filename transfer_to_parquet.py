import pymysql
import pandas as pd
import boto3
import os
import pyarrow.parquet as pq

# MySQL Configuration
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "lajolla4203"
MYSQL_DB = "academy"

# AWS S3 Configuration
S3_BUCKET = "pesu-spirit"
S3_PREFIX = "raw/"  # Folder structure in S3

# List of tables to extract
TABLES = ["Mentoring", "MentorMentee", "StudentCGPA", "UserInfo", "Users"]

# Connect to MySQL
conn = pymysql.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DB
)

# Initialize S3 Client
s3_client = boto3.client('s3')

def export_table_to_parquet(table_name):
    """Extract MySQL table data and store it as a Parquet file"""
    query = f"SELECT * FROM {table_name};"
    
    try:
        # Read data into a Pandas DataFrame
        df = pd.read_sql(query, conn)

        # Define local and S3 paths
        local_file = f"/tmp/{table_name}.parquet"
        s3_file_path = f"{S3_PREFIX}{table_name}/{table_name}.parquet"

        # Convert DataFrame to Parquet
        df.to_parquet(local_file, engine="pyarrow", index=False)

        # Upload to S3
        s3_client.upload_file(local_file, S3_BUCKET, s3_file_path)
        
        print(f"Uploaded {table_name}.parquet to s3://{S3_BUCKET}/{s3_file_path}")

    except Exception as e:
        print(f"Error exporting {table_name}: {e}")

# Export each table
for table in TABLES:
    export_table_to_parquet(table)

# Close MySQL Connection
conn.close()