"""Cut Sahyog Setu's English content into batches for the Colab translation notebook (see languages/i18n_job.py)."""
from django.core.management.base import BaseCommand

from languages import i18n_job as J


class Command(BaseCommand):
    help = "Write the translation job batches (core and/or schemes) for the Colab notebook."

    def add_arguments(self, parser):
        parser.add_argument("--job", choices=["core", "schemes", "all"], default="all")
        parser.add_argument("--langs", default=",".join(J.IT2_CODES), help="comma list of site language codes")

    def handle(self, *a, **o):
        langs = [x.strip() for x in o["langs"].split(",") if x.strip() in J.IT2_CODES]
        for job in (["core", "schemes"] if o["job"] == "all" else [o["job"]]):
            m = J.write_job(job, langs)
            self.stdout.write(f"{job}: {m['segments']:,} segments, {m['chars']:,} characters, {m['chunks']} batches, {len(langs)} languages")
