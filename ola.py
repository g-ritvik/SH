"""
14th April 2025,
Prototype to showcase features of Stealth Habits web idea, using OLA API. Only for INDIA.
"""

# Libraries
import streamlit as st
import geocoder
import joblib
import requests
import uuid
import pandas as pd
import time
import pydeck as pdk

# Cuisine types based on Hyderabad's Restaurants
cuisine_options = ["Biryani", "Mandi", "North Indian", "South Indian",
    "Chinese", "Italian", "Continental", "Hyderabadi", "Mughlai", "Arabian"]
unwanted_cuisines = ['cafe', 'General-Store', 'Sweets']

# OLA API key
api_key = "uGrU3zH16DY2SouyKbtYcnTm63GdTDIFDCpA85yh"

# Loading pre-trained restaurants from hyderabad to predict cuisines
tfidf = joblib.load("tfidf_vectorizer.pkl")
mlb = joblib.load("label_binarizer.pkl")
model = joblib.load("cuisine_predictor.pkl")

# User's geolocation
g = geocoder.ip("me")

latlng = g.latlng
city = g.city
state = g.state
country = g.country

# Setting default to Hyderabad if user is not in India
if country != "IN":
    latlng = [17.491774, 78.295813]
    city = "Hyderabad"
    state = "Telangana"
    country = "India"

