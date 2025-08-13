from odoo import models, fields, api, exceptions, _
import logging

_logger = logging.getLogger(__name__)

class AuditLog(models.Model):
    _name = 'audit.log'
    _description = 'Audit Log for User Actions'
    _order = 'action_date desc'  # Sort by latest action

    user_id = fields.Many2one('res.users', string="User", required=True, readonly=True, help="The user who performed the action being logged.")
    action_date = fields.Datetime(string="Action Date", default=fields.Datetime.now, readonly=True,help="The date and time when the action was performed.")
    action_type = fields.Selection([
        ('delete', 'Delete'),
        ('archive', 'Archive'),
    ], string="Action Type", required=True, readonly=True,help="Specifies the type of action performed, such as delete or archive.")
    model_name = fields.Char(string="Model", readonly=True,help="The name of the model where the action was performed.")
    record_name = fields.Char(string="Record", readonly=True,help="The name or identifier of the specific record affected by the action.")
    details = fields.Text(string="Details", readonly=True,help="Additional details about the action performed, such as field values or conditions.")
    description = fields.Text("Description",help="Optional field to provide a descriptive summary or explanation of the logged action.")  # Add this line if it's missing

    @api.model
    def _has_all_required_groups(self):
        """
        Check if the user belongs to all required groups to be considered an admin.
        """
        required_groups = [
            'zehntech_mass_delete_records.group_sales_manager',
            'zehntech_mass_delete_records.group_project_manager',
            'zehntech_mass_delete_records.group_invoice_manager',
            'zehntech_mass_delete_records.group_manufacturing_manager',
        ]

        # Get the external IDs of groups the user belongs to
        user_groups = self.env['ir.model.data'].search([
            ('model', '=', 'res.groups'),
            ('res_id', 'in', self.env.user.groups_id.ids)
        ]).mapped('complete_name')  # Fetch the full XML ID as 'module.group_id'

        # Check if all required groups are part of user's groups
        for group in required_groups:
            if group not in user_groups:
                _logger.warning("User %s does NOT belong to group %s", self.env.user.name, group)
                return False
            _logger.info("User %s belongs to group %s", self.env.user.name, group)

        return True
    def unlink(self):
        """
        Override the unlink method to restrict deletion based on group membership.
        """
        # Check if the user has all required groups
        has_all_groups = self._has_all_required_groups()
        is_admin = self.env.user.has_group('base.group_system')

        # If the user is not an admin and does not have all required groups, deny deletion
        if not (has_all_groups and is_admin):
            _logger.warning(
                "Access denied: User %s attempted to delete audit logs with groups: %s",
                self.env.user.name,
                self.env.user.groups_id.mapped('name')  # Log group names
            )
            raise exceptions.AccessError(_("You do not have permission to delete Audit Log entries."))

        _logger.info("Audit log deletion authorized for user %s", self.env.user.name)
        return super(AuditLog, self).unlink()