from django.core.management.base import BaseCommand
from api.models import Institute, Member, Shift, Qualification, Analysis
import random
from datetime import timedelta, date

try:
    from faker import Faker
except ImportError:
    Faker = None


class Command(BaseCommand):
    help = "Seeds the database with 5,000 members from realistic CMS institutes (excluding Russia) and operational data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Initializing Seeder...")

        if Faker:
            fake = Faker()
        else:
            # Fallback if Faker isn't installed
            class Fake:
                def first_name(self): return "Physicist"

                def last_name(self): return "Name"

                def email(self): return "email@cern.ch"

                def date_between(self, start_date, end_date): return date.today()

                def sentence(self, nb_words=6): return "Measurement of the Higgs Boson Cross Section"

                def company(self): return "University of Physics"

                def lexify(self, text): return "PHYS"

                def country(self): return "Switzerland"

                def unique(self): return self

                def random_number(self, digits=6): return 123456

                def year(self): return 2025

                def date_this_decade(self): return date.today()

            fake = Fake()

        # --- 1. Create Real Institutes (Expanded & Cleaned) ---
        self.stdout.write("Creating Institutes...")

        # A. CERN Member States (The Core Funders)
        member_states = [
            ("HEPHY Vienna", "Austria", "AT-VIE"),
            ("Université Libre de Bruxelles", "Belgium", "BE-ULB"),
            ("Vrije Universiteit Brussel", "Belgium", "BE-VUB"),
            ("University of Mons", "Belgium", "BE-MONS"),
            ("Sofia University", "Bulgaria", "BG-SOF"),
            ("Charles University Prague", "Czech Republic", "CZ-PRG"),
            ("Niels Bohr Institute", "Denmark", "DK-NBI"),
            ("NICPB Tallinn", "Estonia", "EE-TAL"),
            ("Helsinki Institute of Physics", "Finland", "FI-HEL"),
            ("CEA Saclay", "France", "FR-CEA"),
            ("Institut Pluridisciplinaire Hubert Curien", "France", "FR-IPHC"),
            ("LLR École Polytechnique", "France", "FR-LLR"),
            ("DESY Hamburg", "Germany", "DE-DESY"),
            ("RWTH Aachen University", "Germany", "DE-RWTH"),
            ("Karlsruhe Institute of Technology", "Germany", "DE-KIT"),
            ("University of Athens", "Greece", "GR-ATH"),
            ("University of Ioannina", "Greece", "GR-IOA"),
            ("Wigner RCP Budapest", "Hungary", "HU-WIG"),
            ("Weizmann Institute", "Israel", "IL-WEIZ"),
            ("Technion", "Israel", "IL-TECH"),
            ("INFN Rome", "Italy", "IT-ROMA"),
            ("INFN Bologna", "Italy", "IT-BOL"),
            ("INFN Pisa", "Italy", "IT-PISA"),
            ("INFN Torino", "Italy", "IT-TOR"),
            ("NIKHEF Amsterdam", "Netherlands", "NL-NIK"),
            ("University of Oslo", "Norway", "NO-OSL"),
            ("University of Warsaw", "Poland", "PL-WAR"),
            ("LIP Lisbon", "Portugal", "PT-LIP"),
            ("IFIN-HH Bucharest", "Romania", "RO-BUCH"),
            ("University of Belgrade", "Serbia", "RS-BEL"),
            ("Slovak Academy of Sciences", "Slovakia", "SK-SAS"),
            ("Jozef Stefan Institute", "Slovenia", "SI-LJU"),
            ("CIEMAT Madrid", "Spain", "ES-MAD"),
            ("Instituto de Física de Cantabria", "Spain", "ES-IFCA"),
            ("KTH Stockholm", "Sweden", "SE-KTH"),
            ("Uppsala University", "Sweden", "SE-UPP"),
            ("ETH Zurich", "Switzerland", "CH-ETH"),
            ("University of Zurich", "Switzerland", "CH-UZH"),
            ("Paul Scherrer Institute", "Switzerland", "CH-PSI"),
            ("Imperial College London", "United Kingdom", "UK-IMP"),
            ("University of Bristol", "United Kingdom", "UK-BRI"),
            ("Brunel University", "United Kingdom", "UK-BRU"),
            ("Rutherford Appleton Laboratory", "United Kingdom", "UK-RAL"),
        ]

        # B. Associate Member States & Cooperating States
        associate_states = [
            ("CBPF Rio de Janeiro", "Brazil", "BR-RIO"),
            ("Universidade do Estado do Rio de Janeiro", "Brazil", "BR-UERJ"),
            ("University of Split", "Croatia", "HR-SPL"),
            ("University of Cyprus", "Cyprus", "CY-NIC"),
            ("Tata Institute (TIFR)", "India", "IN-TIFR"),
            ("Panjab University", "India", "IN-PAN"),
            ("University College Dublin", "Ireland", "IE-UCD"),
            ("Riga Technical University", "Latvia", "LV-RIG"),
            ("Vilnius University", "Lithuania", "LT-VIL"),
            ("NCP Islamabad", "Pakistan", "PK-NCP"),
            ("METU Ankara", "Türkiye", "TR-ANK"),
            ("Bogazici University", "Türkiye", "TR-BOG"),
            ("Kharkiv Inst. of Physics", "Ukraine", "UA-KHAR"),
        ]

        # C. Major Partners (USA is huge in CMS, plus China, Japan, Korea)
        partners = [
            ("CERN", "Switzerland", "CERN"),  # Host
            ("IHEP Beijing", "China", "CN-IHEP"),
            ("Peking University", "China", "CN-PKU"),
            ("University of Tokyo", "Japan", "JP-TOK"),
            ("Kyungpook National University", "South Korea", "KR-KNU"),
            ("Seoul National University", "South Korea", "KR-SNU"),
            ("Fermilab", "USA", "US-FNAL"),  # Major Hub
            ("MIT", "USA", "US-MIT"),
            ("Caltech", "USA", "US-CALT"),
            ("Princeton University", "USA", "US-PRI"),
            ("University of Wisconsin Madison", "USA", "US-WIS"),
            ("UCSD", "USA", "US-UCSD"),
            ("Cornell University", "USA", "US-COR"),
            ("Florida State University", "USA", "US-FSU"),
        ]

        all_institutes_data = member_states + associate_states + partners

        institutes = []
        for name, country, code in all_institutes_data:
            # We use get_or_create to avoid duplicates if running seed multiple times without flush
            inst, _ = Institute.objects.get_or_create(name=name, country=country, code=code)
            institutes.append(inst)

        # --- 2. Clear existing data ---
        self.stdout.write("Clearing old data...")
        Shift.objects.all().delete()
        Qualification.objects.all().delete()
        Analysis.objects.all().delete()
        Member.objects.all().delete()
        # Note: We keep institutes created above or previously exists, but you can delete if you want a clean slate
        # Institute.objects.all().delete()

        # --- 3. Bulk Create 5,000 Members ---
        self.stdout.write("Generating 5,000 members...")
        members_to_create = []

        # REALISTIC CERN CONTRACT TYPES
        statuses = [
            'USER', 'USER', 'USER', 'USER',  # Majority are Users
            'STAFF',  # Rare
            'FELLOW', 'FELLOW',  # Junior Researchers
            'DOCTORAL STUDENT', 'DOCTORAL STUDENT',
            'PJAS',  # Project Associates (Real CERN term)
            'TECHNICAL STUDENT'
        ]

        for i in range(5000):
            # Weighted random: CERN and Fermilab have more people
            if random.random() < 0.15:
                # Pick from CERN or Fermilab (known codes)
                inst = next((x for x in institutes if x.code in ['CERN', 'US-FNAL']), institutes[0])
            else:
                inst = random.choice(institutes)

            status = random.choice(statuses)

            # Logic for M&O Qualified:
            # PhD holders (Staff, Fellow, Users, PJAS) are billable. Students are not.
            if status in ['STAFF', 'FELLOW', 'USER', 'PJAS']:
                is_mo = random.choice([True, True, True, False])  # 75% chance
            else:
                is_mo = False

            members_to_create.append(Member(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                cern_id=f"10{i:04d}",
                institute=inst,
                email=fake.email(),
                is_active=random.choice([True, True, True, False]),
                cern_status=status,
                is_mo_qualified=is_mo,
                contract_end_date=fake.date_between(start_date='+1y', end_date='+5y')
            ))

        Member.objects.bulk_create(members_to_create)

        # --- 4. Create Shifts (For first 1500 active members) ---
        self.stdout.write("Generating shifts...")
        active_members = list(Member.objects.filter(is_active=True)[:1500])
        shift_types = ['MORNING', 'EVENING', 'NIGHT']

        # REALISTIC CMS SHIFT LOCATIONS
        locations = [
            'P5 Control Room',  # Point 5 (Cessy) - The Detector
            'CMS Centre (Meyrin)',  # Main Campus Control Room
            'Fermilab ROC',  # Remote Ops Center (Chicago)
            'DESY ROC',  # Remote Ops Center (Germany)
            'Remote (Zoom)',  # Data Quality / Offline
            'Site 40 Lab'  # Hardware Integration
        ]

        shifts_to_create = []
        for member in active_members:
            # Assign 0 to 8 shifts per person
            for _ in range(random.randint(0, 8)):
                shifts_to_create.append(Shift(
                    member=member,
                    date=fake.date_between(start_date='-30d', end_date='+60d'),
                    type=random.choice(shift_types),
                    location=random.choice(locations)
                ))
        Shift.objects.bulk_create(shifts_to_create)

        # --- 5. Create Qualifications ---
        self.stdout.write("Generating qualifications...")
        quals_list = [
            "LHC Control Room Operator",
            "Radiation Safety Level 2",
            "CMS Guide",
            "Python Developer Certification",
            "Cryogenics Expert",
            "Detector on Call",
            "DQM Shifter"
        ]

        quals_to_create = []
        for member in Member.objects.all()[:2000]:
            for _ in range(random.randint(1, 3)):
                quals_to_create.append(Qualification(
                    member=member,
                    name=random.choice(quals_list),
                    date_earned=fake.date_between(start_date='-5y', end_date='today')
                ))
        Qualification.objects.bulk_create(quals_to_create)

        # --- 6. Create Analyses (Papers) ---
        self.stdout.write("Generating scientific papers...")
        groups = ['ATLAS', 'CMS', 'ALICE', 'LHCb', 'TOTEM', 'LHCf', 'MOEDAL', 'FASER', 'SND']
        statuses = ["Draft", "Editor Review", "CWR (Collaboration Wide Review)", "Submitted", "Accepted"]

        # REALISTIC HIGH IMPACT JOURNALS
        journals = [
            "JHEP",  # Journal of High Energy Physics (Standard)
            "Phys. Rev. D",  # Physical Review D (Standard)
            "Phys. Rev. Lett.",  # Letters (High Impact)
            "Eur. Phys. J. C",  # EPJC (Standard)
            "Nature Physics",  # Very High Impact
            "Nature"  # Dream Goal
        ]

        analyses_to_create = []
        for i in range(300):
            group = random.choice(groups)
            year = random.choice([2022, 2023, 2024, 2025])
            ref_code = f"{group}-{year}-{i:04d}"

            analyses_to_create.append(Analysis(
                title=fake.sentence(nb_words=10).replace(".", ""),
                ref_code=ref_code,
                group=group,
                phase=random.choice([0, 1, 2, 3]),
                status_text=random.choice(statuses),
                target_journal=random.choice(journals),
                creation_date=fake.date_between(start_date='-2y', end_date='today')
            ))

        Analysis.objects.bulk_create(analyses_to_create)

        # --- 7. Assign Authors ---
        self.stdout.write("Assigning authors to papers...")
        all_members_list = list(Member.objects.all()[:2000])
        saved_analyses = Analysis.objects.all()

        for paper in saved_analyses:
            # Randomly assign 5 to 50 authors per paper
            authors = random.sample(all_members_list, k=random.randint(5, 50))
            paper.authors.set(authors)

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded 5,000 members from {len(institutes)} institutes!'))