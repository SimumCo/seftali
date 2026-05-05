from datetime import datetime, timedelta
from typing import Optional

from config.database import db
from services.seftali.core import gen_id, now_utc, to_iso, COL_CUSTOMERS, COL_ORDERS, COL_PRODUCTS
from services.seftali.order_service import OrderService
from services.seftali.draft_engine import DraftEngine


class SmartOrderService:
    """Thin façade for smart-order related sales flows."""

    @classmethod
    async def get_smart_orders(cls, salesperson_id: str, route_day: Optional[str] = None) -> dict:
        import math

        if not route_day:
            tomorrow = datetime.utcnow() + timedelta(days=1)
            day_codes = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
            route_day = day_codes[tomorrow.weekday()]

        now = datetime.utcnow()
        cutoff_time = now.replace(hour=16, minute=30, second=0, microsecond=0)
        is_after_cutoff = now > cutoff_time
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'

        user_doc = await db['users'].find_one({'id': salesperson_id}, {'_id': 0})
        plasiyer_region_id = user_doc.get('region_id') if user_doc else None
        plasiyer_depo_no = 'D001'

        if plasiyer_region_id:
            region_doc = await db['sf_regions'].find_one({'id': plasiyer_region_id}, {'_id': 0})
            if region_doc:
                plasiyer_depo_no = region_doc.get('depo_no', 'D001')

        cursor = db[COL_CUSTOMERS].find(
            {'is_active': True, 'route_plan.days': route_day},
            {'_id': 0}
        )
        route_customers = await cursor.to_list(length=500)

        customer_details = []
        products_cursor = db['products'].find({}, {'_id': 0})
        products_list = await products_cursor.to_list(length=500)
        products_map = {p['product_id']: p for p in products_list}

        sf_products_cursor = db[COL_PRODUCTS].find({}, {'_id': 0})
        sf_products_list = await sf_products_cursor.to_list(length=500)
        for product in sf_products_list:
            if product.get('id') not in products_map:
                products_map[product.get('id')] = product
            if product.get('product_id') not in products_map:
                products_map[product.get('product_id')] = product

        warehouse_stock_cursor = db['sf_warehouse_stock'].find(
            {'depo_no': plasiyer_depo_no},
            {'_id': 0}
        )
        warehouse_stocks = await warehouse_stock_cursor.to_list(length=500)
        warehouse_stock_map = {stock['product_id']: stock for stock in warehouse_stocks}

        plasiyer_stock_doc = await db['plasiyer_stock'].find_one(
            {'salesperson_id': salesperson_id},
            {'_id': 0}
        )
        plasiyer_stock_map = {}
        if plasiyer_stock_doc:
            for item in plasiyer_stock_doc.get('items', []):
                plasiyer_stock_map[item['product_id']] = item.get('qty', 0)

        orders_total = {}
        drafts_total = {}

        for customer in route_customers:
            customer_id = customer['id']
            customer_name = customer.get('name', 'Bilinmeyen')

            today_orders = await db[COL_ORDERS].find({
                'customer_id': customer_id,
                'status': {'$in': ['submitted', 'approved']},
                'created_at': {'$gte': today_start}
            }, {'_id': 0}).sort('created_at', -1).to_list(length=10)

            customer_items = []
            source = 'none'

            if today_orders:
                source = 'order'
                for order in today_orders:
                    for item in order.get('items', []):
                        product_id = item.get('product_id')
                        qty = item.get('qty') or item.get('user_qty') or 0
                        if product_id and qty > 0:
                            customer_items.append({
                                'product_id': product_id,
                                'qty': qty,
                                'source': 'order'
                            })
                            orders_total[product_id] = orders_total.get(product_id, 0) + qty
            else:
                source = 'draft'
                working_copy = await db['sf_working_copies'].find_one(
                    {'customer_id': customer_id, 'status': 'active'},
                    {'_id': 0}
                )

                if working_copy:
                    for item in working_copy.get('items', []):
                        product_id = item.get('product_id')
                        qty = item.get('user_qty') or item.get('qty') or 0
                        if product_id and qty > 0:
                            customer_items.append({
                                'product_id': product_id,
                                'qty': qty,
                                'source': 'working_copy'
                            })
                            drafts_total[product_id] = drafts_total.get(product_id, 0) + qty
                else:
                    system_draft = await db['sf_system_drafts'].find_one(
                        {'customer_id': customer_id},
                        {'_id': 0}
                    )
                    if system_draft:
                        for item in system_draft.get('items', []):
                            product_id = item.get('product_id')
                            qty = item.get('suggested_qty') or 0
                            if product_id and qty > 0:
                                customer_items.append({
                                    'product_id': product_id,
                                    'qty': qty,
                                    'source': 'system_draft'
                                })
                                drafts_total[product_id] = drafts_total.get(product_id, 0) + qty

            total_qty = sum(item['qty'] for item in customer_items)
            if total_qty > 0:
                customer_details.append({
                    'customer_id': customer_id,
                    'customer_name': customer_name,
                    'source': source,
                    'items': customer_items,
                    'total_qty': total_qty
                })

        all_product_ids = set(orders_total.keys()) | set(drafts_total.keys())
        final_order_items = []

        for product_id in all_product_ids:
            product = products_map.get(product_id, {})
            order_qty = orders_total.get(product_id, 0)
            draft_qty = drafts_total.get(product_id, 0)
            total_need = order_qty + draft_qty
            box_size = product.get('case_size') or product.get('box_size') or product.get('koli_adeti') or 20
            plasiyer_stock = plasiyer_stock_map.get(product_id, 0)
            net_need = max(0, total_need - plasiyer_stock)

            if box_size > 1 and net_need > 0:
                boxes_needed = math.ceil(net_need / box_size)
                final_qty = boxes_needed * box_size
            else:
                boxes_needed = net_need if box_size == 1 else 0
                final_qty = net_need

            warehouse_stock_info = warehouse_stock_map.get(product_id, {})
            warehouse_stock_qty = warehouse_stock_info.get('quantity', 0)
            warehouse_skt = warehouse_stock_info.get('skt', '') or product.get('skt', '')

            final_order_items.append({
                'product_id': product_id,
                'product_name': product.get('name', 'Bilinmeyen'),
                'product_code': product.get('code', product.get('product_id', '')),
                'order_qty': order_qty,
                'draft_qty': draft_qty,
                'total_need': total_need,
                'plasiyer_stock': plasiyer_stock,
                'net_need': net_need,
                'box_size': box_size,
                'final_qty': final_qty,
                'boxes': boxes_needed,
                'warehouse_stock': warehouse_stock_qty,
                'warehouse_skt': warehouse_skt,
            })

        final_order_items.sort(key=lambda item: item['final_qty'], reverse=True)
        order_customer_count = sum(1 for customer in customer_details if customer['source'] == 'order')
        draft_customer_count = sum(1 for customer in customer_details if customer['source'] == 'draft')

        return {
            'route_day': route_day,
            'route_day_label': {
                'MON': 'Pazartesi', 'TUE': 'Salı', 'WED': 'Çarşamba',
                'THU': 'Perşembe', 'FRI': 'Cuma', 'SAT': 'Cumartesi', 'SUN': 'Pazar'
            }.get(route_day, route_day),
            'is_after_cutoff': is_after_cutoff,
            'cutoff_time': '16:30',
            'customer_count': len(customer_details),
            'order_customer_count': order_customer_count,
            'draft_customer_count': draft_customer_count,
            'customers': customer_details,
            'order_items': final_order_items,
            'total_order_qty': sum(item['final_qty'] for item in final_order_items),
            'total_products': len(final_order_items),
            'plasiyer_depo_no': plasiyer_depo_no,
        }

    @classmethod
    async def get_warehouse_draft(cls, salesperson_id: str, route_day: Optional[str] = None) -> dict:
        return await cls.get_smart_orders(salesperson_id=salesperson_id, route_day=route_day)

    @classmethod
    async def get_smart_draft_v2(cls, salesperson_id: str) -> dict:
        customers = await db[COL_CUSTOMERS].find(
            {'is_active': True, 'salesperson_id': salesperson_id},
            {'_id': 0}
        ).sort([('updated_at', -1), ('created_at', -1)]).to_list(length=500)

        customer_results = []
        flattened_items = []
        flattened_excluded_items = []
        first_route_info = None
        first_calculation_params = None

        for customer in customers:
            draft = await DraftEngine.calculate(customer['id'])
            if not draft:
                continue

            if first_route_info is None:
                first_route_info = draft.get('route_info')
            if first_calculation_params is None:
                first_calculation_params = draft.get('calculation_params')

            customer_payload = {
                'sf_customer_id': customer['id'],
                'customer_id': customer.get('customer_id') or customer['id'],
                'customer_name': customer.get('name', ''),
                'items': draft.get('items', []),
                'excluded_items': draft.get('excluded_items', []),
                'route_info': draft.get('route_info'),
                'calculation_params': draft.get('calculation_params'),
            }
            customer_results.append(customer_payload)

            for item in draft.get('items', []):
                flattened_items.append({
                    **item,
                    'customer_id': customer_payload['customer_id'],
                    'sf_customer_id': customer_payload['sf_customer_id'],
                    'customer_name': customer_payload['customer_name'],
                })
            for item in draft.get('excluded_items', []):
                flattened_excluded_items.append({
                    **item,
                    'customer_id': customer_payload['customer_id'],
                    'sf_customer_id': customer_payload['sf_customer_id'],
                    'customer_name': customer_payload['customer_name'],
                })

        return {
            'route_day': None,
            'route_day_label': 'Müşteri Bazlı Draft',
            'customer_count': len(customer_results),
            'order_customer_count': len([c for c in customer_results if c.get('items')]),
            'draft_customer_count': len([c for c in customer_results if c.get('excluded_items')]),
            'customers': customer_results,
            'order_items': flattened_items,
            'excluded_items': flattened_excluded_items,
            'route_info': first_route_info,
            'calculation_params': first_calculation_params,
            'total_products': len(flattened_items),
            'total_order_qty': sum((item.get('final_need_qty') or item.get('need_qty') or 0) for item in flattened_items),
            'generated_from': 'smart_draft_v2',
        }

    @classmethod
    async def submit_smart_orders(cls, salesperson_id: str, note: str = '') -> dict:

        tomorrow = datetime.utcnow() + timedelta(days=1)
        day_codes = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        tomorrow_code = day_codes[tomorrow.weekday()]
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'

        cursor = db[COL_CUSTOMERS].find(
            {'is_active': True, 'route_plan.days': tomorrow_code},
            {'_id': 0}
        )
        tomorrow_customers = await cursor.to_list(length=500)

        all_items = []
        customer_details = []

        for customer in tomorrow_customers:
            customer_id = customer['id']

            today_order = await db[COL_ORDERS].find_one({
                'customer_id': customer_id,
                'status': {'$in': ['submitted', 'approved']},
                'created_at': {'$gte': today_start}
            }, {'_id': 0})

            if today_order:
                items = today_order.get('items', [])
                source = 'order'
            else:
                system_draft = await db['system_drafts'].find_one({'customer_id': customer_id}, {'_id': 0})
                items = system_draft.get('items', []) if system_draft else []
                source = 'draft'

            for item in items:
                qty = item.get('qty') or item.get('suggested_qty') or 0
                if qty > 0:
                    all_items.append({
                        'product_id': item.get('product_id'),
                        'qty': qty,
                        'customer_id': customer_id
                    })

            customer_details.append({
                'customer_id': customer_id,
                'customer_name': customer.get('name'),
                'source': source
            })

        product_totals = {}
        for item in all_items:
            product_id = item['product_id']
            product_totals[product_id] = product_totals.get(product_id, 0) + item['qty']

        now = now_utc()
        warehouse_order = {
            'id': gen_id(),
            'type': 'warehouse_order',
            'route_day': tomorrow_code,
            'submitted_by': salesperson_id,
            'submitted_at': to_iso(now),
            'note': note,
            'status': 'submitted',
            'customer_count': len(tomorrow_customers),
            'customer_details': customer_details,
            'items': [{'product_id': product_id, 'qty': qty} for product_id, qty in product_totals.items()],
            'total_qty': sum(product_totals.values()),
            'created_at': to_iso(now)
        }

        await db['warehouse_orders'].insert_one(warehouse_order)
        warehouse_order.pop('_id', None)
        return warehouse_order

    @classmethod
    async def submit_warehouse_draft(cls, salesperson_id: str, note: str = '') -> dict:
        return await cls.submit_smart_orders(salesperson_id=salesperson_id, note=note)

    @classmethod
    async def calculate_plasiyer_order(cls, salesperson_id: str, route_day: Optional[str] = None) -> dict:
        return await OrderService.calculate(salesperson_id=salesperson_id, route_day=route_day)

    @classmethod
    async def get_route_order(cls, salesperson_id: str, route_day: str) -> dict:
        valid_days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        normalized_day = route_day.upper()
        if normalized_day not in valid_days:
            raise ValueError(f"Geçersiz gün kodu. Geçerli kodlar: {', '.join(valid_days)}")
        return await OrderService.calculate(salesperson_id, normalized_day)

    @classmethod
    async def get_route_order_tomorrow(cls, salesperson_id: str) -> dict:
        return await OrderService.calculate(salesperson_id)
