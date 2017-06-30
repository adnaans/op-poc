"""
Simple Collector, accept gNMI calls from test client and initiate new gNMI calls
to Probes. Behaves as gNMI server to the test client and gNMI client to the probes
"""

import gnmi.gnmi_pb2_grpc as gnmi_pb2_grpc
import gnmi.gnmi_pb2 as gnmi_pb2
from pathtree.pathtree import Branch as Branch 
from pathtree.pathtree import Path
import grpc
from concurrent import futures
import time
import logging
import argparse

# - logging configuration
logging.basicConfig()
logger = logging.getLogger('collector')

logger.setLevel(logging.DEBUG)

#configure southbound device address
device_ip = "localhost"
device_port = 80049
host_ip = "localhost"
host_port = 80050

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

class CollectorServicer(gnmi_pb2_grpc.gNMIServicer):

    def __init__(self):
        #initiate an empty pathtree for storing updates from the probes
        self.ptree = Branch() 

    def Subscribe(self, request_iterator, context):
        #create a channel connecting to the southbound device
        channel = grpc.insecure_channel(device_ip + ":" + str(device_port))
        stub = gnmi_pb2.gNMIStub(channel)
        
        #start streaming
        for response in stub.Subscribe(request_iterator):
            logger.info(response)
            yield response
            for e in response.update.update:
                self.ptree.add(Path(e.path.element),("timestamp: "+str(response.update.timestamp) +" value: "+ str(e.val.int_val))) 
                logger.info("pathtree snapshot:") 
                logger.info(self.ptree.dic)
        print "Streaming done!"


def serve():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost',
                        help='OpenConfig server host')
    parser.add_argument('--port', type=int, default=80050,
                        help='OpenConfig server port')
    parser.add_argument('--device_port', type=int, default=80049,
                        help='OpenConfig device port')
    args = parser.parse_args()

    global device_port
    device_port = args.device_port

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    gnmi_pb2_grpc.add_gNMIServicer_to_server(
        CollectorServicer(), server)
    server.add_insecure_port(args.host + ":" + str(args.port))
    server.start()
    logger.info("Collector Server Started.....")
    try:
       while True:
          time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
