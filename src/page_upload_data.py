import streamlit as st
from urllib.request import urlretrieve
import sys
from marqo import Client
import logging
import pandas as pd
#logging.basicConfig(level=logging.DEBUG)

client = Client()

account_url = ""
sas_token = ""  # Replace with the SAS token from your URL
container_name = ""
blob_name = ""
local_file_path = "./demo_dataset.csv" # the multimodal dataset csv file will be downloaded to this path
# Construct the URL with the SAS token
url_with_sas = f"{account_url}/{container_name}/{blob_name}?{sas_token}"
N = 13 # samples to use
device = 'cpu' # use 'cuda' if a GPU is available

st.title('Upload Multimodal documents for Vector Search')

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
    st.write('You selected:', selected_index_name)

    url_with_sas = st.text_input("Please input document's Blob Storage URL with the format: https://<storage_acc_name>.blob.core.windows.net/<container_name>/<blob_name>?<sas_token>")

if st.button('Upload'):
    if selected_index_name == None or url_with_sas == None:
        st.stop()
    else:
        with st.spinner(text="Downloading multimodal file..."):
            # Download the file to local current directory
            urlretrieve(url_with_sas, local_file_path)
            st.info("The multimodal document was downloaded to local path: " + local_file_path)
            data = pd.read_csv(local_file_path, nrows=N)

        with st.spinner(text="Document uploading..."):
            if data is not None:
                data['_id'] = data['Title']
                documents = data[['Images_http', 'Title', 'Symptoms', '_id', "Machine_type", "Recommended_actions"]].to_dict(orient='records')
                print(documents[1])
                tensor_fields = ['Images_http', 'Title', 'Symptoms'] #`_id` field cannot be a tensor field.
                try:
                    res = client.index(selected_index_name).add_documents(
                        documents, 
                        tensor_fields=tensor_fields, 
                        device=device
                    )
                    print(res)
                    print("The doc was uploaded to the index %s!" % index_name)
                    st.info("The doc was uploaded to the index %s!" % index_name)
                except Exception as e:
                    print(e)
                    st.error(e)
            else:
                st.error("The document is empty!")

        st.success("done!")
