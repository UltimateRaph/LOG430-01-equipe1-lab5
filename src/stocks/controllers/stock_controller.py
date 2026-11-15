"""
Product stock controller
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

from db import get_redis_conn, get_sqlalchemy_session
from flask import current_app, jsonify
from stocks.queries.read_stock import get_stock_by_id, get_stock_for_all_products
from stocks.commands.write_stock import populate_redis_from_mysql, set_stock_for_product, update_stock_mysql
from stocks.models.stock import Stock

def set_stock(request):
    """Set stock quantities of a product"""
    payload = request.get_json() or {}
    product_id = payload.get('product_id')
    quantity = payload.get('quantity')
    try:
        result = set_stock_for_product(product_id, quantity)
        return jsonify({'result': result}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_stock(request):
    """Apply a stock change for the Saga."""
    payload = request.get_json() or {}
    items = payload.get('items')
    operation = payload.get('operation')
    if operation not in ('+', '-') or not isinstance(items, list) or not items:
        return jsonify({'error': 'Indiquez des articles et une opération + ou -'}), 400
    if any(
        not isinstance(item, dict)
        or type(item.get('product_id')) is not int
        or item['product_id'] <= 0
        or type(item.get('quantity')) is not int
        or item['quantity'] <= 0
        for item in items
    ):
        return jsonify({'error': 'Chaque article doit avoir un identifiant et une quantité positifs'}), 400

    product_ids = {item['product_id'] for item in items}
    try:
        with get_sqlalchemy_session() as session, session.begin():
            update_stock_mysql(session, items, operation)
            stocks = session.query(Stock).filter(Stock.product_id.in_(product_ids)).all()
            if len(stocks) != len(product_ids) or any(stock.quantity < 0 for stock in stocks):
                raise ValueError('Stock inexistant ou insuffisant')
            quantities = {stock.product_id: stock.quantity for stock in stocks}
    except ValueError as error:
        return jsonify({'error': str(error)}), 409
    except Exception as error:
        return jsonify({'error': str(error)}), 500

    try:
        with get_redis_conn().pipeline() as pipeline:
            for product_id, quantity in quantities.items():
                pipeline.hset(f'stock:{product_id}', 'quantity', quantity)
            pipeline.execute()
    except Exception:
        # MySQL has committed the change. A cache failure cannot undo it.
        current_app.logger.exception("Le stock MySQL a changé, mais le cache Redis n'a pas été actualisé")
    return jsonify({'result': 'OK'}), 201

def get_stock(product_id):
    """Get stock quantities of a product"""
    try:
        stock = get_stock_by_id(product_id)
        return jsonify(stock), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
def get_stock_overview():
    """Get stock for all products"""
    return get_stock_for_all_products()

def populate_redis_on_startup():
    r = get_redis_conn()
    populate_redis_from_mysql(r)
