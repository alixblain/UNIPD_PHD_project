# Import necessary libraries
from flask import Flask, render_template
import paho.mqtt.client as mqtt
import os
import time
import cv2
import numpy as np
import datetime

##################################################

## Initialization 

# Create a Flask web application
app = Flask(__name__)

# MQTT Configuration
mqtt_broker_host = "172.20.10.2"
mqtt_topics = ["home/cam", "home/data"]

# Initialize global variables to store the latest data
latest_image_path = ''
latest_data = ''

# Flag to detect motion, initially set to False
detect_mouv = False

##################################################

def get_current_script_directory():
    """
    Get the directory path of the currently running script.

    :return: Directory path of the currently running script.
    """
    # Use the '__file__' attribute to get the path of the current script
    script_path = os.path.abspath(__file__)
    # Use 'os.path.dirname' to get the directory containing the script
    script_directory = os.path.dirname(script_path)
    return script_directory

# Directories for saving received images and data
static_image_folder = get_current_script_directory() + "/static"
image_filename = "received_image.png"
output_folder = static_image_folder+'/MONITORING/'

##################################################

def detect_movement(image1_path, image2_path, threshold=30):
    """
    Detects movement between two images with resizing to match their sizes.

    :param image1_path: Path to the first image.
    :param image2_path: Path to the second image.
    :param threshold: Threshold value to determine movement. Default is 30.
    :return: True if movement is detected, False otherwise.
    """

    # Load the images from the provided file paths
    img1 = cv2.imread(image1_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(image2_path, cv2.IMREAD_GRAYSCALE)

    # Check if images are loaded successfully, if not, raise an exception
    if img1 is None or img2 is None:
        raise ValueError("One or both images could not be loaded. Check the file paths.")

    # Resize img2 to match img1's size
    img2_resized = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

    # Compute the absolute difference between the two grayscale images
    diff = cv2.absdiff(img1, img2_resized)

    # Threshold the difference image to create a binary image
    _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

    # Check for movement by summing the pixel values in the thresholded image
    movement_detected = np.sum(thresh) > 0

    return movement_detected


def detect_and_mark_movement(image1_path, image2_path, output_folder, threshold=30):
    """
    Detects movement between two images, highlights the areas of movement with a red rectangle,
    and optionally saves the marked image.

    :param image1_path: Path to the first image.
    :param image2_path: Path to the second image.
    :param threshold: Threshold value to determine movement. Default is 30.
    :param output_folder: Folder to save the marked image.
    :return: True if movement is detected, False otherwise.
    """

    # Load the images from the provided file paths
    img1 = cv2.imread(image1_path)
    img2 = cv2.imread(image2_path)

    # Check if images are loaded successfully, if not, raise an exception
    if img1 is None or img2 is None:
        raise ValueError("One or both images could not be loaded. Check the file paths.")

    # Convert images to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Compute the absolute difference between the two grayscale images
    diff = cv2.absdiff(gray1, gray2)

    # Threshold the difference image to create a binary image
    _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

    # Find contours in the binary image
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Draw red rectangles around areas of movement
    for contour in contours:
        (x, y, w, h) = cv2.boundingRect(contour)
        cv2.rectangle(img2, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # Check for movement by counting the number of detected contours
    movement_detected = len(contours) > 0

    # Save the marked image if a folder is provided
    if output_folder is not None and movement_detected:
        # Create the folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Generate a timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Construct the file path
        output_path = os.path.join(output_folder, f"monitor_image_{timestamp}.jpg")

        # Save the image
        cv2.imwrite(output_path, img2)
    
    return movement_detected

##################################################

# Callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, message):
    """
    Callback for handling PUBLISH messages received from the server.

    This function is called when a PUBLISH message is received from the MQTT server. 
    It processes two types of messages related to camera and data topics separately.
    
    For camera-related messages:
    - Saves a received image.
    - Compares it with the previous image to detect movement.
    - Publishes a status message based on the movement detection result.
    - Manages image files by renaming and deleting old images.
    
    For data-related messages:
    - Decodes and stores received data.
    
    :param client: The MQTT client instance.
    :param userdata: User-specific data passed to the MQTT client.
    :param message: The received MQTT message.
    :return: None
    """
        
    global latest_image_path, latest_data, detect_mouv

    # Check if the received message is related to the camera topic
    if message.topic == "home/cam":
        new_image_path = os.path.join(static_image_folder, "new_image.jpg")
        latest_image_path = os.path.join(static_image_folder, image_filename)
        
        # Save the newly received image
        print(message.payload)
        with open(new_image_path, 'wb') as image_file:
            image_file.write(message.payload)
        print("New image temporarily saved")

        # Compare it with the old image if it exists
        if latest_image_path and os.path.exists(latest_image_path):
            movement_detected = detect_and_mark_movement(latest_image_path, new_image_path, output_folder)
            if movement_detected:
                detect_mouv = True
                print("Movement detected between the images")
                client.publish("home/monitoring", "ON")
            else:
                detect_mouv = False
                print("No significant movement detected")
                client.publish("home/monitoring", "OFF")

            print(detect_mouv)

            # Remove the old image
            os.remove(latest_image_path)
            print(f"Old image removed: {latest_image_path}")

        # Rename the new image with the name of the old one
        # Check if the file exists before renaming
        if os.path.exists(new_image_path):
            try:
                os.rename(new_image_path, latest_image_path)
            except Exception as e:
                print(f"Error while renaming file: {e}")
            print(f"New image renamed: {latest_image_path}")

    # Check if the received message is related to the data topic
    elif message.topic == "home/data":
        print("Received data")
        data_str = message.payload.decode("utf-8")
        data_parts = data_str.split(';')
        data_dict = {p.split('=')[0].strip(): p.split('=')[1].strip() for p in data_parts}
        latest_data = data_dict
        print(f"Data received on 'home/data': {latest_data}")  # Add this line to display received data

##################################################
        
# Setup MQTT Client
client = mqtt.Client()
client.on_message = on_message
client.connect(mqtt_broker_host, 1883, 60)
for topic in mqtt_topics:
    client.subscribe(topic)

# Run the MQTT client in a separate thread
client.loop_start()

@app.route('/')
def index():
    """
    Flask route for the web application's main page.

    This route renders an HTML template with the latest image, data, and motion detection status.

    :return: Rendered HTML template.
    """
    # Render template with the latest image and data
    return render_template('indexFinal.html', image_path=latest_image_path, data=latest_data, mouv=detect_mouv)

if __name__ == '__main__':
    # Start the Flask web application
    app.run(host='0.0.0.0', port=5001, use_reloader=False, threaded=True)