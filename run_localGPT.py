import os
import logging
import click
import torch
import readline
import nltk

from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceInstructEmbeddings
from langchain.llms import HuggingFacePipeline
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler  # for streaming response
from langchain.callbacks.manager import CallbackManager
from chromadb.config import Settings
from transformers import TextStreamer
from nltk.tokenize import word_tokenize

callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])

from prompt_template_utils import get_prompt_template

from langchain.vectorstores import Chroma
from transformers import (
    GenerationConfig,
    pipeline,
)

from load_models import (
    load_quantized_model_gguf_ggml,
    load_quantized_model_qptq,
    load_full_model,
)

from constants import (
    CHROMA_SETTINGS,
    EMBEDDING_MODEL_NAME,
    PERSIST_DIRECTORY,
    MODEL_ID,
    MODEL_BASENAME,
    MAX_NEW_TOKENS,
    MODELS_PATH,
    MODEL_PROMPT,
)

nltk.download('punkt')

def custom_input(end_marker='/', prompt=''):
    print(prompt, end='')
    input_lines = []
    while True:
        line = input()
        if line == end_marker:
            break
        input_lines.append(line)
    return '\n'.join(input_lines)

def load_model(device_type, model_id, model_basename=None, LOGGING=logging):
    """
    Select a model for text generation using the HuggingFace library.
    If you are running this for the first time, it will download a model for you.
    subsequent runs will use the model from the disk.

    Args:
        device_type (str): Type of device to use, e.g., "cuda" for GPU or "cpu" for CPU.
        model_id (str): Identifier of the model to load from HuggingFace's model hub.
        model_basename (str, optional): Basename of the model if using quantized models.
            Defaults to None.

    Returns:
        HuggingFacePipeline: A pipeline object for text generation using the loaded model.

    Raises:
        ValueError: If an unsupported model or device type is provided.
    """
    logging.info(f"Loading Model: {model_id}, on: {device_type}")
    logging.info("This action can take a few minutes!")

    if model_basename is not None:
        if ".gguf" in model_basename.lower():
            llm = load_quantized_model_gguf_ggml(model_id, model_basename, device_type, LOGGING)
            return llm
        elif ".ggml" in model_basename.lower():
            model, tokenizer = load_quantized_model_gguf_ggml(model_id, model_basename, device_type, LOGGING)
        else:
            model, tokenizer = load_quantized_model_qptq(model_id, model_basename, device_type, LOGGING)
    else:
        model, tokenizer = load_full_model(model_id, model_basename, device_type, LOGGING)

    # Load configuration from the model to avoid warnings
    generation_config = GenerationConfig.from_pretrained(model_id)
    # see here for details:
    # https://huggingface.co/docs/transformers/
    # main_classes/text_generation#transformers.GenerationConfig.from_pretrained.returns

    # Create a pipeline for text generation
    streamer = TextStreamer(tokenizer,skip_prompt=False)
    """
    top_k (int, optional, defaults to 50) — The number of highest probability vocabulary tokens to keep for top-k-filtering.
    top_p (float, optional, defaults to 1.0) — If set to float < 1, only the smallest set of most probable tokens with probabilities that add up to top_p or higher are kept for generation.
    temperature (float, optional, defaults to 1.0) — The value used to modulate the next token probabilities.
    repetition_penalty (float, optional, defaults to 1.0) — The parameter for repetition penalty. 1.0 means no penalty. See this paper for more details.
                                temp.	top_p.
    Code Generation		0.2	0.1	Generates code that adheres to established patterns and conventions. Output is more deterministic and focused. Useful for generating syntactically correct code.
    Creative Writing		0.7	0.8	Generates creative and diverse text for storytelling. Output is more exploratory and less constrained by patterns.
    Chatbot Responses		0.5	0.5	Generates conversational responses that balance coherence and diversity. Output is more natural and engaging.
    Code Comment Generation	0.3	0.2	Generates code comments that are more likely to be concise and relevant. Output is more deterministic and adheres to conventions.
    Data Analysis Scripting	0.2	0.1	Generates data analysis scripts that are more likely to be correct and efficient. Output is more deterministic and focused.
    Exploratory Code Writing	0.6	0.7	Generates code that explores alternative solutions and creative approaches. Output is less constrained by established patterns.
    """
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_length=MAX_NEW_TOKENS,
        do_sample=True,
        temperature=0.1,
        top_p=0.1,
        #top_k=50,
        #repetition_penalty=1.5,
        generation_config=generation_config,
        streamer=streamer,
    )

    local_llm = HuggingFacePipeline(pipeline=pipe)
    logging.info("Local LLM Loaded")

    return local_llm


