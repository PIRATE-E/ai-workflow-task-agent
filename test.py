import json
import re

import duckduckgo_search.exceptions
import langchain_core.exceptions
from langchain.agents import initialize_agent, AgentType
from langchain_core.output_parsers import PydanticOutputParser
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate

import tools
from custom_output_parser import FlexibleOutputParser

# class ModelOutPut(BaseModel):
#     summary: str
#     words: int
#
#
# parser_llm = PydanticOutputParser(pydantic_object=ModelOutPut)
# llm = OllamaLLM(model="deepseek-r1:7b")
llm = OllamaLLM(
    model="llava-llama3:latest",
    format="json",  # Request JSON format when supported
    temperature=0.1,  # Lower temperature for more consistent output
    # Removed conflicting stop parameter
)
#
# this is for chaining which do not have tool calling capability
# prompt_llm_temp = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             "You are a helpful assistant"
#             "Always return your final answer as a JSON object with ... fields."
#             # "Respond ONLY with a valid JSON object with two fields: "
#             # "\"summary\" (the summary text) and \"words\" (the number of words in the summary). "
#             # "Example: {{\"summary\": \"This is a summary.\", \"words\": 4}}. "
#             # "DO NOT include any explanation, tags, or text before or after the JSON. "
#             # "Your response MUST be only the JSON object. {format_instructions}"
#         ),
#         ("placeholder", "{{ chat_history | join('\\n') }}"),
#         ("human", "{query}"),
#         ("placeholder", "{{ agent_scratchpad | join('\\n') }}"),
#     ]
# ).partial(format_instructions=parser_llm.get_format_instructions())

# chain = prompt_llm_temp | llm | parser_llm


system_custom_prompt2 = (
    "You are an AI agent with one tool: 'DuckDuckGoSearch'.\n"
    "Follow these rules:\n"
    "If the user mentions 'duckduckgo', 'search', or 'use a search tool', use the DuckDuckGoSearch tool.\n"
    "IMPORTANT: Your responses MUST follow the exact format below:\n"
    "Thought: <your reasoning>\n"
    "Action: <tool name>\n"
    "Action Input: <tool input>\n\n"
    "After receiving the tool output:\n"
    "Observation: <tool output>\n"
    "Thought: <your reasoning>\n"
    "Action/Final Answer: <next action or your final answer>\n\n"
    "Do not deviate from this format. If you're not using a tool, respond with:\n"
    "Thought: <your reasoning>\n"
    "Final Answer: <your answer>\n\n"
    "Never end your output with '[Current state ends]'."
)

tools_llm = [tools.search_tool]

# Create a template to enforce the proper output format
prompt_template = PromptTemplate(
    template=(
        "You are an AI agent tasked with responding to user queries.\n"
        "You have the following tools available: {tools}\n\n"
        "{system_message}\n\n"
        "User Query: {input}\n\n"
        "{agent_scratchpad}\n\n"
        "Remember to ALWAYS follow the format:\n"
        "Thought: (your reasoning)\n"
        "Action: (tool name or Final Answer)\n"
        "Action Input: (input for the tool if using a tool)"
    ),
    input_variables=["tools", "system_message", "input", "agent_scratchpad"]
)

# Create agent with custom settings for better handling of parsing errors
agent_llm = initialize_agent(
    tools=tools_llm,
    llm=llm,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    max_iterations=3,
    return_intermediate_steps=True,
    handle_parsing_errors=True,
    system_message=system_custom_prompt2
)

try:
    # this is chaining which is not has tool calling capability
    # response_llm = chain.invoke({
    #     "query": "Summarize the pride and prejudice book",
    #     "chat_history": [],
    #     "agent_scratchpad": []
    # })

    # print(response_llm)

    # this is agent which has tool calling capability

    user_query = input("enter your query: ")
    result = agent_llm.invoke(
        {
            "input": user_query.strip()
        }
    )

    # Print the result
    print("\nFinal Result:")
    if 'output' in result:
        print(result['output'])
    else:
        print(result)

    # Print intermediate steps if available
    if 'intermediate_steps' in result and result['intermediate_steps']:
        print("\nIntermediate Steps:")
        for step in result['intermediate_steps']:
            print(f"Tool: {step[0].tool}")
            print(f"Input: {step[0].tool_input}")
            print(f"Output: {step[1]}")
            print("---")

except Exception as e:
    # Enhanced error handling
    if isinstance(e, langchain_core.exceptions.OutputParserException):
        print(f"Output parsing error: {e}")
        # Try to extract the useful information from the LLM output
        if hasattr(e, 'llm_output'):
            # Extract any useful information from the raw output
            raw_output = getattr(e, 'llm_output', '')
            print("Here's what the AI was trying to say:")
            
            # Clean up the output by removing problematic markers
            cleaned_output = raw_output.replace("[Current state ends]", "").strip()
            print(cleaned_output)
            
            # Try to extract structured content if possible
            try:
                parser = FlexibleOutputParser()
                parsed_result = parser.parse(cleaned_output)
                print("Extracted content:")
                print(parsed_result)
            except Exception:
                # Try fallback JSON parsing
                match = re.search(r"\{.*\}", raw_output, re.DOTALL)
                if match:
                    try:
                        parsed_json = json.loads(match.group())
                        print("Extracted content:")
                        print(parsed_json)
                    except json.JSONDecodeError:
                        print("Found structured content but couldn't parse it.")
    elif isinstance(e, duckduckgo_search.exceptions.DuckDuckGoSearchException):
        print("DuckDuckGo search failed (rate limited). Please try again later.")
    else:
        print(f"Error: {type(e).__name__}: {e}")

