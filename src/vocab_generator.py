import anthropic
import os
from typing import List

#this is an importable file that will take a string "context" and return a list of ~100 vocabulary words
def generate_vocabulary(context: str, num_words: int = 100) -> List[str]:
    """
    Generate a list of relevant vocabulary words based on a context description.

    Args:
        context: A string describing the context/topic for vocabulary generation
        num_words: Number of vocabulary words to generate (default: 100)

    Returns:
        A list of relevant vocabulary words
    """
    # Initialize the Anthropic client
    client = anthropic.Anthropic(
        api_key="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"
    )

    # Create the prompt for Claude
    prompt = f"""Given the following context, generate a list of exactly {num_words} most relevant vocabulary words.
Focus on meaningfully different CONTENT WORDS (nouns, verbs, adjectives, adverbs) that carry substantial semantic meaning.
Avoid function words, articles, prepositions, and redundant variations of the same concept.
These should be important terms, concepts, and keywords that someone would need to know to understand and discuss this topic effectively.

Context: {context}

Please provide ONLY the vocabulary words as a comma-separated list, with no additional explanation or formatting."""

    # Call the Claude API
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Extract the text response
    response_text = message.content[0].text

    # Parse the comma-separated list into a Python list
    vocab_list = [word.strip() for word in response_text.split(',')]

    return vocab_list


if __name__ == "__main__":
    # Prompt user for context
    context = input("Enter the context for vocabulary generation: ")
    vocab_words = generate_vocabulary(context)

    print(f"\nGenerated {len(vocab_words)} vocabulary words:")
    for i, word in enumerate(vocab_words, 1):
        print(f"{i}. {word}")
