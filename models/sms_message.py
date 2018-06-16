# -*- coding: utf-8 -*-
import json
import logging
from odoo import fields, models, api, _
from datetime import datetime
from .QueuePublisher import QueuePublisherClient

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


class SMSMessage(models.Model):
    _name = "sms.message"
    _order = "date desc"
    _description = "SMS Interface for interacting with Agents via AfricasTalking"

    name = fields.Char("Name")
    text = fields.Text("Text")
    from_num = fields.Char("From", help="The sender of the message")
    to_num = fields.Char("To", help="The number to send the message to")
    type = fields.Selection([("inbox", "Inbox"), ("outbox", "Outbox")], "Type",  readonly=True, default="outbox")
    order_created = fields.Boolean("Order Created", readonly=True)
    note = fields.Text("Comment", readonly=True)
    date = fields.Datetime(
        "Date and Time", readonly=True, default=lambda *a: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    partner_id = fields.Many2one(
        "res.partner", string="Name", help="The partner Agent/Customer who sent/received this SMS"
    )
    test_sms = fields.Boolean("Test SMS", help="For a dummy SMS that will not be sent")
    state = fields.Selection([("draft", "Pending"), ("done", "Success")], "Status", default="draft")
    invalid = fields.Boolean("Invalid Keyword", help="Messages that do not have a valid keyword", default=False)
    actioned = fields.Boolean(help="If action e.g. reply has been taken", default=False)
    
    @api.model
    def create(self, vals):
        """
        Override the normal create() method for sms.message so that it can
        instead submit a message to the outgoing_sms_all_queue for forwarding
        to AfricasTalking API eventually

        :self: odoo.addons.sms.message Object
        :vals: Dictoinary of the sms.message details
        """
        vals.update({
            "name": "[%s] %s" % (
                vals.get("type", "-").upper(),
                self.env["res.partner"].browse(vals.get("partner_id")).name
            )
        })
        msg = super(SMSMessage, self).create(vals)

        if msg.id and msg.type == "outbox" and self.env.context.get("add_to_queue", False):
            try:
                vals.update({"db_message_id": msg.id})
                QueuePublisherClient("outbound_queue_consumer", json.dumps(vals).__str__())
            except Exception as e:
                _logger.info('Error while queueing SMS')
                _logger.error(e)

        return msg
    
    @api.multi
    def reply_sms(self):
        '''
        Show the send SMS form
        '''
        view_ref = self.env.ref('copia_sale.view_reply_sms')
        view_id = view_ref and view_ref.id
        for record in self:
            _logger.info('record is %s' % record)
            res_id = self.env['wizard.reply.sms'].create({
                'to' : record.from_num,
                'original_message_id' : record.id,
                'text' : '',
                'original_text' : record.text
            })
            _logger.info('res id is %s' % res_id)
            return {
                'type': 'ir.actions.act_window',
                'name': _('Reply to Message'),
                'res_model': 'wizard.reply.sms',
                'res_id': res_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new',
                'nodestroy': True,
            }
