import unittest

from pgdoctor.plan_parser import load_plan
from pgdoctor.rules import Context, diagnose
from pgdoctor import report


def chunk_scan(i, kept, removed, node="Seq Scan", filt="(device_id = 42)"):
    return {"Node Type": node, "Relation Name": f"_hyper_1_{i}_chunk", "Filter": filt,
            "Actual Rows": kept, "Rows Removed by Filter": removed, "Actual Loops": 1, "Plan Rows": kept}


def plan_of(children, root_type="Append", hit=100, read=0, **root):
    r = {"Node Type": root_type, "Plans": children, "Actual Rows": 1, "Actual Loops": 1,
         "Plan Rows": 1, "Shared Hit Blocks": hit, "Shared Read Blocks": read}
    r.update(root)
    return load_plan([{"Plan": r, "Planning Time": 1.0, "Execution Time": 500.0}])


def ids(findings):
    return {f.rule_id for f in findings}


class RuleTests(unittest.TestCase):
    def test_inefficient_filter_fires_and_suggests_index(self):
        p = plan_of([chunk_scan(i, 10, 60_000) for i in range(1, 4)])
        f = diagnose(p, Context("SELECT * FROM sensor_readings WHERE device_id = 42"))
        self.assertIn("INEFFICIENT_FILTER", ids(f))
        fix = next(x for x in f if x.rule_id == "INEFFICIENT_FILTER").sql_fix
        self.assertIn("(device_id, time DESC)", fix)

    def test_inefficient_filter_quiet_when_selective(self):
        p = plan_of([chunk_scan(1, 5000, 100)])
        self.assertNotIn("INEFFICIENT_FILTER", ids(diagnose(p, Context("SELECT * FROM t"))))

    def test_no_chunk_exclusion_wrapped_time(self):
        p = plan_of([chunk_scan(i, 100, 0, filt=None) for i in range(1, 13)])
        f = diagnose(p, Context("SELECT 1 FROM t WHERE date_trunc('day', time) = now()"))
        hit = next(x for x in f if x.rule_id == "NO_CHUNK_EXCLUSION")
        self.assertIn("function", hit.explanation)

    def test_no_chunk_exclusion_missing_range(self):
        p = plan_of([chunk_scan(i, 100, 0, filt=None) for i in range(1, 13)])
        f = diagnose(p, Context("SELECT avg(x) FROM t WHERE device_id = 1"))
        self.assertIn("NO_CHUNK_EXCLUSION", ids(f))

    def test_no_chunk_exclusion_quiet_with_time_range(self):
        p = plan_of([chunk_scan(i, 100, 0, filt=None) for i in range(1, 13)])
        f = diagnose(p, Context("SELECT 1 FROM t WHERE time > now() - interval '7 days'"))
        self.assertNotIn("NO_CHUNK_EXCLUSION", ids(f))

    def test_high_buffer_reads(self):
        p = plan_of([], hit=1000, read=50_000)
        self.assertIn("HIGH_BUFFER_READS", ids(diagnose(p, Context("SELECT 1"))))

    def test_naive_aggregate_and_cagg_exemption(self):
        q = "SELECT time_bucket('1 hour', time) b, avg(x) FROM t GROUP BY b"
        p = plan_of([chunk_scan(i, 300_000, 0, filt=None) for i in range(1, 4)])
        self.assertIn("NAIVE_AGGREGATE", ids(diagnose(p, Context(q))))
        cagg = plan_of([{"Node Type": "Seq Scan", "Relation Name": "_materialized_hypertable_5",
                         "Actual Rows": 2000, "Actual Loops": 1, "Plan Rows": 2000}])
        self.assertNotIn("NAIVE_AGGREGATE", ids(diagnose(cagg, Context(q))))

    def test_sort_spill_and_bad_estimate(self):
        p = plan_of([], root_type="Sort", **{"Sort Method": "external merge", "Plan Rows": 10, "Actual Rows": 50_000})
        got = ids(diagnose(p, Context("SELECT 1")))
        self.assertIn("SORT_SPILL", got)
        self.assertIn("BAD_ROW_ESTIMATE", got)

    def test_clean_plan_has_no_findings_and_report_says_so(self):
        p = plan_of([{"Node Type": "Index Scan", "Relation Name": "_hyper_1_1_chunk",
                      "Actual Rows": 100, "Actual Loops": 1, "Plan Rows": 100}])
        f = diagnose(p, Context("SELECT 1 FROM t WHERE time > now()"))
        self.assertEqual(f, [])
        self.assertIn("did not find", report.render("q", "SELECT 1", p, f))

    def test_report_contains_plain_language_sections(self):
        p = plan_of([chunk_scan(i, 10, 60_000) for i in range(1, 4)])
        q = "SELECT * FROM sensor_readings WHERE device_id = 42"
        md = report.render("q1", q, p, diagnose(p, Context(q)))
        for s in ("What is happening", "What we recommend", "phone book"):
            self.assertIn(s, md)


if __name__ == "__main__":
    unittest.main()
