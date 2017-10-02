# -*- coding: utf-8 -*-
from yowsup.stacks import YowStackBuilder
from layer import KirppariLayer
from yowsup.layers.auth import AuthError
from yowsup.layers import YowLayerEvent
from yowsup.layers.network import YowNetworkLayer
import asyncore
from yowsup.layers.axolotl.props import PROP_IDENTITY_AUTOTRUST
import sys
import threading


class YowsupKirppariStack(object):
    loop_thread = None
    def __init__(self, credentials):
        stackBuilder = YowStackBuilder()

        self.stack = stackBuilder\
            .pushDefaultLayers(True)\
            .push(KirppariLayer)\
            .build()

        # self.stack.setCredentials(credentials)
        self.stack.setCredentials(credentials)
        self.stack.setProp(PROP_IDENTITY_AUTOTRUST, True)

    def start(self):
        print("Yowsup Cli client\n==================\nType /help for available commands\n")
        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
        self.loop_thread = threading.Thread(target=self.stack.loop, name="AsyncoreLoop")
        try:
            print("Asyncore loop...")
            self.loop_thread.start()
            print("Asyncore loop...Done")
        except AuthError as e:
            print("Auth Error, reason %s" % e)
        except KeyboardInterrupt:
            print("\nYowsdown")
            #sys.exit(0)

    def send(self, target, message):
        print("sending")
        self.stack.broadcastEvent(YowLayerEvent(KirppariLayer.EVENT_SEND, target=target, message=message))


    def stop(self):
        print("Sending diconnect")
        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECTED))
        sys.exit(0)
