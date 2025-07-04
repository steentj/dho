import re
from create_embeddings.chunking import SentenceSplitterChunkingStrategy

text = "First sentence!! Second sentence?? Third sentence..."
print(f"Text: {text}")

# Manual sentence splitting to check
parts = re.split(r'([.!?]+)', text)
print('Parts:', parts)

sentences = []
for i in range(0, len(parts) - 1, 2):
    if i + 1 < len(parts):
        sentence_text = parts[i].strip()
        punctuation = parts[i + 1].strip()
        if sentence_text and punctuation:
            sentences.append(sentence_text + punctuation)
        print(f'i={i}, sentence_text="{sentence_text}", punctuation="{punctuation}"')

print(f'Sentences: {sentences}')
for i, sentence in enumerate(sentences):
    print(f'  Sentence {i}: "{sentence}" -> {len(sentence.split())} tokens')

print(f"\nTotal words in first two sentences: {len((sentences[0] + ' ' + sentences[1]).split())}")
print(f"Max tokens allowed: 5")

print("\nTesting strategy:")
strategy = SentenceSplitterChunkingStrategy()
chunks = list(strategy.chunk_text(text, max_tokens=5))
for i, chunk in enumerate(chunks):
    print(f'  Chunk {i}: "{chunk}" -> {len(chunk.split())} tokens')
print(f'Number of chunks: {len(chunks)}')
