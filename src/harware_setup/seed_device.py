import secrets
from firebase import db
from firebase_admin import firestore

# --- Interactive device provisioning ---

device_id = input("Device ID [smartpost-pi-1000]: ").strip() or "smartpost-pi-1000"
display_name = input("Display name [smartpost-pi-1000]: ").strip() or "smartpost-pi-1000"

generated_code = secrets.token_hex(4).upper()  # e.g. "A3F1B90C"
claim_code = input(f"Claim code [{generated_code}]: ").strip() or generated_code

print(f"\n  Device ID:    {device_id}")
print(f"  Display name: {display_name}")
print(f"  Claim code:   {claim_code}")

confirm = input("\nWrite to Firestore? [Y/n]: ").strip().lower()
if confirm not in ("", "y", "yes"):
    print("Aborted.")
    raise SystemExit(0)

db.collection("devices").document(device_id).set({
    "display_name": display_name,
    "owner_username": "",
    "allowed_users": [],
    "claim_code": claim_code,
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
print("\nSeeded device:", device_id)
print("Exists after write?", doc.exists)
print("Data:", doc.to_dict())
