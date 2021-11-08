from django.template import Context
from django.template.loader import get_template
import jinja2
import datetime
from xhtml2pdf import pisa
import pdfkit

from wkhtmltopdf.views import PDFTemplateView

class HtmlToPdf:
    def generatePDF(page, data):
        templateLoader = jinja2.FileSystemLoader(searchpath="analyser/templates/jinja2")
        templateEnv = jinja2.Environment(loader=templateLoader)
        
        template = templateEnv.get_template(page)
        html = template.render(data)
        
        file = open('tmpfiles/test.pdf', "w+b")
        pisaStatus = pisa.CreatePDF(html.encode('utf-8'), dest = file,
        encoding = 'utf-8')

        file.seek(0)
        pdf = file.read()
        file.close()

        return pdf

    # def pdfKit(data):
    #     templateLoader = jinja2.FileSystemLoader(searchpath="analyser/templates/jinja2")
    #     templateEnv = jinja2.Environment(loader=templateLoader)
        
    #     template = templateEnv.get_template('pdf_templates/group_stats.html')
    #     #context = Context({"data": data})

    #     html = template.render(data)
        
    #     pdfkit.from_string(html, 'tmpfiles/tft.pdf')
        
        #pdfkit.from_file('analyser/templates/jinja2/pdf_templates/group_stats.html', 'tmpfiles/tft.pdf')