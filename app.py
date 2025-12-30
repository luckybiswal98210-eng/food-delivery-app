import streamlit as st
from supabase import create_client, Client
import os

# ---------- SETTINGS ----------
USD_TO_INR = 90  # 1 USD ≈ ₹90, change if you want

# Page config
st.set_page_config(
    page_title="FoodCosta - Food Delivery",
    page_icon="🍕",
    layout="wide"
)

# Initialize Supabase client
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Initialize session state
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'selected_restaurant' not in st.session_state:
    st.session_state.selected_restaurant = None
if 'show_checkout' not in st.session_state:
    st.session_state.show_checkout = False
if 'show_front_page' not in st.session_state:
    st.session_state.show_front_page = True  # front page shown first

# ----- CSS: only things that apply everywhere (buttons, fonts etc.) -----
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pacifico&display=swap');

/* ===== GLOBAL VISIBILITY FIX ===== */
[data-testid="stMarkdownContainer"] *,
[data-testid="stText"] *,
.foodcosta-title,
.foodcosta-subtitle,
.main-block,
.main-block * {
    color: #000 !important;
    font-weight: 700 !important;
    text-shadow: 0 2px 6px rgba(0,0,0,0.25) !important;
    position: relative;
    z-index: 10;
}

/* ===== FRONT CARD ===== */
.main-block {
    background: rgba(255,255,255,0.98) !important;
    padding: 2rem;
    border-radius: 1rem;
}

/* ===== TITLES ===== */
.foodcosta-title {
    font-family: 'Pacifico', cursive;
    font-size: 4rem;
    color: #ff7043 !important;
    text-align: center;
}
.foodcosta-subtitle {
    font-size: 1.3rem;
    text-align: center;
    color: #111 !important;
}

