import os
import pika
import json
from functools import partial

from src.common.logger import get_logger
from src.config import RABBIT_URL

logger = get_logger(__name__)


def get_amqp_connection(amqp_url=None):
    if amqp_url is None:
        amqp_url = RABBIT_URL

    connection = pika.BlockingConnection(pika.URLParameters(amqp_url))

    return connection


def publish_message(channel, exchange, routing_key, message, priority=0):
    channel.basic_publish(exchange=exchange, routing_key=routing_key, body=message,
                          properties=pika.BasicProperties(delivery_mode=2, priority=priority))


def publish_delayed_message(exchange_name, routing_key, data, delay, priority=None):
    connection = get_amqp_connection()
    try:
        channel = connection.channel()
        message = json.dumps(data)
        channel.basic_publish(exchange_name, routing_key, message,
                              properties=pika.BasicProperties(delivery_mode=2, headers={"x-delay": f"{delay}"}, priority=priority))
    finally:
        connection.close()


def publish(exchange_name, routing_key, data, amqp_url=None, priority=0):
    connection = get_amqp_connection(amqp_url)
    try:
        channel = connection.channel()
        message = json.dumps(data)
        publish_message(channel, exchange_name, routing_key, message, priority)
    finally:
        connection.close()


def declare_exchange(channel, exchange_name, exchange_type='topic', durable=True):
    channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type, durable=durable)


def declare_queue(channel, queue_name, exchange_name, routing_key, durable=True, priority=None):
    if priority is None:
        channel.queue_declare(queue=queue_name, durable=durable)
    else:
        channel.queue_declare(queue=queue_name, durable=durable, arguments={
            "x-max-priority": priority
        })
    channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)


def configure_queue(amqp_url, exchange_name, queue_name, routing_key, durable=True, exchange_type='topic',
                    priority=None):
    connection = get_amqp_connection(amqp_url)
    try:
        channel = connection.channel()
        logger.info(f"Declaring exchange {exchange_name}")
        if exchange_type == 'x-delayed-message':
            channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type, durable=durable,
                                     arguments={"x-delayed-type": "topic"})
        else:
            channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type, durable=durable)

        logger.info(f"Creating {queue_name} queue")
        if priority is None:
            channel.queue_declare(queue=queue_name, durable=durable)
        else:
            channel.queue_declare(queue=queue_name, durable=durable, arguments={
                "x-max-priority": priority
            })
        channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)
        logger.info('Queue created')
    finally:
        connection.close()
        logger.info(f'Exchange:{exchange_name} declared')
        logger.info(f'Queue:{queue_name} created & bound with routing key: {routing_key}')
        logger.info('Connection closed.')


