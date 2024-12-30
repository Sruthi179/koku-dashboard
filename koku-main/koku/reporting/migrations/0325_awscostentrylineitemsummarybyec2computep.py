# Generated by Django 4.2.14 on 2024-09-23 11:11
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations
from django.db import models

from koku.database import set_pg_extended_mode
from koku.database import unset_pg_extended_mode


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0324_ocppvc_csi_volume_handle"),
    ]

    operations = [
        migrations.RunPython(code=set_pg_extended_mode, reverse_code=unset_pg_extended_mode),
        migrations.CreateModel(
            name="AWSCostEntryLineItemSummaryByEC2ComputeP",
            fields=[
                ("uuid", models.UUIDField(primary_key=True, serialize=False)),
                ("usage_start", models.DateField()),
                ("usage_end", models.DateField(null=True)),
                ("usage_account_id", models.CharField(max_length=50)),
                ("resource_id", models.CharField(max_length=256)),
                ("instance_name", models.CharField(max_length=256, null=True)),
                ("instance_type", models.CharField(max_length=50, null=True)),
                ("operating_system", models.CharField(max_length=50, null=True)),
                ("region", models.CharField(max_length=50, null=True)),
                ("vcpu", models.IntegerField(null=True)),
                ("memory", models.CharField(max_length=50, null=True)),
                ("unit", models.CharField(max_length=63, null=True)),
                ("usage_amount", models.DecimalField(decimal_places=9, max_digits=24, null=True)),
                ("normalization_factor", models.FloatField(null=True)),
                ("normalized_usage_amount", models.FloatField(null=True)),
                ("currency_code", models.CharField(max_length=10)),
                ("unblended_rate", models.DecimalField(decimal_places=9, max_digits=24, null=True)),
                ("unblended_cost", models.DecimalField(decimal_places=9, max_digits=24, null=True)),
                ("markup_cost", models.DecimalField(decimal_places=9, max_digits=24, null=True)),
                ("blended_rate", models.DecimalField(decimal_places=9, max_digits=24, null=True)),
                ("blended_cost", models.DecimalField(decimal_places=9, max_digits=24, null=True)),
                ("markup_cost_blended", models.DecimalField(decimal_places=15, max_digits=33, null=True)),
                ("savingsplan_effective_cost", models.DecimalField(decimal_places=9, max_digits=24, null=True)),
                ("markup_cost_savingsplan", models.DecimalField(decimal_places=15, max_digits=33, null=True)),
                ("calculated_amortized_cost", models.DecimalField(decimal_places=9, max_digits=33, null=True)),
                ("markup_cost_amortized", models.DecimalField(decimal_places=9, max_digits=33, null=True)),
                ("public_on_demand_cost", models.DecimalField(decimal_places=9, max_digits=24, null=True)),
                ("public_on_demand_rate", models.DecimalField(decimal_places=9, max_digits=24, null=True)),
                ("tax_type", models.TextField(null=True)),
                ("tags", models.JSONField(null=True)),
                ("source_uuid", models.UUIDField(null=True)),
                ("cost_category", models.JSONField(null=True)),
                (
                    "account_alias",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.PROTECT, to="reporting.awsaccountalias"
                    ),
                ),
                (
                    "cost_entry_bill",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.CASCADE, to="reporting.awscostentrybill"
                    ),
                ),
            ],
            options={
                "db_table": "reporting_awscostentrylineitem_summary_by_ec2_compute_p",
                "indexes": [
                    models.Index(fields=["usage_start"], name="ec2cp_usage_start_idx"),
                    models.Index(fields=["usage_account_id"], name="ec2cp_usage_account_id_idx"),
                    models.Index(fields=["account_alias"], name="ec2cp_account_alias_idx"),
                    models.Index(fields=["resource_id"], name="ec2cp_resource_id_idx"),
                    models.Index(fields=["instance_name"], name="ec2cp_instance_name_idx"),
                    models.Index(fields=["instance_type"], name="ec2cp_instance_type_idx"),
                    models.Index(fields=["region"], name="ec2cp_region_idx"),
                    models.Index(fields=["operating_system"], name="ec2cp_os_idx"),
                    django.contrib.postgres.indexes.GinIndex(fields=["tags"], name="ec2cp_tags_idx"),
                    django.contrib.postgres.indexes.GinIndex(fields=["cost_category"], name="ec2cp_cost_category_idx"),
                ],
            },
        ),
        migrations.RunPython(code=unset_pg_extended_mode, reverse_code=set_pg_extended_mode),
    ]
