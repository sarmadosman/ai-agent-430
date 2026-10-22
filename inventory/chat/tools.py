from decimal import Decimal

from django.db.models import F
from .models import Item

def check_price(name):
    """Look up price of an item in the inventory."""
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    return {"name": item.name, "price": str(item.price), "quantity": item.quantity}
    


def check_stock(name):
    """Look up how many of an item we have."""
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    return {"name": item.name, "quantity": item.quantity}


def list_items():
    """Return every item in the inventory."""
    items = Item.objects.all()
    return {"items": [{"name": i.name, "quantity": i.quantity} for i in items]}


def add_item(name, quantity):
    """Create a new item, or add to an existing one's stock."""
    if quantity <= 0:
        return {"error": "Quantity must be positive."}

    item = Item.objects.filter(name__iexact=name).first()
    if item is not None:
        Item.objects.filter(id=item.id).update(quantity=F('quantity') + quantity)
        item.refresh_from_db()
        return {"name": item.name, "quantity": item.quantity, "created": False}

    try:
        item = Item.objects.create(name=name, quantity=quantity)
        return {"name": item.name, "quantity": item.quantity, "created": True}
    except Exception:
        item = Item.objects.filter(name__iexact=name).first()
        if item:
            Item.objects.filter(id=item.id).update(quantity=F('quantity') + quantity)
            item.refresh_from_db()
            return {"name": item.name, "quantity": item.quantity, "created": False}
        return {"error": f"Could not add item '{name}'."}


def remove_stock(name, quantity):
    """Take a quantity out of stock."""
    if quantity <= 0:
        return {"error": "Quantity must be positive."}

    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    if quantity > item.quantity:
        return {
            "error": f"Cannot remove {quantity}. Only {item.quantity} in stock.",
            "name": item.name,
            "quantity": item.quantity,
        }

    Item.objects.filter(id=item.id).update(quantity=F('quantity') - quantity)
    item.refresh_from_db()
    return {"name": item.name, "quantity": item.quantity}


def delete_item(name):
    """Remove an item from the inventory entirely."""
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    item.delete()
    return {"deleted": name}


def increase_price_by_percentage(name, percentage):
    """Increase the price of an item by a given percentage."""
    if percentage <= 0:
        return {"error": "Percentage must be positive."}

    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}

    old_price = item.price
    multiplier = 1 + Decimal(str(percentage)) / 100
    new_price = (old_price * multiplier).quantize(Decimal("0.01"))
    Item.objects.filter(id=item.id).update(price=new_price)
    item.refresh_from_db()

    return {
        "name": item.name,
        "old_price": str(old_price),
        "new_price": str(item.price),
        "percentage_increase": percentage
    }


TOOL_DECLARATIONS = [
    {
        "type": "function",
        "name": "check_stock",
        "description": "Look up the current quantity of a single item in the inventory. Use this whenever the user asks whether something is in stock or how many there are.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item, e.g. 'Hammer'.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "type": "function",
        "name": "list_items",
        "description": "Return every item in the inventory with its quantity. Use this when the user asks what is in stock generally, or asks for a list, rather than about one specific item.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "add_item",
        "description": "Add stock to the inventory. If the item does not exist it is created; if it already exists the quantity is added to the existing total. Use this for restocking and for new deliveries.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item, e.g. 'Hammer'.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "How many units to add. Must be positive.",
                },
            },
            "required": ["name", "quantity"],
        },
    },
    {
        "type": "function",
        "name": "remove_stock",
        "description": "Reduce the quantity of an existing item. Use this when items are sold, shipped or used. This does NOT delete the item; it only lowers the number.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item, e.g. 'Hammer'.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "How many units to remove. Must be positive.",
                },
            },
            "required": ["name", "quantity"],
        },
    },
    {
        "type": "function",
        "name": "delete_item",
        "description": "Permanently remove an item and its record from the inventory entirely. This is destructive. Only use it when the user clearly wants the item gone, not when they want to reduce its quantity.",
        "parameters": {
            "type": "object",
            "properties": {

                "name": {
                    "type": "string",
                    "description": "The name of the item to delete.",
                },
            },
            "required": ["name"],
        },
    },
    {
            "type": "function",
            "name": "check_price",
            "description": "Look up the current price of a single item in the inventory. Use this whenever the user asks about the price of an item with potentially the quantity and potentially calculated with VAT.",
            "parameters": {
                "type": "object",
                "properties": {

                    "name": {
                        "type": "string",
                        "description": "The name of the item we want the price of.",
                    },
                },
                "required": ["name"],
            },
    },
    {
        "type": "function",
        "name": "increase_price_by_percentage",
        "description": "Increase the price of an item by a given percentage. Use this when the user wants to raise an item's price. It cannot lower prices.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item to increase the price of, e.g. 'Hammer'.",
                },
                "percentage": {
                    "type": "number",
                    "description": "The percentage to increase the price by. Must be positive. For example, 10 means a 10% increase.",
                },
            },
            "required": ["name", "percentage"],
        },
    },
]

TOOL_FUNCTIONS = {
    "check_stock": check_stock,
    "list_items": list_items,
    "add_item": add_item,
    "remove_stock": remove_stock,
    "delete_item": delete_item,
    "check_price": check_price,
    "increase_price_by_percentage": increase_price_by_percentage
}
