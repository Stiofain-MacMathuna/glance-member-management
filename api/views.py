import csv
from datetime import date
from django.http import HttpResponse
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend

from .models import Institute, Member, Shift, Analysis, Qualification
from .serializers import (
    InstituteSerializer, MemberSerializer, ShiftSerializer,
    AnalysisSerializer, QualificationSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class InstituteViewSet(viewsets.ModelViewSet):
    queryset = Institute.objects.all()
    serializer_class = InstituteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all().order_by('last_name')
    serializer_class = MemberSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'first_name', 'last_name', 'cern_id', 'email',
        'institute__name', 'institute__code'
    ]

    filterset_fields = {
        'is_active': ['exact'],
        'cern_status': ['exact'],
        'is_mo_qualified': ['exact'],
        'institute__country': ['exact'],
        'institute__name': ['icontains'],
    }

    ordering_fields = ['last_name', 'cern_id', 'institute__name']

    @action(detail=False, methods=['get'])
    def export(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="members_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['CERN_ID', 'First Name', 'Last Name', 'Institute', 'Status', 'MO_Qualified', 'Email'])

        for member in queryset:
            writer.writerow([
                member.cern_id, member.first_name, member.last_name,
                member.institute.name, member.cern_status,
                "Yes" if member.is_mo_qualified else "No", member.email
            ])
        return response


class AnalysisViewSet(viewsets.ModelViewSet):
    queryset = Analysis.objects.all().order_by('-creation_date')
    serializer_class = AnalysisSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'ref_code', 'group', 'target_journal', 'status_text']
    filterset_fields = ['group', 'phase', 'status_text']
    ordering_fields = ['creation_date', 'phase', 'group']

    @action(detail=False, methods=['get'])
    def export(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="analysis_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['Ref Code', 'Group', 'Title', 'Phase', 'Status', 'Start Date'])

        for paper in queryset:
            writer.writerow([
                paper.ref_code, paper.group, paper.title,
                paper.get_phase_display(), paper.status_text, paper.creation_date
            ])
        return response


class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['member', 'type', 'date']

    def create(self, request, *args, **kwargs):
        member_id = request.data.get('member')
        date = request.data.get('date')
        if Shift.objects.filter(member_id=member_id, date=date).exists():
            return Response(
                {"detail": "Conflict: Member already has a shift on this date."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)


class QualificationViewSet(viewsets.ModelViewSet):
    queryset = Qualification.objects.all()
    serializer_class = QualificationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# --- DASHBOARD ANALYTICS VIEW ---
class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        total_members = Member.objects.count()
        total_papers = Analysis.objects.count()
        upcoming_shifts = Shift.objects.filter(date__gte=date.today()).count()
        mo_qualified = Member.objects.filter(is_mo_qualified=True).count()

        # 1. Top Institutes (Headcount) -  Grouped by NAME
        top_institutes_data = Member.objects.values('institute__name') \
            .annotate(count=Count('id')) \
            .order_by('-count')[:10]

        # 2. Shift Locations
        shift_location_data = Shift.objects.values('location') \
            .annotate(count=Count('id')) \
            .order_by('-count')

        # 3. Top Institutes by Shift Contribution
        shift_institute_data = Shift.objects.values('member__institute__name') \
            .annotate(count=Count('id')) \
            .order_by('-count')[:8]

        # 4. Journals
        journal_data = Analysis.objects.values('target_journal') \
            .annotate(count=Count('id')) \
            .order_by('-count')

        # 5. Contract Status
        member_contract_data = Member.objects.values('cern_status') \
            .annotate(count=Count('id')) \
            .order_by('-count')

        # 6. Lifecycle Phase
        phase_raw = Analysis.objects.values('phase').annotate(count=Count('id')).order_by('phase')
        phase_map = {0: 'Phase 0 (Idea)', 1: 'Phase 1 (Analysis)', 2: 'Phase 2 (Review)', 3: 'Published'}
        phase_data = [{'label': phase_map.get(x['phase'], 'Unknown'), 'count': x['count']} for x in phase_raw]

        # 7. Paper Status
        paper_status_data = Analysis.objects.values('status_text') \
            .annotate(count=Count('id')) \
            .order_by('-count')[:5]

        return Response({
            "metrics": {
                "total_members": total_members,
                "upcoming_shifts": upcoming_shifts,
                "total_papers": total_papers,
                "mo_qualified_count": mo_qualified,
                "mo_percent": round((mo_qualified / total_members) * 100, 1) if total_members else 0
            },
            "charts": {
                "top_institutes": top_institutes_data,
                "shift_locations": shift_location_data,
                "top_shift_institutes": shift_institute_data,
                "journals": journal_data,
                "member_contracts": member_contract_data,
                "paper_phases": phase_data,
                "papers_status": paper_status_data
            }
        })