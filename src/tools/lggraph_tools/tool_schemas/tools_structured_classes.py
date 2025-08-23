# it gonna carried out the classes that will be used to get the information of the tools and used by the agent
from pydantic import Field, BaseModel


# --- register tools (structured classes)  -----------

class TranslationMessage(BaseModel):
    message: str = Field(
        description="The message to translate. Provide the text you want to translate into the targeted language."
    )

    target_language: str = Field(
        description="The language to translate the message into. Use ISO 639-1 codes (e.g., 'en' for English, 'hi' for Hindi)."
    )


class google_search(BaseModel):
    query: str = Field(
        description="Search query for GoogleSearch. Use this to find information on the web. provide a clear and concise query.",
    )


class rag_search_message(BaseModel):
    query: str = Field(
        description="the query for the RAG search, Provide the meaningful query to search in the knowledge base. with no special characters or symbols. or json objects",
    )



class run_shell_command_message(BaseModel):
    command: str = Field(
        description="The shell command or bash script to execute. You have full control over the shell environment,"
                    " allowing you to run custom commands, scripts, or complex shell operations."
                    " Provide a valid shell command or the path to a bash script for execution.",
    )
    capture_output: bool = Field(
        description="Set to True to capture and return the output of the executed command or script."
                    " If False, output will not be captured.",
        default=True
    )
    creation_flag : bool = Field(
        description="Set True if you want user interaction with the command in a new console window",
        default=False
    )
