# -*- coding: utf-8 -*-
from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_messages.protocolentities  import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities  import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities      import OutgoingAckProtocolEntity
from yowsup.layers import YowLayerEvent, EventCallback
from yowsup.common.tools import Jid
from yowsup.layers.network import YowNetworkLayer
import os
import logging
logger = logging.getLogger(__name__)

class KirppariLayer(YowInterfaceLayer):
    EVENT_SEND    = "org.eerovil.kirppari.event.send"
    EVENT_MESSAGE = "org.eerovil.kirppari.event.message"
    PROP_HTTP =     "org.eerovil.kirppari.prop.http"

    @EventCallback(EVENT_SEND)
    def onSend(self, layerEvent):
        target = layerEvent.getArg("target")
        message = layerEvent.getArg("message")
        messageEntity = TextMessageProtocolEntity(message, to = Jid.normalize(target))
        self.toLower(messageEntity)

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def onStateDisconnected(self,layerEvent):
        logger.info("Disconnected: %s" % layerEvent.getArg("reason"))
        os._exit(os.EX_OK)

    def executeCommand(self, messageProtocolEntity):
        http = self.getProp(self.PROP_HTTP)
        msg = messageProtocolEntity.getBody()
        send = ""
        if (msg == "!saldo"):
            logger.debug("We got there")
            send = "Tämänhetkinen saldo: " + http.getSaldo()
            messageEntity = TextMessageProtocolEntity(send, to = messageProtocolEntity.getFrom())
        else:
            return

        self.toLower(messageEntity)
        #self.toLower(messageEntity.ack())
        #self.toLower(messageEntity.ack(True))
            

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        #send receipt otherwise we keep receiving the same message over and over
        if messageProtocolEntity.getType() == 'text':
            msg = messageProtocolEntity.getBody()
            logger.info(msg)

            if (msg[0] == '!'):
                self.executeCommand(messageProtocolEntity)
        
        receipt = OutgoingReceiptProtocolEntity(
            messageProtocolEntity.getId(),
            messageProtocolEntity.getFrom(), 'read',
            messageProtocolEntity.getParticipant())
        self.toLower(receipt)
    
    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        self.toLower(entity.ack())

    @ProtocolEntityCallback("ack")
    def onAck(self, entity):
        logger.info("Message sent")