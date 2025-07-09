import datetime as dt
import logging
import os
import warnings
from typing import List, Tuple

import numpy as np
import polars as pl
import psycopg
from config import *
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
warnings.filterwarnings("ignore")


class DSLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def info(self, message: str):
        self.logger.info(message)


def load_env_file():
    """Load environment variables from .env file in multiple possible locations."""
    env_paths = [".env", "../.env", "etl/.env", "../etl/.env", "ds/.env", "../ds/.env"]

    for path in env_paths:
        if os.path.exists(path):
            load_dotenv(path)
            return

    # If no .env file found, environment variables should be set elsewhere
    pass


def get_historical_data(
    trading_pair: str,
    start_date: str,
    end_date: str,
) -> Tuple[List[str], np.ndarray]:
    load_env_file()

    # Get the NEON_READ_ONLY connection string
    connection_string = os.getenv("NEON_READ_ONLY")
    if not connection_string:
        raise ValueError(
            "NEON_READ_ONLY environment variable not found. Please ensure it's set in your .env file."
        )

    conn = None
    cursor = None

    try:
        conn = psycopg.connect(connection_string)
        cursor = conn.cursor()

        start_timestamp = int(dt.datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_timestamp = int(dt.datetime.strptime(end_date, "%Y-%m-%d").timestamp())

        base_query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM historical.historical_coinbase_{trading_pair.replace("-", "_")} 
        """

        query = f"{base_query}WHERE timestamp >= '{start_timestamp}' AND timestamp <= '{end_timestamp}' ORDER BY timestamp ASC"
        cursor.execute(query)

        column_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        if not rows:
            return column_names, np.empty((0, len(column_names)))

        column_arrays = np.empty((len(rows), len(column_names)))
        num_columns = len(column_names)

        for col_idx in range(num_columns):
            column_arrays[:, col_idx] = np.array([row[col_idx] for row in rows])

        return column_names, np.array(column_arrays)

    except psycopg.Error as e:
        raise Exception(f"Database error: {e}")
    except Exception as e:
        raise Exception(f"Error fetching data: {e}")
    finally:
        # Clean up connections
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_historical_data_dict(trading_pair: str, start_date: str, end_date: str) -> dict:
    column_names, column_arrays = get_historical_data(
        trading_pair, start_date, end_date
    )
    # Extract each column as a separate array
    return dict(
        zip(column_names, [column_arrays[:, i] for i in range(len(column_names))])
    )


def get_table_info(trading_pair: str) -> dict:
    """
    Get information about the historical_coinbase_btc_usdc table.

    Returns:
        Dictionary with table statistics
    """
    load_env_file()

    connection_string = os.getenv("NEON_READ_ONLY")
    if not connection_string:
        raise ValueError("NEON_READ_ONLY environment variable not found.")

    conn = None
    cursor = None

    try:
        conn = psycopg.connect(connection_string)
        cursor = conn.cursor()

        # Get table info
        queries = {
            "total_rows": f"SELECT COUNT(*) FROM historical.historical_coinbase_{trading_pair.replace('-', '_')}",
            "date_range": f"""
                SELECT 
                    MIN(timestamp) as earliest_timestamp,
                    MAX(timestamp) as latest_timestamp
                FROM historical.historical_coinbase_{trading_pair.replace('-', '_')}
            """,
            "columns": f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'historical' 
                AND table_name = 'historical_coinbase_{trading_pair.replace('-', '_')}'
                ORDER BY ordinal_position
            """,
        }

        results = {}

        # Get total rows
        cursor.execute(queries["total_rows"])
        results["total_rows"] = cursor.fetchone()[0]

        # Get date range
        cursor.execute(queries["date_range"])
        date_range = cursor.fetchone()
        results["earliest_timestamp"] = date_range[0]
        results["latest_timestamp"] = date_range[1]

        # Get column info
        cursor.execute(queries["columns"])
        columns = cursor.fetchall()
        results["columns"] = [{"name": col[0], "type": col[1]} for col in columns]

        return results

    except psycopg.Error as e:
        raise Exception(f"Database error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_signals_table(
    table_name: str,
    df: pl.DataFrame,
    connection_string_env: str = "NEON_DATABASE_URL",
    if_exists: str = "replace",
) -> None:
    """
    Create a table in the signals schema with the specified table name
    and insert data from a Polars DataFrame using fast bulk insertion.

    Args:
        table_name: Name of the table to create (e.g., "coinbase_btc_usdc_config_v1")
        df: Polars DataFrame to insert into the table
        connection_string_env: Environment variable name for the database connection string
        if_exists: What to do if table exists ("replace", "append", "fail")

    Example:
        create_signals_table("coinbase_btc_usdc_config_v1", indicators_df)
        # Creates table: signals.coinbase_btc_usdc_config_v1
    """
    load_env_file()

    # Get the connection string
    connection_string = os.getenv(connection_string_env)
    if not connection_string:
        raise ValueError(
            f"{connection_string_env} environment variable not found. "
            "Please ensure it's set in your .env file."
        )

    # Format trading pair for table name
    full_table_name = f"signals.{table_name}"

    conn = None
    cursor = None

    try:
        conn = psycopg.connect(connection_string)
        cursor = conn.cursor()

        # Create schema if it doesn't exist
        cursor.execute("CREATE SCHEMA IF NOT EXISTS signals")

        # Get DataFrame schema to create table
        schema = df.schema
        columns = []

        # Map Polars data types to PostgreSQL data types
        type_mapping = {
            pl.Int8: "SMALLINT",
            pl.Int16: "SMALLINT",
            pl.Int32: "INTEGER",
            pl.Int64: "BIGINT",
            pl.UInt8: "SMALLINT",
            pl.UInt16: "INTEGER",
            pl.UInt32: "BIGINT",
            pl.UInt64: "BIGINT",
            pl.Float32: "REAL",
            pl.Float64: "DOUBLE PRECISION",
            pl.Boolean: "BOOLEAN",
            pl.Utf8: "TEXT",
            pl.String: "TEXT",
            pl.Date: "DATE",
            pl.Datetime: "TIMESTAMP",
            pl.Time: "TIME",
            pl.Duration: "INTERVAL",
        }

        for col_name, col_type in schema.items():
            pg_type = type_mapping.get(col_type, "TEXT")
            columns.append(f'"{col_name}" {pg_type}')

        # Create table
        if if_exists == "replace":
            cursor.execute(f"DROP TABLE IF EXISTS {full_table_name}")

        create_table_sql = f"""
        CREATE TABLE {full_table_name} (
            {', '.join(columns)}
        )
        """

        cursor.execute(create_table_sql)

        # Use fast bulk insertion with batched INSERT
        if len(df) > 0:
            # Get column names
            col_names = list(df.columns)

            print("COPYING DATA to db")

            # Convert DataFrame to list of tuples for batch insertion
            data_tuples = [tuple(row) for row in df.iter_rows()]

            # Use much smaller batch size to avoid SSL/connection issues
            batch_size = 100  # Process only 100 rows at a time
            placeholders = ", ".join(["%s"] * len(col_names))
            insert_sql = f"""
            INSERT INTO {full_table_name} ({', '.join(f'"{col}"' for col in col_names)})
            VALUES ({placeholders})
            """

            # Insert data in batches
            total_rows = len(data_tuples)
            print(f"Total rows: {total_rows}")

            for i in range(0, total_rows, batch_size):
                print(
                    f"Inserting batch {i//batch_size + 1} of {(total_rows + batch_size - 1)//batch_size}"
                )
                batch = data_tuples[i : i + batch_size]

                try:
                    cursor.executemany(insert_sql, batch)

                    # Progress update
                    progress = min(i + batch_size, total_rows)
                    print(
                        f"Inserted {progress}/{total_rows} rows ({(progress/total_rows)*100:.1f}%)"
                    )

                    # Commit every 10 batches to avoid long transactions
                    if (i // batch_size + 1) % 10 == 0:
                        conn.commit()
                        print(f"Committed batch {i//batch_size + 1}")

                except psycopg.OperationalError as e:
                    print(f"Connection error on batch {i//batch_size + 1}: {e}")
                    # Try to reconnect and continue
                    try:
                        conn.rollback()
                    except:
                        pass

                    # Reconnect
                    cursor.close()
                    conn.close()
                    conn = psycopg.connect(connection_string)
                    cursor = conn.cursor()
                    print("Reconnected to database")

                    # Retry this batch
                    cursor.executemany(insert_sql, batch)
                    progress = min(i + batch_size, total_rows)
                    print(f"Retry successful: Inserted {progress}/{total_rows} rows")

            # Final commit
            conn.commit()

        print(
            f"Successfully created table {full_table_name} with {len(df)} rows using batched INSERT"
        )

    except psycopg.Error as e:
        if conn:
            conn.rollback()
        raise Exception(f"Database error: {e}")
    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"Error creating table: {e}")
    finally:
        # Clean up connections
        if cursor:
            cursor.close()
        if conn:
            conn.close()
