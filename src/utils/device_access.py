from firebase import db
from firebase_admin import firestore


def get_device(device_id):
    doc = db.collection("devices").document(device_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data


def get_user_devices(username):
    docs = db.collection("devices").stream()

    devices = []
    for doc in docs:
        data = doc.to_dict() or {}
        owner = data.get("owner_username")
        allowed = data.get("allowed_users", [])

        if owner == username or username in allowed:
            data["id"] = doc.id
            devices.append(data)

    return devices


def user_is_device_owner(username, device_id):
    device = get_device(device_id)
    if not device:
        return False
    return device.get("owner_username") == username


def user_can_access_device(username, device_id):
    device = get_device(device_id)
    if not device:
        return False

    if device.get("owner_username") == username:
        return True

    allowed = device.get("allowed_users", [])
    return username in allowed


def claim_device(username, device_id, claim_code):
    ref = db.collection("devices").document(device_id)
    doc = ref.get()

    if not doc.exists:
        return False, "Device not found."

    data = doc.to_dict() or {}

    if data.get("owner_username"):
        return False, "Device already claimed."

    if data.get("claim_code") != claim_code:
        return False, "Invalid claim code."

    ref.update({
        "owner_username": username,
        "allowed_users": [],
        "paired_at": firestore.SERVER_TIMESTAMP,
        "is_claimed": True
    })
    return True, "Device claimed."


def add_allowed_user(owner_username, device_id, target_username):
    ref = db.collection("devices").document(device_id)
    doc = ref.get()

    if not doc.exists:
        return False, "Device not found."

    data = doc.to_dict() or {}

    if data.get("owner_username") != owner_username:
        return False, "Only the owner can add users."

    if not target_username:
        return False, "Target username is required."

    if target_username == owner_username:
        return False, "Owner already has access."

    ref.update({
        "allowed_users": firestore.ArrayUnion([target_username])
    })
    return True, "User added."


def remove_allowed_user(owner_username, device_id, target_username):
    ref = db.collection("devices").document(device_id)
    doc = ref.get()

    if not doc.exists:
        return False, "Device not found."

    data = doc.to_dict() or {}

    if data.get("owner_username") != owner_username:
        return False, "Only the owner can remove users."

    if not target_username:
        return False, "Target username is required."

    ref.update({
        "allowed_users": firestore.ArrayRemove([target_username])
    })
    return True, "User removed."
