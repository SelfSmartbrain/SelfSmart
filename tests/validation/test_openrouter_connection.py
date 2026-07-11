"""
Minimal smoke test for OpenRouter API connection.
Tests ChatAnthropic with the configured credentials.
"""
import asyncio
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

async def test_openrouter_connection():
    """Test minimal OpenRouter connection with ChatAnthropic."""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    model = os.getenv("ANTHROPIC_MODEL")
    
    print(f"Testing OpenRouter connection...")
    print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print()
    
    try:
        # Initialize ChatAnthropic with OpenRouter configuration
        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.1,
            max_tokens=100,
        )
        
        print("Sending minimal request...")
        response = await llm.ainvoke([
            HumanMessage(content="Return only: hello")
        ])
        
        print(f"Response: {response.content}")
        print()
        print("✅ SUCCESS: OpenRouter connection working!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}")
        print(f"Message: {str(e)}")
        print()
        print("FAILURE: OpenRouter connection failed")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_openrouter_connection())
    exit(0 if result else 1)
