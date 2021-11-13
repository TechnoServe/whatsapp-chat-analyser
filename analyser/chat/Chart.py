import matplotlib.pyplot as plt
import numpy as np

class Chart:
    def CategoriesOfInformation(data):
        # Pie chart, where the slices will be ordered and plotted counter-clockwise:
        labels = 'Images', 'Messages', 'Links', 'Emojis'
        
        explode = (0, 0.1, 0, 0)  # only "explode" the 2nd slice (i.e. 'Hogs')

        fig1, ax1 = plt.subplots()
        ax1.pie(data, explode=explode, labels=labels, autopct='%1.1f%%',
                shadow=True, startangle=90)
        ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

        plt.legend(['Images', 'Messages', 'Links', 'Emojis'], loc="lower right")

        plt.savefig("analyser/templates/jinja2/pdf_templates/pie_chart.png")

        return plt