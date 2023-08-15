# rest4mqtt

[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/raven-worx/rest4mqtt?logo=github&sort=semver)](https://github.com/raven-worx/rest4mqtt/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](/LICENSE)

rest4mqtt is a simple REST-like proxy to access MQTT data (python3). This might be useful in situation where MQTT is not available. 

The webserver provides the specified topics on the same path as the topic path is. E.g. the subscribed topic `my/topic/data` is accessible on `http://my.rest4mqtt.server:8080/my/topic/data` via a HTTP GET request. Same for publishing topics, which can be written using a HTTP POST request. 

For install instructions using a Debian package (Debian, Ubuntu, RaspberryPi, ...) see the latest release entry.

### Settings

| **Option**            | Default value | **Description**         |
| --------------------- | ------------- | ----------------------- |
| **[www]**             |               | Webserver settings      |
| host                  | 0.0.0.0       | Specifies the network interface the webserver should be launched on. E.g. `0.0.0.0` means the server is reachable from any device inside the network, `127.0.0.1` only locally from the device itself. |
| port                  | 8080          | The port the webserver should be accessible on |
| user                  |               | If set requires HTTP authentication (Basic) to GET/POST data |
| pass                  |               | If set requires HTTP authentication (Basic) to GET/POST data |
| **[mqtt]**            |               | MQTT client settings    |
| host                  | 127.0.0.1     | The network address or hostname of the mqtt broker to connect to |
| port                  | 1883          | The port of the MQTT broker |
| user                  |               | If set uses user credentials authentication when connecting to MQTT broker |
| pass                  |               | If set uses user credentials authentication when connecting to MQTT broker |
| sub                   |               | A whitespace separated list of topics on the broker which should be accessible via HTTP GET requests. Multiline entries are supported, just use the same indentation for each entry |
| pub                   |               | A whitespace separated list of topics on the broker which should be publishable via HTTP POST requests. Multiline entries are supported, just use the same indentation for each entry | 

Edit the settings file and afterwards restart the system service:

````
sudo nano /etc/rest4mqtt/rest4mqtt.conf
sudo systemctl restart rest4mqtt.service
````

# License

Licensed under [GPLv3](/LICENSE)
