#!/usr/bin/env -S python3 -u

from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer
import paho.mqtt.client as mqtt
import logging
import threading
import os
import sys
import traceback
import configparser
import random
import base64

try:
	with open(os.path.abspath(os.path.dirname(__file__))+"/VERSION", 'r') as f:
		VERSION = f.read().rstrip()
except:
	VERSION = "0.0"

# data cache of received mqtt topic messages for serving via webserver
data_cache = dict()
# for publishing enabled topics
pub_topics = set()

### LOGGING
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

### MQTT
def on_mqtt_message(client, userdata, message):
	logger.debug("mqtt message received: topic='%s', message='%s' qos=%d, retain=%d", message.topic, str(message.payload.decode("utf-8")), message.qos, message.retain)
	data_cache["/"+message.topic] = str(message.payload.decode("utf-8"))

### HTTP
class HTTPRequestHandler(SimpleHTTPRequestHandler):
	server_version = "REST4MQTT/" + VERSION

	def do_HEAD(self):
		self.send_response(405) # Method Not Allowed
		self.send_header('Connection', 'close')
		self.end_headers()
	
	def do_POST(self):
		if self.server.need_auth() and not self.headers.get('Authorization'):
			self.send_response(401) # Unauthorized
			self.send_header('WWW-Authenticate', 'Basic realm="REST4MQTT"')
			self.send_header('Connection', 'close')
			self.end_headers()
		if not self.server.check_auth(self.headers.get('Authorization')):
			self.send_response(403) # Forbidden
			self.send_header('Connection', 'close')
			self.end_headers()
		elif self.path in pub_topics:
			length = int(self.headers.get('content-length', 0))
			payload = self.rfile.read(length).decode('utf-8')
			logger.debug("http POST: len: %d, data: %s", length, payload)
			ret = self.server.mqtt_publish(self.path[1:], payload)
			self.send_response(ret)
			self.send_header('Connection', 'close')
			self.end_headers()
		else:
			logger.warning("POST '%s' not found", self.path)
			self.send_response(404) # Not Found
			self.send_header('Connection', 'close')
			self.end_headers()
	
	def do_GET(self):
		if self.server.need_auth() and not self.headers.get('Authorization'):
			self.send_response(401) # Unauthorized
			self.send_header('WWW-Authenticate', 'Basic realm="REST4MQTT"')
			self.send_header('Connection', 'close')
			self.end_headers()
		if not self.server.check_auth(self.headers.get('Authorization')):
			self.send_response(403) # Forbidden
			self.send_header('Connection', 'close')
			self.end_headers()
		elif self.path in data_cache:
			logger.debug("GET '%s':\n%s", self.path, str(data_cache[self.path]))
			if data_cache[self.path] is None:
				self.send_response(204) # No Content
				self.send_header('Connection', 'close')
				self.end_headers()
			else:
				response_data = data_cache[self.path].encode('utf8')
				self.send_response(200) # OK
				self.send_header('Content-length', str(len(response_data)))
				self.send_header('Connection', 'close')
				self.end_headers()
				self.wfile.write(response_data)
		else:
			logger.warning("GET '%s' not found", self.path)
			self.send_response(404) # Not Found
			self.send_header('Connection', 'close')
			self.end_headers()
	
	def do_DELETE(self):
		self.send_response(405) # Method Not Allowed
		self.send_header('Connection', 'close')
		self.end_headers()


class CustomHTTPServer(ThreadingMixIn, HTTPServer):
	auth = None
	mqtt_client = None
	
	def __init__(self, address, handlerClass=HTTPRequestHandler):
		super().__init__(address, handlerClass)
	
	def set_mqtt_client(self, mqtt_client):
		self.mqtt_client = mqtt_client
	
	def set_auth(self, username, password):
		if not username and not password:
			return
		self.auth = "Basic " + base64.b64encode(bytes('%s:%s' % (username, password), 'utf-8')).decode('ascii')
		logger.debug("set_auth: '{}:{}' -> {}".format(username,password,self.auth))
	
	def check_auth(self, auth):
		if not self.need_auth():
			return True
		elif auth == None:
			return False
		else:
			return self.auth == auth
	
	def need_auth(self):
		return bool(self.auth)
		
	def mqtt_publish(self, topic, payload=None, qos=0, retain=False):
		if not self.mqtt_client:
			return 500
		try:
			res = self.mqtt_client.publish(topic, payload, qos, retain)
			if not res.is_published():
				res.wait_for_publish()
			if res.is_published():
				logger.info("successfully published to topic: '" + topic + "'")
				return 200
			else:
				return 500
		except Exception as e:
			logger.error("error publishing to topic '" + topic + "': " + str(e))
			return 500


def main():
	logger.setLevel(logging.INFO)
	
	# CONFIG
	conf_path = os.getenv("CONFIGURATION_DIRECTORY") + "/rest4mqtt.conf"
	logger.info("config file: " + conf_path)
	config = configparser.ConfigParser()
	try:
		with open(conf_path) as f:
			config.read_file(f)
	except IOError as e:
		logger.error("unable to read config file: '" + conf_path + "' (check if CONFIGURATION_DIRECTORY env variable is set correctly)")
		raise e
	
	www_address = config['www'].get('host', fallback='0.0.0.0')
	www_port = config['www'].getint('port', fallback=8080)
	www_user = config['www'].get('user', fallback='').strip()
	www_pass = config['www'].get('pass', fallback='').strip()
	mqtt_host = config['mqtt'].get('host', fallback='127.0.0.1')
	mqtt_port = config['mqtt'].getint('port', fallback=1883)
	mqtt_user = config['mqtt'].get('user', fallback='').strip()
	mqtt_pass = config['mqtt'].get('pass', fallback='').strip()
	mqtt_subs = config['mqtt'].get('sub').split()
	mqtt_pubs = config['mqtt'].get('pub').split()
	
	# INIT MQTT
	client_id = "rest4mqtt-"
	for i in range(1,8):
		client_id += str(random.randint(0,9))
	client = mqtt.Client(client_id)
	client.enable_logger(logger)
	client.on_message=on_mqtt_message
	if mqtt_user:
		client.username_pw_set(mqtt_user, mqtt_pass)
	client.connect(mqtt_host, mqtt_port)
	client.loop_start()
	
	for pub in mqtt_pubs:
		if not pub or "+" in pub or "#" in pub:
			logger.warning("ignoring unsupported topic for publishing: '" + pub + "'")
			continue
		logger.info("enabling publishing to topic: '" + pub + "'")
		pub_topics.add("/"+pub)
	
	for sub in mqtt_subs:
		if not sub or "+" in sub or "#" in sub:
			logger.warning("ignoring subscription to unsupported topic: '" + sub + "'")
			continue
		logger.info("subscribing to topic: '" + sub + "'")
		client.subscribe(sub)
		data_cache["/"+sub] = None
	
	# INIT HTTP
	server = CustomHTTPServer((www_address, www_port))
	server.set_auth(www_user, www_pass)
	server.set_mqtt_client(client)
	
	logger.info("REST4MQTT v" + VERSION + " -  HTTP Server running on " + www_address + ":" + str(www_port) + ", MQTT client connecting to broker on " + mqtt_host + ":" + str(mqtt_port))
	
	server.serve_forever()

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print("Shutdown requested.")
	except Exception:
		traceback.print_exc(file=sys.stdout)
	
	logger.info("Exiting...")
