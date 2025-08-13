import logging
from odoo import models, fields,_
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class MassCleanManufacturingWizard(models.TransientModel):
    _name = 'mass.clean.manufacturing.wizard'
    _description = 'Mass Clean Manufacturing Orders Wizard'

    action = fields.Selection([
        ('delete_ongoing', 'Delete Ongoing Orders'),
        ('archive_done', 'Archive Done Orders'),
    ], string="Select Action", required=True,help=(
            "Choose an action to perform on manufacturing orders:\n"
            "- Delete Ongoing Orders: Permanently delete orders that are in progress.\n"
            "- Archive Done Orders: Move completed orders to an archived state."))

    def confirm_action(self):
        """Confirms the user's selection and performs the action."""
        if self.action == 'delete_ongoing':
            ongoing_orders = self.env['mrp.production'].search([('state', '!=', 'done')])
            if not ongoing_orders:
                return self._show_warning(_('No ongoing manufacturing orders to delete.'))

            # Log this action in the audit log
            self.env['audit.log'].create({
                'user_id': self.env.user.id,
                'action_type': 'delete',
                'model_name': 'mrp.production',
                'record_name': 'Manufacturing Orders',
                'details': _("User %(user_name)s is authorized to delete Manufacturing Orders.") % {'user_name': self.env.user.name}
            })
            self.delete_ongoing_orders(ongoing_orders)
            message = _('Manufacturing Orders got deleted!')

        elif self.action == 'archive_done':
            done_orders = self.env['mrp.production'].search([('state', '=', 'done')])
            if not done_orders:
                return self._show_warning(_('No done manufacturing orders to archive.'))

            # Log this action in the audit log
            self.env['audit.log'].create({
                'user_id': self.env.user.id,
                'action_type': 'archive',
                'model_name': 'mrp.production',
                'record_name': 'Manufacturing Orders',
                'details': _("User %(user_name)s is authorized to archive Manufacturing Orders.") % {'user_name': self.env.user.name}
            })
            self.archive_done_orders(done_orders)
            message = _('Manufacturing Orders got archived!')

        # Return success notification with the appropriate message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':  _('Success'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window_close'
                }
            }
        }

    def delete_ongoing_orders(self, ongoing_orders):
        """Deletes all ongoing manufacturing orders."""
        _logger.info("Deleting %s ongoing manufacturing orders", len(ongoing_orders))
        ongoing_orders.sudo().unlink()
        _logger.info("Successfully deleted ongoing manufacturing orders")

    def archive_done_orders(self, done_orders):
        """Archives done manufacturing orders."""
        for order in done_orders:
            order.sudo().write({'active': False})  # Mark as inactive if active field exists
        _logger.info("Successfully archived %s done manufacturing orders", len(done_orders))

    def _show_warning(self, message):
        """Helper method to show a warning notification."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':  _('Warning'),
                'message': message,
                'type': 'warning',
                'sticky': True,
            }
        }
