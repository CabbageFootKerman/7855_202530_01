#dummy_box.py - A simple simulation of a SmartPost box for development and testing purposes.
# DISCLAIMER:
# This dummy SmartPost box simulation is for development purposes only.
# There is NO guarantee it will work as expected.
# It still needs to be tested and modified to fit your integration needs.

import time
import random


class DummySmartPostBox:
    def __init__(self, device_id="demo123"):
        self.device_id = device_id
        self.door_state = "closed"
        self.weight_g = 0.0
        self.servo_state = "locked"
        self.solenoid_state = "inactive"
        self.actuator_state = "idle"
        self.last_update_iso = None
        self.last_action = None

    def update(self):
        # Simulate state changes
        self.door_state = random.choice(["open", "closed"])
        self.weight_g = max(0.0, self.weight_g + random.uniform(-10, 10))
        self.servo_state = random.choice(["locked", "unlocked"])
        self.solenoid_state = random.choice(["active", "inactive"])
        self.actuator_state = random.choice(["idle", "moving", "error"])
        self.last_update_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.last_action = random.choice([
            "door_opened", "door_closed", "item_placed", "item_removed", "none"
        ])

    def print_status(self):
        print(f"[DummyBox] Device ID: {self.device_id}")
        print(f"[DummyBox] Door State: {self.door_state}")
        print(f"[DummyBox] Weight (g): {self.weight_g:.1f}")
        print(f"[DummyBox] Servo State: {self.servo_state}")
        print(f"[DummyBox] Solenoid State: {self.solenoid_state}")
        print(f"[DummyBox] Actuator State: {self.actuator_state}")
        print(f"[DummyBox] Last Update: {self.last_update_iso}")
        print(f"[DummyBox] Last Action: {self.last_action}")
        print("-----------------------------")

if __name__ == "__main__":
    box = DummySmartPostBox()
    print("--- Dummy SmartPost Box Started ---")
    while True:
        box.update()
        box.print_status()
        time.sleep(2)
