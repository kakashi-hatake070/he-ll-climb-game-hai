"""AI Gesture Controller for Hill Climb Racing.

This script uses OpenCV and MediaPipe to track hand gestures via webcam,
and uses pynput to simulate keypresses (Right Arrow for Gas, Left Arrow for Brake).
"""

import sys
import cv2
import mediapipe as mp
from pynput.keyboard import Key, Controller

def is_hand_closed(hand_landmarks) -> bool:
    """Detect if a hand is closed (fist) by checking if fingers are folded.
    
    Checks coordinates of fingertips (8, 12, 16, 20) relative to joints (6, 10, 14, 18).
    If finger tips are below joints in screen Y (pointing up), they are folded.
    """
    landmarks = hand_landmarks.landmark
    folded_fingers = 0
    
    # 1. Index finger (Tip: 8, PIP: 6)
    if landmarks[8].y > landmarks[6].y:
        folded_fingers += 1
    # 2. Middle finger (Tip: 12, PIP: 10)
    if landmarks[12].y > landmarks[10].y:
        folded_fingers += 1
    # 3. Ring finger (Tip: 16, PIP: 14)
    if landmarks[16].y > landmarks[14].y:
        folded_fingers += 1
    # 4. Pinky finger (Tip: 20, PIP: 18)
    if landmarks[20].y > landmarks[18].y:
        folded_fingers += 1
        
    return folded_fingers >= 3

def main() -> None:
    # Initialize keyboard controller
    keyboard = Controller()
    
    # Initialize MediaPipe Hands
    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6
    )
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam. Make sure a camera is connected.")
        sys.exit(1)
        
    print("\n==============================================")
    print("AI Gesture Controller Started!")
    print("Keep both hands visible to the camera.")
    print("- Close RIGHT Hand to GAS (Right Arrow)")
    print("- Close LEFT Hand to BRAKE (Left Arrow)")
    print("Press 'Q' on the camera window to quit.")
    print("==============================================\n")
    
    gas_pressed = False
    brake_pressed = False
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break
            
        # Flip the frame horizontally for a mirrored selfie view
        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape
        
        # Convert BGR frame to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        right_hand_closed = False
        left_hand_closed = False
        
        # Process hand landmarks
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                # Draw hand landmarks on screen
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Get hand label ("Left" or "Right")
                # MediaPipe handedness is relative to the camera image coordinate,
                # but because we flip the frame, the left/right labels are mirrored.
                # In MediaPipe: "Left" is classified as the physical right hand due to camera projection.
                # With cv2.flip(frame, 1), the classification matches the screen visual layout:
                # "Right" label refers to the hand on the right side of the video, and "Left" to the left side.
                hand_label = handedness.classification[0].label
                
                # Check if this hand is closed
                closed = is_hand_closed(hand_landmarks)
                
                # Draw hand label on the frame
                wrist_landmark = hand_landmarks.landmark[0]
                lx = int(wrist_landmark.x * w)
                ly = int(wrist_landmark.y * h)
                cv2.putText(frame, f"{hand_label} Hand", (lx - 30, ly - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                if hand_label == "Right":
                    right_hand_closed = closed
                elif hand_label == "Left":
                    left_hand_closed = closed
                    
        # Apply logic: Prioritize Right Hand (Gas) if both are closed
        if right_hand_closed:
            # Press Gas, release Brake
            if not gas_pressed:
                keyboard.press(Key.right)
                gas_pressed = True
            if brake_pressed:
                keyboard.release(Key.left)
                brake_pressed = False
        elif left_hand_closed:
            # Press Brake, release Gas
            if not brake_pressed:
                keyboard.press(Key.left)
                brake_pressed = True
            if gas_pressed:
                keyboard.release(Key.right)
                gas_pressed = False
        else:
            # Release both keys if hands are open/absent
            if gas_pressed:
                keyboard.release(Key.right)
                gas_pressed = False
            if brake_pressed:
                keyboard.release(Key.left)
                brake_pressed = False
                
        # Draw on-screen status text
        status_text = "HANDS OPEN"
        text_color = (0, 255, 0) # Green
        if gas_pressed:
            status_text = "GAS ACTIVE"
            text_color = (255, 255, 0) # Cyan
        elif brake_pressed:
            status_text = "BRAKE ACTIVE"
            text_color = (0, 0, 255) # Red
            
        cv2.putText(frame, f"STATUS: {status_text}", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 3)
                    
        # Display instructions on screen
        cv2.putText(frame, "Right Fist: GAS | Left Fist: BRAKE", (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
        # Show window
        cv2.imshow("Hill Climb AI Gesture Controller", frame)
        
        # Break loop on 'q' press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    # Release resources on quit
    if gas_pressed:
        keyboard.release(Key.right)
    if brake_pressed:
        keyboard.release(Key.left)
    cap.release()
    cv2.destroyAllWindows()
    hands.close()

if __name__ == "__main__":
    main()
