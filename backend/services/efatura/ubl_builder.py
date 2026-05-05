import os
import uuid
from decimal import Decimal, ROUND_HALF_UP
from lxml import etree
from dotenv import dotenv_values

from .contracts import EInvoiceCreateRequest

UBL_NS = 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'
CBC_NS = 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
CAC_NS = 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'


def qname(ns, tag):
    return f'{{{ns}}}{tag}'


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


class UBLGenerationError(Exception):
    pass


class UBLInvoiceBuilder:
    def __init__(self, supplier_vkn_tckn: str, supplier_title: str | None = None):
        self.env = dotenv_values('/app/backend/.env')
        self.supplier_vkn_tckn = supplier_vkn_tckn
        self.supplier_title = supplier_title or os.environ.get('TURKCELL_EINVOICE_SUPPLIER_TITLE') or self.env.get('TURKCELL_EINVOICE_SUPPLIER_TITLE') or 'TEST GÖNDERİCİ'

    def build(self, payload: EInvoiceCreateRequest) -> str:
        try:
            root = etree.Element(qname(UBL_NS, 'Invoice'), nsmap={None: UBL_NS, 'cbc': CBC_NS, 'cac': CAC_NS})
            etree.SubElement(root, qname(CBC_NS, 'UBLVersionID')).text = '2.1'
            etree.SubElement(root, qname(CBC_NS, 'CustomizationID')).text = 'TR1.2'
            etree.SubElement(root, qname(CBC_NS, 'ProfileID')).text = payload.scenario or 'TEMELFATURA'
            etree.SubElement(root, qname(CBC_NS, 'ID')).text = payload.local_reference_id
            etree.SubElement(root, qname(CBC_NS, 'UUID')).text = str(uuid.uuid4())
            etree.SubElement(root, qname(CBC_NS, 'IssueDate')).text = payload.issue_date.isoformat()
            etree.SubElement(root, qname(CBC_NS, 'IssueTime')).text = '12:00:00'
            etree.SubElement(root, qname(CBC_NS, 'InvoiceTypeCode')).text = 'SATIS'
            etree.SubElement(root, qname(CBC_NS, 'DocumentCurrencyCode')).text = 'TRY'
            etree.SubElement(root, qname(CBC_NS, 'LineCountNumeric')).text = str(len(payload.lines))

            supplier_party = etree.SubElement(root, qname(CAC_NS, 'AccountingSupplierParty'))
            self._build_supplier_party(supplier_party, self.supplier_vkn_tckn, self.supplier_title)

            customer_party = etree.SubElement(root, qname(CAC_NS, 'AccountingCustomerParty'))
            self._build_customer_party(customer_party, payload.receiver.vkn_tckn, payload.receiver.title)

            subtotal = Decimal('0.00')
            total_tax = Decimal('0.00')
            line_index = 1
            vat_rate = Decimal('0.00')
            for line in payload.lines:
                line_total = (line.quantity * line.unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                tax_amount = (line_total * line.vat_rate / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                subtotal += line_total
                total_tax += tax_amount
                vat_rate = line.vat_rate

                invoice_line = etree.SubElement(root, qname(CAC_NS, 'InvoiceLine'))
                etree.SubElement(invoice_line, qname(CBC_NS, 'ID')).text = str(line_index)
                qty = etree.SubElement(invoice_line, qname(CBC_NS, 'InvoicedQuantity'))
                qty.text = money(line.quantity)
                qty.set('unitCode', line.unit_code)
                line_ext = etree.SubElement(invoice_line, qname(CBC_NS, 'LineExtensionAmount'))
                line_ext.text = money(line_total)
                line_ext.set('currencyID', 'TRY')

                line_tax_total = etree.SubElement(invoice_line, qname(CAC_NS, 'TaxTotal'))
                line_tax_amount = etree.SubElement(line_tax_total, qname(CBC_NS, 'TaxAmount'))
                line_tax_amount.text = money(tax_amount)
                line_tax_amount.set('currencyID', 'TRY')
                line_tax_subtotal = etree.SubElement(line_tax_total, qname(CAC_NS, 'TaxSubtotal'))
                line_taxable_amount = etree.SubElement(line_tax_subtotal, qname(CBC_NS, 'TaxableAmount'))
                line_taxable_amount.text = money(line_total)
                line_taxable_amount.set('currencyID', 'TRY')
                line_tax_amount_sub = etree.SubElement(line_tax_subtotal, qname(CBC_NS, 'TaxAmount'))
                line_tax_amount_sub.text = money(tax_amount)
                line_tax_amount_sub.set('currencyID', 'TRY')
                line_tax_category = etree.SubElement(line_tax_subtotal, qname(CAC_NS, 'TaxCategory'))
                line_percent = etree.SubElement(line_tax_category, qname(CBC_NS, 'Percent'))
                line_percent.text = money(line.vat_rate)
                line_tax_scheme = etree.SubElement(line_tax_category, qname(CAC_NS, 'TaxScheme'))
                etree.SubElement(line_tax_scheme, qname(CBC_NS, 'Name')).text = 'KDV'
                etree.SubElement(line_tax_scheme, qname(CBC_NS, 'TaxTypeCode')).text = '0015'

                item = etree.SubElement(invoice_line, qname(CAC_NS, 'Item'))
                etree.SubElement(item, qname(CBC_NS, 'Name')).text = line.name
                price = etree.SubElement(invoice_line, qname(CAC_NS, 'Price'))
                price_amount = etree.SubElement(price, qname(CBC_NS, 'PriceAmount'))
                price_amount.text = money(line.unit_price)
                price_amount.set('currencyID', 'TRY')
                line_index += 1

            grand_total = (subtotal + total_tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            tax_total_root = etree.SubElement(root, qname(CAC_NS, 'TaxTotal'))
            tax_total_amount = etree.SubElement(tax_total_root, qname(CBC_NS, 'TaxAmount'))
            tax_total_amount.text = money(total_tax)
            tax_total_amount.set('currencyID', 'TRY')
            tax_subtotal = etree.SubElement(tax_total_root, qname(CAC_NS, 'TaxSubtotal'))
            taxable_amount = etree.SubElement(tax_subtotal, qname(CBC_NS, 'TaxableAmount'))
            taxable_amount.text = money(subtotal)
            taxable_amount.set('currencyID', 'TRY')
            tax_amount_sub = etree.SubElement(tax_subtotal, qname(CBC_NS, 'TaxAmount'))
            tax_amount_sub.text = money(total_tax)
            tax_amount_sub.set('currencyID', 'TRY')
            tax_category = etree.SubElement(tax_subtotal, qname(CAC_NS, 'TaxCategory'))
            percent = etree.SubElement(tax_category, qname(CBC_NS, 'Percent'))
            percent.text = money(vat_rate)
            tax_scheme = etree.SubElement(tax_category, qname(CAC_NS, 'TaxScheme'))
            etree.SubElement(tax_scheme, qname(CBC_NS, 'Name')).text = 'KDV'
            etree.SubElement(tax_scheme, qname(CBC_NS, 'TaxTypeCode')).text = '0015'

            legal_total = etree.SubElement(root, qname(CAC_NS, 'LegalMonetaryTotal'))
            line_ext_total = etree.SubElement(legal_total, qname(CBC_NS, 'LineExtensionAmount'))
            line_ext_total.text = money(subtotal)
            line_ext_total.set('currencyID', 'TRY')
            tax_exclusive = etree.SubElement(legal_total, qname(CBC_NS, 'TaxExclusiveAmount'))
            tax_exclusive.text = money(subtotal)
            tax_exclusive.set('currencyID', 'TRY')
            tax_inclusive = etree.SubElement(legal_total, qname(CBC_NS, 'TaxInclusiveAmount'))
            tax_inclusive.text = money(grand_total)
            tax_inclusive.set('currencyID', 'TRY')
            payable = etree.SubElement(legal_total, qname(CBC_NS, 'PayableAmount'))
            payable.text = money(grand_total)
            payable.set('currencyID', 'TRY')

            return etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True).decode('utf-8')
        except Exception as exc:
            raise UBLGenerationError(str(exc)) from exc

    def _build_postal_address(self, party, prefix: str):
        street = os.environ.get(f'TURKCELL_EINVOICE_{prefix}_STREET') or self.env.get(f'TURKCELL_EINVOICE_{prefix}_STREET') or 'Test Mahallesi'
        district = os.environ.get(f'TURKCELL_EINVOICE_{prefix}_DISTRICT') or self.env.get(f'TURKCELL_EINVOICE_{prefix}_DISTRICT') or 'Merkez'
        city = os.environ.get(f'TURKCELL_EINVOICE_{prefix}_CITY') or self.env.get(f'TURKCELL_EINVOICE_{prefix}_CITY') or 'İstanbul'
        postal_code = os.environ.get(f'TURKCELL_EINVOICE_{prefix}_POSTAL_CODE') or self.env.get(f'TURKCELL_EINVOICE_{prefix}_POSTAL_CODE') or '34000'
        country_name = os.environ.get(f'TURKCELL_EINVOICE_{prefix}_COUNTRY') or self.env.get(f'TURKCELL_EINVOICE_{prefix}_COUNTRY') or 'Türkiye'
        postal = etree.SubElement(party, qname(CAC_NS, 'PostalAddress'))
        etree.SubElement(postal, qname(CBC_NS, 'StreetName')).text = street
        etree.SubElement(postal, qname(CBC_NS, 'CitySubdivisionName')).text = district
        etree.SubElement(postal, qname(CBC_NS, 'CityName')).text = city
        etree.SubElement(postal, qname(CBC_NS, 'PostalZone')).text = postal_code
        country = etree.SubElement(postal, qname(CAC_NS, 'Country'))
        etree.SubElement(country, qname(CBC_NS, 'Name')).text = country_name

    def _build_supplier_party(self, parent, vkn_tckn: str, title: str):
        party = etree.SubElement(parent, qname(CAC_NS, 'Party'))
        endpoint = etree.SubElement(party, qname(CBC_NS, 'EndpointID'))
        endpoint.text = vkn_tckn
        endpoint.set('schemeID', 'VKN' if len(vkn_tckn) == 10 else 'TCKN')

        party_identification = etree.SubElement(party, qname(CAC_NS, 'PartyIdentification'))
        party_id = etree.SubElement(party_identification, qname(CBC_NS, 'ID'))
        party_id.text = vkn_tckn
        party_id.set('schemeID', 'VKN' if len(vkn_tckn) == 10 else 'TCKN')

        party_name = etree.SubElement(party, qname(CAC_NS, 'PartyName'))
        etree.SubElement(party_name, qname(CBC_NS, 'Name')).text = title

        self._build_postal_address(party, 'SUPPLIER')

        party_tax_scheme = etree.SubElement(party, qname(CAC_NS, 'PartyTaxScheme'))
        company_id = etree.SubElement(party_tax_scheme, qname(CBC_NS, 'CompanyID'))
        company_id.text = vkn_tckn
        company_id.set('schemeID', 'VKN' if len(vkn_tckn) == 10 else 'TCKN')
        tax_scheme = etree.SubElement(party_tax_scheme, qname(CAC_NS, 'TaxScheme'))
        etree.SubElement(tax_scheme, qname(CBC_NS, 'Name')).text = os.environ.get('TURKCELL_EINVOICE_SUPPLIER_TAX_OFFICE') or self.env.get('TURKCELL_EINVOICE_SUPPLIER_TAX_OFFICE') or 'Marmara Kurumlar'
        etree.SubElement(tax_scheme, qname(CBC_NS, 'TaxTypeCode')).text = '0015'

        legal_entity = etree.SubElement(party, qname(CAC_NS, 'PartyLegalEntity'))
        etree.SubElement(legal_entity, qname(CBC_NS, 'RegistrationName')).text = title

    def _build_customer_party(self, parent, vkn_tckn: str, title: str):
        party = etree.SubElement(parent, qname(CAC_NS, 'Party'))
        endpoint = etree.SubElement(party, qname(CBC_NS, 'EndpointID'))
        endpoint.text = vkn_tckn
        endpoint.set('schemeID', 'VKN' if len(vkn_tckn) == 10 else 'TCKN')

        party_identification = etree.SubElement(party, qname(CAC_NS, 'PartyIdentification'))
        party_id = etree.SubElement(party_identification, qname(CBC_NS, 'ID'))
        party_id.text = vkn_tckn
        party_id.set('schemeID', 'VKN' if len(vkn_tckn) == 10 else 'TCKN')

        party_name = etree.SubElement(party, qname(CAC_NS, 'PartyName'))
        etree.SubElement(party_name, qname(CBC_NS, 'Name')).text = title

        self._build_postal_address(party, 'CUSTOMER')

        party_tax_scheme = etree.SubElement(party, qname(CAC_NS, 'PartyTaxScheme'))
        company_id = etree.SubElement(party_tax_scheme, qname(CBC_NS, 'CompanyID'))
        company_id.text = vkn_tckn
        company_id.set('schemeID', 'VKN' if len(vkn_tckn) == 10 else 'TCKN')
        tax_scheme = etree.SubElement(party_tax_scheme, qname(CAC_NS, 'TaxScheme'))
        etree.SubElement(tax_scheme, qname(CBC_NS, 'Name')).text = os.environ.get('TURKCELL_EINVOICE_CUSTOMER_TAX_OFFICE') or self.env.get('TURKCELL_EINVOICE_CUSTOMER_TAX_OFFICE') or 'Marmara Kurumlar'
        etree.SubElement(tax_scheme, qname(CBC_NS, 'TaxTypeCode')).text = '0015'

        legal_entity = etree.SubElement(party, qname(CAC_NS, 'PartyLegalEntity'))
        etree.SubElement(legal_entity, qname(CBC_NS, 'RegistrationName')).text = title
