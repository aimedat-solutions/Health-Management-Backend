from django.test import TestCase

from ai_assistant.api.serializers import (
    AIModelSerializer,
    AIAgentSerializer,
    ConversationCreateInputSerializer,
    ConversationListOutputSerializer,
    ConversationDetailOutputSerializer,
    ConversationUpdateInputSerializer,
    FeedbackCreateInputSerializer,
    FeedbackOutputSerializer,
    MessageCreateInputSerializer,
    MessageOutputSerializer,
    ReviewCreateInputSerializer,
    ReviewOutputSerializer,
    ReviewUpdateInputSerializer,
    SendMessageResultSerializer,
)
from ai_assistant.constants import MAX_CONVERSATION_TITLE_LENGTH, MAX_MESSAGE_CONTENT_LENGTH


class ConversationCreateInputSerializerTests(TestCase):
    def test_valid_data(self):
        serializer = ConversationCreateInputSerializer(data={"title": "My health question"})
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        self.assertEqual(serializer.validated_data["title"], "My health question")
        self.assertEqual(serializer.validated_data["metadata"], {})

    def test_valid_with_metadata(self):
        serializer = ConversationCreateInputSerializer(
            data={"title": "Test", "metadata": {"source": "mobile"}}
        )
        self.assertTrue(serializer.is_valid())

    def test_missing_title(self):
        serializer = ConversationCreateInputSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_blank_title(self):
        serializer = ConversationCreateInputSerializer(data={"title": ""})
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_title_max_length(self):
        serializer = ConversationCreateInputSerializer(
            data={"title": "a" * (MAX_CONVERSATION_TITLE_LENGTH + 1)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_metadata_not_dict(self):
        serializer = ConversationCreateInputSerializer(
            data={"title": "Test", "metadata": "not a dict"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("metadata", serializer.errors)

    def test_metadata_too_deep(self):
        deep = {"l1": {"l2": {"l3": {"l4": {"l5": {"l6": "too deep"}}}}}}
        serializer = ConversationCreateInputSerializer(data={"title": "Test", "metadata": deep})
        self.assertFalse(serializer.is_valid())

    def test_metadata_none(self):
        serializer = ConversationCreateInputSerializer(data={"title": "Test", "metadata": None})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["metadata"], {})


class ConversationUpdateInputSerializerTests(TestCase):
    def test_valid_partial_title(self):
        serializer = ConversationUpdateInputSerializer(data={"title": "Updated title"})
        self.assertTrue(serializer.is_valid())

    def test_valid_partial_status(self):
        serializer = ConversationUpdateInputSerializer(data={"status": "paused"})
        self.assertTrue(serializer.is_valid())

    def test_invalid_status(self):
        serializer = ConversationUpdateInputSerializer(data={"status": "nonexistent"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)

    def test_blank_title_rejected(self):
        serializer = ConversationUpdateInputSerializer(data={"title": ""})
        self.assertFalse(serializer.is_valid())

    def test_empty_data_valid(self):
        serializer = ConversationUpdateInputSerializer(data={})
        self.assertTrue(serializer.is_valid())


class MessageCreateInputSerializerTests(TestCase):
    def test_valid_text_message(self):
        serializer = MessageCreateInputSerializer(data={"content": "Hello, I have a fever."})
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_blank_content(self):
        serializer = MessageCreateInputSerializer(data={"content": ""})
        self.assertFalse(serializer.is_valid())

    def test_whitespace_only_content(self):
        serializer = MessageCreateInputSerializer(data={"content": "   "})
        self.assertFalse(serializer.is_valid())

    def test_content_too_long(self):
        serializer = MessageCreateInputSerializer(
            data={"content": "a" * (MAX_MESSAGE_CONTENT_LENGTH + 1)}
        )
        self.assertFalse(serializer.is_valid())

    def test_valid_image_url_message(self):
        serializer = MessageCreateInputSerializer(
            data={
                "content": "See this image",
                "content_type": "image_url",
                "content_data": {"url": "https://example.com/img.jpg"},
            }
        )
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_image_url_missing_url(self):
        serializer = MessageCreateInputSerializer(
            data={"content": "See this", "content_type": "image_url", "content_data": {}}
        )
        self.assertFalse(serializer.is_valid())

    def test_image_url_invalid_scheme(self):
        serializer = MessageCreateInputSerializer(
            data={
                "content": "See this",
                "content_type": "image_url",
                "content_data": {"url": "ftp://bad.com/img.jpg"},
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_valid_file_message(self):
        serializer = MessageCreateInputSerializer(
            data={
                "content": "Here is a file",
                "content_type": "file",
                "content_data": {"file_name": "report.pdf", "mime_type": "application/pdf"},
            }
        )
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_file_missing_fields(self):
        serializer = MessageCreateInputSerializer(
            data={"content": "File", "content_type": "file", "content_data": {}}
        )
        self.assertFalse(serializer.is_valid())

    def test_valid_structured_data(self):
        serializer = MessageCreateInputSerializer(
            data={
                "content": "Blood pressure reading",
                "content_type": "structured_data",
                "content_data": {"schema": "vital_signs", "data": {"bp": "120/80"}},
            }
        )
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_structured_missing_fields(self):
        serializer = MessageCreateInputSerializer(
            data={
                "content": "Data",
                "content_type": "structured_data",
                "content_data": {"schema": "test"},
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_content_data_not_dict(self):
        serializer = MessageCreateInputSerializer(
            data={"content": "Test", "content_data": "string"}
        )
        self.assertFalse(serializer.is_valid())

    def test_invalid_content_type(self):
        serializer = MessageCreateInputSerializer(
            data={"content": "Test", "content_type": "video"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("content_type", serializer.errors)


class FeedbackCreateInputSerializerTests(TestCase):
    def test_valid(self):
        serializer = FeedbackCreateInputSerializer(
            data={"rating": 4, "category": "helpful", "comment": "Good answer"}
        )
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_valid_minimal(self):
        serializer = FeedbackCreateInputSerializer(data={"rating": 5})
        self.assertTrue(serializer.is_valid())

    def test_missing_rating(self):
        serializer = FeedbackCreateInputSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("rating", serializer.errors)

    def test_rating_below_min(self):
        serializer = FeedbackCreateInputSerializer(data={"rating": 0})
        self.assertFalse(serializer.is_valid())

    def test_rating_above_max(self):
        serializer = FeedbackCreateInputSerializer(data={"rating": 6})
        self.assertFalse(serializer.is_valid())

    def test_rating_not_integer(self):
        serializer = FeedbackCreateInputSerializer(data={"rating": "good"})
        self.assertFalse(serializer.is_valid())

    def test_invalid_category(self):
        serializer = FeedbackCreateInputSerializer(
            data={"rating": 3, "category": "invalid_cat"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("category", serializer.errors)

    def test_comment_too_long(self):
        serializer = FeedbackCreateInputSerializer(data={"rating": 3, "comment": "a" * 2001})
        self.assertFalse(serializer.is_valid())


class ReviewCreateInputSerializerTests(TestCase):
    def test_valid_defaults(self):
        serializer = ReviewCreateInputSerializer(data={})
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        self.assertEqual(serializer.validated_data["status"], "requested")

    def test_valid_with_notes(self):
        serializer = ReviewCreateInputSerializer(
            data={"status": "in_review", "notes": "Please review this case."}
        )
        self.assertTrue(serializer.is_valid())

    def test_invalid_initial_status(self):
        serializer = ReviewCreateInputSerializer(data={"status": "approved"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)


class ReviewUpdateInputSerializerTests(TestCase):
    def test_valid(self):
        serializer = ReviewUpdateInputSerializer(data={"status": "in_review"})
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_valid_with_notes(self):
        serializer = ReviewUpdateInputSerializer(
            data={"status": "approved", "notes": "Looks good."}
        )
        self.assertTrue(serializer.is_valid())

    def test_missing_status(self):
        serializer = ReviewUpdateInputSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)

    def test_invalid_status(self):
        serializer = ReviewUpdateInputSerializer(data={"status": "invalid"})
        self.assertFalse(serializer.is_valid())


class SerializerRepresentationTests(TestCase):
    def test_serializers_have_correct_meta(self):
        for SerializerClass, expected_model in [
            (ConversationListOutputSerializer, "Conversation"),
            (ConversationDetailOutputSerializer, "Conversation"),
            (MessageOutputSerializer, "Message"),
            (FeedbackOutputSerializer, "MessageFeedback"),
            (ReviewOutputSerializer, "DoctorReview"),
            (AIModelSerializer, "AIModel"),
            (AIAgentSerializer, "AIAgent"),
        ]:
            with self.subTest(serializer=SerializerClass.__name__):
                meta = getattr(SerializerClass, "Meta", None)
                self.assertIsNotNone(meta, f"{SerializerClass.__name__} is missing Meta")
                self.assertEqual(meta.model.__name__, expected_model)
                self.assertTrue(len(meta.fields) > 0)

    def test_send_message_result_serializer(self):
        serializer = SendMessageResultSerializer(data={
            "user_message": None,
            "ai_message": None,
            "triage": {},
            "conversation_status": "active",
        })
        # Serializer can be instantiated, used read-only
        self.assertIsNotNone(serializer)

    def test_error_detail_serializer_structure(self):
        from ai_assistant.api.serializers import ErrorDetailSerializer

        serializer = ErrorDetailSerializer(data={"code": "err", "message": "msg", "details": [], "request_id": "abc"})
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
