"""
Term Ranking System for Context-Based Vocabulary Generation

Given a context sentence, generates ~100 relevant, usable terms for that scenario.
Uses embeddings, semantic similarity, and diversity algorithms.
"""

import anthropic
import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import spacy
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import re
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    print("Downloading spaCy model...")
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


# Configuration
CONFIG = {
    "target_count": 100,
    "neighbor_pool": 500,  # Reduced for API efficiency
    "cluster_k": 10,
    "mmr_lambda": 0.7,
    "spread_threshold": 0.38,
    "category_quotas": {
        "Action/Task": 25,
        "Tech/Tool": 20,
        "Problem/Error": 10,
        "Data/Artifact": 20,
        "Concept/Method": 15,
        "Event/Logistics": 10
    },
    "seeds": {
        "action": ["work", "create", "write", "read", "help", "learn", "teach", "talk",
                   "click", "type", "save", "open", "edit", "share", "test", "run",
                   "tokenize", "debug", "parse", "analyze"],
        "decor": ["room", "chair", "vibe", "light", "atmosphere", "wall", "ceiling",
                  "furniture", "decoration", "ambiance", "setting"]
    },
    "stoplist_extra": ["folks", "guys", "stuff", "thing", "really", "very", "quite"]
}


def embed_text(text: str, openai_client: OpenAI) -> np.ndarray:
    """
    Embed text using OpenAI's text-embedding-3-small model.
    Fast, cheap, and high quality (1536 dimensions).
    """
    # Handle empty or very short text
    if not text or len(text.strip()) < 2:
        return np.zeros(1536)

    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"
        )

        embedding = np.array(response.data[0].embedding)
        return embedding

    except Exception as e:
        print(f"Warning: Embedding failed for '{text[:50]}...': {e}")
        return np.zeros(1536)


def embed_batch(texts: List[str], openai_client: OpenAI, batch_size: int = 100) -> List[np.ndarray]:
    """
    Embed multiple texts in batches for efficiency.
    OpenAI allows up to 2048 texts per request.
    """
    embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]

        try:
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
                encoding_format="float"
            )

            batch_embeddings = [np.array(item.embedding) for item in response.data]
            embeddings.extend(batch_embeddings)

        except Exception as e:
            print(f"Warning: Batch embedding failed for batch {i//batch_size}: {e}")
            # Fallback: add zero vectors
            embeddings.extend([np.zeros(1536) for _ in batch])

    return embeddings


def generate_candidate_terms(client: anthropic.Anthropic, context: str, n: int = 500) -> List[str]:
    """
    Generate candidate terms using LLM.
    """
    prompt = f"""Given this context: "{context}"

Generate {n} SINGLE WORDS for a VOCABULARY LIST that would help someone discuss this type of situation.

CRITICAL: Generate GENERAL, REUSABLE vocabulary - NOT specific image descriptions!

❌ BAD (too specific to this exact scenario):
- "yacht", "five friends", "another boat", "ceiling-mounted", "huskyboard"

✅ GOOD (general vocabulary for this TYPE of situation):
- For BOATING: "boat", "water", "sail", "friend", "trip", "ocean", "wave", "captain"
- For CLASSROOM: "student", "teacher", "learn", "desk", "board", "question", "study"
- For HOME: "cook", "eat", "sleep", "relax", "family", "room", "comfortable"

Match vocabulary to the DOMAIN:
- Boating/water → boat, water, sail, ocean, wave, dock, captain, crew, anchor
- School/learning → student, teacher, study, learn, desk, board, question, test
- Work/office → work, meeting, task, project, deadline, colleague, email
- Home → cook, eat, sleep, relax, family, room, comfortable, clean
- Tech/coding → code, program, debug, test, build, deploy (ONLY if context is technical)

Rules:
1. SINGLE words only (maximum 2 words for compound terms like "swimming pool")
2. GENERAL vocabulary for the situation type, not specific details
3. NO numbers or quantities ("five", "twenty", "several" is OK but "five friends" is NOT)
4. NO articles or demonstratives ("another boat", "the yacht", "this person")
5. Include: basic verbs, basic nouns, common adjectives, useful descriptive words
6. NO proper nouns or brand names

Output ONLY single words, comma-separated."""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=3000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text.strip()

    # Clean response
    if response_text.startswith('```'):
        lines = response_text.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('```'):
                response_text = line
                break

    # Parse terms
    terms = [term.strip() for term in response_text.split(',') if term.strip()]
    terms = [term for term in terms if not term.startswith('```')]

    return terms


