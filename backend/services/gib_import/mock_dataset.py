"""Mock dataset for GİB import flow.

This batch intentionally avoids live GİB login and uses a deterministic mock
invoice stream so import, parsing, upsert and draft aggregation can be tested
end-to-end.
"""


def build_mock_gib_payloads():
    return [
        {
            'source_key': 'mock-gib-001',
            'html_content': '''
                <html>
                  <body>
                    <div id="invoice-number">EA1202600000001</div>
                    <div id="invoice-date">2026-03-01</div>
                    <div id="invoice-ettn">ETTN-MOCK-001</div>
                    <div id="buyer-name">Ailem Market</div>
                    <div id="buyer-tax-no">1111111111</div>
                    <div id="grand-total">1500.00</div>
                    <table id="invoice-lines">
                      <tr data-line="1"><td class="product-code">AYR2L</td><td class="product-name">Ayran 2L</td><td class="qty">400</td><td class="unit-price">3.50</td><td class="line-total">1400.00</td></tr>
                      <tr data-line="2"><td class="product-code">KYOG</td><td class="product-name">Kova Yoğurt</td><td class="qty">10</td><td class="unit-price">10.00</td><td class="line-total">100.00</td></tr>
                    </table>
                  </body>
                </html>
            ''',
        },
        {
            'source_key': 'mock-gib-002',
            'html_content': '''
                <html>
                  <body>
                    <div id="invoice-number">EA1202600000002</div>
                    <div id="invoice-date">2026-03-10</div>
                    <div id="invoice-ettn">ETTN-MOCK-002</div>
                    <div id="buyer-name">Ailem Market</div>
                    <div id="buyer-tax-no">1111111111</div>
                    <div id="grand-total">1050.00</div>
                    <table id="invoice-lines">
                      <tr data-line="1"><td class="product-code">AYR2L</td><td class="product-name">Ayran 2L</td><td class="qty">300</td><td class="unit-price">3.50</td><td class="line-total">1050.00</td></tr>
                    </table>
                  </body>
                </html>
            ''',
        },
        {
            'source_key': 'mock-gib-003',
            'html_content': '''
                <html>
                  <body>
                    <div id="invoice-number">EA1202600000003</div>
                    <div id="invoice-date">2026-03-12</div>
                    <div id="buyer-name">Beta Şarküteri</div>
                    <div id="buyer-tc-no">12345678901</div>
                    <div id="grand-total">250.00</div>
                    <table id="invoice-lines">
                      <tr data-line="1"><td class="product-code">AYR1L</td><td class="product-name">Ayran 1L</td><td class="qty">25</td><td class="unit-price">10.00</td><td class="line-total">250.00</td></tr>
                    </table>
                  </body>
                </html>
            ''',
        },
        {
            'source_key': 'mock-gib-004',
            'html_content': '''
                <html>
                  <body>
                    <div id="invoice-number">EA1202600000004</div>
                    <div id="invoice-date">2026-03-15</div>
                    <div id="buyer-name">Kimliksiz Alıcı</div>
                    <div id="grand-total">100.00</div>
                    <table id="invoice-lines">
                      <tr data-line="1"><td class="product-code">TEST</td><td class="product-name">Deneme Ürün</td><td class="qty">5</td><td class="unit-price">20.00</td><td class="line-total">100.00</td></tr>
                    </table>
                  </body>
                </html>
            ''',
        },
    ]
