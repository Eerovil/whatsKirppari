# -*- coding: utf-8 -*-
from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_messages.protocolentities  import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities  import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities      import OutgoingAckProtocolEntity
from yowsup.layers import YowLayerEvent, EventCallback
from yowsup.common.tools import Jid
from yowsup.layers.network import YowNetworkLayer
import os

class KirppariLayer(YowInterfaceLayer):
    EVENT_SEND    = "org.eerovil.kirppari.event.send"
    EVENT_MESSAGE = "org.eerovil.kirppari.event.message"

    @EventCallback(EVENT_SEND)
    def onSend(self, layerEvent):
        target = layerEvent.getArg("target")
        message = layerEvent.getArg("message")
        messageEntity = TextMessageProtocolEntity(message, to = Jid.normalize(target))
        self.toLower(messageEntity)

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def onStateDisconnected(self,layerEvent):
        print("Disconnected: %s" % layerEvent.getArg("reason"))
        os._exit(os.EX_OK)

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        #send receipt otherwise we keep receiving the same message over and over
        msg = messageProtocolEntity.getBody()
        print(msg)
        
        receipt = OutgoingReceiptProtocolEntity(
            messageProtocolEntity.getId(),
            messageProtocolEntity.getFrom(), 'read',
            messageProtocolEntity.getParticipant())
        self.toLower(receipt)
    
    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(
            entity.getId(), 
            "receipt", 
            entity.getType(), 
            entity.getFrom())
        self.toLower(ack)

    @ProtocolEntityCallback("ack")
    def onAck(self, entity):
        print("Message sent")