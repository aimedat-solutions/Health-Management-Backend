from django.test import TestCase
from rest_framework import status

from ai_assistant.api.response import ApiResponse


class ApiResponseTests(TestCase):
    def test_response_with_data_only(self):
        resp = ApiResponse(data={"id": 1})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {"data": {"id": 1}})

    def test_response_with_meta(self):
        resp = ApiResponse(data=[], meta={"next_cursor": None, "has_next": False})
        self.assertEqual(resp.data["data"], [])
        self.assertEqual(resp.data["meta"]["next_cursor"], None)
        self.assertEqual(resp.data["meta"]["has_next"], False)

    def test_response_without_meta_excludes_key(self):
        resp = ApiResponse(data="ok")
        self.assertNotIn("meta", resp.data)

    def test_response_with_custom_status(self):
        resp = ApiResponse(data=None, status=status.HTTP_201_CREATED)
        self.assertEqual(resp.status_code, 201)

    def test_response_with_meta_none_excludes(self):
        resp = ApiResponse(data="ok", meta=None)
        self.assertNotIn("meta", resp.data)

    def test_response_list_data(self):
        resp = ApiResponse(data=[1, 2, 3])
        self.assertEqual(resp.data["data"], [1, 2, 3])
