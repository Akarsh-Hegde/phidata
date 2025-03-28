import json
from typing import List, Optional, Dict, Any, Union

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.errors import PyMongoError
except ImportError:
    raise ImportError("`pymongo` not installed. Please install with `pip install pymongo`.")


class MongoDBTools(Toolkit):
    def __init__(
        self,
        db_url: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        # Basic operations
        list_collections: bool = True,
        describe_collection: bool = True,
        run_mongo_query: bool = True,
        # Additional operations
        aggregate_pipeline: bool = True,
        count_documents_func: bool = True,
        list_indexes_func: bool = True,
        create_documents_func: bool = True,
        update_documents_func: bool = True,
        delete_documents_func: bool = True,
        # New: optionally enforce read-only mode
        read_only: bool = False,
    ):
        """
        A toolkit for interacting with MongoDB databases.

        Args:
            db_url (str, optional): Full MongoDB URI, e.g. "mongodb://user:pass@host:port/dbname".
                                    If provided, user/password/host/port can be omitted.
            user (str, optional): The username for the DB if not using db_url.
            password (str, optional): The password for the DB if not using db_url.
            host (str, optional): The hostname for the DB if not using db_url.
            port (int, optional): The port for the DB if not using db_url.
            database (str, optional): The name of the database to use.

            list_collections (bool, optional): Register the `list_collections` function.
            describe_collection (bool, optional): Register the `describe_collection` function.
            run_mongo_query (bool, optional): Register the `run_mongo_query` function.
            aggregate_pipeline (bool, optional): Register the `run_aggregation` function.
            count_documents_func (bool, optional): Register the `count_documents` function.
            list_indexes_func (bool, optional): Register the `list_indexes` function.
            create_documents_func (bool, optional): Register the `create_documents` function.
            update_documents_func (bool, optional): Register the `update_documents` function.
            delete_documents_func (bool, optional): Register the `delete_documents` function.

            read_only (bool, optional): If True, attempts to create, update or delete will fail.
        """
        super().__init__(name="mongodb_tools")

        self.read_only = read_only

        # Build Mongo client
        if db_url:
            self.client = MongoClient(db_url)
        else:
            # Construct a MongoDB URI from host/port/user/password if no db_url given
            if host and port:
                if user and password:
                    db_url = f"mongodb://{user}:{password}@{host}:{port}"
                else:
                    db_url = f"mongodb://{host}:{port}"
                self.client = MongoClient(db_url)
            else:
                raise ValueError("Insufficient connection parameters to build a MongoDB URI.")

        if not database:
            raise ValueError("A database name must be provided.")

        # Get the specific database
        self.db = self.client[database]

        # Register operations in the toolkit
        if list_collections:
            self.register(self.list_collections)

        if describe_collection:
            self.register(self.describe_collection)

        if run_mongo_query:
            self.register(self.run_mongo_query)

        if aggregate_pipeline:
            self.register(self.run_aggregation)

        if count_documents_func:
            self.register(self.count_documents)

        if list_indexes_func:
            self.register(self.list_indexes)

        # Register "write" operations only if read_only=False
        if create_documents_func and not self.read_only:
            self.register(self.create_documents)
        if update_documents_func and not self.read_only:
            self.register(self.update_documents)
        if delete_documents_func and not self.read_only:
            self.register(self.delete_documents)

    def list_collections(self) -> str:
        """
        List all collections in the current database.

        Returns:
            str: A JSON list of all collection names or an error message.
        """
        try:
            collections = self.db.list_collection_names()
            logger.debug(f"Collections: {collections}")
            return json.dumps(collections)
        except PyMongoError as e:
            logger.error(f"Error listing collections: {e}")
            return f"Error listing collections: {e}"

    def describe_collection(self, collection_name: str) -> str:
        """
        Describe a collection in a basic way by returning one sample document.

        Args:
            collection_name (str): The collection to describe.

        Returns:
            str: JSON string of the sample document or a message if no documents exist.
        """
        try:
            collection: Collection = self.db[collection_name]
            sample_doc = collection.find_one()
            if sample_doc is None:
                return f"No documents found in collection '{collection_name}'."
            return json.dumps(sample_doc, default=str)
        except PyMongoError as e:
            logger.error(f"Error describing collection '{collection_name}': {e}")
            return f"Error describing collection '{collection_name}': {e}"

    def run_mongo_query(
        self,
        collection_name: str,
        query: Optional[str] = "{}",
        projection: Optional[str] = None,
        limit: Optional[int] = 10
    ) -> str:
        """
        Run a MongoDB find query against a collection.

        Args:
            collection_name (str): The name of the collection to query.
            query (str, optional): The query in JSON format. Defaults to "{}" (match all).
            projection (str, optional): JSON specifying which fields to include/exclude. Default is None.
            limit (int, optional): Max number of documents to return. Default is 10.

        Returns:
            str: A JSON list of query results or an error message.
        """
        try:
            collection: Collection = self.db[collection_name]
            query_dict = json.loads(query) if query else {}
            projection_dict = json.loads(projection) if projection else {}

            cursor = collection.find(query_dict, projection_dict)
            if limit is not None:
                cursor = cursor.limit(limit)

            results = list(cursor)
            return json.dumps(results, default=str)
        except PyMongoError as e:
            logger.error(f"Error running query on '{collection_name}': {e}")
            return f"Error running query on '{collection_name}': {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for query/projection: {e}")
            return f"Invalid JSON: {e}"

    def run_aggregation(
        self,
        collection_name: str,
        pipeline: str,
        limit: Optional[int] = None
    ) -> str:
        """
        Run an aggregation pipeline on a MongoDB collection.

        Args:
            collection_name (str): The collection name.
            pipeline (str): JSON-encoded list of pipeline stages.
            limit (int, optional): Optional limit on the result set.

        Returns:
            str: A JSON list of aggregation results or an error message.
        """
        try:
            collection: Collection = self.db[collection_name]
            pipeline_obj = json.loads(pipeline) if pipeline else []

            cursor = collection.aggregate(pipeline_obj)
            if limit is not None:
                results = list(cursor)[:limit]
            else:
                results = list(cursor)
            return json.dumps(results, default=str)
        except PyMongoError as e:
            logger.error(f"Error running aggregation on '{collection_name}': {e}")
            return f"Error running aggregation: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for pipeline: {e}")
            return f"Invalid JSON: {e}"

    def count_documents(
        self,
        collection_name: str,
        query: Optional[str] = "{}"
    ) -> str:
        """
        Count documents in a collection based on a query.

        Args:
            collection_name (str): The collection name.
            query (str, optional): The filter query in JSON format. Defaults to '{}' (match all).

        Returns:
            str: The count of matching documents as a string, or an error message.
        """
        try:
            collection: Collection = self.db[collection_name]
            query_dict = json.loads(query) if query else {}
            count_value = collection.count_documents(query_dict)
            return str(count_value)
        except PyMongoError as e:
            logger.error(f"Error counting documents in '{collection_name}': {e}")
            return f"Error counting documents: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for query: {e}")
            return f"Invalid JSON: {e}"

    def list_indexes(self, collection_name: str) -> str:
        """
        List all indexes in a collection.

        Args:
            collection_name (str): The collection name.

        Returns:
            str: JSON list of index info or an error message.
        """
        try:
            collection: Collection = self.db[collection_name]
            indexes = list(collection.list_indexes())
            return json.dumps(indexes, default=str)
        except PyMongoError as e:
            logger.error(f"Error listing indexes in '{collection_name}': {e}")
            return f"Error listing indexes: {e}"

    # ------------------------------------------------------------------------
    # Below are WRITE OPERATIONS (skipped if read_only=True)
    # ------------------------------------------------------------------------

    def create_documents(self, collection_name: str, documents: str) -> str:
        """
        Insert one or multiple documents into a collection.

        Args:
            collection_name (str): The collection name.
            documents (str): A JSON string representing the document(s). 
                             - Single doc: '{"name": "Alice"}'
                             - Multiple: '[{"name": "Alice"}, {"name": "Bob"}]'
        Returns:
            str: JSON-encoded dict with inserted_id(s) or an error message.
        """
        if self.read_only:
            return "Write operation blocked: the toolkit is in read-only mode."

        try:
            collection: Collection = self.db[collection_name]
            docs = json.loads(documents)

            if isinstance(docs, dict):
                # Single document
                result = collection.insert_one(docs)
                return json.dumps({"inserted_id": str(result.inserted_id)})
            elif isinstance(docs, list):
                # Multiple documents
                result = collection.insert_many(docs)
                return json.dumps({"inserted_ids": [str(_id) for _id in result.inserted_ids]})
            else:
                return "Error: Documents must be a JSON object or a list of objects."
        except PyMongoError as e:
            logger.error(f"Error inserting documents into '{collection_name}': {e}")
            return f"Error inserting documents: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for documents: {e}")
            return f"Invalid JSON for documents: {e}"

    def update_documents(
        self,
        collection_name: str,
        query: str,
        update: str,
        multi: bool = True
    ) -> str:
        """
        Update documents in a collection based on a query.

        Args:
            collection_name (str): The collection name.
            query (str): JSON string for the filter, e.g. '{"status": "active"}'
            update (str): JSON string for the update operation, e.g. '{"$set": {"status": "inactive"}}'
            multi (bool): Whether to update multiple documents or just one.

        Returns:
            str: JSON-encoded dict of matched_count, modified_count, upserted_id, or an error message.
        """
        if self.read_only:
            return "Write operation blocked: the toolkit is in read-only mode."

        try:
            collection: Collection = self.db[collection_name]
            query_dict = json.loads(query)
            update_dict = json.loads(update)

            if multi:
                result = collection.update_many(query_dict, update_dict)
            else:
                result = collection.update_one(query_dict, update_dict)

            return json.dumps({
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "upserted_id": str(result.upserted_id) if result.upserted_id else None,
            })
        except PyMongoError as e:
            logger.error(f"Error updating documents in '{collection_name}': {e}")
            return f"Error updating documents: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for query/update: {e}")
            return f"Invalid JSON: {e}"

    def delete_documents(
        self,
        collection_name: str,
        query: str,
        multi: bool = True
    ) -> str:
        """
        Delete documents from a collection based on a query.

        Args:
            collection_name (str): The collection name.
            query (str): JSON string for the filter, e.g. '{"status": "inactive"}'
            multi (bool): Whether to delete multiple documents or just one.

        Returns:
            str: JSON-encoded dict with 'deleted_count' or an error message.
        """
        if self.read_only:
            return "Write operation blocked: the toolkit is in read-only mode."

        try:
            collection: Collection = self.db[collection_name]
            query_dict = json.loads(query)

            if multi:
                result = collection.delete_many(query_dict)
            else:
                result = collection.delete_one(query_dict)

            return json.dumps({"deleted_count": result.deleted_count})
        except PyMongoError as e:
            logger.error(f"Error deleting documents from '{collection_name}': {e}")
            return f"Error deleting documents: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for query: {e}")
            return f"Invalid JSON for query: {e}"
