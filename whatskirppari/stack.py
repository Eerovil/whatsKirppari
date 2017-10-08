# -*- coding: utf-8 -*-
from yowsup.stacks import YowStackBuilder
from .layer import KirppariLayer
from yowsup.layers.auth import AuthError
from yowsup.layers import YowLayerEvent
from yowsup.layers.network import YowNetworkLayer
import asyncore
from yowsup.layers.axolotl.props import PROP_IDENTITY_AUTOTRUST
import sys
import threading
import logging
logging.basicConfig(filename='example.log', format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

class YowsupKirppariStack(object):
    loop_thread = None
    def __init__(self, credentials, http):
        stackBuilder = YowStackBuilder()

        self.stack = stackBuilder\
            .pushDefaultLayers(True)\
            .push(KirppariLayer)\
            .build()

        # self.stack.setCredentials(credentials)
        self.stack.setCredentials(credentials)
        self.stack.setProp(PROP_IDENTITY_AUTOTRUST, True)
        self.stack.setProp(KirppariLayer.PROP_HTTP, http)

    def start(self):
        logger.info("Yowsup Cli client\n==================\nType /help for available commands\n")
        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
        self.loop_thread = threading.Thread(target=self.stack.loop, name="AsyncoreLoop")
        try:
            logger.info("Asyncore loop...")
            self.loop_thread.start()
            logger.info("Asyncore loop...Done")
        except AuthError as e:
            logger.info("Auth Error, reason %s" % e)
        except KeyboardInterrupt:
            logger.info("\nYowsdown")
            #sys.exit(0)

    def send(self, target, message):
        logger.info("sending")
        self.stack.broadcastEvent(YowLayerEvent(KirppariLayer.EVENT_SEND, target=target, message=message))


    def stop(self):
        logger.info("Sending diconnect")
        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECTED))
        sys.exit(0)
