import os
import requests
import streamlit as st
import streamlit as st
api_key = st.secrets["AVIATIONSTACK_API"]

def search_flights(query):
    url="https://api.aviationstack.com/v1/flights"
    params={
        "access_key":api_key,
        "limit":5
    }
    response=requests.get(url,params=params)
    data=response.json()
    flights=[]
    if "data" in data:
        for flight in data["data"][:5]:
            airline =  flight.get("airline",{}).get("name","Unknown")
            departure = flight.get("departure",{}).get("airport","Unknown")
            arrival = flight.get( "arrival",{}).get("airport","Unkown")
            status=flight.get("flight_status","Unknown")

        flights.append(
            f"""

Airline:{airline}
Departure:{departure}
Arrival:{arrival}
Status:{status}
"""
        )
    return "\n".join(flights)
