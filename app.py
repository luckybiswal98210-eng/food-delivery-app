import streamlit as st
from supabase import create_client, Client
import os

# Page config
st.set_page_config(
    page_title="FoodCosta - Food Delivery",
    page_icon="🍕",
    layout="wide"
)

# Global CSS: background + custom font + buttons
st.markdown("""
    <style>
    /* Load a handwritten-style font */
    @import url('https://fonts.googleapis.com/css2?family=Pacifico&display=swap');

    /* App background */
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=1600");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* Translucent card for main content on home page */
    .main-block {
        background: rgba(255, 255, 255, 0.88);
        padding: 2rem;
        border-radius: 1rem;
    }

    /* Big handwritten welcome text */
    .foodcosta-title {
        font-family: 'Pacifico', cursive;
        font-size: 3.5rem;
        color: #ff5722;
        text-align: center;
        text-shadow: 2px 2px 5px rgba(0,0,0,0.25);
        margin-top: 0.5rem;
        margin-bottom: 0.25rem;
    }

    .foodcosta-subtitle {
        font-size: 1.1rem;
        text-align: center;
        color: #ffffff;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.4);
        margin-bottom: 2rem;
    }

    /* Button styling */
    .stButton>button {
        width: 100%;
        background-color: #FF6B35;
        color: white;
        border-radius: 8px;
        padding: 10px;
        border: none;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #FF5722;
    }

    /* Price + rating styling */
    .price-tag {
        color: #FF6B35;
        font-size: 24px;
        font-weight: bold;
    }
    h1 {
        color: #FF6B35;
    }
    .rating {
        color: #FFC107;
    }
    </style>
""", unsafe_allow_html=True)

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

# Helper functions
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

def get_cart_total():
    """Calculate cart total"""
    total = 0
    for item_data in st.session_state.cart.values():
        total += item_data['item']['price'] * item_data['quantity']
    return total

def get_cart_count():
    """Get total items in cart"""
    return sum(item['quantity'] for item in st.session_state.cart.values())

def place_order(customer_info):
    """Place order in Supabase"""
    try:
        # Create order
        order_data = {
            'customer_name': customer_info['name'],
            'customer_email': customer_info['email'],
            'customer_phone': customer_info['phone'],
            'delivery_address': customer_info['address'],
            'total_amount': get_cart_total(),
            'status': 'pending'
        }
        order_response = supabase.table('orders').insert(order_data).execute()
        order_id = order_response.data[0]['id']
        
        # Create order items
        order_items = []
        for item_data in st.session_state.cart.values():
            order_items.append({
                'order_id': order_id,
                'menu_item_id': item_data['item']['id'],
                'quantity': item_data['quantity'],
                'price': item_data['item']['price']
            })
        
        supabase.table('order_items').insert(order_items).execute()
        
        # Clear cart
        st.session_state.cart = {}
        st.session_state.show_checkout = False
        
        return True, order_id
    except Exception as e:
        return False, str(e)

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
                    f"<span class='price-tag'>${item['price']:.2f}</span>",
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
        
        # Total
        total = get_cart_total()
        st.markdown(
            f"### Total: <span class='price-tag'>${total:.2f}</span>",
            unsafe_allow_html=True
        )
        
        # Customer information form
        st.subheader("📝 Delivery Information")
        
        with st.form("checkout_form"):
            name = st.text_input("Full Name*", placeholder="John Doe")
            email = st.text_input("Email*", placeholder="john@example.com")
            phone = st.text_input("Phone*", placeholder="+1 234 567 8900")
            address = st.text_area(
                "Delivery Address*",
                placeholder="123 Main St, City, State, ZIP"
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
                    f"<span class='price-tag'>${item['price']:.2f}</span>",
                    unsafe_allow_html=True
                )
            with col2:
                if st.button("Add to Cart", key=f"add_{item['id']}"):
                    add_to_cart(item)
                    st.rerun()
            st.markdown("---")

else:
    # Front page + Restaurants page
    st.markdown(
        '<div class="foodcosta-title">Welcome to FoodCosta</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="foodcosta-subtitle">'
        'Your favorite food, freshly prepared and delivered fast.'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="main-block">', unsafe_allow_html=True)
    st.header("🏪 Popular Restaurants")
    
    restaurants = get_restaurants()
    
    if search_term:
        restaurants = [
            r for r in restaurants
            if search_term.lower() in r['name'].lower()
        ]
    
    # Display restaurants in grid
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
    st.markdown('</div>', unsafe_allow_html=True)
