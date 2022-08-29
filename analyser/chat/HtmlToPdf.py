from django import template
from django.template import Context
from django.template.loader import get_template
import jinja2
import datetime
from xhtml2pdf import pisa
import pdfkit


from weasyprint import HTML
from pathlib import Path

from wkhtmltopdf.views import PDFTemplateView

class HtmlToPdf:
    # def generatePDF(page, data):
    #     import os
    #     templateLoader = jinja2.FileSystemLoader(searchpath="analyser/templates/jinja2")
    #     templateEnv = jinja2.Environment(loader=templateLoader)
        
       
    #     template = get_template(page)
    #     html = template.render(data)
        
    #     file = open('pdfFiles/'+data['fileName'], "w+b")
    #     pisaStatus = pisa.CreatePDF(html.encode('utf-8'), dest = file,
    #     encoding = 'utf-8')

    #     file.seek(0)
    #     pdf = file.read()
    #     file.close()

    #     return pdf


    def generatePDF(page, data):
        infile = "analyser/templates/jinja2/pdf_templates/group_stats.html"

        templateLoader = jinja2.FileSystemLoader(searchpath="analyser/templates/jinja2")
        templateEnv = jinja2.Environment(loader=templateLoader)
        
        template = get_template(page)
        
        html = template.render(data)

        #html = Path(infile).read_text()
        """Generate a PDF file from a string of HTML."""
        htmldoc = HTML(string=html, base_url="")
        pdf = htmldoc.write_pdf()
        Path('pdfFiles/'+data['fileName']).write_bytes(pdf)

        # f = open("/tmp/test.txt", "w")
        # f.write("Hello")
        # f.close()        
        print("Saving to storage")

        return pdf

    

