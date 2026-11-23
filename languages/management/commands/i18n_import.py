"""Fill EMPTY translation fields from the Colab results (see languages/i18n_job.py). Never overwrites a
translation that already has text; every machine-filled field is logged in JOB_ROOT/machine_log.jsonl."""
import json
import os
import time

from django.core.management.base import BaseCommand
from django.db import models as M, transaction

from languages import i18n_job as J


class Command(BaseCommand):
    help = "Import machine translations into empty translation fields."

    def add_arguments(self, parser):
        parser.add_argument("--job", choices=["core", "schemes", "all"], default="all")
        parser.add_argument("--lang", default="", help="one site language code (default: every language with results)")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--changed-only", action="store_true", help="skip a job+language whose results did not change since the last import")

    def handle(self, *a, **o):
        jobs = ["core", "schemes"] if o["job"] == "all" else [o["job"]]
        stamp_file = os.path.join(J.JOB_ROOT, "import_stamps.json")
        try:
            stamps = json.load(open(stamp_file))
        except (OSError, ValueError):
            stamps = {}
        total = 0
        for job in jobs:
            rdir = os.path.join(J.job_dir(job), "results")
            langs = [o["lang"]] if o["lang"] else (sorted(os.listdir(rdir)) if os.path.isdir(rdir) else [])
            for lang in langs:
                if lang not in J.IT2_CODES:
                    continue
                ld = os.path.join(rdir, lang)
                newest = max([os.path.getmtime(os.path.join(ld, f)) for f in os.listdir(ld)] or [0]) if os.path.isdir(ld) else 0
                sk = f"{job}:{lang}"
                if o["changed_only"] and stamps.get(sk, 0) >= newest:
                    continue
                tr = J.load_results(job, lang)
                if not tr:
                    continue
                n = self.import_one(job, lang, tr, o["dry_run"])
                total += n
                self.stdout.write(f"{job} {lang}: {len(tr):,} translated segments -> {n:,} fields filled")
                if not o["dry_run"]:
                    stamps[sk] = newest
        if not o["dry_run"]:
            with open(stamp_file + ".tmp", "w") as f:
                json.dump(stamps, f)
            os.replace(stamp_file + ".tmp", stamp_file)
        self.stdout.write(f"done: {total:,} fields filled")

    def import_one(self, job, lang, tr, dry):
        filled, log = 0, []
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        if job == "core":
            filled += self.import_ui(lang, tr, dry, log, now)
        for tm, base, fk, pairs in J.translatable_models():
            pairs = [(tf, bf) for tf, bf in pairs if J.in_job(job, base, bf)]
            if not pairs:
                continue
            maxlen = {f.name: f.max_length for f in tm._meta.fields if isinstance(f, M.CharField)}
            rows = {getattr(r, fk + "_id"): r for r in tm.objects.filter(language_id=lang)}
            to_create, to_update, upd_fields = [], [], set()
            for obj in base.objects.values("pk", *[bf for _, bf in pairs]).iterator():
                row = rows.get(obj["pk"])
                new_row = None
                for tf, bf in pairs:
                    src = str(obj[bf] or "")
                    if not J.segments_of(src):
                        continue
                    if row is not None and str(getattr(row, tf) or "").strip():
                        continue                      # already translated (human or earlier import): keep it
                    val = J.rebuild(src, tr)
                    if not val or (maxlen.get(tf) and len(val) > maxlen[tf]):
                        continue
                    if row is None:
                        if new_row is None:
                            new_row = tm(**{fk + "_id": obj["pk"], "language_id": lang})
                        setattr(new_row, tf, val)
                    else:
                        setattr(row, tf, val)
                        upd_fields.add(tf)
                        if row not in to_update:
                            to_update.append(row)
                    filled += 1
                    log.append({"at": now, "lang": lang, "model": tm.__name__, "pk": obj["pk"], "field": tf})
                if new_row is not None:
                    to_create.append(new_row)
            if not dry and (to_create or to_update):
                with transaction.atomic():
                    if to_create:
                        tm.objects.bulk_create(to_create, batch_size=500)
                    if to_update:
                        tm.objects.bulk_update(to_update, list(upd_fields), batch_size=500)
        if not dry and log:
            os.makedirs(J.JOB_ROOT, exist_ok=True)
            with open(os.path.join(J.JOB_ROOT, "machine_log.jsonl"), "a", encoding="utf-8") as f:
                for x in log:
                    f.write(json.dumps(x, ensure_ascii=False) + "\n")
        return filled

    def import_ui(self, lang, tr, dry, log, now):
        data = J.load_ui_strings()                     # hand-made + earlier machine
        machine = J._read_json(J.ui_machine_path())
        n = 0
        for en, entry in data.items():
            if str(entry.get(lang) or "").strip():
                continue
            val = J.rebuild(en, tr)
            if val:
                machine.setdefault(en, {})[lang] = val
                n += 1
                log.append({"at": now, "lang": lang, "model": "ui_strings", "pk": en[:60], "field": "text"})
        if n and not dry:
            data = machine
            p = J.ui_machine_path()
            with open(p + ".tmp", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
            os.replace(p + ".tmp", p)
        return n