def extract_terms_from_text(text: str) -> List[str]:
    """
    Extract noun chunks, entities, and key terms from text using spaCy.
    """
    doc = nlp(text)
    terms = []

    # Noun chunks
    terms.extend([chunk.lemma_.lower() for chunk in doc.noun_chunks])

    # Named entities (ORG, PRODUCT, etc.)
    terms.extend([ent.text for ent in doc.ents
                  if ent.label_ in ['ORG', 'PRODUCT', 'GPE', 'EVENT', 'LAW']])

    # Important nouns and verbs
    terms.extend([token.lemma_ for token in doc
                  if token.pos_ in ['NOUN', 'PROPN', 'VERB']
                  and not token.is_stop and token.is_alpha])

    return terms


def normalize_and_dedupe(terms: List[str]) -> List[str]:
    """
    Normalize terms and remove duplicates.
    Filter out overly specific phrases and proper nouns.
    """
    normalized = []
    seen = set()

    # Common proper nouns to filter (libraries, brands, specific products)
    proper_noun_filter = {
        'spacy', 'nltk', 'sklearn', 'pytorch', 'tensorflow', 'keras', 'numpy', 'pandas',
        'matplotlib', 'jupyter', 'openai', 'anthropic', 'claude', 'chatgpt', 'gpt',
        'python', 'javascript', 'typescript', 'java', 'react', 'vue', 'angular',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'github', 'gitlab',
        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
        'fastapi', 'django', 'flask', 'express', 'nextjs', 'node',
        'vscode', 'pycharm', 'intellij', 'eclipse', 'vim', 'emacs'
    }

    # Phrases that indicate overly specific/descriptive content
    bad_phrase_patterns = [
        'in short', 'in summary', 'in brief', 'in other words',
        'another', 'this', 'that', 'these', 'those',
        'five friend', 'three people', 'two student', 'ten person'
    ]

    for term in terms:
        # Basic normalization
        term = term.strip().lower()

        # Skip if too short, too long, or in stoplist
        if len(term) < 2 or len(term) > 30:  # Reduced max length to 30
            continue
        if term in CONFIG["stoplist_extra"]:
            continue

        # Skip overly specific descriptive phrases
        if any(pattern in term for pattern in bad_phrase_patterns):
            continue

        # Skip multi-word phrases with "another", "the", articles
        word_count = len(term.split())
        if word_count > 2:  # Reject anything with more than 2 words
            continue
        if word_count == 2 and any(word in term.split() for word in ['another', 'the', 'a', 'an', 'this', 'that']):
            continue

        # Filter out most proper nouns (keep only essential generic ones)
        doc = nlp(term)
        if len(doc) > 0:
            # Skip if it's a proper noun AND in our filter list
            if doc[0].pos_ == 'PROPN' and term in proper_noun_filter:
                continue
            lemma = doc[0].lemma_
        else:
            lemma = term

        # Check for near-duplicates (simple approach)
        if lemma not in seen:
            normalized.append(term)
            seen.add(lemma)

    return normalized


def categorize_term(term: str) -> str:
    """
    Categorize a term into one of the predefined categories.
    """
    doc = nlp(term)

    # Tech/Tool patterns
    tech_patterns = [
        r'(?i)(spacy|nltk|sklearn|pytorch|tensorflow|pandas|numpy|matplotlib|jupyter|faiss)',
        r'(?i)(python|java|javascript|sql|api|framework|library)',
    ]
    for pattern in tech_patterns:
        if re.search(pattern, term):
            return "Tech/Tool"

    # Problem/Error patterns
    error_patterns = [
        r'(?i)(error|exception|fail|unexpected|issue|bug|warning|crash)',
        r'(?i)(wrong|invalid|corrupt|missing|broken)',
    ]
    for pattern in error_patterns:
        if re.search(pattern, term):
            return "Problem/Error"

    # Data/Artifact patterns
    data_patterns = [
        r'(?i)(data|dataset|model|output|input|file|document|corpus)',
        r'(?i)(matrix|vector|tensor|array|table|schema|weights)',
    ]
    for pattern in data_patterns:
        if re.search(pattern, term):
            return "Data/Artifact"

    # Event/Logistics patterns
    event_patterns = [
        r'(?i)(presentation|talk|workshop|session|meeting|check-in|raffle)',
        r'(?i)(schedule|agenda|timer|break|lunch)',
    ]
    for pattern in event_patterns:
        if re.search(pattern, term):
            return "Event/Logistics"

    # Action/Task (verbs)
    if len(doc) > 0 and doc[0].pos_ == 'VERB':
        return "Action/Task"

    # Concept/Method (abstract nouns)
    concept_patterns = [
        r'(?i)(tokenization|lemmatization|normalization|embedding|similarity)',
        r'(?i)(algorithm|method|technique|approach|process|analysis)',
    ]
    for pattern in concept_patterns:
        if re.search(pattern, term):
            return "Concept/Method"

    # Default based on POS
    if len(doc) > 0:
        if doc[0].pos_ == 'VERB':
            return "Action/Task"
        elif doc[0].pos_ in ['NOUN', 'PROPN']:
            return "Concept/Method"

    return "Concept/Method"


