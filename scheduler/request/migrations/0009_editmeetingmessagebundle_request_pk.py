# Generated by Django 4.1.4 on 2023-09-26 21:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0008_alter_editsectionrequest_section'),
    ]

    operations = [
        migrations.AddField(
            model_name='editmeetingmessagebundle',
            name='request_pk',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
