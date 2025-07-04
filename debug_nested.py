import re
from create_embeddings.chunking import SentenceSplitterChunkingStrategy

text = 'He said "Stop right there." Then he left. Another sentence.'
print(f"Text: {repr(text)}")

# Manual sentence splitting to check
parts = re.split(r'([.!?…․؟]+)', text)
print('Parts:', [repr(p) for p in parts])

sentences = []
for i in range(0, len(parts) - 1, 2):
    if i + 1 < len(parts):
        sentence_text = parts[i].strip()
        punctuation = parts[i + 1].strip()
        if sentence_text and punctuation:
            sentences.append(sentence_text + punctuation)
        print(f'i={i}, sentence_text={repr(sentence_text)}, punctuation={repr(punctuation)}')

print(f'Sentences: {[repr(s) for s in sentences]}')

print("\nTesting strategy:")
strategy = SentenceSplitterChunkingStrategy()
chunks = list(strategy.chunk_text(text, max_tokens=10))
for i, chunk in enumerate(chunks):
    print(f'  Chunk {i}: {repr(chunk)} -> {len(chunk.split())} tokens')
print(f'Number of chunks: {len(chunks)}')
