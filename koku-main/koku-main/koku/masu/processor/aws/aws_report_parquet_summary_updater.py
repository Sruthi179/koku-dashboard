#
# Copyright 2021 Red Hat Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""Summary Updater for AWS Parquet files."""
import logging

import ciso8601
from django.conf import settings
from django.utils import timezone
from django_tenants.utils import schema_context

from api.common import log_json
from koku.pg_partition import PartitionHandlerMixin
from masu.database import AWS_CUR_TABLE_MAP
from masu.database.aws_report_db_accessor import AWSReportDBAccessor
from masu.database.cost_model_db_accessor import CostModelDBAccessor
from masu.processor import is_feature_cost_4403_ec2_compute_cost_enabled
from masu.util.common import date_range_pair
from reporting.provider.aws.models import UI_SUMMARY_TABLES

LOG = logging.getLogger(__name__)


class AWSReportParquetSummaryUpdater(PartitionHandlerMixin):
    """Class to update AWS report parquet summary data."""

    def __init__(self, schema, provider, manifest):
        """Establish parquet summary processor."""
        self._schema = schema
        self._provider = provider
        self._manifest = manifest
        self._context = {
            "schema": self._schema,
            "provider_uuid": self._provider.uuid,
        }

    def _get_sql_inputs(self, start_date, end_date):
        """Get the required inputs for running summary SQL."""

        if isinstance(start_date, str):
            start_date = ciso8601.parse_datetime(start_date).date()
        if isinstance(end_date, str):
            end_date = ciso8601.parse_datetime(end_date).date()

        return start_date, end_date

    def update_summary_tables(self, start_date, end_date, **kwargs):
        """Populate the summary tables for reporting.

        Args:
            start_date (str) The date to start populating the table.
            end_date   (str) The date to end on.

        Returns
            (str, str) A start date and end date.

        """
        start_date, end_date = self._get_sql_inputs(start_date, end_date)
        ec2_compute_summary_table = AWS_CUR_TABLE_MAP["ec2_compute_summary"]

        with schema_context(self._schema):
            partition_summary_tables = (*UI_SUMMARY_TABLES, ec2_compute_summary_table)
            self._handle_partitions(self._schema, partition_summary_tables, start_date, end_date)

        with CostModelDBAccessor(self._schema, self._provider.uuid) as cost_model_accessor:
            markup = cost_model_accessor.markup
            markup_value = float(markup.get("value", 0)) / 100

        with AWSReportDBAccessor(self._schema) as accessor:
            # Need these bills on the session to update dates after processing
            with schema_context(self._schema):
                bills = accessor.bills_for_provider_uuid(self._provider.uuid, start_date)
                bill_ids = [str(bill.id) for bill in bills]
                current_bill_id = bills.first().id if bills else None

            if current_bill_id is None:
                LOG.info(
                    log_json(
                        msg="no bill was found, skipping summarization",
                        context=self._context,
                        start_date=start_date,
                    )
                )
                return start_date, end_date

            for start, end in date_range_pair(start_date, end_date, step=settings.TRINO_DATE_STEP):
                LOG.info(
                    log_json(
                        msg="updating AWS report summary tables via Trino",
                        context=self._context,
                        start_date=start,
                        end_date=end,
                    )
                )
                filters = {
                    "cost_entry_bill_id": current_bill_id
                }  # Use cost_entry_bill_id to leverage DB index on DELETE
                accessor.delete_line_item_daily_summary_entries_for_date_range_raw(
                    self._provider.uuid, start, end, filters
                )
                accessor.populate_line_item_daily_summary_table_trino(
                    start, end, self._provider.uuid, current_bill_id, markup_value
                )
                accessor.populate_ui_summary_tables(start, end, self._provider.uuid)
            accessor.populate_tags_summary_table(bill_ids, start_date, end_date)
            accessor.populate_category_summary_table(bill_ids, start_date, end_date)
            accessor.update_line_item_daily_summary_with_tag_mapping(start_date, end_date, bill_ids)

            # Populate ec2 compute summary table if feature is enabled for schema
            if is_feature_cost_4403_ec2_compute_cost_enabled(self._schema):
                LOG.info(f"AWS EC2 compute summary is enabled for schema: {self._schema}")

                # Ensure start_date is first day of the month
                month_start_date = start_date.replace(day=1)

                # Delete records from the EC2 compute summary table for a specified source and date range before insert
                accessor.delete_line_item_daily_summary_entries_for_date_range_raw(
                    self._provider.uuid,
                    month_start_date,
                    end_date,
                    table=ec2_compute_summary_table,
                    filters={"source_uuid": self._provider.uuid},
                )

                # Populate EC2 compute summary table
                accessor.populate_ec2_compute_summary_table_trino(
                    self._provider.uuid, start_date, current_bill_id, markup_value
                )

                # Update mapped tags in EC2 compute summary table
                accessor.update_line_item_daily_summary_with_tag_mapping(
                    month_start_date, end_date, bill_ids, table_name=ec2_compute_summary_table
                )

            for bill in bills:
                if bill.summary_data_creation_datetime is None:
                    bill.summary_data_creation_datetime = timezone.now()
                bill.summary_data_updated_datetime = timezone.now()
                bill.save()

        return start_date, end_date