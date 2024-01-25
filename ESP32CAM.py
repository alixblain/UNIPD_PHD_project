import camera
import os
import time
import machine
import network
import ubinascii
from mqtt.simple import MQTTClient

##################################################

## Initialization

# WiFi configuration
WIFI_SSID = INSERT_SSID
WIFI_PASSWORD = INSERT_PASSWORD

# MQTT configuration
MQTT_BROKER = INSERT_IP_BROKER
MQTT_PORT = 1883

# Unique MQTT client ID based on the machine's unique ID
CLIENT_ID = ubinascii.hexlify(machine.unique_id())

# MQTT topic for Camera
CAM_TOPIC = 'home/cam'

# MQTT topic for monitoring
MONITORING_TOPIC = 'home/monitoring'

##################################################


class Camera:
	def __init__(self, flash_pin=4):
		"""
		Initializes the Camera class.

		:param flash_pin (int): The pin number used for flash.
		"""
		self.flash = machine.Pin(flash_pin, machine.Pin.OUT)

	def init_camera(self):
		"""
		Initializes the camera connected to the device.

		:return bool: True if the camera is successfully initialized, otherwise False.
		"""
		try:
			camera.init(0, format=camera.JPEG)
			print("Camera initialized successfully")
			return True
		except Exception as e:
			print(f"Error initializing the camera: {e}")
			return False
            
    
	def deinit(self):
		"""
		Release the camera.
		"""
		try:
			camera.deinit()
			print("Camera successfully disabled\n")
		except Exception as e:
			print(f"Error disabling camera: {e}")

	def capture_photo(self):
		"""
		Capture a photo with the camera.

		:return bytes: The data of the captured photo, or None in case of error.
		"""
		try:
			photo = camera.capture()
			print("Photo captured successfully")
			return photo
		except Exception as e:
			print(f"Error capturing photo: {e}")
			return None



	def save_photo(self, photo, path):
		"""
		Saves the photo to the specified location.

		Args:
		photo (bytes): The photo data to be saved.
		path (str): The path where to save the photo.
		"""
		try:
			with open(path, "wb") as file:
				file.write(photo)
				print("Photo saved to ", {path})
		except Exception as e:
			print(f"Error while saving the photo at {path}: {e}")

	def turn_on_flash(self):
		"""
		Turns on the camera flash.
		"""
	    	self.flash.on()

	def turn_off_flash(self):
		"""
		Turns off the camera flash.
		"""
	    	self.flash.off()
    	
	@staticmethod
	def convert_image_to_binary(image_path):
		"""
		Converts an image to binary data.

		:param image_path (str): The path of the image to convert.

		:return bytes: The binary data of the image.
		"""
		with open(image_path, "rb") as image_file:
			return image_file.read()

##################################################

def connect_wifi(ssid, password):
	"""
	Connects the device to the specified Wi-Fi network.

	:param ssid (str): The SSID of the Wi-Fi network.
	:param password (str): The password for the Wi-Fi network.
	"""
	wlan = network.WLAN(network.STA_IF)
	wlan.active(True)
	if not wlan.isconnected():
		print('Connecting to WiFi network...')
		wlan.connect(ssid, password)
		while not wlan.isconnected():
	    		pass
	print('WiFi connected successfully')
	print('IP Address:', wlan.ifconfig())


##################################################
	
	
def publish_image_mqtt(binary_image, client_id, mqtt_broker, mqtt_port, topic):
	"""
	Publishes the image on a specified MQTT topic.

	:param binary_image (bytes): The binary data of the image to be published.
	:param mqtt_broker (str): The address of the MQTT broker.
	:param mqtt_port (int): The port number of the MQTT broker.
	:param topic (str): The MQTT topic where the image is to be published.
	"""
	mqtt_client = MQTTClient(client_id, mqtt_broker, mqtt_port, keepalive=3600)
	try:
		mqtt_client.connect()
		mqtt_client.publish(topic, binary_image)  # Publish the image
		print("Image successfully published on topic", topic)
	except Exception as e:
		print(f"Failed to publish the image: {e}")
	finally:
		mqtt_client.disconnect()


##################################################


def main():
	"""
	Main function to execute the program.
	"""

	print("""
	################################
	ESP 32 CAM - CODE initialization
	################################\n
	""")

	# Connect to the Wi-Fi network
	connect_wifi(WIFI_SSID, WIFI_PASSWORD)
	
	# Create an instance of the Camera class
	my_camera = Camera()
	my_camera.deinit()

	def mqtt_callback(topic, msg):
		"""
		Callback for MQTT messages.

		:param topic (bytes): The topic of the message.
		:param msg (bytes): The received message.
		"""
		if topic == MONITORING_TOPIC.encode():
			if msg == b"ON":
				my_camera.turn_on_flash()  # Call the function to turn on the flash
				time.sleep(1)
				my_camera.turn_off_flash()
			elif msg == b"OFF":
				my_camera.turn_off_flash()  # Call the function to turn off the flash
	    

	# Set up the MQTT client
	mqtt_client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT, keepalive=3600)
	mqtt_client.set_callback(mqtt_callback)
	mqtt_client.connect()
	mqtt_client.subscribe(MONITORING_TOPIC)

	
	while True:
		mqtt_client.check_msg()

		if my_camera.init_camera():
			photo = my_camera.capture_photo()
			if photo is not None:
				save_path = "photo.jpg"
				my_camera.save_photo(photo, save_path)
				time.sleep(1)
				binary_image = Camera.convert_image_to_binary(save_path)
				publish_image_mqtt(binary_image, CLIENT_ID + "FLASH", MQTT_BROKER, MQTT_PORT, CAM_TOPIC)
				time.sleep(2)
				try:
					os.remove(save_path)
					print(f"Photo deleted: {save_path}")
				except Exception as e:
					print(f"Error deleting photo: {e}")
		my_camera.deinit()
		time.sleep(2)


##################################################


if __name__ == "__main__":
	main()

