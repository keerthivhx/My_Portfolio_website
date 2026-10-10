import os
import re

html_path = 'templates/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    data = f.read()

# Update email
data = data.replace('your_email@gmail.com', 'keerthivkeerthiv635@gmail.com')

# Update projects
old_projects_marker_start = '<div class="projects-grid">'
old_projects_marker_end = '</section>'

new_projects = '''<div class="projects-grid">
                <div class="project-card">
                    <h3>ProPath AI</h3>
                    <p>Modern full-stack web application providing AI-driven career guidance and insights. Leverages Node.js/Express and MongoDB Atlas.</p>
                    <div class="tags"><span class="chip small">JavaScript</span><span class="chip small">Node.js</span><span class="chip small">MongoDB</span></div>
                    <a href="https://github.com/keerthivhx/PROPATH-AI---Progressive-Pathway-AI" target="_blank" class="btn small">GitHub Repo</a>
                </div>
                <div class="project-card">
                    <h3>DockQuery AI</h3>
                    <p>AI-powered document question-answering system using RAG to allow users to upload documents and ask questions about their content.</p>
                    <div class="tags"><span class="chip small">RAG</span><span class="chip small">AI</span><span class="chip small">LLMs</span></div>
                    <a href="https://github.com/keerthivhx/DockQuery_AI" target="_blank" class="btn small">GitHub Repo</a>
                </div>
                <div class="project-card">
                    <h3>PathFinder AI</h3>
                    <p>AI-Powered Indoor Navigation & Smart Wayfinding Platform using Google Gemini for context-aware directions.</p>
                    <div class="tags"><span class="chip small">TypeScript</span><span class="chip small">Kotlin</span><span class="chip small">Gemini</span></div>
                    <a href="https://github.com/keerthivhx/PathFounder-AI" target="_blank" class="btn small">GitHub Repo</a>
                </div>
                <div class="project-card">
                    <h3>Customer Segmentation</h3>
                    <p>Python and K-Means Clustering to group customers based on income and spending behavior. Includes data preprocessing and visualization.</p>
                    <div class="tags"><span class="chip small">Python</span><span class="chip small">K-Means</span><span class="chip small">Jupyter</span></div>
                    <a href="https://github.com/keerthivhx/Customer-Segmentation-Project." target="_blank" class="btn small">GitHub Repo</a>
                </div>
            </div>
        </div>
    '''

# Regex replace the projects grid
data = re.sub(r'<div class="projects-grid">.*?</div>\s*</div>\s*', new_projects, data, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(data)

if os.path.exists('.env'):
    with open('.env', 'r', encoding='utf-8') as f:
        env_data = f.read()
    env_data = re.sub(r'GMAIL_USER=.*', 'GMAIL_USER=keerthivkeerthiv635@gmail.com', env_data)
    env_data = re.sub(r'RECEIVER_EMAIL=.*', 'RECEIVER_EMAIL=keerthivkeerthiv635@gmail.com', env_data)
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_data)
