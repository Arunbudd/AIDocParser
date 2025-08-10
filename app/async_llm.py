import asyncio
import re

import tiktoken

from app.config import async_openai_client

# To avoid rate limit errors
semaphore = asyncio.Semaphore(2)


# Retry utility
async def retry_async(func, retries=3, delay=5):
    for attempt in range(retries):
        try:
            return await func()
        except Exception as e:
            print(f"[RETRY] Attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
    raise Exception(f"[FAILURE] Failed after {retries} retries.")


# Chunking Logic
def chunk_text(text, max_tokens=1200):
    sections = re.split(r'(\n#+\s|\n[A-Z][A-Za-z\s]+:)', text)
    chunks, current_chunk = [], []

    for section in sections:
        estimated_tokens = len(" ".join(current_chunk + [section])) // 4
        if estimated_tokens > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = [section]
        else:
            current_chunk.append(section)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


# Async Summarization of Single Chunk (with limiter + retry)
async def summarize_chunk_async(chunk: str) -> str:
    async with semaphore:
        async def task():
            prompt = (
                "Summarize the following document section. "
                "Include actual procedures, syntax, parameters, and details. "
                "Avoid simply listing sections — summarize their content.\n\n"
                f"{chunk[:3000]}"
            )

            response = await async_openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise technical document summarizer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()

        try:
            return await retry_async(task)
        except Exception as e:
            print(f"[ERROR] Summarization failed for chunk: {e}")
            return f"[ERROR] {str(e)}"


# Summarize Entire Document
async def summarize_entire_document(document: str) -> str:
    # Truncate document if too long
    input_text = document[:12000]  # adjust as needed to stay within OpenAI token limits

    response = await async_openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a document summarizer."},
            {"role": "user", "content": input_text}
        ],
        max_tokens=800,
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


async def summarize_text(document: str) -> str:
    chunks = chunk_text(document, max_tokens=1200)
    print(f"[INFO] Summarizing {len(chunks)} chunks...")

    tasks = [summarize_chunk_async(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)
    summaries = [
        result for result in results
        if not result.startswith("[ERROR]")
    ]

    return "\n\n".join(summaries) if summaries else \
        "Summary generation failed due to repeated API rate limits."


async def _answer_single_chunk_async(question: str, context: str) -> str:
    system_msg = (
        "You are a strict document-based assistant. "
        "Use ONLY the document content to answer. "
        "If the document lacks the answer, reply: "
        "'I cannot find relevant information in the provided document.'"
    )

    prompt = f"""
DOCUMENT:
\"\"\"{context[:8000]}\"\"\"

QUESTION:
{question}
"""

    response = await async_openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=500
    )

    return response.choices[0].message.content.strip()


async def answer_question_async(question: str, document: str, token_threshold: int = 10000) -> str:
    estimated_tokens = len(document) // 4

    if estimated_tokens <= token_threshold:
        return await _answer_single_chunk_async(question, document)
    else:
        chunks = chunk_text(document, max_tokens=1200)
        combined = "\n\n".join(chunks)

        # Dynamically leave space for question + response
        available_tokens = 16000 - (len(question) // 4) - 500
        safe_context = truncate_to_token_limit(combined, max_tokens=available_tokens, model="gpt-3.5-turbo")

        return await _answer_single_chunk_async(question, safe_context)


def truncate_to_token_limit(text: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> str:
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return encoding.decode(tokens[:max_tokens])

# async def answer_question_async(question: str, document: str, token_threshold: int = 10000) -> str:
#     estimated_tokens = len(document) // 4
#
#     if estimated_tokens <= token_threshold:
#         return await _answer_single_chunk_async(question, document)
#     else:
#         chunks = chunk_text(document, max_tokens=1200)
#         return await _answer_single_chunk_async(question, chunks)
