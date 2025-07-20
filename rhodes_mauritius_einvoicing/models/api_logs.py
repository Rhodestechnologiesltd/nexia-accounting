from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)


class MRALogs(models.Model):
    _name = "mra.logs"
    _rec_name = "request_id"

    api_type = fields.Selection([('authentication_api', 'Authentication API'), ('transmission_api', 'Transmission API')], string="API Type")
    request_id = fields.Char(string="Request ID")
    request_json = fields.Text(string="Request Parameters")

    response_id = fields.Char(string="Response ID")
    response_status_code = fields.Char(string="Response Code")
    response_json = fields.Text(string="Response")
