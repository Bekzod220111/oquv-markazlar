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


class SearchAndBoundsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from .models import Subject, Center, Course, Review
        eng = Subject.objects.create(name="Ingliz tili", slug="ingliz-tili", alternative_names="English, Английский")
        exam = Subject.objects.create(name="Imtihonga tayyorlov", slug="imtihon")
        prog = Subject.objects.create(name="Dasturlash", slug="dasturlash")
        cls.a = Center.objects.create(name="Najot Ta'lim", address="Toshkent", latitude=41.31, longitude=69.28)
        cls.b = Center.objects.create(name="Alpha School", address="Toshkent", latitude=41.35, longitude=69.30)
        cls.off = Center.objects.create(name="Hidden SAT", address="X", latitude=41.33, longitude=69.29, is_active=False)
        cls.far = Center.objects.create(name="Samarqand Edu", address="Samarqand", latitude=39.65, longitude=66.96)
        c1 = Course.objects.create(name="SAT preparation", category=exam, price_min=450000, price_max=900000)
        c1.centers.add(cls.b, cls.off)
        c2 = Course.objects.create(name="Python Backend", category=prog, price_min=700000, price_max=1200000)
        c2.centers.add(cls.a)
        c3 = Course.objects.create(name="General English", category=eng, price_min=300000, price_max=500000,
                                   alternative_names="Ingliz tili kursi")
        c3.centers.add(cls.a, cls.far)
        Review.objects.create(center=cls.a, author="A", rating=5)
        Review.objects.create(center=cls.a, author="B", rating=4)

    def ids(self, **params):
        r = self.client.get("/api/centers/", params)
        self.assertEqual(r.status_code, 200, r.content)
        return {c["id"] for c in r.json()}

    def test_sat_variants_find_center_by_course_not_name(self):
        for q in ["SAT", "sat", "SAT preparation", "Подготовка к SAT", "podgotovka k sat"]:
            self.assertEqual(self.ids(q=q), {self.b.id}, q)

    def test_inactive_never_returned(self):
        self.assertNotIn(self.off.id, self.ids())

    def test_language_and_typos(self):
        want = {self.a.id, self.far.id}
        for q in ["Ingliz tili", "english", "Английский", "ingliz", "inglis", "Ingliz tili kursi"]:
            self.assertEqual(self.ids(q=q), want, q)
        self.assertEqual(self.ids(q="Python"), {self.a.id})
        self.assertEqual(self.ids(q="pyton"), {self.a.id})
        self.assertEqual(self.ids(q="najot"), {self.a.id})
        self.assertEqual(self.ids(q="Najot Talim"), {self.a.id})
        self.assertEqual(self.ids(q="zzzzzz"), set())

    def test_bbox(self):
        got = self.ids(north=41.4, south=41.2, east=69.4, west=69.1)
        self.assertEqual(got, {self.a.id, self.b.id})
        self.assertEqual(self.client.get("/api/centers/", {"north": "x", "south": 1, "east": 1, "west": 1}).status_code, 400)

    def test_new_center_appears_immediately_and_search_cache_refreshes(self):
        from .models import Center
        self.assertEqual(self.ids(q="Brand New"), set())
        n = Center.objects.create(name="Brand New", address="Y", latitude=41.32, longitude=69.2)
        self.assertEqual(self.ids(q="brand new"), {n.id})
        n.is_active = False
        n.save()
        self.assertEqual(self.ids(q="brand new"), set())

    def test_price_range_and_rating(self):
        data = {c["id"]: c for c in self.client.get("/api/centers/").json()}
        self.assertEqual((data[self.a.id]["price_min"], data[self.a.id]["price_max"]), (300000, 1200000))
        self.assertEqual(data[self.a.id]["rating"], 4.5)
        self.assertNotIn("courses", data[self.a.id])

    def test_detail_full(self):
        d = self.client.get(f"/api/centers/{self.a.id}/").json()
        self.assertEqual(len(d["courses"]), 2)
        self.assertEqual(len(d["reviews"]), 2)
        self.assertEqual(d["review_count"], 2)
        self.assertEqual(self.client.get(f"/api/centers/{self.off.id}/").status_code, 404)

    def test_query_count_is_flat(self):
        self.ids(q="sat")  # cache'ni isitadi
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.client.get("/api/centers/", {"q": "sat", "north": 42, "south": 40, "east": 70, "west": 68})
        self.assertLessEqual(len(ctx), 2)

    def test_suggest_and_course_filter(self):
        from .models import Subject
        d = self.client.get("/api/suggest/", {"q": "Подготовка к SAT"}).json()
        self.assertEqual([c["name"] for c in d["courses"]], ["SAT preparation"])
        self.assertEqual(d["courses"][0]["center_count"], 1)  # faol bo'lmagan markaz sanalmaydi
        self.assertEqual([c["id"] for c in d["centers"]], [self.b.id])
        eng = Subject.objects.get(slug="ingliz-tili")
        self.a.subjects.add(eng)
        d = self.client.get("/api/suggest/", {"q": "ingliz"}).json()
        self.assertEqual(d["subjects"][0]["slug"], "ingliz-tili")
        self.assertEqual(self.client.get("/api/suggest/", {"q": ""}).json()["courses"], [])
        from .models import Course
        cid = Course.objects.get(name="SAT preparation").id
        self.assertEqual(self.ids(course=cid), {self.b.id})
