from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class WizardCreateHoliday(models.TransientModel):
    _name = "wizard.holiday.create"

    def _get_default_company(self):
        return self.env.user._get_company()

    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='cascade', default=_get_default_company)
    from_date = fields.Date('From', required=True)
    to_date = fields.Date('To', required=True)
    mon = fields.Boolean("Monday")
    tue = fields.Boolean("Tuesday")
    wed = fields.Boolean("Wednesday")
    thur = fields.Boolean("Thursday")
    fri = fields.Boolean("Friday")
    sat = fields.Boolean("Saturday")
    sun = fields.Boolean("Sunday")
    
    @api.multi
    def create_holidays(self):
        for record in self:
            valid = record.mon or record.tue or record.wed or record.thur or record.fri or record.sat or record.sun
            if not valid:
                raise ValidationError("Please select at least one day of the week")
            days = []
            if record.mon:
                days.append(1)
            if record.tue:
                days.append(2)
            if record.wed:
                days.append(3)
            if record.thur:
                days.append(4)
            if record.fri:
                days.append(5)
            if record.sat:
                days.append(6)
            if record.sun:
                days.append(7)
            _logger.info('days :%s' % days)
            self.env.cr.execute("select * from (select generate_series(%s, %s, '1 day'::interval)"\
            "::date as gen_date) b where extract(isodow from b.gen_date) = ANY(%s);", \
            (record.from_date, record.to_date, days))
            dates = [l[0] for l in self.env.cr.fetchall()]
            for d in dates:
                vals = {
                    'name' : d,
                    'holiday_date' : d,
                    'company_id': record.company_id.id,
                }
                self.env['sale.holiday'].create(vals)
            _logger.info('dates :%s' % dates)
