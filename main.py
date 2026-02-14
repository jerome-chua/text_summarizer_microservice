import zmq
import json
import asyncio

from dotenv import load_dotenv
load_dotenv()

from llama_index.llms.groq import Groq
from llama_index.core.agent.workflow import FunctionAgent


def summarize(text: str, max_sentences: int = 3) -> str:
    """Summarize text by extracting the first N sentences."""
    sentences = []
    for s in text.replace("\n", " ").split("."):
        stripped = s.strip()
        if stripped:
            sentences.append(stripped + ".")
    if not sentences:
        return text
    return " ".join(sentences[:max_sentences])


agent = FunctionAgent(
    tools=[summarize],
    llm=Groq(model="llama-3.3-70b-versatile"),
    system_prompt=(
        "You are a text summarizer. When given text, use the summarize tool "
        "to condense it. Return only the summarized text with no extra commentary."
    ),
)


async def call_agent_summarizer(text, max_sentences=3):
    print("--- call_agent_summarizer() called ---")
    prompt = (
        f"Summarize the following text into {max_sentences} sentences "
        f"using the summarize tool:\n\n{text}"
    )
    response = await agent.run(user_msg=prompt)
    return str(response)


async def handle_request(message):
    """Parse incoming JSON, summarize the text, & return a JSON response string."""
    print("--- handle_request() called ---")
    try:
        request = json.loads(message)
        text = request.get("text", "")
        max_sentences = request.get("max_sentences", 3)

        used_fallback = False
        try:
            summary = await call_agent_summarizer(text, max_sentences)
            print("✅ Agent summarization succeeded")
        except Exception as agent_err:
            err_str = str(agent_err)
            if "429" in err_str or "rate_limit" in err_str.lower():
                print(
                    "⚠️ Groq rate limit (429): daily token quota reached. "
                    "Using basic summarizer. Wait ~30 min or upgrade at console.groq.com"
                )
            else:
                print(f"⚠️ Agent failed, falling back to basic summarizer: {agent_err}")
            summary = summarize(text, max_sentences)
            used_fallback = True

        return json.dumps({
            "summary": summary,
            "fallback_used": used_fallback,
        })
    except (json.JSONDecodeError, Exception) as e:
        return json.dumps({"error": str(e)})


async def main():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    print("Text Summarizer Microservice running on: Port 5555")

    while True:
        message = socket.recv_string()
        print(f"Request received: '{message}'")

        response = await handle_request(message)
        socket.send_string(response)
        print("Response sent back to client")


if __name__ == "__main__":
    asyncio.run(main())
