from odoo import models, fields

class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    active = fields.Boolean(default=True,help="Indicates whether this payment term is active.")