# TODO now I will not use the deep seek locally installed version

# our AI will give output like this if the duckduck go is unable to give result
r"""
C:\Users\pirat\PycharmProjects\MCPserverP1\.venv\Scripts\python.exe C:\Users\pirat\PycharmProjects\MCPserverP1\testt.py 
C:\Users\pirat\PycharmProjects\MCPserverP1\testt.py:62: LangChainDeprecationWarning: LangChain agents will continue to be supported, but it is recommended for new use cases to be built with LangGraph. LangGraph offers a more flexible and full-featured framework for building agents, including support for tool-calling, persistence of state, and human-in-the-loop workflows. For details, refer to the `LangGraph documentation <https://langchain-ai.github.io/langgraph/>`_ as well as guides for `Migrating from AgentExecutor <https://python.langchain.com/docs/how_to/migrate_agent/>`_ and LangGraph's `Pre-built ReAct agent <https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/>`_.
  agent_llm = initialize_agent(
enter your query: what is nearby restrurants of me?


> Entering new AgentExecutor chain...
<think>
Okay, so I need to figure out how to find nearby restaurants using DuckDuckGoSearch. Let's start by understanding what the user is asking for. They want information about restaurants that are close to them right now.

First, I should consider if they have a specific location in mind or if they just want general information. Since the question doesn't specify, it might be better to provide options both for a specific area and a general search. That way, it's more helpful whether they're thinking about going out for dinner soon or just looking for nearby places.

Next, I'll need to use DuckDuckGoSearch to look up restaurants in their vicinity. Using the tool with input like "nearby restaurants [their location]" should give me a list of results. If they don't have a specific location yet, suggesting they input their location would be useful.

I also want to make sure I provide clear instructions on how to use the search tool so that the user can easily follow along. Maybe mention entering their city or area in the brackets. Also, if there are no restaurants found nearby, it's good to inform them and suggest searching for popular chains instead.

Additionally, including a general search option could be helpful, just in case they don't have a specific location in mind but still want some nearby options. Offering links to see more info on popular chain restaurants might also be useful if there are no local results.

I should structure the response clearly so that it's easy for the user to understand and act upon. Breaking it down into steps or points would make it more organized, especially since they're using a tool that requires multiple actions.
</think>

To find nearby restaurants:

1. Use DuckDuckGoSearch with "nearby restaurants" followed by your city or area to get local options.
2. If no results are found, try searching for popular chain restaurants instead.
3. The search will provide you with links and details about the nearest eateries.

Example Search Query: DuckDuckGoSearch("nearby restaurants San Francisco")
Observation: Invalid Format: Missing 'Action:' after 'Thought:
Thought:<think>
Alright, let's break down how I would respond to a user asking for nearby restaurants using DuckDuckGoSearch. 

First, I need to determine if the user has a specific location in mind or is looking for general options nearby. Offering both possibilities makes the response versatile.

Next, I'll guide them on how to use the search tool effectively. Providing an example query with their city or area will make it clear and actionable.

I should also consider that if no local results come up, suggesting popular chains as a fallback option is helpful. Additionally, directing them to explore more details on those options would be beneficial.

Finally, presenting this information in a clear, step-by-step manner ensures the user can easily follow along without confusion.

Example Search Query: DuckDuckGoSearch("nearby restaurants San Francisco")
Observation: Invalid Format: Missing 'Action:' after 'Thought:
Thought:<think>
Alright, let me walk through how I would respond to someone asking for nearby restaurants using DuckDuckGoSearch. 

Firstly, the user is seeking information about nearby eateries without specifying a location, so it's best to provide both specific and general search options.

I'll start by instructing them to use DuckDuckGoSearch with "nearby restaurants" followed by their city or area for local results. If no local options are available, suggesting they try popular chains is a good backup plan.

Including an example query will make the process clearer. I'll provide a sample search term using their hypothetical location, like "San Francisco."

Finally, I'll ensure the instructions are concise and helpful, guiding them to explore more details if needed.
</think>

To find nearby restaurants:

1. Use DuckDuckGoSearch with the query: "nearby restaurants [your city or area]"  
   For example: DuckDuckGoSearch("nearby restaurants San Francisco")  
2. If no specific location is known, try searching for popular chain restaurants in your area.
3. This will provide you with links to local or nearby restaurant options.

Example Search Query: DuckDuckGoSearch("nearby restaurants San Francisco")
Observation: Invalid Format: Missing 'Action:' after 'Thought:
Thought:

> Finished chain.

Final Result:
Agent stopped due to iteration limit or time limit.

Intermediate Steps:
Tool: _Exception
Input: Invalid Format: Missing 'Action:' after 'Thought:
Output: Invalid Format: Missing 'Action:' after 'Thought:
---
Tool: _Exception
Input: Invalid Format: Missing 'Action:' after 'Thought:
Output: Invalid Format: Missing 'Action:' after 'Thought:
---
Tool: _Exception
Input: Invalid Format: Missing 'Action:' after 'Thought:
Output: Invalid Format: Missing 'Action:' after 'Thought:
---

Process finished with exit code 0

"""

# so we have to make sure that only if the user ask about facts then we will use the search tool else prompt engineer and figure out how to provide the answer