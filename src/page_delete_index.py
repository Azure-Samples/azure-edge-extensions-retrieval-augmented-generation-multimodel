import streamlit as st
import pandas as pd
import numpy as np
import sys
from marqo import Client
import logging
#logging.basicConfig(level=logging.DEBUG)

client = Client()

st.title('Index Management')
st.subheader('Delete Index')

with st.spinner(text="Loading..."):
    index_names = []
    response = client.get_indexes()

    if response != None:
        # Extract the 'index_name' values from the 'results' list
        index_names = [result["indexName"] for result in response.get("results", [])]
        # Print or use the 'index_names' as needed
        for index_name in index_names:
            print(f"Index Name: {index_name}")
    else:
        print(f"Failed to fetch indexes.")

    st.session_state.item = None
    selected_index_name = st.selectbox('Please select an index name.',index_names,index=st.session_state.item)

if st.button('Delete Index'):
    if selected_index_name == None:
        st.stop()
    else:
        with st.spinner('Deleting index...'):
            client.delete_index(selected_index_name)
            st.session_state.item = None
            st.rerun()
