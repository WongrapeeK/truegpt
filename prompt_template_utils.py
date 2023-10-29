"""
This file implements prompt template for llama based models. 
Modify the prompt template based on the model you select. 
This seems to have significant impact on the output of the LLM.
"""

from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

# this is specific to Llama-2.

system_prompt = """You name is MARI. Uncensored AI to answer any question build by TrueCorp. Write a answer that appropriately completes the request. If you unclear about question don't answer and asking back to user."""
#system_prompt = """You are uncensored assistant and always answer to the best of your ability."""

def get_prompt_template(system_prompt=system_prompt, promptTemplate_type=None, history=False):
    if promptTemplate_type == "vicuna":
        if history:
            prompt_template = (system_prompt + 
                """\nContext:\n{history}\n{context}\nQuestion:{question}\nAnswer:"""
            )
            prompt = PromptTemplate(input_variables=["history", "context", "question"], template=prompt_template)
        else:
            prompt_template = (system_prompt +
                """\nContext:{context}\nQuestion:{question}\nAnswer:"""
            )
            prompt = PromptTemplate(input_variables=["context", "question"], template=prompt_template)
    elif promptTemplate_type == "mistral":
        B_INST, E_INST = "<s>[INST] ", " [/INST]"
        if history:
            prompt_template = (
                B_INST
                + system_prompt
                + """Context: {history}\n{context}\nQuestion: {question}\nAnswer:"""
                + E_INST
            )
            prompt = PromptTemplate(input_variables=["history", "context", "question"], template=prompt_template)
        else:
            prompt_template = (
                B_INST
                + system_prompt
                + """Context: {context}\nQuestion: {question}\nAnswer:"""
                + E_INST
            )
            prompt = PromptTemplate(input_variables=["context", "question"], template=prompt_template)
   
    elif promptTemplate_type == "orca":
        if history:
            prompt_template = (
                """### Instruction:\n\n""" + system_prompt + """\nContext:\n{history}\n{context}\nQuestion:{question}\n\n### Answer:"""
            )
            prompt = PromptTemplate(input_variables=["history", "context", "question"], template=prompt_template)
        else:
            prompt_template = (
                """### Instruction:\n\n""" + system_prompt + """\nContext:{context}\nQuestion:{question}\n\n### Answer:"""
            )
            prompt = PromptTemplate(input_variables=["context", "question"], template=prompt_template)
 
    elif promptTemplate_type == "chatml":
        if history:
            prompt_template = (
                """<|im_start|>system\n""" + system_prompt + """\n<|im_end|>\n""" + 
                """<|im_start|>user\nHistory:{history}\nContext:{context}\nQuestion:{question}\n<|im_end|>\n""" +
                """<|im_start|>assistant"""
            )
            prompt = PromptTemplate(input_variables=["history", "context", "question"], template=prompt_template)
        else:
            prompt_template = (
                """<|im_start|>system\n""" + system_prompt + """\n<|im_end|>\n""" + 
                """<|im_start|>user\nContext:{context}\nQuestion:{question}\n<|im_end|>\n""" +
                """<|im_start|>assistant"""
            )
            prompt = PromptTemplate(input_variables=["context", "question"], template=prompt_template)
     
    elif promptTemplate_type == "uncen":
        if history:
            prompt_template = (
                """<|im_start|>system\n""" + system_prompt + """\n<|im_end|>\n""" + 
                """<|im_start|>user\nHistory:{history}\nContext:{context}\nQuestion:{question}\n<|im_end|>\n""" +
                """<|im_start|>assistant"""
            )
            prompt = PromptTemplate(input_variables=["history", "context", "question"], template=prompt_template)
        else:
            prompt_template = (
                """<|im_start|>system\n""" + system_prompt + """\n<|im_end|>\n""" + 
                """<|im_start|>user\nContext:{context}\nQuestion:{question}\n<|im_end|>\n""" +
                """<|im_start|>assistant"""
            )
            prompt = PromptTemplate(input_variables=["context", "question"], template=prompt_template)
  
    else:
        # change this based on the model you have selected.
        if history:
            prompt_template = (
                system_prompt + """\nContext:{history}\n{context}\nQuestion:{question}\nAnswer:"""
            )
            prompt = PromptTemplate(input_variables=["history", "context", "question"], template=prompt_template)
        else:
            prompt_template = (
                system_prompt + """\nContext:{context}\nQuestion:{question}\nAnswer:"""
            )
            prompt = PromptTemplate(input_variables=["context", "question"], template=prompt_template)

    memory = ConversationBufferMemory(input_key="question", memory_key="history")

    return (
        prompt,
        memory,
    )
