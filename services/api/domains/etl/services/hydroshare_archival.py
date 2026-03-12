# import os
# import re
# import uuid
# import hsclient
# import tempfile
# from typing import Optional
# from ninja.errors import HttpError
# from hsmodels.schemas.fields import PointCoverage
# from allauth.socialaccount.models import SocialToken, SocialApp
# from django.contrib.auth import get_user_model
# from etl.models import DataArchive, OrchestrationSystem
# from etl.schemas import (
#     HydroShareArchivalFields,
#     HydroShareArchivalPostBody,
#     HydroShareArchivalPatchBody,
# )
# from sta.services.thing import ThingService
# from sta.services.datastream import DatastreamService
# from api.service import ServiceUtils
#
# User = get_user_model()
# thing_service = ThingService()
# datastream_service = DatastreamService()
#
#
# class HydroShareArchivalService(ServiceUtils):
#     def get_hydroshare_thing_archive(
#         self,
#         principal: User,
#         uid: uuid.UUID,
#     ):
#         thing = thing_service.get_thing_for_action(
#             principal=principal, uid=uid, action="view"
#         )
#         orchestration_system = self.get_hydroshare_archival_system()
#
#         return DataArchive.objects.filter(
#             orchestration_system=orchestration_system,
#             workspace=thing.workspace,
#             settings__thingId=str(thing.id),
#         ).first()
#
#     @staticmethod
#     def get_hydroshare_archival_system():
#         try:
#             return OrchestrationSystem.objects.get(
#                 name="HydroShare Archival Manager", workspace=None
#             )
#         except OrchestrationSystem.DoesNotExist:
#             raise HttpError(400, "HydroShare archival has not been configured")
#
#     @staticmethod
#     def get_hydroshare_connection(
#         principal: User,
#     ):
#         hs_client_id = (
#             SocialApp.objects.filter(provider="hydroshare")
#             .values_list("client_id", flat=True)
#             .first()
#         )
#         hs_access_token = (
#             SocialToken.objects.filter(
#                 account__user=principal, account__provider="hydroshare"
#             )
#             .values_list("token", flat=True)
#             .first()
#         )
#
#         if not hs_client_id or not hs_access_token:
#             raise HttpError(400, "No HydroShare account linked to this user account")
#
#         try:
#             hs_conn = hsclient.HydroShare(
#                 client_id=hs_client_id,
#                 token={
#                     "access_token": hs_access_token,
#                     "token_type": "Bearer",
#                 },
#             )
#         except (Exception,) as e:
#             raise HttpError(400, str(e))
#
#         return hs_conn
#
#     def get(self, principal: Optional[User], uid: uuid.UUID):
#         thing_archive = self.get_hydroshare_thing_archive(principal=principal, uid=uid)
#
#         if not thing_archive:
#             raise HttpError(404, "Thing archive not found")
#
#         return {
#             "thing_id": str(uid),
#             "link": str(thing_archive.settings["link"]),
#             "path": thing_archive.settings["path"],
#             "datastreamIds": thing_archive.settings["datastreamIds"],
#         }
#
#     def create(self, principal: User, uid: uuid.UUID, data: HydroShareArchivalPostBody):
#         thing = thing_service.get_thing_for_action(
#             principal=principal, uid=uid, action="edit"
#         )
#         thing_archive = self.get_hydroshare_thing_archive(principal=principal, uid=uid)
#
#         if thing_archive:
#             raise HttpError(400, "Thing archive already exists")
#
#         hydroshare_archival_system = self.get_hydroshare_archival_system()
#         hs_connection = self.get_hydroshare_connection(principal=principal)
#
#         try:
#             if data.link:
#                 try:
#                     archive_resource = hs_connection.resource(
#                         str(data.link).split("/")[-2]
#                     )
#                 except (Exception,):
#                     raise HttpError(400, "Provided HydroShare resource does not exist.")
#             else:
#                 archive_resource = hs_connection.create()
#                 archive_resource.metadata.title = data.resource_title
#                 archive_resource.metadata.abstract = data.resource_abstract
#                 archive_resource.metadata.subjects = data.resource_keywords
#                 archive_resource.metadata.spatial_coverage = PointCoverage(
#                     name=thing.location.name,
#                     north=thing.location.latitude,
#                     east=thing.location.longitude,
#                     projection="WGS 84 EPSG:4326",
#                     type="point",
#                     units="Decimal degrees",
#                 )
#                 archive_resource.metadata.additional_metadata = {
#                     "Sampling Feature Type": thing.sampling_feature_type,
#                     "Sampling Feature Code": thing.sampling_feature_code,
#                     "Site Type": thing.site_type,
#                 }
#
#                 archive_resource.save()
#         except (Exception,) as e:
#             raise HttpError(400, str(e))
#
#         try:
#             thing_archive = DataArchive.objects.create(
#                 workspace=thing.workspace,
#                 name=f"HydroShare Archive for Thing: {thing.name}",
#                 orchestration_system=hydroshare_archival_system,
#                 settings={
#                     "thingId": str(thing.id),
#                     "link": f"https://www.hydroshare.org/resource/{archive_resource.resource_id}/",
#                     "path": data.path,
#                     "datastreamIds": (
#                         [str(datastream_id) for datastream_id in data.datastream_ids]
#                         if data.datastream_ids is not None
#                         else [str(datastream.id) for datastream in thing.datastreams]
#                     ),
#                 },
#             )
#         except (Exception,) as e:
#             raise HttpError(400, str(e))
#
#         self.run(principal=principal, uid=uid, make_public=data.public_resource)
#
#         return {
#             "thing_id": str(uid),
#             "link": str(thing_archive.settings["link"]),
#             "path": thing_archive.settings["path"],
#             "datastreamIds": thing_archive.settings["datastreamIds"],
#         }
#
#     def update(
#         self, principal: User, uid: uuid.UUID, data: HydroShareArchivalPatchBody
#     ):
#         thing = thing_service.get_thing_for_action(
#             principal=principal, uid=uid, action="edit"
#         )
#         thing_archive = self.get_hydroshare_thing_archive(principal=principal, uid=uid)
#
#         if not thing_archive:
#             raise HttpError(404, "Thing archive not found")
#
#         hs_connection = self.get_hydroshare_connection(principal=principal)
#
#         archive_data = data.dict(
#             include=set(HydroShareArchivalFields.model_fields.keys()),
#             exclude_unset=True,
#         )
#
#         if "path" in archive_data:
#             thing_archive.settings["path"] = archive_data["path"]
#
#         if archive_data.get("link") is not None:
#             try:
#                 hs_connection.resource(data.link.split("/")[-2])
#                 thing_archive.settings["link"] = archive_data["link"]
#             except (Exception,):
#                 raise HttpError(400, "Provided HydroShare resource does not exist.")
#
#         if "datastream_ids" in archive_data:
#             thing_archive.settings["datastreamIds"] = (
#                 [str(datastream_id) for datastream_id in archive_data["datastream_ids"]]
#                 if archive_data["datastream_ids"] is not None
#                 else [str(datastream.id) for datastream in thing.datastreams]
#             )
#
#         thing_archive.save()
#
#         self.run(principal=principal, uid=uid)
#
#         return {
#             "thing_id": str(uid),
#             "link": str(thing_archive.settings["link"]),
#             "path": thing_archive.settings["path"],
#             "datastreamIds": thing_archive.settings["datastreamIds"],
#         }
#
#     def delete(self, principal: Optional[User], uid: uuid.UUID):
#         thing_service.get_thing_for_action(principal=principal, uid=uid, action="edit")
#         thing_archive = self.get_hydroshare_thing_archive(principal=principal, uid=uid)
#
#         if not thing_archive:
#             raise HttpError(404, "Thing archive not found")
#
#         thing_archive.delete()
#
#         return "HydroShare archive configuration removed"
#
#     def run(self, principal: Optional[User], uid: uuid.UUID, make_public=False):
#         thing = thing_service.get_thing_for_action(
#             principal=principal, uid=uid, action="edit"
#         )
#         thing_archive = self.get_hydroshare_thing_archive(principal=principal, uid=uid)
#
#         if not thing_archive:
#             raise HttpError(404, "Thing archive not found")
#
#         hs_connection = self.get_hydroshare_connection(principal=principal)
#
#         try:
#             archive_resource = hs_connection.resource(
#                 thing_archive.settings["link"].split("/")[-2]
#             )
#         except (Exception,):
#             raise HttpError(400, "Provided HydroShare resource does not exist.")
#
#         archive_folder = thing_archive.settings["path"].strip()
#
#         if not archive_folder.endswith("/"):
#             archive_folder += "/"
#
#         if archive_folder == "/":
#             archive_folder = ""
#
#         datastreams = (
#             thing.datastreams.filter(pk__in=thing_archive.settings["datastreamIds"])
#             .select_related("processing_level", "observed_property")
#             .all()
#         )
#
#         processing_levels = {}
#
#         for datastream in datastreams:
#             if datastream.processing_level.code in processing_levels:
#                 processing_levels[datastream.processing_level.code].append(datastream)
#             else:
#                 processing_levels[datastream.processing_level.code] = [datastream]
#
#         with tempfile.TemporaryDirectory() as temp_dir:
#             for processing_level, datastreams in processing_levels.items():
#                 processing_level_directory = f"{archive_folder}{processing_level}"
#                 processing_level_directory = re.sub(
#                     r"\s+", "_", processing_level_directory
#                 )
#
#                 try:
#                     archive_resource.folder_delete(processing_level_directory)
#                 except (Exception,):
#                     pass
#
#                 archive_resource.folder_create(processing_level_directory)
#                 os.mkdir(os.path.join(temp_dir, processing_level))
#
#                 datastream_files = []
#
#                 for datastream in datastreams:
#                     file_name = f"{datastream.observed_property.code}.csv"
#                     file_index = 2
#
#                     while file_name in datastream_files:
#                         file_name = (
#                             f"{datastream.observed_property.code}_{str(file_index)}.csv"
#                         )
#                         file_index += 1
#
#                     datastream_files.append(file_name)
#
#                     temp_file_path = os.path.join(temp_dir, processing_level, file_name)
#                     with open(temp_file_path, "w") as csv_file:
#                         for line in datastream_service.generate_csv(datastream):
#                             csv_file.write(line)
#
#                 datastream_file_paths = [
#                     os.path.join(temp_dir, processing_level, datastream_file)
#                     for datastream_file in datastream_files
#                 ]
#
#                 if datastream_file_paths:
#                     archive_resource.file_upload(
#                         *datastream_file_paths,
#                         destination_path=processing_level_directory,
#                     )
#
#             if make_public is True:
#                 try:
#                     archive_resource.set_sharing_status(public=True)
#                     archive_resource.save()
#                 except (Exception,):
#                     pass
#
#         return {
#             "thing_id": str(uid),
#             "link": str(thing_archive.settings["link"]),
#             "path": thing_archive.settings["path"],
#             "datastreamIds": thing_archive.settings["datastreamIds"],
#         }
