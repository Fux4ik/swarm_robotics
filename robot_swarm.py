import cv2
import numpy as np
import socket
import json
import math

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
CAMERA_INDEX  = 4
THRESHOLD     = 127
MIN_AREA      = 500
TARGET_RADIUS = 25
MERGE_DIST    = 80

ROBOT_IPS = {
    1: "192.168.1.147",
    2: "192.168.1.102",
    3: "192.168.1.103",
    4: "192.168.1.104",
}
RPI_PORT = 5000
# ─────────────────────────────────────────────

cap = cv2.VideoCapture(CAMERA_INDEX)

# State
robots         = []
robot_targets  = {}
selected_robot = None
tracking_mode  = False
show_mask      = False

# Stable ID tracking
stable_robots = {}
next_id       = 1
ID_MAX_LOST   = 10
ID_MAX_DIST   = 60

# Manual assignment: stable_id → robot number (1-4)
# Select a robot, press 1-4 to assign it to that robot number
id_assignments = {}

# Sockets
sockets   = {}
connected = {}


# ── Network ────────────────────────────────────
def connect_robot(num):
    ip = ROBOT_IPS.get(num)
    if not ip:
        return
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((ip, RPI_PORT))
        sockets[num]   = s
        connected[num] = True
        print(f"✓ Robot {num} connected ({ip})")
    except Exception as e:
        connected[num] = False
        print(f"✗ Robot {num} failed: {e}")

def connect_all():
    for num in ROBOT_IPS:
        connect_robot(num)

def send_command(num, cmd):
    if not connected.get(num):
        return
    try:
        sockets[num].sendall((json.dumps(cmd) + "\n").encode())
    except:
        connected[num] = False
        print(f"! Lost Robot {num}")


# ── Stable ID tracker ──────────────────────────
def update_stable_ids(raw):
    global stable_robots, next_id
    matched = set()
    result  = []

    for det in raw:
        cx, cy  = det['center']
        best_id = None
        best_d  = ID_MAX_DIST

        for sid, sr in stable_robots.items():
            if sid in matched:
                continue
            d = np.hypot(cx - sr['center'][0], cy - sr['center'][1])
            if d < best_d:
                best_d, best_id = d, sid

        if best_id is not None:
            stable_robots[best_id].update({'center': det['center'], 'bbox': det['bbox'], 'lost': 0})
            matched.add(best_id)
            result.append({**det, 'num': best_id})
        else:
            stable_robots[next_id] = {'center': det['center'], 'bbox': det['bbox'], 'lost': 0}
            matched.add(next_id)
            result.append({**det, 'num': next_id})
            next_id += 1

    for sid in list(stable_robots):
        if sid not in matched:
            stable_robots[sid]['lost'] += 1
            if stable_robots[sid]['lost'] > ID_MAX_LOST:
                del stable_robots[sid]

    return result

def get_robot_num(stable_id):
    """Get assigned robot number (1-4) for a stable ID, or None if not assigned."""
    return id_assignments.get(stable_id)


# ── Mouse ──────────────────────────────────────
def mouse_callback(event, x, y, flags, param):
    global selected_robot, robot_targets
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    for robot in robots:
        rx, ry, rw, rh = robot['bbox']
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            selected_robot = robot
            num = get_robot_num(robot['num'])
            print(f"Selected stable_id={robot['num']} → Robot {num if num else '(unassigned)'}")
            return
    if selected_robot:
        num = get_robot_num(selected_robot['num'])
        if num:
            robot_targets[num] = (x, y)
            print(f"Target for Robot {num}: ({x},{y})")
        else:
            print("Assign this robot a number first (press 1-4)")


# ── Main ───────────────────────────────────────
cv2.namedWindow('Swarm Control')
cv2.setMouseCallback('Swarm Control', mouse_callback)

print("="*50)
print("  SWARM CONTROL")
print("  Click robot → select")
print("  Press 1-4   → assign robot number")
print("  Click field → set target")
print("  g=go  x=stop  c=clear  m=mask  r=reconnect  q=quit")
print("="*50)

