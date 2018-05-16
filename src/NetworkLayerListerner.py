import threading
import time
from include.logger import logger
class NetworkLayerListener(threading.Thread):
    """
    非阻塞地询问网络层是否有数据到达。若有，则向终端输出数据
    """
    def __init__(self, network_layer) -> None:
        threading.Thread.__init__(self)
        self.network_layer = network_layer
    def run(self) -> None:
        logger.debug('network layer listerner begin to work')
        while True:
            recv = self.network_layer.recv()
            if recv:
                logger.info('network layer pkg received\n{}'.format(recv))
            time.sleep(0.1)