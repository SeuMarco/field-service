# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import pytz

from odoo import api, fields

from odoo.addons.base_geoengine import geo_model
from odoo.addons.base_geoengine import fields as geo_fields


class FSMLocation(geo_model.GeoModel):
    _name = 'fsm.location'
    _inherits = {'res.partner': 'partner_id'}
    _description = 'Field Service Location'

    @api.model
    def _tz_get(self):
        return [(tz, tz) for tz in sorted(pytz.all_timezones,
                                          key=lambda tz: tz
                                          if not tz.startswith('Etc/')
                                          else '_')]

    direction = fields.Char(string='Directions')
    partner_id = fields.Many2one('res.partner', string='Related Partner',
                                 required=True, ondelete='restrict',
                                 delegate=True, auto_join=True)
    owner_id = fields.Many2one('res.partner', string='Related Owner',
                               required=True, ondelete='restrict',
                               auto_join=True)
    customer_id = fields.Many2one('res.partner', string='Billed Customer',
                                  required=True, ondelete='restrict',
                                  auto_join=True)
    contact_id = fields.Many2one('res.partner', string='Primary Contact',
                                 ondelete='restrict', auto_join=True)
    tag_ids = fields.Many2many('fsm.tag', string='Tags')
    description = fields.Char(string='Description')
    territory_id = fields.Many2one('fsm.territory', string='Territory')
    branch_id = fields.Many2one('fsm.branch', string='Branch')
    district_id = fields.Many2one('fsm.district', string='District')
    region_id = fields.Many2one('fsm.region', string='Region')
    territory_manager_id = fields.Many2one(string='Primary Assignment',
                                           related='territory_id.person_id')
    district_manager_id = fields.Many2one(string='District Manager',
                                          related='district_id.partner_id')
    region_manager_id = fields.Many2one(string='Region Manager',
                                        related='region_id.partner_id')
    branch_manager_id = fields.Many2one(string='Branch Manager',
                                        related='branch_id.partner_id')

    timezone = fields.Selection(_tz_get, string='Timezone')

    parent_id = fields.Many2one('fsm.location', string='Parent')
    notes = fields.Text(string="Notes")
    person_ids = fields.Many2many('fsm.person', 'partner_id',
                                  string='Preferred Workers')

    contact_count = fields.Integer(string='Contacts',
                                    compute='_compute_contact_ids')
    equipment_count = fields.Integer(string='Equipment',
                                    compute='_compute_equipment_ids')

    # Geometry Field
    shape = geo_fields.GeoPoint(string='Coordinate')

    @api.model
    def create(self, vals):
        vals.update({'fsm_location': True})
        return super(FSMLocation, self).create(vals)

    @api.onchange('territory_id')
    def _onchange_territory_id(self):
        self.branch_id = self.territory_id.branch_id

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        self.district_id = self.branch_id.district_id

    @api.onchange('district_id')
    def _onchange_district_id(self):
        self.region_id = self.district_id.region_id

    @api.multi
    def action_view_contacts(self):
        '''
        This function returns an action that display existing contacts
        of given fsm locaiton id and its child locations. It can either be a in a list or in a form
        view, if there is only one contact to show.
        '''
        for location in self:
            action = self.env.ref('base.action_partner_tree_view1').read()[0]
            child_locs = self.env['fsm.location'].search([('parent_id', '=', location.id)])

            contacts = self.env['res.partner'].search([('service_location_id', 'in', child_locs.ids)])
            contacts += self.env['res.partner'].search([('service_location_id', '=', location.id)])
            
            if len(contacts) > 1:
                action['domain'] = [('id', 'in', contacts.ids)]
            elif contacts:
                action['views'] = [(self.env.ref('base.view_partner_form').id,
                                    'form')]
                action['res_id'] = contacts.id
            return action
    
    @api.multi
    def _compute_contact_ids(self):
        for location in self:
            child_locs = self.env['fsm.location'].search([('parent_id', '=', location.id)])
            contacts = (self.env['res.partner'].search_count([('service_location_id', 'in', child_locs.ids)]) + 
            self.env['res.partner'].search_count([('service_location_id', '=', location.id)]))
            location.contact_count = contacts or 0

    @api.multi
    def action_view_equipment(self):
        '''
        This function returns an action that display existing equipment
        of given fsm location id. It can either be a in a list or in a form
        view, if there is only one equipment to show.
        '''
        for location in self:
            action = self.env.ref('fieldservice.action_fsm_equipment').read()[0]
            child_locs = self.env['fsm.location'].search([('parent_id', '=', location.id)])

            equipment = self.env['fsm.equipment'].search([('location_id', 'in', child_locs.ids)])
            equipment += self.env['fsm.equipment'].search([('location_id', '=', location.id)])

            if len(equipment) > 1:
                action['domain'] = [('id', 'in', equipment.ids)]
            elif equipment:
                action['views'] = [(self.env.ref('fieldservice.fsm_equipment_form_view').id,
                                    'form')]
                action['res_id'] = equipment.id
            return action
    
    @api.multi
    def _compute_equipment_ids(self):
        for location in self:
            child_locs = self.env['fsm.location'].search([('parent_id', '=', location.id)])
            equipment = (self.env['fsm.equipment'].search_count([('location_id', 'in', child_locs.ids)]) +
            self.env['fsm.equipment'].search_count([('location_id', '=', location.id)]))
            location.equipment_count = equipment or 0
