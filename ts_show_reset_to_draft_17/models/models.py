from odoo import models


class AccountMoveInherited(models.Model):
    _inherit = 'account.move'
    _description = 'inherited account move class for reset to draft button'
