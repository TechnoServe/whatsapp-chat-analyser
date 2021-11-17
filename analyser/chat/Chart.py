import matplotlib.pyplot as plt


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
        plt.title("Categories of Information Sent")

        plt.savefig("analyser/templates/jinja2/pdf_templates/pie_chart.png")
        plt.clf()
        plt.close()
        return True

    
    def activeDaysChart(data):
        
        fig = plt.figure(figsize = (20, 10))

        plt.xlabel("Date")
        plt.ylabel("Messages")
        plt.xticks(rotation=90)

        plt.title("Active Days")        

        dates = data['dates']
        messages = data['messages']
        x_list = dates[::4]
        y_list = messages[::4]

        plt.bar(x_list, y_list)
        plt.savefig("analyser/templates/jinja2/pdf_templates/active_days.png")
        plt.clf()
        plt.close('all')
        return True