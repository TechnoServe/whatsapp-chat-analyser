'''
page
'''

from django.conf import settings

from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class EnhancedPageNumberPagination(PageNumberPagination):

    page_size_query_param = 'page_size'
    max_page_size = settings.MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_size', self.page.paginator.per_page),
            ('current_page', self.page.number),
            ('total_pages', self.page.paginator.num_pages),
            ('start_index', self.page.start_index()),
            ('end_index', self.page.end_index()),
            ('results', data)
        ]))
