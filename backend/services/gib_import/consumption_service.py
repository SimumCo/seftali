from datetime import datetime, timedelta
import re
import unicodedata

from config.database import db
from repositories.gib_import_repository import GIBImportRepository


class ConsumptionCalculationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CustomerConsumptionService:
    """Calculates product-level daily and aggregate consumption from linked historical invoices."""

    MAX_LOOKBACK_DAYS = 365
    DAILY_METHOD = 'interval_spread'

    def __init__(self):
        self.repository = GIBImportRepository(db)

    @staticmethod
    def _parse_date(value: str | None):
        if not value:
            return None
        try:
            if '-' in value:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
            day, month, year = value.split(' ')
            return datetime(int(year), int(month), int(day)).date()
        except Exception:
            return None

    @staticmethod
    def _average(values: list[float]) -> float | None:
        valid = [value for value in values if value is not None]
        if not valid:
            return None
        return round(sum(valid) / len(valid), 4)

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if not value:
            return None
        normalized = unicodedata.normalize('NFKC', value)
        normalized = re.sub(r'\s+', ' ', normalized.strip().lower())
        return normalized or None

    def _apply_lookback_limit(self, invoices: list[dict]) -> list[dict]:
        dated = [invoice for invoice in invoices if self._parse_date(invoice.get('invoice_date'))]
        if not dated:
            return invoices
        latest_date = max(self._parse_date(invoice.get('invoice_date')) for invoice in dated)
        cutoff_date = latest_date - timedelta(days=self.MAX_LOOKBACK_DAYS)
        return [invoice for invoice in invoices if (self._parse_date(invoice.get('invoice_date')) or latest_date) >= cutoff_date]

    def _group_lines_by_product_and_day(self, invoice_lookup: dict, lines: list[dict], alias_map: dict):
        grouped = {}
        skipped_count = 0
        unmatched_line_count = 0

        for line in lines:
            invoice = invoice_lookup.get(line['invoice_id'])
            if not invoice:
                skipped_count += 1
                continue

            normalized_name = self._normalize_text(line.get('normalized_name') or line.get('product_name'))
            product_id = line.get('product_id') or alias_map.get(normalized_name)
            if not product_id:
                skipped_count += 1
                unmatched_line_count += 1
                continue

            invoice_date = invoice.get('invoice_date')
            if not self._parse_date(invoice_date):
                skipped_count += 1
                continue

            quantity = line.get('quantity') or 0
            if quantity <= 0:
                skipped_count += 1
                continue

            product_bucket = grouped.setdefault(product_id, {
                'days': {},
                'direct_hits': 0,
                'alias_hits': 0,
                'unmatched_line_count': 0,
            })
            if line.get('product_id'):
                product_bucket['direct_hits'] += 1
            else:
                product_bucket['alias_hits'] += 1

            day_bucket = product_bucket['days'].setdefault(invoice_date, {
                'date': invoice_date,
                'quantity': 0.0,
                'source_invoice_ids': [],
            })
            day_bucket['quantity'] += quantity
            if line['invoice_id'] not in day_bucket['source_invoice_ids']:
                day_bucket['source_invoice_ids'].append(line['invoice_id'])

        return grouped, skipped_count, unmatched_line_count

    def _build_intervals(self, merged_entries: list[dict]):
        intervals = []
        skipped_interval_count = 0

        for index in range(1, len(merged_entries)):
            previous = merged_entries[index - 1]
            current = merged_entries[index]
            previous_date = self._parse_date(previous.get('date'))
            current_date = self._parse_date(current.get('date'))
            if not previous_date or not current_date:
                skipped_interval_count += 1
                continue

            day_diff = (current_date - previous_date).days
            if day_diff <= 0:
                skipped_interval_count += 1
                continue

            previous_quantity = previous.get('quantity') or 0
            if previous_quantity <= 0:
                skipped_interval_count += 1
                continue

            rate = previous_quantity / day_diff
            intervals.append({
                'start_date': previous.get('date'),
                'end_date': current.get('date'),
                'source_start_invoice_id': previous.get('source_invoice_ids', [None])[0],
                'source_end_invoice_id': current.get('source_invoice_ids', [None])[0],
                'day_diff': day_diff,
                'rate': round(rate, 6),
                'previous_quantity': previous_quantity,
            })

        return intervals, skipped_interval_count

    def _spread_intervals_to_daily_rows(self, customer_id: str, product_id: str, intervals: list[dict]):
        rows = []
        for interval in intervals:
            start_date = self._parse_date(interval['start_date'])
            if not start_date:
                continue
            for offset in range(1, interval['day_diff'] + 1):
                target_date = start_date + timedelta(days=offset)
                rows.append({
                    'customer_id': customer_id,
                    'product_id': product_id,
                    'date': target_date.isoformat(),
                    'daily_rate': round(interval['rate'], 6),
                    'source_start_invoice_id': interval['source_start_invoice_id'],
                    'source_end_invoice_id': interval['source_end_invoice_id'],
                    'day_diff': interval['day_diff'],
                    'method': self.DAILY_METHOD,
                })
        return rows

    @staticmethod
    def _calculate_weighted_rate(intervals: list[dict]) -> float | None:
        total_days = sum(interval['day_diff'] for interval in intervals if interval.get('day_diff', 0) > 0)
        if total_days <= 0:
            return None
        weighted_sum = sum(interval['rate'] * interval['day_diff'] for interval in intervals if interval.get('day_diff', 0) > 0)
        return round(weighted_sum / total_days, 4)

    def _calculate_trend(self, intervals: list[dict]) -> str:
        rates = [interval['rate'] for interval in intervals if interval.get('rate') is not None]
        if len(rates) < 2:
            return 'stable'
        last_rate = rates[-1]
        previous_avg = self._average(rates[:-1])
        if previous_avg is None or previous_avg == 0:
            return 'stable'
        if last_rate > previous_avg * 1.1:
            return 'up'
        if last_rate < previous_avg * 0.9:
            return 'down'
        return 'stable'

    def _determine_normalization_source(self, product_group: dict) -> str:
        direct_hits = product_group.get('direct_hits', 0)
        alias_hits = product_group.get('alias_hits', 0)
        if direct_hits and alias_hits:
            return 'mixed'
        if alias_hits and not direct_hits:
            return 'alias'
        return 'direct'

    def _build_aggregate_payload(self, product_group: dict, merged_entries: list[dict], intervals: list[dict], skipped_interval_count: int):
        last_entry = merged_entries[-1] if merged_entries else None
        interval_rates = [interval['rate'] for interval in intervals]
        interval_count = len(intervals)
        payload = {
            'last_invoice_date': last_entry.get('date') if last_entry else None,
            'last_quantity': last_entry.get('quantity') if last_entry else None,
            'daily_consumption': self._average(interval_rates),
            'average_order_quantity': self._average([entry.get('quantity') for entry in merged_entries]),
            'estimated_days_to_depletion': None,
            'rate_mt_weighted': self._calculate_weighted_rate(intervals),
            'interval_count': interval_count,
            'skipped_interval_count': skipped_interval_count,
            'confidence_score': round(min(1, interval_count / 5), 4),
            'trend': self._calculate_trend(intervals),
            'invoice_count': sum(len(entry.get('source_invoice_ids', [])) for entry in merged_entries),
            'normalization_source': self._determine_normalization_source(product_group),
            'last_calculated_at': datetime.utcnow().isoformat() + 'Z',
        }
        return payload

    async def recalculate(self, customer_id: str) -> dict:
        customer = await self.repository.find_customer_by_id(customer_id)
        if not customer:
            raise ConsumptionCalculationError('Customer bulunamadı', 404)

        invoices = await self.repository.list_customer_invoices(customer_id)
        invoices = self._apply_lookback_limit(invoices)
        await self.repository.delete_customer_product_daily_consumptions(customer_id)

        if not invoices:
            return {
                'customer_id': customer_id,
                'processed_product_count': 0,
                'updated_count': 0,
                'skipped_count': 0,
            }

        invoice_lookup = {invoice['id']: invoice for invoice in invoices}
        lines = await self.repository.list_invoice_lines(list(invoice_lookup.keys()))
        alias_map = await self.repository.get_product_alias_map()
        grouped_lines, skipped_count, _unmatched_line_count = self._group_lines_by_product_and_day(invoice_lookup, lines, alias_map)

        updated_count = 0
        for product_id, product_group in grouped_lines.items():
            merged_entries = sorted(product_group['days'].values(), key=lambda item: self._parse_date(item.get('date')) or datetime.min.date())
            intervals, skipped_interval_count = self._build_intervals(merged_entries)
            daily_rows = self._spread_intervals_to_daily_rows(customer_id, product_id, intervals)
            await self.repository.bulk_upsert_customer_product_daily_consumptions(daily_rows)
            payload = self._build_aggregate_payload(product_group, merged_entries, intervals, skipped_interval_count)
            await self.repository.upsert_customer_product_consumption(customer_id, product_id, payload)
            updated_count += 1
            skipped_count += skipped_interval_count

        return {
            'customer_id': customer_id,
            'processed_product_count': len(grouped_lines),
            'updated_count': updated_count,
            'skipped_count': skipped_count,
        }

    async def list_consumption(self, customer_id: str) -> list:
        customer = await self.repository.find_customer_by_id(customer_id)
        if not customer:
            raise ConsumptionCalculationError('Customer bulunamadı', 404)

        consumptions = await self.repository.list_customer_product_consumptions(customer_id)
        product_ids = [item['product_id'] for item in consumptions]
        products = await self.repository.get_products_by_ids(product_ids)

        result = []
        for item in consumptions:
            product = products.get(item['product_id'], {})
            result.append({
                'product_id': item['product_id'],
                'product_name': product.get('name') or product.get('product_name') or item['product_id'],
                'daily_consumption': item.get('daily_consumption'),
                'average_order_quantity': item.get('average_order_quantity'),
                'last_invoice_date': item.get('last_invoice_date'),
                'last_quantity': item.get('last_quantity'),
            })
        return result