class QueueConsumer(object):
    """This is an example consumer that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.

    If RabbitMQ closes the connection, it will reopen it. You should
    look at the output, as there are limited reasons why the connection may
    be closed, which usually are tied to permission related issues or
    socket timeouts.

    If the channel is closed, it will indicate a problem with one of the
    commands that were issued and that should surface in the output as well.

    """

    def __init__(self, amqp_url, queue_name, callback):
        """Create a new instance of the consumer class, passing in the AMQP
        URL used to connect to RabbitMQ.

        :param str amqp_url: The AMQP url to connect with

        """
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._url = amqp_url
        self._queue_name = queue_name
        self._callback = callback

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection

        """
        logger.info('Connecting to %s', self._url)
        return pika.SelectConnection(pika.URLParameters(self._url),
                                     self.on_connection_open,
                                     stop_ioloop_on_close=False)

    def on_connection_open(self, unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.

        :type unused_connection: pika.SelectConnection

        """
        logger.info('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def add_on_connection_close_callback(self):
        """This method adds an on close callback that will be invoked by pika
        when RabbitMQ closes the connection to the publisher unexpectedly.

        """
        logger.info('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given

        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            logger.warning('Connection closed, reopening in 5 seconds: (%s) %s',
                           reply_code, reply_text)
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        if not self._closing:
            # Create a new connection
            self._connection = self.connect()

            # There is now a new connection, needs a new ioloop to run
            self._connection.ioloop.start()

    def open_channel(self):
        """Open a new channel with RabbitMQ by issuing the Channel.Open RPC
        command. When RabbitMQ responds that the channel is open, the
        on_channel_open callback will be invoked by pika.

        """
        logger.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.

        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object

        """
        logger.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.start_consuming()

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.

        """
        logger.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed

        """
        logger.warning('Channel %i was closed: (%s) %s',
                       channel, reply_code, reply_text)
        self._connection.close()

    def start_consuming(self):
        """This method sets up the consumer by first calling
        add_on_cancel_callback so that the object is notified if RabbitMQ
        cancels the consumer. It then issues the Basic.Consume RPC command
        which returns the consumer tag that is used to uniquely identify the
        consumer with RabbitMQ. We keep the value to use it when we want to
        cancel consuming. The on_message method is passed in as a callback pika
        will invoke when a message is fully received.

        """
        logger.info('Issuing consumer related RPC commands')
        self.add_on_cancel_callback()
        self._channel.basic_qos(prefetch_count=1)
        self._consumer_tag = self._channel.basic_consume(self.on_message,
                                                         self._queue_name)

    def add_on_cancel_callback(self):
        """Add a callback that will be invoked if RabbitMQ cancels the consumer
        for some reason. If RabbitMQ does cancel the consumer,
        on_consumer_cancelled will be invoked by pika.

        """
        logger.info('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame

        """
        logger.info('Consumer was cancelled remotely, shutting down: %r',
                    method_frame)
        if self._channel:
            self._channel.close()

    def on_message(self, unused_channel, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ. The
        channel is passed for your convenience. The basic_deliver object that
        is passed in carries the exchange, routing key, delivery tag and
        a redelivered flag for the message. The properties passed in is an
        instance of BasicProperties with the message properties and the body
        is the message that was sent.

        :param pika.channel.Channel unused_channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param str|unicode body: The message body

        """
        # logger.info('Received message # %s from %s: %s',
        #             basic_deliver.delivery_tag, properties.app_id, body)
        params = json.loads(body)
        params['queue_consumer'] = self
        params['basic_deliver'] = basic_deliver
        self._callback(params)

    def add_callback_threadsafe(self, basic_deliver):
        callback = partial(QueueConsumer.on_message_callback, self, basic_deliver)
        self._connection.add_callback_threadsafe(callback)

    def on_message_callback(self, basic_deliver):
        logger.info(f'On Message callback. Acking message with delivery_tag={basic_deliver.delivery_tag}')
        self.acknowledge_message(basic_deliver.delivery_tag)

    def acknowledge_message(self, delivery_tag):
        """Acknowledge the message delivery from RabbitMQ by sending a
        Basic.Ack RPC method for the delivery tag.

        :param int delivery_tag: The delivery tag from the Basic.Deliver frame

        """
        logger.info('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        """Tell RabbitMQ that you would like to stop consuming by sending the
        Basic.Cancel RPC command.

        """
        if self._channel:
            logger.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def on_cancelok(self, unused_frame):
        """This method is invoked by pika when RabbitMQ acknowledges the
        cancellation of a consumer. At this point we will close the channel.
        This will invoke the on_channel_closed method once the channel has been
        closed, which will in-turn close the connection.

        :param pika.frame.Method unused_frame: The Basic.CancelOk frame

        """
        logger.info('RabbitMQ acknowledged the cancellation of the consumer')
        self.close_channel()

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly by issuing the
        Channel.Close RPC command.

        """
        logger.info('Closing the channel')
        self._channel.close()

    def run(self):
        """Run the example consumer by connecting to RabbitMQ and then
        starting the IOLoop to block and allow the SelectConnection to operate.

        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown the connection to RabbitMQ by stopping the consumer
        with RabbitMQ. When RabbitMQ confirms the cancellation, on_cancelok
        will be invoked by pika, which will then closing the channel and
        connection. The IOLoop is started again because this method is invoked
        when CTRL-C is pressed raising a KeyboardInterrupt exception. This
        exception stops the IOLoop which needs to be running for pika to
        communicate with RabbitMQ. All of the commands issued prior to starting
        the IOLoop will be buffered but not processed.

        """
        logger.info('Stopping')
        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.start()
        logger.info('Stopped')

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        logger.info('Closing connection')
        self._connection.close()
