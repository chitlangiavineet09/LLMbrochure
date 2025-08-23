# imports
# If these fail, please check you're running from an 'activated' environment with (llms) in the command prompt

import os
import requests
import json
from typing import List
from dotenv import load_dotenv
from bs4 import BeautifulSoup
# from IPython.display import Markdown, display
from openai import OpenAI
import gradio as gr
# import markdown
# from weasyprint import HTML, CSS
# -----------------------------------------------------------------------------------------------

# Initialize and constants
#loading the .env file which has open ai key and calling openai class

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

if api_key and api_key.startswith('sk-proj-') and len(api_key)>10:
    print("API key looks good so far")
else:
    print("There might be a problem with your API key? Please visit the troubleshooting notebook!")
    
MODEL = 'gpt-4o-mini'
openai = OpenAI()

# -----------------------------------------------------------------------------------------------

# A class to represent a Webpage
# Some websites need you to use proper headers when fetching them:
#We are scraping the content of home page and all the links present in the home page
headers = {
 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

class Website:
    """
    A utility class to represent a Website that we have scraped, now with links
    """

    def __init__(self, url):
        self.url = url
        response = requests.get(url, headers=headers)
        self.body = response.content
        soup = BeautifulSoup(self.body, 'html.parser')
        # self.body2=soup
        self.title = soup.title.string if soup.title else "No title found"
        # print(soup.body)
        if soup.body:
            for irrelevant in soup.body(["script", "style", "img", "input"]):
                irrelevant.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)
        else:
            self.text = ""
        links = [link.get('href') for link in soup.find_all('a')]
        self.links = []
        for link in links:
            if link:
                self.links.append(link)

    def get_contents(self):
        return f"Webpage Title:\n{self.title}\nWebpage Contents:\n{self.text}\n\n"


# arm=Website("https://www.arm.com/")
# print (arm.links)

# LLM use1 to get the links - system prompt-----------------------------------------------------------------------------------------

link_system_prompt = "You are provided with a list of links found on a webpage. \
You are able to decide which of the links would be most relevant to include in a brochure about the company, \
such as links to an About page, or a Company page, or Careers/Jobs pages.\n"
link_system_prompt += "You should respond in JSON as in this example:"
link_system_prompt += """
{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page", "url": "https://another.full.url/careers"}
    ]
}
"""

# LLM use1 to get the links - function to get the user prompt-----------------------------------------------------------------------------------------

def get_links_user_prompt(website):
    link_user_prompt = f"Here is the list of links on the website of {website.url}."
    link_user_prompt += f"Please decide which of these are relevant web links for a brochure about the company, respond with the full https URL in JSON format. \
Do not include Terms of Service, Privacy, email links.\n"
    link_user_prompt += "\n".join(website.links)   
    return link_user_prompt

# print(get_links_user_prompt(arm))

# LLM use1 to get the links - function to call the OpenAI API-----------------------------------------------------------------------------------------

def get_relevant_links(url):
    website=Website(url)
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": link_system_prompt},
            {"role": "user", "content": get_links_user_prompt(website)}
        ],
        response_format={"type": "json_object"}
    )
    result = response.choices[0].message.content
    return json.loads(result)

# print(get_relevant_links("https://www.arm.com/"))

# function combining data from landing page and all the relevant links in the website-----------------------------------------------------------------------------------------

def get_all_details(url):
    website=Website(url)
    content=website.get_contents()
    links=get_relevant_links(url)
    for link in links["links"]:
        content += f"\n\n{link["type"]}\n"
        content += Website(link["url"]).get_contents()
    return content

# print(get_all_details("https://www.arm.com/"))

#LLM use2 to get the brochure - system prompt-----------------------------------------------------------------------------------------

brochure_system_prompt = """You are a assistant who creates company brochures for clients, investors, \
prospective employees and other stakeholders. You have the ability to take company related information \
given and convert it into a consise brochure in the language required by the user. Include details about company \
business, products, culture and opportunity. Please keep the brochure formal, provide sections for \
contents and give output in markdown format. The output need to be strictly in markdown format."""
 
# print(brochure_system_prompt)

 #LLM use2 to get the brochure - function to get the user prompt----------------------------------------------------------------------------------------

language="English"
def get_brochure_user_prompt(url, language): 
    user_prompt = f"Here is the content of the website of {url}."
    user_prompt += f"Please create a brochure about the company in {language}."
    user_prompt += f"\n\n{get_all_details(url)}"
    return user_prompt

# file = open("filename.txt",mode="w")
# file.write(get_brochure_user_prompt("https://www.arm.com/"))
# file.close()

# print(get_brochure_user_prompt("https://www.arm.com/"))

def generate_pdf(markdown_content):
    # Convert markdown to HTML
    html_content = markdown.markdown(markdown_content)
    
    # Create full HTML document
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            h1, h2, h3 {{ color: #333; }}
            .content {{ max-width: 800px; margin: 0 auto; }}
        </style>
    </head>
    <body>
        <div class="content">{html_content}</div>
    </body>
    </html>
    """
    pdf = HTML(string=full_html).write_pdf()
    
    file=open("brochure.pdf","w")
    file.write(pdf)
    file.close()


#LLM use2 to get the brochure - function to call the OpenAI API-----------------------------------------------------------------------------------------

def get_brochure_content(url, language):
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": brochure_system_prompt},
            {"role": "user", "content": get_brochure_user_prompt(url, language)}
        ],
    )
    result = response.choices[0].message.content
    # generate_pdf(result)
    return result
    

# print(get_brochure_content("https://www.arm.com/"))

#Adding interface to this-----------------------------------------------------------------------------------------

view = gr.Interface(
    fn=get_brochure_content,
    inputs=[gr.Textbox(label="Please type the wesite URL"), gr.Dropdown(["English", "Hindi", "French", "Chinese"], label="Please select the language", value="English")],
    outputs=[gr.Markdown(label="Response:")],
    flagging_mode="never"
)
view.launch(share=True)





