
import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


logger = logging.getLogger(__name__)


class PropertyType(models.Model):
    _name="estate.property_type"
    _description="What sort of property"
    _order = "sequence, name"
    _sql_constraints = [
        ('unique_types', 'UNIQUE(name)', 'Property Types must be unique')
    ]

    name = fields.Char(required=True)
    sequence = fields.Integer('Sequence', default=1, help="Customize ordering, lower for high ranking")
    # This is needed to customize the form view of property type to list properties
    property_ids = fields.One2many('estate.property', 'property_type_id', string='Properties')

    offer_ids = fields.One2many('estate.property.offer', 'property_type_id', string='Offers')

    offer_count = fields.Integer(compute='_compute_offers_count')

    def _compute_offers_count(self):
        for property_type in self:
            property_type.offer_count = len(property_type.offer_ids)


class PropertyTag(models.Model):
    _name="estate.property.tag"
    _description="Property Tags"
    _order = "name"
    _sql_constraints = [
        ('unique_tags', 'UNIQUE(name)', 'Property tags must be unique')
    ]

    name = fields.Char(required=True)
    # color is populated by the many2many_tags widget
    color = fields.Integer()


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Real Estate Property Listing"
    _order = "id desc"
    _sql_constraints = [
        ('positive_expected_price', 'CHECK(expected_price >=0)', 'Expected price must be positive'),
        ('positives_elling_price', 'CHECK(selling_price >=0)', 'Selling price must be greater or equal to 0'),
    ]

    name = fields.Char(help="Property listing title", required=True)
    description = fields.Text(required=True)
    active = fields.Boolean(default=True)
    property_type_id = fields.Many2one("estate.property_type", string="Property Type")
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('offer_received', "Offer Received"),
            ('offer_accepted', 'Offer Accepted'),
            ('sold', 'Sold'),
            ('cancelled', "Cancelled")
        ],
        default='new'
    )
    tag_ids = fields.Many2many('estate.property.tag', string='Tags')
    postcode = fields.Char()
    date_availability = fields.Date(copy=False, default=fields.Date.add(fields.Date.today(), months=3))
    expected_price = fields.Float()
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Float(string='Living Area(sqm)')
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer()
    garden_orientation = fields.Selection(
        selection=[('north','North'), ('south','South'), ('east', 'East'), ('west', 'West')]
    )
    garden_walled = fields.Boolean()
    # res.partner links to an org/company/user
    buyer = fields.Many2one('res.partner', string='Property Buyer', copy=False)
    # By default, the current user is the salesperson, res.user is meant for system users where backend or portal
    salesperson = fields.Many2one('res.users', string='Salesperson', default = lambda self: self.env.user)

    offer_ids = fields.One2many('estate.property.offer', 'property_id')

    total_area = fields.Float(compute='_compute_total_area')

    best_price = fields.Float(compute='_compute_best_price', help='The best offer price', search='_search_best_price')

    @api.depends('garden_area', 'living_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.garden_area + record.living_area

    @api.depends('offer_ids.price')
    def _compute_best_price(self):
        for record in self:
            record.best_price = max(record.offer_ids.mapped('price'), default=0)

    def _search_total_area(self, operator, value):
        """
        Search function to allow searching on total_area computed field

        TODO: Not working as expected. self.<field> does not return any field value. It seems self is not object
        instance and cannot really compare on the data
        """
        print(operator, value, self)
        breakpoint()
        if operator not in ['=', '!=', '>', '<', '>=', '<=']:
            raise ValueError("Only comparison operations are allowed")
        if not (isinstance(value, int) or isinstance(value, float)):
            raise ValueError("Only integers and floats are allowed in the search")
        if isinstance(value, int):
            value = float(value)

        domain = []

        if self.living_area and self.garden_area:
            domain = ['&',
                      ('living_area', operator, value - self.garden_area),
                      ('garden_area', operator, value - self.living_area)
            ]
        elif self.garden_area:
            domain = [('garden_area', operator, value)]
        elif self.living_area:
            domain = [('living_area', operator, value)]

        properties_ids = self.env['estate.property']._search(domain) if domain else []
        return [('id', 'in', properties_ids)]

    def _search_best_price(self, operator, value):
        if operator not in ['=', '!=', '>', '<', '>=', '<=']:
            raise ValueError("Only comparison operations are allowed")
        if not (isinstance(value, int) or isinstance(value, float)):
            raise ValueError("Only integers and floats are allowed in the search")
        if isinstance(value, int):
            value = float(value)

        properties_ids = self.env['estate.property']._search([('offer_ids.price', operator, value)])
        return [('id', 'in', properties_ids)]

    @api.onchange('garden')
    def _handle_garden_toggle(self):
        if self.garden:
            self.garden_orientation = 'north'
            self.garden_area = 10
        else:
            # only reset the values if they are default, otherwise let them be
            if self.garden_area == 10 and self.garden_orientation == 'north':
                self.garden_area = 0
                self.garden_orientation = ''

    @api.constrains('selling_price')
    def validate_selling_price(self):
        for property_record in self:
            if not float_is_zero(
                    property_record.selling_price,
                    precision_digits=2
            ) and float_compare(
                property_record.selling_price,
                property_record.expected_price * 0.90,
                precision_digits=2
            ) == -1:
                raise ValidationError("Selling price should be at least 90% of expected price")

    def mark_property_sold(self):
        for property in self:
            if property.state == 'cancelled':
                raise UserError('Cancelled Properties cannot be sold')
            property.state = 'sold'
        return True

    def mark_property_cancelled(self):
        for property in self:
            if property.state == 'sold':
                raise UserError('Sold Properties cannot be cancelled')
            property.state = 'cancelled'
        return True

    def _set_buyer_details(self, buyer, price):
        self.selling_price = price
        self.buyer = buyer
        self.state = 'offer_accepted'

    def _reject_offers_on_acceptance(self, accepted_offer):
        """
        When an offer on a property is accepted, reject or refuse the remaining offers.

        TODO: Use ORM way to do this. I tried self.search([(offer_ids, not in, accepted_offer.id)]) but it returns
        all the properties that do not have this offer.
        """
        for offer in self.offer_ids:
            if offer.id == accepted_offer.id:
                continue
            offer.mark_offer_refused()

    @api.ondelete(at_uninstall=False)
    def handle_property_deletion(self):
        """
        Verify the property meets the criteria for deletion
        """
        for property in self:
            if property.state in ['offer_received', 'offer_accepted', 'sold']:
                raise UserError(
                    f"Property {property.name} cannot be deleted. Only new or cancelled properties can be deleted"
                )


class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'offers made against a property'
    _order = "price desc"
    _sql_constraints = [
        ('positive_price', 'CHECK(price >= 0)', 'Price must be positive')
    ]

    price = fields.Float()
    status = fields.Selection(
        selection=[('accepted', 'Accepted'),  ('in_review', 'In Review'), ('refused', 'Refused'),],
        copy=False
    )
    partner_id = fields.Many2one('res.partner', required=True)
    property_id = fields.Many2one('estate.property', required=True)

    validity = fields.Float(help="How many days the offer is going to be valid for?", default=7)
    deadline_date = fields.Date(compute='_compute_deadline_date', inverse='_compute_validity_from_deadline')

    property_type_id = fields.Many2one(related='property_id.property_type_id', store=True)


    @api.depends('validity')
    def _compute_deadline_date(self):
        for offer in self:
            if offer.create_date:
                offer.deadline_date = offer.create_date + timedelta(days=offer.validity)

    def _compute_validity_from_deadline(self):
        """
        Use inverse function to determine validity if the user selects deadline_date from UI.
        """
        for offer in self:
            if offer.deadline_date:
                offer.validity = (offer.deadline_date - offer.create_date.date()).days

    def mark_offer_accepted(self):
        for offer in self:
            if offer.status == 'refused':
                raise UserError("Refused Offers cannot be accepted")
            offer.status = 'accepted'
            offer.property_id._set_buyer_details(offer.partner_id, offer.price)
            offer.property_id._reject_offers_on_acceptance(self)
        return True

    def mark_offer_refused(self):
        for offer in self:
            if offer.status == 'accepted':
                raise UserError("Accepted Offers cannot be refused")
            offer.status = 'refused'
        return True

    @api.model
    def create(self, vals):
        try:
            property = self.env['estate.property'].browse(vals['property_id'])
        except:
            logger.exception("Unable to locate the property")
            raise
        price = vals['price']

        # locate if any offer below or equal to entered price exists. If not, the current entered price is lowest
        # and is not allowed
        lower_price_offers = self.env['estate.property.offer'].search_count(
            ['&', ('property_id', '=', property.id), ('price', '<=', price)]
        )

        if lower_price_offers == 0:
            raise UserError(f"Unable to create an offer with lower price than existing offers")

        property.state = 'offer_received'
        return super().create(vals)
