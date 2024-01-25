import machine
from machine import I2C, Pin
from BME280_Class import BME280
from STEP_MOTOR_Class import STEP_MOTOR
import network
import time
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
TOPIC = 'home/data'
MOTOR_TOPIC = 'home/motor'

# Unique MQTT client ID based on the machine's unique ID
CLIENT_ID = ubinascii.hexlify(machine.unique_id())

##################################################


def connect_wifi(ssid, password):
	""" 
	Connect to a Wi-Fi network using provided credentials.

	:param ssid (str): The SSID of the Wi-Fi network.
	:param password (str): The password of the Wi-Fi network.

	:return: None, but prints the connection status and IP address on successful connection.
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


def connect_mqtt():
	""" 
	Connect to the MQTT broker and return the MQTT client instance.

	Parameters:
	None

	:return: client (MQTTClient): The connected MQTT client instance.
	"""
	client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT)
	client.connect()
	return client


##################################################


def main():
	""" 
	Main function to execute the program.

	Connects to WiFi and MQTT, initializes the BME280 sensor, and publishes sensor data.

	Parameters:
	None

	:return: None
	"""
	
	print("""
	#################
	ESP 32 - CODE
	#################\n
	""")
	
	# Establishing WiFi connection
	connect_wifi(WIFI_SSID, WIFI_PASSWORD)

	# Defining and initializing I2C pins and bus
	scl = Pin(32)  # Serial Clock
	sda = Pin(33)  # Serial Data

	i2c = I2C(0, scl=scl, sda=sda, freq=100000)
	i2c_devices = i2c.scan()
	print("List of I2C devices found during scan:")
	for device in i2c_devices:
		print("Found device 0x%02x (dec: %d)" % (device, device))

	# Initializing BME280 sensor with the I2C bus
	bme = BME280(i2c)

	# Defining step_motor
	step_motor = STEP_MOTOR()
	
	def mqtt_callback(topic, msg):
		"""
		Callback for MQTT messages.

		:param topic (bytes): The topic of the message.
		:param msg (bytes): The received message.
		"""
		if topic == MOTOR_TOPIC.encode():
			message = msg.decode("utf-8")
			if message.lower() == "clockwise":
				step_motor.rotate_by_angle(angle=1, delay=1000, clockwise=True)
			elif message.lower() == "counterclockwise":
				step_motor.rotate_by_angle(angle=1, delay=1000, clockwise=False)
			else:
				try:
					step_motor.rotate_to_angle(target_angle=int(message), delay=1000)
				except:
					print("Invalid input. Please enter an integer.")
	
	# Set up the MQTT client
	mqtt_client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT, keepalive=3600)
	mqtt_client.set_callback(mqtt_callback)
	mqtt_client.connect()
	mqtt_client.subscribe(MOTOR_TOPIC)


	# Main loop to measure sensor data and publish it via MQTT
	while True:
		mqtt_client.check_msg()
	
		data = bme.doMeasure()  # Measure sensor data
		bme.dumpLastMeasurement()  # Dump the measurement for debugging
		message = "T = {} ; H = {} ; P = {}".format(data[0], data[2], data[1])  # Format the message
		mqtt_client.publish(TOPIC, message)  # Publish the message to the MQTT topic
		time.sleep(5)  # Wait for 2 seconds before the next measurement


##################################################


if __name__ == '__main__':
	main()
