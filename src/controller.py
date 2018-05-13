'''controller
a subproblem of this project
how-to-run:
$ python3 controller.py ../test/routeA.json
'''
import sys
import json
import threading
import logging
import time

import route
import console
from NetworkLayerListerner import NetworkLayerListener

CONFIG_NAME = sys.argv[1]

logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def main():
    '''main'''
    # open file
    f = open(CONFIG_NAME, 'rt')
    config_data = json.load(f)
    f.close()

    network_layer = route.NetworkLayer(config_data)
    network_layer_listener = NetworkLayerListener(network_layer)
    network_layer_listener.start()

    consoler = console.Console(network_layer, route)
    consoler.task()
if __name__ == "__main__":
    main()