# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.tools import float_compare


class SaleOrderConfirmWizard(models.TransientModel):
    _name = 'sale.order.confirm.wizard'
    _description = 'Sale Order Confirm Wizard'

    order_id = fields.Many2one('sale.order', string='Sale Order')
    message = fields.Html()

    def action_confirm(self):
        self.order_id.action_confirm()
        return self.order_id.open_pickup()