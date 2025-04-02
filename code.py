# Example to send a packet periodically between addressed nodes
# Author: Jerry Needell
#
'''

Set Radio Type:     "<,X,R,2,P,10,N,0,S,0,T,0,>\n"

Set Radio Type:     "<,B,R,2,P,14,N,0,S,0,T,0,>\n"
Set Radio Type:     "<,X,R,1,P,10,N,0,S,0,T,0,>\n"

Send to base node:  bus_msg = "<,B,R,{},P,{},N,{},S,{},T,{},>\n"
                        .format(pmsg['radio'], pmsg['pwr'], pmsg['nbr'],pmsg['base_rssi'],pmsg['remote_rssi']
Ack to remote node: bus_msg = "<,Y,R,{},P,{},N,{},S,{},T,{},>\n"
                        .format(pmsg['radio'], pmsg['pwr'], pmsg['nbr'],pmsg['base_rssi'],pmsg['remote_rssi']

'''

import time
import board
import busio
import digitalio
import adafruit_rfm9x
import data

TX0_PIN      = board.GP0
RX0_PIN      = board.GP1

data.my_radio = data.LORA_868

uart = busio.UART(TX0_PIN, RX0_PIN, baudrate=9600)
# set the time interval (seconds) for sending packets
transmit_interval = 10

# Define radio parameters.
if data.my_radio == data.LORA_433:
    RADIO_FREQ_MHZ = 868.0  # Frequency of the radio in Mhz. Must match your
elif data.my_radio == data.LORA_868:
    RADIO_FREQ_MHZ = 868.0  # Frequency of the radio in Mhz. Must match your
# module! Can be a value like 915.0, 433.0, etc.

# Define pins connected to the chip.
CS = digitalio.DigitalInOut(board.GP10)
RESET = digitalio.DigitalInOut(board.GP11)

# Initialize SPI bus.
spi = busio.SPI(board.GP18, MOSI=board.GP19, MISO=board.GP16)
# Initialze RFM radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)

# enable CRC checking
rfm9x.enable_crc = True
# set node addresses
rfm9x.node = 1
rfm9x.destination = 2
rfm9x.tx_power = 20
# initialize counter
counter = 0
ack_cntr = 0
# send a broadcast message from my_node with ID = counter
rfm9x.send(
    bytes("Startup message {} from node {}".format(counter, rfm9x.node), "UTF-8")
)

test_messages = ["<,A,R,2,P,10,N,0,S,0,T,0,>",
                 "<,B,R,2,P,10,N,0,S,0,T,0,>",
                 "<,B,R,1,P,10,N,0,S,0,T,0,>",
                 "<,Y,R,2,P,10,N,0,S,0,T,0,>",
                 "<,X,R,2,P,10,N,0,S,0,T,0,>",
                 "<,Y,R,2,P,10,N,0,S,0,T,0,>",
                 "<,Z,R,2,P,10,N,0,S,0,T,0,>",
                 "<,B,R,2,P,10,N,0,S,0,T,0,>"]

def parse_radio_msg(line):
    line = line.replace('\n','')
    line = line.replace('\r','')
    lst = line.split(',')
    print(lst)  
    # <','B','R', '3', 'P', '20', 'N', '345', 'T', '-99','S', '-68', '>', '\n']
    #print(lst)
    if (lst[0] == data.MSG_START and 
        lst[2] == 'R' and 
        lst[4] == 'P' and 
        lst[6] == 'N' and
        lst[8] == 'S' and 
        lst[10] == 'T' and
        lst[12] == data.MSG_END):  
        cmd = {'msg_type':lst[1] ,
               'radio': int(lst[3]), 
               'pwr': int(lst[5]), 
               'nbr': int(lst[7]), 
               'base_rssi': int(lst[9]),
               'remote_rssi': int(lst[11])}
        return cmd
    else:
        return None

    if lst[0] == '<' and lst[7] == '>':      
        print("Received valid command")
        pars = {'radio': int(lst[2]), 'tx_power':int(lst[4]), 'msg_nbr': int(lst[6])}
        print(pars)
        return pars
    
def parse_radio_reply(line,center_rssi):
    lst = line.split(',')
    print(lst)  
    if lst[0] == '(' and lst[9] == ')':      
        print("Received valid command")
        pars = {'radio': int(lst[2]), 
                'tx_power':int(lst[4]), 
                'msg_nbr': int(lst[6]),
                'remote_rssi': int(lst[8]),
                'center_rssi': center_rssi}
        print(pars)
        return pars
    

print("LoRa simple modem for range testing: ",data.radio_labels[data.my_radio])

while True:
    # uart.write("X1X2")
    # Look for a new packet: only accept if addresses to my_node
    #line = "<,B,R,2,P,10,N,0,S,0,T,0,>\n"
    #if True:    #uart.in_waiting > 0:
    print("-------------------------------------------------------")
    for line in test_messages:    
        #line = uart.readline().decode('utf-8').strip()
        print("Received from UART:", line)
        parsed = parse_radio_msg(line)
        ok2send = False
        if parsed is not None:
            print(parsed)
            if parsed['msg_type'] == data.MSG_SET_BASE_NODE:
                data.my_node = data.NODE_BASE
            elif parsed['msg_type'] == data.MSG_SET_REMOTE_NODE:
                data.my_node = data.NODE_REMOTE

            if parsed['radio'] == data.my_radio and parsed['pwr'] >= 5 and parsed['pwr'] <= 23: 
                rfm9x.tx_power = parsed['pwr']  

                if data.my_node == data.NODE_BASE:
                    if parsed['msg_type'] == data.MSG_ACK_BASE_TO_REMOTE:
                        rfm9x.send(bytes(line,'utf-8'), keep_listening=True)
                        ok2send = True

                if data.my_node == data.NODE_REMOTE :
                    if parsed['msg_type'] == data.MSG_SEND_REMOTE_TO_BASE:
                       rfm9x.send(bytes(line,'utf-8'), keep_listening=True)
                       ok2send = True
                        
        if not ok2send:
            print("Not for me to send")
        else:    
            packet = rfm9x.receive(with_header=True)
            # If no packet was received during the timeout then None is returned.
            if packet is not None:
                # Received a packet!
                # Print out the raw bytes of the packet:
                ack_cntr = ack_cntr + 1
                print("Received (raw header):", [hex(x) for x in packet[0:4]])
                print("Received (raw payload): {0}".format(packet[4:]))
                print("Received RSSI: {0}".format(rfm9x.last_rssi))
                radio_reply = parse_radio_reply(packet[4:].decode('utf-8'), 'B')
                #radio_reply = parse_radio_reply(packet[4:].decode('utf-8'), rfm9x.last_rssi)
                if radio_reply is not None:
                    print(radio_reply)
                    radio_reply_ack ="<,Y,R,{},P,{},N,{},S,{},T,{},>".format(radio_reply['radio'],
                                                                radio_reply['tx_power'],
                                                                radio_reply['msg_nbr'],
                                                                radio_reply['remote_rssi'],
                                                                rfm9x.last_rssi
                                                                )
                    #uart.write(radio_reply_ack)
                    #print(radio_reply_ack)

        time.sleep(10)

    '''
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
        '''