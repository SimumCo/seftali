import hashlib
import re
from bs4 import BeautifulSoup


def _text(soup, element_id: str):
    node = soup.find(id=element_id)
    return node.get_text(strip=True) if node else None


class GIBHtmlParserAdapter:
    """Parses raw invoice HTML into normalized invoice + invoice_lines payloads."""

    @classmethod
    def parse(cls, html_content: str) -> dict:
        soup = BeautifulSoup(html_content, 'html.parser')

        invoice_number = _text(soup, 'invoice-number')
        invoice_date = _text(soup, 'invoice-date')
        ettn = _text(soup, 'invoice-ettn')
        business_name = _text(soup, 'buyer-name')
        tax_no = _text(soup, 'buyer-tax-no')
        tc_no = _text(soup, 'buyer-tc-no')
        grand_total_text = _text(soup, 'grand-total') or '0'
        identity_number = tax_no or tc_no

        lines = []
        lines_table = soup.find(id='invoice-lines')
        line_rows = lines_table.find_all('tr', attrs={'data-line': True}) if lines_table else []
        for row in line_rows:
            line_no = int(row.get('data-line') or len(lines) + 1)
            product_code_cell = row.find('td', attrs={'class': 'product-code'})
            product_name_cell = row.find('td', attrs={'class': 'product-name'})
            qty_cell = row.find('td', attrs={'class': 'qty'})
            unit_price_cell = row.find('td', attrs={'class': 'unit-price'})
            line_total_cell = row.find('td', attrs={'class': 'line-total'})

            product_code = product_code_cell.get_text(strip=True) if product_code_cell else None
            product_name = product_name_cell.get_text(strip=True) if product_name_cell else 'Bilinmeyen Ürün'
            quantity = float((qty_cell.get_text(strip=True) if qty_cell else '0').replace(',', '.'))
            unit_price = float((unit_price_cell.get_text(strip=True) if unit_price_cell else '0').replace(',', '.'))
            line_total = float((line_total_cell.get_text(strip=True) if line_total_cell else '0').replace(',', '.'))
            normalized_name = re.sub(r'\s+', ' ', product_name.strip().lower())
            derived_product_id = product_code or re.sub(r'[^a-z0-9]+', '_', normalized_name).strip('_').upper()

            lines.append({
                'line_no': line_no,
                'product_id': derived_product_id or None,
                'product_code': product_code,
                'product_name': product_name,
                'normalized_name': normalized_name,
                'quantity': quantity,
                'unit_price': unit_price,
                'line_total': line_total,
            })

        dedupe_key = ettn or hashlib.sha1(f'{invoice_number}|{invoice_date}|{identity_number}'.encode()).hexdigest()

        return {
            'invoice': {
                'ettn': ettn,
                'invoice_number': invoice_number,
                'invoice_date': invoice_date,
                'business_name': business_name,
                'tax_no': tax_no,
                'tc_no': tc_no,
                'identity_number': identity_number,
                'grand_total': float(grand_total_text.replace(',', '.')),
                'dedupe_key': dedupe_key,
            },
            'lines': lines,
        }
