from machine import Pin
import time


class STEP_MOTOR:
	
	def __init__(self):
		# Define motor current angle
		self.motor_angle = 0.0
		
		# Define the pins for motor control
		self.IN1 = Pin(14, Pin.OUT)
		self.IN2 = Pin(27, Pin.OUT)
		self.IN3 = Pin(26, Pin.OUT)
		self.IN4 = Pin(25, Pin.OUT)

		# Define the motor control sequence
		self.sequence = [
			[1, 0, 0, 1],
			[1, 0, 0, 0],
			[1, 1, 0, 0],
			[0, 1, 0, 0],
			[0, 1, 1, 0],
			[0, 0, 1, 0],
			[0, 0, 1, 1],
			[0, 0, 0, 1]
			]

		# Calculate the sequence size
		self.sequence_size = len(self.sequence)

		# Motor specifications
		stride_angle = 5.625  # Stride angle in degrees
		speed_variation_ratio = 1/64  # Speed variation ratio
		self.resolution = int(360 / stride_angle / speed_variation_ratio / self.sequence_size) # 512
	
	
	# Function to set the motor control step based on the sequence
	def set_step(self, step):
		self.IN1.value(self.sequence[step][0])
		self.IN2.value(self.sequence[step][1])
		self.IN3.value(self.sequence[step][2])
		self.IN4.value(self.sequence[step][3])
	
	
	# Function to rotate the motor by a specified angle
	def rotate_by_angle(self, angle, delay, clockwise=True):
		if clockwise:
			print("Clockwise rotation")
			angle = angle if self.motor_angle + angle <= 180 else 180 - self.motor_angle
			steps = int((angle / 360) * self.resolution)
			for _ in range(steps):
				for i in range(self.sequence_size-1):
					self.set_step(i)
					time.sleep_us(delay)
				self.motor_angle += 360 / self.resolution
		else:
			print("Counterclockwise rotation")
			angle = angle if self.motor_angle - angle >= -180 else 180 + self.motor_angle
			steps = int((angle / 360) * self.resolution)
			for _ in range(steps-1, -1, -1):
				for i in range(self.sequence_size-1, -1, -1):
					self.set_step(i)
					time.sleep_us(delay)
				self.motor_angle -= 360 / self.resolution
	
	
	# Function to rotate the motor to a specified angle
	def rotate_to_angle(self, target_angle, delay):
		print(f"Rotation to {target_angle}°")
		
		if target_angle > 180:
			target_angle = 180
		elif target_angle < -180:
			target_angle = -180
		
		angle = target_angle - self.motor_angle
		steps = int((abs(angle) / 360) * self.resolution)
		
		if angle > 0:
			for _ in range(steps):
				for i in range(self.sequence_size-1):
					self.set_step(i)
					time.sleep_us(delay)
				self.motor_angle += 360 / self.resolution
		
		else:
			for _ in range(steps-1, -1, -1):
				for i in range(self.sequence_size-1, -1, -1):
					self.set_step(i)
					time.sleep_us(delay)
				self.motor_angle -= 360 / self.resolution




