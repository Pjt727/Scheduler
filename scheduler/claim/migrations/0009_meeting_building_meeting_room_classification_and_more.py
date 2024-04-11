# Generated by Django 5.0 on 2024-03-28 02:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('claim', '0008_alter_preferencescourse_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='building',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='claim.building'),
        ),
        migrations.AddField(
            model_name='meeting',
            name='room_classification',
            field=models.CharField(blank=True, choices=[('LEC', 'Lecture'), ('LAB', 'Laboratory')], max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='meeting',
            name='student_minimum',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]