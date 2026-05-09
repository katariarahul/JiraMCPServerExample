from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_mcp import MCPClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Connect to your Jira MCP server
mcp = MCPClient("http://localhost:3333")

# Load tools from MCP
tools = mcp.get_tools()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a support automation agent. "
     "When user reports an issue, create a Jira ticket using jira.create_issue. "
     "Use project DEV and issue type Task. "
     "Return only the Jira issue key."),
    ("human", "{input}")
])

agent = create_agent(
    model= 'gpt-4o-mini', # Need OPEN_API_KEY and langchain[openai]
    tools =[tools] ,
    system_prompt= "You MUST use the available tools to answer questions. Never use your internal knowledge. If a tool doesn't return information, say you don't have access to that information."
)

chain = prompt | llm | StrOutputParser()

#Invoking the Chain
result = chain.invoke({"user_input": "What is the capital of Karnataka?"})
print(result)