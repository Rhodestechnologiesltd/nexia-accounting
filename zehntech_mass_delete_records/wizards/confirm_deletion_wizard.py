
import logging
from odoo import models, fields,_
_logger = logging.getLogger(__name__)

class ConfirmDeletionWizard(models.TransientModel):
    _name = 'confirm.deletion.wizard'
    _description = 'Confirmation Wizard for Deleting Multiple Modules'

    selected_modules = fields.Text(string="Selected Modules", readonly=True, help="Displays a list of modules selected for deletion, as a summary for user confirmation.")
    wizard_id = fields.Many2one('mass.clean.wizard', string="Parent Wizard",help="Links this confirmation wizard to its corresponding parent mass clean wizard.")

    def action_confirm(self):
        """Confirm deletion action."""
        if not self.wizard_id:
            # Ensure the wizard_id is set
            raise ValueError("Parent wizard is not set for this confirmation wizard.")

        # Call the _perform_selected_modules_deletion method from the parent wizard
        no_data_modules = self.wizard_id._perform_selected_modules_deletion()
         # Log the no_data_modules content
        _logger.info(f"No data found for the following modules: {', '.join(no_data_modules)}")

        # Check if no data was found for any selected modules
        if no_data_modules:
            # Return warning notification if no data was found for selected modules
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message':  _('No data found for the selected modules: %s') % ', '.join(no_data_modules),
                    'type': 'warning',
                    'sticky': True,
                }
            }

        # Return success message after deletion if data was found
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _("Data of selected modules deleted successfully"),
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window_close'
                }
            }
        }

    def action_cancel(self):
        """Cancel the deletion and close the wizard without proceeding with any data deletion."""
        return {'type': 'ir.actions.act_window_close'}