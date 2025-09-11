
import logging

from odoo import fields, models
from odoo.fields import Command

logger = logging.getLogger(__name__)


class InheritedEstateProperty(models.Model):
    _inherit = 'estate.property'

    def _create_invoice_data_dict(self, property, journal, currency, *args):
        return {
            'partner_id': property.buyer.id,
            'move_type': 'out_invoice',  # Customer Invoice
            'journal_id': journal.id,
            'currency_id': currency.id,
        }

    def _create_invoice_data_lines(self, name, price, **kwargs):
        return {
            'name': name,
            'quantity': kwargs.get('quantity', 0),
            'price_unit': price,
            # product_id needs to be False for the price unit to appear
            'product_id': kwargs.get('product_id', False)
        }

    def mark_property_sold(self):
        res = super().mark_property_sold()

        # get customer journal to relate with Invoice.
        # TODO: Add some sort of atomicity where getting or failure should revert the property sold
        customer_journal = self.env['account.journal'].search([('code', '=', 'INV')])[0]
        currency = self.env['res.currency'].search([('name', '=', 'USD')])[0]

        for property in self:
            try:
                invoice_data = self._create_invoice_data_dict(property, customer_journal, currency)
                invoice_data_lines = [
                    Command.create(self._create_invoice_data_lines(
                        'Selling Price Percentage', property.selling_price * 0.06, quantity=1)
                    ),
                    Command.create(self._create_invoice_data_lines(
                        'Administration Fee', 100.0, quantity=1)
                    )
                ]
                invoice_data.update({'invoice_line_ids': invoice_data_lines})
                self.env['account.move'].create(invoice_data)
            except:
                logger.exception(f"Unable to create invoice for property {property}")

        return res
