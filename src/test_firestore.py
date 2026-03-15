from firebase import db

db.collection("test").document("connection").set({
    "ok": True
})

print("Firestore connection worked")
