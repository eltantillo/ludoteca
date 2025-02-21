# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import math
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _, _lt
from odoo.exceptions import ValidationError
from odoo.tools import format_amount, float_compare, float_is_zero

# For our use case: pricing depending on the duration, the values should be sufficiently different from one plan to
# another to not suffer from the approcimation that all months are 31 longs.
# otherwise, 31 days would result in 2 month.
PERIOD_RATIO = {
    'hour': 1,
    'day': 24,
    'week': 24 * 7,
    'month': 24*31, # average number of days per month over the year
    'year': 24*31*12,
}


class ProductPricing(models.Model):
    """Temporal pricing rules."""

    _name = 'product.pricing'
    _description = 'Pricing rule of temporal products'
    _order = 'product_template_id,price,pricelist_id,recurrence_id'

    name = fields.Char(compute='_compute_name')
    description = fields.Char(compute='_compute_description')
    recurrence_id = fields.Many2one('sale.temporal.recurrence', string='Recurrency', required=True)
    price = fields.Monetary(string="Price $", compute="_compute_price_field")
    price_percent = fields.Float(string="Price %", required=True, default=1.0)
    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency_id', store=True)
    product_template_id = fields.Many2one('product.template', string="Product Templates", ondelete='cascade',
                                          help="Select products on which this pricing will be applied.")
    product_variant_ids = fields.Many2many('product.product', string="Product Variants",
                                           help="Select Variants of the Product for which this rule applies. Leave empty if this rule applies for any variant of this template.")
    pricelist_id = fields.Many2one('product.pricelist', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='pricelist_id.company_id')

    @api.depends('price_percent', 'product_template_id')
    def _compute_price_field(self):
        for price in self:
            price.price = (price.price_percent * price.product_template_id.list_price) / 100

    @api.constrains('product_template_id', 'pricelist_id', 'recurrence_id', 'product_variant_ids')
    def _check_unique_parameters(self):
        """ We want to avoid having several lines that applies for the same conditions.
        The pricing must differ by at least one parameter among
        the template, the variants, the pricelist (if defined or not), the duration and the time unit.
        """
        conflict_counter = defaultdict(int)
        for price in self.product_template_id.product_pricing_ids:
            key_list = [
                price.product_template_id.id,
                price.pricelist_id,
                price.recurrence_id,
            ]
            variants = price.product_variant_ids.ids or [_('all variants')]
            pricing_has_all_variants = price.product_template_id.product_variant_count == len(price.product_variant_ids)
            variants = [_('all variants')] if pricing_has_all_variants else variants
            for v in variants:
                key_list.append(v)
                key_val = tuple(key_list)
                conflict_counter[key_val] += 1
        pricing_issues = [k for k, v in conflict_counter.items() if v > 1]
        if pricing_issues:
            raise ValidationError(_("You cannot have multiple pricing for the same variant, recurrence and pricelist"))

    @api.depends_context('lang')
    @api.depends('recurrence_id')
    def _compute_name(self):
        for pricing in self:
            # TODO in master: use pricing.recurrence_id.duration_display
            pricing.name = _(
                "%s %s",
                pricing.recurrence_id.duration,
                pricing._get_unit_label(pricing.recurrence_id.duration))

    def _compute_description(self):
        for pricing in self:
            description = ""
            if pricing.currency_id.position == 'before':
                description += format_amount(self.env, amount=pricing.price, currency=pricing.currency_id)
            else:
                description += format_amount(self.env, amount=pricing.price, currency=pricing.currency_id)
            description += _("/%s", pricing.recurrence_id.unit)
            pricing.description = description

    @api.depends('pricelist_id', 'pricelist_id.currency_id')
    def _compute_currency_id(self):
        for pricing in self:
            if pricing.pricelist_id:
                pricing.currency_id = pricing.pricelist_id.currency_id
            else:
                pricing.currency_id = self.env.company.currency_id

    def _compute_price(self, duration, unit):
        """Compute the price for a specified duration of the current pricing rule.
        :param float duration: duration in hours
        :param str unit: duration unit (hour, day, week)
        :return float: price
        """
        self.ensure_one()
        if duration <= 0 or self.recurrence_id.duration <= 0:
            return self.price
        if unit != self.recurrence_id.unit:
            converted_duration = math.ceil((duration * PERIOD_RATIO[unit]) / (self.recurrence_id.duration * PERIOD_RATIO[self.recurrence_id.unit]))
        else:
            converted_duration = math.ceil(duration / self.recurrence_id.duration)
        return self.price * converted_duration

    @api.model
    def _compute_duration_vals(self, start_date, end_date):
        duration = end_date - start_date
        vals = dict(hour=(duration.days * 24 + duration.seconds / 3600))
        vals['day'] = math.ceil(vals['hour'] / 24)
        vals['week'] = math.ceil(vals['day'] / 7)
        duration_diff = relativedelta(end_date, start_date)
        months = 1 if duration_diff.days or duration_diff.hours or duration_diff.minutes else 0
        months += duration_diff.months
        months += duration_diff.years * 12
        vals['month'] = months
        vals['year'] = months/12
        return vals

    def _applies_to(self, product):
        """ Check whether current pricing applies to given product.
        :param product.product product:
        :return: true if current pricing is applicable for given product, else otherwise.
        """
        self.ensure_one()
        return (
            self.product_template_id == product.product_tmpl_id
            and (
                not self.product_variant_ids
                or product in self.product_variant_ids))

    def _get_pricing_samples(self):
        """ Get the pricing matching each type of periodicity.
        :returns: recordset containing one pricing per periodicity type
        """
        available_periodicities = set(self.mapped(lambda p: (p.recurrence_id.duration, p.recurrence_id.unit)))
        result = self.env['product.pricing']
        for period in available_periodicities:
            result |= self.filtered(lambda p: p.recurrence_id.duration == period[0] and p.recurrence_id.unit == period[1])[:1]
        return result

    @api.model
    def _get_first_suitable_pricing(self, product, pricelist=None):
        """ Get the first suitable pricing for given product and pricelist.

        Note: model method
        """
        return self._get_suitable_pricings(product, pricelist=pricelist, first=True)

    @api.model
    def _get_suitable_pricings(self, product, pricelist=None, first=False):
        """ Get the suitable pricings for given product and pricelist.

        Note: model method
        """
        is_product_template = product._name == "product.template"
        available_pricings = self.env['product.pricing']
        if pricelist:
            for pricing in product.product_pricing_ids:
                if pricing.pricelist_id == pricelist\
                   and (is_product_template or pricing._applies_to(product)):
                    if first:
                        return pricing
                    available_pricings |= pricing

        for pricing in product.product_pricing_ids:
            if not pricing.pricelist_id and (is_product_template or pricing._applies_to(product)):
                if first:
                    return pricing
                available_pricings |= pricing

        return available_pricings

    def _get_unit_label(self, duration):
        """ Get the translated product pricing unit label. """
        # TODO in master: remove in favor of env['sale.temporal.recurrence']_get_unit_label
        if duration is None:
            return ""
        if float_compare(duration, 1.0, precision_digits=2) < 1\
           and not float_is_zero(duration, precision_digits=2):
            singular_labels = {
                'hour': _lt("Hour"),
                'day': _lt("Day"),
                'week': _lt("Week"),
                'month': _lt("Month"),
                'year': _lt("Year"),
            }
            if self.recurrence_id.unit in singular_labels:
                return singular_labels[self.recurrence_id.unit]
        return dict(
            self.env['sale.temporal.recurrence']._fields['unit']._description_selection(self.env)
        )[self.recurrence_id.unit]
