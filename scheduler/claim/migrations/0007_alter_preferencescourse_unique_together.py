# Generated by Django 5.0 on 2024-02-21 04:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('claim', '0006_preferencescourse'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='preferencescourse',
            unique_together={('preferences', 'course')},
        ),
    ]
