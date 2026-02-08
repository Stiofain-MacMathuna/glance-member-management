from rest_framework import serializers
from .models import Institute, Member, Shift, Analysis, Qualification


class InstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institute
        fields = '__all__'


class SimpleAuthorSerializer(serializers.ModelSerializer):
    institute_name = serializers.CharField(source='institute.name', read_only=True)

    class Meta:
        model = Member
        fields = ['id', 'first_name', 'last_name', 'cern_id', 'institute_name']


class QualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qualification
        fields = ['id', 'name', 'date_earned']


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ['id', 'date', 'type', 'location', 'member']


class MemberSerializer(serializers.ModelSerializer):
    institute_name = serializers.CharField(source='institute.name', read_only=True)
    institute_country = serializers.CharField(source='institute.country', read_only=True)

    shifts = ShiftSerializer(many=True, read_only=True)
    qualifications = QualificationSerializer(many=True, read_only=True)

    class Meta:
        model = Member
        fields = ['id', 'first_name', 'last_name', 'cern_id', 'institute',
                  'institute_name', 'institute_country',
                  'email', 'cern_status', 'contract_end_date', 'is_active',
                  'is_mo_qualified', 'shifts', 'qualifications']


class AnalysisSerializer(serializers.ModelSerializer):
    author_count = serializers.IntegerField(source='authors.count', read_only=True)
    phase_name = serializers.CharField(source='get_phase_display', read_only=True)
    group_name = serializers.CharField(source='get_group_display', read_only=True)
    authors = SimpleAuthorSerializer(many=True, read_only=True)

    class Meta:
        model = Analysis
        fields = ['id', 'ref_code', 'title', 'group', 'group_name',
                  'phase', 'phase_name', 'status_text', 'target_journal',
                  'creation_date', 'author_count', 'authors']