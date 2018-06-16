import logging
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class ReplySMSWizard(models.TransientModel):
    '''
    Wizard to reply to a message that requires action
    '''
    _name = 'wizard.reply.sms'
    _description = 'A wizard to allow users to reply to inbox messages that are invalid and that need to be actioned'

   
    to = fields.Char('Recepient', readonly=True)
    text = fields.Text('Message', required=True)
    original_text = fields.Text('Original Message', readonly=True)
    original_message_id = fields.Many2one('sms.message')
   
    
    @api.multi
    def send_sms(self):
        '''
        Send a message
        '''
        order_object = self.env['sale.order']
        sms_object = self.env['sms.message']
        for record in self:
            msg = record.text
            to_number = record.to
            vals = {
                'from_num' : 'Copia',
                'to_num' : to_number,
                'message' : msg,
                'type' : 'outbox',
                'note' : 'Reply to invalid message',
            }
            #create an outbox which will be sent
            sms_object.with_context(add_to_queue=True).create(vals)
            #mark the inbox message as actioned
            record.original_message_id.write({'actioned' : True})