connect_all()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # ── Detection ──────────────────────────────
    hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    _, binary = cv2.threshold(gray, THRESHOLD, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((5, 5), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  kernel, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    # ── Red dot detection ──────────────────────
    red_mask = cv2.inRange(hsv, np.array([0,   120, 70]), np.array([10,  255, 255])) | \
               cv2.inRange(hsv, np.array([170, 120, 70]), np.array([180, 255, 255]))
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    raw_reds = []
    for rc in cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        if cv2.contourArea(rc) < 20:
            continue
        M = cv2.moments(rc)
        if M['m00'] == 0:
            continue
        raw_reds.append((int(M['m10']/M['m00']), int(M['m01']/M['m00'])))

    # Merge nearby red blobs
    red_centers, used = [], set()
    for i, (ax, ay) in enumerate(raw_reds):
        if i in used:
            continue
        mx, my, count = ax, ay, 1
        for j, (bx, by) in enumerate(raw_reds):
            if j == i or j in used:
                continue
            if np.hypot(ax - bx, ay - by) < MERGE_DIST:
                mx += bx; my += by; count += 1; used.add(j)
        used.add(i)
        red_centers.append((mx // count, my // count))

    # ── Robot detection ────────────────────────
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    raw = []
    for cnt in contours:
        if cv2.contourArea(cnt) < MIN_AREA:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        cx, cy = x + w // 2, y + h // 2

        angle, best_d = None, w
        for rx, ry in red_centers:
            d = np.hypot(rx - cx, ry - cy)
            if d < best_d:
                best_d, angle = d, np.arctan2(ry - cy, rx - cx) + math.pi

        raw.append({'center': (cx, cy), 'bbox': (x, y, w, h), 'angle': angle})

    robots = update_stable_ids(raw)

    if selected_robot:
        match = next((r for r in robots if r['num'] == selected_robot['num']), None)
        if match:
            selected_robot = match

    # ── Tracking ───────────────────────────────
    if tracking_mode:
        for robot in robots:
            num = get_robot_num(robot['num'])
            if num is None or num not in robot_targets:
                continue
            cx, cy = robot['center']
            tx, ty = robot_targets[num]

            if np.hypot(tx - cx, ty - cy) < TARGET_RADIUS:
                send_command(num, {"command": "STOP"})
                del robot_targets[num]
                print(f"Robot {num} reached target!")
            else:
                send_command(num, {
                    "command":     "TRACK",
                    "current_x":  cx,
                    "current_y":  cy,
                    "target_x":   tx,
                    "target_y":   ty,
                    "robot_angle": robot.get('angle'),
                })

        if not robot_targets:
            tracking_mode = False
            print("All robots reached targets!")

    # ── Drawing ────────────────────────────────
    for robot in robots:
        x, y, w, h = robot['bbox']
        cx, cy     = robot['center']
        stable_id  = robot['num']
        num        = get_robot_num(stable_id)
        is_sel     = selected_robot and selected_robot['num'] == stable_id

        color     = (0, 255, 255) if is_sel else (0, 255, 0)
        thickness = 4             if is_sel else 2

        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
        cv2.circle(frame, (cx, cy), 6, (0, 0, 255), -1)

        # Show assigned number or "?" if unassigned
        label = f"R{num}" if num else "R?"
        cv2.putText(frame, f"{label} ({cx},{cy})", (x, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        # Direction arrow
        if robot.get('angle') is not None:
            length = max(w, h) // 2
            ex = int(cx + length * np.cos(robot['angle']))
            ey = int(cy + length * np.sin(robot['angle']))
            cv2.arrowedLine(frame, (cx, cy), (ex, ey), (0, 0, 255), 2, tipLength=0.3)

        # Target line + distance
        if num and num in robot_targets:
            tx, ty = robot_targets[num]
            cv2.line(frame, (cx, cy), (tx, ty), (255, 0, 255), 2)
            cv2.circle(frame, (tx, ty), 10, (255, 0, 255), -1)
            dist = int(np.hypot(tx - cx, ty - cy))
            cv2.putText(frame, f"{dist}px", (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    cv2.putText(frame, "g=go  x=stop  c=clear  m=mask  q=quit | select robot then press 1-4",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

    cv2.imshow('Swarm Control', frame)
    if show_mask:
        cv2.imshow('Mask', binary)
    elif cv2.getWindowProperty('Mask', cv2.WND_PROP_VISIBLE) >= 1:
        cv2.destroyWindow('Mask')

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key in (ord('1'), ord('2'), ord('3'), ord('4')):
        # Assign selected robot to number 1-4
        if selected_robot:
            num = int(chr(key))
            # Remove any previous assignment to this number
            for sid in list(id_assignments):
                if id_assignments[sid] == num:
                    del id_assignments[sid]
            id_assignments[selected_robot['num']] = num
            print(f"✓ Assigned Robot {num} (stable_id={selected_robot['num']})")
            connect_robot(num)  # connect to this robot's IP
        else:
            print("Select a robot first!")
    elif key == ord('g'):
        if robot_targets:
            tracking_mode = True
            print("Tracking started!")
        else:
            print("Set targets first!")
    elif key == ord('x'):
        tracking_mode = False
        for r in robots:
            num = get_robot_num(r['num'])
            if num:
                send_command(num, {"command": "STOP"})
        print("All stopped")
    elif key == ord('c'):
        robot_targets.clear()
        selected_robot = None
        tracking_mode  = False
    elif key == ord('m'):
        show_mask = not show_mask
    elif key in (ord('+'), ord('=')):
        THRESHOLD = min(255, THRESHOLD + 5)
        print(f"Threshold: {THRESHOLD}")
    elif key in (ord('-'), ord('_')):
        THRESHOLD = max(0, THRESHOLD - 5)
        print(f"Threshold: {THRESHOLD}")
    elif key == ord('r'):
        connect_all()

# ── Cleanup ────────────────────────────────────
for num in list(sockets):
    try:
        send_command(num, {"command": "STOP"})
        sockets[num].close()
    except:
        pass

cap.release()
cv2.destroyAllWindows()