/* ===== BUTTON ===== */
.stButton>button {
    width: 100%;
    background: #FF6B35;
    color: white !important;
    border-radius: 8px;
    padding: 10px;
    border: none;
    font-weight: 700;
}
.stButton>button:hover { background: #FF5722; }

/* ===== PRICE / RATING ===== */
.price-tag { color:#FF6B35 !important; font-size:24px; font-weight:bold; }
h1 { color:#FF6B35 !important; }
.rating { color:#FFC107 !important; }
</style>
""", unsafe_allow_html=True)


# ---------- Helper functions ----------

def usd_to_inr(amount_usd: float) -> float:
    return amount_usd * USD_TO_INR

def format_inr(amount_usd: float) -> str:
    inr = usd_to_inr(amount_usd)
    return f"₹{inr:,.0f}"

def get_restaurants():
    """Fetch all restaurants from Supabase"""
    try:
        response = supabase.table('restaurants').select('*').execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching restaurants: {e}")
        return []

def get_menu_items(restaurant_id):
    """Fetch menu items for a restaurant"""
    try:
        response = supabase.table('menu_items').select('*').eq('restaurant_id', restaurant_id).execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching menu items: {e}")
        return []

def add_to_cart(item):
    """Add item to cart"""
    item_id = item['id']
    if item_id in st.session_state.cart:
        st.session_state.cart[item_id]['quantity'] += 1
    else:
        st.session_state.cart[item_id] = {
            'item': item,
            'quantity': 1
        }
    st.success(f"Added {item['name']} to cart!")

def update_cart_quantity(item_id, delta):
    """Update cart item quantity"""
    if item_id in st.session_state.cart:
        st.session_state.cart[item_id]['quantity'] += delta
        if st.session_state.cart[item_id]['quantity'] <= 0:
            del st.session_state.cart[item_id]

def get_cart_total_usd():
    """Calculate cart total in USD (from DB prices)"""
    total = 0
    for item_data in st.session_state.cart.values():
        total += item_data['item']['price'] * item_data['quantity']
    return total

def get_cart_total_inr():
    return usd_to_inr(get_cart_total_usd())

def get_cart_count():
    """Get total items in cart"""
    return sum(item['quantity'] for item in st.session_state.cart.values())

def place_order(customer_info):
    """Place order in Supabase"""
    try:
        # Store total in INR
        order_data = {
            'customer_name': customer_info['name'],
            'customer_email': customer_info['email'],
            'customer_phone': customer_info['phone'],
            'delivery_address': customer_info['address'],
            'total_amount': get_cart_total_inr(),
            'status': 'pending'
        }
        order_response = supabase.table('orders').insert(order_data).execute()
        order_id = order_response.data[0]['id']
        
        # Create order items (store INR price)
        order_items = []
        for item_data in st.session_state.cart.values():
            order_items.append({
                'order_id': order_id,
                'menu_item_id': item_data['item']['id'],
                'quantity': item_data['quantity'],
                'price': usd_to_inr(item_data['item']['price'])
            })
        
        supabase.table('order_items').insert(order_items).execute()
        
        # Clear cart
        st.session_state.cart = {}
        st.session_state.show_checkout = False
        
        return True, order_id
    except Exception as e:
        return False, str(e)

# ============== FRONT PAGE ==============
if st.session_state.show_front_page:
    st.markdown(
        """
        <style>
        .stApp {
            background-image: url("https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=1400");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }

        .welcome-overlay {
            background: rgba(255, 255, 255, 0.82);
            min-height: 100vh;
            padding: 3rem 1rem;
        }

        .welcome-inner {
            max-width: 900px;
            margin: 0 auto;
        }

        .main-block {
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 1rem;
        }
        </style>

        <div class="welcome-overlay">
          <div class="welcome-inner">
            <div class="foodcosta-title">Welcome to FoodCosta</div>
            <div class="foodcosta-subtitle">
              Your favorite food, freshly prepared and delivered fast.
            </div>
            <div class="main-block">
              <h3>Start your food journey 🍽️</h3>
              <p>Browse delicious restaurants and add your favorites to the cart.</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Button must be rendered by Streamlit, but still within the visual card
    if st.button("Explore FoodCosta 🚀"):
        st.session_state.show_front_page = False
        st.rerun()

# ============== MAIN APP (no background image) ==============
else:
    # Remove background image for the rest of the app (plain light background)
    st.markdown("""
        <style>
        .stApp {
            background-image: none !important;
            background-color: #fafafa;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        st.title("🍕 FoodCosta")
    with col2:
        search_term = st.text_input(
            "🔍 Search",
            placeholder="Search restaurants or food...",
            label_visibility="collapsed"
        )
    with col3:
        cart_count = get_cart_count()
        if st.button(f"🛒 Cart ({cart_count})"):
            st.session_state.show_checkout = True

    st.markdown("---")

    # Main content
    if st.session_state.show_checkout:
        # Checkout page
        st.header("🛒 Your Cart")
        
        if len(st.session_state.cart) == 0:
            st.info("Your cart is empty")
            if st.button("← Back to Restaurants"):
                st.session_state.show_checkout = False
                st.rerun()
        else:
            # Display cart items
            for item_id, item_data in st.session_state.cart.items():
                item = item_data['item']
                quantity = item_data['quantity']
                
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.markdown(f"**{item['name']}**")
                    st.caption(item['description'])
                with col2:
                    st.markdown(
                        f"<span class='price-tag'>{format_inr(item['price'])}</span>",
                        unsafe_allow_html=True
                    )
                with col3:
                    st.write(f"Qty: {quantity}")
                with col4:
                    col_minus, col_plus = st.columns(2)
                    with col_minus:
                        if st.button("➖", key=f"minus_{item_id}"):
                            update_cart_quantity(item_id, -1)
                            st.rerun()
                    with col_plus:
                        if st.button("➕", key=f"plus_{item_id}"):
                            update_cart_quantity(item_id, 1)
                            st.rerun()
                
                st.markdown("---")
            
            # Total (INR)
            st.markdown(
                f"### Total: <span class='price-tag'>{format_inr(get_cart_total_usd())}</span>",
                unsafe_allow_html=True
            )
            
            # Customer information form
            st.subheader("📝 Delivery Information")
            
            with st.form("checkout_form"):
                name = st.text_input("Full Name*", placeholder="John Doe")
                email = st.text_input("Email*", placeholder="john@example.com")
                phone = st.text_input("Phone*", placeholder="+91 98765 43210")
                address = st.text_area(
                    "Delivery Address*",
                    placeholder="123 Main St, City, State, PIN"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    submit = st.form_submit_button("Place Order 🚀")
                with col2:
                    cancel = st.form_submit_button("← Back to Menu")
                
                if submit:
                    if not all([name, email, phone, address]):
                        st.error("Please fill in all fields")
                    else:
                        customer_info = {
                            'name': name,
                            'email': email,
                            'phone': phone,
                            'address': address
                        }
                        success, result = place_order(customer_info)
                        if success:
                            st.success(f"🎉 Order placed successfully! Order ID: {result}")
                            st.balloons()
                            st.info("Your order will be delivered soon!")
                        else:
                            st.error(f"Error placing order: {result}")
                
                if cancel:
                    st.session_state.show_checkout = False
                    st.rerun()

    elif st.session_state.selected_restaurant:
        # Menu page
        restaurant = st.session_state.selected_restaurant
        
        if st.button("← Back to Restaurants"):
            st.session_state.selected_restaurant = None
            st.rerun()
        
        # Restaurant header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.header(restaurant['name'])
            st.write(restaurant['description'])
        with col2:
            st.markdown(
                f"<span class='rating'>⭐ {restaurant['rating']}</span>",
                unsafe_allow_html=True
            )
            st.caption(f"🕒 {restaurant['delivery_time']}")
        
        st.markdown("---")
        st.subheader("📋 Menu")
        
        # Fetch and display menu items
        menu_items = get_menu_items(restaurant['id'])
        
        if search_term:
            menu_items = [
                item for item in menu_items
                if search_term.lower() in item['name'].lower()
            ]
        
        # Display menu in grid
        cols = st.columns(3)
        for idx, item in enumerate(menu_items):
            with cols[idx % 3]:
                st.image(item['image_url'], use_container_width=True)
                st.markdown(f"**{item['name']}**")
                st.caption(item['description'])
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        f"<span class='price-tag'>{format_inr(item['price'])}</span>",
                        unsafe_allow_html=True
                    )
                with col2:
                    if st.button("Add to Cart", key=f"add_{item['id']}"):
                        add_to_cart(item)
                        st.rerun()
                st.markdown("---")

    else:
        # Restaurants list page (after front page)
        st.header("🏪 Popular Restaurants")
        
        restaurants = get_restaurants()
        
        if search_term:
            restaurants = [
                r for r in restaurants
                if search_term.lower() in r['name'].lower()
            ]
        
        cols = st.columns(4)
        for idx, restaurant in enumerate(restaurants):
            with cols[idx % 4]:
                st.image(restaurant['image_url'], use_container_width=True)
                st.markdown(f"**{restaurant['name']}**")
                st.caption(restaurant['description'])
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        f"<span class='rating'>⭐ {restaurant['rating']}</span>",
                        unsafe_allow_html=True
                    )
                with col2:
                    st.caption(f"🕒 {restaurant['delivery_time']}")
                
                if st.button("View Menu", key=f"restaurant_{restaurant['id']}"):
                    st.session_state.selected_restaurant = restaurant
                    st.rerun()
                
                st.markdown("---")
