import os
import json
from datetime import datetime, timezone
from pymongo import MongoClient
import pymongo.errors
from mcp.server.fastmcp import FastMCP

def get_db_collection():
    # Retrieve connection string from env or default to localhost
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(mongo_uri)
    db = client["geosignal"]
    collection = db["events"]
    
    # Ensure that the headline is unique across documents
    collection.create_index("headline", unique=True)
    return collection

def register_db_tools(mcp: FastMCP):

    @mcp.tool()
    def check_duplicate(headline: str) -> str:
        """
        Check if an event headline has already been processed and logged.
        Returns 'True' if duplicate, 'False' otherwise.
        """
        try:
            collection = get_db_collection()
            # Use regex for approximate string matching (case-insensitive)
            doc = collection.find_one({"headline": {"$regex": headline, "$options": "i"}})
            return "True" if doc else "False"
        except Exception as e:
            return f"Error checking duplicates: {str(e)}"

    @mcp.tool()
    def log_event(headline: str, severity: int, event_type: str, raw_data_json: str) -> str:
        """
        Log an evaluated event into the MongoDB database.
        raw_data_json should be a JSON string of all related data.
        """
        try:
            collection = get_db_collection()
            
            event_doc = {
                "headline": headline,
                "severity": severity,
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc),
                "raw_data": raw_data_json
            }
            
            collection.insert_one(event_doc)
            return f"Successfully logged event: '{headline}' with severity {severity}."
        except pymongo.errors.DuplicateKeyError:
            return f"Event already exists with headline: '{headline}'"
        except Exception as e:
            return f"Error logging event: {str(e)}"
