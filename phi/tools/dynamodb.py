import json
from typing import Optional

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    import boto3
    from boto3.dynamodb.conditions import Attr
except ImportError:
    raise ImportError("`boto3` not installed. Please install with `pip install boto3`.")


class DynamoDBTools(Toolkit):
    def __init__(
        self,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        # Basic operations
        list_tables: bool = True,
        describe_table: bool = True,
        run_query: bool = True,
        # Additional operations
        count_items_func: bool = True,
        list_indexes_func: bool = True,
        create_items_func: bool = True,
        update_items_func: bool = True,
        delete_items_func: bool = True,
        # Optionally enforce read-only mode
        read_only: bool = False,
    ):
        """
        A toolkit for interacting with DynamoDB.

        Args:
            region_name (str, optional): AWS region name.
            aws_access_key_id (str, optional): AWS access key id.
            aws_secret_access_key (str, optional): AWS secret access key.
            endpoint_url (str, optional): DynamoDB endpoint URL (useful for local testing).
            list_tables (bool, optional): Register the `list_tables` function.
            describe_table (bool, optional): Register the `describe_table` function.
            run_query (bool, optional): Register the `run_query` function.
            count_items_func (bool, optional): Register the `count_items` function.
            list_indexes_func (bool, optional): Register the `list_indexes` function.
            create_items_func (bool, optional): Register the `create_items` function.
            update_items_func (bool, optional): Register the `update_items` function.
            delete_items_func (bool, optional): Register the `delete_items` function.
            read_only (bool, optional): If True, write operations (create, update, delete) will be blocked.
        """
        super().__init__(name="dynamodb_tools")
        self.read_only = read_only

        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url
        )

        # Register operations in the toolkit
        if list_tables:
            self.register(self.list_tables)
        if describe_table:
            self.register(self.describe_table)
        if run_query:
            self.register(self.run_query)
        if count_items_func:
            self.register(self.count_items)
        if list_indexes_func:
            self.register(self.list_indexes)
        # Write operations are registered only if read_only is False.
        if create_items_func and not self.read_only:
            self.register(self.create_items)
        if update_items_func and not self.read_only:
            self.register(self.update_items)
        if delete_items_func and not self.read_only:
            self.register(self.delete_items)

    def list_tables(self) -> str:
        """
        List all DynamoDB tables in the current region.

        Returns:
            str: A JSON list of table names or an error message.
        """
        try:
            client = self.dynamodb.meta.client
            response = client.list_tables()
            tables = response.get('TableNames', [])
            logger.debug(f"Tables: {tables}")
            return json.dumps(tables)
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return f"Error listing tables: {e}"

    def describe_table(self, table_name: str) -> str:
        """
        Describe a DynamoDB table.

        Args:
            table_name (str): The table to describe.

        Returns:
            str: JSON string of the table description or an error message.
        """
        try:
            client = self.dynamodb.meta.client
            response = client.describe_table(TableName=table_name)
            table_description = response.get('Table', {})
            return json.dumps(table_description, default=str)
        except Exception as e:
            logger.error(f"Error describing table '{table_name}': {e}")
            return f"Error describing table '{table_name}': {e}"

    def run_query(
        self,
        table_name: str,
        query: Optional[str] = "{}",
        projection: Optional[str] = None,
        limit: Optional[int] = 10
    ) -> str:
        """
        Run a scan query on a DynamoDB table with optional filtering and projection.

        Args:
            table_name (str): The table name.
            query (str, optional): JSON string representing filter criteria, e.g. '{"status": "active"}'. Defaults to "{}".
            projection (str, optional): JSON array of attribute names to retrieve, e.g. '["id", "name"]'.
            limit (int, optional): Maximum number of items to return. Defaults to 10.

        Returns:
            str: A JSON list of items matching the query or an error message.
        """
        try:
            table = self.dynamodb.Table(table_name)
            filter_dict = json.loads(query) if query else {}
            filter_expression = None
            for key, value in filter_dict.items():
                condition = Attr(key).eq(value)
                filter_expression = condition if filter_expression is None else filter_expression & condition

            projection_expression = None
            if projection:
                proj = json.loads(projection)
                if isinstance(proj, list):
                    projection_expression = ", ".join(proj)
                else:
                    projection_expression = str(proj)

            scan_kwargs = {}
            if filter_expression is not None:
                scan_kwargs['FilterExpression'] = filter_expression
            if projection_expression is not None:
                scan_kwargs['ProjectionExpression'] = projection_expression
            if limit:
                scan_kwargs['Limit'] = limit

            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            return json.dumps(items, default=str)
        except Exception as e:
            logger.error(f"Error running query on table '{table_name}': {e}")
            return f"Error running query on table '{table_name}': {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for query/projection: {e}")
            return f"Invalid JSON: {e}"

    def run_aggregation(
        self,
        table_name: str,
        pipeline: str,
        limit: Optional[int] = None
    ) -> str:
        """
        DynamoDB does not support aggregation pipelines like MongoDB.

        Args:
            table_name (str): The table name.
            pipeline (str): Ignored.
            limit (int, optional): Ignored.

        Returns:
            str: An error message indicating that aggregation is not supported.
        """
        return "Aggregation operation is not supported in DynamoDB."

    def count_items(
        self,
        table_name: str,
        query: Optional[str] = "{}"
    ) -> str:
        """
        Count items in a DynamoDB table based on a filter.

        Args:
            table_name (str): The table name.
            query (str, optional): JSON string representing filter criteria. Defaults to "{}".

        Returns:
            str: The count of matching items as a string, or an error message.
        """
        try:
            table = self.dynamodb.Table(table_name)
            filter_dict = json.loads(query) if query else {}
            filter_expression = None
            for key, value in filter_dict.items():
                condition = Attr(key).eq(value)
                filter_expression = condition if filter_expression is None else filter_expression & condition

            scan_kwargs = {'Select': 'COUNT'}
            if filter_expression is not None:
                scan_kwargs['FilterExpression'] = filter_expression

            response = table.scan(**scan_kwargs)
            count = response.get('Count', 0)
            return str(count)
        except Exception as e:
            logger.error(f"Error counting items in table '{table_name}': {e}")
            return f"Error counting items in table '{table_name}': {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for query: {e}")
            return f"Invalid JSON: {e}"

    def list_indexes(self, table_name: str) -> str:
        """
        List indexes (Global and Local Secondary Indexes) of a DynamoDB table.

        Args:
            table_name (str): The table name.

        Returns:
            str: JSON list of indexes or an error message.
        """
        try:
            client = self.dynamodb.meta.client
            response = client.describe_table(TableName=table_name)
            table_info = response.get('Table', {})
            indexes = {}
            if 'GlobalSecondaryIndexes' in table_info:
                indexes['GlobalSecondaryIndexes'] = table_info['GlobalSecondaryIndexes']
            if 'LocalSecondaryIndexes' in table_info:
                indexes['LocalSecondaryIndexes'] = table_info['LocalSecondaryIndexes']
            return json.dumps(indexes, default=str)
        except Exception as e:
            logger.error(f"Error listing indexes for table '{table_name}': {e}")
            return f"Error listing indexes for table '{table_name}': {e}"

    def create_items(self, table_name: str, items: str) -> str:
        """
        Insert one or multiple items into a DynamoDB table.

        Args:
            table_name (str): The table name.
            items (str): A JSON string representing the item(s). 
                         - Single item: '{"id": "1", "name": "Alice"}'
                         - Multiple items: '[{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]'

        Returns:
            str: JSON-encoded status message or an error message.
        """
        if self.read_only:
            return "Write operation blocked: the toolkit is in read-only mode."

        try:
            table = self.dynamodb.Table(table_name)
            data = json.loads(items)
            if isinstance(data, dict):
                table.put_item(Item=data)
                return json.dumps({"status": "Item inserted"})
            elif isinstance(data, list):
                with table.batch_writer() as batch:
                    for item in data:
                        batch.put_item(Item=item)
                return json.dumps({"status": f"{len(data)} items inserted"})
            else:
                return "Error: Items must be a JSON object or a list of objects."
        except Exception as e:
            logger.error(f"Error inserting items into table '{table_name}': {e}")
            return f"Error inserting items: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for items: {e}")
            return f"Invalid JSON for items: {e}"

    def update_items(
        self,
        table_name: str,
        query: str,
        update: str,
        multi: bool = True
    ) -> str:
        """
        Update items in a DynamoDB table based on a filter.

        Note: DynamoDB does not support multi-item updates in a single API call.
        This function scans for items matching the query and updates them individually.

        Args:
            table_name (str): The table name.
            query (str): JSON string representing filter criteria.
            update (str): JSON string representing attributes to update, e.g. '{"status": "inactive"}'
            multi (bool): Whether to update multiple items or just one.

        Returns:
            str: JSON-encoded dict with the count of updated items or an error message.
        """
        if self.read_only:
            return "Write operation blocked: the toolkit is in read-only mode."

        try:
            table = self.dynamodb.Table(table_name)
            filter_dict = json.loads(query)
            update_data = json.loads(update)

            # Build update expression (assumes simple SET operations)
            update_expr = "SET " + ", ".join([f"#{k} = :{k}" for k in update_data.keys()])
            expression_attribute_values = {f":{k}": v for k, v in update_data.items()}
            expression_attribute_names = {f"#{k}": k for k in update_data.keys()}

            # Build filter expression
            filter_expression = None
            for key, value in filter_dict.items():
                condition = Attr(key).eq(value)
                filter_expression = condition if filter_expression is None else filter_expression & condition

            scan_kwargs = {}
            if filter_expression is not None:
                scan_kwargs['FilterExpression'] = filter_expression

            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            updated_count = 0

            # Retrieve key schema to determine primary key attributes
            client = self.dynamodb.meta.client
            desc = client.describe_table(TableName=table_name)
            key_schema = desc['Table']['KeySchema']

            for item in items:
                key = {}
                for key_def in key_schema:
                    attr = key_def['AttributeName']
                    if attr in item:
                        key[attr] = item[attr]
                if not key:
                    return "Error: Unable to determine key for item update."
                table.update_item(
                    Key=key,
                    UpdateExpression=update_expr,
                    ExpressionAttributeValues=expression_attribute_values,
                    ExpressionAttributeNames=expression_attribute_names
                )
                updated_count += 1
                if not multi:
                    break
            return json.dumps({"updated_count": updated_count})
        except Exception as e:
            logger.error(f"Error updating items in table '{table_name}': {e}")
            return f"Error updating items: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for query/update: {e}")
            return f"Invalid JSON: {e}"

    def delete_items(
        self,
        table_name: str,
        query: str,
        multi: bool = True
    ) -> str:
        """
        Delete items from a DynamoDB table based on a filter.

        Note: DynamoDB does not support multi-item deletion in a single API call.
        This function scans for items matching the query and deletes them individually.

        Args:
            table_name (str): The table name.
            query (str): JSON string representing filter criteria.
            multi (bool): Whether to delete multiple items or just one.

        Returns:
            str: JSON-encoded dict with the count of deleted items or an error message.
        """
        if self.read_only:
            return "Write operation blocked: the toolkit is in read-only mode."

        try:
            table = self.dynamodb.Table(table_name)
            filter_dict = json.loads(query)
            filter_expression = None
            for key, value in filter_dict.items():
                condition = Attr(key).eq(value)
                filter_expression = condition if filter_expression is None else filter_expression & condition

            scan_kwargs = {}
            if filter_expression is not None:
                scan_kwargs['FilterExpression'] = filter_expression

            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            deleted_count = 0

            # Retrieve key schema to determine primary key attributes
            client = self.dynamodb.meta.client
            desc = client.describe_table(TableName=table_name)
            key_schema = desc['Table']['KeySchema']

            for item in items:
                key = {}
                for key_def in key_schema:
                    attr = key_def['AttributeName']
                    if attr in item:
                        key[attr] = item[attr]
                if not key:
                    return "Error: Unable to determine key for item deletion."
                table.delete_item(Key=key)
                deleted_count += 1
                if not multi:
                    break
            return json.dumps({"deleted_count": deleted_count})
        except Exception as e:
            logger.error(f"Error deleting items from table '{table_name}': {e}")
            return f"Error deleting items: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for query: {e}")
            return f"Invalid JSON: {e}"