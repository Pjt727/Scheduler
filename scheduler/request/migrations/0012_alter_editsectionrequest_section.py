# Generated by Django 5.0 on 2024-01-16 03:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('claim', '0003_alter_term_options'),
        ('request', '0011_alter_editmeetingmessagebundlerequest_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='editsectionrequest',
            name='section',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='edit_sections', to='claim.section'),
        ),
    ]