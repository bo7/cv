from flask import Flask, render_template, send_file, request, url_for, redirect, session
from werkzeug.utils import safe_join
import markdown2
import pdfkit
import os
from weasyprint import HTML
from datetime import datetime
import tempfile
import logging
from logging.handlers import RotatingFileHandler
import glob
import anthropic
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
def setup_logger():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure file handler
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.DEBUG)
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Get the Flask app logger
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.DEBUG)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Create Flask app with explicit template and static folders
app = Flask(__name__,
            template_folder=os.path.abspath('templates'),
            static_folder=os.path.abspath('static'))

# Setup logger
logger = setup_logger()

# Initialize Anthropic client with API key from environment
client = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Set Flask secret key from environment
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Add login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def ensure_temp_dir():
    """Ensure temp directory exists with proper permissions"""
    try:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'temp')
        logger.debug(f"Creating temp directory at: {temp_dir}")
        
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, mode=0o777, exist_ok=True)
            logger.info(f"Created temp directory with permissions 777")
        
        return temp_dir
    except Exception as e:
        logger.error(f"Error creating temp directory: {str(e)}")
        raise

def read_markdown_file(language='en'):
    try:
        filename = f"data/cv_{language}.md"
        logger.debug(f"Reading markdown file: {filename}")
        
        if not os.path.exists(filename):
            logger.error(f"Markdown file not found: {filename}")
            raise FileNotFoundError(f"File not found: {filename}")
        
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"Successfully read markdown file: {filename}")
        return content
    except Exception as e:
        logger.error(f"Error reading markdown file: {str(e)}")
        raise

