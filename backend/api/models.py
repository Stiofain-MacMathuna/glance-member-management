from django.db import models


class Institute(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=50)
    code = models.CharField(max_length=20)

    def __str__(self):
        return self.code


class Member(models.Model):
    STATUS_CHOICES = [
        ('USER', 'User'),
        ('STAFF', 'Staff'),
        ('FELLOW', 'Fellow'),
        ('DOCTORAL STUDENT', 'Doctoral Student')
    ]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    cern_id = models.CharField(max_length=20, unique=True)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE)
    email = models.EmailField()

    cern_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='USER')

    is_active = models.BooleanField(default=True)

    is_mo_qualified = models.BooleanField(default=False, help_text="Counted for Maintenance & Operations statistics")

    contract_end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Shift(models.Model):
    TYPE_CHOICES = [('MORNING', 'Morning'), ('EVENING', 'Evening'), ('NIGHT', 'Night')]
    member = models.ForeignKey(Member, related_name='shifts', on_delete=models.CASCADE)
    date = models.DateField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    location = models.CharField(max_length=100)


class Qualification(models.Model):
    member = models.ForeignKey(Member, related_name='qualifications', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    date_earned = models.DateField()


class Analysis(models.Model):
    PHASE_CHOICES = [
        (0, 'Phase 0 (Idea)'),
        (1, 'Phase 1 (Analysis)'),
        (2, 'Phase 2 (Review)'),
        (3, 'Published'),
    ]
    GROUP_CHOICES = [
        ('ATLAS', 'ATLAS'),
        ('CMS', 'CMS'),
        ('ALICE', 'ALICE'),
        ('LHCb', 'LHCb'),
        ('TOTEM', 'TOTEM'),
        ('LHCf', 'LHCf'),
        ('MOEDAL', 'MoEDAL'),
        ('FASER', 'FASER'),
        ('SND', 'SND@LHC'),
    ]

    title = models.CharField(max_length=250)
    ref_code = models.CharField(max_length=20, unique=True)
    group = models.CharField(max_length=10, choices=GROUP_CHOICES)
    phase = models.IntegerField(choices=PHASE_CHOICES, default=0)
    status_text = models.CharField(max_length=100, default="Draft")
    target_journal = models.CharField(max_length=100, blank=True)
    creation_date = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    authors = models.ManyToManyField(Member, related_name='papers')

    def __str__(self):
        return self.ref_code