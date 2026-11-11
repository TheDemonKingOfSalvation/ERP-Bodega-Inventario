from pymongo import MongoClient

from config.config_manager import obtener_mongo_uri, obtener_mongo_base

client = MongoClient(obtener_mongo_uri())
db = client[obtener_mongo_base()]
