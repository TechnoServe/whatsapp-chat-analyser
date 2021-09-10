from django.core.management.base import BaseCommand
from analyser.analyser import Analyser


class Command(BaseCommand):
    help = 'Process all pending chat files'

    def handle(self, *args, **options):
        """Select and configure the provider that the user wants to send the message with

        """
        analyser = Analyser()
        analyser.process_pending_chats()
