import os
import sys

from flask import Flask, jsonify, render_template, request
from prometheus_flask_exporter import PrometheusMetrics
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)
metrics = PrometheusMetrics(app)

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB  = os.environ.get("MONGO_DB", "zorin")

if not MONGO_URI:
    # Local dev fallback — unauthenticated, localhost only
    if os.environ.get("FLASK_ENV", "development") == "production":
        print("FATAL: MONGO_URI must be set in production. Refusing to start.", file=sys.stderr)
        sys.exit(1)
    MONGO_URI = "mongodb://localhost:27017/"

client: MongoClient = MongoClient(MONGO_URI)
db = client[MONGO_DB]
users_collection = db["users"]


def insert_user(name: str, age: int) -> str:
    result = users_collection.insert_one({"name": name, "age": age})
    return str(result.inserted_id)


def get_all_names(limit: int = 100, after: str = "") -> list[str]:
    query = {"name": {"$gt": after}} if after else {}
    return [
        doc["name"]
        for doc in users_collection.find(query, {"name": 1, "_id": 0}).sort("name", 1).limit(limit)
    ]


def get_all_users() -> list[dict]:
    return list(users_collection.find({}, {"_id": 0}))


@app.route("/")
def index():
    try:
        limit = min(int(request.args.get("limit", 50)), 200)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    after = request.args.get("after", "")
    try:
        names = get_all_names(limit=limit, after=after)
        return render_template("index.html", names=names)
    except PyMongoError:
        app.logger.exception("Error connecting to database")
        return "Unable to load names right now.", 500


@app.route("/add", methods=["POST"])
def add_user():
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    name = data.get("name", "").strip()
    age = data.get("age")

    # --- name validation ---
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if len(name) > 100:
        return jsonify({"error": "Name must be 100 characters or fewer"}), 400

    # --- age validation ---
    if age is None:
        return jsonify({"error": "Age is required"}), 400
    if isinstance(age, bool):
        return jsonify({"error": "Age must be an integer"}), 400
    try:
        age = int(age)
    except (ValueError, TypeError):
        return jsonify({"error": "Age must be an integer"}), 400
    if age < 0 or age > 150:
        return jsonify({"error": "Age must be between 0 and 150"}), 400

    try:
        insert_user(name, age)
        return jsonify(
            {"message": f"Successfully inserted: {name}", "names": get_all_names()}
        )
    except PyMongoError:
        app.logger.exception("Database error while adding user")
        return jsonify({"error": "Database error"}), 500


@app.route("/health")
def health():
    try:
        users_collection.command("ping")
        return jsonify({"status": "healthy"}), 200
    except PyMongoError:
        return jsonify({"status": "unhealthy"}), 503


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)