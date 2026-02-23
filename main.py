import zmq
import json
import asyncio

from dotenv import load_dotenv
load_dotenv()

from groq import Groq


MIN_SENTENCES = 1
MAX_SENTENCES = 10
DEFAULT_SENTENCES = 3


def validate_request(request: dict) -> str | None:
    """
    Validate the incoming request dictionary.
    Returns an error message string if invalid, or None if valid.
    """
    text = request.get("text", "")

    if not isinstance(text, str):
        return "Field 'text' must be a string."
    if not text.strip():
        return "Field 'text' is required and cannot be empty or whitespace."
    if len(text.strip()) < 10:
        return "Field 'text' is too short to summarize (minimum 10 characters)."

    max_sentences = request.get("max_sentences", DEFAULT_SENTENCES)
    if not isinstance(max_sentences, int) or isinstance(max_sentences, bool):
        return f"Field 'max_sentences' must be an integer."
    if not (MIN_SENTENCES <= max_sentences <= MAX_SENTENCES):
        return f"Field 'max_sentences' must be between {MIN_SENTENCES} and {MAX_SENTENCES}."

    return None


def summarize(text: str, max_sentences: int = DEFAULT_SENTENCES) -> str:
    """Summarize text by extracting the first N sentences."""
    # Clamp just in case
    max_sentences = max(MIN_SENTENCES, min(max_sentences, MAX_SENTENCES))

    sentences = []
    for s in text.replace("\n", " ").split("."):
        stripped = s.strip()
        if stripped:
            sentences.append(stripped + ".")
    if not sentences:
        return text.strip()
    return " ".join(sentences[:max_sentences])


client = Groq()


async def call_agent_summarizer(text, max_sentences=DEFAULT_SENTENCES):
    print("--- call_agent_summarizer() called ---")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a text summarizer. Return only the summarized text with no extra commentary."
            },
            {
                "role": "user",
                "content": f"Summarize the following text into {max_sentences} sentences:\n\n{text}"
            }
        ]
    )
    return response.choices[0].message.content


async def handle_request(message: str) -> str:
    """Parse incoming JSON, validate it, summarize the text, and return a JSON response string."""
    print("--- handle_request() called ---")

    # --- Parse JSON ---
    try:
        request = json.loads(message)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        return json.dumps({"error": f"Invalid JSON: {e}"})

    if not isinstance(request, dict):
        return json.dumps({"error": "Request must be a JSON object."}) 

    # --- Validate fields ---
    validation_error = validate_request(request)
    if validation_error:
        print(f"❌ Validation error: {validation_error}")
        return json.dumps({"error": validation_error})

    text = request["text"].strip()
    max_sentences = request.get("max_sentences", DEFAULT_SENTENCES)

    # --- Summarize ---
    used_fallback = False
    try:
        summary = await call_agent_summarizer(text, max_sentences)
        print("✅ LLM summarization succeeded")
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
