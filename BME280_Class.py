from machine import I2C, Pin
from struct import unpack
from time import sleep

# Define the following constants to access the registers in the BME280 chip
# Using the const expression saves memoy in the microcontroller
# The meaning of the various registers is explained in the data sheet.

BME_ADR = const(0x77)             # This is the I2C address of the chip

BME_REG_CHIP_ID     = const(0xD0) # This register holds an identification code (0x60)
BME_REG_RESET       = const(0xE0)

# Registers to define details on how the measurements should be performed and
# registers to trigger the actual measurement. 
BME_REG_CRTL_HUM    = const(0xF2) # 5 : oversampling 16
BME_REG_STATUS      = const(0xF3)
BME_REG_CTRL_MEAS   = const(0xF4)
BME_REG_CTRL_CONFIG = const(0xF5)

# Registers which hold the result of a measurement:
BME_REG_PRESS       = const(0xF7) # adr F7 ... F9 are 20 bits pressure (big endian)
                                  # F9 bits 4..7 are the most significant 4 bits)
BME_REG_TEMP        = const(0xFA) # adr FA ... FC contains the 20 bits for temperature
BME_REG_HUM         = const(0xFD) # adr FD and FE contain 16 bits of Humidity


##########################################################################
class BME280 :
##########################################################################

    def __init__( self, i2c ):

        self.i2c = i2c
        self.readCalib()
        self.initSensor()


    # Initialize the sensor for single measurements between sleeps.
    # The maximum amount of oversampling is requested to achieve maximal precision.
    def initSensor( self ):

        # Set the chip to sleep mode
        # Set the pressure oversampling to 16
        # Set the temerature oversampling to 16
        self.i2c.writeto_mem( BME_ADR, BME_REG_CTRL_MEAS, b'\xB4' )

        # Set the oversampling of the pressure measurement to 16
        self.i2c.writeto_mem( BME_ADR, BME_REG_CRTL_HUM, b'\x05' )  


    # Calibration data needs to be read out of the chip (see below the 
    # function "readCalib"). What follows here is a set of helper functions
    # which read single calibration constants our of the memory of the 
    # sensor chip. The format of the the constants can be different
    # (signed or unsigned short (2 byte values) or signed or unsigned char
    # (one byte values)). There is a dedicated function for all of these four
    # types which converts the read bytes into the appropriate python type.
    #
    # The readfrom_mem function reads a number of bytes via i2c into a
    # python "bytes" object. Essentially this is an array of single bytes.
    # To turn a bytes object into a python number the struct.unpack function 
    # is used. It is documented in the python documentation:
    # https://docs.python.org/3.5/library/struct.html?highlight=unpack#struct.unpack
    # If you do not understand how the unpack works, please ask !!!
    #
    # Fill in the ???
    def _readSignedShort( self, adr ):
        tmp = self.i2c.readfrom_mem( BME_ADR, adr, 2 )
        return unpack('<h', tmp)[0]

    def _readUnsignedShort( self, adr ):
        tmp = self.i2c.readfrom_mem( BME_ADR, adr, 2 )
        return unpack('<H',tmp)[0]

    def _readUnsignedChar( self, adr ):
        tmp = self.i2c.readfrom_mem(BME_ADR, adr, 1)
        return unpack('<B',tmp)[0]

    def _readSignedChar( self, adr ):
        tmp = self.i2c.readfrom_mem(BME_ADR, adr, 1)
        return unpack('<b',tmp)[0]



    # Read the calibration data which has been programmed into the chip.
    # Due to production tolerances not every sensor gives exactly the same
    # value at a given temperature/pressure/humidity. At the factory every
    # sensor is calibrated and the calibration constants are programmed
    # into the chip (they cannot be changed afterwards). We read out these
    # constants here, since we need them to calculate calibrated 
    # (i.e. 'correct') sensor values.
    #
    def readCalib( self ):
        calib={}
        calib['T1'] = self._readSignedShort( 0x88 )
        calib['T2'] = self._readSignedShort( 0x8A )
        calib['T3'] = self._readSignedShort( 0x8C )
        calib['P1'] = self._readUnsignedShort( 0x8E )
        calib['P2'] = self._readSignedShort( 0x90 )
        calib['P3'] = self._readSignedShort( 0x92 )
        calib['P4'] = self._readSignedShort( 0x94 )
        calib['P5'] = self._readSignedShort( 0x96 )
        calib['P6'] = self._readSignedShort( 0x98 )
        calib['P7'] = self._readSignedShort( 0x9A )
        calib['P8'] = self._readSignedShort( 0x9C )
        calib['P9'] = self._readSignedShort( 0x9E )
        calib['H1'] = self._readUnsignedChar( 0xA1 )
        calib['H2'] = self._readSignedShort( 0xE1 )
        calib['H3'] = self._readUnsignedChar( 0xE3 )

        # The following two constants need extra treatment.
        # For some (not obvious) reason, the chip producer decided 
        # to pack the following 2 values into three bytes of which
        # one of the bytes contains bits belonging to both fo the
        # constants. Hence some fiddling around with the bits is
        # needed in order to extract the two callibration values:

        tmp = self.i2c.readfrom_mem( BME_ADR, 0xE4, 2 )
        calib['H4'] = (int(tmp[0]))<<4 + (int(tmp[1])&0xf)
        tmp = self.i2c.readfrom_mem( BME_ADR, 0xE5, 2 )
        calib['H5'] = (int(tmp[0]) & 0xF0 ) >> 4 + (int(tmp[1]) << 4 )

        calib['H6'] = self._readSignedChar( 0xE7 )

        self.calib = calib


    # The formulas of the following calculations come from the data sheet.
    #
    # Calculate the Temperature with help of the calibration data
    def calcTemp( self, adc_T ):
        var1 = ( ( ( (adc_T>>3) - (self.calib['T1']<<1) ) * self.calib['T2'] ) ) >> 11
        var2 = (((((adc_T>>4) - (self.calib['T1'])) * ((adc_T>>4) - (self.calib['T1']))) >> 12) * (self.calib['T3'])) >> 14
        t_fine = var1 + var2
        T = (t_fine * 5 + 128) >> 8
        self.t_fine = t_fine
        return T

    # Calculate the pressure with help of the calibration data
    # This calculation includes a temperature correction.
    def calcPress( self, adc_P ):

        #BME280_S64_t var1, var2, p;
        var1 = self.t_fine - 128000;
        var2 = var1 * var1 * self.calib['P6'];
        var2 = var2 + ((var1*self.calib['P5'])<<17);
        var2 = var2 + ((self.calib['P4'])<<35);
        var1 = ((var1 * var1 * self.calib['P3'])>>8) + ((var1 * self.calib['P2'])<<12);
        var1 = ((1<<47)+var1)*(self.calib['P1'])>>33;

        if (var1 == 0):
            return 0;
        # avoid exception caused by division by zero }
        p = 1048576-adc_P;
        p = int( (((p<<31)-var2)*3125)/var1 );
        var1 = ((self.calib['P9']) * (p>>13) * (p>>13)) >> 25;
        var2 = ((self.calib['P8']) * p) >> 19;
        p = ((p + var1 + var2) >> 8) + ((self.calib['P7'])<<4);
        return p/25600

    # Calucalate the humidity with help of the calibration data
    # This calculation includes a temperature correction 
    def calcHum( self, adc_H ):

        v_x1_u32r = self.t_fine - 76800;
        v_x1_u32r = (((((adc_H << 14) - ((self.calib['H4']) << 20) - ((self.calib['H5']) * v_x1_u32r)) + 16384) >> 15) * (((((((v_x1_u32r * self.calib['H6']) >> 10) * (((v_x1_u32r * self.calib['H3']) >> 11) + 32768)) >> 10) + 2097152) * self.calib['H2'] + 8192) >> 14))
        v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * self.calib['H1']) >> 4))
        if v_x1_u32r < 0 :
            v_x1_u32r =  0
        if v_x1_u32r > 419430400 :
            v_x1_u32r = 419430400
        return(v_x1_u32r>>12)


    # Do the measurements of Temperature, Pressure and Humidity
    def doMeasure( self ):
        # Leave the oversampling values as defined in the init routine but wake up the chip into "forced mode".
        # This means the chip is exactly performing one measurement and then returns to sleep mode.
        self.i2c.writeto_mem(  BME_ADR, BME_REG_CTRL_MEAS, b'\xB5' )

        # Here we wait until the measurement is done.
        # The bit 3 is '1' when a measurement is ongoing. It goes to '0' once the
        # measurement is completed and results are ready for reading out.
        # What we program here is called a "polling loop": we read a value over and
        # over again and wait until it's value changes to the expected value. Then
        # we leave the loop.
        measuring = 8
        while measuring == 8:
            sleep(0.1)
            measuring = int(self.i2c.readfrom_mem( BME_ADR, BME_REG_STATUS, 1 )[0]) & 8


        # Now we read out the measurements. The values are raw values which need to
        # be transformed via formulas into Temperature, Pressure and Humidity values.
        # The formulas involve calibration constants. In addition the raw measurement
        # value depend on each other (i.e. the raw values for humidity and pressure
        # are temperature dependent. This dependency is known and worked into to the
        # forumalas for the calculation.

        # read temperature
        temp = self.i2c.readfrom_mem( BME_ADR, BME_REG_TEMP, 3 )
        T = int(temp[0]<<12)+int(temp[1]<<4)+int(temp[2]>>4)
        self.lastT = self.calcTemp( T ) / 100.

        # read pressure
        press = self.i2c.readfrom_mem( BME_ADR, BME_REG_PRESS, 3 )
        P = int(press[0]<<12)+int(press[1]<<4)+int(press[2]>>4)
        self.lastP = self.calcPress( P )

        # read humidity
        hum = self.i2c.readfrom_mem( BME_ADR, BME_REG_HUM, 2 )
        H = int(hum[0]<<8)+int(hum[1])
        self.lastH = self.calcHum( H ) / 1000.

        return( self.lastT, self.lastP, self.lastH )


    def getAltitude( self ):
        # 1013.24 is the reference pressure at sealevel
        # This formula is an approximation, of course. But it is useful
        # to calculate altitude differences (e.g. in a model airplane).
        # You should be able to see altitude differences when holding the
        # Sensor at different heights (1-2 meters of difference should be
        # visible. To make it more obvious sample over multiple measurements
        # and take the mean

        return ( 44330 * ( 1.0 - (self.lastP / 1013.25 )**(1.0 / 5.255)) )
		

    def dumpLastMeasurement( self ):

        print( "Temperature : %7.2f C"  % self.lastT )
        print( "Pressure    : %7.2f mb" % self.lastP )
        print( "Humidity    : %7.2f %%" % self.lastH )
        print()
#############################################################################

