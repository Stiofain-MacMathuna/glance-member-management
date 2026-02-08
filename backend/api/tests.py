from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User  # <--- Added this
from .models import Member, Institute, Analysis, Shift


class DashboardIntegrationTests(APITestCase):
    """
    Tests the 'Incubator Dashboard' logic to ensure the charts
    are telling the truth.
    """

    def setUp(self):
        # 1. Setup Base Data
        self.cern = Institute.objects.create(name="CERN", country="Switzerland", code="CERN")
        self.mit = Institute.objects.create(name="MIT", country="USA", code="MIT")

        # 2. Create a specific mix of workforce
        # 1 Staff (Qualified)
        Member.objects.create(
            first_name="Admin", last_name="User", cern_id="001",
            institute=self.cern, cern_status="STAFF", is_mo_qualified=True
        )
        # 2 PJAS (Qualified)
        Member.objects.create(first_name="Eng", last_name="One", cern_id="002", institute=self.mit, cern_status="PJAS",
                              is_mo_qualified=True)
        Member.objects.create(first_name="Eng", last_name="Two", cern_id="003", institute=self.mit, cern_status="PJAS",
                              is_mo_qualified=True)
        # 1 Student (Not Qualified)
        Member.objects.create(first_name="Student", last_name="New", cern_id="004", institute=self.mit,
                              cern_status="DOCTORAL STUDENT", is_mo_qualified=False)

        # 3. Create Analyses
        Analysis.objects.create(title="Higgs 1", ref_code="H1", group="HIG", phase=3)  # Published
        Analysis.objects.create(title="Susy 1", ref_code="S1", group="SUS", phase=1)  # Active

    def test_dashboard_metrics_accuracy(self):
        """Verify the top-level KPI numbers (Total Members, M&O %, etc.)"""
        response = self.client.get('/api/stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # Check KPI: Total Members
        self.assertEqual(data['metrics']['total_members'], 4)

        # Check KPI: M&O Qualified (3 out of 4 members are qualified)
        self.assertEqual(data['metrics']['mo_qualified_count'], 3)
        self.assertEqual(data['metrics']['mo_percent'], 75.0)  # (3/4)*100

        # Check KPI: Total Papers
        self.assertEqual(data['metrics']['total_papers'], 2)

    def test_chart_data_integrity(self):
        """Verify the bar chart data structures"""
        response = self.client.get('/api/stats/')
        charts = response.data['charts']

        # Check Workforce Composition Chart
        statuses = [item['cern_status'] for item in charts['member_contracts']]
        self.assertIn("PJAS", statuses)
        self.assertIn("STAFF", statuses)

        # Verify count for PJAS is 2
        pjas_data = next(item for item in charts['member_contracts'] if item['cern_status'] == "PJAS")
        self.assertEqual(pjas_data['count'], 2)


class ShiftManagementTests(APITestCase):
    """
    Tests the interactive 'Shift Manager' features.
    """

    def setUp(self):
        # --- FIX: Create a user and log them in ---
        self.user = User.objects.create_user(username='testadmin', password='testpassword')
        self.client.force_authenticate(user=self.user)

        self.inst = Institute.objects.create(name="Fermilab", country="USA", code="FNAL")
        self.member = Member.objects.create(
            first_name="Shift", last_name="Worker", cern_id="999",
            institute=self.inst, cern_status="USER"
        )
        self.url = '/api/shifts/'

    def test_create_shift(self):
        """Test assigning a new shift via the modal"""
        payload = {
            "member": self.member.id,
            "date": "2025-10-15",
            "type": "NIGHT",
            "location": "P5 Control Room (Cessy)"
        }
        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Shift.objects.count(), 1)
        self.assertEqual(Shift.objects.first().location, "P5 Control Room (Cessy)")

    def test_delete_shift(self):
        """Test the 'X' button functionality"""
        shift = Shift.objects.create(member=self.member, date="2025-10-15", type="MORNING", location="Remote")

        delete_url = f"{self.url}{shift.id}/"
        response = self.client.delete(delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Shift.objects.count(), 0)


class AnalysisTrackerTests(APITestCase):
    """
    Tests the Scientific Paper tracking logic.
    """

    def setUp(self):
        Analysis.objects.create(title="A", ref_code="A1", group="ATLAS", target_journal="JHEP", phase=0)
        Analysis.objects.create(title="B", ref_code="B1", group="CMS", target_journal="Nature", phase=3)
        Analysis.objects.create(title="C", ref_code="C1", group="CMS", target_journal="Phys. Rev. Lett.", phase=2)

    def test_filter_by_target_journal(self):
        """Ensure we can filter by the new journal field"""
        url = '/api/analyses/?search=Nature'
        response = self.client.get(url)

        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['target_journal'], "Nature")

    def test_phase_filtering(self):
        """Test filtering by lifecycle phase (e.g., Published vs Draft)"""
        url = '/api/analyses/?phase=3'  # Published
        response = self.client.get(url)

        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ref_code'], "B1")


class MemberDirectoryTests(APITestCase):
    """
    Tests the Directory search and filter features.
    """

    def setUp(self):
        self.inst_ch = Institute.objects.create(name="CERN", country="Switzerland", code="CERN")
        self.inst_us = Institute.objects.create(name="Caltech", country="USA", code="CALT")

        Member.objects.create(first_name="Hans", last_name="Zimmer", cern_id="101", institute=self.inst_ch,
                              cern_status="STAFF")
        Member.objects.create(first_name="John", last_name="Doe", cern_id="102", institute=self.inst_us,
                              cern_status="USER")

    def test_super_search_query(self):
        """Test the global search bar logic"""
        # Search by CERN ID
        response = self.client.get('/api/members/?search=101')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['first_name'], "Hans")

        # Search by Institute Name
        response = self.client.get('/api/members/?search=Caltech')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['last_name'], "Doe")

    def test_contract_filter(self):
        """Test filtering by the new contract types"""
        response = self.client.get('/api/members/?cern_status=STAFF')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['first_name'], "Hans")