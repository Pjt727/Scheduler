# Generated by Django 4.1.4 on 2023-07-03 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('claim', '0007_alter_section_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='is_general_purpose',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]