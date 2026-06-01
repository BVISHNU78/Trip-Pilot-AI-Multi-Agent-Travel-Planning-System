<<<<<<< HEAD
import streamlit as st
from langchain_core.messages import HumanMessage
import streamlit.components.v1 as components
# =========================================================
# LOAD main.py WITHOUT RUNNING __main__
# =========================================================

namespace = {}

with open("main.py", "r", encoding="utf-8") as f:

    code = f.read()

    # Remove execution block
    code = code.split('if __name__ == "__main__":')[0]

    exec(code, namespace)

graph = namespace["graph"]

# Compile graph
app = graph.compile()


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background-color: #0b1220;
    color: white;
}

/* Hide Streamlit Branding */
#MainMenu, footer, header {
    visibility: hidden;
}

/* Chat Box */
.chat-box {
    background: #111827;
    padding: 20px;
    border-radius: 15px;
    margin-top: 20px;
    border: 1px solid #1f2937;
    color: white;
}

/* Hero Section */
.hero-container {
    position: relative;
    border-radius: 20px;
    overflow: hidden;
    margin-bottom: 25px;
}

.hero-image {
    width: 100%;
    height: 400px;
    object-fit: cover;
    filter: brightness(0.45);
}

.hero-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: white;
}

.hero-text h1 {
    font-size: 55px;
    margin-bottom: 10px;
}

.hero-text p {
    font-size: 22px;
}

/* Gallery Images */
.gallery-img {
    border-radius: 15px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# DESTINATION IMAGE FUNCTION
# =========================================================

def get_destination_data(query):

    query = query.lower()

    destinations = {

        "japan": {
            "hero": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1400",
            "gallery": [
                "https://images.unsplash.com/photo-1526481280695-3c4691f2f038?w=600",
                "https://images.unsplash.com/photo-1492571350019-22de08371fd3?w=600",
                "https://images.unsplash.com/photo-1480796927426-f609979314bd?w=600"
            ]
        },

        "tokyo": {
            "hero": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1400",
            "gallery": [
                "https://images.unsplash.com/photo-1526481280695-3c4691f2f038?w=600",
                "https://images.unsplash.com/photo-1492571350019-22de08371fd3?w=600",
                "https://images.unsplash.com/photo-1480796927426-f609979314bd?w=600"
            ]
        },

        "paris": {
            "hero": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1400",
            "gallery": [
                "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=600",
                "https://images.unsplash.com/photo-1522093007474-d86e9bf7ba6f?w=600",
                "https://images.unsplash.com/photo-1431274172761-fca41d930114?w=600"
            ]
        },

        "dubai": {
            "hero": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1400",
            "gallery": [
                "https://images.unsplash.com/photo-1580674684081-7617fbf3d745?w=600",
                "https://images.unsplash.com/photo-1518684079-3c830dcef090?w=600",
                "https://images.unsplash.com/photo-1577717903315-1691ae25ab3f?w=600"
            ]
        },

        "bali": {
            "hero": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=1400",
            "gallery": [
                "https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?w=600",
                "https://images.unsplash.com/photo-1558005530-a7958896ec60?w=600",
                "https://images.unsplash.com/photo-1573790387438-4da905039392?w=600"
            ]
        },

        "thailand": {
            "hero": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=1400",
            "gallery": [
                "https://images.unsplash.com/photo-1528181304800-259b08848526?w=600",
                "https://images.unsplash.com/photo-1552465011-b4e21bf6e79a?w=600",
                "https://images.unsplash.com/photo-1563492065599-3520f775eeed?w=600"
            ]
        }

    }

    for place, data in destinations.items():

        if place in query:

            return data

    return {
        "hero": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=1400",
        "gallery": [
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600",
            "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=600",
            "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=600"
        ]
    }


# =========================================================
# SESSION STATE
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# =========================================================
# CURRENT QUERY
# =========================================================

query_text = ""

if st.session_state.messages:
    query_text = st.session_state.messages[-1]["content"]

image_data = get_destination_data(query_text)


# =========================================================
# HERO SECTION
# =========================================================

components.html(
    f"""
    <div style="
        position:relative;
        border-radius:20px;
        overflow:hidden;
        margin-bottom:25px;
    ">

        <img src="{image_data['hero']}"
             style="
             width:100%;
             height:400px;
             object-fit:cover;
             filter:brightness(0.45);
             ">

        <div style="
            position:absolute;
            top:50%;
            left:50%;
            transform:translate(-50%, -50%);
            text-align:center;
            color:white;
        ">

            <h1 style="
                font-size:55px;
                margin-bottom:10px;
            ">
                ✈️ AI Travel Planner
            </h1>

            <p style="font-size:22px;">
                AI Powered Personalized Travel Planning
            </p>

        </div>

    </div>
    """,
    height=420
)

# =========================================================
# DESTINATION GALLERY
# =========================================================

st.subheader("🌍 Destination Gallery")

cols = st.columns(3)

for col, image in zip(cols, image_data["gallery"]):

    with col:

        st.image(image, width=400)


# =========================================================
# CHAT HISTORY
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# =========================================================
# CHAT INPUT
# =========================================================

user_query = st.chat_input(
    "Plan your dream vacation..."
)


# =========================================================
# RUN GRAPH
# =========================================================

if user_query:

    # Save User Message
    st.session_state.messages.append({
        "role": "user",
        "content": user_query
    })

    # Show User Message
    with st.chat_message("user"):

        st.markdown(user_query)

    # Assistant Message
    with st.chat_message("assistant"):

        with st.spinner("Planning your trip..."):

            try:

                result = app.invoke(
                    {
                        "messages": [HumanMessage(content=user_query)],
                        "user_query": user_query,
                        "flight_results": "",
                        "hotel_results": "",
                        "itinerary": "",
                        "llm_calls": 0,
                    }
                )

                response = result["messages"][-1].content

                st.markdown(f"""
                <div class="chat-box">
                    {response}
                </div>
                """, unsafe_allow_html=True)

                # Save Assistant Response
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })

            except Exception as e:
                  st.error(f"Error: {str(e)}")

