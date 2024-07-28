import gradio as gr
from bs4 import BeautifulSoup
import requests
from jinja2 import Template
from urllib.parse import urljoin
import os
import warnings
import logging

warnings.filterwarnings("ignore")

# Set up logging
logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

books = {
    "College Physics AP": {
        "conceptual_link": "https://openstax.org/books/college-physics-ap-courses-2e/pages/{}-conceptual-questions",
        "problem_link": "https://openstax.org/books/college-physics-ap-courses-2e/pages/{}-problems-exercises",
        "href_base_url": "https://openstax.org/books/college-physics-ap-courses-2e/pages/"
    },
    "University Physics Vol. 1": {
        "conceptual_link": "https://openstax.org/books/university-physics-volume-1/pages/{}-conceptual-questions",
        "problem_link": "https://openstax.org/books/university-physics-volume-1/pages/{}-problems",
        "href_base_url": "https://openstax.org/books/university-physics-volume-1/pages/"
    },
    "University Physics Vol. 2": {
        "conceptual_link": "https://openstax.org/books/university-physics-volume-2/pages/{}-conceptual-questions",
        "problem_link": "https://openstax.org/books/university-physics-volume-2/pages/{}-problems",
        "href_base_url": "https://openstax.org/books/university-physics-volume-2/pages/"
    }
}

img_base_url = 'https://openstax.org'

def get_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        response.raise_for_status()  # Raise an HTTPError for bad responses
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except requests.RequestException as e:
        logging.error(f"An error occurred when getting HTML: {e}")
        return None

def get_question(exercises, question_index, img_base_url, href_base_url):
    question_index = question_index - 1
    
    if question_index >= len(exercises):
        return "Question index out of range."

    exercise_div = exercises[question_index]
    logging.debug(f"Processing exercise: {exercise_div}")

    for img_tag in exercise_div.find_all('img'):
        img_tag['src'] = urljoin(img_base_url, img_tag['data-lazy-src'])

    for a_tag in exercise_div.find_all('a'):
        a_tag['href'] = urljoin(href_base_url, a_tag['href'])
        
    return str(exercise_div)

def get_all_questions(book_key, unit_num, conceptual_list, problem_list):
    book = books[book_key]
    conceptual_url = book["conceptual_link"].format(int(unit_num))
    problem_url = book["problem_link"].format(int(unit_num))

    conceptual_html = get_html(conceptual_url)
    if conceptual_html is None:
        return []
    problem_html = get_html(problem_url)
    if problem_html is None:
        return []

    conceptual_exercises = conceptual_html.find_all('div', {'data-type': 'exercise'})
    problem_exercises = problem_html.find_all('div', {'data-type': 'exercise'})
    questions = []

    for i in conceptual_list:
        questions.append(get_question(conceptual_exercises, i, img_base_url, book["href_base_url"]))
    
    for i in problem_list:
        questions.append(get_question(problem_exercises, i, img_base_url, book["href_base_url"]))
    
    return questions

def generate_html(book_key, chapter_num, conceptual_input, problem_input, path):
    conceptual_list = list(map(int, conceptual_input.split(",")) if conceptual_input else [])
    problem_list = list(map(int, problem_input.split(",")) if problem_input else [])

    questions = get_all_questions(book_key, int(chapter_num), conceptual_list, problem_list)
    template_str = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chapter {{ chapter_number }} Questions</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.13.11/dist/katex.min.css">
        <script defer src="https://cdn.jsdelivr.net/npm/katex@0.13.11/dist/katex.min.js"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/katex@0.13.11/dist/contrib/auto-render.min.js"
                onload="renderMathInElement(document.body);"></script>
        <style>
            body {
                font-family: 'Calibri', sans-serif;
                font-size: 20px;
            }
            .page-break {
                page-break-after: always;
            }
            .mathjax {
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div>
            <h2>Chapter: {{ chapter_number }}</h2>
            {% if conceptual_problem_list %}
                <h2>Conceptual Problems: {{ conceptual_problem_list|join(", ") }}</h2>
            {% endif %}
            {% if problems_and_exercise_list %}
                <h2>Problems and Exercises: {{ problems_and_exercise_list|join(", ") }}</h2>
            {% endif %}
        </div>
        <div class="page-break"></div>
        
        {% for question in questions %}
            <div class="mathjax">{{ question|safe }}</div>
            <div class="page-break"></div>
        {% endfor %}
    </body>
    </html>
    '''
    template = Template(template_str)
    
    rendered_html = template.render(chapter_number=int(chapter_num),
                                    conceptual_problem_list=conceptual_list,
                                    problems_and_exercise_list=problem_list,
                                    questions=questions)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

def main_function(book_key, unit_num, conceptual_input, problem_input):
    try:
        if not conceptual_input and not problem_input:
            return "Both lists cannot be empty. Please provide at least one."

        # Ensure the directory exists
        abs_path = "D:\\projects\\phy_pdf"
        if not os.path.exists(abs_path):
            os.makedirs(abs_path)

        # Delete all existing HTML files in the directory
        for file_name in os.listdir(abs_path):
            if file_name.endswith(".html"):
                os.remove(os.path.join(abs_path, file_name))

        file_name = "questions_" + str(int(unit_num))
        html_path = os.path.join(abs_path, file_name + ".html")

        generate_html(book_key, unit_num, conceptual_input, problem_input, html_path)

        logging.info("HTML generated successfully")
        return html_path
    except Exception as e:
        logging.error(f"An error occurred in main_function: {e}")
        return "An error occurred. Please check the logs for more details."

iface = gr.Interface(
    fn=main_function,
    inputs=[
        gr.Dropdown(label="Select Book", choices=list(books.keys())),
        gr.Number(label="Chapter Number"),
        gr.Textbox(label="Conceptual Problems List (comma-separated)"),
        gr.Textbox(label="Problems & Exercises List (comma-separated)")
    ],
    outputs=gr.File(label="Generated HTML"),
    live=False
)

iface.launch()
