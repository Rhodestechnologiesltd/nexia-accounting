import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
_logger = logging.getLogger(__name__)

class PurchaseCleanWizard(models.TransientModel):
    _name = 'purchase.clean.wizard'
    _description = 'Purchase Clean Wizard'

    delete_all = fields.Boolean(string="Delete All Purchase Orders", default=False,help="Select this option to delete all purchase orders regardless of their status or date.")
    delete_by_status = fields.Boolean(string="Delete by Status",help="Select this option to delete purchase orders based on their status.")
    status = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string="Status", default='draft', help="Select the status of the Purchase Orders to delete", required=True)
    delete_by_confirmation_date = fields.Boolean(string="Delete by Confirmation Dates", help="Select this option to delete purchase orders based on their confirmation dates.")
    delete_by_expected_arrival = fields.Boolean(string="Delete by Expected Arrival Date",   help="Select this option to delete purchase orders based on their expected arrival dates.")
    
    start_confirmation_date = fields.Date(string="Start Confirmation Date", help="Enter the start date for the confirmation date range to delete purchase orders.")
    end_confirmation_date = fields.Date(string="End Confirmation Date",  help="Enter the end date for the confirmation date range to delete purchase orders.")
    start_expected_arrival = fields.Date(string="Start Expected Arrival Date",help="Enter the start date for the expected arrival date range to delete purchase orders.")
    end_expected_arrival = fields.Date(string="End Expected Arrival Date",help="Enter the end date for the expected arrival date range to delete purchase orders.")

    @api.onchange('delete_all')
    def _onchange_delete_all(self):
        """Ensure only one option can be selected."""
        if self.delete_all:
            self.delete_by_status = False

    @api.onchange('delete_by_status')
    def _onchange_delete_by_status(self):
        """Ensure only one option can be selected."""
        if self.delete_by_status:
            self.delete_all = False

    def action_confirm_clean(self):
        """Method to trigger the deletion based on user input."""
        if not self.delete_all and not self.delete_by_status and not self.delete_by_expected_arrival:
            raise UserError(_("Please select an option: delete all purchase orders or delete by status or by expected arrival date."))
        
        # Create an audit log entry before cleaning the purchases
        action_details = "Deleting all purchase orders" if self.delete_all else f"Deleting purchase orders with status: {self.status}"
        self.env['audit.log'].create({
            'user_id': self.env.user.id,
            'action_type': 'delete',
            'model_name': 'purchase.order',
            'record_name': 'All' if self.delete_all else self.status,
            'details': _("User %(user_name)s is initiating the cleanup of purchase orders. %(action_details)s") % {'user_name': self.env.user.name,'action_details': action_details}
        })

        if self.delete_all:
            purchase_orders = self.env['purchase.order'].search([])
            if not purchase_orders:
                raise UserError(_("No purchase orders found to delete."))
            self.env['mass.clean.model'].clean_purchases(delete_all=True)
        
        elif self.delete_by_status and self.status:
            purchase_orders = self.env['purchase.order'].search([('state', '=', self.status)])
            if not purchase_orders:
                raise UserError(_("No purchase orders found with status to delete."))
            self.env['mass.clean.model'].clean_purchases(delete_all=False, status=self.status)

        # Call function to delete based on date ranges
        self.action_clean_by_date_ranges()

         # Success message customization
        if self.delete_all:
            message = _("All Purchase Orders have been successfully deleted.")
        elif self.delete_by_status:
            message = _("Purchase Orders with status '%s' have been successfully deleted.") % self.status
        elif self.delete_by_expected_arrival:
            message = _("Purchase Orders within the specified date range have been successfully deleted.")
        else:
            message = _("No Purchase Orders were deleted.")

        # Close the wizard and show the notification using JS
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'}  # Close the wizard window
            }
        }

    def action_clean_by_date_ranges(self):
        """Delete purchase orders based on the provided date ranges."""
        # Check user access
        user_groups = self.env.user.groups_id.mapped('name')
        _logger.info("User %s is attempting to clean purchase orders by date ranges with groups: %s", self.env.user.name, user_groups)

        is_system_group = self.env.user.has_group('base.group_system')
        is_sales_manager_group = self.env.user.has_group('zehntech_mass_delete_records.group_sales_manager')

        _logger.info("System group check for user %s: %s", self.env.user.name, is_system_group)
        _logger.info("Sales Manager group check for user %s: %s", self.env.user.name, is_sales_manager_group)

        # Deny access if the user is not in the allowed groups
        if not is_sales_manager_group:
            _logger.info("Access denied for user %s with groups: %s", self.env.user.name, self.env.user.groups_id.mapped('name'))
            raise AccessError(_("You do not have permission to delete purchase orders by date ranges."))

        # Proceed with deletion if the user has access
        purchase_orders = self.env['purchase.order']
        # Check if the expected arrival date range is provided
        if self.start_expected_arrival and self.end_expected_arrival:
            # Validate that the end date is greater than or equal to the start date
            if self.end_expected_arrival < self.start_expected_arrival:
                raise ValidationError(_("End Expected Arrival Date must be greater than or equal to Start Expected Arrival Date."))
             # Check if any records exist in the given expected arrival date range
            records_in_range = self.env['purchase.order'].search([
                ('date_planned', '>=', self.start_expected_arrival),
                ('date_planned', '<=', self.end_expected_arrival)
            ])
            
            if not records_in_range:
                raise ValidationError(_("No purchase orders found in the given Expected Arrival Date range."))

        # Add to the purchase orders to delete based on confirmation date range
        if self.start_confirmation_date and self.end_confirmation_date:
            purchase_orders |= self.env['purchase.order'].search([
                ('date_approve', '>=', self.start_confirmation_date),
                ('date_approve', '<=', self.end_confirmation_date)
            ])

        # Add to the purchase orders to delete based on expected arrival date range
        if self.start_expected_arrival and self.end_expected_arrival:
            purchase_orders |= self.env['purchase.order'].search([
                ('date_planned', '>=', self.start_expected_arrival),
                ('date_planned', '<=', self.end_expected_arrival)
            ])

        # Delete the found purchase orders
        self._delete_purchase_orders(purchase_orders)

        # Close the wizard after confirmation
        return {'type': 'ir.actions.act_window_close'}

    def _delete_purchase_orders(self, purchase_orders):
        """Helper method to cancel and then delete purchase orders and their related transfers."""
        for order in purchase_orders:
            # Cancel the purchase order if it's not already cancelled
            if order.state not in ['cancel']:
                # Create an audit log for cancellation
                self.env['audit.log'].create({
                    'user_id': self.env.user.id,
                    'action_type': 'archive',
                    'model_name': 'purchase.order',
                    'record_name': order.name,
                    'details': _("Purchase Order %(order_name)s canceled by %(user_name)s") % {'order_name': order.name,'user_name': self.env.user.name}
                })
                order.button_cancel()
            # Log deletion action
            self.env['audit.log'].create({
                'user_id': self.env.user.id,
                'action_type': 'delete',
                'model_name': 'purchase.order',
                'record_name': order.name,
                'details': _("Purchase Order %(order_name)s deleted by %(user_name)s") % {'order_name': order.name,'user_name': self.env.user.name}
            })

            # Find and cancel related stock pickings
            related_pickings = self.env['stock.picking'].search([('origin', '=', order.name)])
            for picking in related_pickings:
                # Directly delete the picking
                picking.sudo().unlink()

        # After cancelling and deleting related transfers, unlink the orders
        purchase_orders.sudo().unlink()