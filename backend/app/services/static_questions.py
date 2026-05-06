# Static high-quality questions for demo fallback
STATIC_QUESTIONS = {
    "software engineer": [
        {
            "question": "How do you ensure the scalability and reliability of a distributed system?",
            "expected_answer": ["Load balancing", "Horizontal scaling", "Caching strategies", "Database sharding", "Monitoring/Alerting"],
            "difficulty": "hard"
        },
        {
            "question": "Describe your process for debugging a complex production issue.",
            "expected_answer": ["Reproducing the bug", "Checking logs/metrics", "Isolating the cause", "Implementing a fix", "Regression testing"],
            "difficulty": "medium"
        },
        {
            "question": "What are the advantages and disadvantages of using a microservices architecture?",
            "expected_answer": ["Independent scaling", "Technological diversity", "Operational complexity", "Network latency", "Data consistency"],
            "difficulty": "medium"
        }
    ],
    "frontend developer": [
        {
            "question": "Explain the concept of Virtual DOM and how it improves performance in React.",
            "expected_answer": ["Minimal DOM manipulation", "Diffing algorithm", "Batching updates", "Component lifecycle"],
            "difficulty": "medium"
        },
        {
            "question": "How do you optimize a web application for better Core Web Vitals scores?",
            "expected_answer": ["Lazy loading", "Image optimization", "Minification", "CDN usage", "Reducing render-blocking resources"],
            "difficulty": "hard"
        }
    ],
    "backend developer": [
        {
            "question": "Compare REST and GraphQL. When would you choose one over the other?",
            "expected_answer": ["Over-fetching/Under-fetching", "Strongly typed schema", "Standardization", "Caching complexity"],
            "difficulty": "medium"
        },
        {
            "question": "How do you handle database migrations in a production environment with zero downtime?",
            "expected_answer": ["Blue-green deployment", "Backward compatible changes", "Feature flags", "Staged rollouts"],
            "difficulty": "hard"
        }
    ],
    "general": [
        {
            "question": "Tell me about a technical project where you solved a meaningful problem. What was your approach and result?",
            "expected_answer": ["Problem definition", "Solution design", "Implementation", "Measurable impact"],
            "difficulty": "medium"
        },
        {
            "question": "How do you stay up-to-date with the latest trends and technologies in your field?",
            "expected_answer": ["Reading blogs", "Side projects", "Conferences", "Online courses"],
            "difficulty": "easy"
        }
    ]
}

def get_static_questions(role: str = "general", count: int = 1) -> list:
    role_key = role.lower()
    if role_key not in STATIC_QUESTIONS:
        role_key = "general"
    
    import random
    questions = STATIC_QUESTIONS[role_key]
    if count >= len(questions):
        return questions
    return random.sample(questions, count)
