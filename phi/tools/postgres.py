from typing import Optional, Dict, Any, List, Union

try:
    import psycopg2
except ImportError:
    raise ImportError(
        "`psycopg2` not installed. Please install using `pip install psycopg2`. "
        "If you face issues, try `pip install psycopg2-binary`."
    )

from phi.tools import Toolkit
from phi.utils.log import logger


class PostgresTools(Toolkit):
    """
    A tool to connect to a PostgreSQL database and perform both read and write operations.
    """

    def __init__(
        self,
        connection: Optional[psycopg2.extensions.connection] = None,
        db_name: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        run_queries: bool = True,
        inspect_queries: bool = False,
        summarize_tables: bool = True,
        export_tables: bool = False,
        table_schema: str = "public",
        # New:
        read_only: bool = False,
    ):
        super().__init__(name="postgres_tools")

        self._connection: Optional[psycopg2.extensions.connection] = connection
        self.db_name: Optional[str] = db_name
        self.user: Optional[str] = user
        self.password: Optional[str] = password
        self.host: Optional[str] = host
        self.port: Optional[int] = port

        self.table_schema: str = table_schema
        self.read_only: bool = read_only

        # Register existing commands
        self.register(self.show_tables)
        self.register(self.describe_table)
        if inspect_queries:
            self.register(self.inspect_query)
        if run_queries:
            self.register(self.run_query)
        if summarize_tables:
            self.register(self.summarize_table)
        if export_tables:
            self.register(self.export_table_to_path)

        # Register new write commands
        # Only register them if we are not strictly read-only
        if not self.read_only:
            self.register(self.insert_records)
            self.register(self.update_records)
            self.register(self.delete_records)

    @property
    def connection(self) -> psycopg2.extensions.connection:
        """
        Returns the Postgres psycopg2 connection, creating one if needed.
        """
        if self._connection is None:
            connection_kwargs: Dict[str, Any] = {}
            if self.db_name is not None:
                connection_kwargs["database"] = self.db_name
            if self.user is not None:
                connection_kwargs["user"] = self.user
            if self.password is not None:
                connection_kwargs["password"] = self.password
            if self.host is not None:
                connection_kwargs["host"] = self.host
            if self.port is not None:
                connection_kwargs["port"] = self.port

            # Make sure the default schema is set
            if self.table_schema is not None:
                connection_kwargs["options"] = f"-c search_path={self.table_schema}"

            self._connection = psycopg2.connect(**connection_kwargs)

            # Set the session read-only if requested
            # (Trying INSERT/UPDATE/DELETE on a read-only session will fail)
            self._connection.set_session(readonly=self.read_only)

        return self._connection

    def show_tables(self) -> str:
        """
        Show tables in the specified schema.
        """
        stmt = f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{self.table_schema}';
        """
        tables = self.run_query(stmt)
        logger.debug(f"Tables: {tables}")
        return tables

    def describe_table(self, table: str) -> str:
        """
        Describe a table's columns and their data types.
        """
        stmt = f"""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = '{table}' 
              AND table_schema = '{self.table_schema}';
        """
        table_description = self.run_query(stmt)
        logger.debug(f"Table description: {table_description}")
        return f"{table}\n{table_description}"

    def summarize_table(self, table: str) -> str:
        """
        Compute basic aggregates (min, max, avg, std) for numeric columns in the table.
        """
        stmt = f"""
            WITH column_stats AS (
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table}'
                  AND table_schema = '{self.table_schema}'
            )
            SELECT
                column_name,
                data_type,
                COUNT(COALESCE(column_name::text, '')) AS non_null_count,
                COUNT(*) - COUNT(COALESCE(column_name::text, '')) AS null_count,
                SUM(COALESCE(column_name::numeric, 0)) AS sum,
                AVG(COALESCE(column_name::numeric, 0)) AS mean,
                MIN(column_name::numeric) AS min,
                MAX(column_name::numeric) AS max,
                STDDEV(COALESCE(column_name::numeric, 0)) AS stddev
            FROM column_stats,
                 LATERAL (SELECT * FROM {table}) AS tbl
            WHERE data_type IN ('integer', 'numeric', 'real', 'double precision')
            GROUP BY column_name, data_type

            UNION ALL

            SELECT
                column_name,
                data_type,
                COUNT(COALESCE(column_name::text, '')) AS non_null_count,
                COUNT(*) - COUNT(COALESCE(column_name::text, '')) AS null_count,
                NULL AS sum,
                NULL AS mean,
                NULL AS min,
                NULL AS max,
                NULL AS stddev
            FROM column_stats,
                 LATERAL (SELECT * FROM {table}) AS tbl
            WHERE data_type NOT IN ('integer', 'numeric', 'real', 'double precision')
            GROUP BY column_name, data_type;
        """
        table_summary = self.run_query(stmt)
        logger.debug(f"Table summary: {table_summary}")
        return table_summary

    def inspect_query(self, query: str) -> str:
        """
        Return the query plan for the given SQL query (via EXPLAIN).
        """
        stmt = f"EXPLAIN {query};"
        plan = self.run_query(stmt)
        logger.debug(f"Query plan: {plan}")
        return plan

    def export_table_to_path(self, table: str, path: Optional[str] = None) -> str:
        """
        Export a table to a CSV file. If no path is given, the file name defaults to `table.csv` in the current directory.
        """
        if path is None:
            path = f"{table}.csv"
        else:
            path = f"{path}/{table}.csv"

        logger.debug(f"Exporting Table {table} as CSV to path {path}")
        export_statement = f"COPY {self.table_schema}.{table} TO '{path}' DELIMITER ',' CSV HEADER;"
        result = self.run_query(export_statement)
        logger.debug(f"Exported {table} to {path}")
        return result

    def run_query(self, query: str) -> str:
        """
        Execute any SQL query (read or write) and return the result as a string.
        """
        # Clean up the query a bit
        formatted_sql = query.replace("`", "")
        formatted_sql = formatted_sql.split(";")[0]

        try:
            logger.info(f"Running: {formatted_sql}")
            cursor = self.connection.cursor()

            cursor.execute(formatted_sql)
            # If it's a SELECT-like query, fetch results
            if cursor.description is not None:
                rows = cursor.fetchall()
                # Build a header from cursor.description if we want
                headers = [desc[0] for desc in cursor.description]
                result_output = ",".join(headers) + "\n"
                for row in rows:
                    row_str = ",".join(str(x) for x in row)
                    result_output += row_str + "\n"
            else:
                # For DML (INSERT/UPDATE/DELETE) queries, we might want to commit if not in read-only mode
                if not self.read_only:
                    self.connection.commit()
                result_output = "Query executed successfully (no output)."

            cursor.close()
            logger.debug(f"Query result: {result_output.strip()}")
            return result_output.strip()

        except Exception as e:
            logger.error(f"Error running query: {e}")
            # Optionally rollback on error
            if not self.read_only:
                self.connection.rollback()
            return str(e)

    # ------------------------------------------------------------------------
    # Write operations (only registered if read_only=False)
    # ------------------------------------------------------------------------

    def insert_records(
        self,
        table: str,
        rows: List[Dict[str, Any]]
    ) -> str:
        """
        Insert multiple records into the specified table.

        :param table: Name of the table
        :param rows: A list of dictionaries, each representing one record (column -> value)
        :return: A success message or error string
        """
        if not rows:
            return "No rows to insert."

        # Build a list of columns from the first row
        columns = list(rows[0].keys())
        col_str = ", ".join(columns)
        # Build a list of placeholders
        placeholders = ", ".join(["%s"] * len(columns))

        # Convert each dict to a tuple in the correct order
        values = []
        for row in rows:
            values.append(tuple(row[col] for col in columns))

        query = f"INSERT INTO {self.table_schema}.{table} ({col_str}) VALUES ({placeholders})"
        logger.debug(f"Inserting into {table}. Columns: {col_str}, #rows={len(values)}")

        try:
            cursor = self.connection.cursor()
            cursor.executemany(query, values)

            if not self.read_only:
                self.connection.commit()

            cursor.close()
            return f"Inserted {len(rows)} record(s) into {table}."
        except Exception as e:
            logger.error(f"Error inserting records into {table}: {e}")
            if not self.read_only:
                self.connection.rollback()
            return str(e)

    def update_records(
        self,
        table: str,
        set_values: Dict[str, Any],
        condition: Optional[str] = None
    ) -> str:
        """
        Update records in the specified table using a condition.

        :param table: Name of the table
        :param set_values: Dictionary of column -> new value
        :param condition: Optional SQL condition (e.g., "id = 1")
        :return: A success message or error string
        """
        if not set_values:
            return "No values to update."

        set_clause = ", ".join([f"{col} = %s" for col in set_values.keys()])
        query = f"UPDATE {self.table_schema}.{table} SET {set_clause}"
        if condition:
            query += f" WHERE {condition}"

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, tuple(set_values.values()))

            if not self.read_only:
                self.connection.commit()

            rowcount = cursor.rowcount
            cursor.close()
            return f"Updated {rowcount} record(s) in {table}."
        except Exception as e:
            logger.error(f"Error updating records in {table}: {e}")
            if not self.read_only:
                self.connection.rollback()
            return str(e)

    def delete_records(
        self,
        table: str,
        condition: Optional[str] = None
    ) -> str:
        """
        Delete records from the specified table using a condition.

        :param table: Name of the table
        :param condition: Optional SQL condition (e.g. "id = 1").
                          If no condition is given, all rows will be deleted.
        :return: A success message or error string
        """
        query = f"DELETE FROM {self.table_schema}.{table}"
        if condition:
            query += f" WHERE {condition}"

        try:
            cursor = self.connection.cursor()
            cursor.execute(query)

            if not self.read_only:
                self.connection.commit()

            rowcount = cursor.rowcount
            cursor.close()
            return f"Deleted {rowcount} record(s) from {table}."
        except Exception as e:
            logger.error(f"Error deleting records from {table}: {e}")
            if not self.read_only:
                self.connection.rollback()
            return str(e)
