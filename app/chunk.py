import re


def chunk_text(text, max_tokens=800):
    sections = re.split(r'(\n#+\s|\n[A-Z][A-Za-z\s]+:)', text)
    chunks = []
    current_chunk = []

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
