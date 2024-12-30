import logging
import typing as t

from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django_filters import AllValuesMultipleFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.common.pagination import ListPaginator
from api.common.permissions.settings_access import SettingsAccessPermission
from api.settings.tags.serializers import SettingsTagIDSerializer
from api.settings.tags.serializers import SettingsTagSerializer
from api.settings.utils import NonValidatedMultipleChoiceFilter
from api.settings.utils import SettingsFilter
from masu.config import Config
from reporting.provider.all.models import EnabledTagKeys
from reporting.provider.all.models import TagMapping

LOG = logging.getLogger(__name__)


def get_enabled_tags_count() -> int:
    return EnabledTagKeys.objects.filter(enabled=True).count()


class SettingsTagFilter(SettingsFilter):
    key = NonValidatedMultipleChoiceFilter(lookup_expr="icontains")
    uuid = AllValuesMultipleFilter()
    provider_type = AllValuesMultipleFilter()
    source_type = AllValuesMultipleFilter(field_name="provider_type")

    class Meta:
        model = EnabledTagKeys
        fields = ("enabled",)
        default_ordering = ["provider_type", "-enabled"]


class SettingsTagView(generics.GenericAPIView):
    queryset = EnabledTagKeys.objects.all()
    serializer_class = SettingsTagSerializer
    permission_classes = (SettingsAccessPermission,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = SettingsTagFilter

    @method_decorator(never_cache)
    def get(self, request: Request, **kwargs):
        filtered_qset = self.filter_queryset(self.get_queryset())
        serializer = self.serializer_class(filtered_qset, many=True)

        paginator = ListPaginator(serializer.data, request)
        response = paginator.paginated_response

        additional_meta = {
            "enabled_tags_count": get_enabled_tags_count(),
            "enabled_tags_limit": Config.ENABLED_TAG_LIMIT,
        }
        response.data["meta"].update(additional_meta)

        return response


class SettingsTagUpdateView(APIView):
    permission_classes = [SettingsAccessPermission]

    def put(self, request: Request, **kwargs) -> Response:
        uuid_list = request.data.get("ids", [])
        serializer = SettingsTagIDSerializer(data={"id_list": uuid_list})
        serializer.is_valid(raise_exception=True)

        objects = EnabledTagKeys.objects.filter(uuid__in=uuid_list)
        if response := self._check_tag_mapping(uuid_list):
            return response

        if response := self._check_limit(objects):
            return response

        objects.update(enabled=self.enabled)
        EnabledTagKeys.objects.bulk_update(objects, ["enabled"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class SettingsEnableTagView(SettingsTagUpdateView):
    enabled = True

    def _check_limit(self, qs: QuerySet) -> t.Optional[Response]:
        if Config.ENABLED_TAG_LIMIT > 0:
            # Only count UUIDs requested to be enabled that are currently disabled.
            records_to_update_count = qs.filter(enabled=False).count()
            enabled_tags_count = get_enabled_tags_count()
            future_enabled_tags_count = enabled_tags_count + records_to_update_count
            if future_enabled_tags_count > Config.ENABLED_TAG_LIMIT:
                return Response(
                    {
                        "error": f"The maximum number of enabled tags is {Config.ENABLED_TAG_LIMIT}.",
                        "enabled": enabled_tags_count,
                        "limit": Config.ENABLED_TAG_LIMIT,
                    },
                    status=status.HTTP_412_PRECONDITION_FAILED,
                )

    def _check_tag_mapping(self, qs):
        # There are protections that prevent
        # unenabled tags from being added to
        # TagMapping feature.
        pass


class SettingsDisableTagView(SettingsTagUpdateView):
    enabled = False

    def _check_limit(self, qs):
        pass

    def _check_tag_mapping(self, uuid_list) -> t.Optional[Response]:
        """Checks that a map tag can not be enabled or disabled."""
        tag_keys = TagMapping.objects.filter(Q(parent__uuid__in=uuid_list) | Q(child__uuid__in=uuid_list))
        if not tag_keys:
            return
        tracked_errors = set()
        for tag_key in tag_keys:
            if str(tag_key.parent.uuid) in uuid_list:
                tracked_errors.add(str(tag_key.parent.uuid))
            if str(tag_key.child.uuid) in uuid_list:
                tracked_errors.add(str(tag_key.child.uuid))
        return Response(
            {
                "error": "Can not disable a key associated with a tag mapping",
                "ids": tracked_errors,
            },
            status=status.HTTP_412_PRECONDITION_FAILED,
        )
