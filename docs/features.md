# SmartPost Cloud Services: FEATURE GUIDE

## Purpose
- Enable SmartPost owners to feel secure and in control of delivery orders and packages at all times, anywhere with Internet access.
- Provide a private, online user interface for:
  - Private access to your SmartPost box
  - Secure connection between your phone or laptop and your SmartPost
  - Remote control over your SmartPost box

## User input commands
- open door
- close door
- scan parcel weight
- view camera 1
- view camera 2
- view camera 3
- debug console

## Console output responses
- Confirmation message and image of the door open
- Confirmation message and image of the door closed
- The current parcel(s) weight
- Image from camera 1
- Image from camera 2
- Image from camera 3
- Access to your SmartPost's debugger UI

## Data storage
- Media (images/video) stored on local hardware connected to the server
- Personal, account, and device-status information stored securely in the cloud (Firestore)

## End-to-end flow (request → response)
- User selects a command in the SmartPost UI

 → the request is sent over a secure channel to the SmartPost controller
 
 → the device executes the action (e.g., open door, fetch camera frame, read scale)
 
 → the controller returns confirmation plus any media/telemetry

 → the UI displays the confirmation message, latest state, and relevant image/weight.