from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Center


class ExistingCenterFunctionalityTests(TestCase):
    def setUp(self):
        self.center = Center.objects.create(
            name="Manual Center",
            address="Tashkent",
            latitude=41.311,
            longitude=69.279,
        )
        Center.objects.create(
            name="Inactive Center",
            address="Tashkent",
            latitude=41.312,
            longitude=69.280,
            is_active=False,
        )

    def test_public_centers_api_returns_active_centers(self):
        response = self.client.get("/api/centers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()], ["Manual Center"])

    def test_map_page_still_renders_map_and_frontend_script(self):
        response = self.client.get(reverse("map"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="map"')
        self.assertContains(response, 'id="center-sheet"')
        self.assertContains(response, 'id="center-sheet-drag"')
        self.assertContains(response, 'aria-modal="true"')
        self.assertContains(response, "js/map.js")

    def test_admin_can_access_manually_managed_center_forms(self):
        user = get_user_model().objects.create_superuser(
            username="center-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        changelist = self.client.get(reverse("admin:centers_center_changelist"))
        change_form = self.client.get(
            reverse("admin:centers_center_change", args=(self.center.pk,))
        )

        self.assertEqual(changelist.status_code, 200)
        self.assertContains(changelist, "Manual Center")
        self.assertEqual(change_form.status_code, 200)
        self.assertNotContains(changelist, "Discover centers")

    def test_admin_still_lists_course_and_subject_management(self):
        user = get_user_model().objects.create_superuser(
            username="course-admin",
            email="courses@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        subjects = self.client.get(reverse("admin:centers_subject_changelist"))
        courses = self.client.get(reverse("admin:centers_course_changelist"))

        self.assertEqual(subjects.status_code, 200)
        self.assertEqual(courses.status_code, 200)
