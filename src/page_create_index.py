import streamlit as st
import pandas as pd
import numpy as np
import sys
from marqo import Client
import logging
#logging.basicConfig(level=logging.DEBUG)

#marqo client
client = Client()
#client = Client(url='http://localhost:8882')
settings = {
    "treat_urls_and_pointers_as_images": True,
    "model": "open_clip/ViT-L-14/laion2b_s32b_b82k",
    "normalize_embeddings": True
}

st.title('Index Management')
st.subheader('Create Index')
index_name = st.text_input('Please input an index name that you want to create')

if st.button('Create Index'):
    if index_name == '':
        st.error('Please input index name!')
        st.stop()
    else:
        with st.spinner('Creating index...'):
            try:
                response = client.create_index(index_name, **settings)
                print(response)
                print("multimodal index \"%s\" was created!" % index_name)
                st.info("multimodal index \"%s\" was created!" % index_name)
            except Exception as e:
                print(e)
                st.error(e)

            st.success("done!")
