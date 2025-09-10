"""
Contains all the inherited models to comply with
"""

from odoo import fields, models


class InheritedUsers(models.Model):
    _inherit = 'res.users'

    property_ids = fields.One2many(
        'estate.property', 'salesperson', domain="[('state', 'in', ['new', 'offer_received'])]"
    )
