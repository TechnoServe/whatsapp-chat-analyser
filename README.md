# WhatsApp Chat Analyser API

## Description

This API enables user to upload whatsapp group exports from a dashboard or via email.

The API then analyses the text files and sends back analysed data. 

The text file is saved to Google Drive along with the message, members and events output files

Analysed data is received as a `json` with the following information:
- members with metadata
- messages with metadata
- events with metadata
- links to the output files
- most_active_members
- most_popular_emojis
- most_active_days
- most_active_time
- chat_group
- date_uploaded
- uploaded_by
- media


## Getting Started

### Dependencies
- Python 3.6

### Installing packages
- `pip install -r requirements.txt`

### Run Celery tasks
Celery will allow server to listen for emails sent for analysis

- `celery -A mspark_whatsapp_analyzer beat -l info`
- `celery -A mspark_whatsapp_analyzer worker -l info`

