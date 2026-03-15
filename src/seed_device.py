from firebase import db
from firebase_admin import firestore

device_id = "smartpost-pi-01"

db.collection("devices").document(device_id).set({
    "display_name": "SmartPost Main Unit",
    "owner_username": "",
    "allowed_users": [],
    "claim_code": "ABC123",
    "paired_at": None,
    "created_at": firestore.SERVER_TIMESTAMP,
    "is_claimed": False,
    "status": {
        "last_seen_at": None,
        "weight_g": 0.0,
        "door_state": "unknown",
        "servo_state": "unknown",
        "solenoid_state": "unknown",
        "actuator_state": "unknown",
        "firmware_version": "unknown",
        "camera_count": 0
    }
}, merge=True)

doc = db.collection("devices").document(device_id).get()
print("Seeded device:", device_id)
print("Exists after write?", doc.exists)
print("Data:", doc.to_dict())
