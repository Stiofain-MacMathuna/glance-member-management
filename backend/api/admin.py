## Interface

from django.contrib import admin
from .models import Institute, Member

@admin.register(Institute)
class InstituteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'country')
    search_fields = ('name', 'code')

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'institute', 'cern_id', 'is_active')
    list_filter = ('institute', 'is_active')
    search_fields = ('last_name', 'cern_id')