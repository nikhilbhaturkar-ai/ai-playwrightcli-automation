import os
from pydantic import SecretStr
from langchain_groq import ChatGroq

def get_llm_model():
        try:
            groq_api_key=os.environ["GROQ_API_KEY"]
            selected_groq_model=os.environ["MODEL"]
            if groq_api_key=='' and os.environ["GROQ_API_KEY"] =='':
                raise ValueError("Groq API key and model must be set in environment variables.")
            
            llm=ChatGroq(api_key=SecretStr(groq_api_key),model=selected_groq_model)
        except Exception as e:
            raise ValueError(f"Error Ocuured With Exception : {e}")
        return llm