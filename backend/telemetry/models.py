from django.db import models

class LhcSector(models.Model):
    name = models.CharField(max_length=50) # e.g., "Sector 1-2"
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class MachineEvent(models.Model):
    STATUS_CHOICES = [
        ('OK', 'Healthy'),
        ('WARNING', 'Degraded'),
        ('FAULT', 'CRITICAL (Quench)'),
    ]

    sector = models.ForeignKey(LhcSector, on_delete=models.CASCADE, related_name='events')
    timestamp = models.DateTimeField(auto_now_add=True)
    signal_type = models.CharField(max_length=100) # e.g., "Magnet Temperature"
    value = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OK')

    class Meta:
        ordering = ['-timestamp']