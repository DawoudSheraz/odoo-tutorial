
import logging

from odoo import fields, models
from odoo.fields import Command

logger = logging.getLogger(__name__)


class InheritedEstateProperty(models.Model):
    _inherit = 'estate.property'

    def mark_property_sold(self):
        res = super().mark_property_sold()

        # get customer journal to relate with Invoice.
        # TODO: Add some sort of atomicity where getting or failure should revert the property sold
        customer_journal = self.env['account.journal'].search([('code', '=', 'INV')])[0]
        currency = self.env['res.currency'].search([('name', '=', 'USD')])[0]

        for property in self:
            try:
                self.env['account.move'].create({
                    'partner_id': property.buyer.id,
                    'move_type': 'out_invoice',  # Customer Invoice
                    'journal_id': customer_journal.id,
                    'currency_id': currency.id,
                    # product_id needs to be False for the price unit to appear
                    'invoice_line_ids': [
                        Command.create({
                            'name': 'Selling Price Percentage',
                            'quantity': 0,
                            'price_unit': property.selling_price * 0.06,
                            'product_id': False
                        }),
                        Command.create({
                            'name': 'Administration Fee',
                            'quantity': 0,
                            'price_unit': 100.0,
                            'product_id': False
                        })
                    ]
                })
            except:
                logger.exception(f"Unable to create invoice for property {property}")

        return res