def retrieval_qa_pipline(device_type, use_history, promptTemplate_type=MODEL_PROMPT):
    """
    Initializes and returns a retrieval-based Question Answering (QA) pipeline.

    This function sets up a QA system that retrieves relevant information using embeddings
    from the HuggingFace library. It then answers questions based on the retrieved information.

    Parameters:
    - device_type (str): Specifies the type of device where the model will run, e.g., 'cpu', 'cuda', etc.
    - use_history (bool): Flag to determine whether to use chat history or not.

    Returns:
    - RetrievalQA: An initialized retrieval-based QA system.

    Notes:
    - The function uses embeddings from the HuggingFace library, either instruction-based or regular.
    - The Chroma class is used to load a vector store containing pre-computed embeddings.
    - The retriever fetches relevant documents or data based on a query.
    - The prompt and memory, obtained from the `get_prompt_template` function, might be used in the QA system.
    - The model is loaded onto the specified device using its ID and basename.
    - The QA system retrieves relevant documents using the retriever and then answers questions based on those documents.
    """

    embeddings = HuggingFaceInstructEmbeddings(model_name=EMBEDDING_MODEL_NAME, model_kwargs={"device": device_type})
    # uncomment the following line if you used HuggingFaceEmbeddings in the ingest.py
    # embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # load the vectorstore
    db = Chroma(
        persist_directory=PERSIST_DIRECTORY,
        embedding_function=embeddings,
        client_settings=CHROMA_SETTINGS,
    )
    retriever = db.as_retriever()

    # get the prompt template and memory if set by the user.
    prompt, memory = get_prompt_template(promptTemplate_type=promptTemplate_type, history=use_history)
    # load the llm pipeline
    llm = load_model(device_type, model_id=MODEL_ID, model_basename=MODEL_BASENAME, LOGGING=logging)


    if use_history:
        qa = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",  # try other chains types as well. refine, map_reduce, map_rerank
            return_source_documents=False,  # verbose=True,
            callbacks=callback_manager,
            chain_type_kwargs={"prompt": prompt, "memory": memory},
            retriever=retriever,
        )
    else:
        qa = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",  # try other chains types as well. refine, map_reduce, map_rerank
            return_source_documents=False,  # verbose=True,
            callbacks=callback_manager,
            chain_type_kwargs={"prompt": prompt},
            retriever=retriever,
        )

    return qa

def count_tokens(text):
    tokens = word_tokenize(text)
    return len(tokens)

# chose device typ to run on as well as to show source documents.
@click.command()
@click.option(
    "--device_type",
    default="cuda" if torch.cuda.is_available() else "cpu",
    type=click.Choice(
        [
            "cpu",
            "cuda",
            "ipu",
            "xpu",
            "mkldnn",
            "opengl",
            "opencl",
            "ideep",
            "hip",
            "ve",
            "fpga",
            "ort",
            "xla",
            "lazy",
            "vulkan",
            "mps",
            "meta",
            "hpu",
            "mtia",
        ],
    ),
    help="Device to run on. (Default is cuda)",
)
@click.option(
    "--show_sources",
    "-s",
    is_flag=True,
    help="Show sources along with answers (Default is False)",
)
@click.option(
    "--use_history",
    "-h",
    is_flag=True,
    help="Use history (Default is False)",
)

def main(device_type, show_sources, use_history):
    """
    Implements the main information retrieval task for a localGPT.

    This function sets up the QA system by loading the necessary embeddings, vectorstore, and LLM model.
    It then enters an interactive loop where the user can input queries and receive answers. Optionally,
    the source documents used to derive the answers can also be displayed.

    Parameters:
    - device_type (str): Specifies the type of device where the model will run, e.g., 'cpu', 'mps', 'cuda', etc.
    - show_sources (bool): Flag to determine whether to display the source documents used for answering.
    - use_history (bool): Flag to determine whether to use chat history or not.

    Notes:
    - Logging information includes the device type, whether source documents are displayed, and the use of history.
    - If the models directory does not exist, it creates a new one to store models.
    - The user can exit the interactive loop by entering "exit".
    - The source documents are displayed if the show_sources flag is set to True.

    """

    logging.info(f"Running on: {device_type}")
    logging.info(f"Display Source Documents set to: {show_sources}")
    logging.info(f"Use history set to: {use_history}")

    # check if models directory do not exist, create a new one and store models here.
    if not os.path.exists(MODELS_PATH):
        os.mkdir(MODELS_PATH)

    qa = retrieval_qa_pipline(device_type, use_history, promptTemplate_type=MODEL_PROMPT)
    # Interactive questions and answers

    logging.getLogger().setLevel(logging.ERROR)

    while True: 
        #query = input("\nTrue's AI query: ").strip()
        query = custom_input(prompt="True's AI query multiline (Press '/' followed by Enter to finish)\n").strip()
        if query == "exit":
            break
        if query == "":
            continue
        in_tokens = count_tokens(query)
        print("<<<< True's AI answer >>>>")
        res = qa(query)
        out_tokens = count_tokens(str(res))
        total_token = in_tokens + out_tokens
        # print(res["result"])
        print("\nTotal Token:",total_token,", Price:",round(total_token*0.00222,2),"Baht")

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s", level=logging.INFO
    )
    main()
