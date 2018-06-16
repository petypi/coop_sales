# -*- coding: utf-8 -*-

import calendar
from dateutil.parser import parse
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
from pytz import timezone
import logging

_logger = logging.getLogger(__name__)

class SaleHoliday(models.Model):
    _name = 'sale.holiday'

    def _get_default_company(self):
        return self.env.user._get_company()

    name = fields.Char(required=True)
    holiday_date = fields.Date(required=True)
    company_id = fields.Many2one('res.company', required=True, ondelete='cascade', default=_get_default_company)

    _sql_constraints = [
        ('unique_name', 'unique(name, company_id)', "Holiday name must be unique per company"),
        ('unique_date', 'unique(holiday_date, company_id)', "Holiday date must be unique per company"),
    ]

    @api.model
    def search_holidays(self, start_date, end_date):
        '''
        Finds holidays that fall within a date range
        '''
        _logger.info('start_date: %s, end_date: %s' % (start_date, end_date))
        domain = []
        domain.append(('company_id', '=', self.env.user._get_company() and self.env.user._get_company().id or False))
        domain.append(('holiday_date', '>=', start_date))
        domain.append(('holiday_date', '<=', end_date))
        res = self.search_read(domain)
        if not res:
            return []
        res = [i['holiday_date'] for i in res]
        #need the unique holidays
        res = list(set(res))
        #query postgres to get the dates
        queries = ["select generate_series('%s', '%s', '1 day'::interval)::date" \
        % (i, i) for i in res]
        query = " union all ".join(queries)
        _logger.info('queries: %s' % queries)
        _logger.info('query: %s' % query)
        query = "select distinct(t1.generate_series) from (%s) t1" % query
        self.env.cr.execute(query)
        off_days = self.env.cr.fetchall()
        return off_days
