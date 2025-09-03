
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class PropertyType(models.Model):
    _name="estate.property_type"
    _description="What sort of property"

    name = fields.Char(required=True)


class PropertyTag(models.Model):
    _name="estate.property.tag"
    _description="Property Tags"

    name = fields.Char(required=True)


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Real Estate Property Listing"

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


class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'offers made against a property'

    price = fields.Float()
    status = fields.Selection(
        selection=[('accepted', 'Accepted'),  ('in_review', 'In Review'), ('refused', 'Refused'),],
        copy=False
    )
    partner_id = fields.Many2one('res.partner', required=True)
    property_id = fields.Many2one('estate.property', required=True)

    validity = fields.Float(help="How many days the offer is going to be valid for?", default=7)
    deadline_date = fields.Date(compute='_compute_deadline_date', inverse='_compute_validity_from_deadline')


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
