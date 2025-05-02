from flask import Flask, render_template, request, jsonify, session
from langchain_groq import ChatGroq
from langchain_community.utilities import ArxivAPIWrapper, WikipediaAPIWrapper
from langchain_community.tools import ArxivQueryRun, WikipediaQueryRun
from langchain.agents import initialize_agent, AgentType
import os
from dotenv import load_dotenv
import uuid
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

app = Flask(__name__)
app.secret_key=os.urandom(24)

# Load environment variables
load_dotenv()
api_key=os.getenv("GROQ_API_KEY")

# Initialize tools
arxiv_wrapper = ArxivAPIWrapper(top_k_results=1, doc_content_chars_max=200)
arxiv = ArxivQueryRun(api_wrapper=arxiv_wrapper)

api_wrapper=WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=200)
wiki=WikipediaQueryRun(api_wrapper=api_wrapper)

@app.route('/')
def index():
    # Initialize session if needed
    if 'messages' not in session:
        session['messages'] = [
            {"role": "assistant", "content": "Hi, I can search the web. How can I help you?"}
        ]
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html', messages=session['messages'])

@app.route('/ask', methods=['POST'])
def ask():
    data=request.get_json()
    prompt=data.get('prompt')
    
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    # Add user message to session
    if 'messages' not in session:
        session['messages']=[]
    
    session['messages'].append({"role": "user", "content": prompt})
    
    try:
        # Initialize LLM and tools
        llm=ChatGroq(groq_api_key=api_key, model_name="qwen-qwq-32b", streaming=False)
        tools=[arxiv, wiki]
        
        # Initialize agent
        search_agent=initialize_agent(
            tools, 
            llm, 
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
            handle_parsing_errors=True
        )
        
        # Get response
        response=search_agent.invoke([{"role": "user", "content": prompt}])
        
        # Extract the string from the response if it's an object
        if isinstance(response, dict):
            response_text=response.get('output', str(response))
        else:
            response_text=str(response)
            
        # Add assistant message to session
        session['messages'].append({"role": "assistant", "content": response_text})
        session.modified=True
        
        return jsonify({"response": response_text})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear_chat():
    session['messages']=[
        {"role": "assistant", "content": "Hi, I can search the web. How can I help you?"}
    ]
    session['session_id']=str(uuid.uuid4())
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)