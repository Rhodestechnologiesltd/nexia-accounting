from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)
from .mra_einvoicing import (
    MRAEinvocing
)


class ResPartner(models.Model):
    _inherit = "res.partner"

    trade_name = fields.Char(string="Trade name", copy=False)
    brn = fields.Char(string="BRN", copy=False)
    transaction_type = fields.Selection([('B2B', 'B2B'),
                                         ('B2G', 'B2G'),
                                         ('B2C', 'B2C')],
                                        string="Transaction Type", copy=False, tracking=True)
    buyer_type = fields.Selection([('VATR', 'VATR'),
                                   ('NVTR', 'NVTR'),
                                   ('EXMP', 'EXMP')],
                                  string="Buyer Type", copy=False, tracking=True)


class Product(models.Model):
    _inherit = "product.product"

    tax_code = fields.Selection([('TC01', 'TC01'), ('TC02', 'TC02'), ('TC03', 'TC03')],string="Tax Code", default='TC01',copy=False)