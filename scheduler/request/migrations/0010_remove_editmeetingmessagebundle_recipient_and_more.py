# Generated by Django 5.0 on 2024-01-11 21:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
        ('request', '0009_editmeetingmessagebundle_request_pk'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='editmeetingmessagebundle',
            name='recipient',
        ),
        migrations.RemoveField(
            model_name='editmeetingmessagebundle',
            name='request',
        ),
        migrations.RemoveField(
            model_name='editmeetingmessagebundle',
            name='sender',
        ),
        migrations.RemoveField(
            model_name='editrequestbundle',
            name='requester',
        ),
        migrations.CreateModel(
            name='EditMeetingMessageBundleRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_sent', models.DateTimeField(auto_now_add=True)),
                ('message', models.CharField(blank=True, default=None, max_length=300, null=True)),
                ('request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='message_bundles', to='request.editrequestbundle')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requested_bundles', to='authentication.professor')),
            ],
            options={
                'ordering': ['-date_sent'],
            },
        ),
        migrations.CreateModel(
            name='EditMeetingMessageBundleResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_sent', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(blank=True, default=False)),
                ('status', models.CharField(choices=[('accepted', 'Accepted'), ('revised_accepted', 'Revised and Accepted'), ('denied', 'Denied')], max_length=20)),
                ('message', models.CharField(blank=True, default=None, max_length=300, null=True)),
                ('request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='response', to='request.editmeetingmessagebundlerequest')),
                ('section_bundle', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='response', to='request.editrequestbundle')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='authorized_bundles', to='authentication.professor')),
            ],
        ),
        migrations.DeleteModel(
            name='EditMeetingMessage',
        ),
        migrations.DeleteModel(
            name='EditMeetingMessageBundle',
        ),
    ]