def generate_pdf(language='en'):
    markdown_content = read_markdown_file(language)
    logger.debug(f"Generating PDF for {language} version")
    
    # Convert markdown to HTML with proper styling
    html_content = markdown2.markdown(markdown_content, extras=['tables', 'break-on-newline'])
    
    styled_html = f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Arial', sans-serif;
                    margin: 0;
                    padding: 0;
                    color: #333;
                    line-height: 1.6;
                    background-color: #f9f9f9;
                }}

                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #fff;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }}

                h1 {{
                    color: #0073e6;
                    text-align: center;
                    font-size: 24px;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #0073e6;
                    padding-bottom: 10px;
                }}

                h2 {{
                    color: #0073e6;
                    font-size: 20px;
                    margin-top: 25px;
                    margin-bottom: 15px;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 5px;
                }}

                h3 {{
                    color: #333;
                    font-size: 18px;
                    margin-bottom: 10px;
                }}

                h4 {{
                    color: #666;
                    font-size: 16px;
                    margin-top: 5px;
                    margin-bottom: 10px;
                }}

                p {{
                    margin: 5px 0;
                }}

                ul {{
                    list-style-type: disc;
                    margin: 5px 0;
                    padding-left: 20px;
                }}

                li {{
                    margin-bottom: 5px;
                    font-family: 'Arial', sans-serif;
                }}

                strong {{
                    color: #0073e6;
                }}

                hr {{
                    border: none;
                    border-top: 1px solid #eee;
                    margin: 20px 0;
                }}

                .section {{
                    margin-bottom: 20px;
                }}

                .job {{
                    margin-bottom: 15px;
                    padding: 10px;
                    background: #f8f9fa;
                    border-left: 3px solid #0073e6;
                }}

                .education {{
                    margin-bottom: 15px;
                    padding: 10px;
                    background: #f8f9fa;
                }}

                .skills {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                }}

                @page {{
                    size: A4;
                    margin: 2cm;
                }}

                pre {{
                    font-family: 'Arial', sans-serif;
                    margin: 0;
                    padding: 0;
                    white-space: pre-wrap;
                    font-size: inherit;
                    line-height: 1.6;
                }}

                pre:before {{
                    content: "•";
                    color: #333;
                    display: inline-block;
                    width: 1em;
                    margin-left: -1em;
                }}

                * {{
                    font-family: 'Arial', sans-serif;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                {html_content}
            </div>
        </body>
    </html>
    """
    
    # Generate PDF using the complete HTML content
    try:
        temp_dir = ensure_temp_dir()
        pdf_filename = f'cv_{language}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        pdf_path = os.path.join(temp_dir, pdf_filename)
        
        # Use WeasyPrint to generate PDF
        HTML(string=styled_html).write_pdf(pdf_path)
        logger.debug(f"Successfully generated PDF at: {pdf_path}")
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise

def generate_latex(language='en'):
    markdown_content = read_markdown_file(language)
    template_file = f"data/cv_template{'_de' if language == 'de' else ''}.tex"
    logger.debug(f"Generating LaTeX for {language} version")
    
    with open(template_file, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Convert markdown content to LaTeX
    latex_content = ""
    sections = markdown_content.split('---\n')
    
    for section in sections:
        if not section.strip():
            continue
            
        lines = section.strip().split('\n')
        for line in lines:
            if line.startswith('# '):
                latex_content += f"\\section*{{{line[2:]}}}\n"
            elif line.startswith('## '):
                latex_content += f"\\section{{{line[3:]}}}\n"
            elif line.startswith('### '):
                latex_content += f"\\subsection*{{{line[4:]}}}\n"
            elif line.startswith('#### '):
                latex_content += f"\\subsubsection*{{{line[5:]}}}\n"
            elif line.startswith('- '):
                if not latex_content.endswith('\\begin{itemize}\n'):
                    latex_content += '\\begin{itemize}\n'
                latex_content += f"\\item {line[2:]}\n"
            elif line.startswith('	•'):
                if not latex_content.endswith('\\begin{itemize}\n'):
                    latex_content += '\\begin{itemize}\n'
                latex_content += f"\\item {line[2:]}\n"
            elif line.strip() and latex_content.endswith('\\begin{itemize}\n'):
                latex_content += '\\end{itemize}\n'
                latex_content += f"{line}\n"
            elif line.strip():
                latex_content += f"{line}\n"
    
    if latex_content.endswith('\\begin{itemize}\n'):
        latex_content += '\\end{itemize}\n'
    
    # Replace special characters
    latex_content = latex_content.replace('_', '\\_')
    latex_content = latex_content.replace('&', '\\&')
    latex_content = latex_content.replace('$', '\\$')
    latex_content = latex_content.replace('%', '\\%')
    latex_content = latex_content.replace('#', '\\#')
    latex_content = latex_content.replace('**', '')  # Remove markdown bold
    
    # Replace the placeholder with the generated content
    final_content = template.replace('[CV content will be dynamically inserted here]', latex_content)
    
    # Write to file
    output_path = f'static/temp/cv_{language}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.tex'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    logger.debug(f"Successfully generated LaTeX at: {output_path}")
    return output_path

def get_media_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(base_dir, 'static', 'images')
    
    # Get all image files
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        image_files.extend(glob.glob(os.path.join(image_dir, ext)))
    
    # Convert to relative paths and create media info
    media_info = []
    for img_path in image_files:
        filename = os.path.basename(img_path)
        if 'StartUpderWoche' in filename:
            title = "WIRTSCHAFTSWOCHE: SILEO IST STARTUP DER WOCHE"
        elif 'InternationalBusForum' in filename:
            title = "INTERNATIONAL BUS FORUM"
        elif 'ElekBu' in filename:
            title = "ELEKBU"
        else:
            title = filename
            
        media_info.append({
            'src': url_for('static', filename=f'images/{filename}'),
            'alt': title,
            'title': title
        })
    
    return media_info

# Add login routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == os.getenv('LOGIN_PASSWORD'):
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Update the index route to require login
@app.route('/')
@login_required
def index():
    try:
        logger.info("Loading index page")
        media_files = get_media_files()
        return render_template('index.html', media_files=media_files)
    except Exception as e:
        logger.error(f"Error loading index page: {str(e)}")
        return f"Error loading CV: {str(e)}", 500

@app.route('/download/<format>/<language>')
def download(format, language):
    try:
        logger.info(f"Processing download request: format={format}, language={language}")
        
        if format == 'md':
            filename = safe_join('data', f'cv_{language}.md')
            logger.debug(f"Downloading markdown file: {filename}")
            
            if not os.path.exists(filename):
                logger.error(f"File not found: {filename}")
                return "File not found", 404
                
            return send_file(
                filename,
                as_attachment=True,
                download_name=f"cv_{language}.md",
                mimetype='text/markdown'
            )
        
        elif format == 'pdf':
            logger.debug("Generating PDF")
            pdf_path = generate_pdf(language)
            
            if not os.path.exists(pdf_path):
                logger.error(f"PDF generation failed, file not found: {pdf_path}")
                return "PDF generation failed", 500
                
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=f"cv_{language}.pdf",
                mimetype='application/pdf'
            )
        
        elif format == 'latex':
            logger.debug("Generating LaTeX")
            latex_path = generate_latex(language)
            
            if not os.path.exists(latex_path):
                logger.error(f"LaTeX generation failed, file not found: {latex_path}")
                return "LaTeX generation failed", 500
                
            return send_file(
                latex_path,
                as_attachment=True,
                download_name=f"cv_{language}.tex",
                mimetype='application/x-tex'
            )
            
    except Exception as e:
        logger.error(f"Error in download route: {str(e)}")
        return f"Error generating file: {str(e)}", 500

@app.route('/preview/<language>')
def preview(language):
    try:
        logger.info(f"Loading preview for language: {language}")
        content = read_markdown_file(language)
        logger.debug(f"Successfully loaded preview content for {language}")
        return content
    except Exception as e:
        logger.error(f"Error loading preview: {str(e)}")
        return str(e), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        question = request.form.get('question')
        
        # Read the profile markdown
        with open('data/Sven_Bohnstedt_Profile.md', 'r', encoding='utf-8') as f:
            profile_content = f.read()
        
        # Create the API request with specific parameters for business-like responses
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            temperature=0.1,  # Lower temperature for more factual responses
            system="You are a professional colleague of Sven Bohnstedt. Respond in a business-appropriate tone, focusing on facts from the provided document. Be precise and concise, avoiding speculation. Format responses professionally and maintain a respectful, collegial tone.",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Here is a document about Sven Bohnstedt:\n\n{profile_content}\n\nAs a professional colleague, please answer this question based strictly on the provided information: {question}"
                    }
                ]
            }]
        )
        
        return response.content[0].text
        
    except Exception as e:
        logger.error(f"Error in ask route: {str(e)}")
        return f"Error processing question: {str(e)}", 500

if __name__ == '__main__':
    try:
        # Create necessary directories with proper permissions
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"Base directory: {base_dir}")
        
        static_dir = os.path.join(base_dir, 'static')
        os.makedirs(static_dir, exist_ok=True)
        os.chmod(static_dir, 0o755)
        logger.info(f"Created static directory: {static_dir}")
        
        temp_dir = os.path.join(static_dir, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        os.chmod(temp_dir, 0o777)
        logger.info(f"Created temp directory: {temp_dir}")
        
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        os.chmod(data_dir, 0o755)
        logger.info(f"Created data directory: {data_dir}")
        
        # Set debug mode and run
        app.debug = True
        logger.info("Starting Flask application in debug mode")
        app.run(host='0.0.0.0', port=5590, debug=True)
        
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}")
        raise 