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
data.my_node = data.NODE_REMOTE

uart = busio.UART(TX0_PIN, RX0_PIN, baudrate=9600)
# set the time interval (seconds) for sending packets
transmit_interval = 10

# Define radio parameters.
if data.my_radio == data.LORA_433:
    RADIO_FREQ_MHZ = 433.0  # Frequency of the radio in Mhz. Must match your
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
if data.my_node == data.NODE_BASE:
    rfm9x.node = 2
    rfm9x.destination = 1
elif data.my_node == data.NODE_REMOTE:
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
                 "<,A,R,2,P,10,N,0,S,0,T,0,>",
                 "<,Y,R,2,P,10,N,0,S,0,T,0,>",
                 "<,Z,R,2,P,10,N,0,S,0,T,0,>",
                 "<,B,R,2,P,10,N,0,S,0,T,0,>"]

def parse_radio_msg(line):
    try:
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
    except:
        print("parse_radio_msg failed: ", line)
        return None


def write_msg_to_uart(msg):
    tx_msg = "<,{},R,{},P,{},N,{},S,{},T,{},>\n".format(msg['msg_type'],msg['radio'], msg['pwr'], msg['nbr'],msg['base_rssi'],msg['remote_rssi'])
    print("BusMaster sending:", msg)
    uart.write(tx_msg.encode())

def exec_uart_cmd(cmd):
    print(cmd)
    cmd_str = cmd.strip().replace('\n','').replace('\r','')
    cmd = ""
    print("Received from UART:", cmd_str)
    uart.write(bytearray("Received".encode()))
    parsed = parse_radio_msg(cmd_str)
    ok2send = False
    if parsed is not None:
        print(parsed)
        if parsed['msg_type'] == data.MSG_SET_BASE_NODE:
            data.my_node = data.NODE_BASE
        elif parsed['msg_type'] == data.MSG_SET_REMOTE_NODE:
            data.my_node = data.NODE_REMOTE

        if parsed['radio'] == data.my_radio and parsed['pwr'] >= 5 and parsed['pwr'] <= 23: 
            rfm9x.tx_power = parsed['pwr']  
            print("base or remote")
            if data.my_node == data.NODE_BASE:
                print("send to remote")
                if parsed['msg_type'] == data.MSG_ACK_BASE_TO_REMOTE:
                    rfm9x.send(bytearray(cmd_str.encode()), keep_listening=True)
                    ok2send = True
            if data.my_node == data.NODE_REMOTE :
                print("send to base")
                if parsed['msg_type'] == data.MSG_SEND_REMOTE_TO_BASE:
                   rfm9x.send(bytearray(cmd_str.encode()), keep_listening=True)
                   ok2send = True
                    
        if not ok2send:
            print("Not for me to send")

def xparse_radio_msg():
    # Received a packet!
    # Print out the raw bytes of the packet:
    ack_cntr = ack_cntr + 1
    print("Received (raw header):", [hex(x) for x in packet[0:4]])
    print("Received (raw payload): {0}".format(packet[4:]))
    print("Received RSSI: {0}".format(rfm9x.last_rssi))
    parsed_received = parse_radio_msg(packet[4:].decode('utf-8'))
    #radio_reply = parse_radio_reply(packet[4:].decode('utf-8'), rfm9x.last_rssi)
    if parsed_received is not None:
        print(parsed_received)
        if data.my_node == data.NODE_BASE:
            if parsed_received['msg_type'] == data.MSG_SEND_REMOTE_TO_BASE:
                write_msg_to_uart(parsed_received)
                
                
        if data.my_node == data.NODE_REMOTE :
             if parsed_received['msg_type'] == data.MSG_ACK_BASE_TO_REMOTE:
                 write_msg_to_uart(parsed_received)

     
      
      
print("LoRa simple modem for range testing: ",data.radio_labels[data.my_radio])

cmd = ""

new_state = 0
state = new_state
    

timeout = time.monotonic() + 4.0

