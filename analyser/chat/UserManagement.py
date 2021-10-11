from analyser.models import Personnel, CounselorAdvisorAssignment, AdvisorManagerAssignment
from analyser.serializers import PersonnelSerializer, CounselorAdvisorAssignmentSerializer, AdvisorManagerAssignmentSerializer
from django.db.models import Q

class UserManagement:
    searchPersonnel(self, keyword):
        filter_name = Q(first_name__icontains=keyword) | Q(last_name__icontains=keyword)
        qs = Personnel.objects.filter(filter_name)

        results = PersonnelSerializer(qs, many=True)
        return results.data

    searchPersonnelByRole(self, keyword, role):
        filter_name = Q(first_name__icontains=keyword) | Q(last_name__icontains=keyword)
        filter_role = Q(designation=role)
        qs = Personnel.objects.filter(filter_name, filter_role)

        results.data = PersonnelSerializer(qs, many=True)
        return results.data
       
    assignCounselorToAdvisor(self, counselor_username, advisor_username):
        counselor = Personnel.objects.get(Q(username=counselor_username))
        advisor = Personnel.objects.get(Q(username=advisor_username))

        assign = CounselorAdvisorAssignment(counselor=counselor, advisor=advisor)
        assign.save()

        return True

    assignAdvisorToManager(self, manager_username, advisor_username):
        manager = Personnel.objects.get(Q(username=manager_username))
        advisor = Personnel.objects.get(Q(username=advisor_username))

        assign = AdvisorManagerAssignment(manager=manager, advisor=advisor)
        assign.save()

        return True
    
    getCounselorsAssignedToAdvisors(self, advisor_username):
        advisor = Personnel.objects.get(Q(username=advisor_username))

        qs = CounselorAdvisorAssignment.objects.filter(advisor=advisor)
        results = CounselorAdvisorAssignmentSerializer(qs, many=True)

        return results.data

    getAdvisorsAssignedToManagers(self, manager_username):
        manager = Personnel.objects.get(Q(username=manager_username))

        qs = AdvisorManagerAssignment.objects.filter(advisor=advisor)
        results = AdvisorManagerAssignmentSerializer(qs, many=True)

        return results.data