#!/usr/bin/env python3
import socket
import json
import math
from AlphaBot2 import AlphaBot2

HOST         = '0.0.0.0'
PORT         = 5000
SPEED        = 15
TURN_SPEED   = 10
ANGLE_THRESH = 25
DIST_THRESH  = 25

bot = AlphaBot2()
bot.stop()

def move(left, right):
    """Set individual wheel speeds. Positive = forward, negative = backward."""
    bot.setMotor(left, right)

def handle_track(cmd):
    cx, cy       = cmd['current_x'], cmd['current_y']
    tx, ty       = cmd['target_x'],  cmd['target_y']
    robot_angle  = cmd.get('robot_angle')

    dist = math.hypot(tx - cx, ty - cy)
    if dist < DIST_THRESH:
        move(0, 0)
        print("Reached target")
        return

    if robot_angle is None:
        move(SPEED, SPEED)  # no angle info — just go forward
        return
    target_angle = math.atan2(ty - cy, tx - cx)
    diff = math.degrees((target_angle - robot_angle + math.pi) % (2 * math.pi) - math.pi)

    if abs(diff) < ANGLE_THRESH:
        correction = int(diff / ANGLE_THRESH * 5)
        move(SPEED + correction, SPEED - correction)      # forward
        print(f"FORWARD  diff={diff:+.1f}° dist={dist:.0f}px")
    elif diff > 0:
        move(TURN_SPEED, -TURN_SPEED)   # turn right
        print(f"RIGHT    diff={diff:+.1f}° dist={dist:.0f}px")
    else:
        move(-TURN_SPEED, TURN_SPEED)   # turn left
        print(f"LEFT     diff={diff:+.1f}° dist={dist:.0f}px")

def run():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"Listening on port {PORT}...")

    try:
        while True:
            conn, addr = server.accept()
            print(f"Connected: {addr}")
            buffer = ""
            try:
                while True:
                    data = conn.recv(1024).decode()
                    if not data:
                        break
                    buffer += data
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        try:
                            cmd = json.loads(line)
                            if cmd['command'] == 'TRACK':
                                handle_track(cmd)
                            elif cmd['command'] == 'STOP':
                                move(0, 0)
                                print("STOP")
                        except Exception as e:
                            print(f"Error: {e}")
            except:
                pass
            finally:
                move(0, 0)
                conn.close()
                print("Disconnected")
    except KeyboardInterrupt:
        pass
    finally:
        move(0, 0)
        import RPi.GPIO as GPIO
        GPIO.cleanup()
        server.close()

if __name__ == "__main__":
    run()
