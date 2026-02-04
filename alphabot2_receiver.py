#!/usr/bin/env python3
"""
Simple AlphaBot2 Receiver with Real-Time Tracking
"""

import socket
import json
import time
import math
from AlphaBot2 import AlphaBot2

HOST = '0.0.0.0'
PORT = 5000

# ADJUST THESE VALUES!
PIXELS_PER_CM = 10       # Calibrate: measure 10cm with ruler
SPEED = 15               # Motor speed (20-80, start low!)

robot = AlphaBot2()
robot.setPWMA(SPEED)
robot.setPWMB(SPEED)
robot.stop()

print("="*60)
print("ALPHABOT2 SIMPLE RECEIVER")
print("="*60)
print(f"Speed: {SPEED}")
print(f"Pixels per cm: {PIXELS_PER_CM}")
print("Listening on port 5000...")
print("="*60)

def calculate_direction(current_x, current_y, target_x, target_y):
    """Calculate which direction to move"""
    dx = target_x - current_x
    dy = target_y - current_y
    
    # Calculate angle in degrees
    angle = math.degrees(math.atan2(dx, -dy))
    
    # Calculate distance
    distance = math.sqrt(dx*dx + dy*dy)
    
    return angle, distance

# Movement state
last_action_time = 0
current_action = "IDLE"
action_start_time = 0

def move_robot(angle, distance):
    """Move robot with step algorithm: forward -> turn -> forward"""
    global last_action_time, current_action, action_start_time
    
    current_time = time.time()
    
    # If very close, stop
    if distance < 20:  # pixels
        robot.stop()
        current_action = "IDLE"
        return "REACHED"
    
    # Step-by-step movement algorithm
    if current_action == "IDLE":
        # Start new cycle
        if abs(angle) > 10:  # Need to turn
            # Turn first
            if angle > 0:
                robot.right()
                current_action = "TURNING_RIGHT"
            else:
                robot.left()
                current_action = "TURNING_LEFT"
            action_start_time = current_time
            return current_action
        else:
            # Go straight
            robot.forward()
            current_action = "MOVING"
            action_start_time = current_time
            return "FORWARD"
    
    elif current_action in ["TURNING_RIGHT", "TURNING_LEFT"]:
        # Turn for max 0.5 seconds
        if current_time - action_start_time >= 0.5:
            robot.stop()
            current_action = "IDLE"
            return "TURN_DONE"
        return current_action
    
    elif current_action == "MOVING":
        # Move forward for 0.5 seconds
        if current_time - action_start_time >= 0.5:
            robot.stop()
            current_action = "IDLE"
            return "MOVE_DONE"
        return "FORWARD"
    
    return current_action

def start_server():
    """Start server"""
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    
    try:
        while True:
            print("\nWaiting for connection...")
            conn, addr = server.accept()
            print(f"✓ Connected to {addr}")
            
            buffer = ""
            
            try:
                while True:
                    data = conn.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    buffer += data
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        
                        try:
                            cmd = json.loads(line)
                            
                            if cmd['command'] == 'TRACK':
                                # Real-time tracking
                                cx = cmd['current_x']
                                cy = cmd['current_y']
                                tx = cmd['target_x']
                                ty = cmd['target_y']
                                
                                angle, distance = calculate_direction(cx, cy, tx, ty)
                                action = move_robot(angle, distance)
                                
                                print(f"Angle: {angle:6.1f}° | Dist: {distance:6.1f}px | {action}")
                            
                            elif cmd['command'] == 'STOP':
                                robot.stop()
                                print("⏹ STOPPED")
                        
                        except Exception as e:
                            print(f"Error: {e}")
            
            except Exception as e:
                print(f"Connection error: {e}")
            
            finally:
                robot.stop()
                conn.close()
                print("Connection closed")
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    finally:
        robot.stop()
        import RPi.GPIO as GPIO
        GPIO.cleanup()
        server.close()

if __name__ == "__main__":
    start_server()
