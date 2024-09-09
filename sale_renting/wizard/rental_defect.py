# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class RentalDefect(models.TransientModel):
    _name = 'rental.order.defect.wizard'
    _description = 'Pick-up/Return products'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    order_line_id = fields.Many2one('sale.order.line', required=True, domain="[('order_id', '=', order_id)]", string="Product")
    product_template_id = fields.Many2one('product.template', required=True, related="order_line_id.product_template_id")
    product_piece_id = fields.Many2one('product.piece', required=True, string="Piece", domain="[('product_template_id', '=', product_template_id)]")
    qty = fields.Integer(string='Quantity', required=True)

    def apply(self):
        """Apply the wizard modifications to the SaleOrderLine(s)."""
        self.env['product.piece.defect'].create({
            'order_line_id': self.order_line_id.id,
            'product_piece_id': self.product_piece_id.id,
            'qty': self.qty
        })
        return {'type': 'ir.actions.act_window_close'}