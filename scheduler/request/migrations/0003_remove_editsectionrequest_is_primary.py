# Generated by Django 4.1.4 on 2023-09-14 20:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0002_alter_editmeetingmessagebundle_options'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='editsectionrequest',
            name='is_primary',
        ),
    ]