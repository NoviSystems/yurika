from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import models

class TestImport(TestCase):
    def test_import(self):
        user = User.objects.create_user("test")

        project = models.Project.objects.create(
            name="my project",
            slug="my_project",
        )

        tree = models.ProjectTree(
            name="tree name",
            slug="tree_name",
            project=project,
        )
        tree.save()

        with open("concepts.csv", "r") as importfile:
            self.client.post(reverse("tree-detail", kwargs=dict(
                project_slug="my_project",
                slug="tree_name",
            )),
                             data={"file": importfile}
                             )

