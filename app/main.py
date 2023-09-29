from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse

import pandas as pd
import json
import os

# Load model directly
my_fastapi_app = FastAPI()

DOCUMENT_STORE_PATH = "documents"
HISTORY_STORE_PATH = "chat_histories"


@my_fastapi_app.get("/")
def home():
    return {"message": "Doc Chat is Live"}


############################################################################################################
###################### Document Store
############################################################################################################


@my_fastapi_app.post("/add_source")
async def add_source(file: UploadFile, user_id: str, doc_id: str = None):
    if not os.path.exists(DOCUMENT_STORE_PATH):
        os.mkdir(DOCUMENT_STORE_PATH)
    if not os.path.exists(os.path.join(DOCUMENT_STORE_PATH, user_id)):
        os.mkdir(os.path.join(DOCUMENT_STORE_PATH, user_id))

    file_path = os.path.join(
        DOCUMENT_STORE_PATH,
        user_id,
        file.filename
        if doc_id is None
        else doc_id,  # save the file as doc_id if provided, else save it as it's original name
    )

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "filename": file.filename if doc_id is None else doc_id,
        "saved_path": file_path,
    }


@my_fastapi_app.get("/list_sources")
def list_sources(user_id: str):
    if not os.path.exists(DOCUMENT_STORE_PATH):
        return []
    if not os.path.exists(os.path.join(DOCUMENT_STORE_PATH, user_id)):
        return []
    return os.listdir(os.path.join(DOCUMENT_STORE_PATH, user_id))


@my_fastapi_app.get("/delete_source")
def delete_source(user_id: str, doc_id: str):
    os.remove(os.path.join(DOCUMENT_STORE_PATH, user_id, doc_id))
    return {
        "status": "success",
        "message": f"Document deleted for the user {user_id} and doc {doc_id}",
    }


@my_fastapi_app.get("/get_source", response_class=FileResponse)
async def get_source(user_id: str, doc_id: str):
    return os.path.join(DOCUMENT_STORE_PATH, user_id, doc_id)


############################################################################################################
###################### Response Generation
############################################################################################################


@my_fastapi_app.get("/generate")
def query(
    query: str,
    user_id: str,
    doc_id: str,
    temperature: float = 0.5,
    answer_length: int = 512,
):
    # TODO: If number of current reuests > 1, wait

    response = "Generated Response"
    messages = read_message_history(user_id, doc_id=doc_id)["messages"]
    messages.append({"role": "user", "content": query})
    messages.append({"role": "assistant", "content": response})

    if len(messages) == 3:  # (System prompt, user query, system response)
        chat_title = "Very Interesting Chat Title"
        write_message_history(user_id, doc_id, messages, chat_title=chat_title)
    else:
        write_message_history(user_id, doc_id, messages)

    return response


@my_fastapi_app.get("/regenerate_last_response")
def regenerate_last_response(user_id: str, doc_id: str):
    messages = read_message_history(user_id, doc_id)["messages"]
    last_user_query = messages[-2]["content"]
    messages = remove_last_qa_from_history(messages)

    response = "Generated Response"
    messages.append({"role": "user", "content": query})
    messages.append({"role": "assistant", "content": response})

    write_message_history(user_id, doc_id, messages)

    return response


############################################################################################################
###################### Chat History
############################################################################################################

# Sample Chat History
# {
#     "user_id": "user1",
#     "doc_id": "doc1",
#     "doc_summary": "This is a summary of the document",
#     "chat_title": "This is the title of the chat",
#     "messages": [
#         {
#             "role": "system",
#             "content": "You a helpful assistant. Your task is to answer the user's qustions to your best ability without lying or making up information.",
#         },
#         {"role": "user", "content": "Who is the President of Pakistan?"},
#         {
#             "role": "assistant",
#             "content": "The current President of Pakistan is Arif Alvi",
#         },
#         {"role": "user", "content": "Tell me more about him!"},
#     ],
# }


def read_message_history(user_id: str, doc_id: str):
    if os.path.exists("chat_histories"):
        history_name = user_id + "_" + doc_id + ".json"
        history_files = os.listdir("chat_histories")
        if history_name in history_files:
            with open(f"chat_histories/{history_name}") as f:
                return json.load(f)
    return {
        "user_id": user_id,
        "doc_id": doc_id,
        "doc_summary": "Document Summary",
        "chat_title": "Chat Title",
        "messages": [],
    }


def write_message_history(
    user_id: str, doc_id: str, messages: list[dict], chat_title: str = None
):
    if not os.path.exists("chat_histories"):
        os.mkdir("chat_histories")

    message_history = read_message_history(user_id, doc_id)
    message_history["messages"] = messages
    if chat_title is not None:
        message_history["chat_title"] = chat_title

    with open(f"chat_histories/{user_id}_{doc_id}.json", "w") as f:
        json.dump(message_history, f)


def remove_last_qa_from_history(messages: list[dict]):
    return messages[:-2]


@my_fastapi_app.get("/get_chat_history")
def return_chat_history(user_id: str, doc_id: str):
    return read_message_history(user_id, doc_id)


@my_fastapi_app.get("/delete_chat_history")
def delete_chat_history(user_id: str, doc_id: str):
    message_history = read_message_history(user_id, doc_id)
    message_history["messages"] = []
    write_message_history(user_id, doc_id, message_history)
    return {
        "status": "success",
        "message": f"Chat history deleted for the user{user_id} and doc {doc_id}",
    }


############################################################################################################
###################### Chat Title
############################################################################################################


@my_fastapi_app.get("/get_chat_title")
def get_chat_title(user_id: str, doc_id: str):
    return read_message_history(user_id, doc_id)["chat_title"]


@my_fastapi_app.get("/edit_chat_title")
def edit_chat_title(user_id: str, doc_id: str, new_chat_title: str):
    history = read_message_history(user_id, doc_id)
    write_message_history(
        user_id, doc_id, history["messages"], chat_title=new_chat_title
    )
    return {
        "status": "success",
        "message": f"Chat title updated for the user {user_id} and doc {doc_id}",
    }


############################################################################################################
###################### Document Summary
############################################################################################################


@my_fastapi_app.get("/get_doc_summary")
def get_doc_summary(user_id: str, doc_id: str):
    message_history = read_message_history(user_id, doc_id)
    if message_history.get("doc_summary") is None:
        message_history[
            "doc_summary"
        ] = "This document has very interesting things in it :)"
        write_message_history(user_id, doc_id, message_history)

    return message_history["doc_summary"]


############################################################################################################
###################### Streaming generation
############################################################################################################

# TODO: API endpoint to get streaming response from model


@my_fastapi_app.get("/stop_streaming")
def stop_streaming(user_id: str, doc_id: str):
    ## model.stop_streaming(user_id, doc_id)
    return {
        "status": "success",
        "message": f"Streaming stopped for the user {user_id} and doc {doc_id}",
    }


# TODO: API endpoint to simplify the last response
