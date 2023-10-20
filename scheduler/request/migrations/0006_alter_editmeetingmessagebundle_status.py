# Generated by Django 4.1.4 on 2023-09-26 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0005_remove_editmeetingmessage_request_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='editmeetingmessagebundle',
            name='status',
            field=models.CharField(choices=[('requested', 'Requested'), ('accepted', 'Accepted'), ('revised_accepted', 'Revised and Accepted'), ('denied', 'Denied'), ('canceled', 'Canceled')], max_length=20),
        ),
    ]