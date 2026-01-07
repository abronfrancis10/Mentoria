import spacy
nlp = spacy.load("en_core_web_sm")

def calculate_optimality_score(candidate, optimal):
    c_doc = nlp(candidate.lower())
    o_doc = nlp(optimal.lower())

    c_tokens = set(t.lemma_ for t in c_doc if t.is_alpha and not t.is_stop)
    o_tokens = set(t.lemma_ for t in o_doc if t.is_alpha and not t.is_stop)

    if not o_tokens:
        return 0

    return round((len(c_tokens & o_tokens) / len(o_tokens)) * 10, 2)
