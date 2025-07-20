from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)
from .mra_einvoicing import (
    MRAEinvocing
)


class ResCompany(models.Model):
    _inherit = "res.company"

    enable_mra_api = fields.Boolean(string="MRA e-Invoicing", copy=False)

    username = fields.Char(string='Username', copy=False)
    password = fields.Char(string='Password', copy=False)
    ebs_mra_id = fields.Char(string='EBS ID', copy=False)
    area_code = fields.Char(string='Area Code', copy=False)

    token_status = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Status", copy=False)
    token = fields.Char(string="Token", copy=False)
    encrypted_key = fields.Char(string="Encrypted Key", copy=False)
    encoded_key = fields.Char(string="Encoded Key", copy=False)
    token_expiry_date = fields.Datetime(string="Expiry Date", copy=False)
    token_creation_date = fields.Datetime(string="Generation Date", copy=False)
    
    std_count = fields.Integer(string="Standard Invoice Counter", readonly=True)
    prf_count = fields.Integer(string="Proforma Invoice Counter", readonly=True)
    crn_count = fields.Integer(string="Credit Note Counter", readonly=True)
    drn_count = fields.Integer(string="Debit Note Counter", readonly=True)
    trn_count = fields.Integer(string="Training Invoice Counter", readonly=True)
    global_count = fields.Integer(string="Global Invoice Counter", readonly=True)

    def action_generate_token(self):
        rhodes_mra_invoicing = MRAEinvocing(self)
        response, api_logs, encoded_key = rhodes_mra_invoicing._get_new_auth_token(self.username, self.password, self.ebs_mra_id)
        if api_logs:
            self.env['mra.logs'].sudo().create(api_logs)

        if response.status_code == 200:
            result = response.json()
            self.token_status = 'success'
            self.token = result.get('token')
            self.encrypted_key = result.get('key')
            self.encoded_key = encoded_key
            expiry_date = result.get('expiryDate')
            utc_time = datetime.strptime(expiry_date, "%Y%m%d %H:%M:%S") - timedelta(hours=4)
            self.token_expiry_date = utc_time
            self.token_creation_date = fields.Datetime.now()

            title = _("Successfully!")
            message = _("Authentication successful!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }
        else:
            result = response.json()
            raise ValidationError(_(
                "Authentication failed. \nStatus code: %s \nMessage: %s", response.status_code, result.get('errors')
            ))
