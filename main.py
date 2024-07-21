import logging


#region configuration

http_server_ip = '0.0.0.0'
http_server_port = 3000

_socket_udp_ip = "127.0.0.1"
_socket_udp_port = 5000

uri_mongo = "mongodb://mongo_srv:27017/"

#endregion

#region http

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import pathlib
import mimetypes
import json

http_front_path = ""

class HttpProcessor(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file(f'{http_front_path}index.html')
        elif pr_url.path == '/message.html':
            self.send_html_file(f'{http_front_path}message.html')
        elif pr_url.path == '/success.html':
            self.send_html_file(f'{http_front_path}success.html')
        else:
            if pathlib.Path().joinpath(f'{http_front_path}{pr_url.path[1:]}').exists():
                self.send_static()
            else:
                self.send_html_file(f'{http_front_path}error.html', 404)

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(f'{http_front_path}{self.path}')
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'{http_front_path}{self.path}', 'rb') as file:
            self.wfile.write(file.read())
        
    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())
            
    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        data_parse = urllib.parse.unquote_plus(data.decode())
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
        send_via_socket(data_dict)
        self.send_html_file(f'{http_front_path}success.html')

def send_via_socket(message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = _socket_udp_ip, _socket_udp_port
    
    for line in f"@@{json.dumps(message)}##".split(" "):
        data = line.encode()
        sock.sendto(data, server)
        print(f"Send data: {data.decode()} to server: {server}")
        response, address = sock.recvfrom(1024)
        print(f"Response data: {response.decode()} from address: {address}")
    sock.close()

def http_listener(http_server_ip, http_server_port, server_class=HTTPServer, handler_class=HttpProcessor):
    print(f"http_listener started {http_server_ip}:{http_server_port}...")
    server_address = (http_server_ip, http_server_port)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()

def http_server():
    http_listener(http_server_ip, http_server_port)

#endregion

#region socket service

from datetime import datetime
import socket
from pymongo import MongoClient
import json

def socket_server():
    socket_listener(_socket_udp_ip, _socket_udp_port)

def socket_listener(ip, port):
    print(f"socket_listener started {ip}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    sock.bind(server)
    try:
        
        
        collected = ""
        
        while True:
            data, address = sock.recvfrom(1024)
            string_socket = data.decode()
            #print(f"Socket: Received data: {string_socket} from: {address}")
            sock.sendto(data, address)
            #print(f"Socket: Send data: {string_socket} to: {address}")
            
            if(string_socket.startswith("@@")):
                print(f"Socket: init collection")
                collected = ""
                collected += string_socket[2:]
            elif(string_socket.endswith("##")):
                collected += string_socket[:-2]
                print(f"Socket: finish collection")
                print(f"Socket: result: {collected}")
                print(f"Socket: save to db")
                save_to_db(collected)
                collected = ""
            else:
                print(f"Socket: collecting...")
                collected += string_socket

    except KeyboardInterrupt:
        print(f"Destroy server")
    finally:
        sock.close()

def save_to_db(data):
    client = MongoClient(uri_mongo)
    db = client['messager_db']
    collection = db['messages_collection']
    collection.insert_one(parse_message(json.loads(data)))

def parse_message(json_data):
    
    if not "datetime" in json_data:
        dt = str(datetime.now())
    else:
        dt = datetime.strptime(json_data["datetime"], "%Y-%m-%d %H:%M:%S.%f")
        
    return {
        'datetime': dt,
        'username': json_data["username"],
        'message': json_data["message"]
    }


#endregion

from multiprocessing import Process

if __name__ == "__main__":
    
    logging.basicConfig(level=logging.INFO, format="%(threadname)s - %(timestamp)s")
    
    print("Running http")
    
    http_server_process = Process(target=http_server)
    http_server_process.start()
    
    print("Running socket")
    socket_server_process = Process(target=socket_server)
    socket_server_process.start()
    
    
