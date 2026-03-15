try:
    from langchain_core.documents import Document
    print("SUCCESS: Document imported from langchain_core.documents")
except ImportError:
    print("FAILED: Document NOT found in langchain_core.documents")

try:
    from langchain.schema import Document
    print("SUCCESS: Document imported from langchain.schema")
except ImportError:
    print("FAILED: Document NOT found in langchain.schema")

try:
    from langchain_core.prompts import ChatPromptTemplate
    print("SUCCESS: ChatPromptTemplate imported from langchain_core.prompts")
except ImportError:
    print("FAILED: ChatPromptTemplate NOT found in langchain_core.prompts")

try:
    from langchain.prompts import ChatPromptTemplate
    print("SUCCESS: ChatPromptTemplate imported from langchain.prompts")
except ImportError:
    print("FAILED: ChatPromptTemplate NOT found in langchain.prompts")

try:
    import langchain
    print(f"LangChain version: {langchain.__version__}")
except Exception as e:
    print(f"Error checking langchain version: {e}")
