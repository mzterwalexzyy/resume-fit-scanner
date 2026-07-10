"""
Synthetic, clearly-fake resume/job-description pairs used to exercise the
analyze_resume_fit pipeline end-to-end. None of these describe real people
or real companies.
"""

# --- Pair A: strong match, clean formatting ---------------------------------

RESUME_A = """
Jordan Rivera
jordan.rivera.demo@example.com | (555) 010-2044

Summary
Backend engineer with 4 years of experience building web services.

Experience
Backend Engineer, Nimbus Cloud Systems -- Jun 2022 - Present
- Built REST API services in Python using Django and PostgreSQL.
- Containerized services with Docker and deployed to AWS.
- Used Git and GitHub for version control in an Agile/Scrum team.
- Wrote unit tests and maintained CI/CD pipelines with Jenkins.

Junior Developer, Fictional Data Co -- Aug 2020 - May 2022
- Maintained internal tools with Python and MySQL.
- Participated in sprint planning and code reviews.

Education
B.S. in Computer Science, Springfield State University, 2020

Skills
Python, Django, PostgreSQL, Docker, AWS, REST API, Git, Agile, unit testing, CI/CD
"""

JOB_DESCRIPTION_A = """
Backend Engineer -- Fictional Startup Inc.

About the role
We are looking for a Backend Engineer to help build and scale our core API.

Requirements
- Strong experience with Python and Django or Flask
- Experience with PostgreSQL and relational database design
- Experience with Docker and AWS
- Familiarity with REST API design
- Comfortable with Git and Agile/Scrum workflows
- Experience with unit testing and CI/CD pipelines

Preferred
- Knowledge of Kubernetes
- Experience with GraphQL
"""

# --- Pair B: weak match, with deliberate ATS formatting issues ---------------

RESUME_B = """
Taylor Nguyen ✉ taylor.n.demo@example.com ☎ 555-019-3321

EXPERIENCE
Marketing Coordinator | Acme Retail Co
Ran social media campaigns and tracked engagement metrics.

Skills          Level
Excel           |  Advanced
PowerPoint      |  Advanced
Google Analytics|  Intermediate
Social Media Marketing | Advanced

Handled day to day marketing operations including copywriting, email marketing campaigns, content calendars, vendor coordination, budget tracking, event planning, and cross-functional collaboration with the sales and product teams on a wide range of ongoing seasonal promotional initiatives throughout the year.
"""

JOB_DESCRIPTION_B = """
Senior Data Scientist -- Fictional Analytics Corp

Responsibilities
- Build machine learning and deep learning models for demand forecasting
- Write production Python code and SQL queries against large datasets
- Design and analyze A/B testing experiments
- Build data pipelines and ETL processes
- Use TensorFlow or PyTorch for model development
- Deploy models on AWS or GCP
- Communicate findings clearly to non-technical stakeholders

Qualifications
- 5+ years of experience in data science or applied statistics
- Strong communication and presentation skills
"""

# --- Pair C: invalid input (should be rejected, not scored) -----------------

RESUME_C_GIBBERISH = "asdkj qweoiu random text not a resume at all lol"
JOB_DESCRIPTION_C_GIBBERISH = "zzz not a job posting just noise words here ok"


PAIRS = {
    "strong_match": (RESUME_A, JOB_DESCRIPTION_A),
    "weak_match_with_formatting_issues": (RESUME_B, JOB_DESCRIPTION_B),
    "invalid_input": (RESUME_C_GIBBERISH, JOB_DESCRIPTION_C_GIBBERISH),
}