def compute_term_vectors(terms: List[str], openai_client: OpenAI) -> Dict[str, np.ndarray]:
    """
    Compute embeddings for each term using OpenAI in batches.
    """
    print(f"   Embedding {len(terms)} terms in batches...")
    embeddings = embed_batch(terms, openai_client, batch_size=100)

    vectors = {}
    for term, emb in zip(terms, embeddings):
        vectors[term] = emb

    return vectors


def compute_signals(terms: List[str], term_vectors: Dict[str, np.ndarray],
                   ctx_vec: np.ndarray, openai_client: OpenAI) -> Dict[str, Dict]:
    """
    Compute relevance signals for each term.
    """
    # Compute prototype vectors
    action_vecs = embed_batch(CONFIG["seeds"]["action"][:5], openai_client)
    decor_vecs = embed_batch(CONFIG["seeds"]["decor"][:5], openai_client)

    proto_action = np.mean(action_vecs, axis=0)
    proto_decor = np.mean(decor_vecs, axis=0)

    signals = {}

    for term in terms:
        if term not in term_vectors:
            continue

        v = term_vectors[term]

        # Similarity to context
        sim_topic = cosine_similarity([v], [ctx_vec])[0][0]

        # Action margin
        sim_action = cosine_similarity([v], [proto_action])[0][0]
        sim_decor = cosine_similarity([v], [proto_decor])[0][0]
        action_margin = sim_action - sim_decor

        signals[term] = {
            "sim_topic": float(sim_topic),
            "action_margin": float(action_margin),
        }

    return signals


def score_terms(signals: Dict[str, Dict]) -> Dict[str, float]:
    """
    Compute final scores from signals.
    """
    scores = {}

    # Normalize signals
    all_sim_topic = [s["sim_topic"] for s in signals.values()]
    all_action_margin = [s["action_margin"] for s in signals.values()]

    min_sim = min(all_sim_topic) if all_sim_topic else 0
    max_sim = max(all_sim_topic) if all_sim_topic else 1
    min_action = min(all_action_margin) if all_action_margin else 0
    max_action = max(all_action_margin) if all_action_margin else 1

    for term, sig in signals.items():
        # Normalize
        norm_sim = (sig["sim_topic"] - min_sim) / (max_sim - min_sim + 1e-6)
        norm_action = (sig["action_margin"] - min_action) / (max_action - min_action + 1e-6)

        # Combined score
        score = 0.7 * norm_sim + 0.3 * norm_action
        scores[term] = float(score)

    return scores


def diversify_mmr(terms: List[str], vectors: Dict[str, np.ndarray],
                  scores: Dict[str, float], n: int, lambda_param: float = 0.7) -> List[str]:
    """
    Maximal Marginal Relevance diversification.
    """
    selected = []
    remaining = list(terms)

    # Start with highest-scoring term
    remaining.sort(key=lambda t: scores.get(t, 0), reverse=True)
    selected.append(remaining.pop(0))

    while len(selected) < n and remaining:
        best_term = None
        best_mmr = -float('inf')

        for term in remaining:
            if term not in vectors:
                continue

            # Relevance score
            relevance = scores.get(term, 0)

            # Max similarity to already selected
            max_sim = 0
            for sel_term in selected:
                if sel_term in vectors:
                    sim = cosine_similarity([vectors[term]], [vectors[sel_term]])[0][0]
                    max_sim = max(max_sim, sim)

            # MMR score
            mmr = lambda_param * relevance - (1 - lambda_param) * max_sim

            if mmr > best_mmr:
                best_mmr = mmr
                best_term = term

        if best_term:
            selected.append(best_term)
            remaining.remove(best_term)
        else:
            break

    return selected


