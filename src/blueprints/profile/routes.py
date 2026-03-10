from flask import Blueprint, request, jsonify

from firebase import db

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/api/profile", methods=["POST"])
def create_profile():
    data = request.get_json() or {}
    username = data.get("username")
    if not username:
        return jsonify({"error": "username is required"}), 400

    # Save the whole JSON as the document
    db.collection("profiles").document(username).set(data)
    return jsonify({"message": "Created", "username": username}), 201


@profile_bp.route("/api/profile/<username>", methods=["GET"])
def get_profile(username):
    doc = db.collection("profiles").document(username).get()
    if not doc.exists:
        return jsonify({"error": "Not found"}), 404

    return jsonify({"username": doc.id, **doc.to_dict()}), 200


@profile_bp.route("/api/profile/<username>", methods=["PUT"])
def update_profile(username):
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    data = request.get_json(silent=True) or {}

    #  update only the provided fields (partial update)
    doc_ref = db.collection("profiles").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Not found"}), 404

    # Firestore update fails if data is empty
    if not data:
        return jsonify({"error": "No fields to update"}), 400

    doc_ref.update(data)
    return jsonify({"message": "Updated", "username": username}), 200


@profile_bp.route("/api/profile/<username>", methods=["DELETE"])
def delete_profile(username):
    doc_ref = db.collection("profiles").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Not found"}), 404

    doc_ref.delete()
    return jsonify({"message": "Deleted", "username": username}), 200