while True:
    if new_state != state:
        print(state,'->',new_state)
        state = new_state
        
        
    if state == 0:
        if data.my_node == data.NODE_BASE:
            new_state = 5
        else:
            new_state = 20

    if state == 5:
        d = uart.read(1)
        if d is not None:
            c = d.decode()
            if c == '<':
               cmd = '<'
               new_state = 6
               
               
    elif state == 6:
        d = uart.read(1)
        if d is not None:
            c = d.decode()
            if c == '>':
               new_state = 10
            cmd = cmd + c

    elif state == 10:  # parse uart command and send via radio
        exec_uart_cmd(cmd)
        new_state = 20
        timeout =time.monotonic() + 2.0    
    
    elif state == 20:
        packet = rfm9x.receive(with_header=True)
        # If no packet was received during the timeout then None is returned.
        if packet is not None:
            new_state = 30
        elif time.monotonic() > timeout:
            new_state = 0
            
    elif state == 30:
        parse_radio_msg()
        # Received a packet!
        # Print out the raw bytes of the packet:
        ack_cntr = ack_cntr + 1
        print("Received (raw header):", [hex(x) for x in packet[0:4]])
        print("Received (raw payload): {0}".format(packet[4:]))
        print("Received RSSI: {0}".format(rfm9x.last_rssi))
        parsed_received = parse_radio_msg(packet[4:].decode('utf-8'))
        #radio_reply = parse_radio_reply(packet[4:].decode('utf-8'), rfm9x.last_rssi)
        if parsed_received is not None:
            print(parsed_received)
            if data.my_node == data.NODE_BASE:
                if parsed_received['msg_type'] == data.MSG_SEND_REMOTE_TO_BASE:
                    write_msg_to_uart(parsed_received)
                    
                    
            if data.my_node == data.NODE_REMOTE :
                 if parsed_received['msg_type'] == data.MSG_ACK_BASE_TO_REMOTE:
                     write_msg_to_uart(parsed_received)
        new_state = 5



          
    '''
    if state == 2:
        print(cmd)
        cmd_str = cmd.strip().replace('\n','').replace('\r','')
        cmd = ""
        print("Received from UART:", cmd_str)
        uart.write(bytearray("Received".encode()))
        parsed = parse_radio_msg(cmd_str)
        ok2send = False
        if parsed is not None:
            print(parsed)
            if parsed['msg_type'] == data.MSG_SET_BASE_NODE:
                data.my_node = data.NODE_BASE
            elif parsed['msg_type'] == data.MSG_SET_REMOTE_NODE:
                data.my_node = data.NODE_REMOTE

            if parsed['radio'] == data.my_radio and parsed['pwr'] >= 5 and parsed['pwr'] <= 23: 
                rfm9x.tx_power = parsed['pwr']  
                print("base or remote")
                if data.my_node == data.NODE_BASE:
                    print("send to remote")
                    if parsed['msg_type'] == data.MSG_ACK_BASE_TO_REMOTE:
                        rfm9x.send(bytearray(cmd_str.encode()), keep_listening=True)
                        ok2send = True
                if data.my_node == data.NODE_REMOTE :
                    print("send to base")
                    if parsed['msg_type'] == data.MSG_SEND_REMOTE_TO_BASE:
                       rfm9x.send(bytearray(cmd_str.encode()), keep_listening=True)
                       ok2send = True
                        
            if not ok2send:
                print("Not for me to send")
         
    '''
    '''
    packet = rfm9x.receive(with_header=True)
    # If no packet was received during the timeout then None is returned.
    if packet is not None:
        # Received a packet!
        # Print out the raw bytes of the packet:
        ack_cntr = ack_cntr + 1
        print("Received (raw header):", [hex(x) for x in packet[0:4]])
        print("Received (raw payload): {0}".format(packet[4:]))
        print("Received RSSI: {0}".format(rfm9x.last_rssi))
        parsed_received = parse_radio_msg(packet[4:].decode('utf-8'))
        #radio_reply = parse_radio_reply(packet[4:].decode('utf-8'), rfm9x.last_rssi)
        if parsed_received is not None:
            print(parsed_received)
            if data.my_node == data.NODE_BASE:
                if parsed_received['msg_type'] == data.MSG_SEND_REMOTE_TO_BASE:
                    write_msg_to_uart(parsed_received)
                    
                    
            if data.my_node == data.NODE_REMOTE :
                 if parsed_received['msg_type'] == data.MSG_ACK_BASE_TO_REMOTE:
                     write_msg_to_uart(parsed_received)

'''
 
