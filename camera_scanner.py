import cv2
from PIL import Image
from pyzbar.pyzbar import decode
import time

def scan_barcode_from_camera():
    """
    This function opens the default camera, looks for a barcode,
    prints the barcode data when found, and then closes.
    """
    # Start video capture from the default camera (usually index 0)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return None

    print("👉 Point camera at a barcode...")
    print("Press 'q' to quit manually.")
    
    detected_barcode = None

    while True:
        # Read a frame from the camera
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        # Use pyzbar to find and decode barcodes in the frame
        decoded_objects = decode(Image.fromarray(frame))
        
        if decoded_objects:
            # Get the first detected barcode
            barcode_obj = decoded_objects[0]
            detected_barcode = barcode_obj.data.decode("utf-8")
            
            # Draw a green rectangle around the detected barcode
            points = barcode_obj.polygon
            if len(points) == 4:
                # pyzbar returns points, we need to convert them for OpenCV
                pts = [(points[j].x, points[j].y) for j in range(4)]
                # Create a simple list of points for polylines
                cv2.polylines(frame, [cv2.UMat(pts)], True, (0, 255, 0), 3)

            # Display the detected barcode data on the frame
            cv2.putText(frame, f"Detected: {detected_barcode}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Show the frame in a window
            cv2.imshow("Barcode Scanner", frame)
            
            # Wait for a moment to show the user it was detected
            print(f"\n✅ Barcode Detected: {detected_barcode}")
            time.sleep(2) # Keep the window open for 2 seconds after detection
            break # Exit the loop once a barcode is found

        # Display the live camera feed
        cv2.imshow("Barcode Scanner", frame)

        # Check if the 'q' key was pressed to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nQuitting scanner.")
            break

    # Release the camera and close all OpenCV windows
    cap.release()
    cv2.destroyAllWindows()
    
    return detected_barcode

# --- Main part of the script ---
if __name__ == "__main__":
    print("Starting barcode scanner...")
    barcode_data = scan_barcode_from_camera()

    if barcode_data:
        print(f"\nProcess finished. The scanned barcode is: {barcode_data}")
    else:
        print("\nProcess finished. No barcode was scanned.")