from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    active = fields.Boolean(default=True,help="Indicates whether this project is active.")
