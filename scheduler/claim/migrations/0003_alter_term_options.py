# Generated by Django 4.1.4 on 2023-08-13 04:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('claim', '0002_meeting_is_sharable'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='term',
            options={'ordering': ('-year', models.Case(models.When(season='fall', then=1), models.When(season='winter', then=2), models.When(season='spring', then=3), models.When(season='summer', then=4), default=0, output_field=models.IntegerField()))},
        ),
    ]