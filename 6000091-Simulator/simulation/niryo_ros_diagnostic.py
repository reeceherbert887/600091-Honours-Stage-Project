import websocket
import json
import time

ROBOT = "ws://10.10.10.10:9090"

print("=" * 60)
print("NIRYO ONE ROS DIAGNOSTIC")
print("=" * 60)

try:
    print("\n[1] Connecting to ROSBridge...")
    ws = websocket.create_connection(ROBOT, timeout=5)

    print("[PASS] WebSocket connection established")

    print("\n[2] Asking ROS for available topics...")

    request = {
        "op": "call_service",
        "service": "/rosapi/topics",
        "args": {}
    }

    ws.send(json.dumps(request))

    response = ws.recv()
    data = json.loads(response)

    print("[PASS] ROS responded")

    topics = data.get("values", {}).get("topics", [])

    print("\nROS topics found:", len(topics))
    print("-" * 60)

    for topic in sorted(topics):
        print(topic)

    print("-" * 60)

    niryo_topics = [
        topic for topic in topics
        if "niryo" in topic.lower()
        or "joint" in topic.lower()
        or "robot" in topic.lower()
    ]

    print("\nNiryo / robot related topics:")
    print("-" * 60)

    if niryo_topics:
        for topic in sorted(niryo_topics):
            print(topic)
    else:
        print("No obvious Niryo topics found.")

    print("\n[3] Connection test complete.")
    print("[PASS] Raspberry Pi reachable")
    print("[PASS] ROSBridge reachable")
    print("[PASS] ROS API responding")

    ws.close()

except ConnectionRefusedError:
    print("\n[FAIL] Connection refused.")
    print("Port 9090 is not accepting ROSBridge connections.")

except websocket.WebSocketTimeoutException:
    print("\n[FAIL] Connection timed out.")

except Exception as error:
    print("\n[FAIL] Test failed:")
    print(type(error).__name__ + ":", error)
