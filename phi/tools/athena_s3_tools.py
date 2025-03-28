import json
import boto3
from typing import Optional
from phi.tools import Toolkit
from phi.utils.log import logger

class AthenaS3Tools(Toolkit):
    def __init__(
        self,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        region_name: Optional[str] = None,
        database: Optional[str] = None,
        s3_output_location: Optional[str] = None,
        
        run_athena_query: bool = True,
        get_query_results: bool = True,
        list_tables: bool = True,
    ):
        """
        A toolkit for fetching data from AWS S3 using Athena.

        Args:
            aws_access_key (str, optional): AWS access key ID.
            aws_secret_key (str, optional): AWS secret access key.
            region_name (str, optional): AWS region name.
            database (str, optional): The Athena database name.
            s3_output_location (str, optional): The S3 location for query results.
        """
        super().__init__(name="athena_s3_tools")

        if not aws_access_key or not aws_secret_key or not database or not s3_output_location:
            raise ValueError("AWS credentials, database, and S3 output location are required.")

        self.client = boto3.client(
            "athena",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region_name
        )

        self.database = database
        self.s3_output_location = s3_output_location

        if run_athena_query:
            self.register(self.run_athena_query)
        if get_query_results:
            self.register(self.get_query_results)
        if list_tables:
            self.register(self.list_tables)
            
    def run_athena_query(self, query: str) -> str:
        """
        Run an Athena query and return the query execution ID.

        Args:
            query (str): The SQL query to execute.

        Returns:
            str: Query execution ID or an error message.
        """
        try:
            response = self.client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": self.database},
                ResultConfiguration={"OutputLocation": self.s3_output_location}
            )
            execution_id = response["QueryExecutionId"]
            logger.info(f"Athena query started: {execution_id}")
            return json.dumps({"execution_id": execution_id})
        except Exception as e:
            logger.error(f"Error running Athena query: {e}")
            return f"Error running query: {e}"

    def get_query_results(self, execution_id: str) -> str:
        """
        Fetch query results using execution ID.

        Args:
            execution_id (str): The execution ID of the Athena query.

        Returns:
            str: JSON list of query results or an error message.
        """
        try:
            response = self.client.get_query_execution(QueryExecutionId=execution_id)
            state = response["QueryExecution"]["Status"]["State"]

            if state == "FAILED":
                reason = response["QueryExecution"]["Status"].get("StateChangeReason", "Unknown Error")
                logger.error(f"Query failed: {reason}")
                return f"Query failed: {reason}"
            elif state != "SUCCEEDED":
                return "Query still running. Try again later."

            result_response = self.client.get_query_results(QueryExecutionId=execution_id)
            rows = result_response.get("ResultSet", {}).get("Rows", [])

            result_data = []
            headers = [col.get("VarCharValue", "") for col in rows[0]["Data"]]
            for row in rows[1:]:
                result_data.append({headers[i]: col.get("VarCharValue", "") for i, col in enumerate(row["Data"])})

            return json.dumps(result_data)
        except Exception as e:
            logger.error(f"Error fetching Athena query results: {e}")
            return f"Error fetching query results: {e}"

    def list_tables(self) -> str:
        """
        List all tables in the current Athena database.

        Returns:
            str: JSON list of table names or an error message.
        """
        try:
            query = "SHOW TABLES"
            execution_response = self.run_athena_query(query)
            execution_id = json.loads(execution_response).get("execution_id")

            if not execution_id:
                return "Failed to start Athena query for listing tables."

            return self.get_query_results(execution_id)
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return f"Error listing tables: {e}"
