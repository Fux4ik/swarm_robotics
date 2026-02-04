import cv2
import numpy as np

# Open camera
cap = cv2.VideoCapture(0)

# Blue color range (HSV)
lower_blue = np.array([90, 50, 50])
upper_blue = np.array([130, 255, 255])

print("Simple Car Detection Started!")
print("Press 'q' to quit")
print("Press 's' to save coordinates")

while True:
    # Read frame from camera
    ret, frame = cap.read()
    if not ret:
        break
    
    # Convert to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Find blue color
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    # Clean up the mask
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)
    
    # Find blue objects
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    car_count = 0
    
    # Draw rectangles around blue objects
    for contour in contours:
        area = cv2.contourArea(contour)
        
        # Only detect objects bigger than 500 pixels
        if area > 500:
            car_count += 1
            
            # Get rectangle coordinates
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculate center
            cx = x + w // 2
            cy = y + h // 2
            
            # Draw green rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw center point
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            
            # Write coordinates
            cv2.putText(frame, f"Car {car_count}", (x, y - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"({cx}, {cy})", (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    # Show car count
    cv2.putText(frame, f"Cars: {car_count}", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    
    # Show the result
    cv2.imshow('Car Detection', frame)
    
    # Handle keyboard
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        # Save coordinates
        with open('car_coordinates.txt', 'w') as f:
            f.write(f"Cars detected: {car_count}\n\n")
            
            car_num = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:
                    car_num += 1
                    x, y, w, h = cv2.boundingRect(contour)
                    cx = x + w // 2
                    cy = y + h // 2
                    
                    f.write(f"Car {car_num}:\n")
                    f.write(f"  Center: ({cx}, {cy})\n")
                    f.write(f"  Box: x={x}, y={y}, w={w}, h={h}\n\n")
        
        print("Coordinates saved!")

# Close everything
cap.release()
cv2.destroyAllWindows()
