"""
Unit tests for the parametric claim rules (pure function, no DB, no network).

Run from the project root:
    python -m unittest tests.test_insurance_rules -v
"""
import os
import unittest
from datetime import date, timedelta

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/test")
os.environ.setdefault("SECRET_KEY", "test")

from app.services.insurance_service import DailyObservation, evaluate_policy  # noqa: E402

START = date(2026, 11, 1)
END = date(2027, 5, 1)


def obs(days_rain_temp, last_day=date(2026, 11, 20)):
    """Build observations oldest-first ending at last_day from (rain, temp) tuples."""
    n = len(days_rain_temp)
    return [
        DailyObservation(last_day - timedelta(days=n - 1 - i), r, t)
        for i, (r, t) in enumerate(days_rain_temp)
    ]


def run(observations, existing=(), paid=0.0, start=START, coverage=5_000_000, dry=7):
    return evaluate_policy(
        rain_threshold=50,
        dry_days_threshold=dry,
        temp_threshold=38,
        coverage_amount=coverage,
        policy_start=start,
        policy_end=END,
        observations=observations,
        existing_claims=existing,
        paid_so_far=paid,
    )


class EvaluatePolicyTest(unittest.TestCase):
    def test_normal_weather_no_claim(self):
        self.assertEqual(run(obs([(5, 30)] * 7)), [])

    def test_extreme_rain_pays_50_percent(self):
        d = run(obs([(5, 30)] * 6 + [(75, 29)]))
        self.assertEqual([(c.trigger_type, c.claim_amount, c.trigger_value) for c in d], [("banjir", 2_500_000, 75)])

    def test_rain_exactly_at_threshold_does_not_trigger(self):
        self.assertEqual(run(obs([(5, 30)] * 6 + [(50, 29)])), [])

    def test_extreme_heat_pays_30_percent(self):
        d = run(obs([(5, 30)] * 6 + [(2, 39.5)]))
        self.assertEqual([(c.trigger_type, c.claim_amount) for c in d], [("suhu_ekstrem", 1_500_000)])

    def test_rain_and_heat_same_day_both_pay(self):
        d = run(obs([(5, 30)] * 6 + [(80, 39)]))
        self.assertEqual(sorted(c.trigger_type for c in d), ["banjir", "suhu_ekstrem"])

    def test_drought_after_7_dry_days(self):
        d = run(obs([(5, 30)] + [(0.2, 33)] * 7))
        self.assertEqual([(c.trigger_type, c.trigger_value, c.claim_amount) for c in d], [("kekeringan", 7, 2_000_000)])

    def test_six_dry_days_not_enough(self):
        self.assertEqual(run(obs([(5, 30)] + [(0, 33)] * 6)), [])

    def test_drizzle_below_1mm_counts_as_dry(self):
        d = run(obs([(5, 30)] + [(0.9, 33)] * 7))
        self.assertEqual([c.trigger_type for c in d], ["kekeringan"])

    def test_drought_pays_once_per_dry_spell(self):
        o = obs([(5, 30)] + [(0, 33)] * 9)  # day 9 of the same spell
        spell_day7 = o[-3].day
        self.assertEqual(run(o, existing=[("kekeringan", spell_day7)]), [])

    def test_new_dry_spell_pays_again(self):
        o = obs([(0, 33)] * 3 + [(10, 30)] + [(0, 33)] * 7)  # rain broke the earlier spell
        old_claim_day = o[2].day
        d = run(o, existing=[("kekeringan", old_claim_day)])
        self.assertEqual([c.trigger_type for c in d], ["kekeringan"])

    def test_missing_data_breaks_streak(self):
        self.assertEqual(run(obs([(0, 33)] * 3 + [(None, None)] + [(0, 33)] * 4)), [])

    def test_no_duplicate_for_same_day(self):
        o = obs([(5, 30)] * 6 + [(75, 29)])
        self.assertEqual(run(o, existing=[("banjir", o[-1].day)]), [])

    def test_waiting_period_purchase_day_not_covered(self):
        o = obs([(75, 29)], last_day=START)
        self.assertEqual(run(o), [])
        o2 = obs([(75, 29)], last_day=START + timedelta(days=1))
        self.assertEqual(len(run(o2)), 1)

    def test_dry_days_before_policy_start_do_not_count(self):
        # 7 dry days but only 3 of them are after the purchase day
        last = START + timedelta(days=3)
        self.assertEqual(run(obs([(0, 33)] * 7, last_day=last)), [])

    def test_after_policy_end_no_claim(self):
        self.assertEqual(run(obs([(75, 29)], last_day=END + timedelta(days=1))), [])

    def test_total_payout_capped_at_coverage(self):
        d = run(obs([(5, 30)] * 6 + [(90, 40)]), paid=4_000_000)
        self.assertEqual(sum(c.claim_amount for c in d), 1_000_000)
        self.assertEqual(len(d), 1)  # second trigger gets nothing left

    def test_fully_paid_policy_earns_nothing(self):
        self.assertEqual(run(obs([(5, 30)] * 6 + [(90, 40)]), paid=5_000_000), [])


if __name__ == "__main__":
    unittest.main()