while True:
    # uart.write("X1X2")
    # Look for a new packet: only accept if addresses to my_node
    #cmd_str = "<,B,R,2,P,10,N,0,S,0,T,0,>\n"
    #barray = bytearray("#-#".encode())
    #uart.write(barray)
    #if uart.in_waiting > 0:
    #    uart.write(bytearray("*!*".encode()))
    #    print("-------------------------------------------------------")
    #    #for line in test_messages:   
         
        #line = uart.readline()
    line = uart.readline()  # read(80)
    if line is not None:
        
        cmd_str = ''.join([chr(c) for c in line])
        # cmd_str = "<,B,R,2,P,10,N,0,S,0,T,0,>\n" 
        print("cmd_str: ", cmd_str)
        cmd_str = cmd_str.strip().replace('\n','').replace('\r','')
        print("Received from UART:", cmd_str)
        uart.write(bytearray("Received".encode()))
        parsed = parse_radio_msg(cmd_str)
        ok2send = False
        if parsed is not None:
            print(parsed)
            if parsed['msg_type'] == data.MSG_SET_BASE_NODE:
                data.my_node = data.NODE_BASE
            elif parsed['msg_type'] == data.MSG_SET_REMOTE_NODE:
                data.my_node = data.NODE_REMOTE

            if parsed['radio'] == data.my_radio and parsed['pwr'] >= 5 and parsed['pwr'] <= 23: 
                rfm9x.tx_power = parsed['pwr']  
                print("base or remote")
                if data.my_node == data.NODE_BASE:
                    print("send to remote")
                    if parsed['msg_type'] == data.MSG_ACK_BASE_TO_REMOTE:
                        rfm9x.send(bytearray(cmd_str.encode()), keep_listening=True)
                        ok2send = True
                if data.my_node == data.NODE_REMOTE :
                    print("send to base")
                    if parsed['msg_type'] == data.MSG_SEND_REMOTE_TO_BASE:
                       rfm9x.send(bytearray(cmd_str.encode()), keep_listening=True)
                       ok2send = True
                        
            if not ok2send:
                print("Not for me to send")
        if True:   #read LoRa radio messages
            packet = rfm9x.receive(with_header=True)
            # If no packet was received during the timeout then None is returned.
            if packet is not None:
                # Received a packet!
                # Print out the raw bytes of the packet:
                ack_cntr = ack_cntr + 1
                print("Received (raw header):", [hex(x) for x in packet[0:4]])
                print("Received (raw payload): {0}".format(packet[4:]))
                print("Received RSSI: {0}".format(rfm9x.last_rssi))
                parsed_received = parse_radio_msg(packet[4:].decode('utf-8'))
                #radio_reply = parse_radio_reply(packet[4:].decode('utf-8'), rfm9x.last_rssi)
                if parsed_received is not None:
                    print(parsed_received)
                    if data.my_node == data.NODE_BASE:
                        if parsed_received['msg_type'] == data.MSG_SEND_REMOTE_TO_BASE:
                            write_msg_to_uart(parsed_received)
                            
                            
                    if data.my_node == data.NODE_REMOTE :
                         if parsed_received['msg_type'] == data.MSG_ACK_BASE_TO_REMOTE:
                             write_msg_to_uart(parsed_received)
    time.sleep(0.5)
