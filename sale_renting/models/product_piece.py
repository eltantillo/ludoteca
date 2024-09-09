# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ProductPiece(models.Model):
    _name = 'product.piece'

    product_template_id = fields.Many2one('product.template')
    name = fields.Char(string='Name')
    qty = fields.Integer(string='Quantity')
    group_value = fields.Float(string='Total percentage value')
    individual_value = fields.Float(string='Piece value', compute="_compute_individual_value")

    @api.onchange('qty', 'group_value')
    def _compute_individual_value(self):
        for piece in self:
            if not piece.product_template_id.list_price or not piece.qty:
                piece.individual_value = 0
            else:
                piece.individual_value = ((piece.group_value / 100) * piece.product_template_id.list_price) / piece.qty


class ProductPieceSale(models.Model):
    _name = 'product.piece.defect'

    name = fields.Char(compute="_compute_name")
    order_line_id = fields.Many2one('sale.order.line')
    product_piece_id = fields.Many2one('product.piece', string="Piece")
    qty = fields.Integer(string='Quantity')
    total = fields.Integer(string='Total', compute="_compute_total", store=True)
    processed = fields.Boolean()

    @api.depends('qty', 'product_piece_id')
    def _compute_total(self):
        for piece in self:
            piece.total = piece.qty * piece.product_piece_id.individual_value

    def _compute_name(self):
        for defect in self:
            defect.name = "{} {}(s) - ${}".format(defect.qty, defect.product_piece_id.name, defect.total)
