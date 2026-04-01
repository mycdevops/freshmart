import sqlite3, os, random

DATABASE = 'products.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        with open('schema.sql', 'r') as f:
            conn.cursor().executescript(f.read())
        conn.commit()

def img(seed: str) -> str:
    return f"https://picsum.photos/seed/{seed}/400/300"

def populate_db():
    # 100 curated grocery names
    names = [
        # Fruits
        "Apple Royal Gala","Banana Robusta","Orange Nagpur","Grapes Green Seedless","Mango Alphonso","Pineapple","Strawberry","Watermelon Kiran","Kiwi","Pomegranate",
        "Papaya","Guava","Lychee","Chikoo","Dragon Fruit","Blueberry","Raspberry","Blackberry","Pear","Peach",
        # Vegetables
        "Potato","Onion Red","Tomato Hybrid","Carrot","Spinach","Cucumber","Bell Pepper Yellow","Cauliflower","Broccoli","Ginger",
        "Garlic","Green Chilli","Lemon","Coriander Leaves","Curry Leaves","Beetroot","Radish","Brinjal","Okra (Lady Finger)","Cabbage",
        "Capsicum Green","Pumpkin","Bitter Gourd","Bottle Gourd","Sweet Corn","Sweet Potato","Mushroom Button","Spring Onion","Mint Leaves","Fenugreek Leaves",
        # Dairy & Eggs
        "Milk Toned 1L","Curd 500g","Eggs Brown 6 pcs","Paneer 200g","Butter Salted 100g","Cheese Slices 200g","Ghee Cow 500ml","Buttermilk 500ml","Cream 200ml","Yogurt 400g",
        # Grains & Pulses
        "Basmati Rice 1kg","Wheat Flour 1kg","Toor Dal 1kg","Moong Dal 1kg","Chana Dal 1kg","Rajma 1kg","Kabuli Chana 1kg","Poha 1kg","Rava Sooji 1kg","Besan 1kg",
        "Sona Masoori Rice 1kg","Brown Rice 1kg","Urad Dal 1kg","Masoor Dal 1kg","Moong Whole 1kg","Chana Whole 1kg","Barley 1kg","Quinoa 500g","Oats 1kg","Flattened Rice Red 1kg",
        # Spices & Masalas
        "Turmeric Powder 100g","Red Chilli Powder 100g","Coriander Powder 100g","Cumin Seeds 100g","Garam Masala 100g","Black Pepper 100g","Mustard Seeds 100g","Fenugreek Seeds 100g","Asafoetida 50g","Cardamom 50g",
        # Oils & Beverages
        "Sunflower Oil 1L","Mustard Oil 1L","Groundnut Oil 1L","Olive Oil 500ml","Tea Powder 250g","Coffee Instant 100g","Green Tea 100g","Orange Juice 1L","Lemon Juice 500ml","Coconut Water 1L",
        # Snacks Bakery Household
        "Marie Biscuits 200g","Potato Chips 50g","Bhujia 200g","Roasted Peanuts 200g","Bread White 400g","Bread Brown 400g","Pav Buns 6 pcs","Croissant 2 pcs","Bathing Soap 125g","Shampoo 200ml",
        "Toothpaste 100g","Hand Wash 250ml","Dishwash Liquid 500ml","Laundry Detergent 1kg","Floor Cleaner 1L","Toilet Cleaner 500ml","Tissue Roll 4 pcs","Aluminium Foil 10m","Garbage Bags 30 pcs","Scrub Pad Pack"
    ]

    # Ensure exactly 100
    names = names[:100]
    rows = []
    for i, name in enumerate(names, start=1):
        # Simple unit heuristic
        if any(k in name for k in ["Rice","Dal","Flour","Chana","Rajma","Poha","Rava","Besan","Quinoa","Oats","Barley"]):
            unit = "kg"
        elif "Banana" in name:
            unit = "dozen"
        elif any(k in name for k in ["Spinach","Coriander","Curry","Mint","Fenugreek","Leaves"]):
            unit = "bunch"
        elif any(k in name for k in ["Pineapple","Cauliflower","Broccoli","Croissant","Papaya","Watermelon","Pumpkin","Cabbage"]):
            unit = "piece"
        elif any(k in name for k in ["Milk","Oil","Juice","Buttermilk","Cream","Water"]):
            unit = "liter"
        elif any(k in name for k in ["Curd","Paneer","Butter","Cheese","Yogurt","Tea","Coffee","Spice","Masala","Powder","Seeds"]):
            unit = "pack"
        else:
            unit = "pack"

        desc = "Fresh and quality product"
        price = round(random.uniform(25.0, 650.0), 2)
        rows.append((name, desc, price, unit, img(f"grocery-{i}")))

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.executemany(
            'INSERT INTO products (name, description, price, unit, image_url) VALUES (?,?,?,?,?)',
            rows
        )
        conn.commit()
    print(f"Populated database with {len(rows)} products.")

if __name__ == '__main__':
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
        print(f"Removed existing {DATABASE}")
    init_db()
    populate_db()
    print("Database setup and population complete.")