# Example to send a packet periodically between addressed nodes
# Author: Jerry Needell
#
import time
import board
import busio
import digitalio 
import adafruit_rfm9x

TX0_PIN      = board.GP0
RX0_PIN      = board.GP1


uart = busio.UART(TX0_PIN, RX0_PIN, baudrate=9600)
# set the time interval (seconds) for sending packets
transmit_interval = 10

# Define radio parameters.
RADIO_FREQ_MHZ = 868.0  # Frequency of the radio in Mhz. Must match your
# module! Can be a value like 915.0, 433.0, etc.

# Define pins connected to the chip.
CS = digitalio.DigitalInOut(board.GP10)
RESET = digitalio.DigitalInOut(board.GP11)

# Initialize SPI bus.
#spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
spi = busio.SPI(board.GP18, MOSI=board.GP19, MISO=board.GP16)
# Initialze RFM radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)

# enable CRC checking
rfm9x.enable_crc = True
# set node addresses
rfm9x.node = 1
rfm9x.destination = 2
# initialize counter
counter = 0
ack_cntr = 0
# send a broadcast message from my_node with ID = counter
rfm9x.send(
    bytes("Startup message {} from node {}".format(counter, rfm9x.node), "UTF-8")
)

# Wait to receive packets.
print("Waiting for packets...")
now = time.monotonic()
while True:
    # uart.write("X1X2")
    # Look for a new packet: only accept if addresses to my_node
    packet = rfm9x.receive(with_header=True)
    # If no packet was received during the timeout then None is returned.
    if packet is not None:
        # Received a packet!
        # Print out the raw bytes of the packet:
        ack_cntr = ack_cntr + 1
        print("Received (raw header):", [hex(x) for x in packet[0:4]])
        print("Received (raw payload): {0}".format(packet[4:]))
        print("Received RSSI: {0}".format(rfm9x.last_rssi))
    if time.monotonic() - now > transmit_interval:
        now = time.monotonic()
        counter = counter + 1
        # send a  mesage to destination_node from my_node
        rfm9x.send(
            bytes(
                "message number {} from node {} ack_cntr {}".format(counter, rfm9x.node, ack_cntr), "UTF-8"
            ),
            keep_listening=True,
        )