@st.cache_data(show_spinner=False)
def get_lat_lng(place_id):
    lt_url = "https://api.olamaps.io/places/v1/details/advanced"

    params = {
        "place_id": place_id,
        "api_key": api_key
    }

    headers = {
        "X-Request-Id": str(uuid.uuid4()),
        "X-Correlation-Id": str(uuid.uuid4())
    }

    try:
        response = requests.get(lt_url, headers=headers, params=params)
        data = response.json()
        if "result" in data and "geometry" in data["result"]:
            location = data["result"]["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]
            return f"{lat}, {lng}"
        else:
            return "NA"
    except Exception as e:
        print(f"Error for {place_id}: {e}")
        return "NA"


# Calling api
location = str(latlng[0]) + ", " + str(latlng[1])
res_params = {
    "location": location,
    "types": "restaurant",
    "radius": 5000,             # in meters
    "withCentroid": "false",
    "rankBy": "popular",
    "limit": 15,
    "api_key": api_key
}

cafe_params = {
    "location": location,
    "types": "cafe",
    "radius": 5000,             # in meters
    "withCentroid": "false",
    "rankBy": "popular",
    "limit": 15,
    "api_key": api_key
}

bar_params = {
    "location": location,
    "types": "bar",
    "radius": 5000,             # in meters
    "withCentroid": "false",
    "rankBy": "popular",
    "limit": 15,
    "api_key": api_key
}

headers = {
    "X-Request-Id": str(uuid.uuid4()),
    "X-Correlation-Id": str(uuid.uuid4())
}

url = "https://api.olamaps.io/places/v1/nearbysearch/advanced"

# Making Request
@st.cache_data(show_spinner=False)
def fetch_places(params):
    return requests.get(url, headers=headers, params=params).json()

res_response = fetch_places(res_params)
cafe_response = fetch_places(cafe_params)
bar_response = fetch_places(bar_params)

predictions = res_response.get('predictions', []) + cafe_response.get('predictions', []) + bar_response.get('predictions', [])
name = []
distance = []
ola_id = []
open_now = []
pic = []

for place in predictions:
    name.append(place.get('structured_formatting', {}).get('main_text'))
    distance.append(place.get('distance_meters'))
    ola_id.append(place.get('place_id'))
    open_now.append(place.get('opening_hours', {}).get('open_now'))
    pic.append(place.get('photos'))

X_test = tfidf.transform(name)
preds = model.predict(X_test)
predicted_cuisines = mlb.inverse_transform(preds)

df = pd.DataFrame({
    'name': name,
    'cuisine': predicted_cuisines,
    'distance': distance,
    'ola-id': ola_id,
    'open-now': open_now,
    'pics': pic
})

df["lat_lng"] = df["ola-id"].apply(lambda pid: get_lat_lng(pid))
# Remove rows with 'NA' lat_lng
df = df[df['lat_lng'] != 'NA']

# Split lat_lng into separate columns
df[['latitude', 'longitude']] = df['lat_lng'].str.split(', ', expand=True).astype(float)


# Details of locations

st.set_page_config(page_title="Stealth Habits Feature Prototype", page_icon="🍽️")

# Initialize session state if not already
if "page" not in st.session_state:
    st.session_state.page = "login"

# Page 1: Login Form
def login_page():
    st.markdown("<h1 style='text-align: center; color: #ff991c;'>🍽️ Stealth Habits</h1>", unsafe_allow_html=True)
    st.subheader("Login to continue")

    with st.form("login_form"):
        full_name = st.text_input("Full Name")
        username = st.text_input("Username")
        email_or_mobile = st.text_input("Email or Mobile Number")
        submitted = st.form_submit_button("Submit")

        if submitted:
            if full_name and username and email_or_mobile:
                st.form_submit_button("Send OTP")
                st.session_state.page = "otp"
                st.session_state.username = username
            else:
                st.error("Please fill in all fields.")

    st.badge("⚠️ Things to consider for beta version", color="red")
    st.markdown(":red-badge[Login options with Google, Yahoo, and Apple Mail should be clickable and allow direct login.]"
                ":red-badge[Need a way to send real OTPs to users for secure authentication.]"
                ":red-badge[Store user details in our DB and check for duplicate usernames during registration.]")

# Page 2: OTP Page
def otp_page():
    st.markdown("<h1 style='text-align: center; color: #ff991c;'>🍽️ Stealth Habits</h1>", unsafe_allow_html=True)
    st.title("🔐 Verify OTP")
    st.write(f"Enter the OTP sent to {st.session_state.username}.")

    otp_input = st.text_input("OTP", max_chars=6)
    if st.button("Verify"):
        if otp_input:
            st.success("✅ Logged in successfully!")
            st.session_state.page = "diet"
            st.rerun()
        else:
            st.error("Please enter the OTP.")

    st.badge("⚠️ Things to consider for beta version", color="red")
    st.markdown(":red-badge[Need to find a way to send actual OTPs to the user.] ")


# Page 3: Cuisines Page
def diet_pref():
    st.markdown("<h1 style='text-align: center; color: #ff991c;'>🍽️ Stealth Habits</h1>", unsafe_allow_html=True)
    st.title("Dietary Preferences")
    st.header("Diet Choices")

    if "diet_type" not in st.session_state:
        st.session_state.diet_type = None

    if "selected_cuisines" not in st.session_state:
        st.session_state.selected_cuisines = []

    veg = st.checkbox("Vegetarian", key="veg")
    non_veg = st.checkbox("Non-Vegetarian", key="non_veg")
    pure_veg = st.checkbox("Pure Vegetarian", key="pure_veg")

    # Update selected dietary types
    st.session_state.diet_types = []
    if veg: st.session_state.diet_types.append("Vegetarian")
    if non_veg: st.session_state.diet_types.append("Non-Vegetarian")
    if pure_veg: st.session_state.diet_types.append("Pure Vegetarian")

    if st.session_state.diet_types:
        st.success("Selected Dietary Type(s): " + ", ".join(st.session_state.diet_types))

    st.subheader("Select Up to 5 Cuisines You Enjoy")

    cols = st.columns(4)
    for idx, cuisine in enumerate(cuisine_options):
        with cols[idx % 4]:
            if cuisine not in st.session_state.selected_cuisines:
                if st.button(cuisine):
                    if len(st.session_state.selected_cuisines) < 5:
                        st.session_state.selected_cuisines.append(cuisine)
                    else:
                        st.warning("You can only select up to 5 cuisines.")
            else:
                if st.button(f"✅ {cuisine}"):
                    st.session_state.selected_cuisines.remove(cuisine)

    if st.session_state.selected_cuisines:
        st.success("Selected Cuisines: " + ", ".join(st.session_state.selected_cuisines))

    # --- Save Button ---
    if "preferences_saved" not in st.session_state:
        st.session_state.preferences_saved = False

    if st.button("Save Preferences"):
        if not st.session_state.diet_types:
            st.error("Please select at least one dietary type.")
        elif not st.session_state.selected_cuisines:
            st.error("Please select at least one cuisine.")
        else:
            st.success("✅ Preferences saved successfully!")
            st.session_state.preferences_saved = True
            st.rerun()

    if st.session_state.preferences_saved:
        if st.button("Continue"):
            st.session_state.page = "home"
            st.rerun()

    st.badge("⚠️ Things to consider for beta version", color="red")
    st.markdown(":red-badge[Display more cuisine types — currently limited options.]"
                ":red-badge[Cuisine options should be dynamic and change based on user’s location.]")


def home():
    st.markdown("<h4 style='text-align: left; color: #ff991c;'>🍽️ Stealth Habits</h1>", unsafe_allow_html=True)
    st.caption(f"{city}, {state}")

    st.warning("Data Frame displayed only for prototype purpose.")
    st.dataframe(df)

    # Create a DataFrame for the user's current location
    user_location_df = pd.DataFrame({
        'latitude': [latlng[0]],
        'longitude': [latlng[1]],
        'name': ['Your Location'],
        'cuisine': ['You are here']
    })

    # pydeck map with two layers: one for restaurants, one for user
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/streets-v11',
        initial_view_state=pdk.ViewState(
            latitude=latlng[0],
            longitude=latlng[1],
            zoom=13,
            pitch=45
        ),
        layers=[
            # Restaurants, cafes, bars
            pdk.Layer(
                'ScatterplotLayer',
                data=df,
                get_position='[longitude, latitude]',
                get_radius=100,
                get_color='[255, 140, 0, 160]',  # Orange
                pickable=True,
            ),
            # User location (blue)
            pdk.Layer(
                'ScatterplotLayer',
                data=user_location_df,
                get_position='[longitude, latitude]',
                get_radius=150,
                get_color='[30, 144, 255, 200]',  # Dodger Blue
                pickable=True,
            )
        ],
        tooltip={"text": "{name} - {cuisine}"}
    ))

    if st.button("Sample Individual restaurant page."):
        st.session_state.page = "sample"

    st.badge("⚠️ Things to consider for beta version", color="red")
    st.markdown(":red-badge[User's live location displayed on top left corner; if user is not located in India, default to Hyderabad.]"
                ":red-badge[Currently using IP to fetch user location, need to use device's GNSS. ]"
                ":red-badge[The Cuisines displayed are predicted using ML models, needs more training data for better predictions.]"
                ":red-badge[Lack of pictures from restaurants, bars and cafes.]"
                ":red-badge[Each entry should be called again using Advance Details request API to fetch its Locations.]"
                ":red-badge[Need to Cache data session wise to prevent API exhaustion]"
                ":red-badge[Need friendly and interactive UI.]"
                ":red-badge[OLA-API isn't clean, general stores, Milk booths are shown under restaurant request data, need filtering using ML.]"
                ":red-badge[Need to add review system, can make map dynamic; clicking on the restaurant, cafe or bar will redirect to a more detailed page to give reviews, ratings, photos.]"
                ":red-badge[Add users contacts as friend recommendation to increase networking.]"
                ":red-badge[Introduce regional languages - Built for India.]")