def diversify_with_quotas(terms: List[str], vectors: Dict[str, np.ndarray],
                          scores: Dict[str, float], categories: Dict[str, str],
                          target_n: int) -> List[str]:
    """
    Diversify using category quotas and MMR.
    """
    # Group by category
    by_category = defaultdict(list)
    for term in terms:
        cat = categories.get(term, "Concept/Method")
        by_category[cat].append(term)

    # Sort within each category
    for cat in by_category:
        by_category[cat].sort(key=lambda t: scores.get(t, 0), reverse=True)

    # Apply quotas
    selected = []
    quotas = CONFIG["category_quotas"]

    for cat, quota in quotas.items():
        if cat in by_category:
            # Take top items up to quota
            cat_terms = by_category[cat][:quota * 2]  # Get extras for MMR
            # Apply MMR within category
            if cat_terms:
                mmr_terms = diversify_mmr(cat_terms, vectors, scores,
                                         min(quota, len(cat_terms)),
                                         CONFIG["mmr_lambda"])
                selected.extend(mmr_terms)

    # Fill remaining slots with highest-scoring terms not yet selected
    if len(selected) < target_n:
        remaining = [t for t in terms if t not in selected]
        remaining.sort(key=lambda t: scores.get(t, 0), reverse=True)
        selected.extend(remaining[:target_n - len(selected)])

    return selected[:target_n]


def generate_terms(context: str, n: int = 100,
                  anthropic_client: anthropic.Anthropic = None,
                  openai_client: OpenAI = None) -> dict:
    """
    Main pipeline: generate ranked terms for a given context.
    """
    print(f"\n{'='*70}")
    print(f"Generating {n} terms for context:")
    print(f"  \"{context}\"")
    print(f"{'='*70}\n")

    if anthropic_client is None:
        anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    if openai_client is None:
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # 1. Embed context
    print("1. Embedding context with OpenAI...")
    ctx_vec = embed_text(context, openai_client)

    # 2. Generate candidates
    print("2. Generating candidate terms with Claude...")
    candidates = generate_candidate_terms(anthropic_client, context, CONFIG["neighbor_pool"])

    # Add terms extracted from context itself
    candidates.extend(extract_terms_from_text(context))

    print(f"   Generated {len(candidates)} raw candidates")

    # 3. Normalize and dedupe
    print("3. Normalizing and deduplicating...")
    candidates = normalize_and_dedupe(candidates)
    print(f"   {len(candidates)} unique candidates after normalization")

    # 4. Compute vectors
    print("4. Computing term vectors with OpenAI embeddings...")
    term_vectors = compute_term_vectors(candidates, openai_client)

    # 5. Compute signals
    print("5. Computing relevance signals...")
    signals = compute_signals(candidates, term_vectors, ctx_vec, openai_client)

    # 6. Score terms
    print("6. Scoring terms...")
    scores = score_terms(signals)

    # 7. Categorize
    print("7. Categorizing terms...")
    categories = {term: categorize_term(term) for term in candidates}

    # 8. Diversify
    print("8. Applying diversity selection...")
    selected = diversify_with_quotas(candidates, term_vectors, scores, categories, n)

    # 9. Build result
    print(f"\n✓ Selected {len(selected)} terms\n")

    result = {
        "context": context,
        "terms": [
            {
                "term": term,
                "score": round(scores.get(term, 0), 3),
                "category": categories.get(term, "Concept/Method")
            }
            for term in selected
        ]
    }

    # Sort by score within result
    result["terms"].sort(key=lambda x: x["score"], reverse=True)

    return result


def print_results(result: dict):
    """
    Pretty-print results.
    """
    print(f"{'='*70}")
    print(f"RESULTS FOR: {result['context']}")
    print(f"{'='*70}\n")

    # Group by category
    by_cat = defaultdict(list)
    for item in result["terms"]:
        by_cat[item["category"]].append(item)

    for cat in CONFIG["category_quotas"].keys():
        if cat in by_cat:
            print(f"\n[{cat}] ({len(by_cat[cat])} terms)")
            for item in by_cat[cat][:15]:  # Show top 15 per category
                print(f"  • {item['term']:30s} (score: {item['score']:.3f})")

    print(f"\n{'='*70}")
    print(f"Total: {len(result['terms'])} terms")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import sys

    # API keys from .env file
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key or not openai_key:
        print("ERROR: API keys not found in .env file")
        print("Please create a .env file with ANTHROPIC_API_KEY and OPENAI_API_KEY")
        sys.exit(1)

    # Get context from command line or prompt
    if len(sys.argv) > 1:
        context = " ".join(sys.argv[1:])
    else:
        context = input("Enter context sentence: ")

    # Initialize clients
    try:
        anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
        openai_client = OpenAI(api_key=openai_key)
    except Exception as e:
        print(f"ERROR initializing API clients: {e}")
        sys.exit(1)

    # Generate terms
    try:
        result = generate_terms(context, n=100,
                              anthropic_client=anthropic_client,
                              openai_client=openai_client)

        # Print results
        print_results(result)

        # Save to JSON
        output_file = "ranked_terms.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\nResults saved to {output_file}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
