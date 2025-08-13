from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    active = fields.Boolean(default=True,help="Indicates whether this account is active.")  # Add this line to allow archiving

    def unlink(self):
        """Override unlink method to log deletions and handle foreign key constraints."""
        for record in self:
            if record.move_type in ['out_invoice', 'in_invoice', 'entry']:
                try:
                    # Log the deletion attempt to the audit log
                    self.env['account.deletion.audit.log'].sudo().create({
                        'record_type': 'invoice' if record.move_type in ['out_invoice', 'in_invoice'] else 'journal_entry',
                        'record_id': record.id,
                        'state': record.state,
                        'additional_info': f'Reference: {record.name}'
                    })
                    _logger.info("Logged deletion of %s with ID %s to audit log.", record.move_type, record.id)
                    
                    # Attempt to delete the record
                    super(AccountMove, record).unlink()
                except Exception as e:
                    if 'posted entry' in str(e):
                        # Log the incident if deletion fails due to foreign key constraints
                        _logger.warning("Cannot delete posted entry %s. Archiving instead.", record.name)
                        # Archive instead of deleting
                        record.active = False  # Mark the record as inactive
                    else:
                        # Raise the error for any other exception
                        _logger.error("Failed to delete %s with ID %s: %s", record.move_type, record.id, e)
                        raise UserError(_("Cannot delete record: %s" % e))