def sample():
    # Sample Restaurant Data (you'll dynamically load this later)
    restaurant = {
        "name": "Pavan's Pakodi",
        "latitude": 17.4567,
        "longitude": 78.4335,
        "phone": "+91-70755 62349",
        "cuisines": ["South Indian"],
        "is_veg": True,
        "reviews": [
            {"user": "Gajala", "rating": 4.5, "comment": "Thope Pakoda, Nothing like this in Washington DC"},
            {"user": "Jaya Surya", "rating": 3.0, "comment": "Good Good Fantastic!!"},
            {"user": "Idly Vishwanath", "rating": 1.0, "comment": "Pakodi oddhu Idly muddhu"}
        ]
    }

    # Display Restaurant Info
    st.title(restaurant["name"])
    st.markdown(f"📍 **Location:** {restaurant['latitude']}, {restaurant['longitude']}")
    st.markdown(f"📞 **Phone:** {restaurant['phone']}")
    st.markdown(f"🍽️ **Cuisines:** {', '.join(restaurant['cuisines'])}")
    st.markdown(f"🥗 **Type:** {'Veg' if restaurant['is_veg'] else 'Non-Veg'}")

    st.divider()

    # Sample Reviews & Ratings
    st.subheader("🗣️ Reviews & Ratings")
    for review in restaurant["reviews"]:
        st.markdown(f"**{review['user']}** - ⭐ {review['rating']}/5")
        st.markdown(f"_{review['comment']}_")
        st.markdown("---")

    st.divider()

    # Report an Issue
    st.subheader("🚩 Report an Issue")
    report_options = [
        "Cuisine tag is missing",
        "Cuisine tag is incorrect",
        "Restaurant is permanently closed",
        "Location seems wrong",
        "Phone number is incorrect",
        "Suggest additional cuisine tags",
        "Other (please specify below)"
    ]

    selected_issues = st.multiselect("What's wrong with this listing?", report_options)

    other_feedback = ""
    if "Other (please specify below)" in selected_issues:
        other_feedback = st.text_area("Describe the issue")

    if st.button("Submit Report"):
        st.success("✅ Thanks! We’ll review your report and update the listing.")
        # Here you could append the report to a DB or send it via email etc.

    st.badge("⚠️ Things to consider for beta version", color="red")
    st.markdown(":red-badge[User should be able to post rating, review and photo.]"
                ":red-badge[Reviews have to be refreshed every 15 days.]")

    # Render appropriate page
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "otp":
    otp_page()
elif st.session_state.page == "diet":
    diet_pref()
elif st.session_state.page == "home":
    home()
elif st.session_state.page == "sample":
    sample()
