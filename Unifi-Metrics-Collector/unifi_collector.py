import sys
import time
import re
import os
import configparser
from datetime import datetime, date
from influxdb import InfluxDBClient
from pyunifi import controller


# Logging Related
import logging
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                    stream=sys.stderr, level=logging.INFO)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


class unifi():
    """Provide device information support from Unifi stack."""

    def __init__(self, pyunifi_controller):
        """Initialize the probe."""
        self._controller = pyunifi_controller
        self._update()

    def _update(self):
        """Update function"""
        from pyunifi.controller import APIError
        try:
            stack = self._controller.get_aps()
            self._stack_info = {item['name']: item for item in stack}
        except APIError as err:
            logger.ERROR("Failed to update: " % err)
            pass

    def get_devices(self):
        """Collect unifi device name."""
        self._update()
        names = []
        for key in self._stack_info.keys():
            names.append(key)
        return names

    def get_stats(self, device_name):
        """Collect stats of device."""
        self._update()
        device_info = self._stack_info.get(device_name)
        stats = device_info.get('stat')
        stats_struc = {}
        for port, value in stats.items():
            stats_struc[port] = value
        return stats_struc


class influxdbConnection():
    """Class to connect to influxdb"""

    def __init__(self, host, port, user, password, dbname):
        client = InfluxDBClient(host, port, user, password, dbname)
        self._client = client

    def send_data(self, measurement, tags={}, fields={}):
        """Send data to influxdb."""
        json_body = [
            {
                'measurement': measurement,
                "tags": tags,
                "fields": fields
            }
        ]
        self._client.write_points(json_body)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        serial = obj.isoformat().split('.')
        return serial[0]
    raise TypeError("Type %s not serializable" % type(obj))


def parseConfig():
    config = configparser.ConfigParser()
    config.read(os.path.join(
                os.path.abspath(os.path.dirname(__file__)), 'config.ini'))
    configDict = {}
    for section in config.sections():
        config_section_items = {}
        for option in config[section]:
            config_section_items[option] = config.get(section, option)
            configDict[section] = config_section_items
    return configDict


def run():
    try:
        config = parseConfig()
        unifi_parm = config['Unifi']
        influx_parm = config['Influx']
    except Exception as err:
        logger.error('Config file error: ' % err)
        sys.exit(1)
    # Connect to Unifi Controller
    try:
        logger.info('Attempting connection to Unifi Controller.')
        if unifi_parm['ssl'] == 'True':
            ssl = True
        else:
            ssl = False
        unifi_obj = unifi(controller.Controller(unifi_parm['url'],
                                                unifi_parm['username'],
                                                unifi_parm['password'],
                                                site_id=unifi_parm['site_id'],
                                                version=unifi_parm['version'],
                                                ssl_verify=ssl))
    except Exception as err:
        logger.error('Unifi Controller error: ' % err)
        sys.exit(1)
    # Connect to Influx DB
    try:
        logger.info('Attempting connection to Influx DB.')
        influx_obj = influxdbConnection(influx_parm['url'],
                                        influx_parm['port'],
                                        influx_parm['username'],
                                        influx_parm['password'],
                                        influx_parm['database'])
    except Exception as err:
        logger.error('Influx DB error: ' % err)
        sys.exit(1)
    # Collect Unifi stack device names
    try:
        devices = unifi_obj.get_devices()
        logger.info("Unifi devices: " % devices)
    except Exception as err:
        logger.error('Failed to get Unifi stack devices: ' % err)
        sys.exit(1)
    # Loop through devices collecting stats
    while True:
        start_time = time.time()
        device_metrics = {}
        for device in devices:
            stats = unifi_obj.get_stats(device)
            numerical_stats = {}
            for stat, value in stats.items():
                if isinstance(value, float):
                    numerical_stats[stat] = value
                    stats = [numerical_stats]
            rx_port_metrics = {}
            tx_port_metrics = {}
            for measurement, value in numerical_stats.items():
                if (re.match('(port_[0-9]*)-rx_bytes', measurement)
                        is not None):
                    reg = re.search('(port_[0-9]*)', measurement)
                    port = reg.group(0).replace('_', ' ').capitalize()
                    rx_port_metrics[port] = value
                    stats.append(rx_port_metrics)
                elif (re.match('(port_[0-9]*)-tx_bytes', measurement)
                        is not None):
                    reg = re.search('(port_[0-9]*)', measurement)
                    port = reg.group(0).replace('_', ' ').capitalize()
                    tx_port_metrics[port] = value
                    stats.append(tx_port_metrics)
            device_metrics[device] = stats
        for device, stats in device_metrics.items():
            logger.info('Pushing "' + device + '" data to Influx')
            logger.debug(stats)
            influx_obj.send_data('{0}'.format(device),
                                 {'device': device, 'data': 'all'},
                                 stats[0])
            try:
                for port, value in stats[1].items():
                    influx_obj.send_data('unifi',
                                         {'device': device, 'port': port},
                                         {'rx-bytes': value})
                for port, value in stats[2].items():
                    influx_obj.send_data('unifi',
                                         {'device': device, 'port': port},
                                         {'tx-bytes': value})
            except Exception as err:
                logger.error(device.capitalize() + ' rx/tx error: ' + str(err))
        end_time = time.time()
        logger.debug('total time for this loop: ' +
                     str(end_time - start_time)[0:3] +
                     ' seconds.')
        logger.debug("Sleeping for " + unifi_parm['sleep'] + ' seconds.')
        time.sleep(int(unifi_parm['sleep']) - (end_time - start_time))


if __name__ == "__main__":
    run()
