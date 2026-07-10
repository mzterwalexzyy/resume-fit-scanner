"""
Curated, hand-maintained vocabulary used to deterministically spot skill/tool
mentions in job descriptions and resumes. This is intentionally a plain data
list (not model-generated) so that extraction stays reproducible: the same
job description text always yields the same requirement set.
"""

# Canonical skill/tool/methodology terms. Matching is case-insensitive and
# word-boundary aware (see core/extract.py). Multi-word entries are matched
# as phrases.
SKILLS_TAXONOMY = [
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "bash",
    "shell scripting", "matlab", "perl",
    # Web / frontend
    "react", "react.js", "vue", "vue.js", "angular", "next.js", "svelte",
    "html", "css", "sass", "tailwind", "redux", "webpack",
    # Backend / frameworks
    "node.js", "express", "django", "flask", "fastapi", "spring", "spring boot",
    ".net", "asp.net", "graphql", "rest api", "grpc", "microservices",
    # Data / ML
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "pytorch", "tensorflow", "keras", "scikit-learn",
    "pandas", "numpy", "data analysis", "data science", "data engineering",
    "etl", "data pipeline", "data visualization", "tableau", "power bi",
    "statistics", "a/b testing", "predictive modeling",
    # Cloud / devops
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
    "ansible", "jenkins", "ci/cd", "devops", "linux", "unix", "git", "github",
    "gitlab", "cloudformation", "serverless", "lambda",
    # Databases
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "dynamodb", "sqlite", "oracle", "nosql", "database design",
    # Project management / methodology
    "agile", "scrum", "kanban", "jira", "confluence", "product management",
    "project management", "stakeholder management", "roadmap planning",
    "sprint planning", "waterfall", "pmp",
    # Business / finance
    "financial modeling", "financial analysis", "budgeting", "forecasting",
    "accounting", "gaap", "excel", "powerpoint", "salesforce", "crm",
    "business development", "market research", "competitive analysis",
    "go-to-market", "b2b", "b2c", "p&l management", "kpi tracking",
    # Marketing
    "seo", "sem", "content marketing", "social media marketing",
    "email marketing", "google analytics", "google ads", "brand strategy",
    "copywriting", "growth marketing",
    # Design
    "figma", "sketch", "adobe photoshop", "adobe illustrator", "ui design",
    "ux design", "user research", "wireframing", "prototyping",
    # Soft skills / general
    "communication", "leadership", "problem solving", "critical thinking",
    "team collaboration", "cross-functional collaboration", "mentoring",
    "public speaking", "negotiation", "time management", "adaptability",
    "customer service", "presentation skills", "conflict resolution",
    # Certifications
    "cpa", "cfa", "aws certified", "pmp certification", "six sigma",
    "scrum master", "csm",
    # QA / testing
    "unit testing", "test automation", "selenium", "cypress", "qa testing",
    "quality assurance",
    # Security
    "cybersecurity", "penetration testing", "network security",
    "information security", "compliance", "risk management", "soc 2",
    "gdpr",
]

# Common abbreviation / alternate-spelling pairs. Keys and values are both
# lowercase; presence of either side counts as a match for the other.
SYNONYMS = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "k8s": "kubernetes",
    "node": "node.js",
    "nodejs": "node.js",
    "reactjs": "react.js",
    "vuejs": "vue.js",
    "postgres": "postgresql",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "ci": "ci/cd",
    "cd": "ci/cd",
    "gcp": "google cloud",
    "ga": "google analytics",
    "crm": "customer relationship management",
    "qa": "quality assurance",
    "pm": "project management",
}

# Words too generic to ever count as an extracted requirement on their own,
# used to filter regex-derived candidate phrases (see core/extract.py).
GENERIC_STOPWORDS = {
    "the", "and", "or", "a", "an", "of", "to", "in", "with", "for", "on",
    "is", "are", "be", "as", "at", "by", "will", "you", "we", "our", "your",
    "this", "that", "years", "year", "experience", "strong", "excellent",
    "good", "ability", "skills", "knowledge", "understanding", "proven",
    "demonstrated", "working", "etc", "including", "such", "plus", "role",
    "team", "candidate", "candidates",
}
