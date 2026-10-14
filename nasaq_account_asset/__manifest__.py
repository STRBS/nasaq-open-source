# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    'name': "Nasaq Fixed Assets",
    'summary': "Restricted-fund rule for OCA's asset register: the fund is charged at purchase, never again by depreciation or disposal",
    'version': '20.0.1.0.0',
    'category': 'Nasaq',
    'author': 'STRIDE Business Solutions',
    'website': "https://www.stridebs.com",
    # AGPL-3, not OPL-1 (LAWYER H1030): this module extends OCA's AGPL-3 asset models and
    # runs as one combined work with them. No OPL-1 Nasaq module may depend on it.
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'sequence': 9,

    # LAWYER H1035: OCA + core Odoo ONLY. No Nasaq (OPL-1) module may sit below an AGPL one.
    'depends': [
        'account_asset_management',
    ],

    'data': [
        'data/ir_access_data.xml',
        'data/source_offer.xml',
        'views/account_asset_views.xml',
        'views/account_analytic_account_views.xml',
        'views/res_config_settings_views.xml',
    ],

    'description': """
Nasaq Fixed Assets
==================
OCA's ``account_asset_management`` is the asset register: assets from vendor
bills, the depreciation board, posting, disposal and the Excel register. This
module adds the one rule a non-profit needs on top (HAVA H1027/H1028, SOCPA /
NCNP 31401001):

* **A grant-funded asset is charged to its fund once, at purchase.** The fund
  is the restriction, and it is released when the asset is placed in service.
  Depreciation and disposal entries carry the programme analytic, never the
  Funds plan, so the restricted-fund guard is never asked to pay twice.
* The restricted funds are the accounts of one analytic plan, named in the
  Accounting settings (*Funds Plan for Assets*); on Nasaq, its Funds plan.
* **Funded by** is stored on the asset, taken from the bill line's fund. An
  accountant may set it by hand on an asset that has none and no posted
  depreciation (the opening register); it may also stay empty.
* **Depreciation starts on the 1st of the month after purchase.**
* **Billing users read assets.** A Billing clerk's bill is never blocked: the
  asset it creates is made in draft, for finance to confirm.
* A **Funded by** column and filter, and an **Assets** button on the fund's
  analytic account.

* **Source code of the open-source components** (Assets menu): the AGPL-3
  offer to every user, linking the public repository of the exact code run.

Licence: AGPL-3, as the OCA modules it extends.
    """,
}
