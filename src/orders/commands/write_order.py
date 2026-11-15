"""
Orders (write-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import json
from logger import Logger
from orders.models.order import Order
from stocks.models.product import Product
from sqlalchemy.exc import SQLAlchemyError
from orders.models.order_item import OrderItem
from db import get_sqlalchemy_session, get_redis_conn

logger = Logger.get_instance("add_order")

def add_order(user_id: int, items: list):
    """Insert order with items in MySQL, keep Redis in sync"""
    if not items:
        raise ValueError("Cannot create order. An order must have 1 or more items.")

    product_ids = [item['product_id'] for item in items]
    session = get_sqlalchemy_session()

    try:
        logger.debug("Commencer : ajout de commande")
        products_query = session.query(Product).filter(Product.id.in_(product_ids)).all()
        price_map = {product.id: product.price for product in products_query}
        total_amount = 0
        order_items = []
        
        for item in items:
            pid = item["product_id"]
            qty = item["quantity"]

            if pid not in price_map:
                raise ValueError(f"Product ID {pid} not found in database.")

            unit_price = price_map[pid]
            total_amount += unit_price * qty

            order_items.append({
                'product_id': pid,
                'quantity': qty,
                'unit_price': unit_price
            })

        new_order = Order(user_id=user_id, total_amount=total_amount, payment_link="", is_paid=False)
        session.add(new_order)
        session.flush()   

        order_id = new_order.id

        for item in order_items:
            order_item = OrderItem(
                order_id=order_id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                unit_price=item['unit_price']
            )
            session.add(order_item)

        session.commit()
        logger.debug("Une commande a été ajouté")

        add_order_to_redis(order_id, user_id, total_amount, items, new_order.payment_link)
        return order_id

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def modify_order(order_id: int, is_paid: bool | None, payment_link: str | None = None):
    session = get_sqlalchemy_session()
    try:
        order = session.query(Order).filter(Order.id == order_id).first()

        if order is None:
            return False
        if is_paid is not None:
            order.is_paid = is_paid
        if payment_link is not None:
            order.payment_link = payment_link

        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        print(e)
        return False
    except Exception as e:
        session.rollback()
        print(e)
        return False
    finally:
        session.close()

def delete_order(order_id: int):
    """Delete order in MySQL, keep Redis in sync"""
    session = get_sqlalchemy_session()
    try:
        order = session.query(Order).filter(Order.id == order_id).first()
        if order:

            # MySQL
            session.delete(order)
            session.commit()

            # Redis
            delete_order_from_redis(order_id)
            return 1  
        else:
            return 0  
            
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def add_order_to_redis(order_id, user_id, total_amount, items, payment_link):
    """Insert order to Redis"""
    r = get_redis_conn()
    r.hset(
        f"order:{order_id}",
        mapping={
            "user_id": user_id,
            "total_amount": float(total_amount),
            "items": json.dumps(items),
            "payment_link": payment_link
        }
    )

def delete_order_from_redis(order_id):
    """Delete order from Redis"""
    r = get_redis_conn()
    r.delete(f"order:{order_id}")
