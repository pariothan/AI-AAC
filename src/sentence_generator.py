# ai_sentence_gen.py
# Make sure you ran: pip install openai

from openai import OpenAI

# Initialize OpenAI client
# You can either set OPENAI_API_KEY as an environment variable,
# or replace it directly in the line below.
client = OpenAI(api_key=None)  # or use "your_api_key_here"

def ai_sentence_gen(words):
    prompt = f"Create 3 to 5 natural, friendly English sentences using these words in context: {', '.join(words)}."

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # or 'gpt-4o' if available
        messages=[
            {"role": "system", "content": "You are a helpful assistant that writes natural English sentences."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        temperature=0.8
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    words = ["coffee", "friends", "music"]
    print(ai_sentence_gen(words))