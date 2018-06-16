import re
import uuid
import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from . import PushPublisher as pb
import json


class WizardSendSMSMessage(models.TransientModel):
    _name = "wizard.send.sms.message"
    _description = "Model that provides interface for sending SMS via the Outbox"

    partner_phone_numbers = fields.Char("Recepients Phone Number(s)")
    partner_ids = fields.Many2many("res.partner", string="Recepients", help="The recipients of the message")
    text = fields.Text("Message")

    @api.one
    def action_send_sms(self):
        # try:
        _phones = set([
            re.sub(r"^(0|254)", "+254", q.strip()) for q in self.partner_phone_numbers and self.partner_phone_numbers.split(",") or ""
        ])
        _partner_phones = set([p.phone for p in self.partner_ids])

        # Unite both without either set duplicates
        _res_numbers = _phones ^ _partner_phones

        # Validations
        if _res_numbers.__len__() == 0:
            raise UserError(_(
                "Please provide the receipients' phone numbers (comma separated) in the Recepients Phone Number(s) field or add them via "\
                "the Recepients field."
            ))

        _bad_nums = [p for p in filter(lambda x: re.match(r"^(\+254|0)7\d{8}$", x) is None, _res_numbers)]
        if _bad_nums:
            raise ValidationError(_(
                "Please provide phone numbers in the format 07xxxxxxxx or +2547xxxxxxxx"\
                "The following numbers did not fit this format:\n %s" % "\n".join(_bad_nums)
            ))

        _batch = uuid.uuid4()
        for phone in _res_numbers:
            sms_paylod = {}
            sms_paylod['phone'] = phone
            sms_paylod['msg'] = self.text
            pb.DataProvisionClient('bulk_sms_consumer', json.dumps(sms_paylod))

        return {
            "type": "ir.actions.act_window_close",
        }
