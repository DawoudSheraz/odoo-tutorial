from odoo import fields, models

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
    living_areas = fields.Integer()
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


class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'offers made against a property'

    price = fields.Float()
    status = fields.Selection(
        selection=[('accepted', 'Accepted'), ('refused', 'Refused')],
        copy=False
    )
    partner_id = fields.Many2one('res.partner', required=True)
    property_id = fields.Many2one('estate.property', required=True)
