"""
Text Analysis Service.
Calculates synthetic markers (perplexity, sentence burstiness, and repetitive entropy).
"""
import re
import math

# Text resource policy constants
MAX_TEXT_LENGTH = 25_000
MAX_SENTENCE_BREAKDOWN_ITEMS = 100

class TextDetectionService:
    @staticmethod
    def analyze_text(text: str) -> dict:
        """
        Analyzes text for AI generation markers.
        Analyzes the complete accepted text, but caps the returned
        sentence_breakdown at MAX_SENTENCE_BREAKDOWN_ITEMS (100) entries
        to prevent database payload bloat. As a result, sentence_breakdown
        may not represent every sentence in long text submissions.
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty.")

        cleaned_text = text.strip()
        if len(cleaned_text) > MAX_TEXT_LENGTH:
            raise ValueError(f"Input text exceeds maximum permitted length of {MAX_TEXT_LENGTH} characters.")

        sentences = re.split(r'(?<=[.!?]) +', cleaned_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            raise ValueError("No valid sentences detected in input text.")

        # 1. Calculate Burstiness (Variance in sentence lengths)
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_sentence_len = sum(sentence_lengths) / len(sentence_lengths)
        
        if len(sentence_lengths) > 1:
            variance = sum((l - avg_sentence_len) ** 2 for l in sentence_lengths) / (len(sentence_lengths) - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        # AI text typically has uniform sentence length (low burstiness)
        # Human text has high variance in sentence length
        burstiness_score = max(0.0, min(1.0, 1.0 - (std_dev / (avg_sentence_len + 1e-5))))

        # 2. Vocabulary Repetition / Uniformity
        words = re.findall(r'\b\w+\b', cleaned_text.lower())
        total_words = len(words)
        unique_words = len(set(words))
        type_token_ratio = (unique_words / total_words) if total_words > 0 else 1.0

        # 3. Aggregate AI probability estimate
        # Low variance in sentence length + high predictability = high AI probability
        ai_probability = round((burstiness_score * 0.6) + ((1.0 - type_token_ratio) * 0.4), 3)
        ai_probability = max(0.05, min(0.98, ai_probability))

        # 4. Sentence-by-sentence breakdown (capped at MAX_SENTENCE_BREAKDOWN_ITEMS for payload safety)
        sentence_results = []
        for s in sentences[:MAX_SENTENCE_BREAKDOWN_ITEMS]:
            s_len = len(s.split())
            diff = abs(s_len - avg_sentence_len)
            is_suspicious = diff < 3.0
            sentence_results.append({
                "sentence": s,
                "word_count": s_len,
                "suspicious": is_suspicious
            })

        is_ai = ai_probability > 0.65

        return {
            "is_ai_generated": is_ai,
            "ai_confidence_score": ai_probability,
            "metrics": {
                "total_sentences": len(sentences),
                "total_words": total_words,
                "burstiness_index": round(burstiness_score, 3),
                "lexical_diversity": round(type_token_ratio, 3)
            },
            "sentence_breakdown": sentence_results
        }