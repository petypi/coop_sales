import pika
import uuid
import logging
from pika.adapters import SelectConnection

_logger = logging.getLogger(__name__)

class QueuePublisherClient(object):
    def __init__(self, queue, request):
        self.queue = queue
        self.response = None
        self.channel = None
        self.request = request
        self.corrId = str(uuid.uuid4())
        self.callBackQueue = None
        self.connection = None
        parameters = pika.ConnectionParameters(host="0.0.0.0")
        self.connection = SelectConnection(
            parameters, self.on_response_connected
        )
        self.connection.ioloop.start()

    def on_response(self,ch, method, props, body):
        if self.corrId == props.correlation_id:
            self.response = body
            self.connection.close()
            self.connection.ioloop.start()

    def on_response_connected(self,connection):
        _logger.info("Connected...\t(%s)" % self.queue)
        self.connection = connection
        self.connection.channel(self.on_channel_open)

    def on_response_channel_open(self,channel):
        self.responseChannel = channel
        result = self.responseChannel.queue_declare(
            exclusive=True, callback=self.on_response_queue_declared
        )

    def on_connected(self,connection):
        self.connection = connection
        self.connection.channel(self.on_channel_open)

    def on_channel_open(self, channel):
        _logger.info("Channel Opened...\t(%s)" % self.queue)
        self.channel = channel
        self.channel.queue_declare(queue = self.queue,
                                   durable=True,
                                   exclusive=False,
                                   auto_delete=False,
                                   callback=self.on_queue_declared)

    def on_queue_declared(self,frame):
        self.channel.basic_publish(exchange="",
                                   routing_key = self.queue,
                                   properties = pika.BasicProperties(),
                                   body=str(self.request))
        self.connection.close()
        _logger.info("Message Published...\t(%s)" % self.queue)

