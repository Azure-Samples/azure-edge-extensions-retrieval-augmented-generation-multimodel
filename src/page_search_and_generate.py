import streamlit as st
import os
import subprocess
import sys
import requests
from urllib.parse import urlparse, unquote
from marqo import Client
import pprint
from pathlib import Path
import glob
import subprocess
#logging.basicConfig(level=logging.DEBUG)

#default values. optional
default_image_url_search_query = f""
default_user_text_query = "All LEDs are off, how to fix?" 
default_mm_query_img_weight = 1.0
default_mm_query_txt_weight = 1.0
# MARQO PARAMS
device = 'cpu' # use 'cuda' if a GPU is available
client = Client()

# LLAVA PARAMS
PROMPT = '''
According to this image, the problem is:
SEARCH_QUERY_HERE

Here is the guidance:
The machine type: MACHINE_TYPE_HERE
The issue case: CASE_TYPE_HERE
The recommended actions:RECOMMENDED_ACTION_HERE
'''

#***********************change the path relevant to web path*****************
LLAVA_EXEC_PATH = "../llava/llava-cli "
MODEL_PATH = "../llava/models/ggml-model-q4_k.gguf"
MMPROJ_PATH = "../llava/models/mmproj-model-f16.gguf"

TEMP = 0.1
bash_command = f'{LLAVA_EXEC_PATH} -m {MODEL_PATH} --mmproj {MMPROJ_PATH} --temp {TEMP}'

def run_search(mm_search_query,selected_index_name):
    try:
        results = client.index(selected_index_name).search(mm_search_query, attributes_to_retrieve=['Images_http', 'Machine_type', 'Recommended_actions'], device=device, limit=1)
        pprint.pprint(results)
        return results
    except Exception as e:
        print(e)
        return None

def run_llava(image_paths, prompt):
    output_list = []
    for image_path in image_paths:
        print(f"Processing {image_path}")
        bash_command_cur = f'{bash_command}  -p "{prompt}" --image "{image_path}"' 
        # run the bash command
        process = subprocess.Popen(
            bash_command_cur, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # get the output and error from the command
        output, error = process.communicate()

        return_code = process.returncode
        if return_code != 0:
            print(error.decode("utf-8"))
            print(f"Return code: {return_code}")
        if return_code == 0:
            output_list.append(output)

    print("Done")
    return output_list

def clean_generated_text(llava_output_list):
    image_text_cleaned = []

    for text_index, image_text in enumerate(llava_output_list):
        image_text_split = image_text.decode("utf-8").split("\n")

        # find index of the line that starts with prompt:
        start_index_list = [
            i for i, line in enumerate(image_text_split) if line.startswith("encode_image_with_clip:")
        ]

        if (
            len(start_index_list) == 0
        ):
            # there was a problem with image text
            print(f"Warning: start indices couldn't be found for document {text_index}")
            continue

        start_index = start_index_list[-1]

        # extract the text based on indices above
        image_text_cleaned.append(
            "".join(image_text_split[start_index + 1 : ]).strip()
        )
    return image_text_cleaned

def download_image(image_url):
    # create a new directory
    new_directory = "./images-query/temp"
    if os.path.exists(new_directory):
    # If it exists, remove the existing directory
        try:
            os.rmdir(new_directory)
            print(f"Existing directory '{new_directory}' removed successfully.")
        except Exception as e:
            print(f"Error removing existing directory '{new_directory}': {e}")
    # Create the new directory
    try:
        os.makedirs(new_directory)
        print(f"New directory '{new_directory}' created successfully.")
    except Exception as e:
        print(f"Error creating new directory '{new_directory}': {e}")

    # Parse the URL to get the image name
    parsed_url = urlparse(image_url)
    image_name = os.path.basename(unquote(parsed_url.path))
    image_path = os.path.join(new_directory, image_name)
    # Download the image
    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        # Save the image to the local path
        with open(image_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=128):
                file.write(chunk)
        print(f"Image downloaded successfully to {image_path}")
        return image_path
    else:
        print(f"Failed to download image. Status code: {response.status_code}")
        return None

def query_retrieval():
    st.title('Please input your question and press enter for suggested solution:')
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

    user_text_query = st.text_input('please input your question')
    image_url_search_query = st.text_input('please input your image url')
    # visualize the image
    if image_url_search_query:
        st.image(image_url_search_query, caption='User Input Image Query', width =200)
    st.info("A weighting of 1.0 gives this query a neutral effect.\n a higher weighting, e.g. 2.5, gives results more similar to this. \nA negative weighting makes it less likely to appear.")
    mm_query_txt_weight = st.text_input('please input the weight for your question', value=default_mm_query_txt_weight)
    mm_query_img_weight = st.text_input('please input the weight for your image query', value=default_mm_query_img_weight)
    # If the user hits enter
    if user_text_query and image_url_search_query and st.button('Search'):
        with st.spinner(text="Document Searching..."):
            mm_search_query = {user_text_query:mm_query_txt_weight, image_url_search_query:mm_query_img_weight} 
            mm_search_results = run_search(mm_search_query,selected_index_name)
            Recommended_actions = mm_search_results['hits'][0]['Recommended_actions']
            Machine_type = mm_search_results['hits'][0]['Machine_type']
            Case_type = mm_search_results['hits'][0]['_id']
            Search_score = mm_search_results['hits'][0]['_score']

            st.info(f"The search result from multimodal vector DB:\n")
            retrieval_result = f'SEARCH_QUERY: {mm_search_query}' + "\n" + f'SEARCH_CONTENT: {mm_search_results}'
            st.write(f"{retrieval_result}\n\n")

        with st.spinner(text="Solution Generating..."):
            # run llava using local image path
            image_path_search_query = download_image(image_url_search_query) #work
            image_paths = [image_path_search_query]
            llava_prompt = PROMPT.replace('SEARCH_QUERY_HERE', user_text_query).replace('MACHINE_TYPE_HERE', Machine_type).replace('CASE_TYPE_HERE', Case_type).replace('RECOMMENDED_ACTION_HERE', Recommended_actions)
            print("llava_prompt",llava_prompt)   
            llava_output_list = run_llava(image_paths, llava_prompt)
            image_text_cleaned = clean_generated_text(llava_output_list)
            st.info(f"The generated solution from LMM:\n")
            for i in range(len(image_text_cleaned)):
                print(f"Image {i}: {image_text_cleaned[i]}")
                st.write(f"{image_text_cleaned[i]}\n\n")


if __name__ == "__main__":
    query_retrieval()

