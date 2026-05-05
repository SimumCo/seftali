from services.seftali.order_service import OrderService
from config.database import db


class StockService:
    """Thin façade for plasiyer stock endpoints."""

    @classmethod
    async def get_plasiyer_stock(cls, salesperson_id: str) -> dict:
        stock_doc = await db['plasiyer_stock'].find_one(
            {'salesperson_id': salesperson_id},
            {'_id': 0}
        )

        if not stock_doc:
            return {'success': False, 'message': 'Stok kaydı bulunamadı'}

        products_cursor = db['products'].find({}, {'_id': 0, 'product_id': 1, 'name': 1})
        products = await products_cursor.to_list(length=500)
        product_names = {product['product_id']: product['name'] for product in products}

        enriched_items = []
        for item in stock_doc.get('items', []):
            enriched_items.append({
                'product_id': item['product_id'],
                'product_name': product_names.get(item['product_id'], item['product_id']),
                'qty': item['qty']
            })

        stock_doc['items'] = enriched_items
        return {'success': True, 'data': stock_doc}

    @classmethod
    async def update_plasiyer_stock(cls, salesperson_id: str, items: list, operation: str = 'set') -> dict:
        return await OrderService.update_stock(
            salesperson_id=salesperson_id,
            items=items,
            operation=operation,
        )
