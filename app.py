import os

import pinecone
import streamlit as st
from langchain.chains import RetrievalQA, RetrievalQAWithSourcesChain
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone

from service.env import OPENAI_API_KEY, PINECONE_API_KEY
from service.stream_handler import StreamHandler

pinecone.init(api_key=PINECONE_API_KEY, environment="us-west4-gcp")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

embeddings = OpenAIEmbeddings()
my_index = "eth-org-website-index"
docsearch = Pinecone.from_existing_index(my_index, embeddings)

model_temp = 0
model_name_functions = "gpt-3.5-turbo-0613"
model_name_main = "gpt-3.5-turbo"
model_name = model_name_main

from langchain.chains import RetrievalQA, RetrievalQAWithSourcesChain
from langchain.chat_models import ChatOpenAI

# Initialize the ChatOpenAI and RetrievalQAWithSourcesChain instances

llm = ChatOpenAI(
    temperature=model_temp,
    model_name=model_name,
    request_timeout=180,
    streaming=True,
)


# QA chain will always complete chat response e.g. can improvise and translate into different languages
qa_with_sources_chat = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=docsearch.as_retriever(),
    return_source_documents=True,
)  # RETURN FORMAT = [query, result, source_documents[]]

# QA chain will NOT improvise e.g. only provide answers derived from source information
qa_with_sources = RetrievalQAWithSourcesChain.from_chain_type(
    llm=llm, chain_type="stuff", retriever=docsearch.as_retriever()
)  # RETURN FORMAT = [question, answer, sources]


customize_response = True
st.title("ChatGPT-like clone")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask your question about Web3 here"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant") as chat_message:
        message_placeholder = st.empty()
        stream_handler = StreamHandler(message_placeholder, display_method="markdown")
        llm.callbacks = [stream_handler]
        full_response = (
            qa_with_sources_chat(prompt)
            if customize_response
            else qa_with_sources(prompt)
        )

        source_list = "\n".join(
            [f"* {doc.metadata['source']}" for doc in full_response["source_documents"]]
        )
        source_text = "\n\n**Sources:**\n" + source_list
        stream_handler.append_text(source_text)

        combined_content = f"{full_response['result']} {source_text}"

        st.session_state.messages.append(
            {"role": "assistant", "content": combined_content}
        )
