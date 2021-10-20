from analyser.models import Personnel, CounselorAdvisorAssignment, AdvisorManagerAssignment
from analyser.serializers import PersonnelSerializer, CounselorAdvisorAssignmentSerializer, AdvisorManagerAssignmentSerializer
from django.db.models import Q

class UserManagement:
    def searchPersonnel(self, keyword):
        filter_name = Q(first_name__icontains=keyword) | Q(last_name__icontains=keyword)
        qs = Personnel.objects.filter(filter_name)

        results = PersonnelSerializer(qs, many=True)
        return results.data

    def searchPersonnelByRole(self, keyword, role):
        filter_name = Q(first_name__icontains=keyword) | Q(last_name__icontains=keyword)
        filter_role = Q(designation=role)
        qs = Personnel.objects.filter(filter_name, filter_role)

        results = PersonnelSerializer(qs, many=True)
        return results.data
       
    def assignCounselorToAdvisor(self, counselor, advisor):
        assign = CounselorAdvisorAssignment(counselor=counselor, advisor=advisor)
        assign.save()

        return True

    def assignAdvisorToManager(self, manager, advisor):
        assign = AdvisorManagerAssignment(manager=manager, advisor=advisor)
        assign.save()

        return True
    
    def getCounselorsAssignedToAdvisor(self, advisor):
        qs = CounselorAdvisorAssignment.objects.filter(advisor=advisor)
        results = CounselorAdvisorAssignmentSerializer(qs, many=True)

        return results.data

    def getAdvisorsAssignedToManager(self, manager_username):
        manager = Personnel.objects.get(Q(username=manager_username))

        qs = AdvisorManagerAssignment.objects.filter(manager=manager)
        results = AdvisorManagerAssignmentSerializer(qs, many=True)

        return results.data

    def getAllAdvisors(self):
        qs = Personnel.objects.filter(designation="business_advisor").all()
        results = PersonnelSerializer(qs, many=True)

        return results.data

    def getAllManagers(self):
        qs = Personnel.objects.filter(designation="program_manager").all()
        results = PersonnelSerializer(qs, many=True)

        return results.data
    
    def dropCounselorAssignedToAdvisor(self, counselor, advisor):
        obj = CounselorAdvisorAssignment.objects.get(counselor=counselor, advisor=advisor)
        obj.delete()

        return True

    def dropAdvisorAssignedToManager(self, manager, advisor):
        obj = AdvisorManagerAssignment.objects.get(manager=manager, advisor=advisor)
        obj.delete()

        return True